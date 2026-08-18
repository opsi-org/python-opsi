# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import enum
import locale
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from functools import lru_cache
from getpass import getuser
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, PIPE, STDOUT, Popen, list2cmdline
from threading import Event, Lock, Thread
from types import TracebackType
from typing import Literal, Self

from opsi.logging import LOG_TRACE, get_logger, is_log_level_enabled
from opsi.retry import Retry, RetryConfig, RetryConfigType, get_retry_config
from opsi.system.file.temp import TempFile
from opsi.system.info import is_linux, is_windows
from opsi.util.pattern import MappedStrEnum

LD_LIBRARY_EXCLUDE_LIST = ["/usr/lib/opsiclientd", "/usr/lib/opsiconfd", "/usr/lib/opsi-agent"]

logger = get_logger("opsi")


class CaptureOutputMode(MappedStrEnum):
	STDOUT = "stdout"
	STDERR = "stderr"
	BOTH = "both"
	COMBINED = "combined"
	NONE = "none"

	_NAME = enum.nonmember("output capture mode")


class DiscardOutputMode(MappedStrEnum):
	STDOUT = "stdout"
	STDERR = "stderr"
	BOTH = "both"
	NONE = "none"

	_NAME = enum.nonmember("output discard mode")


class InterpreterType(MappedStrEnum):
	CMD = "cmd"
	POWERSHELL = "powershell"
	BASH = "bash"

	_NAME = enum.nonmember("interpreter type")


class DecodingErrors(MappedStrEnum):
	STRICT = "strict"
	IGNORE = "ignore"
	REPLACE = "replace"

	_NAME = enum.nonmember("decoding error handling mode")


def get_subprocess_environment(env: Mapping[str, str] | None = None) -> dict[str, str]:
	if env is None:
		env = os.environ.copy()
	else:
		env = dict(env)
	logger.trace("Original environment: %s", env)

	remove_vars = ["OPENSSL_MODULES"]
	if getattr(sys, "frozen", False):
		# Running in pyinstaller / frozen

		if is_linux():
			# https://www.pyinstaller.org/en/stable/common-issues-and-pitfalls.html#linux-and-unix-like-oses
			ldlp_orig = env.get("LD_LIBRARY_PATH_ORIG")
			if ldlp_orig is not None:
				logger.debug("Restoring LD_LIBRARY_PATH to '%s' in env for subprocess", ldlp_orig)
				env["LD_LIBRARY_PATH"] = ldlp_orig
			else:
				logger.debug("Removing LD_LIBRARY_PATH from env for subprocess")
				env.pop("LD_LIBRARY_PATH", None)

		remove_vars.extend(
			[
				"_PYI_APPLICATION_HOME_DIR",
				"_PYI_ARCHIVE_FILE",
				"_PYI_PARENT_PROCESS_LEVEL",
				"_PYI_LINUX_PROCESS_NAME",
				"_PYI_SPLASH_IPC",
				"_MEIPASS2",
			]
		)

	env = {k: v for k, v in env.items() if k not in remove_vars}

	path = env.get("PATH")
	if path:
		# Cleanup PATH variable. Remove empty values and values containing "pywin32_system32" and "opsi".
		# Otherwise, these values can end up in the user environment PATH in Windows registry.
		values = list(dict.fromkeys(v for v in path.split(os.pathsep) if v and not ("pywin32_system32" in v and "opsi" in v)))
		env["PATH"] = os.pathsep.join(values)

	logger.trace("Environment for subprocess: %s", env)
	return env


class ProcessError(Exception):
	"""Raised when a process execution fails."""

	max_output_length = 1000

	def __init__(self, message: str, *, process: Process) -> None:
		super().__init__(message)
		self.process = process

	def __str__(self) -> str:
		output = self.output
		ret = super().__str__()
		if self.command:
			ret += f"\nCommand: {self.command}"
		if self.exit_code is not None:
			ret += f"\nExit code: {self.exit_code}"
		if output:
			ret += "\nOutput:\n"
			ret += f"{'...' if len(output) > self.max_output_length else ''}{output[3 - self.max_output_length :]}"
		return ret

	@property
	def cause(self) -> BaseException | None:
		return self.__cause__ or self.__context__ or None

	@property
	def command_not_found(self) -> bool:
		return isinstance(self.cause, FileNotFoundError)

	@property
	def command(self) -> str:
		return self.process.get_command()

	@property
	def script(self) -> str | None:
		return self.process.get_script()

	@property
	def exit_code(self) -> int | None:
		return self.process.exit_code

	@property
	def output(self) -> str:
		return self.process.output


@contextmanager
def disable_file_system_redirection() -> Iterator[None]:
	"""
	Temporarily disable WOW64 file system redirection.

	In a 32-bit process on 64-bit Windows, access to ``C:\\Windows\\System32``
	is redirected to ``C:\\Windows\\SysWOW64``. This context manager disables
	the redirection and reverts it on exit. On other platforms it is a no-op.

	The redirection state is thread-local, so redirection must be disabled
	in the thread that actually performs the file system access.

	Yields
	------
	None

	Examples
	--------
	::

		with disable_file_system_redirection():
			data = Path(r"C:\\Windows\\System32\\drivers\\etc\\hosts").read_bytes()

	"""
	if os.name != "nt":
		yield
		return

	old_value = ctypes.c_long()
	success = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection(ctypes.byref(old_value))
	try:
		yield
	finally:
		if success:
			ctypes.windll.kernel32.Wow64RevertWow64FsRedirection(old_value)


