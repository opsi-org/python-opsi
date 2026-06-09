# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import opsi.system.network


def _load_platform_module(monkeypatch: pytest.MonkeyPatch, module_name: str, platform: str) -> ModuleType:
	monkeypatch.setattr(sys, "platform", platform)
	sys.modules.pop(module_name, None)
	return importlib.import_module(module_name)


def _load_linux_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
	return _load_platform_module(monkeypatch, "opsi.system.network._linux", "linux")


def _load_macos_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
	return _load_platform_module(monkeypatch, "opsi.system.network._macos", "darwin")


def _load_windows_module(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, list[tuple[Any, ...]], list[tuple[Any, ...]]]:
	net_use_add_calls: list[tuple[Any, ...]] = []
	net_use_del_calls: list[tuple[Any, ...]] = []

	class FakeWinFunction:
		argtypes: list[Any]
		restype: Any

		def __call__(self, *_args: Any) -> int:
			return 0

	class FakeNetapi32:
		NetUseEnum = FakeWinFunction()
		NetApiBufferFree = FakeWinFunction()

	class FakeWin32NetError(Exception):
		pass

	fake_win32net = ModuleType("win32net")
	fake_win32net.NetUseAdd = lambda *args: net_use_add_calls.append(args)  # ty: ignore[unresolved-attribute]
	fake_win32net.NetUseDel = lambda *args: net_use_del_calls.append(args)  # ty: ignore[unresolved-attribute]
	fake_win32net.NetUseGet = lambda *_args: (_ for _ in ()).throw(FakeWin32NetError())  # ty: ignore[unresolved-attribute]
	fake_win32net.error = FakeWin32NetError  # ty: ignore[unresolved-attribute]

	fake_win32netcon = ModuleType("win32netcon")
	fake_win32netcon.USE_FORCE = 1  # ty: ignore[unresolved-attribute]
	fake_win32netcon.RESOURCETYPE_DISK = 1  # ty: ignore[unresolved-attribute]

	fake_win32wnet = ModuleType("win32wnet")
	fake_win32wnet.WNetAddConnection2 = lambda *_args: None  # ty: ignore[unresolved-attribute]

	monkeypatch.setattr(ctypes, "WinDLL", lambda _name: FakeNetapi32(), raising=False)
	monkeypatch.setitem(sys.modules, "win32net", fake_win32net)
	monkeypatch.setitem(sys.modules, "win32netcon", fake_win32netcon)
	monkeypatch.setitem(sys.modules, "win32wnet", fake_win32wnet)
	module = _load_platform_module(monkeypatch, "opsi.system.network._windows", "win32")
	return module, net_use_add_calls, net_use_del_calls


@pytest.mark.linux
def test_linux_mount_cifs_share_creates_mount_point_and_uses_credentials_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)
	run_command_calls: list[dict[str, Any]] = []

	def fake_run_command(command: list[str], *, environment: dict[str, str], timeout: int) -> None:
		credentials_path = command[6].split(",", 1)[0].removeprefix("credentials=")
		run_command_calls.append(
			{
				"command": command,
				"environment": environment,
				"timeout": timeout,
				"credentials_path": credentials_path,
				"credentials": Path(credentials_path).read_text(encoding="utf-8"),
			}
		)

	monkeypatch.setattr(module, "run_command", fake_run_command)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)
	mount_point = tmp_path / "mnt"

	module.mount_cifs_share("server", "share", mount_point, r"DOMAIN\\user", "secret")

	assert mount_point.is_dir()
	assert len(run_command_calls) == 1
	assert run_command_calls[0] == {
		"command": [
			"mount",
			"-t",
			"cifs",
			"//server/share",
			str(mount_point.absolute()),
			"-o",
			f"credentials={run_command_calls[0]['credentials_path']},domain=DOMAIN",
		],
		"environment": {"LC_ALL": "C"},
		"timeout": 15,
		"credentials_path": run_command_calls[0]["credentials_path"],
		"credentials": "username=user\npassword=secret\n",
	}


