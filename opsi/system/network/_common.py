# opsicommon is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2020-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
system.network
"""

import concurrent.futures
import ipaddress
import os
import socket
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import netifaces
from dns.resolver import Resolver

from opsi.logging import get_logger
from opsi.opsiservice.model.type import to_fqdn
from opsi.system.info import is_linux

if TYPE_CHECKING:
	from requests import Session

logger = get_logger("opsi")


@dataclass
class NetworkInterface:
	"""
	Network interface information.
	"""

	family: int  # socket.AF_INET or socket.AF_INET6
	name: str
	address: ipaddress.IPv4Address | ipaddress.IPv6Address
	netmask: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
	broadcast: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
	prefixlen: int | None = None
	mac_address: str | None = None
	is_loopback: bool = False
	is_link_local: bool = False
	is_default_gateway: bool = False


@dataclass
class NetworkRoute:
	"""
	Network route information.
	"""

	family: int  # socket.AF_INET or socket.AF_INET6
	interface_name: str
	gateway: ipaddress.IPv4Address | ipaddress.IPv6Address
	destination: ipaddress.IPv4Network | ipaddress.IPv6Network | None = None
	is_default: bool = False


@dataclass
class DNSNameserver:
	"""
	DNS nameserver information.
	"""

	family: int  # socket.AF_INET or socket.AF_INET6
	address: ipaddress.IPv4Address | ipaddress.IPv6Address


@dataclass
class NetworkInfo:
	"""
	Network information.
	"""

	interfaces: list[NetworkInterface] = field(default_factory=list)
	routes: list[NetworkRoute] = field(default_factory=list)
	dns_nameservers: list[DNSNameserver] = field(default_factory=list)
	search_domains: list[str] = field(default_factory=list)


def get_network_info(*, include_link_local: bool = True) -> NetworkInfo:
	# res.search[0].to_unicode(omit_final_dot=True)
	network_info = NetworkInfo()
	gateways = netifaces.gateways()
	logger.debug("Gateways: %s", gateways)
	default_gw = gateways.get("default")
	if default_gw and isinstance(default_gw, dict):
		for family, info in default_gw.items():
			network_info.routes.append(
				NetworkRoute(
					family=family,
					interface_name=info[1],
					gateway=ipaddress.ip_address(info[0]),
					is_default=True,
				)
			)

	nameservers = []
	try:
		resolver = Resolver()
		network_info.search_domains = []
		for search_domain in resolver.search:
			search_domain_str = search_domain.to_unicode().strip(". ")
			if search_domain_str and search_domain_str not in network_info.search_domains:
				network_info.search_domains.append(search_domain_str)
		nameservers = [str(x) for x in resolver.nameservers]
		logger.debug("Nameservers from Resolver: %s", nameservers)
	except Exception as err:
		logger.warning("Failed to get nameservers from Resolver: %s", err)

	for nameserver in nameservers:
		try:
			address = ipaddress.ip_address(nameserver)
			network_info.dns_nameservers.append(
				DNSNameserver(address=address, family=socket.AF_INET6 if address.version == 6 else socket.AF_INET)
			)
		except ValueError:
			continue

	ifaces = netifaces.interfaces()
	logger.debug("Network interfaces: %s", ifaces)
	for iface_name in ifaces:
		if_addresses = netifaces.ifaddresses(iface_name)
		for family in (socket.AF_INET, socket.AF_INET6):
			for if_info in if_addresses.get(family, []):
				try:
					address = ipaddress.ip_address(if_info["addr"].split("%")[0])
					if (not include_link_local) and address.is_link_local:
						continue
				except ValueError:
					continue

				network_address = (
					ipaddress.ip_network(f"{if_info['addr']}/{if_info['netmask'].split('/')[-1]}", strict=False)
					if "netmask" in if_info
					else None
				)
				network_info.interfaces.append(
					NetworkInterface(
						family=family,
						name=iface_name,
						address=address,
						netmask=network_address.netmask if network_address else None,
						broadcast=network_address.broadcast_address if network_address else None,
						prefixlen=network_address.prefixlen if network_address else None,
						mac_address=if_addresses.get(netifaces.AF_LINK, [{}])[0].get("addr"),
						is_loopback=address.is_loopback,
						is_link_local=address.is_link_local,
						is_default_gateway=any(
							route.is_default and route.interface_name == iface_name and route.family == family
							for route in network_info.routes
						),
					)
				)
	return network_info


def get_fqdn() -> str:
	fqdn = ""
	try:
		fqdn = socket.getfqdn()
		return to_fqdn(fqdn.lower())
	except Exception as err:
		logger.debug("Failed to get FQDN by socket.getfqdn(): %s - %s", fqdn, err)

	if os.name == "posix":
		logger.debug("Trying to get FQDN by running hostname -f")
		try:
			proc = subprocess.run(["hostname", "-f"], capture_output=True, text=True, check=False, timeout=0.1)
			logger.debug("hostname -f returned: %s (exit code %d)", proc.stdout.strip(), proc.returncode)
			if proc.returncode == 0:
				return to_fqdn(proc.stdout.strip())
		except Exception as err:
			logger.debug("Failed to get FQDN by running hostname -f: %s", err)

	for hostname in get_hostnames():
		if "." in hostname:
			try:
				return to_fqdn(hostname.lower())
			except ValueError:
				continue

	raise RuntimeError("Failed to get FQDN")


def get_domain() -> str:
	return ".".join(get_fqdn().split(".")[1:])


def _gethostbyaddr_with_timeout(address: str, timeout: float) -> tuple[str, list[str], list[str]]:
	with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
		future = executor.submit(socket.gethostbyaddr, address)
		try:
			return future.result(timeout=timeout)
		except concurrent.futures.TimeoutError:
			raise TimeoutError(f"DNS lookup for {address} timed out after {timeout} seconds")


def get_hostnames() -> set[str]:
	names = {"localhost", "ip6-localhost", "ip6-loopback"}
	try:
		names.add(to_fqdn(socket.getfqdn()))
	except Exception as err:
		logger.info("Failed to get fqdn: %s", err)
	for interface in get_network_info(include_link_local=False).interfaces:
		try:
			addr = str(interface.address)
			(hostname, aliases, _addr) = _gethostbyaddr_with_timeout(addr, timeout=0.1)
			if hostname != addr:
				names.add(hostname)
				for alias in aliases:
					names.add(alias)
		except (socket.error, TimeoutError) as err:
			logger.info("No hostname for %s: %s", addr, err)
	return names


def prepare_proxy_environment(
	hostname: str, proxy_url: str | None = "system", no_proxy_addresses: list[str] | None = None, session: Session | None = None
) -> Session:
	"""
	proxy_url can be:
	* an explicid url like http://<address>:<port>
	* the string "system" in which case the os environment determines proxy behaviour
	* emptystring or None to disable proxy usage.
	If session is given its proxy settings are adapted. Else a new session is created and returned.
	"""
	for env_var in ("CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE"):
		if env_var in os.environ:
			os.environ.pop(env_var)

	def add_protocol(host: str, protocol: str = "http") -> str:
		if not host or "://" in host:
			return host
		logger.debug("Adding schema '%s://' to form proxy url from host '%s'", protocol, host)
		return "://".join((protocol, host))

	if no_proxy_addresses is None:
		no_proxy_addresses = ["::1", "127.0.0.1", "ip6-localhost", "ip6-loopback", "localhost"]
	if session is None:
		# Import is slow
		from requests import Session

		session = Session()

	if proxy_url:
		# Use a proxy
		if is_linux():
			# on windows, services that use WinHTTP API will use the global (netsh) proxy settings
			# https://learn.microsoft.com/en-us/windows/win32/api/winhttp/nf-winhttp-winhttpgetdefaultproxyconfiguration

			# on macos, services use the system proxy settings (networksetup -setwebproxy)
			# https://apple.stackexchange.com/questions/226544/how-to-set-proxy-on-os-x-terminal-permanently
			from opsi.system.linux import update_environment_from_config_files

			try:
				update_environment_from_config_files()
			except Exception as error:
				logger.error("Failed to update environment from config files: %s", error)

		env_http_proxy = os.environ.get("http_proxy") or ""
		env_https_proxy = os.environ.get("https_proxy") or ""
		env_no_proxy = os.environ.get("no_proxy") or ""
		no_proxy_list: list[str] = [x.strip() for x in env_no_proxy.split(",") if x.strip()]
		logger.debug(
			"Current proxy related environment variables: http_proxy=%s, https_proxy=%s, no_proxy=%s, no_proxy_list=%s",
			env_http_proxy,
			env_https_proxy,
			env_no_proxy,
			no_proxy_list,
		)

		if proxy_url.lower() == "system":
			logger.debug("Using system proxy settings")
			# Making sure system proxy has correct form
			if env_http_proxy:
				os.environ["http_proxy"] = add_protocol(env_http_proxy)
			if env_https_proxy:
				os.environ["https_proxy"] = add_protocol(env_https_proxy)
			if no_proxy_list != ["*"]:
				no_proxy_list.extend(no_proxy_addresses)
		else:
			proxy_url = add_protocol(proxy_url)
			logger.debug("Using explicit proxy URL: %s", proxy_url)
			if hostname in no_proxy_addresses:
				logger.info("Not using proxy for address %s", hostname)
			else:
				session.proxies.update(
					{
						"http": proxy_url,
						"https": proxy_url,
					}
				)
				for key in ("http_proxy", "https_proxy"):
					if key in os.environ:
						del os.environ[key]
			no_proxy_list = no_proxy_addresses

		os.environ["no_proxy"] = ",".join(set(no_proxy_list))
	else:
		# Do not use a proxy
		logger.debug("Not using a proxy")
		os.environ["no_proxy"] = "*"

	logger.info(
		"Using proxy settings: http_proxy=%r, https_proxy=%r, no_proxy=%r",
		proxy_url if proxy_url and proxy_url.lower() != "system" else os.environ.get("http_proxy"),
		proxy_url if proxy_url and proxy_url.lower() != "system" else os.environ.get("https_proxy"),
		os.environ.get("no_proxy"),
	)
	return session
