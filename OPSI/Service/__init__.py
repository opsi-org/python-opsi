# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Service functionality.
"""

from opsicommon.logging import get_logger

from OPSI.Service.Session import SessionHandler

logger = get_logger("opsi.general")


class OpsiService(object):
	def __init__(self):
		self._sessionHandler = None

	def _getSessionHandler(self):
		if self._sessionHandler is None:
			self._sessionHandler = SessionHandler()
		return self._sessionHandler

	def getInterface(self):
		return {}
