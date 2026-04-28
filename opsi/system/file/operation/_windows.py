# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "win32":
	raise OperatingSystemUnsupportedError("This module is only supported on Windows")

import ctypes
from ctypes import wintypes
from pathlib import Path

FSCTL_SET_REPARSE_POINT = 0x000900A4
FSCTL_GET_REPARSE_POINT = 0x000900A8
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
IO_REPARSE_TAG_SYMLINK = 0xA000000C
MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

ERROR_FILE_NOT_FOUND = 2
ERROR_PATH_NOT_FOUND = 3
ERROR_NOT_A_REPARSE_POINT = 4390

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = (
	wintypes.LPCWSTR,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.LPVOID,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.HANDLE,
)
CreateFileW.restype = wintypes.HANDLE
DeviceIoControl = kernel32.DeviceIoControl
DeviceIoControl.argtypes = (
	wintypes.HANDLE,
	wintypes.DWORD,
	wintypes.LPVOID,
	wintypes.DWORD,
	wintypes.LPVOID,
	wintypes.DWORD,
	ctypes.POINTER(wintypes.DWORD),
	wintypes.LPVOID,
)
DeviceIoControl.restype = wintypes.BOOL
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = (wintypes.HANDLE,)
CloseHandle.restype = wintypes.BOOL


def create_junction(link_path: Path, target: Path) -> None:
	link_path = link_path.absolute()
	link_path.mkdir(parents=True, exist_ok=True)

	# Convert target to NT path
	target = target.absolute()
	nt_target = rf"\??\{target}"

	# Prepare buffer (UTF-16-LE)
	target_bytes = nt_target.encode("utf-16-le")
	substitute_name_offset = 0
	substitute_name_length = len(target_bytes)
	print_name_offset = substitute_name_length + 2
	print_name = str(target).encode("utf-16-le")
	print_name_length = len(print_name)

	# Build reparse buffer
	path_buffer = target_bytes + b"\x00\x00" + print_name + b"\x00\x00"

	reparse_data_length = 8 + len(path_buffer)

	class REPARSE_DATA_BUFFER(ctypes.Structure):
		_fields_ = [
			("ReparseTag", wintypes.DWORD),
			("ReparseDataLength", wintypes.WORD),
			("Reserved", wintypes.WORD),
			("SubstituteNameOffset", wintypes.WORD),
			("SubstituteNameLength", wintypes.WORD),
			("PrintNameOffset", wintypes.WORD),
			("PrintNameLength", wintypes.WORD),
			("PathBuffer", ctypes.c_byte * len(path_buffer)),
		]

	buffer = REPARSE_DATA_BUFFER()
	buffer.ReparseTag = IO_REPARSE_TAG_MOUNT_POINT
	buffer.ReparseDataLength = reparse_data_length
	buffer.Reserved = 0
	buffer.SubstituteNameOffset = substitute_name_offset
	buffer.SubstituteNameLength = substitute_name_length
	buffer.PrintNameOffset = print_name_offset
	buffer.PrintNameLength = print_name_length

	for i, b in enumerate(path_buffer):
		buffer.PathBuffer[i] = b

	# Open directory
	handle = CreateFileW(
		str(link_path),
		GENERIC_WRITE,
		0,
		None,
		OPEN_EXISTING,
		FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS,
		None,
	)

	if handle == INVALID_HANDLE_VALUE:
		raise ctypes.WinError(ctypes.get_last_error())

	# Apply reparse point
	bytes_returned = wintypes.DWORD()

	result = DeviceIoControl(
		handle,
		FSCTL_SET_REPARSE_POINT,
		ctypes.byref(buffer),
		ctypes.sizeof(buffer),
		None,
		0,
		ctypes.byref(bytes_returned),
		None,
	)

	CloseHandle(handle)

	if not result:
		raise ctypes.WinError(ctypes.get_last_error())


def get_link_target(link_path: Path | str) -> Path | None:
	"""
	Return the target path of a Windows junction or symbolic link.

	Parameters
	----------
	link_path : Path | str
		The path to inspect.

	Returns
	-------
	Path | None
		The link target if `link_path` is a junction or symbolic link, otherwise None.
	"""
	link_path = Path(link_path).absolute()
	handle = CreateFileW(
		str(link_path),
		GENERIC_READ,
		FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
		None,
		OPEN_EXISTING,
		FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS,
		None,
	)

	if handle == INVALID_HANDLE_VALUE:
		last_error = ctypes.get_last_error()
		if last_error in (ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND):
			return None
		raise ctypes.WinError(last_error)

	try:
		buffer = ctypes.create_string_buffer(MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
		bytes_returned = wintypes.DWORD()
		result = DeviceIoControl(
			handle,
			FSCTL_GET_REPARSE_POINT,
			None,
			0,
			buffer,
			ctypes.sizeof(buffer),
			ctypes.byref(bytes_returned),
			None,
		)
		if not result:
			last_error = ctypes.get_last_error()
			if last_error == ERROR_NOT_A_REPARSE_POINT:
				return None
			raise ctypes.WinError(last_error)

		reparse_data = buffer.raw[: bytes_returned.value]
		reparse_tag = int.from_bytes(reparse_data[0:4], "little")
		if reparse_tag == IO_REPARSE_TAG_MOUNT_POINT:
			path_buffer_offset = 16
		elif reparse_tag == IO_REPARSE_TAG_SYMLINK:
			path_buffer_offset = 20
		else:
			return None

		substitute_name_offset = int.from_bytes(reparse_data[8:10], "little")
		substitute_name_length = int.from_bytes(reparse_data[10:12], "little")
		print_name_offset = int.from_bytes(reparse_data[12:14], "little")
		print_name_length = int.from_bytes(reparse_data[14:16], "little")
		path_buffer = reparse_data[path_buffer_offset:]

		print_name = path_buffer[print_name_offset : print_name_offset + print_name_length].decode("utf-16-le")
		if print_name:
			return Path(print_name)

		substitute_name = path_buffer[substitute_name_offset : substitute_name_offset + substitute_name_length].decode("utf-16-le")
		if substitute_name.startswith("\\??\\UNC\\"):
			return Path("\\\\" + substitute_name[8:])
		if substitute_name.startswith("\\??\\"):
			return Path(substitute_name[4:])
		return Path(substitute_name)
	finally:
		CloseHandle(handle)
