# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from opsi.exception import OperatingSystemUnsupportedError
from opsi.file.text import patch_text_file
from opsi.file.text._common import TextFile, _get_params_from_file
from opsi.logging import LOG_INFO
from opsi.system.info import is_linux, is_windows
from opsi.testing.helper import log_stream


def test_get_params_from_file(tmp_path: Path) -> None:
	param_file = tmp_path / "params"
	param_file.write_text(
		"key_without_value\n"
		"var1  = simple\n"
		"# comment1 = comment1\n"
		"; comment2 = comment2\n"
		"  ;; comment3 = comment3\n"
		" var2 = invalid\\escape\n"
		"  var3  = valid\\tescape\n"
		"var4 = before-tab\tafter-tab\n"
	)
	with pytest.warns(DeprecationWarning, match="invalid escape sequence"):
		params = _get_params_from_file(param_file)
	assert params == {
		"key_without_value": "",
		"var1": "simple",
		"var2": "invalid\\escape",
		"var3": "valid\tescape",
		"var4": "before-tab\tafter-tab",
	}

	param_file.write_text("var1  = linu\\x\n")
	with log_stream(LOG_INFO, format="%(levelname)s: %(message)s") as stream:
		params = _get_params_from_file(param_file)
		assert "Failed to escape decode ' linu\\x': invalid \\x escape" in stream.getvalue()


@pytest.mark.parametrize("encoding", ["cp1250", "utf-8", "utf-16"])
def test_detect_encoding(tmp_path: Path, encoding: str) -> None:
	file_path = tmp_path / "textfile"
	text = "Some text with special characters: Ý Ü »"
	file_path.write_text(text, encoding=encoding)

	with TextFile(file_path) as file:
		assert file.get_lines() == [text]
		assert file.get_encoding() == encoding

	file_path = tmp_path / "new_textfile"
	with TextFile(file_path) as file:
		assert file.get_lines() == []
		assert file.get_encoding() == "utf-16" if is_windows() else "utf-8"

	encoding = TextFile(tmp_path / "new_textfile2").get_encoding()
	assert encoding == "utf-16" if is_windows() else "utf-8"

	file_path.write_bytes(b"\xff\xff\xff")
	with TextFile(file_path) as file:
		assert file.get_encoding() == "cp1250"

	with patch("opsi.file.text._common.TextFile._encodings_to_try", ["utf-8", "utf-16"]):
		with pytest.raises(UnicodeDecodeError):
			with TextFile(file_path) as file:
				file.get_encoding()


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_detect_line_ending(tmp_path: Path, line_ending: str) -> None:
	file_path = tmp_path / "textfile"
	lines = ["Line 1", "Line 2", "Line 3"]
	text = line_ending.join(lines) + line_ending
	file_path.write_text(text, encoding="utf-8", newline="")

	with TextFile(file_path) as text_file:
		assert text_file.get_lines() == lines
		assert text_file.get_line_ending() == line_ending

	file_path.write_text("no line ending", encoding="utf-8", newline="")
	with TextFile(file_path) as text_file:
		assert text_file.get_lines() == ["no line ending"]
		assert text_file.get_line_ending() == os.linesep

	file_path.write_text("", encoding="utf-16", newline="")
	with TextFile(file_path) as text_file:
		assert text_file.get_lines() == []
		assert text_file.get_line_ending() == os.linesep

	file_path = tmp_path / "new_textfile"
	with TextFile(file_path) as file:
		assert file.get_lines() == []
		assert file.get_line_ending() == os.linesep

	line_ending = TextFile(tmp_path / "new_textfile2").get_line_ending()
	assert line_ending == os.linesep


def test_change_encoding_and_line_ending(tmp_path: Path) -> None:
	file_path = tmp_path / "textfile"
	lines = ["Line 1", "Line 2", "Line 3"]
	text = "\n".join(lines) + "\n"
	file_path.write_text(text, encoding="utf-8", newline="")

	with TextFile(file_path, encoding="utf-8", line_ending="\n") as text_file:
		text_file.set_encoding("utf-16")
		text_file.set_line_ending("\r\n")

	assert file_path.read_bytes().decode("utf-16") == "Line 1\r\nLine 2\r\nLine 3\r\n"

	with TextFile(file_path) as text_file:
		assert text_file.get_lines() == lines
		assert text_file.get_encoding() == "utf-16"
		assert text_file.get_line_ending() == "\r\n"

	with pytest.raises(ValueError, match="Encoding 'invalid-encoding' is not available on this system"):
		with TextFile(file_path) as text_file:
			text_file.set_encoding("invalid-encoding")

	with pytest.raises(ValueError, match=r"Line ending must be '\\n', '\\r\\n' or ''"):
		with TextFile(file_path) as text_file:
			text_file.set_line_ending("invalid-line-ending")  # type: ignore[invalid-argument-type]


