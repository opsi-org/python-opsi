# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import locale
import os
import re
import shlex
import subprocess
import time
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from pathlib import Path
from shutil import which
from subprocess import PIPE, STDOUT, Popen, list2cmdline
from threading import Event, Lock, Thread
from types import TracebackType
from typing import Collection, Literal, Self, cast

from opsi.exception import OpsiError
from opsi.file.temp import TempFile
from opsi.logging import get_logger
from opsi.retry import Retry, RetryConfig, get_retry_config
from opsi.system.info import is_windows

logger = get_logger()


class ProcessError(OpsiError):
	"""Raised when a process execution fails."""

	max_output_length = 1000

	def __init__(self, message: str, process: Process) -> None:
		super().__init__(message)
		self.process = process

	def __str__(self) -> str:
		output = self.output
		return (
			f"{super().__str__()}\n"
			f"Command: {self.command}\n"
			f"Exit code: {self.exit_code}\n"
			f"Output:\n"
			f"{'...' if len(output) > self.max_output_length else ''}{output[3 - self.max_output_length :]}"
		)

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
def _disable_file_system_redirection():
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


@lru_cache()
def _get_process_io_encoding(interpreter: Literal["cmd", "powershell", "bash"] | None = None) -> str:
	encoding = ""
	if is_windows() and interpreter == "cmd":
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
	logger.info("Using encoding %r for process I/O", encoding)
	return encoding


