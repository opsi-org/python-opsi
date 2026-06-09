# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import re
import sys
from pathlib import Path
from shlex import join

import pexpect

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "darwin":
	raise OperatingSystemUnsupportedError("This module is only supported on macOS")

from cryptography import x509

from opsi.logging import get_logger, secret_filter
from opsi.process import run_command
from opsi.system.certificate_store import install_ca

logger = get_logger("opsi")


def _get_mount(device: str | None = None, mount_point: Path | str | None = None) -> tuple[str, Path] | None:
	"""Check if a device is mounted on macOS and return the device and mount point."""
	if not device and not mount_point:
		raise ValueError("Either device or mount_point must be provided")
	if mount_point:
		mount_point = str(Path(mount_point).resolve())

	dev_or_mountpoint = (device or str(mount_point)).lower()
	regex = re.compile(r"^(\S+)\s+on\s+(\S+)\s")
	for line in run_command(["mount"], timeout=15).get_stdout_lines():
		line = line.strip()
		match = regex.match(line)
		if match and dev_or_mountpoint in (match.group(1).lower(), match.group(2).lower()):
			return match.group(1), Path(match.group(2))
	return None


def _run_mount_command(command: list[str], *, username: str | None, password: str) -> None:
	command_str = join(command)
	logger.info("Running mount command: %s", command_str)
	process = pexpect.spawn(command_str)
	if username:
		process.expect("Username.*: ", timeout=10)
		process.sendline(username)

	index = process.expect(["Password.*: ", pexpect.EOF], timeout=10)
	if index == 0:
		# It is possible that mount_smbfs caches a password and does not prompt for it again.
		process.sendline(password)
		process.expect(pexpect.EOF)
	output = process.before.decode("utf-8", "replace") if process.before else ""
	process.close()
	exit_code = process.exitstatus
	logger.debug("Command exit code is %s, output: %s", exit_code, output)
	if exit_code != 0:
		raise RuntimeError(f"Command {command!r} failed with exit code {exit_code}: {output}")


def mount_cifs_share(address: str, share: str, mount_point: Path | str, username: str, password: str) -> None:
	"""Mount a CIFS share on macOS."""
	secret_filter.add_secrets(password)
	mount_point = Path(mount_point).absolute()
	share = share.replace("\\", "/")
	if "\\" in username:
		username = re.sub(r"\\+", ";", username)
		if '"' in username:
			raise ValueError("Username cannot contain double quotes")

	remote = f"//{username}@{address}/{share}"
	mount_point.mkdir(parents=True, exist_ok=True)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	logger.info("Mounting CIFS share '%s' to '%s' with username '%s'", remote, mount_point, username)

	mount_command = ["mount_smbfs", remote, str(mount_point)]
	_run_mount_command(mount_command, username=None, password=password)


def mount_webdav_share(
	address: str, port: int, path: str, mount_point: Path | str, username: str, password: str, ca_cert: x509.Certificate | None = None
) -> None:
	secret_filter.add_secrets(password)
	mount_point = Path(mount_point).absolute()

	remote = f"https://{address}:{port}/{path.lstrip('/')}"
	mount_point.mkdir(parents=True, exist_ok=True)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	if ca_cert:
		install_ca(ca_cert)

	logger.info("Mounting WebDAV share '%s' to '%s' with username '%s'", remote, mount_point, username)
	mount_command = ["mount_webdav", "-i", remote, str(mount_point)]
	_run_mount_command(mount_command, username=username, password=password)


def unmount_network_share(mount_point: Path | str | None) -> None:
	"""Unmount a network share mount point on macOS."""
	if mount_point is None:
		raise ValueError("Either device or mount_point must be provided")

	mount_point = Path(mount_point).absolute()
	if not _get_mount(mount_point=mount_point):
		logger.info("Mount point '%s' is not mounted, skipping unmount", mount_point)
		return

	logger.info("Unmounting mount point '%s'", mount_point)
	unmount_command = ["umount", str(mount_point)]
	run_command(unmount_command, timeout=15)
