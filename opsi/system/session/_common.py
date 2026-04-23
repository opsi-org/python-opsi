from dataclasses import dataclass

@dataclass
class DesktopSession:
	id: int
	desktop: str
	user: str
	win_state: str | None = None