@lru_cache
def get_process_io_encoding(interpreter: InterpreterType | None = None) -> str:
	encoding = ""
	if is_windows() and interpreter in (InterpreterType.CMD, None):
		# Windows suggests cp1252 even if using something else like cp850
		try:
			output = subprocess.check_output("chcp", shell=True).decode("ascii", errors="replace")
			match = re.search(r": (\d+)", output)
			if match:
				codepage = int(match.group(1))
				encoding = f"cp{codepage}"
		except Exception as exc:
			logger.info("Failed to determine codepage: %s", exc)
	if not encoding:
		try:
			encoding = locale.getpreferredencoding(False)
		except Exception as exc:
			logger.info("Failed to get preferred encoding: %s", exc)
	if not encoding:
		encoding = "utf-8"
	if interpreter:
		logger.info("Using encoding %r for process I/O with interpreter '%s'", encoding, interpreter)
	else:
		logger.info("Using encoding %r for process I/O", encoding)
	return encoding


def _get_interpreter_command(
	interpreter: InterpreterType,
	*,
	script_file: str | os.PathLike[str] | TempFile = "-",
	arguments: list[str] | None = None,
	hide_window: bool = False,
) -> list[str]:
	script_file = (
		str(script_file.path) if isinstance(script_file, TempFile) else os.fspath(script_file)
	)  # os.fspath handles both str and os.PathLike
	if is_windows():
		system_root = Path(os.environ.get("SystemRoot") or r"c:\Windows")

		if interpreter == InterpreterType.CMD:
			if script_file == "-" and arguments:
				raise ValueError("Cannot use arguments with piped cmd.exe script input")

			if script_file != "-":
				if not script_file.endswith((".cmd", ".bat")):
					raise ValueError(f"cmd.exe interpreter requires script file with .cmd or .bat extension, got: {script_file}")

				args = [script_file]
				if arguments:
					args.extend(arguments)
				logger.debug("Using shell command %r (%%ComSpec%%)", args)
				return args

			# /q: no echo, /d: disable auto-run, /k: run command and do not exit
			# /k Is used to prevent the copyright header and disable echo
			args = ["cmd.exe", "/q", "/d", "/k", "@echo off"]
			if arguments:
				args.extend(arguments)

			if comspec := os.environ.get("ComSpec"):
				shell_path = Path(comspec)
				if not shell_path.is_absolute():
					logger.warning("%%ComSpec%% is not an absolute path: '%s'", comspec)
				elif not shell_path.is_file():
					logger.warning("%%ComSpec%% does not point to a file: '%s'", comspec)
				else:
					args[0] = str(shell_path)
					logger.debug("Using shell command %r (%%ComSpec%%)", args)
					return args

			shell_path = system_root / "System32" / "cmd.exe"
			if shell_path.is_file():
				args[0] = str(shell_path)
				logger.debug("Using shell command %r", args)
				return args

			raise FileNotFoundError("cmd.exe not found")

		elif interpreter == InterpreterType.POWERSHELL:
			if script_file == "-" and arguments:
				raise ValueError("Cannot use arguments with piped PowerShell script input")

			args = [
				"powershell.exe",
				"-NoLogo",
				"-NonInteractive",
				"-NoProfile",
			]
			if hide_window:
				args.extend(["-WindowStyle", "Hidden"])
			args.extend(["-ExecutionPolicy", "Bypass", "-File", script_file])
			if arguments:
				args.extend(arguments)

			for name in "powershell.exe", "pwsh.exe":
				if path := which(name):
					shell_path = Path(path)
					if shell_path.is_file():
						args[0] = str(shell_path)
						logger.debug("Using shell command %r", args)
						return args
					logger.warning("Found %r in PATH but it is not a file: '%s'", name, shell_path)

			logger.warning("PowerShell executable not found in PATH")
			shell_path = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
			if shell_path.is_file():
				args[0] = str(shell_path)
				logger.debug("Using shell command %r", args)
				return args
			raise FileNotFoundError("PowerShell executable not found")

	path = which(str(interpreter))
	if path:
		args = [path]
		if script_file == "-":
			args.extend(["-s", "--"])
		else:
			args.extend([script_file])
		if arguments:
			args.extend(arguments)
		logger.debug("Using interpreter command %r", args)
		return args

	raise FileNotFoundError(f"Interpreter not found: {interpreter}")


