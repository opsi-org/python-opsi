# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import sys
import time
from pathlib import Path
from subprocess import list2cmdline
from typing import Literal
from unittest.mock import patch

import psutil
import pytest

from opsi.process import Process, ProcessError, run_command, run_script, run_script_file
from opsi.process._common import _get_interpreter_command, _get_process_io_encoding
from opsi.system.info import is_windows
from opsi.testing.helper import environment


@pytest.mark.parametrize(
	"interpreter, script_file, arguments, expected_command",
	[
		("cmd", Path("script_file.bat"), ["arg1", "arg2"], ["script_file.bat", "arg1", "arg2"]),
		("cmd", "script_file.cmd", [], ["script_file.cmd"]),
		("cmd", "-", None, ["cmd.exe", "/q", "/d", "/k", "@echo off"]),
		(
			"powershell",
			Path("script_file.ps1"),
			["arg1", "arg2"],
			[
				"powershell.exe",
				"-NoLogo",
				"-NonInteractive",
				"-NoProfile",
				"-ExecutionPolicy",
				"Bypass",
				"-File",
				"script_file.ps1",
				"arg1",
				"arg2",
			],
		),
		(
			"powershell",
			"-",
			None,
			["powershell.exe", "-NoLogo", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "-"],
		),
	]
	if is_windows()
	else [
		("bash", Path("script_file"), ["arg1", "arg2"], ["bash", "script_file", "arg1", "arg2"]),
		("bash", "-", None, ["bash", "-s", "--"]),
		("bash", "-", ["arg 1", "arg 2"], ["bash", "-s", "--", "arg 1", "arg 2"]),
	],
)
def test_get_interpreter_command(
	interpreter: Literal["cmd", "powershell", "bash"], script_file: Path | str, arguments: list[str] | None, expected_command: list[str]
) -> None:
	command = _get_interpreter_command(interpreter=interpreter, script_file=script_file, arguments=arguments)
	command[0] = os.path.basename(command[0])
	assert command == expected_command

	if is_windows():
		with pytest.raises(ValueError, match="cmd.exe interpreter requires script file with .cmd or .bat extension"):
			_get_interpreter_command(interpreter="cmd", script_file="script")


def test_get_interpreter_command_error() -> None:
	with pytest.raises(FileNotFoundError, match="Interpreter not found: unknown"):
		_get_interpreter_command(interpreter="unknown", script_file="-")  # type: ignore[invalid-argument-type]


@pytest.mark.parametrize("interpreter", ["cmd", "powershell", None] if is_windows() else ["bash", None])
def test_get_process_io_encoding(interpreter: Literal["cmd", "powershell", "bash"] | None) -> None:
	_get_process_io_encoding.cache_clear()
	encoding = _get_process_io_encoding(interpreter)
	if is_windows():
		if interpreter == "powershell":
			assert encoding.lower() == "utf-8" or encoding.lower().startswith("cp")
		else:
			assert encoding.lower().startswith("cp")
	else:
		assert encoding.lower() == "utf-8"

	with (
		patch("opsi.process._common.locale.getpreferredencoding", side_effect=Exception("Failed")),
		patch("opsi.process._common.subprocess.check_output", side_effect=Exception("Failed")),
	):
		_get_process_io_encoding.cache_clear()
		encoding = _get_process_io_encoding(interpreter)
		assert encoding.lower() == "utf-8"


