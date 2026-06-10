# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys
from pathlib import Path

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "win32":
	raise OperatingSystemUnsupportedError("This module is only supported on Windows")

import ctypes
import re
from ctypes import wintypes

import win32net
import win32netcon
import win32wnet
from cryptography import x509

from opsi.logging import get_logger, secret_filter
from opsi.system.certificate_store import install_ca

DRIVE_LETTER_REGEX = re.compile(r"^[a-zA-Z]:$")

logger = get_logger("opsi")

netapi32 = ctypes.WinDLL("Netapi32.dll")

# Constants
MAX_PREFERRED_LENGTH = 0xFFFFFFFF
ERROR_MORE_DATA = 234
USE_DISKDEV = 0


# USE_INFO_0 structure (simplest level)
class USE_INFO_0(ctypes.Structure):
	_fields_ = [
		("ui0_local", wintypes.LPWSTR),
		("ui0_remote", wintypes.LPWSTR),
	]


# Function prototype
NetUseEnum = netapi32.NetUseEnum
NetUseEnum.argtypes = [
	wintypes.LPWSTR,  # servername (None = local machine)
	wintypes.DWORD,  # level
	ctypes.POINTER(ctypes.c_void_p),  # bufptr
	wintypes.DWORD,  # prefmaxlen
	ctypes.POINTER(wintypes.DWORD),  # entriesread
	ctypes.POINTER(wintypes.DWORD),  # totalentries
	ctypes.POINTER(wintypes.DWORD),  # resume_handle
]
NetUseEnum.restype = wintypes.DWORD

NetApiBufferFree = netapi32.NetApiBufferFree
NetApiBufferFree.argtypes = [ctypes.c_void_p]
NetApiBufferFree.restype = wintypes.DWORD


def _normalize_drive(mount_point: Path | str | None) -> str:
	"""Return a normalized Windows drive-letter mount point."""
	mount_point = str(mount_point).lower()
	if not DRIVE_LETTER_REGEX.match(mount_point):
		raise ValueError("Mount point must be a drive letter followed by a colon (e.g., 'z:')")
	return mount_point


def _get_mount(device: str | None = None, mount_point: Path | str | None = None) -> tuple[str, Path] | None:
	"""Check if a device is mounted on Windows and return the device and mount point."""

	if not device and not mount_point:
		raise ValueError("Either device or mount_point must be provided")
	if mount_point:
		mount_point = _normalize_drive(mount_point)

	dev_or_mountpoint = (device or str(mount_point)).lower()

	if mount := _get_mount_from_net_use(dev_or_mountpoint):
		return mount
	return _get_mount_from_wnet_connection(dev_or_mountpoint, mount_point)


def _get_mount_from_net_use(dev_or_mountpoint: str) -> tuple[str, Path] | None:
	"""Return a mount reported by the Windows NetUse API."""

	bufptr = ctypes.c_void_p()
	entries_read = wintypes.DWORD()
	total_entries = wintypes.DWORD()
	resume_handle = wintypes.DWORD(0)

	status = NetUseEnum(
		None,
		0,  # USE_INFO_0
		ctypes.byref(bufptr),
		MAX_PREFERRED_LENGTH,
		ctypes.byref(entries_read),
		ctypes.byref(total_entries),
		ctypes.byref(resume_handle),
	)

	if status != 0 and status != ERROR_MORE_DATA:
		raise ctypes.WinError(status)
	if not entries_read.value or not bufptr:
		return None

	try:
		array_type = USE_INFO_0 * entries_read.value
		entries = ctypes.cast(bufptr, ctypes.POINTER(array_type)).contents

		for i in range(entries_read.value):
			logger.debug("Found mount: local='%s', remote='%s'", entries[i].ui0_local, entries[i].ui0_remote)
			if dev_or_mountpoint in (entries[i].ui0_remote.lower(), entries[i].ui0_local.lower()):
				return entries[i].ui0_remote, Path(entries[i].ui0_local)
	finally:
		if bufptr:
			NetApiBufferFree(bufptr)

	return None


def _get_mount_from_wnet_connection(dev_or_mountpoint: str, mount_point: str | None = None) -> tuple[str, Path] | None:
	"""Return a mount reported by the Windows WNet API."""
	mount_points = (mount_point,) if mount_point else (f"{chr(drive)}:" for drive in range(ord("a"), ord("z") + 1))
	for local_mount_point in mount_points:
		try:
			remote = win32wnet.WNetGetConnection(local_mount_point)
		except Exception:
			continue
		logger.debug("Found WNet mount: local='%s', remote='%s'", local_mount_point, remote)
		if dev_or_mountpoint in (remote.lower(), local_mount_point.lower()):
			return remote, Path(local_mount_point)
	return None


def mount_cifs_share(
	*,
	address: str,
	share: str,
	mount_point: Path | str,
	username: str,
	password: str,
	read_only: bool = False,
	dir_mode: int | None = None,
	file_mode: int | None = None,
) -> None:
	"""Mount a CIFS share on Windows."""
	secret_filter.add_secrets(password)
	remote = f"\\\\{address}\\{share}"
	mount_point = _normalize_drive(mount_point)
	domain = None
	if "\\" in username:
		username = re.sub(r"\\+", r"\\", username)
		(domain, username) = username.split("\\", 1)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	logger.info("Mounting CIFS share '%s' to '%s' with username '%s'", remote, mount_point, username)
	use_info = {
		"remote": remote,
		"local": mount_point,
		"password": password,
		"username": username,
		"asg_type": USE_DISKDEV,
	}
	if domain:
		use_info["domainname"] = domain

	# Using NetUseAdd instead of WNetAddConnection2 to avoid Windows falling back to WebDAV
	# https://www.synacktiv.com/publications/taking-the-relaying-capabilities-of-multicast-poisoning-to-the-next-level-tricking
	win32net.NetUseAdd(None, 2, use_info)


def mount_webdav_share(
	*,
	address: str,
	port: int,
	path: str,
	mount_point: Path | str,
	username: str,
	password: str,
	read_only: bool = False,
	dir_mode: int | None = None,
	file_mode: int | None = None,
	ca_certs: list[x509.Certificate] | None = None,
) -> None:
	secret_filter.add_secrets(password)
	remote = f"https://{address}:{port}/{path.lstrip('/')}"
	mount_point = _normalize_drive(mount_point)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	if ca_certs:
		for ca_cert in ca_certs:
			install_ca(ca_cert)

	logger.info("Mounting WebDAV share '%s' to '%s' with username '%s'", remote, mount_point, username)
	# HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebClient\Parameters FileSizeLimitInBytes = 0xffffffff
	# HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains\<fqdn>@SSL@4447 file = 1
	win32wnet.WNetAddConnection2(win32netcon.RESOURCETYPE_DISK, mount_point, remote, None, username, password, 0)


def unmount_network_share(mount_point: Path | str | None) -> None:
	"""Unmount a network share mount point on Windows."""
	mount_point = _normalize_drive(mount_point)

	logger.info("Unmounting mount point '%s'", mount_point)

	if not _get_mount(mount_point=mount_point):
		logger.info("Mount point '%s' is not mounted, skipping unmount", mount_point)
		return

	win32net.NetUseDel(None, mount_point, getattr(win32netcon, "USE_LOTS_OF_FORCE", 2))
