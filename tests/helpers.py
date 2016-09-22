#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Helpers for testing opsi.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import shutil
import tempfile
from contextlib import contextmanager

try:
    import unittest.mock as mock
except ImportError:
    import mock

import unittest
if 'SkipTest' not in dir(unittest):
    try:
        import unittest2 as unittest
    except ImportError:
        print("Your are missing a recent enough version of unittest. "
              "Please install the unittest2 package.")
        raise ImportError("Your unittest module is too old.")


@contextmanager
def workInTemporaryDirectory(tempDir=None):
    """
    Creates a temporary folder to work in. Deletes the folder afterwards.

    :param tempDir: use the given dir as temporary directory. Will not \
be deleted if given.
    """
    temporary_folder = tempDir or tempfile.mkdtemp()
    with cd(temporary_folder):
        try:
            yield temporary_folder
        finally:
            if not tempDir:
                try:
                    shutil.rmtree(temporary_folder)
                except OSError:
                    pass


@contextmanager
def cd(path):
    'Change the current directory to `path` as long as the context exists.'

    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


def copyTestfileToTemporaryFolder(filename):
    temporary_folder = tempfile.mkdtemp()
    shutil.copy(filename, temporary_folder)

    (_, new_filename) = os.path.split(filename)

    return os.path.join(temporary_folder, new_filename)


@contextmanager
def createTemporaryTestfile(original, tempDir=None):
    '''Copy `original` to a temporary directory and \
yield the path to the new file.

    The temporary directory can be specified overridden with `tempDir`.'''

    with workInTemporaryDirectory(tempDir) as targetDir:
        shutil.copy(original, targetDir)

        (_, new_filename) = os.path.split(original)

        yield os.path.join(targetDir, new_filename)


def getLocalFQDN():
    'Get the FQDN of the local machine.'
    # Lazy imports to not hinder other tests.
    from OPSI.Types import forceHostId
    from OPSI.Util import getfqdn

    return forceHostId(getfqdn())


@contextmanager
def patchAddress(fqdn="opsi.test.invalid", address="172.16.0.1"):
    """
    Modify the results of socket so that expected addresses are returned.

    :param fqdn: The FQDN to use. Everything before the first '.' will serve\
as hostname.
    :param address: The IP address to use.
    """
    fqdn = fqdn
    hostname = fqdn.split(".")[0]
    address = address

    def getfqdn(*_):
        return fqdn

    def gethostbyaddr(*_):
        return (fqdn, [hostname], [address])

    with mock.patch('socket.getfqdn', getfqdn):
        with mock.patch('socket.gethostbyaddr', gethostbyaddr):
            yield


@contextmanager
def patchEnvironmentVariables(**environmentVariables):
    """
    Patches to environment variables to be empty during the context.
    Anything supplied as keyword argument will be added to the environment.
    """
    originalEnv = os.environ.copy()
    try:
        os.environ.clear()
        for key, value in environmentVariables.items():
            os.environ[key] = value

        yield
    finally:
        os.environ = originalEnv


@contextmanager
def fakeGlobalConf(fqdn="opsi.test.invalid", dir=None):
    "Fake a global.conf and return the path to the file."

    with workInTemporaryDirectory(dir) as tempDir:
        configPath = os.path.join(tempDir, 'global.conf')

        with open(configPath, "w") as conf:
            conf.write("""[global]
hostname = {0}
""".format(fqdn))

        yield configPath


@contextmanager
def showLogs(logLevel=7, color=True):
    """
    A contextmanager that returns a usable logger that is configured
    to log debug output.
    """
    from OPSI.Logger import Logger

    logger = Logger()

    logLevelBefore = logger.getConsoleLevel()

    try:
        logger.setConsoleLevel(logLevel)
        logger.setConsoleColor(color)
        yield logger
    finally:
        logger.setConsoleLevel(logLevelBefore)
