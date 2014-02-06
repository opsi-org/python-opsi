#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Util.File.Archive import Archive



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

if __name__ == '__main__':
    unittest.main()
