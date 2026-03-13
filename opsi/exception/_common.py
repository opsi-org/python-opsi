# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only


class OpsiError(Exception):
	"""Base exception for all OPSI errors."""


class OperatingSystemUnsupportedError(OpsiError):
	"""Raised when the operating system is not supported."""