@pytest.mark.linux
def test_linux_mount_cifs_share_unmounts_existing_mount_before_mounting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)
	events: list[tuple[str, Path | list[str]]] = []
	mount_point = tmp_path / "mnt"
	mounted_point = mount_point.absolute()

	def fake_run_command(command: list[str], *, environment: dict[str, str], timeout: int) -> None:
		assert environment == {"LC_ALL": "C"}
		assert timeout == 15
		events.append(("mount", command))

	def fake_unmount_network_share(mount_point: Path | str | None) -> None:
		assert mount_point is not None
		events.append(("unmount", Path(mount_point)))

	monkeypatch.setattr(module, "run_command", fake_run_command)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("//server/old", mounted_point))
	monkeypatch.setattr(module, "unmount_network_share", fake_unmount_network_share)

	module.mount_cifs_share("server", "share", mount_point, "user", "secret")

	assert events[0] == ("unmount", mounted_point)
	assert events[1][0] == "mount"
	mount_command = events[1][1]
	assert isinstance(mount_command, list)
	assert mount_command[:6] == ["mount", "-t", "cifs", "//server/share", str(mounted_point), "-o"]
	assert mount_command[6].startswith("credentials=")


@pytest.mark.linux
def test_linux_mount_cifs_share_rejects_domain_with_double_quote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)

	with pytest.raises(ValueError, match="Domain cannot contain double quotes"):
		module.mount_cifs_share("server", "share", tmp_path / "mnt", 'DO"MAIN\\user', "secret")


@pytest.mark.linux
def test_linux_get_mount_finds_device_and_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)

	def fake_read_text(path: Path, *_args: Any, **_kwargs: Any) -> str:
		assert path == Path("/proc/mounts")
		return "//server/share /mnt/share cifs rw,relatime 0 0\n/dev/sda1 / ext4 rw 0 0\n"

	monkeypatch.setattr(Path, "read_text", fake_read_text)

	assert module._get_mount(device="//server/share") == ("//server/share", Path("/mnt/share"))
	assert module._get_mount(mount_point="/mnt/share") == ("//server/share", Path("/mnt/share"))


@pytest.mark.linux
def test_linux_get_mount_requires_device_or_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)

	with pytest.raises(ValueError, match="Either device or mount_point must be provided"):
		module._get_mount()


@pytest.mark.linux
def test_linux_mount_webdav_share_uses_rclone_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)
	run_command_calls: list[dict[str, Any]] = []

	class FakeCommandResult:
		def get_stdout_text(self) -> str:
			return "obscured-secret\n"

	def fake_run_command(command: list[str], *, timeout: int, stdin: str | None = None) -> FakeCommandResult:
		call: dict[str, Any] = {"command": command, "timeout": timeout, "stdin": stdin}
		if command[1] == "mount":
			config_path = Path(command[command.index("--config") + 1])
			call["config"] = config_path.read_text(encoding="utf-8")
		run_command_calls.append(call)
		return FakeCommandResult()

	monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/opsi-rclone" if name == "opsi-rclone" else None)
	monkeypatch.setattr(module, "generate_secret", lambda *, length, alphabet: "abcdef12")
	monkeypatch.setattr(module, "run_command", fake_run_command)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)
	mount_point = tmp_path / "webdav"

	module.mount_webdav_share("server", 4447, "/depot", mount_point, "user", "secret")

	assert mount_point.is_dir()
	assert run_command_calls == [
		{"command": ["/usr/bin/opsi-rclone", "obscure", "-"], "timeout": 10, "stdin": "secret\n"},
		{
			"command": [
				"/usr/bin/opsi-rclone",
				"mount",
				"--config",
				run_command_calls[1]["command"][3],
				"--daemon",
				"--vfs-cache-mode",
				"writes",
				"--use-cookies",
				"abcdef12:",
				str(mount_point.absolute()),
			],
			"timeout": 15,
			"stdin": None,
			"config": "[abcdef12]\ntype = webdav\nurl = https://server:4447/depot\nvendor = other\nuser = user\npass = obscured-secret\n",
		},
	]


@pytest.mark.linux
def test_linux_mount_webdav_share_requires_rclone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)

	monkeypatch.setattr(module.shutil, "which", lambda _name: None)

	with pytest.raises(RuntimeError, match="rclone is required"):
		module.mount_webdav_share("server", 4447, "depot", tmp_path / "webdav", "user", "secret")


@pytest.mark.linux
@pytest.mark.parametrize(
	("mount_exists", "expected_calls"),
	[
		(True, 1),
		(False, 0),
	],
)
def test_linux_unmount_network_share_uses_umount_for_existing_mount(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
	mount_exists: bool,
	expected_calls: int,
) -> None:
	module = _load_linux_module(monkeypatch)
	run_command_calls: list[tuple[list[str], int]] = []
	mount_point = tmp_path / "mnt"
	mounted_point = mount_point.absolute()

	def fake_run_command(command: list[str], *, timeout: int) -> None:
		run_command_calls.append((command, timeout))

	monkeypatch.setattr(module, "run_command", fake_run_command)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("//server/share", mounted_point) if mount_exists else None)

	module.unmount_network_share(mount_point)

	if expected_calls:
		assert run_command_calls == [(["umount", str(mounted_point)], 15)]
	else:
		assert run_command_calls == []