def test_patch_text_file(tmp_path: Path) -> None:

	file_path = tmp_path / "textfile"
	unpatched_data = (
		"################################################\n"
		"line1\n"
		"line2 {{test_var1}} - {{test_var1}} - {{{test_var2}}} end2\n"
		"line3\n"
		"line 4: #@test_var3*# - #@test_var3*###\n"
		"line 5\n"
		"line 6: #@test_var4*#\n"
		"line 7: {{test_var5}}\n"
	)
	file_path.write_text(unpatched_data)

	params_file = tmp_path / "params.txt"
	params_file.write_text("test_var1=val1\ntest_var2 = val2\ntest_var3=val3")

	with log_stream(LOG_INFO, format="%(levelname)s: %(message)s") as stream:
		patch_text_file(file_path, params_file=params_file)
		assert "Params:\n   test_var1 = val1\n   test_var2 = val2\n   test_var3 = val3\n" in stream.getvalue()

	data = file_path.read_text()
	assert data == (
		"################################################\n"
		"line1\n"
		"line2 val1 - val1 - {val2} end2\n"
		"line3\n"
		"line 4: val3 - val3\n"
		"line 5\n"
		"line 6: #@test_var4*#\n"
		"line 7: {{test_var5}}\n"
	)

	file_path.write_text(unpatched_data)
	patch_text_file(file_path, params_file=params_file, params={"test_var1": "new_val1", "test_var4": "new_val4"})
	data = file_path.read_text()
	assert data == (
		"################################################\n"
		"line1\n"
		"line2 new_val1 - new_val1 - {val2} end2\n"
		"line3\n"
		"line 4: val3 - val3\n"
		"line 5\n"
		"line 6: new_val4\n"
		"line 7: {{test_var5}}\n"
	)

	if not is_linux():
		with pytest.raises(OperatingSystemUnsupportedError, match="Kernel parameters can only be retrieved on Linux systems"):
			patch_text_file(file_path, kernel_params=True)
		return

	file_path.write_text(unpatched_data)

	with patch("opsi.file.text._common.get_kernel_params", return_value={"test_var1": "kernel_val1", "test_var5": "kernel_val5"}):
		patch_text_file(file_path, params_file=params_file, params={"test_var4": "new_val4"}, kernel_params=True)

	data = file_path.read_text()
	assert data == (
		"################################################\n"
		"line1\n"
		"line2 val1 - val1 - {val2} end2\n"
		"line3\n"
		"line 4: val3 - val3\n"
		"line 5\n"
		"line 6: new_val4\n"
		"line 7: kernel_val5\n"
	)


TEST_FILE = (
	"The sun rose quietly over the empty street.\n"
	"A small bird sang from the top of a tree.\n"
	"Fresh coffee filled the kitchen with warmth.\n"
	"Someone laughed in the distance, light and free.\n"
	"The wind moved gently through open windows.\n"
	"Pages of a book turned slowly in the afternoon light.\n"
	"Time seemed to pause for just a moment.\n"
	"Thoughts wandered without any clear destination.\n"
	"The day felt calm, ordinary, and perfect.\n"
	"Night arrived softly, wrapping everything in silence.\n"
)


def test_find_line(tmp_path: Path) -> None:
	file_path = tmp_path / "textfile"
	file_path.write_text(TEST_FILE, encoding="utf-8")
	with TextFile(file_path) as text_file:
		assert text_file.find_line("with", start="top") == 3
		assert text_file.get_selected_line_number() == 3
		assert text_file.get_line() == "Fresh coffee filled the kitchen with warmth."

		assert text_file.find_line("with", start="selected") == 3
		assert text_file.get_selected_line_number() == 3

		assert text_file.find_line("with", start="below_selected") == 8
		assert text_file.get_selected_line_number() == 8

		assert text_file.find_line("with", start="below_selected") == 0
		assert text_file.get_selected_line_number() == 8
		assert text_file.get_line() == "Thoughts wandered without any clear destination."

		assert text_file.find_line("the", start="above_selected") == 6
		assert text_file.get_line() == "Pages of a book turned slowly in the afternoon light."

		assert text_file.find_line("the", start="above_selected", ignore_case=True) == 5
		assert text_file.get_line() == "The wind moved gently through open windows."

		text_file.select_line_number(6)
		assert text_file.find_line("the", start="above_selected", ignore_case=False) == 4
		assert text_file.get_line() == "Someone laughed in the distance, light and free."

		assert text_file.find_line("rose", start="above_selected") == 1
		assert text_file.find_line("rose", start="above_selected") == 0

		assert text_file.find_line("in", start="bottom") == 10
		assert text_file.find_line("The", start="bottom") == 9

		with pytest.raises(
			ValueError,
			match="Invalid start position 'invalid', must be one of: 'selected', 'above_selected', 'below_selected', 'top', 'bottom'",
		):
			text_file.find_line("coffee", start="invalid")  # type: ignore[invalid-argument-type]