@pytest.mark.parametrize("size_limit", [1000, 120])
@pytest.mark.parametrize("capture_output", ["stdout", "stderr", "both", "combined", "none"])
@pytest.mark.parametrize("truncate", [True, False])
def test_process_read(size_limit: int, capture_output: Literal["stdout", "stderr", "both", "combined", "none"], truncate: bool) -> None:
	stdout_data = b""
	stderr_data = b""
	script = (
		(
			"echo stdout one stdout one stdout one stdout one",
			"echo stderr one stderr one stderr one stderr one>&2",
			"ping -n 2 127.0.0.1 >NUL",
			"echo stdout two stdout two stdout two stdout two",
			"echo stderr two stderr two stderr two stderr two>&2",
			"ping -n 2 127.0.0.1 >NUL",
			"echo stdout three stdout three stdout three stdout three",
			"echo stderr three stderr three stderr three stderr three>&2",
		)
		if is_windows()
		else (
			'echo "stdout one stdout one stdout one stdout one"',
			'echo "stderr one stderr one stderr one stderr one" 1>&2',
			"sleep 1",
			'echo "stdout two stdout two stdout two stdout two"',
			'echo "stderr two stderr two stderr two stderr two" 1>&2',
			"sleep 1",
			'echo "stdout three stdout three stdout three stdout three"',
			'echo "stderr three stderr three stderr three stderr three" 1>&2',
		)
	)
	with patch.object(Process, "_stderr_limit", size_limit), patch.object(Process, "_stdout_limit", size_limit):
		with Process(script=script, capture_output=capture_output) as proc:
			num = 0
			while proc.is_running():
				num += 1
				if num % 2 == 0:
					stdout, stderr = proc.read_bytes(truncate=truncate)
					if capture_output != "none" and proc.exit_code is None:
						assert stdout or stderr
				else:
					stderr = proc.read_stderr_bytes(timeout=0.1, truncate=truncate)
					stdout = proc.read_stdout_bytes(timeout=0.1, truncate=truncate)
				if stdout:
					stdout_data += stdout
				if stderr:
					stderr_data += stderr
			assert proc.read_bytes(stdout=False, stderr=False) == (b"", b"")  # Make no sense, just a test

	stdout_lines = [
		b"stdout one stdout one stdout one stdout one",
		b"stdout two stdout two stdout two stdout two",
		b"stdout three stdout three stdout three stdout three",
	]
	stderr_lines = [
		b"stderr one stderr one stderr one stderr one",
		b"stderr two stderr two stderr two stderr two",
		b"stderr three stderr three stderr three stderr three",
	]
	expected_stdout_lines = []
	expected_stderr_lines = []
	if capture_output == "stdout":
		expected_stdout_lines = stdout_lines
	elif capture_output == "stderr":
		expected_stderr_lines = stderr_lines
	elif capture_output == "both":
		expected_stdout_lines = stdout_lines
		expected_stderr_lines = stderr_lines
	elif capture_output == "combined":
		expected_stdout_lines = [line for lines in zip(stdout_lines, stderr_lines) for line in lines]
	elif capture_output == "none":
		pass

	linesep = os.linesep.encode()
	expected_stdout_data = (linesep.join(expected_stdout_lines) + linesep) if expected_stdout_lines else b""
	expected_stderr_data = (linesep.join(expected_stderr_lines) + linesep) if expected_stderr_lines else b""
	if not truncate:
		# If not truncating, the data stays in the buffer and no more data will be appended when the limit is reached
		expected_stdout_data = expected_stdout_data[:size_limit]
		expected_stderr_data = expected_stderr_data[:size_limit]

	print("==============================================================================")
	print("size_limit:", size_limit, ", capture_output:", capture_output, ", truncate:", truncate)
	print("==============================================================================")
	print(len(expected_stdout_data), expected_stdout_data)
	print(len(stdout_data), stdout_data)
	print(len(proc.get_stdout_bytes()), proc.get_stdout_bytes())
	print("==============================================================================")
	print(len(expected_stderr_data), expected_stderr_data)
	print(len(stderr_data), stderr_data)
	print(len(proc.get_stderr_bytes()), proc.get_stderr_bytes())
	print("==============================================================================")

	assert stdout_data == expected_stdout_data
	assert stderr_data == expected_stderr_data

	assert proc.exit_code == 0
	assert proc.wait(timeout=1)
	assert not proc.is_running()

	# All data should be already read
	assert proc.read_stdout_bytes(truncate=truncate) == b""
	assert proc.read_stderr_bytes(truncate=truncate) == b""

	if truncate:
		# If truncating, the data is removed from the buffer
		assert proc.get_stdout_bytes() == b""
		assert proc.get_stderr_bytes() == b""
	else:
		# If not truncating, the data stays in the buffer
		assert proc.get_stdout_bytes() == expected_stdout_data
		assert proc.get_stderr_bytes() == expected_stderr_data

	if proc._manager_thread:
		assert not proc._manager_thread.is_alive()
	if proc._stderr_reader:
		assert not proc._stderr_reader.is_alive()
	if proc._stdout_reader:
		assert not proc._stdout_reader.is_alive()


