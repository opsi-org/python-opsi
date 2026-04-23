from opsi.logging import get_logger

from ._common import DesktopSession

logger = get_logger("opsi")

def get_sessions(protocol: str | None = None, user: str | None = None) -> list[DesktopSession]:
	import win32ts  # ty: ignore[unresolved-import]

	WTS_PROTOCOLS = {
		"console": win32ts.WTS_PROTOCOL_TYPE_CONSOLE,
		"citrix": win32ts.WTS_PROTOCOL_TYPE_ICA,
		"rdp": win32ts.WTS_PROTOCOL_TYPE_RDP,
	}

	WTS_STATES = {
		win32ts.WTSActive: "active",
		win32ts.WTSDisconnected: "disconnected",
	}

	if protocol is not None:
		if protocol not in WTS_PROTOCOLS:
			logger.warning("Invalid session protocol '%s'", protocol)
			wts_protocol = None
		else:
			wts_protocol = WTS_PROTOCOLS[protocol]

	server = win32ts.WTS_CURRENT_SERVER_HANDLE
	sessions: list[DesktopSession] = []
	for session in win32ts.WTSEnumerateSessions(server):
		# WTS_CONNECTSTATE_CLASS:
		# WTSActive,WTSConnected,WTSConnectQuery,WTSShadow,WTSDisconnected,WTSIdle,WTSListen,WTSReset,WTSDown,WTSInit
		state = WTS_STATES.get(session.get("State"))
		if not state:
			continue
		session_id = int(session["SessionId"])
		session_user = win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSUserName)
		if not session_user or (user and session_user != user):
			continue
		if wts_protocol and wts_protocol != win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSClientProtocolType):
			continue
		sessions.append(
			DesktopSession(
				id=session_id,
				desktop=str(win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSWorkingDirectory)).lower() or "default",
				user=session_user or "",
				win_state=state,
			)
		)
	return sessions