def test_select_line(tmp_path: Path) -> None:
	file_path = tmp_path / "textfile"
	file_path.write_text(TEST_FILE, encoding="utf-8")
	with TextFile(file_path) as text_file:
		text_file.select_line_number(5)
		assert text_file.get_selected_line_number() == 5
		assert text_file.get_line() == "The wind moved gently through open windows."

		text_file.select_line_number(0)
		assert text_file.get_selected_line_number() == 1
		assert text_file.get_line() == "The sun rose quietly over the empty street."

		text_file.select_previous_line()
		assert text_file.get_selected_line_number() == 1
		assert text_file.get_line() == "The sun rose quietly over the empty street."

		text_file.select_next_line()
		assert text_file.get_selected_line_number() == 2
		assert text_file.get_line() == "A small bird sang from the top of a tree."

		text_file.select_line_number(11)
		assert text_file.get_selected_line_number() == 11
		assert text_file.get_line() == ""

		text_file.select_previous_line()
		assert text_file.get_selected_line_number() == 10
		assert text_file.get_line() == "Night arrived softly, wrapping everything in silence."

		text_file.select_line_number(15)
		assert text_file.get_selected_line_number() == 15
		assert text_file.get_line() == ""

		assert text_file.get_lines() == TEST_FILE.strip().splitlines() + [""] * 5

	file_path.read_text() == TEST_FILE.strip().splitlines() + [""] * 4


def test_retry_on_io_error(tmp_path: Path) -> None:
	attempt = 0

	def side_effect():
		nonlocal attempt
		attempt += 1
		if attempt < 3:
			raise OSError("Read error")

	with patch("opsi.file.text._common.TextFile._read_attempt", side_effect=side_effect):
		file_path = tmp_path / "textfile"
		with TextFile(file_path) as text_file:
			text_file.select_line_number(1)
	assert attempt == 4