def test_process_read_max(tmp_path: Path) -> None:
	data = b"A" * 500_000
	file_path = tmp_path / "data.bin"
	file_path.write_bytes(data)

	stdout_data = b""
	if is_windows():
		script = f"@echo off && type {file_path}"
		with patch.object(Process, "_read_max", 10_000):
			with Process(script=script, interpreter="cmd") as proc:
				while proc.is_running():
					stdout, _ = proc.read_bytes(timeout=10)
					if stdout:
						stdout_data += stdout
	else:
		with Process(command=["cat", str(file_path)]) as proc:
			with patch.object(Process, "_read_max", 10_000):
				while proc.is_running():
					stdout, _ = proc.read_bytes(timeout=10)
					if stdout:
						stdout_data += stdout

	assert stdout_data == data
	assert proc.runtime < 5


@pytest.mark.windows
@pytest.mark.parametrize("interpreter", ["cmd", "powershell", None])
@pytest.mark.parametrize("pipe_script", [True, False])
@pytest.mark.parametrize("script_file", [True, False])
def test_process_interpreter_windows(tmp_path: Path, interpreter: str | None, pipe_script: bool, script_file: bool) -> None:
	user = os.environ.get("USERNAME", "")
	if interpreter == "powershell":
		script = 'Write-Output "Multi line script"\r\necho "$env:USERNAME"\r\necho "end of script"'
	else:
		script = "@echo off\r\necho Multi line script\r\necho %USERNAME%\r\necho end of script"
	if script_file:
		script_path = tmp_path / f"script.{'ps1' if interpreter == 'powershell' else 'cmd'}"
		script_path.write_text(script)
		script_arg: str | Path = script_path
	else:
		script_arg = script
	with patch.object(Process, "_pipe_script", pipe_script):
		with Process(script=script_arg, interpreter=interpreter) as proc:
			assert proc._pipe_script == pipe_script
			pass

	out = proc.get_output_text().strip()
	if interpreter == "powershell" and pipe_script:
		# PowerShell will echo commands and show prompt
		# Bug in PowerShell 5.3?
		assert "Multi line script\r\n" in out
		assert f"{user}\r\n" in out
		assert "end of script" in out
	else:
		assert out == f"Multi line script\r\n{user}\r\nend of script"
		lines = proc.get_output_lines()
		assert lines == ["Multi line script", user, "end of script"]


@pytest.mark.posix
@pytest.mark.parametrize("interpreter", ["bash", None])
@pytest.mark.parametrize("pipe_script", [True, False])
@pytest.mark.parametrize("script_file", [True, False])
def test_process_interpreter_posix(tmp_path: Path, interpreter: str | None, pipe_script: bool, script_file: bool) -> None:
	user = os.environ.get("USER", "")
	script = "echo Multi line script\necho $USER\necho $1 - $2 - $3\necho end of script"
	if script_file:
		script_path = tmp_path / "script.sh"
		script_path.write_text(script)
		script_arg: str | Path = script_path
	else:
		script_arg = script
	with patch.object(Process, "_pipe_script", pipe_script):
		with Process(script=script_arg, arguments=["arg1", 2, 0.3], interpreter=interpreter) as proc:
			assert proc._pipe_script == pipe_script
			pass
	assert proc.get_output_text().strip() == f"Multi line script\n{user}\narg1 - 2 - 0.3\nend of script"
	lines = proc.get_output_lines()
	assert lines == ["Multi line script", user, "arg1 - 2 - 0.3", "end of script"]


def test_process_stop() -> None:
	command = ["ping", "/n" if is_windows() else "-c", "10", "127.0.0.1"]
	pid = None
	with Process(command=command) as proc:
		pid = proc.pid
		assert pid is not None
		time.sleep(2)
		proc.stop()

	assert not proc.is_running()
	assert proc.runtime < 5
	assert proc.pid == pid

	stdout_data, stderr_data = proc.read_bytes(truncate=False)
	assert b"127.0.0.1" in stdout_data
	assert stderr_data == b""

	assert proc.wait(timeout=1)
	assert proc.exit_code == (1 if is_windows() else -9)
	assert proc.get_stderr_bytes() == stderr_data
	assert proc.get_stdout_bytes() == stdout_data
	if proc._manager_thread:
		assert not proc._manager_thread.is_alive()
	if proc._stderr_reader:
		assert not proc._stderr_reader.is_alive()
	if proc._stdout_reader:
		assert not proc._stdout_reader.is_alive()
	with Process(command=command) as proc:
		time.sleep(1)
		proc.stop()
		assert not proc.is_running()


