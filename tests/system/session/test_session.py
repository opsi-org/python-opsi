# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import pytest

from opsi.system.info import is_linux, is_windows
from opsi.system.session import get_console_session, get_display_sessions


@pytest.mark.parametrize("one_session_per_user", [True, False])
def test_get_display_sessions(one_session_per_user: bool) -> None:
	sessions = get_display_sessions(one_session_per_user=one_session_per_user)
	assert isinstance(sessions, list)
	if not sessions and is_linux():
		pytest.skip("No display sessions found, might be running in a headless Linux environment")

	assert sessions
	users = set()
	for session in sessions:
		assert session.id
		assert session.desktop
		assert session.user

		if is_windows():
			assert session.windows_state is not None
			assert session.windows_protocol is not None

		if one_session_per_user:
			assert session.user not in users
		users.add(session.user)


def test_get_console_session() -> None:
	session = get_console_session()
	if not session and is_linux():
		pytest.skip("No console session found, might be running in a headless Linux environment")

	assert session
	assert session.id
	assert session.desktop
	assert session.user

	if is_windows():
		assert session.windows_state is not None
		assert session.windows_protocol is not None
