from opsi.system.info import is_linux
from opsi.system.session import get_sessions


def test_get_sessions() -> None:
	sessions = get_sessions()
	assert isinstance(sessions, list)
	print(sessions)
	if is_linux():
		return  # Might run in a headless environment, so we can't reliably test for sessions
	assert sessions
	assert sessions[0].id
	assert sessions[0].desktop
	assert sessions[0].user
