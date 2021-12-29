# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the work with repositories.
"""

import os
import time

import pytest
import unittest.mock as mock

from OPSI.Exceptions import RepositoryError
from OPSI.Util.Repository import FileRepository, getRepository, getFileInfosFromDavXML

from .helpers import http_file_server

def testGettingFileRepository():
	repo = getRepository("file:///not-here")
	assert isinstance(repo, FileRepository)


def testGettingRepositoryFailsOnUnsupportedURL():
	with pytest.raises(RepositoryError):
		getRepository("lolnope:///asdf")


def testListingRepository(tempDir):
	repo = FileRepository(url='file://{path}'.format(path=tempDir))
	assert not repo.content('', recursive=True)

	os.mkdir(os.path.join(tempDir, "foobar"))

	assert 1 == len(repo.content('', recursive=True))
	for content in repo.content('', recursive=True):
		assert content == {'path': 'foobar', 'type': 'dir', 'name': 'foobar', 'size': 0}

	with open(os.path.join(tempDir, "bar"), "w"):
		pass

	assert 2 == len(repo.content('', recursive=True))
	assert 2 == len(repo.listdir())
	assert "bar" in repo.listdir()

	# TODO: list subdir tempDir and check if file is shown


def testFileRepositoryFailsWithWrongURL():
	with pytest.raises(RepositoryError):
		FileRepository('nofile://nada')


@pytest.fixture
def twistedDAVXMLPath(test_data_path):
	return os.path.join(test_data_path, 'util', 'davxml', 'twisted-davxml.data')


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



@pytest.mark.parametrize("repo_type,dynamic", [("file", False), ("http", False), ("http", True)])
def test_limit_download(tmpdir, repo_type, dynamic):
	#from opsicommon.logging import logging_config
	#logging_config(stderr_level=8)

	data = "o" * 3_000_000
	limit = 100_000

	src_dir = tmpdir.mkdir("src")
	src = src_dir.join("test.txt")
	src.write(data)
	dst_dir = tmpdir.mkdir("dst")
	dst = dst_dir.join("test.txt")

	repo = None
	simulate_other_traffic = False

	def download():
		start = time.time()
		repo.download("test.txt", str(dst))
		end = time.time()

		assert dst.read() == data
		if not dynamic:
			assert abs(round(end - start) - round(len(data) / limit)) <= 1

	def get_network_usage(self):
		traffic_ratio = repo.speed_limiter._dynamic_bandwidth_threshold_no_limit
		if simulate_other_traffic:
			traffic_ratio = repo.speed_limiter._dynamic_bandwidth_limit_rate

		bandwidth = int(repo.speed_limiter._average_speed / traffic_ratio)
		if repo._bytesTransfered >= len(data) * 0.8:
			if simulate_other_traffic:
				assert (repo.speed_limiter._dynamic_bandwidth_limit / bandwidth) <= repo.speed_limiter._dynamic_bandwidth_limit_rate * 1.09
			else:
				assert repo.speed_limiter._dynamic_bandwidth_limit == 0
		return bandwidth

	# Setting DEFAULT_BUFFER_SIZE to slow down transfer
	with mock.patch('OPSI.Util.Repository.Repository.DEFAULT_BUFFER_SIZE', 1000 if dynamic else 32 * 1000):
		if repo_type.startswith(("http", "webdav")):
			with http_file_server(src_dir) as server:
				repo_url = f"{repo_type}://localhost:{server.port}"
				repo = getRepository(repo_url, maxBandwidth=0 if dynamic else limit, dynamicBandwidth=dynamic)
				with mock.patch('OPSI.Util.Repository.SpeedLimiter._get_network_usage', get_network_usage):
					download()
					if dynamic:
						simulate_other_traffic = True
						download()
		else:
			repo_url = f"{repo_type}://{src_dir}"
			repo = getRepository(repo_url, maxBandwidth=limit, dynamicBandwidth=dynamic)
			download()


@pytest.mark.parametrize("repo_type", ["file", "webdav"])
def test_limit_upload(tmpdir, repo_type):
	data = "o" * 1_000_000
	limit = 100_000
	seconds = len(data) / limit

	src_dir = tmpdir.mkdir("src")
	src = src_dir.join("test.txt")
	src.write(data)
	dst_dir = tmpdir.mkdir("dst")
	dst = dst_dir.join("test.txt")

	def upload(repo_url):
		start = time.time()
		repo = getRepository(repo_url, maxBandwidth=limit)
		repo.upload(str(src), "test.txt")
		end = time.time()

		assert dst.read() == data
		assert abs(round(end - start) - round(seconds)) <= 1

	if repo_type.startswith(("http", "webdav")):
		with http_file_server(dst_dir) as server:
			upload(f"{repo_type}://localhost:{server.port}")
	else:
		upload(f"{repo_type}://{dst_dir}")
