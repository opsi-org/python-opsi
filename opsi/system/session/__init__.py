import os
from opsi.system.info import is_linux, is_macos, is_windows
from ._common import DisplaySession

__all__ = ["get_display_sessions"]


def get_display_sessions(*, protocol: str | None = None, user: str | None = None) -> list[DisplaySession]:
	if is_windows():
		from ._windows import get_display_sessions as _get_display_sessions
	elif is_linux():
		from ._linux import get_display_sessions as _get_display_sessions
	elif is_macos():
		return [DisplaySession(id=1, desktop="default", user=os.getenv("USER") or "")]
	else:
		raise RuntimeError("Unsupported operating system")

	return _get_display_sessions(protocol=protocol, user=user)