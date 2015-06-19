#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2015 uib GmbH <info@uib.de>

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

from OPSI.Types import forceHostId
from OPSI.Util import getfqdn

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
def workInTemporaryDirectory():
    """
    Creates a temporary folder to work in. Deletes the folder afterwards.
    """
    temporary_folder = tempfile.mkdtemp()
    with cd(temporary_folder):
        yield temporary_folder

    if os.path.exists(temporary_folder):
        shutil.rmtree(temporary_folder)


@contextmanager
def cd(path):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def copyTestfileToTemporaryFolder(filename):
    temporary_folder = tempfile.mkdtemp()
    shutil.copy(filename, temporary_folder)

    (_, new_filename) = os.path.split(filename)

    return os.path.join(temporary_folder, new_filename)


def getLocalFQDN():
    return forceHostId(getfqdn())


@contextmanager
def patchAddress(fqdn="opsi.test.invalid", address="172.16.0.1"):
    """
    Modify the results of socket so that expected addresses are returned.

    :param fqdn: The FQDN to use. Everything before the first '.' will server\
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


def requireModulesFile(function):
    """
    This decorator will skip tests if no modules file is found.
    """
    if not os.path.exists('/etc/opsi/modules'):
        raise unittest.SkipTest("This test requires a modules file!")

    # TODO: make it possible to require specific parts of the modules file to be enabled

    return function