@pytest.mark.linux
def test_linux_unmount_network_share_requires_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_linux_module(monkeypatch)

	with pytest.raises(ValueError, match="Either device or mount_point must be provided"):
		module.unmount_network_share(None)


@pytest.mark.macos
def test_macos_mount_cifs_share_uses_mount_smbfs_and_writes_prompted_password(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	module = _load_macos_module(monkeypatch)
	processes: list[FakeMacosProcess] = []

	class FakeMacosProcess:
		before = b""
		exitstatus = 0

		def __init__(self, command: str) -> None:
			self.command = command
			self.logfile_read: Any = None
			self.sent_lines: list[str] = []
			processes.append(self)

		def expect(self, patterns: Any, *, timeout: int) -> int:
			assert timeout == 10
			if isinstance(patterns, list):
				self.logfile_read.write(b"Password: ")
				return 0
			self.logfile_read.write(b"Mounted successfully\n")
			return 0

		def sendline(self, text: str) -> None:
			self.sent_lines.append(text)

		def close(self) -> None:
			return None

	monkeypatch.setattr(module.pexpect, "spawn", FakeMacosProcess)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)
	mount_point = tmp_path / "mnt"

	module.mount_cifs_share("server", r"share\folder", mount_point, r"DOMAIN\\user", "secret")

	assert mount_point.is_dir()
	assert len(processes) == 1
	assert processes[0].command == f"mount_smbfs '//DOMAIN;user@server/share/folder' {mount_point.absolute()}"
	assert processes[0].sent_lines == ["secret"]


@pytest.mark.macos
def test_macos_run_mount_command_raises_with_complete_output(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)
	processes: list[FakeMacosProcess] = []

	class FakeMacosProcess:
		before = b"only the final chunk\n"
		exitstatus = 67

		def __init__(self, _command: str) -> None:
			self.logfile_read: Any = None
			self.sent_lines: list[str] = []
			self.expect_calls = 0
			processes.append(self)

		def expect(self, patterns: Any, *, timeout: int) -> int:
			assert timeout == 10
			self.expect_calls += 1
			if patterns == "Username.*: ":
				self.logfile_read.write(b"Username: ")
				return 0
			if isinstance(patterns, list):
				self.logfile_read.write(b"Password: ")
				return 0
			self.logfile_read.write(b"first diagnostic line\nsecond diagnostic line\n")
			return 0

		def sendline(self, text: str) -> None:
			self.sent_lines.append(text)

		def close(self) -> None:
			return None

	monkeypatch.setattr(module.pexpect, "spawn", FakeMacosProcess)

	with pytest.raises(RuntimeError) as error:
		module._run_mount_command(["mount_webdav", "-i", "https://server/share", "/mnt"], username="user", password="secret")

	assert len(processes) == 1
	assert processes[0].sent_lines == ["user", "secret"]
	assert "Username: Password: first diagnostic line\nsecond diagnostic line" in str(error.value)


@pytest.mark.macos
def test_macos_run_mount_command_raises_ssl_certificate_error(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)

	class FakeMacosProcess:
		exitstatus = 19

		def __init__(self, _command: str) -> None:
			self.logfile_read: Any = None

		def expect(self, patterns: Any, *, timeout: int) -> int:
			assert timeout == 10
			if isinstance(patterns, list):
				return 1
			return 0

		def close(self) -> None:
			return None

	monkeypatch.setattr(module.pexpect, "spawn", FakeMacosProcess)

	with pytest.raises(RuntimeError, match="SSL certificate verification failure"):
		module._run_mount_command(["mount_webdav", "-i", "https://server/share", "/mnt"], username=None, password="secret")


@pytest.mark.macos
def test_macos_get_mount_finds_device_and_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)

	class FakeMountOutput:
		def get_stdout_lines(self) -> list[str]:
			return ["//server/share on /Volumes/share (smbfs, nodev, nosuid, mounted by user)", "/dev/disk1s1 on / (apfs)"]

	monkeypatch.setattr(module, "run_command", lambda command, *, timeout: FakeMountOutput())

	assert module._get_mount(device="//server/share") == ("//server/share", Path("/Volumes/share"))
	assert module._get_mount(mount_point="/Volumes/share") == ("//server/share", Path("/Volumes/share"))


