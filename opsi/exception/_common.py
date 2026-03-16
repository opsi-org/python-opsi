# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from typing import Any


class OpsiError(Exception):
	"""Base class for OPSI Backend exceptions."""

	def __init__(self, message: str = "") -> None:
		super().__init__(message)
		self.message = message


class OperatingSystemUnsupportedError(OpsiError):
	"""Raised when the operating system is not supported."""


class OpsiServiceError(OpsiError):
	"""Base class for exceptions related to the OPSI Service."""

	def __init__(self, message: str = "", status_code: int | None = None, content: str | None = None) -> None:
		super().__init__(message)
		self.status_code = status_code
		self.content = content


class OpsiServiceConnectionRefusedError(OpsiServiceError):
	"""Raised when the connection to the OPSI Service is refused, e.g. because the service is not running or a firewall is blocking the connection."""


class OpsiServiceAuthenticationError(OpsiServiceError):
	"""Raised when authentication with the OPSI Service fails."""


class OpsiServiceClientCertificateError(OpsiServiceAuthenticationError):
	"""Raised when there is an issue with the client certificate used for authentication."""


BackendAuthenticationError = OpsiServiceAuthenticationError


class OpsiServicePermissionError(OpsiServiceError):
	"""Raised when the user does not have the necessary permissions to perform an action on the OPSI Service."""


BackendPermissionDeniedError = OpsiServicePermissionError


class OpsiServiceConnectionError(OpsiServiceError):
	"""Raised when there is a connection error with the OPSI Service, e.g. due to network issues or service unavailability."""


class OpsiServiceVerificationError(OpsiServiceConnectionError):
	"""Raised when there is a verification error with the OPSI Service, e.g. due to SSL certificate issues."""


class OpsiServiceTimeoutError(OpsiServiceConnectionError):
	"""Raised when a connection to the OPSI Service times out."""


class OpsiServiceUnavailableError(OpsiServiceConnectionError):
	"""Raised when the OPSI Service is unavailable, e.g. due to maintenance or high load."""

	def __init__(self, message: str = "", status_code: int | None = None, content: str | None = None, until: float | None = None) -> None:
		super().__init__(message)
		self.status_code = status_code
		self.content = content
		self.until = until


class OpsiBadRpcError(OpsiError):
	"""Raised due to a malformed RPC."""


class OpsiRpcError(OpsiError):
	"""Raised when an error occurs during an RPC to the OPSI Service."""

	def __init__(self, message: str = "", response: dict[str, Any] | None = None) -> None:
		super().__init__(message)
		self.response = response


class OpsiLicenseConfigurationError(OpsiError):
	"""Exception raised if a configuration error occurs in the license data base."""


class OpsiLicenseMissingError(OpsiError):
	"""Exception raised if a license is requested but cannot be found."""


class OpsiRepositoryError(OpsiError):
	"""Exception raised if an error occurs when accessing an OPSI repository."""