class Process:
	"""
	Run an external process.
	"""

	_stdout_limit = 5_000_000
	_stderr_limit = 5_000_000
	_read_max = 100_000
	_start_wait_timeout = 10
	_pipe_script = False

	def __init__(
		self,
		*,
		command: Collection[str] | str | None = None,
		script: str | Collection[str] | Path | None = None,
		interpreter: InterpreterType | str | Path | Collection[str] | None = None,
		arguments: Collection[str | int | float] | None = None,
		working_dir: str | os.PathLike[str] | None = None,
		environment: Mapping[str, str] | None = None,
		timeout: float | None = None,
		stdin: str | bytes | None = None,
		close_stdin: bool = True,
		capture_output: CaptureOutputMode | str = CaptureOutputMode.BOTH,
		discard_output: DiscardOutputMode | str = DiscardOutputMode.NONE,
		encoding: str | None = None,
		exit_on_error: bool = False,
		success_exit_codes: Collection[int] | None = (0,),
		hide_window: bool = False,
		detach: bool = False,
		session_id: str | None = None,
		session_desktop: str | None = None,
		session_elevated: bool = False,
		retry_config: RetryConfig | None = None,
	) -> None:
		"""
		Initialize a new Process instance.

		Supports two mutually exclusive modes:
		- **Command mode**: Run a command directly (provide ``command``).
		- **Script mode**: Run a script via an interpreter (provide ``script``).

		:param command:
			Command to execute directly, provided as a list of argument strings or a single string.
			Mutually exclusive with ``script``.
		:param script:
			A script to execute via an interpreter. Can be a string containing the script body,
			or a Path to a script file.
			Mutually exclusive with ``command``.
		:param interpreter:
			The interpreter to use for running a script. Only valid with ``script``.
			Can be a well-known interpreter name: ``"cmd"``, ``"powershell"``, ``"bash"``.
			None selects the interpreter based on the script file extension (if script is a Path) or defaults to the OS shell (if script is a string).
			Can also be a list of strings for a custom interpreter command, e.g. ``["uv", "run", "python"]``
			It is also possible to pass a command name as string or Path.
		:param arguments:
			Optional list of arguments to pass to the script or command.
		:param working_dir:
			Working directory for the process.
			If None, uses the current directory.
		:param environment:
			Environment variables for the process. If None, inherits the current environment.
		:param timeout:
			Maximum execution time in seconds.
			If exceeded, the process is killed and a ProcessError is raised.
			If None, no timeout is enforced.
		:param stdin:
			Initial data to send to the process's standard input, as a string or bytes.
		:param close_stdin:
			If True, close stdin after writing initial data.
			If False, stdin remains open for further writes via write_text() or write_bytes().
		:param capture_output:
			Specifies which output streams to capture.
			Options are "stdout", "stderr", "both", "combined", or "none".
		:param discard_output:
			Specifies which output streams to redirect to DEVNULL.
			Options are "stdout", "stderr", "both", or "none".
			If an output stream is both captured and discarded, it will be discarded.
		:param encoding:
			Character encoding for stdin/stdout/stderr.
			If None, the system's preferred encoding is used.
		:param success_exit_codes:
			List of exit codes that indicate successful execution.
			If the process exits with a code outside this set, a ProcessError is raised.
			If None, all exit codes are treated as successful.
		:param exit_on_error:
			Only valid with script execution and interpreter bash or powershell.
			If True the script will exit on the first error.
			If False the script will continue execution even if some commands fail.
		:param hide_window:
			If True, hide the process window on Windows.
		:param detach:
			If True, start the process detached from the current process session.
		:param session_id:
			If specified the process will be started in the given session.
		:param session_desktop:
			If specified (Windows only), the process will be started with the given desktop (e.g. "WinSta0\\Default").
		:param session_elevated:
			If True and session_id is specified, the process will be started elevated in the given session.
		:param retry_config:
			Configuration for automatic retry behavior on failure.
			If None, uses the default retry configuration for process execution.
			The default configuration does not retry on TimeoutError.
			Pass NoRetry to disable retries.
		"""

		self._command: list[str] = []
		self._script: str | None = None
		self._interpreter: InterpreterType | Collection[str] | None = None
		self._temp_script_file: TempFile | None = None
		self._script_file: Path | None = None
		self._exit_on_error = bool(exit_on_error)
		self._working_dir = Path(working_dir) if working_dir else None
		self._timeout = float(timeout) if timeout is not None and timeout > 0 else None
		self._hide_window = bool(hide_window)
		self._detach = bool(detach)
		self._environment: dict[str, str] | None = None
		self._session_id: str | None = None
		self._session_desktop: str | None = None
		self._session_elevated: bool = False
		self._encoding = encoding or "utf-8"
		self._stdin_data: bytes | None = None
		self._close_stdin_after_start = bool(close_stdin)
		self._success_exit_codes = None if success_exit_codes is None else set(success_exit_codes)
		self._retry_config = retry_config or get_retry_config(RetryConfigType.RUN_PROCESS)
		self._proc: Popen | None = None
		self._attempts = 0
		self._should_stop = False
		self._wait_after_stop: float | int | None = 5
		self._started = Event()
		self._ended = Event()
		self._data_lock = Lock()
		self._manager_thread: Thread | None = None
		self._stdout_reader: Thread | None = None
		self._stderr_reader: Thread | None = None

		self._reset_state()

		if command is not None and script is not None:
			raise ProcessError("'command' and 'script' are mutually exclusive", process=self)
		if command is None and script is None:
			raise ProcessError("Either 'command' or 'script' must be provided", process=self)
		if command is not None and interpreter is not None:
			raise ProcessError("'interpreter' can only be used with 'script', not with 'command'", process=self)

		try:
			self._capture_output = CaptureOutputMode(capture_output)
			self._discard_output = DiscardOutputMode(discard_output)
		except ValueError as exc:
			raise ProcessError(str(exc), process=self) from exc

		if session_id is not None:
			if not is_windows() and not is_linux():
				raise ProcessError("Parameter 'session_id' is only supported on Windows and Linux", process=self)
			self._session_id = str(session_id)

			if session_desktop:
				if not is_windows():
					raise ProcessError("Parameter 'session_desktop' is only supported on Windows", process=self)
				session_desktop = str(session_desktop)
				if r"\\" not in session_desktop:
					session_desktop = f"WinSta0\\{session_desktop}"
				if session_desktop.split("\\")[-1].lower() not in ("default", "winlogon", "screensaver"):
					raise ValueError(f"Invalid desktop '{session_desktop}'")
				self._session_desktop = session_desktop

			self._session_elevated = bool(session_elevated)
			if self._session_elevated and not (is_windows() or is_linux()):
				raise ProcessError("Parameter 'session_elevated' is only supported on Windows and Linux", process=self)
		else:
			if session_desktop is not None:
				raise ProcessError("Parameter 'session_desktop' requires 'session_id' to be set", process=self)
			if session_elevated:
				raise ProcessError("Parameter 'session_elevated' requires 'session_id' to be set", process=self)

		self._environment = dict(environment) if environment else None

		arguments = [str(arg) for arg in arguments] if arguments else []
		# Build command
		if command:
			# Direct command execution
			self._command = shlex.split(command) if isinstance(command, str) else list(command)
			if arguments:
				self._command.extend(arguments)
		else:
			# Script execution
			if not interpreter:
				if isinstance(script, Path):
					extension = str(script).lower().rsplit(".", 1)[-1]
					if extension in ("cmd", "bat"):
						interpreter = InterpreterType.CMD
					elif extension in ("ps1",):
						interpreter = InterpreterType.POWERSHELL
					elif extension in ("sh",):
						interpreter = InterpreterType.BASH
					else:
						interpreter = InterpreterType.CMD if is_windows() else InterpreterType.BASH
						logger.info("Cannot auto-detect interpreter for file extension '.%s', defaulting to %r", extension, interpreter)
				else:
					interpreter = InterpreterType.CMD if is_windows() else InterpreterType.BASH
			elif isinstance(interpreter, InterpreterType):
				pass
			elif isinstance(interpreter, (str, Path)):
				try:
					interpreter = InterpreterType(interpreter)
				except ValueError:
					# Not a known interpreter type, treat as custom command
					interpreter = [str(interpreter)]
			else:
				interpreter: list[str] = [str(part) for part in interpreter]
			self._interpreter = interpreter

			if self._exit_on_error and interpreter not in (InterpreterType.BASH, InterpreterType.POWERSHELL):
				raise ProcessError("'exit_on_error' can only be used with 'bash' or 'powershell' interpreter", process=self)

			if not encoding:
				self._encoding = get_process_io_encoding(interpreter=interpreter if isinstance(interpreter, InterpreterType) else None)
				logger.debug("Using auto-detected encoding for process I/O: %r", self._encoding)

			if isinstance(script, Path):
				self._script_file = script
			else:
				assert isinstance(script, Collection)
				if isinstance(script, str):
					self._script = script
				else:
					self._script = os.linesep.join(script) + os.linesep

				if not self._script:
					raise ProcessError("Script content cannot be empty", process=self)

			if self._pipe_script:
				if stdin:
					raise ProcessError("Cannot use stdin with piped script execution", process=self)
			else:
				extension = ""
				if self._script_file:
					extension = self._script_file.suffix.lstrip(".")
				if not extension:
					if interpreter == InterpreterType.CMD:
						extension = "cmd"
					elif interpreter == InterpreterType.POWERSHELL:
						extension = "ps1"
					elif interpreter == InterpreterType.BASH:
						extension = "sh"
				if not extension:
					extension = "tmp"
				self._temp_script_file = TempFile(encoding=self._encoding, extension=extension)

			if isinstance(interpreter, InterpreterType):
				try:
					self._command = _get_interpreter_command(
						interpreter=interpreter,
						script_file=str(self._temp_script_file.path) if self._temp_script_file else "-",
						arguments=arguments or None,
						hide_window=self._hide_window,
					)
				except Exception as exc:
					raise ProcessError(f"Failed to get interpreter command for interpreter '{interpreter}': {exc}", process=self) from exc
			else:
				self._command = list(interpreter)
				if self._temp_script_file:
					self._command.append(str(self._temp_script_file))
				if arguments:
					self._command.extend(arguments)

		if isinstance(stdin, bytes):
			self._stdin_data = stdin
		elif isinstance(stdin, str):
			self._stdin_data = stdin.encode(self._encoding)

	def _reset_state(self) -> None:
		"""
		Reset the internal state for a new process run attempt.
		"""
		self._exception: Exception | None = None
		self._pid = None
		self._exit_code: int | None = None
		self._start_time = 0.0
		self._end_time = 0.0
		self._started.clear()
		self._ended.clear()
		self.timed_out = False

		self._stdin_closed = False

		self._stdout_data = bytearray()
		self._stdout_bytes_read = 0
		self._stdout_bytes_written = 0
		self._stdout_read_position = 0

		self._stderr_data = bytearray()
		self._stderr_bytes_read = 0
		self._stderr_bytes_written = 0
		self._stderr_read_position = 0

	def _reader(self, type: Literal["stdout", "stderr"]) -> None:
		"""
		Read from the process's stdout or stderr and store the data in memory.
		:param type: Whether to read from stdout or stderr.
		"""
		assert self._proc
		pipe = self._proc.stdout if type == "stdout" else self._proc.stderr
		assert pipe
		try:
			is_overflow = False
			data = b""
			data_len = 0
			while True:
				if is_overflow:
					if self._end_time:
						break
				else:
					data = pipe.readline(self._read_max)
					data_len = len(data)
					if not data_len:
						total_bytes_read = self._stdout_bytes_read if type == "stdout" else self._stderr_bytes_read
						logger.trace("End of %s stream reached, read %d bytes in total", type, total_bytes_read)
						# EOF
						break
					logger.trace("Read %d bytes from %s: %r", data_len, type, data)

				with self._data_lock:
					if type == "stdout":
						avail_size = self._stdout_limit - len(self._stdout_data)
					else:
						avail_size = self._stderr_limit - len(self._stderr_data)

					remaining_data = b""
					if avail_size >= data_len:
						is_overflow = False
					elif avail_size > 0:
						logger.trace("Buffer '%s' is almost full, only %d bytes available", type, avail_size)
						remaining_data = data[avail_size:]
						data = data[:avail_size]
						data_len = len(data)
					else:
						if not is_overflow:
							is_overflow = True
							logger.warning("Buffer '%s' is full", type)

					if not is_overflow:
						if type == "stdout":
							self._stdout_bytes_read += data_len
							self._stdout_data.extend(data)
						else:
							self._stderr_bytes_read += data_len
							self._stderr_data.extend(data)

						if remaining_data:
							data = remaining_data
							data_len = len(data)

				time.sleep(0.1 if is_overflow else 0.001 if not data_len else 0.0)
		except Exception as exc:
			logger.warning("Exception in %s reader thread: %r", type, exc)

		try:
			pipe.close()
		except Exception as exc:
			logger.debug("Failed to close %s pipe: %r", type, exc)

	def _prepare_script(self):
		if not self._script and not self._script_file:
			return

		script = self._script or ""
		if self._script_file:
			# TODO: Retry
			script = self._script_file.read_text(encoding=self._encoding)

		script_lines = script.splitlines()
		assert script_lines
		if self._interpreter == InterpreterType.CMD and not script_lines[0].startswith("@echo "):
			script_lines.insert(0, "@echo off")
		if self._exit_on_error:
			if self._interpreter == InterpreterType.BASH:
				script_lines.insert(0, "set -e")
			elif self._interpreter == InterpreterType.POWERSHELL:
				script_lines.insert(0, '$ErrorActionPreference = "Stop"')

		self._script = os.linesep.join(script_lines) + os.linesep
		if self._temp_script_file:
			self._temp_script_file.create(content=self._script, encoding=self._encoding)

	def _manager(self) -> None:
		"""
		Run the process with retries according to the retry configuration.
		"""
		try:
			self._prepare_script()
			for attempt in Retry(self._retry_config):
				with attempt:
					self._attempts += 1
					self._run_attempt()
		except Exception as exc:
			self._exception = exc
		finally:
			if self._temp_script_file:
				self._temp_script_file.delete()
			self._started.set()
			self._ended.set()

	def _run_attempt(self) -> None:
		"""
		Run a single attempt to execute the process.
		"""
		self._reset_state()
		logger.debug("Running process attempt %d", self._attempts)

		env = get_subprocess_environment(self._environment)
		startupinfo = None
		creationflags = 0
		start_new_session = False
		if os.name == "nt":
			if self._hide_window:
				from subprocess import STARTF_USESHOWWINDOW, STARTUPINFO, SW_HIDE

				startupinfo = STARTUPINFO()
				startupinfo.dwFlags |= STARTF_USESHOWWINDOW
				startupinfo.wShowWindow = SW_HIDE
			if self._detach:
				from subprocess import CREATE_NEW_PROCESS_GROUP, DETACHED_PROCESS

				creationflags |= DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

			if self._session_id is not None:
				from opsi.process._windows import patch_create_process

				patch_create_process()

				env["_opsi_process_session_id"] = self._session_id
				env["_opsi_process_session_elevated"] = str(int(bool(self._session_elevated)))
				if self._session_desktop:
					env["_opsi_process_session_desktop"] = str(self._session_desktop)
		else:
			if self._detach:
				start_new_session = True
			if is_linux() and self._session_id is not None:
				from opsi.process._linux import prepare_run_in_session

				if self._session_elevated and os.geteuid() != 0:
					raise ProcessError("Cannot start elevated process in session on Linux when not running as root", process=self)

				command, env, user = prepare_run_in_session(
					session_id=self._session_id,
					command=self._command,
					env=env,
					as_session_user=not self._session_elevated,
					full_user_env=False,
				)
				if self._attempts == 1:
					self._command = command
					if self._temp_script_file and user != getuser():
						self._temp_script_file.path.chmod(0o755)

		self._start_time = time.monotonic()

		stdin_data = self._stdin_data
		close_stdin = self._close_stdin_after_start
		if self._pipe_script:
			logger.debug("Using piped script input for shell execution")
			close_stdin = True
			assert self._script
			stdin_data = self._script.encode(self._encoding)

		stdout = (
			DEVNULL
			if self._discard_output in (DiscardOutputMode.STDOUT, DiscardOutputMode.BOTH)
			else PIPE
			if self._capture_output in (CaptureOutputMode.STDOUT, CaptureOutputMode.BOTH, CaptureOutputMode.COMBINED)
			else None
		)
		stderr = (
			DEVNULL
			if self._discard_output in (DiscardOutputMode.STDERR, DiscardOutputMode.BOTH)
			else PIPE
			if self._capture_output in (CaptureOutputMode.STDERR, CaptureOutputMode.BOTH)
			else STDOUT
			if self._capture_output == CaptureOutputMode.COMBINED
			else None
		)
		stdin = PIPE if stdin_data is not None or not close_stdin else None

		logger.notice(
			"Starting process with command: %r, working_dir: '%s', stdout: %r, stderr: %r, stdin: %r",
			self._command,
			self._working_dir,
			stdout,
			stderr,
			stdin,
		)
		with disable_file_system_redirection():
			self._proc = Popen(
				self._command,
				stdout=stdout,
				stderr=stderr,
				stdin=stdin,
				cwd=self._working_dir,
				env=env,
				startupinfo=startupinfo,
				creationflags=creationflags,
				start_new_session=start_new_session,
			)
		self._pid = self._proc.pid
		logger.info("Started process %r with PID %d on attempt %d", self.get_command(), self._pid, self._attempts)
		assert self._proc
		try:
			logger.debug("Starting stdout reader thread")
			if stdout == PIPE:
				self._stdout_reader = Thread(target=self._reader, args=("stdout",), daemon=True)
				self._stdout_reader.start()

			if stderr == PIPE:
				logger.debug("Starting stderr reader thread")
				self._stderr_reader = Thread(target=self._reader, args=("stderr",), daemon=True)
				self._stderr_reader.start()

			if stdin_data:
				logger.debug("Writing initial stdin data to process")
				assert self._proc.stdin
				self._proc.stdin.write(stdin_data)
				if close_stdin:
					logger.debug("Closing stdin after writing initial data")
					self._close_stdin()

			self._started.set()

			while True:
				if self._should_stop:
					logger.debug("Stop requested, stopping process")
					self._stop()
					return

				exit_code = self._proc.poll()
				if exit_code is not None:
					self._exit_code = exit_code
					if self._success_exit_codes and self._exit_code is not None and self._exit_code not in self._success_exit_codes:
						raise ProcessError(f"Process exited with code {self._exit_code}", process=self)
					logger.info("Process %r with PID %d exited with code %d", self.get_command(), self._pid, self._exit_code)
					return

				if self._timeout is not None:
					elapsed_time = time.monotonic() - self._start_time
					if elapsed_time >= self._timeout:
						self.timed_out = True
						logger.debug("Process timed out after %.2f seconds, stopping process", elapsed_time)
						self._stop()
						# Raise a TimeoutError which can be handled separately from other ProcessErrors by the retry logic.
						# _raise_exception() will raise a ProcessError from the original exception.
						raise TimeoutError(f"Process timed out after {elapsed_time:.2f} seconds")
				time.sleep(0.1)
		finally:
			self._end_time = time.monotonic()
			self._close_stdin()
			if self._stdout_reader and self._stdout_reader.is_alive():
				self._stdout_reader.join(timeout=5)
			if self._stderr_reader and self._stderr_reader.is_alive():
				self._stderr_reader.join(timeout=5)

	def _stop(self) -> None:
		"""
		Stop the process by sending a signal if it is still running.
		"""
		self._close_stdin()
		if self._proc and self._exit_code is None:
			signals = [(signal.SIGTERM, 0.75), (signal.SIGKILL, 0.25)] if os.name != "nt" else [(signal.SIGTERM, 1.0)]
			# On Windows, SIGTERM is an alias for terminate() which calls TerminateProcess() to stop the child.
			for idx, (signum, wait_fraction) in enumerate(signals):
				signame = signal.Signals(signum).name
				wait = None
				if self._wait_after_stop is None:
					if idx < len(signals) - 1:
						wait = 5
				else:
					wait = self._wait_after_stop * wait_fraction

				logger.info(
					"Sending signal %s to process with PID %d and waiting %s for process to end",
					signame,
					self._pid,
					f"{wait} seconds" if wait else "indefinitely",
				)
				self._proc.send_signal(signum)
				try:
					self._exit_code = self._proc.wait(timeout=wait)
					break
				except subprocess.TimeoutExpired:
					logger.info(
						"Process %r with PID %d did not stop within %r seconds after sending signal %s",
						self.get_command(),
						self._pid,
						wait,
						signame,
					)
			if self._exit_code is None:
				logger.warning("Failed to stop process with PID %d", self._pid)

	def __enter__(self) -> Self:
		"""
		Enter the context, start the process and return the Process instance.

		:return: The Process instance.
		"""
		return self.start()

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, wait for the process to finish and raise any exceptions that occurred during execution.
		"""
		self.wait()
		self._raise_exception()

	def _start_manager(self) -> None:
		"""
		Start the manager thread to run the process with retries.
		"""
		self._manager_thread = Thread(target=self._manager, daemon=True)
		self._manager_thread.start()

	def start(self) -> Self:
		"""
		Start the process and return the Process instance.

		:return: The Process instance.
		"""
		logger.debug("Starting process")
		self._start_manager()
		self._started.wait(self._start_wait_timeout)
		return self

	def _raise_exception(self) -> None:
		if not self._exception:
			return
		if isinstance(self._exception, ProcessError):
			raise self._exception
		raise ProcessError(f"Failed to run process after {self._attempts} attempts: {self._exception}", process=self) from self._exception

	def _close_stdin(self) -> None:
		"""
		Close the process's standard input if it is open.
		"""
		if self._proc and self._proc.stdin and not self._stdin_closed:
			try:
				self._proc.stdin.close()
			except Exception as err:
				logger.debug("Failed to close process stdin: %r", err)
			self._stdin_closed = True

	@property
	def runtime(self) -> float:
		"""
		Get the runtime of the process in seconds.
		:return: Runtime in seconds, or 0 if the process has not started.
		"""
		if not self._start_time:
			return 0.0
		if not self._end_time:
			return time.monotonic() - self._start_time
		return self._end_time - self._start_time

	@property
	def pid(self) -> int | None:
		return self._pid

	@property
	def exit_code(self) -> int | None:
		"""
		Get the exit code of the process, or None if it is still running.
		:return: Exit code, or None if the process is still running.
		"""
		return self._exit_code

	@property
	def output(self) -> str:
		"""
		Get the combined standard output and standard error of the process as text.
		:return: Combined output as text.
		"""
		return self.get_output_text()

	def get_command(self) -> str:
		"""
		Get the command that was run as a string.
		:return: Command as a string.
		"""
		return list2cmdline(self._command)

	def get_script(self) -> str | None:
		"""
		Get the script that was executed when using shell execution, or None if not using shell execution.
		:return: Script as a string, or None if not using shell execution.
		"""
		return self._script

	def is_running(self, *, wait: float = 0.01) -> bool:
		"""
		Check if the process is still running and
		:param wait: Time to wait for the process to end before checking, in seconds.
		:return: True if the process is still running, False if it has ended.
		"""
		return not self._ended.wait(timeout=wait)

	def stop(self, *, wait_before_stop: float | None = None, wait_after_stop: float | None = 5) -> bool:
		"""
		Stop the process by sending a signal if it is still running.
		:param wait_before_stop: Time to wait for the process to end before sending a stop signal, in seconds. If None, stop immediately.
		:param wait_after_stop: Time to wait after sending the stop signal, in seconds.
		:return: True if the process is still running, False if it has ended.
		"""
		logger.info("Stopping process with PID %r, wait_before_stop: %r, wait_after_stop: %r", self._pid, wait_before_stop, wait_after_stop)
		if wait_before_stop is not None and self.wait(timeout=wait_before_stop):
			return False

		self._wait_after_stop = wait_after_stop
		self._should_stop = True
		# Wait a little longer than wait_after_stop to ensure _should_stop is fully processed
		self.wait(timeout=None if wait_after_stop is None else wait_after_stop + 0.5)
		return self.is_running(wait=0)

	def wait(self, *, timeout: float | None = None) -> bool:
		"""
		Wait for the process to finish.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:return: True if the process finished, False if the timeout was reached.
		"""
		ended = self._ended.wait(timeout=timeout)
		if ended and self._manager_thread:
			self._manager_thread.join(timeout=3)
		return ended

	def write_bytes(self, data: bytes, close: bool = False) -> None:
		"""
		Write bytes to the process's standard input.
		:param data: Data to write as bytes.
		:param close: Whether to close the standard input after writing.
		"""
		if not self._started.wait(self._start_wait_timeout) or not self._proc or not self._proc.stdin or self._stdin_closed:
			raise RuntimeError("Process is not running or stdin is closed")

		if is_log_level_enabled(logger, LOG_TRACE):
			logger.trace("Writing %d bytes to process stdin: %r", len(data), data)
		self._proc.stdin.write(data)
		self._proc.stdin.flush()
		if close:
			logger.debug("Closing stdin after writing data")
			self._close_stdin()

	def write_text(self, data: str, close: bool = False) -> None:
		"""
		Write text to the process's standard input.
		:param data: Data to write as text.
		:param close: Whether to close the standard input after writing.
		"""
		self.write_bytes(data.encode(self._encoding), close=close)

	def get_stdout_bytes(self) -> bytes:
		"""
		Get the standard output of the process as bytes.
		:return: Standard output as bytes.
		"""
		return bytes(self._stdout_data)

	def get_stdout_text(self, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> str:
		"""
		Get the standard output of the process as text.
		:param errors: How to handle decoding errors.
		:return: Standard output as text.
		"""
		return self.get_stdout_bytes().decode(self._encoding, errors=DecodingErrors(errors).value)

	def get_stdout_lines(self, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> list[str]:
		"""
		Get the standard output of the process as a list of lines.
		:param errors: How to handle decoding errors.
		:return: Standard output as a list of lines.
		"""
		stdout_text = self.get_stdout_text(errors=DecodingErrors(errors).value)
		return stdout_text.splitlines()

	def get_stderr_bytes(self) -> bytes:
		"""
		Get the standard error of the process as bytes.
		:return: Standard error as bytes.
		"""
		return bytes(self._stderr_data)

	def get_stderr_text(self, *, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> str:
		"""
		Get the standard error of the process as text.
		:param errors: How to handle decoding errors.
		:return: Standard error as text.
		"""
		return self.get_stderr_bytes().decode(self._encoding, errors=DecodingErrors(errors).value)

	def get_stderr_lines(self, *, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> list[str]:
		"""
		Get the standard error of the process as a list of lines.
		:param errors: How to handle decoding errors.
		:return: Standard error as a list of lines.
		"""
		stderr_text = self.get_stderr_text(errors=DecodingErrors(errors).value)
		return stderr_text.splitlines()

	def get_output_bytes(self) -> bytes:
		"""
		Get the combined standard output and standard error of the process as bytes.
		:return: Combined output as bytes.
		"""
		return bytes(self._stdout_data) + bytes(self._stderr_data)

	def get_output_text(self, *, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> str:
		"""
		Get the combined standard output and standard error of the process as text.
		:param errors: How to handle decoding errors.
		:return: Combined output as text.
		"""
		return self.get_output_bytes().decode(self._encoding, errors=DecodingErrors(errors).value)

	def get_output_lines(self, *, errors: DecodingErrors | str = DecodingErrors.REPLACE) -> list[str]:
		"""
		Get the combined standard output and standard error of the process as a list of lines.
		:param errors: How to handle decoding errors.
		:return: Combined output as a list of lines.
		"""
		output_text = self.get_output_text(errors=DecodingErrors(errors).value)
		return output_text.splitlines()

	def read_bytes(
		self, *, timeout: float | None = None, truncate: bool = True, stdout: bool = True, stderr: bool = True
	) -> tuple[bytes, bytes]:
		"""
		Read new data from the process's standard output and standard error since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:param stdout: Whether to read from standard output.
		:param stderr: Whether to read from standard error.
		:return: A tuple containing the new standard output and standard error as bytes.
		"""
		start_time: int | float = time.monotonic()
		if not stdout and not stderr:
			return b"", b""

		while (
			self._exit_code is None
			and (not stdout or self._stdout_bytes_read == self._stdout_bytes_written)
			and (not stderr or self._stderr_bytes_read == self._stderr_bytes_written)
		):
			if timeout is not None:
				elapsed_time = time.monotonic() - start_time
				if elapsed_time >= timeout:
					logger.trace("Read from process timed out after %r seconds", timeout)
					return b"", b""
			time.sleep(0.1)

		if self._exit_code is not None:
			# If the process has ended, ensure all reader threads have finished to capture any remaining output
			if self._stdout_reader and self._stdout_reader.is_alive():
				self._stdout_reader.join(timeout=5)
			if self._stderr_reader and self._stderr_reader.is_alive():
				self._stderr_reader.join(timeout=5)

		stdout_data, stderr_data = b"", b""
		with self._data_lock:
			if stdout:
				stdout_data = bytes(self._stdout_data[self._stdout_read_position :])
				if stdout_data:
					data_len = len(stdout_data)
					self._stdout_read_position += data_len
					self._stdout_bytes_written += data_len
					if truncate:
						del self._stdout_data[: self._stdout_read_position]
						self._stdout_read_position = 0
			if stderr:
				stderr_data = bytes(self._stderr_data[self._stderr_read_position :])
				if stderr_data:
					data_len = len(stderr_data)
					self._stderr_read_position += data_len
					self._stderr_bytes_written += data_len
					if truncate:
						del self._stderr_data[: self._stderr_read_position]
						self._stderr_read_position = 0

		return stdout_data, stderr_data

	def read_stdout_bytes(self, *, timeout: float | None = None, truncate: bool = True) -> bytes:
		"""
		Read new data from the process's standard output since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:return: New standard output data as bytes.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=True, stderr=False)[0]

	def read_stderr_bytes(self, *, timeout: float | None = None, truncate: bool = True) -> bytes:
		"""
		Read new data from the process's standard error since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:return: New standard error data as bytes.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=False, stderr=True)[1]

	def read_text(
		self,
		*,
		timeout: float | None = None,
		errors: DecodingErrors | str = DecodingErrors.REPLACE,
		truncate: bool = True,
	) -> tuple[str, str]:
		"""
		Read new data from the process's standard output and standard error since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: A tuple containing the new standard output and standard error as text.
		"""
		stdout_bytes, stderr_bytes = self.read_bytes(timeout=timeout, truncate=truncate)
		return stdout_bytes.decode(self._encoding, errors=DecodingErrors(errors).value), stderr_bytes.decode(
			self._encoding, errors=DecodingErrors(errors).value
		)

	def read_stdout_text(
		self,
		*,
		timeout: float | None = None,
		errors: DecodingErrors | str = DecodingErrors.REPLACE,
		truncate: bool = True,
	) -> str:
		"""
		Read new data from the process's standard output since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: New standard output data as text.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=True, stderr=False)[0].decode(
			self._encoding, errors=DecodingErrors(errors).value
		)

	def read_stderr_text(
		self,
		*,
		timeout: float | None = None,
		errors: DecodingErrors | str = DecodingErrors.REPLACE,
		truncate: bool = True,
	) -> str:
		"""
		Read new data from the process's standard error since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: New standard error data as text.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=False, stderr=True)[1].decode(
			self._encoding, errors=DecodingErrors(errors).value
		)


def run_command(
	command: Collection[str] | str | None = None,
	*,
	working_dir: str | os.PathLike[str] | None = None,
	environment: Mapping[str, str] | None = None,
	timeout: float | None = None,
	stdin: str | bytes | None = None,
	capture_output: CaptureOutputMode | str = CaptureOutputMode.BOTH,
	discard_output: DiscardOutputMode | str = DiscardOutputMode.NONE,
	encoding: str | None = None,
	success_exit_codes: Collection[int] | None = (0,),
	hide_window: bool = False,
	detach: bool = False,
	session_id: str | None = None,
	session_desktop: str | None = None,
	session_elevated: bool = False,
	wait: bool = True,
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a command directly and return the Process instance.
	"""
	proc = Process(
		command=command,
		working_dir=working_dir,
		environment=environment,
		timeout=timeout,
		stdin=stdin,
		capture_output=capture_output,
		discard_output=discard_output,
		encoding=encoding,
		success_exit_codes=success_exit_codes,
		hide_window=hide_window,
		detach=detach,
		session_id=session_id,
		session_desktop=session_desktop,
		session_elevated=session_elevated,
		retry_config=retry_config,
	)
	if wait:
		with proc:
			pass
	else:
		proc.start()
		proc._raise_exception()
	return proc


