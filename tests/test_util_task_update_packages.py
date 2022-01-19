# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the opsi-package-updater functionality.
"""

import os
import shutil
import json

import pytest

from opsicommon.testing.helpers import http_test_server

from OPSI.Util import md5sum
from OPSI.Util.File import ZsyncFile
from OPSI.Util.Task.UpdatePackages import OpsiPackageUpdater
from OPSI.Util.Task.UpdatePackages.Notifier import DummyNotifier
from OPSI.Util.Task.UpdatePackages.Config import DEFAULT_CONFIG
from OPSI.Util.Task.UpdatePackages.Repository import ProductRepositoryInfo, LinksExtractor

from .helpers import mock, createTemporaryTestfile, workInTemporaryDirectory
from .test_hosts import getConfigServer


@pytest.fixture
def package_updater_class(backendManager) -> OpsiPackageUpdater:
	configServer = getConfigServer()
	backendManager.host_insertObject(configServer)

	klass = OpsiPackageUpdater
	with mock.patch.object(klass, "getConfigBackend", return_value=backendManager):
		yield klass


def test_listing_local_packages(package_updater_class):  # pylint: disable=redefined-outer-name
	with workInTemporaryDirectory() as tempDir:
		configFile = os.path.join(tempDir, 'emptyconfig.conf')
		with open(configFile, 'wb'):
			pass

		filenames = [
			'not.tobefound.opsi.nono',
			'thingy_1.2-3.opsi', 'thingy_1.2-3.opsi.no'
		]

		for filename in filenames:
			with open(os.path.join(tempDir, filename), 'wb'):
				pass

		config = DEFAULT_CONFIG.copy()
		config['packageDir'] = tempDir
		config['configFile'] = configFile

		packageUpdater = package_updater_class(config)
		localPackages = packageUpdater.getLocalPackages()
		packageInfo = localPackages.pop()
		assert not localPackages, "There should only be one package!"

		expectedInfo = {
			"productId": "thingy",
			"version": "1.2-3",
			"packageFile": os.path.join(tempDir, 'thingy_1.2-3.opsi'),
			"filename": "thingy_1.2-3.opsi",
			"md5sum": None
		}

		assert set(packageInfo.keys()) == set(expectedInfo.keys())
		assert packageInfo['md5sum']  # We want any value

		del expectedInfo['md5sum']  # Not comparing this
		for key, expectedValue in expectedInfo.items():
			assert packageInfo[key] == expectedValue


@pytest.fixture
def example_config_path(test_data_path):
	filePath = os.path.join(test_data_path, 'util', 'task', 'updatePackages', 'example_updater.conf')
	with createTemporaryTestfile(filePath) as newPath:
		yield newPath


def test_parsing_config_file(example_config_path, package_updater_class):  # pylint: disable=redefined-outer-name
	with workInTemporaryDirectory() as tempDir:
		preparedConfig = DEFAULT_CONFIG.copy()
		preparedConfig['packageDir'] = tempDir
		preparedConfig['configFile'] = example_config_path

		repoPath = os.path.join(tempDir, 'repos.d')
		os.mkdir(repoPath)

		patch_config_file(example_config_path, packageDir=tempDir, repositoryConfigDir=repoPath)
		copy_example_repo_configs(repoPath)

		packageUpdater = package_updater_class(preparedConfig)
		config = packageUpdater.config

		assert config
		assert config['repositories']
		assert len(config['repositories']) == 3
		for repo in config['repositories']:
			assert isinstance(repo, ProductRepositoryInfo)

		assert config['packageDir'] == tempDir
		assert config['tempdir'] == '/tmp'
		assert config['repositoryConfigDir'] == repoPath

		# Global proxy
		assert not config['proxy']

		# e-mail notification settings
		assert config['notification'] is False
		assert config['smtphost'] == 'smtp'
		assert config['smtpport'] == 25
		assert config['smtpuser'] == DEFAULT_CONFIG['smtpuser']
		assert config['smtppassword'] == DEFAULT_CONFIG['smtppassword']
		assert config['use_starttls'] is False
		assert config['sender'] == 'opsi-package-updater@localhost'
		assert config['receivers'] == ['root@localhost', 'anotheruser@localhost']
		assert config['subject'] == 'opsi-package-updater example config'

		# Automatic installation settings
		assert config['installationWindowStartTime'] == '01:23'
		assert config['installationWindowEndTime'] == '04:56'
		assert config['installationWindowExceptions'] == ['firstproduct', 'second-product']

		# Wake-On-LAN settings
		assert config['wolAction'] is False
		assert config['wolActionExcludeProductIds'] == ['this', 'that']
		assert config['wolShutdownWanted'] is True
		assert config['wolStartGap'] == 10


def patch_config_file(filename, **values):
	with open(filename, encoding="utf-8") as configFile:
		lines = configFile.readlines()

	newLines = []
	for line in lines:
		for key, value in values.items():
			if line.startswith(key):
				newLines.append(f'{key} = {value}\n')
				break
		else:
			newLines.append(line)

	with open(filename, 'w', encoding="utf-8") as configFile:
		for line in newLines:
			configFile.write(line)


def copy_example_repo_configs(targetDir):
	from .conftest import TEST_DATA_PATH  # pylint: disable=import-outside-toplevel
	for filename in ('experimental.repo', ):
		filePath = os.path.join(TEST_DATA_PATH, 'util', 'task', 'updatePackages', filename)
		shutil.copy(filePath, targetDir)


@pytest.fixture(
	params=['apachelisting.html'],
	ids=['apache']
)
def repository_listing_page(test_data_path, request):
	filePath = os.path.join(test_data_path, 'util', 'task', 'updatePackages', request.param)

	with open(filePath, encoding="utf-8") as exampleFile:
		return exampleFile.read()


def test_link_extracting(repositoryListingPage):  # pylint: disable=redefined-outer-name
	extractor = LinksExtractor()
	extractor.feed(repositoryListingPage)
	extractor.close()

	for _link in extractor.getLinks():
		# Currently just checking their existance
		break
	else:
		raise RuntimeError("No links found!")


def test_global_proxy_applied_to_repos(example_config_path, package_updater_class):  # pylint: disable=redefined-outer-name
	testProxy = 'http://hurr:durr@someproxy:1234'

	with workInTemporaryDirectory() as tempDir:
		preparedConfig = DEFAULT_CONFIG.copy()
		preparedConfig['packageDir'] = tempDir
		preparedConfig['configFile'] = example_config_path

		repoPath = os.path.join(tempDir, 'repos.d')
		os.mkdir(repoPath)

		patch_config_file(example_config_path, packageDir=tempDir, repositoryConfigDir=repoPath, proxy=testProxy)
		copy_example_repo_configs(repoPath)

		packageUpdater = package_updater_class(preparedConfig)
		config = packageUpdater.config

		assert config['proxy'] == testProxy

		for repo in config['repositories']:
			print(repo.active)
			assert repo.proxy == testProxy


def test_check_accept_ranges(tmp_path, package_updater_class):  # pylint: disable=redefined-outer-name,too-many-locals
	config_file = tmp_path / "empty.conf"
	config_file.touch()
	local_dir = tmp_path / "local_packages"
	local_dir.mkdir()
	server_dir = tmp_path / "server_packages"
	server_dir.mkdir()
	repo_conf_path = tmp_path / "repos.d"
	repo_conf_path.mkdir()
	test_repo_conf = repo_conf_path / "test.repo"
	server_log = tmp_path / "server.log"

	config = DEFAULT_CONFIG.copy()
	config['configFile'] = str(config_file)
	config['packageDir'] = str(local_dir)

	config_file.write_text(
		data=(
			"[general]\n"
			f"packageDir = {str(local_dir)}\n"
			f"repositoryConfigDir = {str(repo_conf_path)}\n"

		),
		encoding="utf-8"
	)

	server_package_file = server_dir / "test1_1.2-3.opsi"
	server_package_file.write_bytes(b"data" * 200)
	zsync_file = server_dir / "test1_1.2-3.opsi.zsync"
	ZsyncFile(str(zsync_file)).generate(str(server_package_file))
	md5sum_file = server_dir / "test1_1.2-3.opsi.md5"
	server_package_md5sum = md5sum(str(server_package_file))
	md5sum_file.write_text(server_package_md5sum, encoding="ascii")

	def write_repo_conf(server_port):
		test_repo_conf.write_text(
			data=(
				"[repository_test]\n"
				"active = true\n"
				f"baseUrl = http://localhost:{server_port}\n"
				"dirs = /\n"
				"autoInstall = true\n"
			),
			encoding="utf-8"
		)

	for accept_ranges in (True, False):
		with http_test_server(
			serve_directory=server_dir,
			response_headers={"accept-ranges": "bytes"} if accept_ranges else None,
			log_file=str(server_log)
		) as server:
			write_repo_conf(server.port)

			local_package_file = local_dir / "test1_1.2-1.opsi"
			local_package_file.write_bytes(b"data" * 100)

			package_updater: OpsiPackageUpdater = package_updater_class(config)

			availabale_packages = package_updater.getDownloadablePackages()
			local_packages = package_updater.getLocalPackages()

			assert len(availabale_packages) == 1
			package = availabale_packages[0]
			assert package["productId"] == "test1"
			assert package["version"] == "1.2-3"
			assert package["packageFile"] == f"http://localhost:{server.port}/test1_1.2-3.opsi"
			assert package["filename"] == server_package_file.name
			assert package["md5sum"] == server_package_md5sum
			assert package["zsyncFile"] == f"http://localhost:{server.port}/{zsync_file.name}"
			assert package["acceptRanges"] is accept_ranges
			assert package_updater._useZsync(package, local_packages[0]) == accept_ranges  # pylint: disable=protected-access

			server_log.unlink()
			new_packages = package_updater.get_packages(DummyNotifier())
			assert len(new_packages) == 1

			assert md5sum(str(local_dir / server_package_file.name)) == server_package_md5sum

			request = json.loads(server_log.read_text(encoding="utf-8").rstrip().split("\n")[-1])
			server_log.unlink()
			# print(request)
			if accept_ranges:
				assert "Range" in request["headers"]
			else:
				assert "Range" not in request["headers"]