@pytest.mark.macos
def test_macos_mount_webdav_share_installs_ca_and_runs_mount_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)
	ca_cert: Any = object()
	installed_certs: list[Any] = []
	run_mount_calls: list[tuple[list[str], str | None, str]] = []
	mount_point = tmp_path / "webdav"

	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)
	monkeypatch.setattr(module, "install_ca", lambda cert: installed_certs.append(cert))
	monkeypatch.setattr(
		module,
		"_run_mount_command",
		lambda command, *, username, password: run_mount_calls.append((command, username, password)),
	)

	module.mount_webdav_share("server", 4447, "/depot", mount_point, "user", "secret", ca_cert)

	assert mount_point.is_dir()
	assert installed_certs == [ca_cert]
	assert run_mount_calls == [(["mount_webdav", "-i", "https://server:4447/depot", str(mount_point.absolute())], "user", "secret")]


@pytest.mark.macos
def test_macos_mount_cifs_share_unmounts_existing_mount_before_mounting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)
	events: list[tuple[str, Path | str]] = []
	mount_point = tmp_path / "mnt"
	mounted_point = mount_point.absolute()

	class FakeMacosProcess:
		before = b""
		exitstatus = 0

		def __init__(self, command: str) -> None:
			self.logfile_read: Any = None
			events.append(("mount", command))

		def expect(self, patterns: Any, *, timeout: int) -> int:
			assert timeout == 10
			if isinstance(patterns, list):
				return 1
			return 0

		def sendline(self, text: str) -> None:
			raise AssertionError(f"Unexpected input: {text}")

		def close(self) -> None:
			return None

	def fake_unmount_network_share(mount_point: Path | str | None) -> None:
		assert mount_point is not None
		events.append(("unmount", Path(mount_point)))

	monkeypatch.setattr(module.pexpect, "spawn", FakeMacosProcess)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("//server/old", mounted_point))
	monkeypatch.setattr(module, "unmount_network_share", fake_unmount_network_share)

	module.mount_cifs_share("server", "share", mount_point, "user", "secret")

	assert events == [
		("unmount", mounted_point),
		("mount", f"mount_smbfs //user@server/share {mounted_point}"),
	]


@pytest.mark.macos
def test_macos_unmount_network_share_uses_umount_for_existing_mount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)
	run_command_calls: list[tuple[list[str], int]] = []
	mount_point = tmp_path / "mnt"
	mounted_point = mount_point.absolute()

	def fake_run_command(command: list[str], *, timeout: int) -> None:
		run_command_calls.append((command, timeout))

	monkeypatch.setattr(module, "run_command", fake_run_command)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("//server/share", mounted_point))

	module.unmount_network_share(mount_point)

	assert run_command_calls == [(["umount", str(mount_point.absolute())], 15)]


@pytest.mark.macos
def test_macos_unmount_network_share_skips_missing_mount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	module = _load_macos_module(monkeypatch)
	run_command_calls: list[list[str]] = []

	monkeypatch.setattr(module, "run_command", lambda command, *, timeout: run_command_calls.append(command))
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)

	module.unmount_network_share(tmp_path / "mnt")

	assert run_command_calls == []


@pytest.mark.macos
def test_macos_module_rejects_non_macos_platform(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(sys, "platform", "linux")
	sys.modules.pop("opsi.system.network._macos", None)

	with pytest.raises(opsi.system.network.OperatingSystemUnsupportedError, match="macOS"):
		importlib.import_module("opsi.system.network._macos")


@pytest.mark.windows
def test_windows_mount_cifs_share_calls_net_use_add(monkeypatch: pytest.MonkeyPatch) -> None:
	module, net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)

	module.mount_cifs_share("server", "share", "Z:", r"DOMAIN\\user", "secret")

	assert net_use_add_calls == [
		(
			None,
			2,
			{
				"remote": "\\\\server\\share",
				"local": "z:",
				"password": "secret",
				"username": "user",
				"domainname": "DOMAIN",
				"asg_type": 0,
			},
		)
	]


@pytest.mark.windows
def test_windows_mount_cifs_share_unmounts_existing_mount_before_mounting(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)
	events: list[tuple[str, Path | tuple[Any, ...]]] = []

	def fake_net_use_add(*args: Any) -> None:
		events.append(("mount", args))

	def fake_unmount_network_share(mount_point: Path | str | None) -> None:
		assert mount_point is not None
		events.append(("unmount", Path(mount_point)))

	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("\\\\server\\old", Path("z:")))
	monkeypatch.setattr(module, "unmount_network_share", fake_unmount_network_share)
	monkeypatch.setattr(module.win32net, "NetUseAdd", fake_net_use_add)

	module.mount_cifs_share("server", "share", "Z:", "user", "secret")

	assert events == [
		("unmount", Path("z:")),
		(
			"mount",
			(
				None,
				2,
				{
					"remote": "\\\\server\\share",
					"local": "z:",
					"password": "secret",
					"username": "user",
					"asg_type": 0,
				},
			),
		),
	]


