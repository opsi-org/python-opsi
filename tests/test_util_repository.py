# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the work with repositories.
"""

import os
import time
from unittest import mock

import pytest
from opsicommon.testing.helpers import http_test_server

from OPSI.Exceptions import RepositoryError
from OPSI.Util.Repository import FileRepository, getFileInfosFromDavXML, getRepository


def testGettingFileRepository():
	repo = getRepository("file:///not-here")
	assert isinstance(repo, FileRepository)


def testGettingRepositoryFailsOnUnsupportedURL():
	with pytest.raises(RepositoryError):
		getRepository("lolnope:///asdf")


def testListingRepository(tempDir):
	repo = FileRepository(url=f"file://{tempDir}")
	assert not repo.content("", recursive=True)

	os.mkdir(os.path.join(tempDir, "foobar"))

	assert 1 == len(repo.content("", recursive=True))
	for content in repo.content("", recursive=True):
		assert content == {"path": "foobar", "type": "dir", "name": "foobar", "size": 0}

	with open(os.path.join(tempDir, "bar"), "w", encoding="utf8"):
		pass

	assert 2 == len(repo.content("", recursive=True))
	assert 2 == len(repo.listdir())
	assert "bar" in repo.listdir()


def testFileRepositoryFailsWithWrongURL():
	with pytest.raises(RepositoryError):
		FileRepository("nofile://nada")


@pytest.fixture
def twistedDAVXMLPath(test_data_path):
	return os.path.join(test_data_path, "util", "davxml", "twisted-davxml.data")


@pytest.fixture
def twistedDAVXML(twistedDAVXMLPath):  # pylint: disable=redefined-outer-name
	with open(twistedDAVXMLPath, "r", encoding="utf8") as file:
		return file.read()


def testGetFileInfosFromDavXML(twistedDAVXML):  # pylint: disable=redefined-outer-name
	content = getFileInfosFromDavXML(twistedDAVXML)
	assert len(content) == 4

	dirs = 0
	files = 0
	for item in content:
		assert isinstance(item["size"], int)
		if item["type"] == "dir":
			dirs = dirs + 1
		elif item["type"] == "file":
			files = files + 1
		else:
			raise ValueError(f"Unexpected type '{item['type']}' found. Maybe creepy testdata?")

	assert dirs == 1
	assert files == 3


def test_file_repo_start_end(tmpdir):
	src_dir = tmpdir.mkdir("src")
	src = src_dir.join("test.txt")
	src.write("123456789")
	dst_dir = tmpdir.mkdir("dst")
	dst = dst_dir.join("test.txt")

	with http_test_server(serve_directory=src_dir) as server:
		for repo_url in (f"file://{src_dir}", f"http://localhost:{server.port}"):
			repo = getRepository(repo_url)
			repo.download("test.txt", str(dst), startByteNumber=-1, endByteNumber=-1)
			assert dst.read() == "123456789"

			repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=-1)
			assert dst.read() == "123456789"

			repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=0)
			assert dst.read() == "1"

			repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=1)
			assert dst.read() == "12"

			repo.download("test.txt", str(dst), startByteNumber=1, endByteNumber=1)
			assert dst.read() == "2"

			repo.download("test.txt", str(dst), startByteNumber=0, endByteNumber=2)
			assert dst.read() == "123"

			repo.download("test.txt", str(dst), startByteNumber=5, endByteNumber=8)
			assert dst.read() == "6789"


@pytest.mark.parametrize("repo_type,dynamic", [("file", False), ("http", False), ("http", True)])
def test_limit_download(tmpdir, repo_type, dynamic):
	data = "o" * 2_000_000
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

	def get_network_usage(self):  # pylint: disable=unused-argument
		traffic_ratio = repo.speed_limiter._dynamic_bandwidth_threshold_no_limit  # pylint: disable=protected-access
		if simulate_other_traffic:
			traffic_ratio = repo.speed_limiter._dynamic_bandwidth_limit_rate  # pylint: disable=protected-access

		bandwidth = int(repo.speed_limiter._average_speed / traffic_ratio)  # pylint: disable=protected-access
		if repo._bytesTransfered >= len(data) * 0.8:  # pylint: disable=protected-access
			if simulate_other_traffic:
				assert (
					repo.speed_limiter._dynamic_bandwidth_limit / bandwidth  # pylint: disable=protected-access
				) <= repo.speed_limiter._dynamic_bandwidth_limit_rate * 2  # pylint: disable=protected-access
			else:
				assert repo.speed_limiter._dynamic_bandwidth_limit == 0  # pylint: disable=protected-access
		return bandwidth

	# Setting DEFAULT_BUFFER_SIZE to slow down transfer
	with mock.patch("OPSI.Util.Repository.Repository.DEFAULT_BUFFER_SIZE", 1000 if dynamic else 32 * 1000):
		if repo_type.startswith(("http", "webdav")):
			with http_test_server(serve_directory=src_dir) as server:
				repo_url = f"{repo_type}://localhost:{server.port}"
				repo = getRepository(repo_url, maxBandwidth=0 if dynamic else limit, dynamicBandwidth=dynamic)
				with mock.patch("OPSI.Util.Repository.SpeedLimiter._get_network_usage", get_network_usage):
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
		with http_test_server(serve_directory=dst_dir) as server:
			upload(f"{repo_type}://localhost:{server.port}")
	else:
		upload(f"{repo_type}://{dst_dir}")
