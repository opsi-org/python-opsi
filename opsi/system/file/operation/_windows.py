import sys

if sys.platform != "win32":
	raise OSError("This module is only supported on Windows")

import ctypes
from ctypes import wintypes
from pathlib import Path

FSCTL_SET_REPARSE_POINT = 0x000900A4
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003

GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

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

	if handle == wintypes.HANDLE(-1).value:
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