def test_process_timeout() -> None:
	command = ["ping", "/n" if is_windows() else "-c", "5", "127.0.0.1"]
	with pytest.raises(ProcessError, match="Failed to run process after 1 attempts: Process timed out after") as exc_info:
		with Process(command=command, timeout=2) as proc:
			proc.wait(timeout=10)

	assert exc_info.value.process == proc
	assert proc.timed_out
	assert not proc.is_running()
	assert proc.exit_code == (1 if is_windows() else -9)
	if proc._manager_thread:
		assert not proc._manager_thread.is_alive()
	if proc._stderr_reader:
		assert not proc._stderr_reader.is_alive()
	if proc._stdout_reader:
		assert not proc._stdout_reader.is_alive()


def test_process_stdin() -> None:
	command = ["findstr" if is_windows() else "grep", "opsi"]
	proc = Process(command=command)
	with patch.object(Process, "_start_wait_timeout", 1.0):
		with pytest.raises(RuntimeError, match="Process is not running or stdin is closed"):
			proc.write_text("opsi2\n")

	with Process(command=command, stdin="start\nopsi\nend\n") as proc:
		pass

	assert not proc.is_running()
	assert proc.get_output_text() == "opsi\n"

	with Process(command=command, stdin="opsi1\n", close_stdin=False) as proc:
		proc.write_text("opsi2\n")
		proc.write_text("other\n")
		proc.write_text("opsi3\n", close=True)

	assert not proc.is_running()
	assert proc.get_output_text() == "opsi1\nopsi2\nopsi3\n"


def test_process_run_time() -> None:
	command = ["ping", "-n", "3", "-w", "1000", "localhost"] if is_windows() else ["sleep", "3"]
	proc = Process(command=command)
	assert proc.runtime == 0.0

	with Process(command=command) as proc:
		assert proc.runtime < 1.0

	assert not proc.is_running()
	assert proc.exit_code == 0
	assert proc.runtime > 2.0
	assert proc.runtime < 4.0


def test_process_working_dir(tmp_path: Path) -> None:
	for filename in "test.txt", "ÜÖÄöäü.txt":
		(tmp_path / filename).touch()
	command = "dir" if is_windows() else "ls"
	with Process(script=command, working_dir=tmp_path) as proc:
		pass

	assert proc.exit_code == 0
	out = proc.get_output_text().strip()
	assert "test.txt" in out
	assert "ÜÖÄöäü.txt" in out


def test_process_environment() -> None:
	script = "echo %ENV_TEST1%" if is_windows() else "echo $ENV_TEST1"
	with Process(script=script, environment={"ENV_TEST1": "value 1"}) as proc:
		pass

	assert proc.exit_code == 0
	assert proc.get_output_text().strip() == "value 1"


def test_process_arguments() -> None:
	command = ["ping"]
	arguments = ["/n", "1", "127.0.0.1"] if is_windows() else ["-c", "1", "127.0.0.1"]
	with Process(command=command, arguments=arguments) as proc:
		pass

	assert proc.exit_code == 0


