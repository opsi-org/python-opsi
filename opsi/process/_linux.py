# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "linux":
	raise OperatingSystemUnsupportedError("This module is only supported on Linux")

from opsi.system.session import LinuxDisplaySessionType, get_display_sessions


def prepare_sudo_in_session(
	session_id: str, command: list[str], env: dict[str, str], *, full_user_env: bool = False
) -> tuple[list[str], dict[str, str], str]:
	sessions = [s for s in get_display_sessions() if s.id == session_id]
	if not sessions:
		raise RuntimeError(f"Session {session_id!r} not found")

	session = sessions[0]
	if not session.user:
		raise RuntimeError(f"Session {session_id!r} has no user")

	for key in list(session.environment) if full_user_env else ["HOME", "USER", "LANG"]:
		val = session.environment.get(key)
		if key not in ("PATH", "LD_PRELOAD") and val is not None:
			env[key] = val

	if session.linux_session_type == LinuxDisplaySessionType.X11:
		assert session.environment.get("DISPLAY") and session.environment.get("XAUTHORITY")
		env["DISPLAY"] = session.environment["DISPLAY"]
		env["XAUTHORITY"] = session.environment["XAUTHORITY"]
	elif session.linux_session_type == LinuxDisplaySessionType.WAYLAND:
		assert session.environment.get("WAYLAND_DISPLAY") and session.environment.get("XDG_RUNTIME_DIR")
		env["WAYLAND_DISPLAY"] = session.environment["WAYLAND_DISPLAY"]
		env["XDG_RUNTIME_DIR"] = session.environment["XDG_RUNTIME_DIR"]
		if session.environment.get("DISPLAY"):
			env["DISPLAY"] = session.environment["DISPLAY"]

	# sudo-rs does not support -E
	sudo_command = ["sudo", "-n", "-u", session.user]
	for key in sorted(env):
		sudo_command.append(f"{key}={env[key]}")
	sudo_command += ["--"] + command
	return sudo_command, env, session.user
