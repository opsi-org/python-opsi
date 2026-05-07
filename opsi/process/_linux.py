# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "linux":
	raise OperatingSystemUnsupportedError("This module is only supported on Linux")

from getpass import getuser
from opsi.system.session import get_display_sessions


def prepare_run_in_session(
	*, session_id: str, command: list[str], env: dict[str, str], as_session_user: bool, full_user_env: bool = False
) -> tuple[list[str], dict[str, str], str]:
	user = getuser()
	sessions = [s for s in get_display_sessions() if s.id == session_id]
	if not sessions:
		raise RuntimeError(f"Session {session_id!r} not found")

	session = sessions[0]
	if as_session_user:
		if not session.user:
			raise RuntimeError(f"Session {session_id!r} has no user")

		user = session.user
		for key in list(session.environment) if full_user_env else ["HOME", "USER", "LANG"]:
			val = session.environment.get(key)
			if key not in ("PATH", "LD_PRELOAD") and val is not None:
				env[key] = val

	for key in ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
		if key in session.environment:
			env[key] = session.environment[key]

	if as_session_user:
		# sudo-rs does not support -E
		sudo_command = ["sudo", "-n", "-u", user]
		for key in sorted(env):
			sudo_command.append(f"{key}={env[key]}")
		sudo_command += ["--"] + command
		command = sudo_command

	return command, env, user
