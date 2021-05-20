# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
BackendManager configuration helper.
"""

import os
import socket
import sys
from functools import lru_cache

from OPSI.Exceptions import BackendConfigurationError


def loadBackendConfig(path):
	"""
	Load the backend configuration at `path`.
	:param path: Path to the configuration file to load.
	:type path: str
	:rtype: dict
	"""
	if not os.path.exists(path):
		raise BackendConfigurationError(u"Backend config file '%s' not found" % path)

	moduleGlobals = {
		'config': {},  # Will be filled after loading
		'module': '',  # Will be filled after loading
		'os': os,
		'socket': socket,
		'sys': sys,
	}

	exec(_readFile(path), moduleGlobals)  # pylint: disable=exec-used

	return moduleGlobals


@lru_cache(maxsize=None)
def _readFile(path):
	with open(path) as configFile:
		return configFile.read()