@pytest.mark.linux
@pytest.mark.parametrize(
	"ld_library_path_orig, ld_library_path, executable_path, expected_ld_library_path",
	(
		# LD_LIBRARY_PATH_ORIG is set to a valid value, LD_LIBRARY_PATH must be set to that value
		("/orig/ld/path", "/usr/lib/opsi_component", "/usr/lib/opsi_component/bin/executable", "/orig/ld/path"),
		("/orig/ld/path", "/some/path:/usr/lib/opsiclientd:/usr/lib/opsiconfd", "/usr/lib/opsi_component/bin/executable", "/orig/ld/path"),
		# LD_LIBRARY_PATH_ORIG is not set, LD_LIBRARY_PATH must be removed
		(None, "/usr/lib/opsi_component", "/usr/lib/opsi_component/bin/executable", None),
		# LD_LIBRARY_PATH_ORIG is empty, LD_LIBRARY_PATH must be removed
		("", "/usr/lib/opsi_component", "/usr/lib/opsi_component/bin/executable", None),
		# LD_LIBRARY_PATH_ORIG is empty, LD_LIBRARY_PATH is valid and must be kept
		("", "/some/path", "/usr/lib/opsi_component/bin/executable", "/some/path"),
		# LD_LIBRARY_PATH_ORIG is empty, LD_LIBRARY_PATH is valid and must be kept
		("", "/some/path: /other/path", "/usr/lib/opsi_component/bin/executable", "/some/path:/other/path"),
		# LD_LIBRARY_PATH_ORIG is not set, executable path must be removed fom LD_LIBRARY_PATH
		("", "/some/path:/usr/lib/opsi_component", "/usr/lib/opsi_component/bin/executable", "/some/path"),
		# LD_LIBRARY_PATH_ORIG is not set, hardcoded excludes must be removed fom LD_LIBRARY_PATH
		("", "/some/path:/usr/lib/opsiclientd:/usr/lib/opsiconfd", "/usr/lib/opsi_component/bin/executable", "/some/path"),
		# LD_LIBRARY_PATH_ORIG is not set, hardcoded excludes must not be added to LD_LIBRARY_PATH
		("", "/some/path:/usr/lib:/usr/lib/opsiclientd/_internal", "mount", "/some/path:/usr/lib"),
	),
)
def test_process_ld_library_path(
	ld_library_path_orig: str, ld_library_path: str, executable_path: str, expected_ld_library_path: str
) -> None:
	frozen = getattr(sys, "frozen", False)
	setattr(sys, "frozen", True)
	try:
		env_vars = {"_MEIPASS2": "/tmp/foobar", "_PYI_APPLICATION_HOME_DIR": "/tmp/foobar", "_PYI_LINUX_PROCESS_NAME": "frozen-proc"}
		if ld_library_path_orig is not None:
			env_vars["LD_LIBRARY_PATH_ORIG"] = ld_library_path_orig
		if ld_library_path is not None:
			env_vars["LD_LIBRARY_PATH"] = ld_library_path
		with (
			patch("opsi.process._common._get_executable_path", lambda: Path(executable_path)),
			environment(env_vars),
		):
			assert os.environ.get("LD_LIBRARY_PATH_ORIG") == ld_library_path_orig
			assert os.environ.get("LD_LIBRARY_PATH") == ld_library_path
			with run_command(["sleep", "1"]) as proc:
				ps_proc = psutil.Process(proc.pid)
				assert ps_proc and ps_proc.environ
				proc_env = ps_proc.environ()
				assert proc_env.get("LD_LIBRARY_PATH_ORIG") == ld_library_path_orig
				assert proc_env.get("LD_LIBRARY_PATH") == expected_ld_library_path
				assert proc_env.get("_MEIPASS2") is None
				assert proc_env.get("_PYI_APPLICATION_HOME_DIR") is None
				assert proc_env.get("_PYI_LINUX_PROCESS_NAME") is None
				proc.wait()
			assert os.environ.get("LD_LIBRARY_PATH_ORIG") == ld_library_path_orig
			assert os.environ.get("LD_LIBRARY_PATH") == ld_library_path
			assert os.environ.get("_MEIPASS2") == "/tmp/foobar"
			assert os.environ.get("_PYI_APPLICATION_HOME_DIR") == "/tmp/foobar"
			assert os.environ.get("_PYI_LINUX_PROCESS_NAME") == "frozen-proc"
	finally:
		setattr(sys, "frozen", frozen)


def test_process_argument_validation() -> None:
	with pytest.raises(ValueError, match="'command' and 'script' are mutually exclusive"):
		Process(command="echo test", script="echo test")
	with pytest.raises(ValueError, match="Either 'command' or 'script' must be provided"):
		Process()
	with pytest.raises(ValueError, match="'interpreter' can only be used with 'script', not with 'command'"):
		Process(command="echo test", interpreter="python")
	with pytest.raises(ValueError, match="'exit_on_error' can only be used with 'bash' or 'powershell' interpreter"):
		Process(script="exit 0", interpreter="cmd", exit_on_error=True)
	with pytest.raises(ValueError, match="Invalid capture_output value"):
		Process(script="exit 0", interpreter="bash", capture_output="invalid_value")  # type: ignore[invalid-argument-type]


