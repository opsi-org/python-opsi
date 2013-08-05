#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Util.File.Archive import TarArchive, PigzMixin
from OPSI.System import which, execute
from OPSI.Util import compareVersions


def is_pigz_installed():
    def is_correct_pigz_version():
        ver = execute('pigz --version')[5:]
        return compareVersions(ver, '>=', '2.2.3')

    try:
        which('pigz')
        has_pigz = is_correct_pigz_version()
    except Exception:
        has_pigz = False

    return has_pigz


class TarArchiveTestCase(unittest.TestCase):
    def test_pigz_detection(self):
        self.assertEqual(is_pigz_installed(), TarArchive.is_pigz_available())


class PigzMixinTestCase(unittest.TestCase):
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
        pigz_installed = is_pigz_installed()
        self.assertEqual(pigz_installed, self.test_object.pigz_detected)
        self.assertEqual(pigz_installed, self.test_object.is_pigz_available())


if __name__ == '__main__':
    unittest.main()
