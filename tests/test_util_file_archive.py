#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Util.File.Archive import Archive, PigzMixin, TarArchive


class ArchiveFactoryTestCase(unittest.TestCase):
    def testUnknownFormatsRaiseException(self):
        self.assertRaises(Exception, Archive, 'no_filename', format='unknown')
        # def Archive('no_filename', format=None, compression=None, progressSubject=None):

    def testGivingKnownFormatsDoesNotRaiseException(self):
        tarArchive = Archive('no_file', format='tar')
        cpioArchive = Archive('no_file', format='cpio')

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


if __name__ == '__main__':
    unittest.main()
