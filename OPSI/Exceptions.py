# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
OPSI Exceptions.
Deprecated, use opsicommon.exceptions instead.
"""

from opsicommon.exceptions import *  # pylint: disable=wildcard-import,unused-wildcard-import


class CommandNotFoundException(RuntimeError):
	pass
