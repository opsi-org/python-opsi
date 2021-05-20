# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Backends.
"""

from __future__ import absolute_import

from .Backend import describeInterface, Backend
from .ConfigData import ConfigDataBackend
from .Extended import (
	getArgAndCallString, ExtendedBackend, ExtendedConfigDataBackend)
from .ModificationTracking import (
	ModificationTrackingBackend, BackendModificationListener)

__all__ = (
	'describeInterface', 'getArgAndCallString',
	'Backend', 'ExtendedBackend', 'ConfigDataBackend',
	'ExtendedConfigDataBackend',
	'ModificationTrackingBackend', 'BackendModificationListener'
)
