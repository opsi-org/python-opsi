# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import getpass
import os
import time
from unittest.mock import patch

try:
	import grp
except ModuleNotFoundError:  # not present for windows
	pass
import platform
import shutil
import tempfile
from pathlib import Path
from random import randbytes
from typing import Literal

import pytest
from hypothesis import given, settings
from hypothesis.strategies import binary, from_regex, sampled_from

from opsi.archive._common import (
	CPIO_EXTRACT_COMMAND,
	TAR_EXTRACT_COMMAND,
	ArchiveFile,
	ArchiveProgress,
	ArchiveProgressListener,
	create_archive,
	create_archive_external,
	create_archive_internal,
	decompress_command,
	extract_archive_external,
	extract_archive_internal,
	extract_command,
	get_archive_files,
	use_pigz,
)
from opsi.process import run_command
from opsi.sync.zsync import SOURCE_REMOTE, create_zsync_file, get_patch_instructions, read_zsync_file
from opsi.testing.helper import memory_usage_monitor, opsi_config

# File may not
# * contain slash/backslash path delimiters
FILENAME_REGEX = r"^[^/\\]{4,64}$"


class ProgressListener(ArchiveProgressListener):
	def __init__(self) -> None:
		self.percent_completed_vals: list[float] = []

	def progress_changed(self, progress: ArchiveProgress) -> None:
		# print(f"{progress.percent_completed:0.1f} %")
		self.percent_completed_vals.append(progress.percent_completed)


def make_source_files(path: Path) -> Path:
	source = path / "source"
	source.mkdir()
	(source / "test file with spaces").write_bytes(randbytes(100_000_000))
	(source / "#how^can°people`think,this´is'a good~idea#").write_bytes(randbytes(50_000_000))
	(source / "test'dir").mkdir()
	(source / "test'dir" / "testfileindir").write_bytes(randbytes(10_000_000))
	(source / "Empty Dir").mkdir()
	(source / "dir" / "in" / "dir").mkdir(parents=True)
	if platform.system().lower() != "windows":  # windows does not like ?, < and > characters
		(source / "test'dir" / 'test"file$in€dir<with>special?').write_bytes(randbytes(1000))
	(source / "some_dir").mkdir()
	os.symlink(source / "some_dir", source / "link_to_some_dir")
	(source / "some_file").write_bytes(randbytes(100))
	os.symlink(source / "some_file", source / "link_to_some_file")
	return source


def test_archive_progress() -> None:
	listener = ProgressListener()
	assert listener.percent_completed_vals == []

	progress = ArchiveProgress(100)
	progress.set_completed(10)
	assert listener.percent_completed_vals == []

	time.sleep(ArchiveProgress._notification_interval + 0.1)
	progress.set_completed(15)
	assert listener.percent_completed_vals == []

	time.sleep(ArchiveProgress._notification_interval + 0.1)
	progress.register_progress_listener(listener)
	progress.set_completed(20)
	assert listener.percent_completed_vals == [20.0]

	time.sleep(ArchiveProgress._notification_interval + 0.1)
	progress.unregister_progress_listener(listener)
	progress.set_completed(50)
	assert listener.percent_completed_vals == [20.0]

	# Test notification interval
	time.sleep(ArchiveProgress._notification_interval + 0.1)
	progress.set_completed(0)
	listener.percent_completed_vals.clear()
	progress.register_progress_listener(listener)
	assert listener.percent_completed_vals == []

	progress.set_completed(0)
	for _ in range(10):
		time.sleep(0.1)
		progress.advance(1)
	progress.set_completed(100)

	assert listener.percent_completed_vals[0] == 0
	assert listener.percent_completed_vals[-1] == 100.0
	assert len(listener.percent_completed_vals) < 5


@pytest.mark.linux
def test_use_pigz() -> None:
	class MockProcess:
		def __init__(self, output: str) -> None:
			self._output = output

		def get_output_text(self) -> str:
			return self._output

	use_pigz.cache_clear()
	with opsi_config({"packages.use_pigz": False}):
		assert not use_pigz()

	use_pigz.cache_clear()
	with opsi_config({"packages.use_pigz": True}), patch("opsi.archive._common.run_command", return_value=MockProcess("pigz 2.2.2")):
		assert not use_pigz()

	use_pigz.cache_clear()
	with opsi_config({"packages.use_pigz": True}), patch("opsi.archive._common.run_command", return_value=MockProcess("pigz 2.2.3")):
		assert use_pigz()


