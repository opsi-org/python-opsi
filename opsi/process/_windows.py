# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "win32":
	raise OperatingSystemUnsupportedError("This module is only supported on Windows")

import _winapi
from typing import Any

import ntsecuritycon
import psutil
import win32api
import win32con
import win32process
import win32profile
import win32security
import win32ts

from opsi.logging import get_logger

logger = get_logger("opsi")


def _get_process(process_name: str, session_id: int | str) -> psutil.Process | None:
	logger.debug("Looking for process '%s' in session %r", process_name, session_id)
	process_name = process_name.lower()
	session_id = int(session_id)
	for proc in psutil.process_iter():
		try:
			if proc.name() == process_name and win32ts.ProcessIdToSessionId(proc.pid) == session_id:
				return proc
		except (psutil.AccessDenied, psutil.NoSuchProcess):
			pass
	return None


def _get_process_user_token(process_id: int, duplicate: bool = False) -> int:
	logger.debug("Getting user token for process %d", process_id)
	proc_handle = win32api.OpenProcess(win32con.MAXIMUM_ALLOWED, False, process_id)
	proc_token = win32security.OpenProcessToken(proc_handle, win32con.MAXIMUM_ALLOWED)
	if not duplicate:
		return proc_token
	return win32security.DuplicateTokenEx(
		ExistingToken=proc_token,
		# To request the same access rights as the existing token, specify zero.
		DesiredAccess=0,
		# https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-security_impersonation_level
		# SecurityDelegation: The server process can impersonate the client's security context on remote systems.
		ImpersonationLevel=win32security.SecurityDelegation,
		# The new token is a primary token that you can use in the CreateProcessAsUser function.
		TokenType=ntsecuritycon.TokenPrimary,
	)


CreateProcessOrig = _winapi.CreateProcess


def CreateProcess(
	__application_name: str | None,
	__command_line: str | None,
	__proc_attrs: Any,
	__thread_attrs: Any,
	__inherit_handles: bool,
	__creation_flags: int,
	__env_mapping: dict[str, str],
	__current_directory: str | None,
	__startup_info: Any,
) -> tuple[int, int, int, int]:
	if not __env_mapping or not __env_mapping.get("_opsi_process_session_id"):
		logger.trace("No session information in environment, using original CreateProcess")
		return CreateProcessOrig(
			__application_name,
			__command_line,
			__proc_attrs,
			__thread_attrs,
			__inherit_handles,
			__creation_flags,
			__env_mapping,
			__current_directory,
			__startup_info,
		)

	session_id = int(__env_mapping.pop("_opsi_process_session_id"))
	session_elevated = bool(int(__env_mapping.pop("_opsi_process_session_elevated", "0")))
	session_desktop = __env_mapping.pop("_opsi_process_session_desktop", "")
	process_name = "winlogon.exe" if session_elevated else "explorer.exe"

	logger.info("Creating process in session %d (elevated: %s, desktop: %r)", session_id, session_elevated, session_desktop)
	proc = _get_process(process_name=process_name, session_id=session_id)
	if not proc:
		raise RuntimeError(f"Failed to find '{process_name}' in session {session_id}")

	user_token = _get_process_user_token(proc.pid, duplicate=True)
	startup_info = win32process.STARTUPINFO()
	for attr, val in __startup_info.__dict__.items():
		if attr != "lpAttributeList" and val is not None:
			setattr(startup_info, attr, val)

	if session_desktop:
		startup_info.lpDesktop = session_desktop

	env = win32profile.CreateEnvironmentBlock(user_token, False)
	env.update(__env_mapping)

	(process_handle, thread_handle, process_id, thread_id) = win32process.CreateProcessAsUser(
		user_token,
		__application_name,
		__command_line,
		__proc_attrs,
		__thread_attrs,
		__inherit_handles,
		__creation_flags,
		env,
		__current_directory,
		startup_info,
	)
	# TODO: Call Detach() on the handles?
	return (process_handle, thread_handle, process_id, thread_id)


def patch_create_process() -> None:
	_winapi.CreateProcess = CreateProcess
