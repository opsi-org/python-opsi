#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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

from __future__ import absolute_import

import grp
import os
import pwd
import shutil
import tempfile

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.File import FileBackend

from . import BackendMixin


class FileBackendMixin(BackendMixin):
    BACKEND_SUBFOLDER = os.path.join('etc', 'opsi')
    CONFIG_DIRECTORY = os.path.join('var', 'lib', 'opsi')
    CREATES_INVENTORY_HISTORY = False

    def setUpBackend(self):
        self._fileBackendConfig = {}
        self._fileTempDir = self._copyOriginalBackendToTemporaryLocation()

        self.backend = ExtendedConfigDataBackend(FileBackend(**self._fileBackendConfig))
        # TODO: Make use of a BackendManager Backend.
        # This is to easily check if we have a file backend in the tests.
        # With such a check we can easily skip tests.

        self.backend.backend_createBase()

    def _copyOriginalBackendToTemporaryLocation(self):
        tempDir = tempfile.mkdtemp()
        originalBackendDir = self._getOriginalBackendLocation()

        shutil.copytree(originalBackendDir, os.path.join(tempDir, self.BACKEND_SUBFOLDER))

        self._setupFileBackend(tempDir)
        self._patchDispatchConfig(tempDir)

        return tempDir

    @staticmethod
    def _getOriginalBackendLocation():
        return os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), '..', '..', 'data'
            )
        )

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
            dpconf.write(
"""
.* : file
"""
)

    def tearDownBackend(self):
        self.backend.backend_deleteBase()

        if os.path.exists(self._fileTempDir):
            shutil.rmtree(self._fileTempDir)

        del self.backend


class ExtendedFileBackendMixin(FileBackendMixin):
    def setUpBackend(self):
        self._fileBackendConfig = {}
        self._fileTempDir = self._copyOriginalBackendToTemporaryLocation()

        self.backend = BackendManager(
            backend='file',
            backendconfigdir=os.path.join(self._fileTempDir, self.BACKEND_SUBFOLDER, 'backends'),
            extensionconfigdir=os.path.join(self._fileTempDir, self.BACKEND_SUBFOLDER, 'backendManager', 'extend.d')
        )

        self.backend.backend_createBase()
