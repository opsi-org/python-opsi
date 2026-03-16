# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only


from ._common import (
	OperatingSystemUnsupportedError,
	OpsiBadRpcError,
	OpsiError,
	OpsiLicenseConfigurationError,
	OpsiLicenseMissingError,
	OpsiRepositoryError,
	OpsiRpcError,
	OpsiServiceAuthenticationError,
	OpsiServiceClientCertificateError,
	OpsiServiceConnectionError,
	OpsiServiceConnectionRefusedError,
	OpsiServiceError,
	OpsiServicePermissionError,
	OpsiServiceTimeoutError,
	OpsiServiceUnavailableError,
	OpsiServiceVerificationError,
)

__all__ = [
	"OpsiError",
	"OperatingSystemUnsupportedError",
	"OpsiBadRpcError",
	"OpsiLicenseConfigurationError",
	"OpsiLicenseMissingError",
	"OpsiRepositoryError",
	"OpsiRpcError",
	"OpsiServiceAuthenticationError",
	"OpsiServiceClientCertificateError",
	"OpsiServiceConnectionError",
	"OpsiServiceConnectionRefusedError",
	"OpsiServiceError",
	"OpsiServicePermissionError",
	"OpsiServiceTimeoutError",
	"OpsiServiceUnavailableError",
	"OpsiServiceVerificationError",
	"RepositoryError",
]
