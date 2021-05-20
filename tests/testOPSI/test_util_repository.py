# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the work with repositories.
"""

import os
import pytest

from OPSI.Exceptions import RepositoryError
from OPSI.Util.Repository import FileRepository, getRepository, getFileInfosFromDavXML


def testGettingFileRepository():
	repo = getRepository("file:///not-here")
	assert isinstance(repo, FileRepository)


def testGettingRepositoryFailsOnUnsupportedURL():
	with pytest.raises(RepositoryError):
		getRepository("lolnope:///asdf")


def testListingRepository(tempDir):
	repo = FileRepository(url=u'file://{path}'.format(path=tempDir))
	assert not repo.content('', recursive=True)

	os.mkdir(os.path.join(tempDir, "foobar"))

	assert 1 == len(repo.content('', recursive=True))
	for content in repo.content('', recursive=True):
		assert content == {'path': u'foobar', 'type': 'dir', 'name': u'foobar', 'size': 0}

	with open(os.path.join(tempDir, "bar"), "w"):
		pass

	assert 2 == len(repo.content('', recursive=True))
	assert 2 == len(repo.listdir())
	assert "bar" in repo.listdir()

	# TODO: list subdir tempDir and check if file is shown


def testFileRepositoryFailsWithWrongURL():
	with pytest.raises(RepositoryError):
		FileRepository(u'nofile://nada')


@pytest.fixture
def twistedDAVXMLPath():
	return os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'davxml', 'twisted-davxml.data')


@pytest.fixture
def twistedDAVXML(twistedDAVXMLPath):
	with open(twistedDAVXMLPath, 'r') as f:
		return f.read()


def testGetFileInfosFromDavXML(twistedDAVXML):
	content = getFileInfosFromDavXML(twistedDAVXML)
	assert len(content) == 4

	dirs = 0
	files = 0
	for item in content:
		assert isinstance(item['size'], int)
		if item['type'] == 'dir':
			dirs = dirs + 1
		elif item['type'] == 'file':
			files = files + 1
		else:
			raise ValueError("Unexpected type {!r} found. Maybe creepy testdata?".format(item['type']))

	assert dirs == 1
	assert files == 3

def test_file_repo_start_end(tmpdir):
	src_dir = tmpdir.mkdir("src")
	src = src_dir.join("test.txt")
	src.write("123456789")
	dst_dir = tmpdir.mkdir("dst")
	dst = dst_dir.join("test.txt")

	repo = getRepository(f"file://{src_dir}")
	repo.download("test.txt", str(dst), startByteNumber=-1, endByteNumber=-1)
	assert dst.read() == "123456789"

	repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=-1)
	assert dst.read() == "123456789"

	repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=1)
	assert dst.read() == "1"

	repo.download("test.txt", str(dst), startByteNumber=1, endByteNumber=1)
	assert dst.read() == ""

	repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=2)
	assert dst.read() == "12"

	repo.download("test.txt", str(dst), startByteNumber=5, endByteNumber=9)
	assert dst.read() == "6789"