def test_line_editing_operations(tmp_path: Path) -> None:
	file_path = tmp_path / "textfile"
	file_path.write_text("one\ntwo\nthree\n", encoding="utf-8")
	with TextFile(file_path) as text_file:
		assert text_file.get_line_count() == 3

		# select
		assert text_file.select_first_line() == 1
		assert text_file.get_line() == "one"

		assert text_file.select_last_line() == 3
		assert text_file.get_line() == "three"

		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"

		assert text_file.select_line_number(0) == 1
		assert text_file.get_line() == "one"

		assert text_file.select_line_number(-1) == 1
		assert text_file.get_line() == "one"

		assert text_file.select_line_number(10) == 10
		assert text_file.get_line() == ""

		assert text_file.get_lines() == ["one", "two", "three"] + [""] * 7

		# insert
		assert text_file.write_text("one\ntwo\nthree\n") == 3
		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"

		assert text_file.insert_line("before", where="above_selected") == 2
		assert text_file.get_line() == "before"
		assert text_file.get_lines() == ["one", "before", "two", "three"]

		assert text_file.insert_line("new_text", where="selected") == 2
		assert text_file.get_line() == "new_text"
		assert text_file.get_lines() == ["one", "new_text", "two", "three"]

		assert text_file.insert_line("after", where="below_selected") == 3
		assert text_file.get_line() == "after"
		assert text_file.get_lines() == ["one", "new_text", "after", "two", "three"]

		assert text_file.insert_line("top", where="top") == 1
		assert text_file.get_line() == "top"
		assert text_file.get_lines() == ["top", "one", "new_text", "after", "two", "three"]

		assert text_file.insert_line("bottom", where="bottom") == 7
		assert text_file.get_line() == "bottom"
		assert text_file.get_lines() == ["top", "one", "new_text", "after", "two", "three", "bottom"]

		assert text_file.select_line_number(3) == 3
		assert text_file.set_line("THREE") == 3
		assert text_file.get_line() == "THREE"
		assert text_file.get_lines() == ["top", "one", "THREE", "after", "two", "three", "bottom"]

		with pytest.raises(
			ValueError,
			match="Invalid insert position 'invalid', must be one of: 'selected', 'above_selected', 'below_selected', 'top', 'bottom'",
		):
			text_file.insert_line("invalid", where="invalid")  # type: ignore[invalid-argument-type]

		# delete selected
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n") == 5
		assert text_file.select_line_number(3) == 3
		assert text_file.get_line() == "three"
		assert text_file.delete_lines(where="selected", count=2) == 3
		assert text_file.get_line() == "five"
		assert text_file.get_lines() == ["one", "two", "five"]

		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"
		assert text_file.delete_lines(where="selected") == 2
		assert text_file.get_line() == "five"
		assert text_file.get_lines() == ["one", "five"]

		assert text_file.delete_lines(where="selected", count=100) == 1
		assert text_file.get_lines() == ["one"]

		# delete above selected
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n") == 5
		assert text_file.select_line_number(4) == 4
		assert text_file.get_line() == "four"
		assert text_file.delete_lines(where="above_selected", count=2) == 2
		assert text_file.get_line() == "four"
		assert text_file.get_lines() == ["one", "four", "five"]

		assert text_file.select_line_number(3) == 3
		assert text_file.delete_lines(where="above_selected") == 1
		assert text_file.get_lines() == ["five"]

		assert text_file.delete_lines(where="above_selected", count=100) == 1
		assert text_file.get_lines() == ["five"]

		# delete below selected
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"
		assert text_file.delete_lines(where="below_selected", count=2) == 2
		assert text_file.get_line() == "two"
		assert text_file.get_lines() == ["one", "two", "five"]

		assert text_file.select_line_number(1) == 1
		assert text_file.delete_lines(where="below_selected") == 1
		assert text_file.get_lines() == ["one"]

		assert text_file.delete_lines(where="below_selected", count=100) == 1
		assert text_file.get_lines() == ["one"]

		# delete top
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.select_line_number(3) == 3
		assert text_file.get_line() == "three"
		assert text_file.delete_lines(where="top", count=2) == 1
		assert text_file.get_lines() == ["three", "four", "five"]
		assert text_file.get_line() == "three"

		assert text_file.delete_lines(where="top") == 1
		assert text_file.get_lines() == []

		assert text_file.delete_lines(where="top", count=100) == 1
		assert text_file.get_lines() == []

		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"
		assert text_file.delete_lines(where="top", count=3) == 1
		assert text_file.get_lines() == ["four", "five"]
		assert text_file.get_line() == "four"

		# delete bottom
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.select_line_number(2) == 2
		assert text_file.get_line() == "two"
		assert text_file.delete_lines(where="bottom", count=2) == 2
		assert text_file.get_lines() == ["one", "two", "three"]
		assert text_file.get_line() == "two"

		assert text_file.delete_lines(where="bottom") == 1
		assert text_file.get_lines() == []

		assert text_file.delete_lines(where="bottom", count=100) == 1
		assert text_file.get_lines() == []

		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.select_line_number(4) == 4
		assert text_file.get_line() == "four"
		assert text_file.delete_lines(where="bottom", count=3) == 2
		assert text_file.get_lines() == ["one", "two"]
		assert text_file.get_line() == "two"

		# delete single line
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		assert text_file.get_line_count() == 5
		assert text_file.select_line_number(3) == 3
		assert text_file.delete_line() == 3
		assert text_file.get_line() == "four"
		assert text_file.get_lines() == ["one", "two", "four", "five"]
		assert text_file.get_line_count() == 4

		with pytest.raises(
			ValueError,
			match="Invalid delete position 'invalid', must be one of: 'selected', 'above_selected', 'below_selected', 'top', 'bottom'",
		):
			text_file.delete_line(where="invalid")  # type: ignore[invalid-argument-type]

		# others
		assert text_file.write_text("one\ntwo\nthree\nfour\nfive\n")
		text_file.flush()
		assert file_path.read_text() == "one\ntwo\nthree\nfour\nfive\n"

		text_file.set_line_ending("\r\n")
		assert text_file.write_text("new\nlines\n") == 2
		assert text_file.get_lines() == ["new", "lines"]
		assert text_file.read_text() == "new\r\nlines\r\n"

	assert file_path.read_bytes() == b"new\r\nlines\r\n"


def test_line_helpers_new_file(tmp_path: Path) -> None:
	file_path = tmp_path / "new"
	with TextFile(file_path) as text_file:
		assert text_file.get_line_count() == 0
		assert text_file.get_line() == ""  # should return empty string for new file, not None
		assert text_file.get_lines() == []
		assert text_file.read_text() == ""

		assert text_file.select_first_line() == 1
		assert text_file.get_line() == ""
		assert text_file.get_line_count() == 1

	file_path.unlink()
	with TextFile(file_path) as text_file:
		assert text_file.select_last_line() == 1
		assert text_file.get_line() == ""

	file_path.unlink()
	with TextFile(file_path) as text_file:
		assert text_file.find_line("anything") == 0
	assert not file_path.exists()

	with TextFile(file_path) as text_file:
		assert text_file.delete_line() == 1
		assert text_file.get_line_count() == 0
		assert text_file.get_line() == ""

	with TextFile(file_path) as text_file:
		assert text_file.set_line("first line") == 1
		assert text_file.get_lines() == ["first line"]
