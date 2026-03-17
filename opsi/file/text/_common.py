# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import codecs
import encodings
import os
import re
from functools import lru_cache
from pathlib import Path
from types import TracebackType
from typing import Literal, Self, get_args

from opsi.exception import OperatingSystemUnsupportedError
from opsi.logging import get_logger
from opsi.logging._const import INFO
from opsi.retry import Retry, RetryConfig, get_retry_config
from opsi.system.info import is_linux, is_windows

if is_linux():
	from opsi.system.linux import get_kernel_params

logger = get_logger("opsi")

PLACEHOLDER_REGEX = re.compile(r"^(.*)#\@(\w+)\**#+(.*)$")
PLACEHOLDER_REGEX_NEW = re.compile(r"^(.*){{\s*(.*?)\s*}}(.*)$")

TypeWhere = Literal["selected", "above_selected", "below_selected", "top", "bottom"]


def _get_params_from_file(params_file: str | Path) -> dict[str, str]:
	"""
	Read parameters from a file in the format KEY=VALUE, one per line.
	Lines starting with # or ; will be ignored as comments.
	Values can contain escaped characters like \n for newline or \t for tab, which will be unescaped when read.

	:param params_file: The path to the parameters file.
	:return: A dictionary of parameters read from the file.
	"""
	result = {}
	with open(params_file, "r", encoding="utf-8", errors="replace") as file:
		for line in file:
			line = line.strip()
			if not line or line.startswith(("#", ";")):
				continue
			key = line
			value = ""
			if "=" in line:
				key, value = line.split("=", 1)
				try:
					value = codecs.escape_decode(value.encode("utf-8"))[0].decode("utf-8")  # type: ignore[unresolved-attribute]
				except ValueError as err:
					# Could be an invalid escape sequence like in linu\x
					logger.warning("Failed to escape decode '%s': %s", value, err)
			result[key.strip()] = value.strip()
	return result


@lru_cache(maxsize=1)
def _get_available_encodings() -> set[str]:
	"""
	Get a set of available encodings names on the system, including both canonical names and aliases.

	:return: A set of available encoding names.
	"""
	return set(encodings.aliases.aliases.keys()) | set(encodings.aliases.aliases.values())


