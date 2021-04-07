# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the work with archives.
"""

import os

import pytest

from OPSI.Util.File.Archive import getFileType, Archive, PigzMixin, TarArchive

from .helpers import mock


def testArchiveFactoryRaisesExceptionOnUnknownFormat():
	with pytest.raises(Exception):
		Archive('no_filename', format='unknown')


@pytest.mark.parametrize("fileFormat", ["tar", "cpio"])
def testCreatingArchive(fileFormat):
	Archive('no_file', format=fileFormat)


def testRaisingExceptionIfFiletypeCanNotBeDetermined():
	with pytest.raises(Exception):
		Archive(__file__)


def testPigzDetectionOnTarArchive():
	assert PigzMixin.is_pigz_available() == TarArchive.is_pigz_available()


@pytest.fixture
def dumbArchive():
	class DumbArchive(PigzMixin):
		pass

	yield DumbArchive()


def testPigzMixinProvidesMethods(dumbArchive):
	assert hasattr(dumbArchive, 'pigz_detected')
	assert hasattr(dumbArchive, 'is_pigz_available')


def testPigzMixinMethods(dumbArchive):
	assert PigzMixin.is_pigz_available() == dumbArchive.pigz_detected
	assert PigzMixin.is_pigz_available() == dumbArchive.is_pigz_available()


def testDisablingPigz(dumbArchive):
	"""
	Disabling the usage of pigz by setting PIGZ_ENABLED to False.
	"""
	with mock.patch('OPSI.Util.File.Archive.PIGZ_ENABLED', False):
		assert dumbArchive.is_pigz_available() is False
