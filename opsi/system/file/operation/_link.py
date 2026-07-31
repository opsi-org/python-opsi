# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from pathlib import Path

from opsi.retry import Retry, RetryConfig, RetryConfigType, get_retry_config
from opsi.system.file.operation._common import LinkType
from opsi.system.info import is_posix, is_windows

if is_posix():
	from opsi.system.file.operation._posix import get_link_target
elif is_windows():
	from opsi.system.file.operation._windows import get_link_target

__all__ = ["get_link_target", "link"]


def _link_attempt(link_path: Path, target: Path, link_type: LinkType, target_is_directory: bool | None = None) -> None:
	if link_type == LinkType.SYMLINK:
		if target_is_directory is not None:
			link_path.symlink_to(target, target_is_directory=target_is_directory)
		else:
			link_path.symlink_to(target, target_is_directory=target.is_dir())
		return
	if link_type == LinkType.HARDLINK:
		link_path.hardlink_to(target)
		return
	if link_type == LinkType.JUNCTION:
		from ._windows import create_junction

		create_junction(link_path, target)
		return
	raise ValueError(f"Invalid link type: {link_type}")


def link(
	link_path: Path | str,
	target: Path | str,
	*,
	link_type: LinkType | str = LinkType.SYMLINK,
	target_is_directory: bool | None = None,
	overwrite: bool = False,
	retry_config: RetryConfig | None = None,
) -> None:
	"""
	Create a symbolic link or hard link.

	Parameters
	----------
	target : Path | str
		The target path the link should point to.
	link_path : Path | str
		The path of the link to create.
	link_type : LinkType | str, default: LinkType.SYMLINK
		The type of link to create.
	target_is_directory : bool, optional
		On Windows, a symbolic link is created as either a file link or a directory link,
		and its type does not change based on the target later.
		If the target already exists, the symlink is created with the same type as the target.
		If the target does not exist, the symlink is created as a directory when `target_is_directory` is True,
		and as a file symlink (the default) otherwise.
		On non-Windows systems, the `target_is_directory` parameter is ignored.
	overwrite : bool, default: False
		If True, overwrite the link if it already exists. If False, raise a FileExistsError if the link already exists.
	retry_config : RetryConfig, optional
		Configuration for automatic retry behavior on failure. If None, uses the default retry configuration for file I/O operations.

	Raises
	------
	FileExistsError
		If link_path already exists and overwrite is False.
	FileNotFoundError
		If a hardlink is requested but the target does not exist.
	ValueError
		If link_type is invalid.
	"""
	target = Path(target)
	link_path = Path(link_path)
	link_type = LinkType(link_type)

	if link_type == LinkType.JUNCTION and not is_windows():
		raise ValueError("Junctions are only supported on Windows")
	if link_path.is_symlink() or link_path.exists():
		if not overwrite:
			raise FileExistsError(link_path)
		from opsi.system.file.operation import delete

		delete(link_path, retry_config=retry_config)
	if link_type == LinkType.HARDLINK and not target.exists():
		raise FileNotFoundError(target)

	retry_config = retry_config or get_retry_config(RetryConfigType.FILE_IO)
	for attempt in Retry(retry_config):
		with attempt:
			_link_attempt(link_path, target, link_type, target_is_directory)


def get_link_type(link_path: Path | str) -> LinkType | None:
	link_path = Path(link_path)
