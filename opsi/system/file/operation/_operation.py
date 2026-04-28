from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from opsi.retry import Retry, RetryConfig, get_retry_config

LinkType = Literal["symlink", "hardlink"]


def _delete_attempt(path: Path, missing_ok: bool) -> None:
	if path.is_symlink() or path.is_file():
		path.unlink()
	else:
		shutil.rmtree(path)


def delete(path: Path | str, *, missing_ok: bool = False, retry_config: RetryConfig | None = None) -> None:
	"""
	Delete a file, link, or directory recursively if it exists.

	Parameters
	----------
	path : Path | str
		The filesystem path to delete. Symbolic links are deleted as links; their targets are not traversed.
	missing_ok : bool, default: False
		If True, do not raise an error if the path does not exist.
	retry_config : RetryConfig, optional
		Configuration for automatic retry behavior on failure. If None, uses the default retry configuration for file I/O operations.
	"""
	path = Path(path)
	# Checking for existence without retry
	if not path.is_symlink() and not path.exists():
		if missing_ok:
			return
		raise FileNotFoundError(path)

	retry_config = retry_config or get_retry_config("file_io")
	for attempt in Retry(retry_config):
		with attempt:
			_delete_attempt(path, missing_ok)


def _link_attempt(link_path: Path, target: Path, link_type: LinkType, target_is_directory: bool | None = None) -> None:
	if link_type == "symlink":
		if target_is_directory is not None:
			link_path.symlink_to(target, target_is_directory=target_is_directory)
		else:
			link_path.symlink_to(target, target_is_directory=target.is_dir())
		return
	if link_type == "hardlink":
		link_path.hardlink_to(target)
		return
	raise ValueError(f"Invalid link type: {link_type}")


def link(
	link_path: Path | str,
	target: Path | str,
	*,
	link_type: LinkType = "symlink",
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
	link_type : Literal["symlink", "hardlink"]
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
	if link_type not in ("symlink", "hardlink"):
		raise ValueError(f"Invalid link type: {link_type}")
	if link_path.is_symlink() or link_path.exists():
		if not overwrite:
			raise FileExistsError(link_path)
		delete(link_path, retry_config=retry_config)
	if link_type == "hardlink" and not target.exists():
		raise FileNotFoundError(target)

	retry_config = retry_config or get_retry_config("file_io")
	for attempt in Retry(retry_config):
		with attempt:
			_link_attempt(link_path, target, link_type, target_is_directory)
