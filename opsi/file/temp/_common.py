# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import random
import shutil
from pathlib import Path
from tempfile import gettempdir
from types import TracebackType

from opsi.logging import get_logger
from opsi.retry import Retry, RetryConfig, get_retry_config

logger = get_logger()

TEMP_DIR_PREFIX = "opsi_temp_"
TEMP_FILE_PREFIX = "opsi_temp_"


class TempDir:
	"""
	Create a temporary directory that is automatically deleted when the context is exited.
	"""

	def __init__(self, *, retry_config: RetryConfig | None = None) -> None:
		"""
		Initialize a new TempDir instance.

		:param retry_config:
			Configuration for automatic retry behavior on failure.
			If None, uses the default retry configuration for file I/O operations.
		"""
		self._retry_config = retry_config or get_retry_config("file_io")
		name = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
		self._path = Path(gettempdir()) / f"{TEMP_DIR_PREFIX}{name}"

	@property
	def path(self) -> Path:
		"""
		Get the path to the temporary directory.

		:return: The path to the temporary directory.
		"""
		return self._path

	def _create(self) -> None:
		"""
		Create the temporary directory if it does not exist.
		"""
		self._path.mkdir(mode=0o700, parents=True, exist_ok=True)

	def _delete(self) -> None:
		"""
		Delete the temporary directory and all its contents if it exists.
		"""
		if self._path.exists():
			shutil.rmtree(self._path)

	def __enter__(self) -> Path:
		"""
		Enter the context, creating the temporary directory if it does not exist.

		:return: The path to the temporary directory.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._create()
		return self._path

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, deleting the temporary directory and all its contents.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._delete()


def create_temp_dir(*, retry_config: RetryConfig | None = None) -> Path:
	"""
	Create a temporary directory and return its path.
	The directory will be not be automatically deleted, so the caller is responsible for cleanup.
	"""
	temp_dir = TempDir(retry_config=retry_config)
	temp_dir._create()
	return temp_dir._path


class TempFile:
	"""
	Create a temporary file that is automatically deleted when the context is exited.
	"""

	def __init__(
		self,
		*,
		content: str | bytes | None = None,
		encoding: str | None = None,
		extension: str = "tmp",
		retry_config: RetryConfig | None = None,
	) -> None:
		"""
		Initialize a new TempFile instance.

		:param extension:
			The file extension for the temporary file.
		:param retry_config:
			Configuration for automatic retry behavior on failure.
			If None, uses the default retry configuration for file I/O operations.
		"""
		self._retry_config = retry_config or get_retry_config("file_io")
		name = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
		self._path = Path(gettempdir()) / f"{TEMP_FILE_PREFIX}{name}.{extension}"
		self._content = content
		self._encoding = encoding

	@property
	def path(self) -> Path:
		"""
		Get the path to the temporary file.

		:return: The path to the temporary file.
		"""
		return self._path

	def __str__(self) -> str:
		"""
		Return the path of the temporary file as a string.
		"""
		return str(self._path)

	def _create(self) -> None:
		"""
		Create the temporary file if it does not exist.
		"""
		self._path.touch(mode=0o600, exist_ok=True)
		content = self._content or ""
		if isinstance(content, str):
			self._path.write_text(content, encoding=self._encoding, newline="")
		else:
			self._path.write_bytes(content)

	def _delete(self) -> None:
		"""
		Delete the temporary file if it exists.
		"""
		if self._path.exists():
			self._path.unlink()

	def __enter__(self) -> Path:
		"""
		Enter the context, creating the temporary file if it does not exist.

		:return: The path to the temporary file.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._create()
		return self._path

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, deleting the temporary file.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._delete()


def create_temp_file(
	*,
	content: str | bytes | None = None,
	encoding: str | None = None,
	extension: str = "tmp",
	retry_config: RetryConfig | None = None,
) -> Path:
	"""
	Create a temporary file with the specified content and return its path.
	The file will be not be automatically deleted, so the caller is responsible for cleanup.
	"""
	temp_file = TempFile(content=content, encoding=encoding, extension=extension, retry_config=retry_config)
	temp_file._create()
	return temp_file._path