def run_script(
	script: str | Collection[str] | Path,
	*,
	interpreter: InterpreterType | Collection[str] | str | Path | None = None,
	arguments: Collection[str | int | float] | None = None,
	working_dir: str | os.PathLike[str] | None = None,
	environment: Mapping[str, str] | None = None,
	timeout: float | None = None,
	stdin: str | bytes | None = None,
	capture_output: CaptureOutputMode | str = CaptureOutputMode.BOTH,
	discard_output: DiscardOutputMode | str = DiscardOutputMode.NONE,
	encoding: str | None = None,
	exit_on_error: bool = False,
	success_exit_codes: Collection[int] | None = (0,),
	hide_window: bool = True,
	detach: bool = False,
	session_id: str | None = None,
	session_desktop: str | None = None,
	session_elevated: bool = False,
	wait: bool = True,
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a script via an interpreter and return the Process instance.
	"""
	proc = Process(
		script=script,
		interpreter=interpreter,
		arguments=arguments,
		working_dir=working_dir,
		environment=environment,
		timeout=timeout,
		stdin=stdin,
		capture_output=capture_output,
		discard_output=discard_output,
		encoding=encoding,
		exit_on_error=exit_on_error,
		success_exit_codes=success_exit_codes,
		hide_window=hide_window,
		detach=detach,
		session_id=session_id,
		session_desktop=session_desktop,
		session_elevated=session_elevated,
		retry_config=retry_config,
	)
	if wait:
		with proc:
			pass
	else:
		proc.start()
		proc._raise_exception()
	return proc


def run_script_file(
	script_file: str | os.PathLike[str],
	*,
	interpreter: InterpreterType | Collection[str] | str | Path | None = None,
	arguments: Collection[str | int | float] | None = None,
	working_dir: str | os.PathLike[str] | None = None,
	environment: Mapping[str, str] | None = None,
	timeout: float | None = None,
	stdin: str | bytes | None = None,
	capture_output: CaptureOutputMode | str = CaptureOutputMode.BOTH,
	discard_output: DiscardOutputMode | str = DiscardOutputMode.NONE,
	encoding: str | None = None,
	exit_on_error: bool = False,
	success_exit_codes: Collection[int] | None = (0,),
	hide_window: bool = True,
	detach: bool = False,
	session_id: str | None = None,
	session_desktop: str | None = None,
	session_elevated: bool = False,
	wait: bool = True,
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a script via an interpreter and return the Process instance.
	"""
	proc = Process(
		script=Path(script_file),
		interpreter=interpreter,
		arguments=arguments,
		working_dir=working_dir,
		environment=environment,
		timeout=timeout,
		stdin=stdin,
		capture_output=capture_output,
		discard_output=discard_output,
		encoding=encoding,
		exit_on_error=exit_on_error,
		hide_window=hide_window,
		detach=detach,
		session_id=session_id,
		session_desktop=session_desktop,
		session_elevated=session_elevated,
		success_exit_codes=success_exit_codes,
		retry_config=retry_config,
	)
	if wait:
		with proc:
			pass
	else:
		proc.start()
		proc._raise_exception()
	return proc
