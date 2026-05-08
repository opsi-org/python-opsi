# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pyzsync import create_zsync_file

from opsi.crypt.hash import compute_file_hash
from opsi.logging import get_logger
from opsi.util.pattern import MappedStrEnum
import enum

logger = get_logger("opsi")


class PackageContentFileEntryType(MappedStrEnum):
	DIRECTORY = "directory"
	FILE = "file"
	SYMLINK = "symlink"

	_NAME = enum.nonmember("package content file entry type")
	_ALIASES = enum.nonmember({"d": "directory", "f": "file", "l": "symlink"})

	@property
	def file_value(self) -> str:
		return {"directory": "d", "file": "f", "symlink": "l"}[self.value]


@dataclass
class PackageContentFileEntry:
	type: PackageContentFileEntryType
	filename: str
	size: int = 0
	target: str | None = None
	md5sum: str | None = None


def create_package_content_file(base_dir: Path, *, links_as_links: bool = True) -> Path:
	def handle_directory(path: Path) -> PackageContentFileEntry:
		logger.trace("Processing '%s' as directory", path)
		return PackageContentFileEntry(type=PackageContentFileEntryType.DIRECTORY, filename=path.relative_to(base_dir).as_posix())

	def handle_file(path: Path) -> PackageContentFileEntry:
		logger.trace("Processing '%s' as file", path)
		return PackageContentFileEntry(
			type=PackageContentFileEntryType.FILE,
			filename=path.relative_to(base_dir).as_posix(),
			size=path.stat().st_size,
			md5sum=compute_file_hash(path, algorithm="md5"),
		)

	def handle_symlink(path: Path) -> PackageContentFileEntry:
		logger.trace("Processing '%s' as symlink", path)
		target = path.resolve()
		if target.is_relative_to(base_dir):
			target_str = target.relative_to(base_dir).as_posix()
		else:
			target_str = "/" + target.relative_to(base_dir.parent).as_posix()
		return PackageContentFileEntry(
			type=PackageContentFileEntryType.SYMLINK, filename=path.relative_to(base_dir).as_posix(), target=target_str
		)

	package_content_file = base_dir / f"{base_dir.name}.files"
	package_content_file.unlink(missing_ok=True)
	logger.info("Creating package content file %s", package_content_file)
	lines = []

	try:
		for path in base_dir.rglob("*", recurse_symlinks=not links_as_links):
			try:
				if path.is_symlink() and links_as_links:
					entry = handle_symlink(path)
				elif path.is_dir():
					entry = handle_directory(path)
				else:
					entry = handle_file(path)

				additional = ""
				if entry.target:
					additional = f" '{entry.target.replace("'", "\\'")}'"
				elif entry.md5sum:
					additional = f" {entry.md5sum}"

				lines.append(f"{entry.type.file_value} '{entry.filename.replace("'", "\\'")}' {entry.size}{additional}")
			except Exception as err:
				logger.warning(err, exc_info=True)

		lines.sort()
		package_content_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")

	except Exception as err:
		logger.error(err, exc_info=True)
		raise RuntimeError(f"Failed to create package content file of directory '{base_dir}': {err}") from err
	return package_content_file


def parse_package_content_file(file: Path) -> list[PackageContentFileEntry]:
	"""
	Parse a package content file into structured entries.

	Parameters
	----------
	file : Path
		The package content file to parse.

	Returns
	-------
	list[PackageContentFileEntry]
		The parsed package content entries in file order.
	"""

	def split_quoted_value(value: str) -> tuple[str, str]:
		"""Split a quoted package content value from the remaining line content."""

		if not value.startswith("'"):
			raise ValueError(f"Invalid quoted value in package content file '{file}': {value!r}")

		quote_end = value.find("'", 1)
		while quote_end != -1 and value[quote_end - 1] == "\\":
			quote_end = value.find("'", quote_end + 1)
		if quote_end == -1:
			raise ValueError(f"Invalid quoted value in package content file '{file}': {value!r}")

		next_index = quote_end + 1
		if next_index == len(value):
			remaining = ""
		elif value[next_index] == " ":
			remaining = value[next_index + 1 :]
		else:
			raise ValueError(f"Invalid quoted value in package content file '{file}': {value!r}")

		return value[1:quote_end].replace("\\'", "'"), remaining

	entries = []
	with file.open("r", encoding="utf-8") as file_handle:
		for line in file_handle:
			stripped_line = line.strip()
			if not stripped_line:
				continue

			try:
				entry_type_str, remaining = stripped_line.split(None, 1)
			except ValueError:
				logger.warning("Skipping invalid line in package content file '%s': %s", file, stripped_line)
				continue

			try:
				entry_type = PackageContentFileEntryType(entry_type_str)
			except ValueError:
				logger.warning("Unknown entry type '%s' in package content file '%s'", entry_type_str, file)
				continue

			filename, remaining = split_quoted_value(remaining)
			size_value, separator, additional = remaining.partition(" ")
			if not size_value:
				raise ValueError(f"Invalid entry in package content file '{file}': {stripped_line!r}")

			size = int(size_value)
			additional = additional if separator else ""
			target = None
			md5 = None

			if entry_type == PackageContentFileEntryType.FILE:
				md5 = additional
			elif entry_type == PackageContentFileEntryType.SYMLINK:
				target, remaining = split_quoted_value(additional)
				if remaining:
					raise ValueError(f"Invalid symlink target in package content file '{file}': {stripped_line!r}")

			entries.append(
				PackageContentFileEntry(
					type=entry_type,
					filename=filename,
					size=size,
					target=target,
					md5sum=md5,
				)
			)

	return entries


def create_package_md5_file(
	package_path: Path, filename: Path | None = None, progress_callback: Callable[[int, int], None] | None = None
) -> Path:
	if not filename:
		filename = Path(f"{package_path}.md5")
	file_hash = compute_file_hash(package_path, algorithm="md5", progress_callback=progress_callback)
	filename.write_text(file_hash, encoding="utf-8", newline="")
	return filename


def create_package_zsync_file(
	package_path: Path, filename: Path | None = None, progress_callback: Callable[[int, int], None] | None = None
) -> Path:
	if not filename:
		filename = Path(f"{package_path}.zsync")
	create_zsync_file(file=package_path, zsync_file=filename, legacy_mode=True, progress_callback=progress_callback)
	return filename
