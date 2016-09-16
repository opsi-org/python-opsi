#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Testing the work with archives.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import mock
import unittest

from OPSI.Util.File.Archive import Archive, PigzMixin, TarArchive


class ArchiveFactoryTestCase(unittest.TestCase):
    def testUnknownFormatsRaiseException(self):
        self.assertRaises(Exception, Archive, 'no_filename', format='unknown')

    def testGivingKnownFormatsDoesNotRaiseException(self):
        Archive('no_file', format='tar')
        Archive('no_file', format='cpio')

    def testRaisingExceptionIfFiletypeCanNotBeDetermined(self):
        # Checking if the filetype for this python file can be guessed.
        self.assertRaises(Exception, Archive, __file__)


class TarArchiveTestCase(unittest.TestCase):
    def test_pigz_detection(self):
        self.assertEqual(PigzMixin.is_pigz_available(),
            TarArchive.is_pigz_available())


class PigzMixinAppliedTestCase(unittest.TestCase):
    def setUp(self):
        class DumbArchive(PigzMixin):
            pass

        self.test_object = DumbArchive()

    def tearDown(self):
        del self.test_object

    def test_having_mixin_methods(self):
        self.assertTrue(hasattr(self.test_object, 'pigz_detected'))
        self.assertTrue(hasattr(self.test_object, 'is_pigz_available'))

    def test_mixin_methods_work(self):
        self.assertEqual(PigzMixin.is_pigz_available(), self.test_object.pigz_detected)
        self.assertEqual(PigzMixin.is_pigz_available(), self.test_object.is_pigz_available())

    def testDisablingPigz(self):
        """
        Disabling the usage of pigz by setting PIGZ_ENABLED to False.
        """
        with mock.patch('OPSI.Util.File.Archive.PIGZ_ENABLED', False):
            self.assertEqual(False, self.test_object.is_pigz_available())


if __name__ == '__main__':
    unittest.main()
