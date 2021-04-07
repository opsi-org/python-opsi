# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Functionality to update OPSI backends.

.. versionadded:: 4.0.6.1
"""


class BackendUpdateError(RuntimeError):
	"This error indicates a problem during a backend update."
