#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import tempfile
import unittest

from OPSI.Util.File.Opsi import OpsiBackupArchive
from OPSI.Util import randomString


class BackendArchiveTestCase(unittest.TestCase):
    def setUp(self):
        self._tempDir = tempfile.gettempdir()

    def tearDown(self):
        try:
            if os.path.exists(self.archive.name):
                os.remove(self.archive.name)
        except AttributeError:
            pass

    def createArchive(self, **kwargs):
        """
        Creates an archive with the given keyword arguments.
        """
        kwargs['tempdir'] = self._tempDir
        self._kwargs = kwargs
        self.archive = OpsiBackupArchive(**kwargs)

    def testArchiveGetsCreated(self):
        self.createArchive()
        self.assertTrue(os.path.exists(self.archive.name))

    def testArchiveCanBeNamed(self):
        randomName = os.path.join(self._tempDir, '{0}.tar'.format(randomString(16)))
        self.createArchive(name=randomName, mode="w")

        self.assertTrue(os.path.exists(self.archive.name))
