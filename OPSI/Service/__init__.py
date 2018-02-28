# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2017 uib GmbH <info@uib.de>

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
Service functionality.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
from OpenSSL import SSL
from OPSI.Service.Session import SessionHandler

from OPSI.Logger import Logger

logger = Logger()


class SSLContext(object):
	def __init__(self, sslServerKeyFile, sslServerCertFile, acceptedCiphers=''):
		"""
		Create a context for the usage of SSL in twisted.

		:param sslServerCertFile: Path to the certificate file.
		:type sslServerCertFile: str
		:param sslServerKeyFile: Path to the key file.
		:type sslServerKeyFile: str
		:param acceptedCiphers: A string defining what ciphers should \
be accepted. Please refer to the OpenSSL documentation on how such a \
string should be composed. No limitation will be done if an empty value \
is set.
		:type acceptedCiphers: str
		"""
		self._sslServerKeyFile = sslServerKeyFile
		self._sslServerCertFile = sslServerCertFile
		self._acceptedCiphers = acceptedCiphers

	def getContext(self):
		'''
		Get an SSL context.

		:rtype: OpenSSL.SSL.Context
		'''

		# Test if server certificate and key file exist.
		if not os.path.isfile(self._sslServerKeyFile):
			raise OSError(u"Server key file {0!r} does not exist!".format(self._sslServerKeyFile))

		if not os.path.isfile(self._sslServerCertFile):
			raise OSError(u"Server certificate file {0!r} does not exist!".format(self._sslServerCertFile))

		context = SSL.Context(SSL.SSLv23_METHOD)
		context.use_privatekey_file(self._sslServerKeyFile)
		context.use_certificate_file(self._sslServerCertFile)

		if self._acceptedCiphers:
			context.set_cipher_list(self._acceptedCiphers)

		return context


class OpsiService(object):
	def __init__(self):
		self._sessionHandler = None

	def _getSessionHandler(self):
		if self._sessionHandler is None:
			self._sessionHandler = SessionHandler()
		return self._sessionHandler

	def getInterface(self):
		return {}
