# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import shutil
from unittest.mock import patch

from opsi.system.file.temp import TempDir, TempFile, create_temp_dir, create_temp_file
from opsi.system.info import is_linux


def test_temp_dir():
	with TempDir() as temp_dir:
		assert temp_dir.exists()
		if is_linux():
			assert str(temp_dir).startswith("/tmp/opsi_temp_")
			assert temp_dir.stat().st_mode & 0o777 == 0o700
		(temp_dir / "sub1" / "sub2").mkdir(parents=True)
		(temp_dir / "sub1" / "sub2" / "file.txt").write_text("Temp file content")
		(temp_dir / "sub1" / "file2.txt").write_text("Another temp file")

	assert not temp_dir.exists()


def test_create_temp_dir():
	path = create_temp_dir()
	assert path.is_dir()
	shutil.rmtree(path)


def test_temp_dir_retry_on_io_error() -> None:
	create_attempt = 0
	delete_attempt = 0
	orig_create_attempt = TempDir._create_attempt
	orig_delete_attempt = TempDir._delete_attempt

	def side_effect_create(self) -> None:
		nonlocal create_attempt
		create_attempt += 1
		if create_attempt < 2:
			raise OSError("Create error")
		return orig_create_attempt(self)

	def side_effect_delete(self) -> None:
		nonlocal delete_attempt
		delete_attempt += 1
		if delete_attempt < 2:
			raise OSError("Delete error")
		return orig_delete_attempt(self)

	with (
		patch("opsi.system.file.temp._temp.TempDir._create_attempt", side_effect=side_effect_create, autospec=True),
		patch("opsi.system.file.temp._temp.TempDir._delete_attempt", side_effect=side_effect_delete, autospec=True),TempDir() as temp_dir
	):
		assert temp_dir.exists()

	assert create_attempt == 2
	assert delete_attempt == 2


def test_temp_file():
	with TempFile() as temp_file:
		assert temp_file.path.exists()
		if is_linux():
			assert str(temp_file.path).startswith("/tmp/opsi_temp_")
			assert temp_file.path.stat().st_mode & 0o777 == 0o600
		temp_file.path.write_text("OPSI")
		assert temp_file.path.read_text() == "OPSI"
	assert not temp_file.path.exists()

	temp_file = TempFile()
	temp_file.create(content="OPSI")
	with temp_file:
		assert temp_file.path.exists()
		assert temp_file.path.read_text() == "OPSI"
	assert not temp_file.path.exists()


def test_temp_file_retry_on_io_error() -> None:
	create_attempt = 0
	delete_attempt = 0
	orig_create_attempt = TempFile._create_attempt
	orig_delete_attempt = TempFile._delete_attempt

	def side_effect_create(self) -> None:
		nonlocal create_attempt
		create_attempt += 1
		if create_attempt < 2:
			raise OSError("Create error")
		return orig_create_attempt(self)

	def side_effect_delete(self) -> None:
		nonlocal delete_attempt
		delete_attempt += 1
		if delete_attempt < 2:
			raise OSError("Delete error")
		return orig_delete_attempt(self)

	with (
		patch("opsi.system.file.temp._temp.TempFile._create_attempt", side_effect=side_effect_create, autospec=True),
		patch("opsi.system.file.temp._temp.TempFile._delete_attempt", side_effect=side_effect_delete, autospec=True),TempFile() as temp_file
	):
		assert temp_file.path.exists()

	assert create_attempt == 2
	assert delete_attempt == 2


def test_create_temp_file():
	path = create_temp_file()
	assert path.is_file()
	path.unlink()