@pytest.mark.windows
def test_windows_mount_webdav_share_installs_ca_and_adds_connection(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)
	ca_cert: Any = object()
	installed_certs: list[Any] = []
	add_connection_calls: list[tuple[Any, ...]] = []

	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)
	monkeypatch.setattr(module, "install_ca", lambda cert: installed_certs.append(cert))
	monkeypatch.setattr(module.win32wnet, "WNetAddConnection2", lambda *args: add_connection_calls.append(args))

	module.mount_webdav_share("server", 4447, "/depot", "Z:", "user", "secret", ca_cert)

	assert installed_certs == [ca_cert]
	assert add_connection_calls == [(1, "z:", "https://server:4447/depot", None, "user", "secret", 0)]


@pytest.mark.windows
def test_windows_mount_webdav_share_unmounts_existing_mount_before_mounting(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)
	events: list[tuple[str, Path | tuple[Any, ...]]] = []

	def fake_unmount_network_share(mount_point: Path | str | None) -> None:
		assert mount_point is not None
		events.append(("unmount", Path(mount_point)))

	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("https://server:4447/old", Path("z:")))
	monkeypatch.setattr(module, "unmount_network_share", fake_unmount_network_share)
	monkeypatch.setattr(module.win32wnet, "WNetAddConnection2", lambda *args: events.append(("mount", args)))

	module.mount_webdav_share("server", 4447, "depot", "Z:", "user", "secret")

	assert events == [
		("unmount", Path("z:")),
		("mount", (1, "z:", "https://server:4447/depot", None, "user", "secret", 0)),
	]


@pytest.mark.windows
def test_windows_get_mount_returns_none_for_empty_mount_list(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)

	assert module._get_mount(mount_point="Z:") is None


@pytest.mark.windows
def test_windows_get_mount_finds_wnet_connection_by_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)

	monkeypatch.setattr(module.win32wnet, "WNetGetConnection", lambda _mount_point: r"\\server@SSL\DavWWWRoot\share", raising=False)

	assert module._get_mount(mount_point="Z:") == (r"\\server@SSL\DavWWWRoot\share", Path("z:"))


@pytest.mark.windows
def test_windows_get_mount_finds_wnet_connection_by_device(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)

	def fake_wnet_get_connection(mount_point: str) -> str:
		if mount_point == "x:":
			return r"\\server@SSL\DavWWWRoot\share"
		raise OSError("No network connection")

	monkeypatch.setattr(module.win32wnet, "WNetGetConnection", fake_wnet_get_connection, raising=False)

	assert module._get_mount(device=r"\\server@SSL\DavWWWRoot\share") == (r"\\server@SSL\DavWWWRoot\share", Path("x:"))


@pytest.mark.windows
@pytest.mark.parametrize("mount_point", ["z", "zz:", "/mnt/share"])
def test_windows_mount_cifs_share_requires_drive_letter(monkeypatch: pytest.MonkeyPatch, mount_point: str) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: None)

	with pytest.raises(ValueError, match="Mount point must be a drive letter"):
		module.mount_cifs_share("server", "share", mount_point, "user", "secret")


@pytest.mark.windows
@pytest.mark.parametrize(
	("mount_exists", "expected_net_use_del_calls"),
	[
		(True, [(None, "z:", 2)]),
		(False, []),
	],
)
def test_windows_unmount_network_share_calls_net_use_del_for_existing_mount(
	monkeypatch: pytest.MonkeyPatch,
	mount_exists: bool,
	expected_net_use_del_calls: list[tuple[None, str, int]],
) -> None:
	module, _net_use_add_calls, net_use_del_calls = _load_windows_module(monkeypatch)
	monkeypatch.setattr(module, "_get_mount", lambda **_kwargs: ("\\\\server\\share", Path("z:")) if mount_exists else None)

	module.unmount_network_share("Z:")

	assert net_use_del_calls == expected_net_use_del_calls


@pytest.mark.windows
def test_windows_unmount_network_share_requires_drive_letter(monkeypatch: pytest.MonkeyPatch) -> None:
	module, _net_use_add_calls, _net_use_del_calls = _load_windows_module(monkeypatch)

	with pytest.raises(ValueError, match="Mount point must be a drive letter"):
		module.unmount_network_share(None)
