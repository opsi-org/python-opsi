# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import shutil
import sys
from pathlib import Path

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "linux":
	raise OperatingSystemUnsupportedError("This module is only supported on Linux")

from cryptography import x509

from opsi.crypt.secret import SecretAlphabet, generate_secret
from opsi.crypt.ssl import as_pem
from opsi.logging import get_logger, secret_filter
from opsi.process import run_command
from opsi.system.file.temp import TempDir, TempFile

logger = get_logger("opsi")


def _get_mount(device: str | None = None, mount_point: Path | str | None = None) -> tuple[str, Path] | None:
	"""Check if a device is mounted on Linux and return the device and mount point."""
	if not device and not mount_point:
		raise ValueError("Either device or mount_point must be provided")
	if mount_point:
		mount_point = str(Path(mount_point).resolve())

	dev_or_mountpoint = (device or str(mount_point)).lower()
	for line in Path("/proc/mounts").read_text().splitlines():
		(dev, mountpoint) = line.strip().split(" ", 2)[:2]
		if dev_or_mountpoint in (dev, mountpoint):
			return dev, Path(mountpoint)
	return None


def mount_cifs_share(
	address: str,
	share: str,
	mount_point: Path | str,
	username: str,
	password: str,
	*,
	read_only: bool = False,
	dir_mode: int | None = None,
	file_mode: int | None = None,
) -> None:
	"""Mount a CIFS share on Linux."""
	secret_filter.add_secrets(password)
	remote = f"//{address}/{share}"
	mount_point = Path(mount_point).absolute()
	domain = None
	if "\\" in username:
		import re

		username = re.sub(r"\\+", r"\\", username)
		(domain, username) = username.split("\\", 1)
		if '"' in domain:
			raise ValueError("Domain cannot contain double quotes")

	mount_point.mkdir(parents=True, exist_ok=True)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	logger.info("Mounting CIFS share '%s' to '%s' with username '%s'", remote, mount_point, username)

	with TempFile(content=f"username={username or ''}\npassword={password or ''}\n") as credentials_file:
		mount_options = [f"credentials={credentials_file.path}"]
		if domain:
			mount_options.append(f"domain={domain}")
		if read_only:
			mount_options.append("ro")
		if dir_mode is not None:
			mount_options.append(f"dir_mode={dir_mode:04o}")
		if file_mode is not None:
			mount_options.append(f"file_mode={file_mode:04o}")
		mount_command = ["mount", "-t", "cifs", remote, str(mount_point), "-o", ",".join(mount_options)]
		run_command(mount_command, environment={"LC_ALL": "C"}, timeout=15)


def mount_webdav_share(
	address: str,
	port: int,
	path: str,
	mount_point: Path | str,
	username: str,
	password: str,
	*,
	read_only: bool = False,
	dir_mode: int | None = None,
	file_mode: int | None = None,
	ca_cert: x509.Certificate | None = None,
) -> None:
	secret_filter.add_secrets(password)
	rclone = shutil.which("opsi-rclone") or shutil.which("rclone")
	if not rclone:
		raise RuntimeError("rclone is required to mount WebDAV shares")

	url = f"https://{address}:{port}/{path.lstrip('/')}"
	mount_point = Path(mount_point).absolute()
	mount_point.mkdir(parents=True, exist_ok=True)

	if current_mount := _get_mount(mount_point=mount_point):
		logger.info("'%s' is already mounted on '%s', unmounting first", current_mount[0], current_mount[1])
		unmount_network_share(current_mount[1])

	obscured_password = run_command([rclone, "obscure", "-"], timeout=10, stdin=f"{password}\n").get_stdout_text().strip()
	secret_filter.add_secrets(obscured_password)

	share_name = generate_secret(length=8, alphabet=SecretAlphabet.HEXDIGITS)

	logger.info("Mounting WebDAV share '%s' to '%s' with username '%s'", url, mount_point, username)
	with TempDir() as temp_dir:
		config_file = temp_dir / "rclone.conf"
		config_file.write_text(
			f"[{share_name}]\ntype = webdav\nurl = {url}\nvendor = other\nuser = {username}\npass = {obscured_password}\n",
			encoding="utf-8",
		)
		command = [
			rclone,
			"mount",
			"--config",
			str(config_file),
			"--daemon",
			"--vfs-cache-mode",
			"writes",
			"--use-cookies",
		]
		if read_only:
			command.append("--read-only")
		if dir_mode is not None:
			command.append(f"--dir-perms={dir_mode:04o}")
		if file_mode is not None:
			command.append(f"--file-perms={file_mode:04o}")
		if ca_cert:
			ca_cert_file = temp_dir / "ca_cert.pem"
			ca_cert_file.write_text(as_pem(ca_cert), encoding="utf-8")
			command.extend(["--ca-cert", str(ca_cert_file)])
		command.extend([f"{share_name}:", str(Path(mount_point).absolute())])
		run_command(command, timeout=15)


def unmount_network_share(mount_point: Path | str | None) -> None:
	"""Unmount a network share mount point on Linux."""
	if mount_point is None:
		raise ValueError("Either device or mount_point must be provided")

	mount_point = Path(mount_point).absolute()
	if not _get_mount(mount_point=mount_point):
		logger.info("Mount point '%s' is not mounted, skipping unmount", mount_point)
		return

	logger.info("Unmounting mount point '%s'", mount_point)
	unmount_command = ["umount", str(mount_point)]
	run_command(unmount_command, timeout=15)