def _get_interpreter_command(
	interpreter: Literal["cmd", "powershell", "bash"], script_file: str | Path | TempFile = "-", arguments: list[str] | None = None
) -> list[str]:
	script_file = str(script_file.path) if isinstance(script_file, TempFile) else str(script_file)
	if is_windows():
		system_root = Path(os.environ.get("SystemRoot") or r"c:\Windows")

		if interpreter == "cmd":
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

		elif interpreter == "powershell":
			if script_file == "-" and arguments:
				raise ValueError("Cannot use arguments with piped PowerShell script input")

			args = ["powershell.exe", "-NoLogo", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_file]
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

	path = which(interpreter)
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
		interpreter: Literal["cmd", "powershell", "bash"] | Collection[str] | str | None = None,
		arguments: Collection[str | int | float] | None = None,
		working_dir: Path | str | None = None,
		timeout: float | int | None = None,
		stdin: str | bytes | None = None,
		close_stdin: bool = True,
		capture_output: Literal["stdout", "stderr", "both", "combined", "none"] = "combined",
		encoding: str | None = None,
		success_exit_codes: Collection[int] | None = (0,),
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
			Can also be a list of strings for a custom interpreter command, e.g. ``["uv", "run", "python"]``.
		:param arguments:
			Optional list of arguments to pass to the script or command.
		:param working_dir:
			Working directory for the process.
			If None, uses the current directory.
		:param timeout:
			Maximum execution time in seconds.
			If exceeded, the process is killed and a TimeoutError is raised.
			If None, no timeout is enforced.
		:param stdin:
			Initial data to send to the process's standard input, as a string or bytes.
		:param close_stdin:
			If True, close stdin after writing initial data.
			If False, stdin remains open for further writes via write_text() or write_bytes().
		:param capture_output:
			Specifies which output streams to capture.
			Options are "stdout", "stderr", "both", "combined", or "none".
		:param encoding:
			Character encoding for stdin/stdout/stderr.
			If None, the system's preferred encoding is used.
		:param success_exit_codes:
			List of exit codes that indicate successful execution.
			If the process exits with a code outside this set, a ProcessError is raised.
			If None, all exit codes are treated as successful.
		:param retry_config:
			Configuration for automatic retry behavior on failure.
			If None, uses the default retry configuration for process execution.
			The default configuration does not retry on TimeoutError.
			Pass NoRetry to disable retries.
		"""
		if command is not None and script is not None:
			raise ValueError("'command' and 'script' are mutually exclusive")
		if command is None and script is None:
			raise ValueError("Either 'command' or 'script' must be provided")
		if command is not None:
			if interpreter is not None:
				raise ValueError("'interpreter' can only be used with 'script', not with 'command'")

		self._command: list[str] = []
		self._script: str | None = None
		self._working_dir = Path(working_dir) if working_dir else None
		self._timeout = timeout
		arguments = [str(arg) for arg in arguments] if arguments else []
		if capture_output not in ("stdout", "stderr", "both", "combined", "none"):
			raise ValueError(f"Invalid capture_output value: {capture_output}")
		self._capture_output = capture_output

		# Build command
		self._script_file: TempFile | Path | None = None
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
						interpreter = "cmd"
					elif extension in ("ps1",):
						interpreter = "powershell"
					elif extension in ("sh",):
						interpreter = "bash"
					else:
						raise ValueError(f"Cannot auto-detect interpreter for file extension '.{extension}'")
				else:
					interpreter = "cmd" if is_windows() else "bash"
			elif interpreter in ("cmd", "powershell", "bash"):
				pass
			elif not isinstance(interpreter, list):
				interpreter = [str(interpreter)]

			if not encoding:
				encoding = _get_process_io_encoding(interpreter=interpreter if interpreter in ("cmd", "powershell", "bash") else None)

			if isinstance(script, Path):
				self._script_file = script
			else:
				assert isinstance(script, (str, Collection))
				script_lines = script.splitlines() if isinstance(script, str) else list(script)
				script_text = os.linesep.join(script_lines) + os.linesep
				if interpreter == "cmd" and not script_text.startswith("@echo "):
					script_text = "@echo off" + os.linesep + script_text
				self._script = script_text

			if self._pipe_script:
				if stdin:
					raise ValueError("Cannot use stdin with piped script execution")
			elif not self._script_file:
				extension = "tmp"
				if interpreter == "cmd":
					extension = "cmd"
				elif interpreter == "powershell":
					extension = "ps1"
				elif interpreter == "bash":
					extension = "sh"
				self._script_file = TempFile(
					content=self._script,
					encoding=encoding,
					extension=extension,
				)
			if interpreter in ("cmd", "powershell", "bash"):
				self._command = _get_interpreter_command(
					cast(Literal["cmd", "powershell", "bash"], interpreter),
					script_file=self._script_file if self._script_file and not self._pipe_script else "-",
					arguments=arguments or None,
				)
			else:
				self._command = list(interpreter)
				if self._script_file:
					self._command.append(str(self._script_file))
				if arguments:
					self._command.extend(arguments)

		self._encoding = encoding or "utf-8"
		self._stdin_data: bytes | None = None
		self._close_stdin_after_start = bool(close_stdin)
		if isinstance(stdin, bytes):
			self._stdin_data = stdin
		elif isinstance(stdin, str):
			self._stdin_data = stdin.encode(self._encoding)

		self._success_exit_codes = None if success_exit_codes is None else set(success_exit_codes)
		self._retry_config = retry_config or get_retry_config("run_process")
		self._proc: Popen | None = None
		self._should_stop = False
		self._data_lock = Lock()
		self._started = Event()
		self._ended = Event()
		self._attempts = 0
		self._manager_thread: Thread | None = None
		self._stdout_reader: Thread | None = None
		self._stderr_reader: Thread | None = None

		self._reset_state()

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
						logger.debug("Buffer '%s' is almost full, only %d bytes available", type, avail_size)
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

				time.sleep(0.1 if is_overflow else 0.01)
		except Exception as exc:
			logger.warning("Exception in %s reader thread: %r", type, exc)

		try:
			pipe.close()
		except Exception as exc:
			logger.debug("Failed to close %s pipe: %r", type, exc)

	def _manager(self) -> None:
		"""
		Run the process with retries according to the retry configuration.
		"""
		try:
			with self._script_file if isinstance(self._script_file, TempFile) else nullcontext():
				for attempt in Retry(self._retry_config):
					with attempt:
						self._attempts += 1
						self._run_attempt()
		except Exception as exc:
			self._exception = exc
		finally:
			self._started.set()
			self._ended.set()

	def _run_attempt(self) -> None:
		"""
		Run a single attempt to execute the process.
		"""
		self._reset_state()
		logger.debug("Running process attempt %d: %r", self._attempts, self._command)

		startupinfo = None
		if os.name == "nt":
			from subprocess import STARTF_USESHOWWINDOW, STARTUPINFO, SW_HIDE

			startupinfo = STARTUPINFO()
			startupinfo.dwFlags |= STARTF_USESHOWWINDOW
			startupinfo.wShowWindow = SW_HIDE

		self._start_time = time.monotonic()

		stdin_data = self._stdin_data
		close_stdin = self._close_stdin_after_start
		if self._pipe_script:
			logger.debug("Using piped script input for shell execution")
			close_stdin = True
			if self._script:
				stdin_data = self._script.encode(self._encoding)
			elif isinstance(self._script_file, Path):
				stdin_data = self._script_file.read_bytes() + os.linesep.encode(self._encoding)
			else:
				raise ValueError("No script content available for piped input")

		stdout = PIPE if self._capture_output in ("stdout", "both", "combined") else None
		stderr = PIPE if self._capture_output in ("stderr", "both") else STDOUT if self._capture_output == "combined" else None
		stdin = PIPE if stdin_data is not None or not close_stdin else None

		logger.info(
			"Starting process with command: %r, working_dir: %r, stdout: %r, stderr: %r, stdin: %r",
			self._command,
			self._working_dir,
			stdout,
			stderr,
			stdin,
		)
		with _disable_file_system_redirection():
			self._proc = Popen(
				self._command,
				stdout=stdout,
				stderr=stderr,
				stdin=stdin,
				cwd=self._working_dir,
				startupinfo=startupinfo,
			)
		self._pid = self._proc.pid
		logger.notice("Started process %r with PID %d (attempt %d)", self.get_command(), self._pid, self._attempts)
		assert self._proc
		try:
			logger.debug("Starting stdout reader thread")
			if self._capture_output in ("stdout", "both", "combined"):
				self._stdout_reader = Thread(target=self._reader, args=("stdout",), daemon=True)
				self._stdout_reader.start()

			if self._capture_output in ("stderr", "both"):
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
					self._stop()
					return

				exit_code = self._proc.poll()
				if exit_code is not None:
					self._exit_code = exit_code
					if self._success_exit_codes and self._exit_code is not None and self._exit_code not in self._success_exit_codes:
						raise ProcessError(f"Process exited with code {self._exit_code}", self)
					return

				if self._timeout is not None:
					elapsed_time = time.monotonic() - self._start_time
					if elapsed_time >= self._timeout:
						self.timed_out = True
						self._stop()
						raise TimeoutError(f"Process timed out after {elapsed_time:.2f} seconds")
				time.sleep(0.1)
		finally:
			self._end_time = time.monotonic()
			self._close_stdin()
			if self._stdout_reader and self._stdout_reader.is_alive():
				self._stdout_reader.join(timeout=3)
			if self._stderr_reader and self._stderr_reader.is_alive():
				self._stderr_reader.join(timeout=3)

	def _stop(self) -> None:
		"""
		Stop the process by killing it if it is still running.
		"""
		self._close_stdin()
		if self._proc and not self._exit_code:
			self._proc.kill()
			self._exit_code = self._proc.wait(timeout=3)

	def __enter__(self) -> Self:
		"""
		Enter the context, start the process and return the Process instance.

		:return: The Process instance.
		"""
		self._start_manager()
		self._started.wait(self._start_wait_timeout)
		return self

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, wait for the process to finish and raise any exceptions that occurred during execution.
		"""
		self.wait()
		if self._exception:
			if isinstance(self._exception, ProcessError):
				raise self._exception
			else:
				raise ProcessError(f"Failed to run process after {self._attempts} attempts: {self._exception}", self)

	def _start_manager(self) -> None:
		"""
		Start the manager thread to run the process with retries.
		"""
		self._manager_thread = Thread(target=self._manager, daemon=True)
		self._manager_thread.start()

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

	def is_running(self, *, wait: float | int = 0.01) -> bool:
		"""
		Check if the process is still running.
		:param wait: Time to wait for the process to end before checking, in seconds.
		:return: True if the process is still running, False if it has ended.
		"""
		return not self._ended.wait(timeout=wait)

	def stop(self) -> None:
		"""
		Stop the process by killing it if it is still running.
		"""
		self._should_stop = True
		self.wait()

	def wait(self, *, timeout: float | int | None = None) -> bool:
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

		self._proc.stdin.write(data)
		if close:
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

	def get_stdout_text(self, errors: Literal["ignore", "replace", "strict"] = "replace") -> str:
		"""
		Get the standard output of the process as text.
		:param errors: How to handle decoding errors.
		:return: Standard output as text.
		"""
		return self.get_stdout_bytes().decode(self._encoding, errors=errors)

	def get_stderr_bytes(self) -> bytes:
		"""
		Get the standard error of the process as bytes.
		:return: Standard error as bytes.
		"""
		return bytes(self._stderr_data)

	def get_stderr_text(self, *, errors: Literal["ignore", "replace", "strict"] = "replace") -> str:
		"""
		Get the standard error of the process as text.
		:param errors: How to handle decoding errors.
		:return: Standard error as text.
		"""
		return self.get_stderr_bytes().decode(self._encoding, errors=errors)

	def get_output_bytes(self) -> bytes:
		"""
		Get the combined standard output and standard error of the process as bytes.
		:return: Combined output as bytes.
		"""
		return bytes(self._stdout_data) + bytes(self._stderr_data)

	def get_output_text(self, *, errors: Literal["ignore", "replace", "strict"] = "replace") -> str:
		"""
		Get the combined standard output and standard error of the process as text.
		:param errors: How to handle decoding errors.
		:return: Combined output as text.
		"""
		return self.get_output_bytes().decode(self._encoding, errors=errors)

	def get_output_lines(self, *, errors: Literal["ignore", "replace", "strict"] = "replace") -> list[str]:
		"""
		Get the combined standard output and standard error of the process as a list of lines.
		:param errors: How to handle decoding errors.
		:return: Combined output as a list of lines.
		"""
		output_text = self.get_output_text(errors=errors)
		return output_text.splitlines()

	def read_bytes(
		self, *, timeout: float | int | None = None, truncate: bool = True, stdout: bool = True, stderr: bool = True
	) -> tuple[bytes, bytes]:
		"""
		Read new data from the process's standard output and standard error since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:param stdout: Whether to read from standard output.
		:param stderr: Whether to read from standard error.
		:return: A tuple containing the new standard output and standard error as bytes.
		"""
		start_time = time.monotonic()
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
					logger.debug("Read from process timed out after %r seconds", timeout)
					return b"", b""
			time.sleep(0.1)

		if self._exit_code is not None:
			# If the process has ended, ensure all reader threads have finished to capture any remaining output
			if self._stdout_reader and self._stdout_reader.is_alive():
				self._stdout_reader.join(timeout=3)
			if self._stderr_reader and self._stderr_reader.is_alive():
				self._stderr_reader.join(timeout=3)

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

	def read_stdout_bytes(self, *, timeout: float | int | None = None, truncate: bool = True) -> bytes:
		"""
		Read new data from the process's standard output since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:return: New standard output data as bytes.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=True, stderr=False)[0]

	def read_stderr_bytes(self, *, timeout: float | int | None = None, truncate: bool = True) -> bytes:
		"""
		Read new data from the process's standard error since the last read.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param truncate: Whether to to truncate the buffer after reading.
		:return: New standard error data as bytes.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=False, stderr=True)[1]

	def read_text(
		self, *, timeout: float | int | None = None, errors: Literal["ignore", "replace", "strict"] = "replace", truncate: bool = True
	) -> tuple[str, str]:
		"""
		Read new data from the process's standard output and standard error since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: A tuple containing the new standard output and standard error as text.
		"""
		stdout_bytes, stderr_bytes = self.read_bytes(timeout=timeout, truncate=truncate)
		return stdout_bytes.decode(self._encoding, errors=errors), stderr_bytes.decode(self._encoding, errors=errors)

	def read_stdout_text(
		self, *, timeout: float | int | None = None, errors: Literal["ignore", "replace", "strict"] = "replace", truncate: bool = True
	) -> str:
		"""
		Read new data from the process's standard output since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: New standard output data as text.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=True, stderr=False)[0].decode(self._encoding, errors=errors)

	def read_stderr_text(
		self, *, timeout: float | int | None = None, errors: Literal["ignore", "replace", "strict"] = "replace", truncate: bool = True
	) -> str:
		"""
		Read new data from the process's standard error since the last read, and decode it as text.
		:param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
		:param errors: How to handle decoding errors.
		:param truncate: Whether to truncate the buffer after reading.
		:return: New standard error data as text.
		"""
		return self.read_bytes(timeout=timeout, truncate=truncate, stdout=False, stderr=True)[1].decode(self._encoding, errors=errors)


def run_command(
	command: Collection[str] | str | None = None,
	*,
	working_dir: Path | str | None = None,
	timeout: float | int | None = None,
	stdin: str | bytes | None = None,
	close_stdin: bool = True,
	capture_output: Literal["stdout", "stderr", "both", "combined", "none"] = "combined",
	encoding: str | None = None,
	success_exit_codes: Collection[int] | None = (0,),
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a command directly and return the Process instance.
	"""
	with Process(
		command=command,
		working_dir=working_dir,
		timeout=timeout,
		stdin=stdin,
		close_stdin=close_stdin,
		capture_output=capture_output,
		encoding=encoding,
		success_exit_codes=success_exit_codes,
		retry_config=retry_config,
	) as proc:
		pass
	return proc