@pytest.mark.parametrize(
	"archive_name, archive_type, expected_command",
	(
		("file.tar", "tar", TAR_EXTRACT_COMMAND),
		("file.cpio", "cpio", CPIO_EXTRACT_COMMAND),
		("file.tar.gz", "tar", TAR_EXTRACT_COMMAND),
		("file.tar.bz2", "tar", TAR_EXTRACT_COMMAND),
		("file.tar.zst", "tar", TAR_EXTRACT_COMMAND),
		("file.tar", "cpio", TAR_EXTRACT_COMMAND),
		("file.cpio", "tar", CPIO_EXTRACT_COMMAND),
		("file", "tar", TAR_EXTRACT_COMMAND),
		("file", "cpio", CPIO_EXTRACT_COMMAND),
		("file.gz", "gz", None),
		("file", "", None),
	),
)
@pytest.mark.linux
def test_extract_command(tmp_path: Path, archive_name: str, archive_type: str, expected_command: str | None) -> None:
	archive_file = tmp_path / archive_name
	archive_src = tmp_path / "archive_src"
	archive_src.mkdir()
	test_file = archive_src / "testfile"
	test_file.write_bytes(b"test")

	if archive_type == "tar":
		shutil.which("tar") or pytest.skip("tar not available")
		run_command(["tar", "cvf", str(archive_file), str(archive_src)])
	elif archive_type == "cpio":
		shutil.which("cpio") or pytest.skip("cpio not available")
		data = run_command(["cpio", "--create", "--format", "crc"], stdin=f"{test_file}\n").get_stdout_bytes()
		archive_file.write_bytes(data)
	elif archive_type == "gz":
		archive_file.write_bytes(b"\x1f\x8b\x08")
	else:
		archive_file.write_bytes(b"test")

	if expected_command:
		assert extract_command(archive_file, "opsi.*") == f"{expected_command} 'opsi.*'"
	else:
		with pytest.raises(TypeError):
			extract_command(archive_file)


@pytest.mark.linux
def test_decompress_command(tmp_path: Path) -> None:
	use_pigz.cache_clear()
	with opsi_config({"packages.use_pigz": False}):
		gz_file = tmp_path / "file.gz"
		assert decompress_command(gz_file) == "gunzip --stdout --quiet --decompress"

	use_pigz.cache_clear()
	with opsi_config({"packages.use_pigz": True}):
		gz_file = tmp_path / "file.gz"
		assert decompress_command(gz_file) == "pigz --stdout --quiet --decompress"

	for ext in (".zstd", ".zst"):
		zst_file = tmp_path / f"file{ext}"
		with patch("shutil.which", return_value=False):
			with pytest.raises(RuntimeError, match="Zstdcat not available."):
				decompress_command(zst_file)
		with patch("shutil.which", return_value=True):
			assert decompress_command(zst_file) == "zstd --stdout --quiet --decompress"

	bz2_file = tmp_path / "file.bz2"
	assert decompress_command(bz2_file) == "bunzip2 --stdout --quiet --decompress"

	unknown_file = tmp_path / "file.unknown"
	with pytest.raises(RuntimeError, match=f"Unknown compression of file '{unknown_file}'"):
		decompress_command(unknown_file)


