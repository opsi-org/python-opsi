# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "win32":
	raise OperatingSystemUnsupportedError("This module is only supported on Windows")

import _winapi
import os
from enum import IntEnum, IntFlag
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


class ProcessCreationFlags(IntFlag):
	"""
	Process creation flags for CreateProcess.

	https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
	"""

	DEBUG_PROCESS = 0x00000001
	DEBUG_ONLY_THIS_PROCESS = 0x00000002
	CREATE_SUSPENDED = 0x00000004
	DETACHED_PROCESS = 0x00000008
	CREATE_NEW_CONSOLE = 0x00000010
	NORMAL_PRIORITY_CLASS = 0x00000020
	IDLE_PRIORITY_CLASS = 0x00000040
	HIGH_PRIORITY_CLASS = 0x00000080
	REALTIME_PRIORITY_CLASS = 0x00000100
	CREATE_NEW_PROCESS_GROUP = 0x00000200
	CREATE_UNICODE_ENVIRONMENT = 0x00000400
	CREATE_SEPARATE_WOW_VDM = 0x00000800
	CREATE_SHARED_WOW_VDM = 0x00001000
	CREATE_FORCEDOS = 0x00002000
	BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
	ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
	INHERIT_PARENT_AFFINITY = 0x00010000
	CREATE_PROTECTED_PROCESS = 0x00040000
	EXTENDED_STARTUPINFO_PRESENT = 0x00080000
	PROCESS_MODE_BACKGROUND_BEGIN = 0x00100000
	PROCESS_MODE_BACKGROUND_END = 0x00200000
	CREATE_SECURE_PROCESS = 0x00400000
	CREATE_BREAKAWAY_FROM_JOB = 0x01000000
	CREATE_PRESERVE_CODE_AUTHZ_LEVEL = 0x02000000
	CREATE_DEFAULT_ERROR_MODE = 0x04000000
	CREATE_NO_WINDOW = 0x08000000


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
	/,
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
	logger.debug("Process creation flags: %s", ProcessCreationFlags(__creation_flags).name)

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
	# Detach() detaches the Win32 handle from the handle object
	return (process_handle.Detach(), thread_handle.Detach(), process_id, thread_id)


def patch_create_process() -> None:
	_winapi.CreateProcess = CreateProcess


class ProcessIntegrityLevel(IntEnum):
	UNTRUSTED = 0x0
	LOW = 0x1000
	MEDIUM_LOW = 0x1100
	MEDIUM = 0x2000
	MEDIUM_PLUS = 0x2100
	HIGH = 0x3000
	SYSTEM = 0x4000
	PROTECTED_PROCESS = 0x5000
	SECURE_PROCESS = 0x7000

	@classmethod
	def from_sid(cls, sid: str) -> ProcessIntegrityLevel:
		rid = int(str(sid).split("-")[-1])
		return cls.from_int(rid)

	@classmethod
	def from_int(cls, value: int) -> ProcessIntegrityLevel:
		for sorted_member in sorted(ProcessIntegrityLevel, key=lambda m: m.value, reverse=True):
			if value >= sorted_member.value:
				return sorted_member
		return cls.UNTRUSTED


def get_process_integrity_level(pid: int | None = None) -> ProcessIntegrityLevel:
	"""
	Get the integrity level of a process.
	:param pid: Process ID. If None, the current process is used.
	:return: Integrity level of the process.
	"""
	if pid is None:
		pid = os.getpid()
	current_process = win32api.OpenProcess(win32con.MAXIMUM_ALLOWED, False, pid)
	current_process_token = win32security.OpenProcessToken(current_process, win32con.MAXIMUM_ALLOWED)
	sid, _ = win32security.GetTokenInformation(current_process_token, ntsecuritycon.TokenIntegrityLevel)
	return ProcessIntegrityLevel.from_sid(win32security.ConvertSidToStringSid(sid))