def run_script(
	script: str | Collection[str] | Path,
	*,
	interpreter: Literal["cmd", "powershell", "bash"] | Collection[str] | str | None = None,
	arguments: Collection[str | int | float] | None = None,
	working_dir: Path | str | None = None,
	timeout: float | int | None = None,
	stdin: str | bytes | None = None,
	close_stdin: bool = True,
	capture_output: Literal["stdout", "stderr", "both", "combined", "none"] = "combined",
	encoding: str | None = None,
	success_exit_codes: Collection[int] | None = (0,),
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a script via an interpreter and return the Process instance.
	"""
	if isinstance(script, list):
		script = os.linesep.join(script) + os.linesep

	with Process(
		script=script,
		interpreter=interpreter,
		arguments=arguments,
		working_dir=working_dir,
		timeout=timeout,
		capture_output=capture_output,
		encoding=encoding,
		success_exit_codes=success_exit_codes,
		retry_config=retry_config,
	) as proc:
		pass
	return proc


def run_script_file(
	script_file: str | Path,
	*,
	interpreter: Literal["cmd", "powershell", "bash"] | Collection[str] | str | None = None,
	arguments: Collection[str | int | float] | None = None,
	working_dir: Path | str | None = None,
	timeout: float | int | None = None,
	stdin: str | bytes | None = None,
	close_stdin: bool = True,
	capture_output: Literal["stdout", "stderr", "both", "combined", "none"] = "combined",
	encoding: str | None = None,
	success_exit_codes: Collection[int] | None = (0,),
	retry_config: RetryConfig | None = None,
) -> Process:
	"""
	Run a script via an interpreter and return the Process instance.
	"""
	with Process(
		script=Path(script_file),
		interpreter=interpreter,
		arguments=arguments,
		working_dir=working_dir,
		timeout=timeout,
		capture_output=capture_output,
		encoding=encoding,
		success_exit_codes=success_exit_codes,
		retry_config=retry_config,
	) as proc:
		pass
	return proc
