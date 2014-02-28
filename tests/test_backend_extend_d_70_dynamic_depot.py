#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import unittest

from OPSI.Logger import Logger
from .Backends.File import ExtendedFileBackendMixin


logger = Logger()


class DynamicDepotTestCase(unittest.TestCase, ExtendedFileBackendMixin):
	def setUp(self):
		self.setUpBackend()

	def tearDown(self):
		self.tearDownBackend()

	def testDefaultConfigurationIsExecutable(self):
		algo = self.backend.getDepotSelectionAlgorithm()
		exec(algo)
		selectDepot({}, 'asdf.lol.noob')


if __name__ == '__main__':
	unittest.main()
