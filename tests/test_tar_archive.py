#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Util.File.Archive import TarArchive, PigzMixin


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
