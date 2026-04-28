import os
from contextlib import nullcontext
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from opsi.system.file.operation import delete, link
from opsi.system.file.operation._operation import LinkType, _delete_attempt, _link_attempt


def test_delete_file(tmp_path: Path) -> None:
	test_file = tmp_path / "test.txt"
	test_file.write_text("opsi", encoding="utf-8")

	delete(test_file)

	assert not test_file.exists()

	with pytest.raises(FileNotFoundError):
		delete(test_file)

	delete(test_file, missing_ok=True)  # Should not raise an error


def test_delete_dir(tmp_path: Path) -> None:
	test_dir = tmp_path / "directory"
	test_dir.mkdir()

	delete(test_dir)

	assert not test_dir.exists()

	with pytest.raises(FileNotFoundError):
		delete(test_dir)

	delete(test_dir, missing_ok=True)  # Should not raise an error


def test_delete_directory_recursively(tmp_path: Path) -> None:
	test_dir = tmp_path / "directory"
	(test_dir / "subdir").mkdir(parents=True)
	(test_dir / "subdir" / "test.txt").write_text("opsi", encoding="utf-8")

	delete(test_dir)

	assert not test_dir.exists()


def test_delete_file_symlink_without_deleting_target(tmp_path: Path) -> None:
	target = tmp_path / "target.txt"
	link = tmp_path / "link.txt"
	target.write_text("opsi", encoding="utf-8")
	try:
		link.symlink_to(target)
	except OSError as err:
		pytest.skip(f"Symbolic links are not available: {err}")

	delete(link)

	assert not link.exists()
	assert target.read_text(encoding="utf-8") == "opsi"


def test_delete_directory_symlink_without_deleting_target(tmp_path: Path) -> None:
	target = tmp_path / "target"
	link = tmp_path / "link"
	target.mkdir()
	(target / "test.txt").write_text("opsi", encoding="utf-8")
	try:
		link.symlink_to(target, target_is_directory=True)
	except OSError as err:
		pytest.skip(f"Symbolic links are not available: {err}")

	delete(link)

	assert not link.exists()
	assert (target / "test.txt").read_text(encoding="utf-8") == "opsi"


def test_delete_broken_symlink(tmp_path: Path) -> None:
	link = tmp_path / "link.txt"
	try:
		link.symlink_to(tmp_path / "missing.txt")
	except OSError as err:
		pytest.skip(f"Symbolic links are not available: {err}")

	delete(link)

	assert not link.is_symlink()


def test_delete_hard_link_without_deleting_original(tmp_path: Path) -> None:
	target = tmp_path / "target.txt"
	link = tmp_path / "link.txt"
	target.write_text("opsi", encoding="utf-8")
	try:
		os.link(target, link)
	except OSError as err:
		pytest.skip(f"Hard links are not available: {err}")

	delete(link)

	assert not link.exists()
	assert target.read_text(encoding="utf-8") == "opsi"


def test_retry_on_delete(tmp_path: Path) -> None:
	test_file = tmp_path / "test.txt"

	delete_attempt = 0
	orig_delete_attempt = _delete_attempt

	def side_effect_delete(path: Path, missing_ok: bool) -> None:
		nonlocal delete_attempt
		delete_attempt += 1
		if delete_attempt < 2:
			raise OSError("Delete error")
		return orig_delete_attempt(path, missing_ok)

	with patch("opsi.system.file.operation._operation._delete_attempt", side_effect=side_effect_delete, autospec=True):
		# File does not exist, no retry should occur
		with pytest.raises(FileNotFoundError):
			delete(test_file)
		assert delete_attempt == 0

		test_file.write_text("opsi", encoding="utf-8")
		delete(test_file)
		assert delete_attempt == 2
		assert not test_file.exists()


