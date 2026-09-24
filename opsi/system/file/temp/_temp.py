# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path
from tempfile import gettempdir
from types import TracebackType
from typing import Self

from opsi.logging import get_logger
from opsi.retry import Retry, RetryConfig, RetryConfigType, get_retry_config

logger = get_logger("opsi")

TEMP_DIR_PREFIX = "opsi_temp_"
TEMP_FILE_PREFIX = "opsi_temp_"
TEMP_NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
TEMP_NAME_LENGTH = 8


def _get_random_name() -> str:
	"""
	Return a random name for a temporary file or directory.
	A cryptographically secure generator is used, so that names cannot be predicted.
	"""
	return "".join(secrets.choice(TEMP_NAME_CHARS) for _ in range(TEMP_NAME_LENGTH))


class TempDir:
	"""
	Create a temporary directory that is automatically deleted when the context is exited.
	"""

	def __init__(self, *, base_dir: Path | str | None = None, retry_config: RetryConfig | None = None) -> None:
		"""
		Initialize a new TempDir instance.
		:param base_dir:
			The base directory where the temporary directory will be created.
			If None, uses the system default temporary directory.
		:param retry_config:
			Configuration for automatic retry behavior on failure.
			If None, uses the default retry configuration for file I/O operations.
		"""
		base_dir = Path(base_dir) if base_dir else Path(gettempdir())
		self._retry_config = retry_config or get_retry_config(RetryConfigType.FILE_IO)
		self._path = base_dir / f"{TEMP_DIR_PREFIX}{_get_random_name()}"

	@property
	def path(self) -> Path:
		"""
		Get the path to the temporary directory.

		:return: The path to the temporary directory.
		"""
		return self._path

	def _create_attempt(self) -> None:
		self._path.mkdir(mode=0o700, parents=True, exist_ok=True)

	def create(self) -> None:
		"""
		Create the temporary directory if it does not exist.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._create_attempt()

	def _delete_attempt(self) -> None:
		if self._path.exists():
			shutil.rmtree(self._path)

	def delete(self) -> None:
		"""
		Delete the temporary directory and all its contents if it exists.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._delete_attempt()

	def __enter__(self) -> Path:
		"""
		Enter the context, creating the temporary directory if it does not exist.

		:return: The path to the temporary directory.
		"""
		self.create()
		return self._path

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, deleting the temporary directory and all its contents.
		"""
		self.delete()


def create_temp_dir(*, retry_config: RetryConfig | None = None) -> Path:
	"""
	Create a temporary directory and return its path.
	The directory will not be automatically deleted, so the caller is responsible for cleanup.
	"""
	temp_dir = TempDir(retry_config=retry_config)
	temp_dir.create()
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
		self._retry_config = retry_config or get_retry_config(RetryConfigType.FILE_IO)
		self._path = Path(gettempdir()) / f"{TEMP_FILE_PREFIX}{_get_random_name()}.{extension}"
		self._content = content
		self._encoding = encoding
		self._created = False

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

	def _create_attempt(self) -> None:
		flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
		if not self._created:
			# Fail if the file already exists, so that a file or symlink planted by someone else is never used.
			# Once created, the file is reused (repeated create() calls or a retry after a failed write).
			flags |= os.O_EXCL
		fd = os.open(self._path, flags, 0o600)
		self._created = True
		content = self._content or ""
		if isinstance(content, str):
			with open(fd, "w", encoding=self._encoding, newline="") as file:
				file.write(content)
		else:
			with open(fd, "wb") as file:
				file.write(content)

	def create(self, *, content: str | bytes | None = None, encoding: str | None = None) -> None:
		"""
		Create the temporary file.

		The first creation is exclusive, a FileExistsError is raised if the file already exists.
		Calling create() again overwrites the content of the file.
		"""
		if content:
			self._content = content
		if encoding:
			self._encoding = encoding
		for attempt in Retry(self._retry_config):
			with attempt:
				self._create_attempt()

	def _delete_attempt(self) -> None:
		if self._path.exists():
			self._path.unlink()
		self._created = False

	def delete(self) -> None:
		"""
		Delete the temporary file if it exists.
		"""
		for attempt in Retry(self._retry_config):
			with attempt:
				self._delete_attempt()

	def __enter__(self) -> Self:
		"""
		Enter the context, creating the temporary file if it does not exist.

		:return: The path to the temporary file.
		"""
		self.create()
		return self

	def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
		"""
		Exit the context, deleting the temporary file.
		"""
		self.delete()


def create_temp_file(
	*,
	content: str | bytes | None = None,
	encoding: str | None = None,
	extension: str = "tmp",
	retry_config: RetryConfig | None = None,
) -> Path:
	"""
	Create a temporary file with the specified content and return its path.
	The file will not be automatically deleted, so the caller is responsible for cleanup.
	"""
	temp_file = TempFile(content=content, encoding=encoding, extension=extension, retry_config=retry_config)
	temp_file.create()
	return temp_file._path
