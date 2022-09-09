# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the work with archives.
"""

import os

import pytest

from OPSI.Util.File.Archive import Archive, TarArchive, getFileType, is_pigz_available

from .helpers import mock


def testArchiveFactoryRaisesExceptionOnUnknownFormat():
	with pytest.raises(Exception):
		Archive("no_filename", format="unknown")


@pytest.mark.parametrize("fileFormat", ["tar", "cpio"])
def testCreatingArchive(fileFormat):
	Archive("no_file", format=fileFormat)


def testRaisingExceptionIfFiletypeCanNotBeDetermined():
	with pytest.raises(Exception):
		Archive(__file__)


def testDisablingPigz(dumbArchive):
	"""
	Disabling the usage of pigz by setting PIGZ_ENABLED to False.
	"""
	with mock.patch("OPSI.Util.File.Archive.PIGZ_ENABLED", False):
		assert is_pigz_available() is False
