# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
OPSI Exceptions.

:copyright:	uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Types import forceUnicode


__all__ = (
	'BackendAuthenticationError', 'BackendBadValueError',
	'BackendConfigurationError', 'BackendError', 'BackendIOError',
	'BackendMissingDataError', 'BackendModuleDisabledError',
	'BackendPermissionDeniedError', 'BackendReferentialIntegrityError',
	'BackendTemporaryError', 'BackendUnableToConnectError',
	'BackendUnaccomplishableError',
	'CanceledException', 'LicenseConfigurationError', 'LicenseMissingError',
	'OpsiAuthenticationError', 'OpsiBackupBackendNotFound',
	'OpsiBackupFileError', 'OpsiBackupFileNotFound', 'OpsiBadRpcError',
	'OpsiConnectionError', 'OpsiError', 'OpsiProductOrderingError',
	'OpsiRpcError', 'OpsiServiceVerificationError', 'OpsiTimeoutError',
	'RepositoryError',
)


class OpsiError(Exception):
	""" Base class for OPSI Backend exceptions. """

	ExceptionShortDescription = "Opsi error"
	_message = None

	def __init__(self, message=''):
		self._message = forceUnicode(message)

	def __str__(self):
		if self._message:
			return u"%s: %s" % (self.ExceptionShortDescription, self._message)
		else:
			return u"%s" % self.ExceptionShortDescription

	def __repr__(self):
		if self._message and self._message != u'None':
			text = u"<{0}({1!r})>".format(self.__class__.__name__, self._message)
		else:
			text = u"<{0}()>".format(self.__class__.__name__)

		return text

	complete_message = __str__

	def message():
		def get(self):
			return self._message

		def set(self, message):
			self._message = forceUnicode(message)

		return property(get, set)


class OpsiBackupFileError(OpsiError):
	ExceptionShortDescription = u"Opsi backup file error"


class OpsiBackupFileNotFound(OpsiBackupFileError):
	ExceptionShortDescription = u"Opsi backup file not found"


class OpsiBackupBackendNotFound(OpsiBackupFileError):
	ExceptionShortDescription = u"Opsi backend not found in backup"


class OpsiAuthenticationError(OpsiError):
	ExceptionShortDescription = u"Opsi authentication error"


class OpsiServiceVerificationError(OpsiError):
	ExceptionShortDescription = u"Opsi service verification error"


class OpsiBadRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi bad rpc error"


class OpsiRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi rpc error"


class OpsiConnectionError(OpsiError):
	ExceptionShortDescription = u"Opsi connection error"


class OpsiTimeoutError(OpsiError):
	ExceptionShortDescription = u"Opsi timeout error"


class OpsiProductOrderingError(OpsiError):
	ExceptionShortDescription = u"A condition for ordering cannot be fulfilled"

	def __init__(self, message='', problematicRequirements=None):
		problematicRequirements = problematicRequirements or []

		self._message = forceUnicode(message)
		self.problematicRequirements = problematicRequirements

	def __repr__(self):
		if self._message and self._message != u'None':
			text = u"<{0}({1!r}, {2!r})>".format(self.__class__.__name__, self._message, self.problematicRequirements)
		else:
			text = u"<{0}()>".format(self.__class__.__name__)

		return text

	def __str__(self):
		if self._message:
			if self.problematicRequirements:
				return u"{0}: {1} ({2})".format(self.ExceptionShortDescription, self._message, self.problematicRequirements)
			else:
				return u"{0}: {1}".format(self.ExceptionShortDescription, self._message)
		else:
			return forceUnicode(self.ExceptionShortDescription)


class BackendError(OpsiError):
	""" Exception raised if there is an error in the backend. """
	ExceptionShortDescription = u"Backend error"


class BackendIOError(OpsiError):
	""" Exception raised if there is a read or write error in the backend. """
	ExceptionShortDescription = u"Backend I/O error"


class BackendUnableToConnectError(BackendIOError):
	"Exception raised if no connection can be established in the backend."
	ExceptionShortDescription = u"Backend I/O error"


class BackendConfigurationError(OpsiError):
	""" Exception raised if a configuration error occurs in the backend. """
	ExceptionShortDescription = u"Backend configuration error"


class BackendReferentialIntegrityError(OpsiError):
	"""
	Exception raised if there is a referential integration
	error occurs in the backend.
	"""
	ExceptionShortDescription = u"Backend referential integrity error"


class BackendBadValueError(OpsiError):
	""" Exception raised if a malformed value is found. """
	ExceptionShortDescription = u"Backend bad value error"


class BackendMissingDataError(OpsiError):
	""" Exception raised if expected data not found. """
	ExceptionShortDescription = u"Backend missing data error"


class BackendAuthenticationError(OpsiAuthenticationError):
	""" Exception raised if authentication failes. """
	ExceptionShortDescription = u"Backend authentication error"


class BackendPermissionDeniedError(OpsiError):
	""" Exception raised if a permission is denied. """
	ExceptionShortDescription = u"Backend permission denied error"


class BackendTemporaryError(OpsiError):
	""" Exception raised if a temporary error occurs. """
	ExceptionShortDescription = u"Backend temporary error"


class BackendUnaccomplishableError(OpsiError):
	"Exception raised if an unaccomplishable situation appears"

	ExceptionShortDescription = u"Backend unaccomplishable error"


class BackendModuleDisabledError(OpsiError):
	""" Exception raised if a needed module is disabled. """
	ExceptionShortDescription = u"Backend module disabled error"


class LicenseConfigurationError(OpsiError):
	"""
	Exception raised if a configuration error occurs in the license data base.
	"""
	ExceptionShortDescription = u"License configuration error"


class LicenseMissingError(OpsiError):
	""" Exception raised if a license is requested but cannot be found. """
	ExceptionShortDescription = u"License missing error"


class RepositoryError(OpsiError):
	ExceptionShortDescription = u"Repository error"


class CanceledException(Exception):
	ExceptionShortDescription = u"CanceledException"
