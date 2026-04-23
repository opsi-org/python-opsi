from opsi.logging import get_logger
import psutil
from ._common import DesktopSession

logger = get_logger("opsi")


def get_sessions(protocol: str | None = None, user: str | None = None, limit_to_one_per_user: bool = True) -> list[DesktopSession]:
	sessions: list[DesktopSession] = []
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			session_class = env.get("XDG_SESSION_CLASS")
			if env.get("USER") and env.get("DISPLAY") and session_class:
				if env.get("DISPLAY") == ":1024":
					continue  # never try to use :1024 session as it seems to break gdm!
				if user and env.get("USER") != user:
					continue
				if not any((session.id == int(env["DISPLAY"][1:]) for session in sessions)):
					sessions.append(DesktopSession(id=int(env["DISPLAY"][1:]), desktop=session_class, user=env["USER"]))
		except (psutil.AccessDenied, psutil.NoSuchProcess) as err:
			logger.debug(err)
	logger.devel(sessions)
	if limit_to_one_per_user:
		relevant_users = [user] if user else list({entry.user for entry in sessions})
		relevant_sessions: list[DesktopSession] = []
		for single_user in relevant_users:
			relevant_sessions.append(
				min([user_session for user_session in sessions if user_session.user == single_user], key=lambda x: x.id)
			)
		sessions = relevant_sessions
	logger.devel(sessions)
	return sessions