def test_command_and_script() -> None:
	for script in ('echo "OPSI is great!"', ["echo", "OPSI is great!"]):
		script_str = script if isinstance(script, str) else list2cmdline(script)
		with Process(script=script_str) as proc:
			pass
		assert proc.exit_code == 0
		if is_windows():
			assert proc.get_script() == "@echo off" + os.linesep + 'echo "OPSI is great!"' + os.linesep
			assert proc.get_output_text().strip() == '"OPSI is great!"'
		else:
			assert proc.get_script() == 'echo "OPSI is great!"' + os.linesep
			assert proc.get_output_text().strip() == "OPSI is great!"

	for command in (
		("ping /n 1 127.0.0.1", ["ping", "/n", "1", "127.0.0.1"])
		if is_windows()
		else ("ping -c 1 127.0.0.1", ["ping", "-c", "1", "127.0.0.1"])
	):
		with Process(command=command) as proc:
			pass
		assert proc.exit_code == 0
		if is_windows():
			assert proc.get_command() == "ping /n 1 127.0.0.1"
		else:
			assert proc.get_command() == "ping -c 1 127.0.0.1"


def test_process_detect_interpreter() -> None:
	for extension in ("cmd", "bat", "ps1") if is_windows() else ("sh",):
		with patch.object(Process, "_pipe_script", True):
			proc = Process(script=Path(f"test_script.{extension}"))
		if extension in ("cmd", "bat"):
			assert proc._command[0].endswith("cmd.exe")
		elif extension == "ps1":
			assert proc._command[0].endswith("powershell.exe")
		else:
			assert proc._command[0].endswith("bash")


def test_process_custom_interpreter_list() -> None:
	with Process(
		script="import sys; print(f'Running with uv: {sys.argv[1]}')", interpreter=["uv", "run", "python"], arguments=["arg1"]
	) as proc:
		pass
	assert proc.exit_code == 0
	assert proc.get_output_text().strip() == "Running with uv: arg1"


@pytest.mark.posix
def test_process_custom_interpreter_string() -> None:
	with Process(script='echo "from shell: $1"', interpreter="sh", arguments=["arg1"]) as proc:
		pass
	assert proc.exit_code == 0
	assert proc.get_output_text().strip() == "from shell: arg1"


@pytest.mark.parametrize("exit_on_error", [True, False])
def test_process_script_exit_on_error(exit_on_error: bool) -> None:
	with Process(
		script="Invoke-WebRequest https://localhost:1234\nexit 0" if is_windows() else "ls -l /notexisting\nexit 0",
		interpreter="powershell" if is_windows() else "bash",
		exit_on_error=exit_on_error,
		success_exit_codes=None,
	) as proc:
		pass
	if exit_on_error:
		assert proc.exit_code != 0
		script = proc.get_script()
		assert script
		if is_windows():
			assert '$ErrorActionPreference = "Stop"' in script
		else:
			assert "set -e" in script
	else:
		assert proc.exit_code == 0


def test_process_script_exit_on_error_error() -> None:
	for interpreter in ("cmd", "zsh", ["uv", "run"]):
		with pytest.raises(ValueError, match="'exit_on_error' can only be used with 'bash' or 'powershell' interpreter"):
			with Process(script="exit 0", interpreter=interpreter, exit_on_error=True):
				pass


def test_process_error(tmp_path: Path) -> None:
	with pytest.raises(ProcessError, match="Process exited with code 3") as exc_info:
		with Process(script="exit 3"):
			pass
	assert exc_info.value.script == ("@echo off" + os.linesep if is_windows() else "") + "exit 3" + os.linesep
	assert exc_info.value.exit_code == 3

	with Process(script="echo exit 3 && exit 3", success_exit_codes=(0, 3)) as proc:
		proc.wait()
		assert proc.exit_code == 3
		assert proc.get_script() == ("@echo off" + os.linesep if is_windows() else "") + "echo exit 3 && exit 3" + os.linesep
		assert proc.get_output_text().strip() == "exit 3"

	with pytest.raises(
		ProcessError, match="Failed to run process after 5 attempts.*" + ("WinError 2" if is_windows() else "No such file")
	) as exc_info:
		with Process(command=["not_available_command", "arg1"]):
			pass
	assert exc_info.value.command == "not_available_command arg1"
	assert exc_info.value.exit_code is None

	not_executable = tmp_path / "not_executable"
	not_executable.write_text("echo not executable")
	not_executable.chmod(0o644)
	with pytest.raises(
		ProcessError, match="Failed to run process after 5 attempts.*" + ("WinError 193" if is_windows() else "Permission denied")
	) as exc_info:
		with Process(command=[str(not_executable)]):
			pass
	assert exc_info.value.command == str(not_executable)
	assert exc_info.value.exit_code is None
	assert exc_info.value.process._attempts == 5