class TextFile:
	"""
	Read, write and modify text files with support for different encodings and line endings, as well as patching placeholders with parameters.
	"""

	_encodings_to_try = ["utf-8", "utf-16", "cp1250"]

	def __init__(
		self,
		path: Path | str,
		*,
		encoding: str | None = None,
		line_ending: Literal["\n", "\r\n"] | None = None,
		retry_config: RetryConfig | None = None,
	) -> None:
		"""
		:param path: The path to the text file to read and modify.
		:param encoding:
			The encoding to use for reading and writing the file.
			If not specified, the encoding will be detected when reading the file or
			default to utf-8 on Unix and utf-16 on Windows if the file does not exist or the encoding cannot be detected.
		:param line_ending:
			The line ending to use for writing the file.
			If not specified, the line ending will be detected when reading the file
			or default to the system default line ending if the file does not exist or the line ending cannot be detected.
		:param retry_config:
			Optional configuration for retrying file I/O operations in case of transient errors.
			If not specified, a default retry configuration will be used.
		"""
		self._path = Path(path)
		self._encoding = None
		self._line_ending = None
		self._lines = []
		self._line_index = 0
		self._file_read = False
		self._changed = False
		self._retry_config = retry_config or get_retry_config("file_io")

		if encoding is not None:
			self.set_encoding(encoding)
		if line_ending is not None:
			self.set_line_ending(line_ending)

	def __enter__(self) -> Self:
		self._read()
		return self

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		if not exc_type:
			self.flush()

	def _set_defaults(self) -> None:
		"""
		Set default encoding and line ending if they are not already set.
		"""
		if not self._encoding:
			self._encoding = "utf-16" if is_windows() else "utf-8"
			logger.info("No encoding specified for file '%s', defaulting to '%s'", self._path, self._encoding)
		if not self._line_ending:
			self._line_ending = os.linesep
			logger.info("No line ending specified for file '%s', defaulting to '%s'", self._path, repr(self._line_ending))

	def _read(self) -> None:
		"""
		Read the content of the text file, detect encoding and line ending if not already set, and store the lines in memory.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				return self._read_attempt()

	def _read_attempt(self) -> None:
		"""
		Attempt to read the content of the text file, detect encoding and line ending if not already set, and store the lines in memory.
		This method is intended to be called by the _read method which handles retries in case of transient errors.
		"""
		self._lines = []
		self._file_read = False

		if not self._path.exists():
			self._file_read = True
			self._changed = False
			self._set_defaults()
			return

		encodings = [self._encoding] if self._encoding else self._encodings_to_try
		for idx, encoding in enumerate(encodings):
			try:
				# Universal newline mode enabled, line endings are returned untranslated
				with open(self._path, "r", encoding=encoding, errors="strict", newline="") as file:
					for line in file:
						if not self._line_ending:
							if line.endswith("\r\n"):
								self._line_ending = "\r\n"
							elif line.endswith("\n"):
								self._line_ending = "\n"
							if self._line_ending:
								logger.info("Detected line ending '%s' for file '%s'", repr(self._line_ending), self._path)
						self._lines.append(line.rstrip("\r\n"))

				self._encoding = encoding
				if not self._line_ending:
					self._line_ending = os.linesep
					logger.info("Could not detect line ending for file '%s', defaulting to '%s'", self._path, repr(self._line_ending))
				logger.info("Successfully read file '%s' with encoding '%s'", self._path, encoding)
				break
			except UnicodeDecodeError as exc:
				logger.debug("Failed to read file '%s' with encoding '%s': %s", self._path, encoding, exc)
				if idx == len(encodings) - 1:
					# This should not happen currently, because cp1250 is a one byte encoding and should be able to decode any file
					raise
				continue

		self._file_read = True
		self._changed = False
		self._set_defaults()

	def _assert_read(self) -> None:
		"""
		Assert that the file has been read and the lines are available in memory.
		If the file has not been read yet, it will be read by calling the _read method.
		"""
		if not self._file_read:
			self._read()

	def _write(self) -> None:
		"""
		Write the content of the text file from memory to disk using the specified encoding and line ending.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				return self._write_attempt()

	def _write_attempt(self) -> None:
		"""
		Attempt to write the content of the text file from memory to disk using the specified encoding and line ending.
		This method is intended to be called by the flush method which handles retries in case of transient errors.
		"""
		self._set_defaults()
		assert self._encoding is not None
		assert self._line_ending is not None

		with open(self._path, "w", encoding=self._encoding, newline="") as file:
			for line in self._lines:
				file.write(line)
				file.write(self._line_ending)

		logger.info("Successfully wrote file '%s' with encoding '%s'", self._path, self._encoding)

	def flush(self) -> None:
		"""
		Flush the content of the text file from memory to disk if there are any changes.
		"""
		if self._changed:
			self._write()

	def get_encoding(self) -> str:
		"""
		Get the encoding used for reading and writing the text file.

		:return: The name of the encoding.
		"""
		if self._encoding:
			return self._encoding
		self._assert_read()
		assert self._encoding is not None
		return self._encoding

	def set_encoding(self, encoding: str) -> None:
		"""
		Set the encoding to use for reading and writing the text file.

		:param encoding: The name of the encoding to use.
		"""
		encodings = _get_available_encodings()
		if str(encoding).replace("-", "_") not in encodings:
			raise ValueError(f"Encoding '{encoding}' is not available on this system. Available encodings: {', '.join(encodings)}")

		if encoding != self._encoding:
			self._encoding = encoding
			self._changed = True

	def get_line_ending(self) -> str:
		"""
		Get the line ending used for reading and writing the text file.

		:return: The line ending as a string, e.g. "\n" for LF, "\r\n" for CRLF or "" for no line endings.
		"""
		if self._line_ending:
			return self._line_ending
		self._assert_read()
		assert self._line_ending is not None
		return self._line_ending

	def set_line_ending(self, line_ending: Literal["\n", "\r\n", ""]) -> None:
		"""
		Set the line ending to use for reading and writing the text file.

		:param line_ending: The line ending to use. Must be one of:
			- "\n": Use LF line endings.
			- "\r\n": Use CRLF line endings.
			- "": Use no line endings, lines will be concatenated without any separator.
		"""
		if line_ending not in ("\n", "\r\n", ""):
			raise ValueError("Line ending must be '\\n', '\\r\\n' or ''")

		if line_ending != self._line_ending:
			self._line_ending = line_ending
			self._changed = True

	def get_selected_line_number(self) -> int:
		"""
		Get the currently selected line number.
		Line numbers start at 1.
		When the file is empty, 1 will be returned as the selected line number.

		:return: The currently selected line number, starting at 1.
		"""
		self._assert_read()
		return self._line_index + 1

	def select_line_number(self, line_number: int) -> int:
		"""
		Select the specified line number.
		Line numbers start at 1.
		If the specified line number is greater than the number of lines in the file,
		new lines will be created until the specified line number is reached.

		:param line_number: The line number to select, starting at 1.
		:return: The new line number of the selected line.
		"""
		self._assert_read()
		line_number = max(1, line_number)
		missing_lines = line_number - len(self._lines)
		if missing_lines > 0:
			self._lines.extend([""] * missing_lines)
			self._changed = True
		self._line_index = line_number - 1
		return self._line_index + 1

	def select_first_line(self) -> int:
		"""
		Select the first line of the text file.
		If the file is empty, a new line will be created and selected.

		:return: The first line number of the selected line, which will always be 1, even if the file is empty.
		"""
		return self.select_line_number(1)

	def select_last_line(self) -> int:
		"""
		Select the last line of the text file.
		If the file is empty, a new line will be created and selected.

		:return: The new line number of the last line in the file, which will be 1 if the file is empty.
		"""
		self._assert_read()
		return self.select_line_number(len(self._lines))

	def select_next_line(self) -> int:
		"""
		Select the next line in the text file.
		If the currently selected line is the last line in the file, a new line will be created and selected.

		:return: The new line number of the selected line.
		"""
		self._assert_read()
		return self.select_line_number(self._line_index + 2)

	def select_previous_line(self) -> int:
		"""
		Select the previous line in the text file.

		:return: The new line number of the selected line.
		"""
		self._assert_read()
		return self.select_line_number(self._line_index)

	def find_line(self, pattern: str, *, start: TypeWhere = "below_selected", ignore_case: bool = False) -> int:
		"""
		Find the first line matching the given regular expression pattern and select it.

		:param pattern: The regular expression pattern to search for in the lines of the text file.
		:param start: The position to start the search from. Must be one of:
			- "selected": Start searching down from the currently selected line, including it.
			- "below_selected": Start searching down from the line below the currently selected line.
			- "above_selected": Start searching up from the line above the currently selected line.
			- "top": Start searching down from the top of the file.
			- "bottom": Start searching up from the bottom of the file.

		:return: The line number of the first matching line, or 0 if no match is found.
		"""
		if start not in get_args(TypeWhere):
			raise ValueError(f"Invalid start position {start!r}, must be one of: {', '.join(repr(arg) for arg in get_args(TypeWhere))}")

		self._assert_read()
		regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)

		if start in ("selected", "below_selected"):
			search_range = range(self._line_index + (0 if start == "selected" else 1), len(self._lines))
		elif start == "above_selected":
			search_range = range(self._line_index - 1, -1, -1)
		elif start == "top":
			search_range = range(0, len(self._lines))
		elif start == "bottom":
			search_range = range(len(self._lines) - 1, -1, -1)

		for idx in search_range:
			if regex.search(self._lines[idx]):
				self._line_index = idx
				return self._line_index + 1
		return 0

	def get_line(self) -> str:
		"""
		Get the text of the currently selected line, or an empty string if the file is empty.

		:return: The text of the currently selected line, or an empty string if the file is empty.
		"""
		self._assert_read()
		if not self._lines:
			return ""
		return self._lines[self._line_index]

	def insert_lines(self, lines: list[str], *, where: TypeWhere = "below_selected") -> int:
		"""
		Insert multiple lines of text at the specified position.

		:param lines: The lines of text to insert.
		:param where: The position to insert the lines. Must be one of:
			- "selected": Insert at the currently selected line, the selected line will be overwritten.
			- "above_selected": Insert above the currently selected line, pushing the current line and following lines down.
			- "below_selected": Insert below the currently selected line, pushing the following lines down.
			- "top": Insert at the top of the file, pushing all lines down.
			- "bottom": Insert at the bottom of the file.
		:return: The new line number of the last inserted line.
		"""
		if where not in get_args(TypeWhere):
			raise ValueError(f"Invalid insert position {where!r}, must be one of: {', '.join(repr(arg) for arg in get_args(TypeWhere))}")

		self._assert_read()
		insert_index = self._line_index
		if where == "below_selected":
			insert_index = self._line_index + 1
		elif where == "top":
			insert_index = 0
		elif where == "bottom":
			insert_index = len(self._lines)

		self._lines[insert_index : insert_index + (1 if where == "selected" else 0)] = lines
		self._line_index = insert_index + len(lines) - 1
		self._changed = True
		return self._line_index + 1

	def insert_line(self, text: str, *, where: TypeWhere = "below_selected") -> int:
		"""
		Insert a single line of text at the specified position.

		:param text: The text to insert as a single line.
		:param where: The position to insert the line. Must be one of:
			- "selected": Insert at the currently selected line, the selected line will be overwritten.
			- "above_selected": Insert above the currently selected line, pushing the current line and following lines down.
			- "below_selected": Insert below the currently selected line, pushing the following lines down.
			- "top": Insert at the top of the file, pushing all lines down.
			- "bottom": Insert at the bottom of the file.
		:return: The new line number of the inserted line.
		"""
		return self.insert_lines([text], where=where)

	def set_line(self, text: str) -> int:
		"""
		Set the text of the currently selected line, overwriting it.

		:param text: The text to set for the selected line.
		:return: The new line number of the set line.
		"""
		return self.insert_line(text, where="selected")

	def delete_lines(
		self,
		*,
		where: TypeWhere = "below_selected",
		count: int | None = None,
	) -> int:
		"""
		Delete one or more lines of text at the specified position.

		:param where: The position to delete lines from. Must be one of:
			- "selected": Start deletion at the currently selected line.
			- "above_selected": Delete lines above the currently selected line.
			- "below_selected": Delete lines below the currently selected line.
			- "top": Delete lines from the top of the file.
			- "bottom": Delete lines from the bottom of the file.
		:param count: The number of lines to delete. If None, the number of lines to delete will be determined based on the position:
			- "selected": Delete the selected line.
			- "above_selected": Delete all lines above the selected line.
			- "below_selected": Delete all lines below the selected line.
			- "top": Delete all lines from the top of the file.
			- "bottom": Delete all lines from the bottom of the file.
		:return: The new line number of the line following the last deleted line, or the last line if the deleted lines were at the end of the file.
		"""
		if where not in get_args(TypeWhere):
			raise ValueError(f"Invalid delete position {where!r}, must be one of: {', '.join(repr(arg) for arg in get_args(TypeWhere))}")

		self._assert_read()
		if not self._lines:
			return self._line_index + 1

		if where == "selected":
			delete_start = self._line_index
			delete_end = min(self._line_index + (count or 1), len(self._lines))
		elif where == "above_selected":
			if not count:
				delete_start = 0
			else:
				delete_start = max(self._line_index - count, 0)
			delete_end = self._line_index
			self._line_index -= delete_end - delete_start
		elif where == "below_selected":
			delete_start = self._line_index + 1
			if not count:
				delete_end = len(self._lines)
			else:
				delete_end = min(self._line_index + 1 + count, len(self._lines))
		elif where == "top":
			delete_start = 0
			if not count:
				delete_end = len(self._lines)
			else:
				delete_end = min(count, len(self._lines))
			self._line_index -= delete_end - delete_start
		elif where == "bottom":
			if not count:
				delete_start = 0
			else:
				delete_start = max(len(self._lines) - count, 0)
			delete_end = len(self._lines)

		del self._lines[delete_start:delete_end]
		self._changed = True
		self._line_index = max(0, min(self._line_index, len(self._lines) - 1))
		return self._line_index + 1

	def delete_line(self, *, where: TypeWhere = "selected") -> int:
		"""
		Delete a single line of text at the specified position.

		:param where: The position to delete the line from. Must be one of:
			- "selected": Delete the currently selected line.
			- "above_selected": Delete the line above the currently selected line.
			- "below_selected": Delete the line below the currently selected line.
			- "top": Delete the top line of the file.
			- "bottom": Delete the bottom line of the file.
		:return: The new line number of the line following the deleted line, or the last line if the deleted line was at the end of the file.
		"""
		return self.delete_lines(where=where, count=1)

	def get_lines(self) -> list[str]:
		"""
		Get all lines of the text file as a list of strings without line endings.

		:return: A list of lines in the text file, without line endings.
		"""
		self._assert_read()
		return self._lines

	def get_line_count(self) -> int:
		"""
		Get the number of lines in the text file.

		:return: The number of lines in the text file.
		"""
		self._assert_read()
		return len(self._lines)

	def read_text(self) -> str:
		"""
		Read the entire content of the text file as a single string with line endings.

		:return: The entire content of the text file as a single string with line endings.
			If the file is empty, an empty string will be returned.
		"""
		self._assert_read()
		assert self._line_ending is not None
		if not self._lines:
			return ""
		return self._line_ending.join(self._lines) + self._line_ending

	def write_text(self, text: str) -> int:
		"""
		Write the given text to the file, replacing the entire content.
		The text can contain multiple lines separated by \n or \r\n line endings.

		:param text: The text to write to the file. Can contain multiple lines separated by \n or \r\n line endings.
		:return: The new line number of the last line in the file after writing the text, or 1 if the text is empty.
		"""
		self._assert_read()
		assert self._line_ending is not None
		self._lines = text.splitlines()
		self._changed = True
		return len(self._lines)

	def patch(self, *, params: dict[str, str] | None = None, params_file: str | Path | None = None, kernel_params: bool = False) -> None:
		"""
		Patch the text file by replacing placeholders with values from the provided parameters.
		Placeholders in the text file can be in the format #@KEY# or {{KEY}}. The KEY will be replaced with the corresponding value from the parameters.

		:param params: A dictionary of parameters to use for patching. The keys are the placeholder names, and the values are the values to replace them with.
		:param params_file: A file containing parameters in the format KEY=VALUE, one per line.
			Lines starting with # or ; will be ignored as comments. Values can contain escaped characters like
			\n for newline or \t for tab, which will be unescaped when read.
		:param kernel_params: If True, parameters will also be read from the Linux kernel command line.
			This is only supported on Linux systems. The kernel parameters will be available as key-value pairs
			where the key is the parameter name and the value is the parameter value. Parameters without a value will have an empty string as value.
		"""
		self._assert_read()
		_params = {}
		if kernel_params:
			if not is_linux():
				raise OperatingSystemUnsupportedError("Kernel parameters can only be retrieved on Linux systems")

			logger.notice("Getting params from kernel commandline")
			_params.update(get_kernel_params())

		if params_file:
			logger.notice("Reading params from file '%s'", params_file)
			_params.update(_get_params_from_file(params_file))

		if params:
			logger.notice("Using params from function arguments")
			_params.update(params)

		if logger.isEnabledFor(INFO):
			lines = ["Params:"]
			for key, value in _params.items():
				lines.append(f"   {key} = {value}")
			logger.info("\n".join(lines) + "\n")

		logger.notice("Patching file '%s'", self._path)

		for idx, line in enumerate(self._lines):
			for regex in (PLACEHOLDER_REGEX_NEW, PLACEHOLDER_REGEX):
				match = regex.search(line)
				while match:
					key = match.group(2)
					if key not in _params:
						logger.warning("Cannot patch placeholder '%s' in file '%s': param not defined", key, self._path)
						break
					logger.notice("Patching placeholder '%s' in file '%s'", key, self._path)
					line = f"{match.group(1)}{_params[key]}{match.group(3)}"
					match = regex.search(line)

			if line != self._lines[idx]:
				self._changed = True
				self._lines[idx] = line


def patch_text_file(
	text_file: str | Path, *, params: dict[str, str] | None = None, params_file: str | Path | None = None, kernel_params: bool = False
) -> None:
	with TextFile(text_file) as file:
		file.patch(params=params, params_file=params_file, kernel_params=kernel_params)
