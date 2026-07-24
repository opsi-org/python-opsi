# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.process._process import (
	CaptureOutputMode,
	DecodingErrors,
	DiscardOutputMode,
	InterpreterType,
	Process,
	ProcessError,
	disable_file_system_redirection,
	get_process_io_encoding,
	get_subprocess_environment,
	run_command,
	run_script,
	run_script_file,
)

__all__ = [
	"Process",
	"ProcessError",
	"run_command",
	"run_script",
	"run_script_file",
	"disable_file_system_redirection",
	"get_subprocess_environment",
	"get_process_io_encoding",
	"InterpreterType",
	"CaptureOutputMode",
	"DiscardOutputMode",
	"DecodingErrors",
]

from opsi.system.info import is_windows

if is_windows():
	from opsi.process._windows import ProcessIntegrityLevel, get_process_integrity_level  # noqa F401

	__all__.extend(["ProcessIntegrityLevel", "get_process_integrity_level"])
