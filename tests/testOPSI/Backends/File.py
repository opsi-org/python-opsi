# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Mixins that provide an ready to use File backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import grp
import os
import pwd
import shutil
import tempfile
from contextlib import contextmanager

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.File import FileBackend

from . import BackendMixin
from ..helpers import workInTemporaryDirectory


class FileBackendMixin(BackendMixin):
    BACKEND_SUBFOLDER = os.path.join('etc', 'opsi')
    CONFIG_DIRECTORY = os.path.join('var', 'lib', 'opsi')
    CREATES_INVENTORY_HISTORY = False

    def setUpBackend(self):
        self._fileBackendConfig = {}
        self._fileTempDir = self._copyOriginalBackendToTemporaryLocation()

        self.backend = ExtendedConfigDataBackend(FileBackend(**self._fileBackendConfig))
        self.backend.backend_createBase()

    def _copyOriginalBackendToTemporaryLocation(self):
        tempDir = tempfile.mkdtemp()
        originalBackendDir = _getOriginalBackendLocation()

        shutil.copytree(originalBackendDir, os.path.join(tempDir, self.BACKEND_SUBFOLDER))

        self._setupFileBackend(tempDir)
        self._patchDispatchConfig(tempDir)

        return tempDir

    def _setupFileBackend(self, targetDirectory):
        self._patchFileBackend(targetDirectory)
        self._createClientTemplateFolders(os.path.join(targetDirectory, self.CONFIG_DIRECTORY))

    def _patchFileBackend(self, backendDirectory):
        baseDir = os.path.join(backendDirectory, self.CONFIG_DIRECTORY, 'config')
        hostKeyDir = os.path.join(backendDirectory, self.BACKEND_SUBFOLDER, 'pckeys')

        currentGroupId = os.getgid()
        groupName = grp.getgrgid(currentGroupId)[0]

        userName = pwd.getpwuid(os.getuid())[0]

        self._fileBackendConfig.update(dict(basedir=baseDir, hostKeyFile=hostKeyDir, fileGroupName=groupName, fileUserName=userName))

        config_file = os.path.join(backendDirectory, self.BACKEND_SUBFOLDER, 'backends', 'file.conf')
        with open(config_file, 'w') as config:
            new_configuration = """
# -*- coding: utf-8 -*-

module = 'File'
config = {{
    "baseDir": u"{basedir}",
    "hostKeyFile": u"{keydir}",
    "fileGroupName": u"{groupName}",
    "fileUserName": u"{userName}",
}}
""".format(basedir=baseDir, keydir=hostKeyDir, groupName=groupName, userName=userName)

            config.write(new_configuration)

    @classmethod
    def _createClientTemplateFolders(cls, targetDirectory):
        templateDirectory = os.path.join(targetDirectory, 'config', 'templates')
        os.makedirs(templateDirectory)

    def _patchDispatchConfig(self, targetDirectory):
        configDir = os.path.join(targetDirectory, self.BACKEND_SUBFOLDER, 'backends')
        dispatchConfigPath = os.path.join(configDir, 'dispatch.conf')

        self._fileBackendConfig['dispatchConfig'] = dispatchConfigPath

        with open(dispatchConfigPath, 'w') as dpconf:
            dpconf.write("""
.* : file
""")

    def tearDownBackend(self):
        self.backend.backend_deleteBase()

        try:
            shutil.rmtree(self._fileTempDir)
        except OSError:
            pass

        del self.backend


@contextmanager
def getFileBackend(path=None, **backendOptions):
    originalLocation = _getOriginalBackendLocation()

    BACKEND_SUBFOLDER = os.path.join('etc', 'opsi')
    CONFIG_DIRECTORY = os.path.join('var', 'lib', 'opsi')

    with workInTemporaryDirectory(path) as tempDir:
        shutil.copytree(originalLocation, os.path.join(tempDir, BACKEND_SUBFOLDER))

        baseDir = os.path.join(tempDir, CONFIG_DIRECTORY, 'config')
        os.makedirs(baseDir)  # Usually done in OS package
        hostKeyFile = os.path.join(tempDir, BACKEND_SUBFOLDER, 'pckeys')

        currentGroupId = os.getgid()
        groupName = grp.getgrgid(currentGroupId)[0]

        userName = pwd.getpwuid(os.getuid())[0]

        backendConfig = {
            "baseDir": baseDir,
            "hostKeyFile": hostKeyFile,
            "fileGroupName": groupName,
            "fileUserName": userName
        }
        backendConfig.update(backendOptions)

        new_configuration = """
# -*- coding: utf-8 -*-

module = 'File'
config = {{
    "baseDir": u"{baseDir}",
    "hostKeyFile": u"{hostKeyFile}",
    "fileGroupName": u"{fileGroupName}",
    "fileUserName": u"{fileUserName}",
}}
""".format(**backendConfig)

        config_file = os.path.join(tempDir, BACKEND_SUBFOLDER, 'backends', 'file.conf')
        with open(config_file, 'w') as config:
            config.write(new_configuration)

        yield FileBackend(**backendConfig)


def _getOriginalBackendLocation():
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'data'
        )
    )
