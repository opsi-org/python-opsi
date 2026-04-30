from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import is_linux, is_macos, is_windows, get_system

if is_linux():
	from ._linux import get_display_sessions
elif is_macos():
	from ._macos import get_display_sessions
elif is_windows():
	from ._windows import get_display_sessions
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")

__all__ = ["get_display_sessions"]