@pytest.mark.parametrize(
	"test_defect_link, follow_symlinks, test_excludes",
	(
		(False, True, False),
		(False, False, False),
		(True, True, False),
		(True, False, False),
		(False, False, True),
	),
)
def test_get_archive_files(tmp_path: Path, test_defect_link: bool, follow_symlinks: bool, test_excludes: bool) -> None:
	(tmp_path / "file1.dat").write_bytes(b"1234")
	(tmp_path / "file2.txt").write_bytes(b"12345678")
	(tmp_path / "Thumbs.db").touch()
	(tmp_path / ".git").mkdir()
	(tmp_path / ".git" / "index").touch()
	(tmp_path / "dir1").mkdir()
	(tmp_path / "dir1" / "thumbs.db").touch()
	(tmp_path / "dir2").mkdir()
	(tmp_path / "dir2" / "empty_dir").mkdir()
	(tmp_path / "dir2" / "file3.txt").touch()
	os.symlink(tmp_path / "dir1", tmp_path / "dir2" / "link_to_dir1")
	os.symlink(tmp_path / "file2.txt", tmp_path / "link_to_file2.txt")
	if test_defect_link:
		os.symlink(tmp_path / "non_existing_file", tmp_path / "link_to_non_existing_file")

	exclude_dirs = ["/.git"] if test_excludes else []
	exclude_files = ["[Tt]humbs.db", "*.txt"] if test_excludes else []
	if test_defect_link and follow_symlinks:
		with pytest.raises(FileNotFoundError):
			list(get_archive_files(tmp_path, follow_symlinks=follow_symlinks, exclude_dirs=exclude_dirs, exclude_files=exclude_files))
		return

	files = list(get_archive_files(tmp_path, follow_symlinks=follow_symlinks, exclude_dirs=exclude_dirs, exclude_files=exclude_files))

	assert (
		ArchiveFile(
			path=tmp_path / "file1.dat",
			size=4,
			archive_path=Path("file1.dat"),
		)
		in files
	)

	file = ArchiveFile(
		path=tmp_path / "file2.txt",
		size=8,
		archive_path=Path("file2.txt"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	file = ArchiveFile(
		path=tmp_path / "Thumbs.db",
		size=0,
		archive_path=Path("Thumbs.db"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	file = ArchiveFile(
		path=tmp_path / ".git/index",
		size=0,
		archive_path=Path(".git/index"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	file = ArchiveFile(
		path=tmp_path / "dir1/thumbs.db",
		size=0,
		archive_path=Path("dir1/thumbs.db"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	assert (
		ArchiveFile(
			path=tmp_path / "dir2/empty_dir",
			size=0,
			archive_path=Path("dir2/empty_dir"),
		)
		in files
	)

	file = ArchiveFile(
		path=tmp_path / "dir2/file3.txt",
		size=0,
		archive_path=Path("dir2/file3.txt"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	if follow_symlinks:
		file = ArchiveFile(
			path=tmp_path / "dir2/link_to_dir1/thumbs.db",
			size=0,
			archive_path=Path("dir2/link_to_dir1/thumbs.db"),
		)
		if test_excludes:
			assert file not in files
		else:
			assert file in files
	else:
		assert (
			ArchiveFile(
				path=tmp_path / "dir2/link_to_dir1",
				size=0,
				archive_path=Path("dir2/link_to_dir1"),
			)
			in files
		)

	file = ArchiveFile(
		path=tmp_path / "link_to_file2.txt",
		size=8 if follow_symlinks else 0,
		archive_path=Path("link_to_file2.txt"),
	)
	if test_excludes:
		assert file not in files
	else:
		assert file in files

	if test_defect_link:
		assert (
			ArchiveFile(
				path=tmp_path / "link_to_non_existing_file",
				size=0,
				archive_path=Path("link_to_non_existing_file"),
			)
			in files
		)


# Cannot use function scoped fixtures with hypothesis
@pytest.mark.linux
@settings(deadline=10_000)
@given(from_regex(FILENAME_REGEX), binary(max_size=4096), sampled_from((True, False)), sampled_from(("zstd", "bz2", "gz")))
def test_archive_hypothesis(filename: str, data: bytes, internal: bool, compression: Literal["zstd", "bz2", "gz"]) -> None:
	with tempfile.TemporaryDirectory() as tempdir:
		filename = filename.replace("\x00", "").replace("\n", "")
		if filename.startswith("-"):
			filename = filename[1:]
		tmp_path = Path(tempdir)
		source = tmp_path / "source"
		source.mkdir()
		file_path = source / filename
		file_path.write_bytes(data)
		archive = tmp_path / f"archive.tar.{compression}"
		create_archive = create_archive_internal if internal else create_archive_external
		files = list(get_archive_files(source))
		if filename.endswith("~"):
			assert not files
		else:
			create_archive(archive, files, compression=compression)
			destination = tmp_path / "destination"
			extract_archive = extract_archive_internal if internal else extract_archive_external
			extract_archive(archive, destination)
			src_contents = [file.relative_to(source) for file in source.rglob("*")]
			dst_contents = [file.relative_to(destination) for file in destination.rglob("*")]
			src_contents.sort()
			dst_contents.sort()
			# print("src:", src_contents)
			# print("dst:", dst_contents)
			assert dst_contents == src_contents


@pytest.mark.linux
@pytest.mark.parametrize(
	"compression, dereference",
	(("zstd", False), ("zstd", True), ("bz2", False), ("gz", False)),
)
def test_archive_external(tmp_path: Path, compression: Literal["zstd", "bz2", "gz"], dereference: bool) -> None:
	source = make_source_files(tmp_path)
	with memory_usage_monitor(interval=0.01) as mem_monitor:
		try:
			# Setting group ownership of source to adm group
			shutil.chown(source, None, "adm")
		except PermissionError:
			pass

		archive = tmp_path / f"archive.tar.{compression}"
		progress_listener = ProgressListener()

		files = list(get_archive_files(source, follow_symlinks=dereference))
		create_archive_external(archive, files, compression=compression, dereference=dereference, progress_listener=progress_listener)

		assert progress_listener.percent_completed_vals[-1] == 100
		for idx, val in enumerate(progress_listener.percent_completed_vals):
			if idx + 1 < len(progress_listener.percent_completed_vals):
				assert val <= progress_listener.percent_completed_vals[idx + 1]

		# Ownership of archive should be current user group
		assert archive.stat().st_gid == grp.getgrnam(getpass.getuser()).gr_gid

		try:
			# Setting group ownership of source to adm group
			shutil.chown(archive, None, "adm")
		except PermissionError:
			pass

		destination = tmp_path / "destination"
		progress_listener = ProgressListener()

		extract_archive_external(archive, destination, progress_listener=progress_listener)

		assert progress_listener.percent_completed_vals[-1] == 100
		for idx, val in enumerate(progress_listener.percent_completed_vals):
			if idx + 1 < len(progress_listener.percent_completed_vals):
				assert val <= progress_listener.percent_completed_vals[idx + 1]

		# Ownership of archive should be current user group
		assert destination.stat().st_gid == grp.getgrnam(getpass.getuser()).gr_gid

		for file in source.rglob("*"):
			destination_file = destination / file.relative_to(source)
			assert destination_file.exists()
			if dereference:
				assert not destination_file.is_symlink()
			else:
				assert file.is_symlink() == destination_file.is_symlink()

		mem_monitor.stop()
		mem_monitor.print_stats()
		assert mem_monitor.max_increase_rss < 20_000_000


@pytest.mark.parametrize(
	"compression, dereference",
	(("zstd", False), ("zstd", True), ("bz2", False), ("gz", False)),
)
def test_archive_internal(tmp_path: Path, compression: Literal["zstd", "bz2", "gz"], dereference: bool) -> None:
	source = make_source_files(tmp_path)
	with memory_usage_monitor(interval=0.01) as mem_monitor:
		archive = tmp_path / f"archive.tar.{compression}"
		progress_listener = ProgressListener()

		files = list(get_archive_files(source, follow_symlinks=dereference))
		create_archive_internal(archive, files, compression=compression, dereference=dereference, progress_listener=progress_listener)

		assert progress_listener.percent_completed_vals[-1] == 100
		for idx, val in enumerate(progress_listener.percent_completed_vals):
			if idx + 1 < len(progress_listener.percent_completed_vals):
				assert val <= progress_listener.percent_completed_vals[idx + 1]

		destination = tmp_path / "destination"
		progress_listener = ProgressListener()

		extract_archive_internal(archive, destination, progress_listener=progress_listener)

		assert progress_listener.percent_completed_vals[-1] == 100
		for idx, val in enumerate(progress_listener.percent_completed_vals):
			if idx + 1 < len(progress_listener.percent_completed_vals):
				assert val <= progress_listener.percent_completed_vals[idx + 1]

		for file in source.rglob("*"):
			destination_file = destination / file.relative_to(source)
			assert destination_file.exists()
			if dereference:
				assert not destination_file.is_symlink()
			else:
				assert file.is_symlink() == destination_file.is_symlink()

		mem_monitor.stop()
		mem_monitor.print_stats()
		assert mem_monitor.max_increase_rss < 20_000_000


@pytest.mark.linux
@pytest.mark.parametrize(
	"mode, compression, expect_min_percent_same",
	(
		# external
		("external", None, 85),
		("external", "zstd", 85),
		("external", "bz2", 0),
		("external", "gz", 72),
		# internal
		("internal", None, 85),
		("internal", "zstd", 85),
		("internal", "bz2", 0),
		("internal", "gz", 55),
		# auto
		("auto", None, 85),
		("auto", "zstd", 85),
		("auto", "bz2", 0),
		("auto", "gz", 74),
	),
)
def test_syncable(
	tmp_path: Path, mode: Literal["external", "internal"], compression: Literal["zstd", "bz2", "gz"], expect_min_percent_same: float
) -> None:
	create_archive_func = create_archive
	if mode == "external":
		create_archive_func = create_archive_external
	elif mode == "internal":
		create_archive_func = create_archive_internal

	source = tmp_path / "source"
	source.mkdir()

	(source / "file1.dat").write_bytes(randbytes(100_000))
	(source / "file2.dat").write_bytes(randbytes(10_000))
	archive_old = tmp_path / f"archive-old.tar.{compression}"
	create_archive_func(archive_old, list(get_archive_files(source)), compression=compression)

	# Keep file1.dat, change file2.dat
	(source / "file2.dat").write_bytes(randbytes(10_000))
	archive_new = tmp_path / f"archive-new.tar.{compression}"
	zsync_new = tmp_path / f"archive-new.tar.{compression}.zsync"
	create_archive_func(archive_new, list(get_archive_files(source)), compression=compression)
	create_zsync_file(archive_new, zsync_new)

	zsync_info = read_zsync_file(zsync_new)
	instructions = get_patch_instructions(zsync_info, archive_old)

	same_bytes = sum([i.size for i in instructions if i.source != SOURCE_REMOTE])
	percent_same = same_bytes * 100 / zsync_info.length

	print(mode, compression, expect_min_percent_same, percent_same)

	assert percent_same >= expect_min_percent_same
