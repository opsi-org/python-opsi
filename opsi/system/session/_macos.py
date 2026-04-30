import os

from ._common import DisplaySession


def get_display_sessions(protocol: str | None = None, user: str | None = None) -> list[DisplaySession]:
	return [DisplaySession(id=1, desktop="default", user=os.getenv("USER") or "")]