def test_process_error_max_output_length(tmp_path: Path) -> None:
	stderr_data = "E" * 1000
	stderr_file = tmp_path / "stderr.txt"
	stderr_file.write_bytes(stderr_data.encode("ascii"))
	stdout_data = "O" * 1000
	stdout_file = tmp_path / "stdout.txt"
	stdout_file.write_bytes(stdout_data.encode("ascii"))

	if is_windows():
		script = f"@echo off && type {stderr_file} 1>&2 && type {stdout_file} && exit 1"
	else:
		script = f"cat {stderr_file} 1>&2 && cat {stdout_file} && exit 1"

	with patch.object(ProcessError, "max_output_length", 100):
		with pytest.raises(ProcessError, match="Process exited with code 1") as exc_info:
			with Process(script=script):
				pass

		assert exc_info.value.exit_code == 1
		assert exc_info.value.output == stdout_data + stderr_data
		err_lines = str(exc_info.value).split("\n")
		assert err_lines[0] == "Process exited with code 1"
		assert err_lines[1].startswith("Command:")
		assert err_lines[2] == "Exit code: 1"
		assert err_lines[3] == "Output:"
		assert err_lines[4] == "..." + "E" * 97


def test_run_command() -> None:
	with pytest.raises(
		ProcessError, match="Failed to run process after 5 attempts.*" + ("WinError 2" if is_windows() else "No such file")
	) as exc_info:
		run_command(command=["not_available_command", "arg1"])
	assert exc_info.value.command == "not_available_command arg1"


def test_run_script(tmp_path: Path) -> None:

	stderr_data = "E" * 10
	stderr_file = tmp_path / "stderr.txt"
	stderr_file.write_bytes(stderr_data.encode("ascii"))
	stdout_data = "O" * 10
	stdout_file = tmp_path / "stdout.txt"
	stdout_file.write_bytes(stdout_data.encode("ascii"))

	if is_windows():
		script = ["@echo off", f"type {stderr_file} 1>&2", f"type {stdout_file}"]
	else:
		script = [f"cat {stderr_file} 1>&2", f"cat {stdout_file}"]

	proc = run_script(script=script, capture_output="both")
	assert proc.get_output_text().strip() == stdout_data + stderr_data
	assert proc.get_stderr_text().strip() == stderr_data
	assert proc.get_stdout_text().strip() == stdout_data
	assert proc.get_stderr_bytes().strip() == stderr_data.encode("ascii")
	assert proc.get_stdout_bytes().strip() == stdout_data.encode("ascii")
	assert proc.read_text(truncate=False) == (stdout_data, stderr_data)
	proc._stdout_read_position = proc._stderr_read_position = 0
	assert proc.read_stderr_text(truncate=False).strip() == stderr_data
	assert proc.read_stdout_text(truncate=False).strip() == stdout_data
	proc._stdout_read_position = proc._stderr_read_position = 0
	assert proc.read_bytes(truncate=False) == (stdout_data.encode("ascii"), stderr_data.encode("ascii"))
	proc._stdout_read_position = proc._stderr_read_position = 0
	assert proc.read_stderr_bytes(truncate=False).strip() == stderr_data.encode("ascii")
	assert proc.read_stdout_bytes(truncate=False).strip() == stdout_data.encode("ascii")

	with pytest.raises(ProcessError, match="Process exited with code 3") as exc_info:
		run_script(script="exit 3")
	assert exc_info.value.script == ("@echo off" + os.linesep if is_windows() else "") + "exit 3" + os.linesep

	with pytest.raises(ProcessError):
		run_script(
			script="Invoke-WebRequest https://localhost:1234\nexit 0" if is_windows() else "ls -l /notexisting\nexit 0",
			interpreter="powershell" if is_windows() else "bash",
			exit_on_error=True,
		)


def test_run_script_file(tmp_path: Path) -> None:
	script_path = tmp_path / ("test_script.sh" if not is_windows() else "test_script.cmd")
	script_path.write_text(("@echo off" + os.linesep if is_windows() else "") + "echo OPSI" + os.linesep)
	for script_arg in (script_path, str(script_path)):
		proc = run_script_file(script_file=script_arg)
		assert proc.get_output_text().strip() == "OPSI"
