import os
from opsi.system.info import is_linux, is_macos, is_windows
from ._common import DesktopSession

__all__ = ["get_sessions"]


def get_sessions(*, protocol: str | None = None, user: str | None = None) -> list[DesktopSession]:
	if is_windows():
		from ._windows import get_sessions as _get_sessions
	elif is_linux():
		from ._linux import get_sessions as _get_sessions
	elif is_macos():
		return [DesktopSession(id=1, desktop="default", user=os.getenv("USER") or "")]
	else:
		raise RuntimeError("Unsupported operating system")

	return _get_sessions(protocol=protocol, user=user)