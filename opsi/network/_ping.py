# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import errno
import select
import socket
import struct
import time
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import TypeAlias

from opsi.logging import get_logger
from opsi.network._resolve import resolve_hostname

ICMP_ECHO_REPLY = 0
ICMP_ECHO_REQUEST = 8
ICMPV6_ECHO_REQUEST = 128
ICMPV6_ECHO_REPLY = 129
PING_PAYLOAD_SIZE = 192

IPAddress: TypeAlias = IPv4Address | IPv6Address
SocketAddress: TypeAlias = tuple[str, int] | tuple[str, int, int, int]

logger = get_logger("opsi")


@dataclass(frozen=True, kw_only=True)
class PingTarget:
	address: IPAddress
	socket_address: SocketAddress
	family: socket.AddressFamily
	protocol: int


@dataclass(frozen=True, kw_only=True)
class PingResult:
	destination: IPAddress
	total_time: float = 0.0
	packets_send: int
	packets_received: int
	packet_loss: float
	rtt_min: float | None
	rtt_max: float | None
	rtt_avg: float | None


def checksum(source_bytes: bytes) -> int:
	"""
	Calculate the Internet checksum for ICMP packets.

	Parameters
	----------
	source_bytes : bytes
		The packet bytes to calculate the checksum for.

	Returns
	-------
	int
		The 16-bit one's complement checksum.
	"""
	if len(source_bytes) % 2:
		source_bytes += b"\0"

	total = sum(source_bytes[index] << 8 | source_bytes[index + 1] for index in range(0, len(source_bytes), 2))
	while total >> 16:
		total = (total & 0xFFFF) + (total >> 16)

	return ~total & 0xFFFF


def resolve_ping_target(destination: str | IPv4Address | IPv6Address) -> PingTarget:
	"""
	Resolve a destination to an IP address and socket parameters.

	Parameters
	----------
	destination : str | IPv4Address | IPv6Address
		IP address or hostname to ping.

	Returns
	-------
	PingTarget
		The normalized target address and socket details.
	"""
	if isinstance(destination, str):
		try:
			destination = ip_address(destination)
		except ValueError:
			ip_addresses = resolve_hostname(str(destination))
			if not ip_addresses:
				raise ValueError(f"Hostname {destination} could not be resolved to an IP address.")
			destination = ip_addresses[0]

	if isinstance(destination, IPv4Address):
		return PingTarget(address=destination, socket_address=(str(destination), 0), family=socket.AF_INET, protocol=socket.IPPROTO_ICMP)
	if isinstance(destination, IPv6Address):
		return PingTarget(
			address=destination, socket_address=(str(destination), 0, 0, 0), family=socket.AF_INET6, protocol=socket.IPPROTO_ICMPV6
		)
	raise ValueError(f"Unsupported destination type: {type(destination)}")


def _icmpv6_checksum(source_address: IPv6Address, destination_address: IPv6Address, packet: bytes) -> int:
	"""Calculate the ICMPv6 checksum including the IPv6 pseudo-header."""
	pseudo_header = source_address.packed + destination_address.packed + struct.pack("!I3xB", len(packet), socket.IPPROTO_ICMPV6)
	return checksum(pseudo_header + packet)


def create_echo_request(
	identifier: int,
	sequence: int,
	request_type: int,
	*,
	source_address: IPv6Address | None = None,
	destination_address: IPv6Address | None = None,
) -> bytes:
	"""
	Create an ICMP echo request packet.

	Parameters
	----------
	identifier : int
		The echo request identifier.

	sequence : int
		The echo request sequence number.

	request_type : int
		The ICMP echo request type.

	source_address : IPv6Address, optional
		The IPv6 source address used for ICMPv6 checksums.

	destination_address : IPv6Address, optional
		The IPv6 destination address used for ICMPv6 checksums.

	Returns
	-------
	bytes
		The ICMP echo request packet.
	"""
	checksum_value = 0
	header = struct.pack("!BBHHH", request_type, 0, checksum_value, identifier, sequence)
	payload = struct.pack("!d", time.perf_counter()) + b"Q" * (PING_PAYLOAD_SIZE - struct.calcsize("!d"))
	packet = header + payload

	if request_type == ICMPV6_ECHO_REQUEST:
		if source_address and destination_address:
			checksum_value = _icmpv6_checksum(source_address, destination_address, packet)
	else:
		checksum_value = checksum(packet)

	return struct.pack("!BBHHH", request_type, 0, checksum_value, identifier, sequence) + payload


def _reply_offset(packet: bytes, family: socket.AddressFamily) -> int:
	"""Return the byte offset where the ICMP reply starts."""
	if not packet:
		return 0

	version = packet[0] >> 4
	if family == socket.AF_INET and version == 4:
		return (packet[0] & 0x0F) * 4
	if family == socket.AF_INET6 and version == 6:
		return 40
	return 0


