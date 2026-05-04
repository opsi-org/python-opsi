from dataclasses import dataclass


@dataclass
class DisplaySession:
	id: int
	desktop: str
	user: str
	win_state: str | None = None