@pytest.mark.parametrize("target_exists", (True, False))
@pytest.mark.parametrize("link_exists", ("", "link", "file", "directory"))
def test_create_symlink_to_file(tmp_path: Path, target_exists: bool, link_exists: str) -> None:
	target = tmp_path / "target.txt"
	if target_exists:
		target.write_text("opsi", encoding="utf-8")

	link_path = tmp_path / "link.txt"
	if link_exists == "link":
		some_file = tmp_path / "some_file.txt"
		some_file.write_text("some content", encoding="utf-8")
		link_path.symlink_to(some_file)
	elif link_exists == "file":
		link_path.write_text("existing", encoding="utf-8")
	elif link_exists == "directory":
		link_path.mkdir()

	if link_exists:
		with pytest.raises(FileExistsError):
			link(link_path, target, link_type="symlink")
		link(link_path, target, link_type="symlink", overwrite=True)
	else:
		link(link_path, target, link_type="symlink")

	assert link_path.is_symlink()
	if target_exists:
		assert link_path.read_text(encoding="utf-8") == "opsi"


@pytest.mark.parametrize("target_exists", (True, False))
@pytest.mark.parametrize("link_exists", ("", "link", "file", "directory"))
def test_create_symlink_to_directory(tmp_path: Path, target_exists: bool, link_exists: str) -> None:
	target = tmp_path / "target"
	if target_exists:
		target.mkdir()
		(target / "test.txt").write_text("opsi", encoding="utf-8")

	link_path = tmp_path / "link"
	if link_exists == "link":
		some_dir = tmp_path / "some_dir"
		some_dir.mkdir()
		link_path.symlink_to(some_dir)
	elif link_exists == "file":
		link_path.write_text("existing", encoding="utf-8")
	elif link_exists == "directory":
		link_path.mkdir()

	if link_exists:
		with pytest.raises(FileExistsError):
			link(link_path, target, link_type="symlink")
		link(link_path, target, link_type="symlink", overwrite=True, target_is_directory=not target_exists)
	else:
		link(link_path, target, link_type="symlink", target_is_directory=not target_exists)

	assert link_path.is_symlink()
	if not target_exists:
		# Create the target after creating the symlink to test the target_is_directory parameter
		target.mkdir()
		(target / "test.txt").write_text("opsi", encoding="utf-8")

	assert link_path.is_dir()
	assert (link_path / "test.txt").read_text(encoding="utf-8") == "opsi"


@pytest.mark.parametrize("target_exists", (True, False))
@pytest.mark.parametrize("link_exists", ("", "link", "file", "directory"))
def test_create_hardlink_to_file(tmp_path: Path, target_exists: bool, link_exists: str) -> None:
	target = tmp_path / "target.txt"
	if target_exists:
		target.write_text("opsi", encoding="utf-8")

	link_path = tmp_path / "link.txt"
	if link_exists == "link":
		some_file = tmp_path / "some_file.txt"
		some_file.write_text("some content", encoding="utf-8")
		link_path.symlink_to(some_file)
	elif link_exists == "file":
		link_path.write_text("existing", encoding="utf-8")
	elif link_exists == "directory":
		link_path.mkdir()

	with nullcontext() if target_exists else pytest.raises(FileNotFoundError):
		if link_exists:
			with pytest.raises(FileExistsError):
				link(link_path, target, link_type="hardlink")
			link(link_path, target, link_type="hardlink", overwrite=True)
		else:
			link(link_path, target, link_type="hardlink")

	if target_exists:
		assert link_path.exists()
		assert link_path.read_text(encoding="utf-8") == "opsi"
	else:
		assert not link_path.exists()


def test_link_raises_on_invalid_link_type(tmp_path: Path) -> None:
	target = tmp_path / "target.txt"
	target.write_text("opsi", encoding="utf-8")

	with pytest.raises(ValueError):
		link(target, tmp_path / "link.txt", link_type=cast(LinkType, "invalid"))


def test_retry_on_link(tmp_path: Path) -> None:
	target = tmp_path / "target.txt"
	link_path = tmp_path / "link.txt"
	target.write_text("opsi", encoding="utf-8")

	link_attempt = 0
	orig_link_attempt = _link_attempt

	def side_effect_link(source: Path, link_path: Path, link_type: LinkType, target_is_directory: bool | None = None) -> None:
		nonlocal link_attempt
		link_attempt += 1
		if link_attempt < 2:
			raise OSError("Link error")
		return orig_link_attempt(source, link_path, link_type)

	with patch("opsi.system.file.operation._operation._link_attempt", side_effect=side_effect_link, autospec=True):
		link(link_path, target, link_type="hardlink")

	assert link_attempt == 2
	assert link_path.exists()
