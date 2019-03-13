# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

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
Basic backend.

This holds the basic backend classes.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import threading
from contextlib import contextmanager

from .Base import describeInterface, Backend
from .Base import ConfigDataBackend
from .Base import getArgAndCallString, ExtendedBackend, ExtendedConfigDataBackend
from .Base import ModificationTrackingBackend, BackendModificationListener

__all__ = (
	'describeInterface', 'getArgAndCallString', 'temporaryBackendOptions',
	'DeferredCall', 'Backend', 'ExtendedBackend', 'ConfigDataBackend',
	'ExtendedConfigDataBackend',
	'ModificationTrackingBackend', 'BackendModificationListener'
)


@contextmanager
def temporaryBackendOptions(backend, **options):
	oldOptions = backend.backend_getOptions()
	try:
		backend.backend_setOptions(options)
		yield
	finally:
		backend.backend_setOptions(oldOptions)


class DeferredCall(object):
	def __init__(self, callback=None):
		self.error = None
		self.result = None
		self.finished = threading.Event()
		self.callback = callback
		self.callbackArgs = []
		self.callbackKwargs = {}

	def waitForResult(self):
		self.finished.wait()
		if self.error:
			raise self.error  # pylint: disable=raising-bad-type
		return self.result

	def setCallback(self, callback, *args, **kwargs):
		self.callback = callback
		self.callbackArgs = args
		self.callbackKwargs = kwargs

	def _gotResult(self):
		self.finished.set()
		if self.callback:
			self.callback(self, *self.callbackArgs, **self.callbackKwargs)