def _parse_echo_reply(packet: bytes, family: socket.AddressFamily) -> tuple[int, float] | None:
	"""Return the packet identifier and send time from a matching ICMP echo reply."""
	offset = _reply_offset(packet, family)
	packet = packet[offset:]
	if len(packet) < 8 + struct.calcsize("!d"):
		return None

	reply_type, _, _, identifier, _ = struct.unpack("!BBHHH", packet[:8])
	if family == socket.AF_INET and reply_type != ICMP_ECHO_REPLY:
		return None
	if family == socket.AF_INET6 and reply_type != ICMPV6_ECHO_REPLY:
		return None

	send_time = struct.unpack("!d", packet[8 : 8 + struct.calcsize("!d")])[0]
	return identifier, send_time


def receive_one_ping(raw_socket: socket.socket, identifier: int, timeout: float, family: socket.AddressFamily) -> float | None:
	"""
	Receive an ICMP echo reply from a socket.

	Parameters
	----------
	raw_socket : socket.socket
		The raw socket to receive from.

	identifier : int
		The echo request identifier to match.

	timeout : float
		The receive timeout in seconds.

	family : socket.AddressFamily
		The socket address family.

	Returns
	-------
	float | None
		The round-trip delay in seconds, or None if no matching reply was received before the timeout.
	"""
	logger.trace("Waiting for ping reply with identifier %d", identifier)
	time_left = timeout
	while time_left > 0:
		select_started = time.perf_counter()
		ready, _, _ = select.select([raw_socket], [], [], time_left)
		select_duration = time.perf_counter() - select_started

		if not ready:
			return None

		received_time = time.perf_counter()
		packet, _ = raw_socket.recvfrom(65535)
		reply = _parse_echo_reply(packet, family)
		if reply and reply[0] == identifier:
			return received_time - reply[1]

		time_left -= select_duration

	return None


def send_one_ping(raw_socket: socket.socket, target: PingTarget, identifier: int, sequence: int = 1) -> None:
	"""
	Send one ICMP echo request.

	Parameters
	----------
	raw_socket : socket.socket
		The raw socket to send from.

	target : PingTarget
		The target address and socket details.

	identifier : int
		The echo request identifier.

	sequence : int, default: 1
		The echo request sequence number.
	"""
	logger.trace("Sending ping to %s with identifier %d", target.address, identifier)
	source_address = None
	if isinstance(target.address, IPv6Address):
		try:
			raw_socket.connect(target.socket_address)
		except OSError as error:
			if error.errno != errno.EISCONN:
				raise
		source_address = ip_address(raw_socket.getsockname()[0])

	packet = create_echo_request(
		identifier,
		sequence,
		ICMPV6_ECHO_REQUEST if target.family == socket.AF_INET6 else ICMP_ECHO_REQUEST,
		source_address=source_address if isinstance(source_address, IPv6Address) else None,
		destination_address=target.address if isinstance(target.address, IPv6Address) else None,
	)
	if target.family == socket.AF_INET6:
		raw_socket.send(packet)
		return

	raw_socket.sendto(packet, target.socket_address)


def ping(destination: str | IPv4Address | IPv6Address, timeout: float = 2, count: int = 1) -> PingResult:
	"""
	Ping a destination by using ICMP echo requests.

	Parameters
	----------
	destination : str | IPv4Address | IPv6Address
		The IP address or hostname to ping.

	timeout : float, default: 2
		The receive timeout in seconds.

	count : int, default: 1
		The number of echo requests to send.

	Returns
	-------
	float | None
		The average round-trip delay in seconds, or None if the request timed out.

	"""
	target = resolve_ping_target(destination)
	try:
		raw_socket = socket.socket(target.family, socket.SOCK_RAW, target.protocol)
	except OSError as error:
		if error.errno == errno.EPERM:
			raise OSError(errno.EPERM, "ICMP messages can only be sent from processes running as root.") from error
		raise

	start_time = time.monotonic()
	rtts = []
	try:
		for idx in range(count):
			identifier = int(time.time() * 100000) & 0xFFFF
			rtt = None
			try:
				send_one_ping(raw_socket, target, identifier)
				rtt = receive_one_ping(raw_socket, identifier, timeout, target.family)
			except Exception as exc:
				logger.debug("Error sending or receiving ping: %s", exc)
			logger.trace("Ping RTT: %s seconds", rtt)
			if rtt is not None:
				rtts.append(rtt)
			if idx < count - 1:
				time.sleep(1)
	finally:
		total_time = time.monotonic() - start_time
		raw_socket.close()

	return PingResult(
		destination=target.address,
		total_time=total_time,
		packets_send=count,
		packets_received=len(rtts),
		packet_loss=(count - len(rtts)) / count * 100,
		rtt_min=min(rtts) if rtts else None,
		rtt_max=max(rtts) if rtts else None,
		rtt_avg=sum(rtts) / len(rtts) if rtts else None,
	)
