from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows

if is_linux():
	from ._linux import set_system_datetime
elif is_windows():
	from ._windows import set_system_datetime
elif is_macos():
	from ._macos import set_system_datetime
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = ["set_system_datetime"]
