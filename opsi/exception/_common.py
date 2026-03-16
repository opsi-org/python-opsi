# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from typing import Any


class OpsiError(Exception):
	"""Base class for OPSI Backend exceptions."""

	ExceptionShortDescription = "OPSI error"

	def __init__(self, message: str = "") -> None:
		super().__init__(message)
		self.message = str(message)

	def __str__(self) -> str:
		if self.message:
			return f"{self.ExceptionShortDescription}: {self.message}"
		return self.ExceptionShortDescription

	def __repr__(self) -> str:
		if self.message:
			return f'<{self.__class__.__name__}("{self.message}")>'
		return f"<{self.__class__.__name__}>"


class OperatingSystemUnsupportedError(OpsiError):
	"""Raised when the operating system is not supported."""


class OpsiBackupFileError(OpsiError):
	ExceptionShortDescription = "OPSI backup file error"


class OpsiBackupFileNotFound(OpsiBackupFileError):
	ExceptionShortDescription = "OPSI backup file not found"


class OpsiBackupBackendNotFound(OpsiBackupFileError):
	ExceptionShortDescription = "OPSI backend not found in backup"


class OpsiServiceError(OpsiError):
	ExceptionShortDescription = "OPSI service error"

	def __init__(self, message: str = "", status_code: int | None = None, content: str | None = None) -> None:
		super().__init__(message)
		self.status_code = status_code
		self.content = content


class OpsiServiceConnectionRefusedError(OpsiServiceError):
	ExceptionShortDescription = "OPSI service connection refused error"


class OpsiServiceAuthenticationError(OpsiServiceError):
	ExceptionShortDescription = "OPSI service authentication error"


class OpsiServiceClientCertificateError(OpsiServiceAuthenticationError):
	ExceptionShortDescription = "OPSI service client certificate error"


BackendAuthenticationError = OpsiServiceAuthenticationError


class OpsiServicePermissionError(OpsiServiceError):
	ExceptionShortDescription = "OPSI service permission error"


BackendPermissionDeniedError = OpsiServicePermissionError


class OpsiServiceConnectionError(OpsiServiceError):
	ExceptionShortDescription = "OPSI service connection error"


class OpsiServiceVerificationError(OpsiServiceConnectionError):
	ExceptionShortDescription = "OPSI service verification error"


class OpsiServiceTimeoutError(OpsiServiceConnectionError):
	ExceptionShortDescription = "OPSI service timeout error"


class OpsiServiceUnavailableError(OpsiServiceConnectionError):
	ExceptionShortDescription = "OPSI service unavailable error"

	def __init__(self, message: str = "", status_code: int | None = None, content: str | None = None, until: float | None = None) -> None:
		super().__init__(message)
		self.status_code = status_code
		self.content = content
		self.until = until


class OpsiBadRpcError(OpsiError):
	ExceptionShortDescription = "OPSI bad rpc error"


class OpsiRpcError(OpsiError):
	ExceptionShortDescription = "OPSI rpc error"

	def __init__(self, message: str = "", response: dict[str, Any] | None = None) -> None:
		super().__init__(message)
		self.response = response


class OpsiProductOrderingError(OpsiError):
	"""A condition for ordering cannot be fulfilled"""

	ExceptionShortDescription = "A condition for ordering cannot be fulfilled"

	def __init__(self, message: str = "", problematicRequirements: list[int] | list[str] | None = None) -> None:
		super().__init__(message)
		self.problematicRequirements: list[int] | list[str] | list = problematicRequirements or []

	def __str__(self) -> str:
		if self.message:
			if self.problematicRequirements:
				return f"{self.ExceptionShortDescription}: {self.message} ({self.problematicRequirements})"
			return f"{self.ExceptionShortDescription}: {self.message}"
		return self.ExceptionShortDescription

	def __repr__(self) -> str:
		if self.message:
			if self.problematicRequirements:
				return f'<{self.__class__.__name__}("{self.message}", {self.problematicRequirements})>'
			return f'<{self.__class__.__name__}("{self.message}")>'
		return f"<{self.__class__.__name__}>"


class LicenseConfigurationError(OpsiError):
	"""Exception raised if a configuration error occurs in the license data base."""

	ExceptionShortDescription = "License configuration error"


class LicenseMissingError(OpsiError):
	"""Exception raised if a license is requested but cannot be found."""

	ExceptionShortDescription = "License missing error"


class RepositoryError(OpsiError):
	ExceptionShortDescription = "Repository error"


class CanceledException(Exception):
	ExceptionShortDescription = "CanceledException"
