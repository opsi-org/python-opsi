# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2019 uib GmbH <info@uib.de>

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
Testing .opsirc handling.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os
import pytest

from OPSI.Util.File.Opsi.Opsirc import getOpsircPath, readOpsirc
from OPSI.Util import randomString


@pytest.fixture
def filename(tempDir):
    return os.path.join(tempDir, randomString(8) + '.conf')


def testReadingMissingFileReturnsNoConfig(tempDir):
    assert {} == readOpsirc('iamnothere')


def testReadingEmptyConfigFile(filename):
    with open(filename, 'w'):
        pass

    config = readOpsirc(filename)

    assert {} == config


def testReadingConfigFile(filename):
    with open(filename, 'w') as f:
        f.write('address = https://lullaby.machine.dream:12345/c3\n')
        f.write('username = hanz\n')
        f.write('password = gr3tel\n')

    config = readOpsirc(filename)

    assert len(config) == 3
    assert config['address'] == 'https://lullaby.machine.dream:12345/c3'
    assert config['username'] == 'hanz'
    assert config['password'] == 'gr3tel'


def testReadingConfigFileIgnoresLeadingAndTrailingSpacing(filename):
    with open(filename, 'w') as f:
        f.write('   address = https://lullaby.machine.dream:12345/c3\n')
        f.write('username=hanz   \n')
        f.write('        password   = gr3tel      \n')

    config = readOpsirc(filename)

    assert len(config) == 3
    assert config['address'] == 'https://lullaby.machine.dream:12345/c3'
    assert config['username'] == 'hanz'
    assert config['password'] == 'gr3tel'


def testReadingPasswordFromCredentialsfile(filename):
    password = randomString(32)

    pwdfile = filename + '.secret'
    with codecs.open(pwdfile, 'w', 'utf-8') as f:
        f.write(password + '\n')

    with open(filename, 'w') as f:
        f.write('address = https://lullaby.machine.dream:12345/c3\n')
        f.write('username = hanz\n')
        f.write('password file = {}\n'.format(pwdfile))

    config = readOpsirc(filename)

    assert len(config) == 3
    assert config['address'] == 'https://lullaby.machine.dream:12345/c3'
    assert config['username'] == 'hanz'
    assert config['password'] == password


def testIgnoringComments(filename):
    with open(filename, 'w') as f:
        f.write(';address = https://bad.guy.dream:12345/c3\n')
        f.write('# address = https://blue.pill.dream:12345/c3\n')
        f.write('address = https://lullaby.machine.dream:12345/c3\n')
        f.write('  # address = https://last.one.neo:12345/c3\n')

    config = readOpsirc(filename)

    assert len(config) == 1
    assert config['address'] == 'https://lullaby.machine.dream:12345/c3'


def testIgnoringUnknownKeywords(filename):
    with open(filename, 'w') as f:
        f.write('hello = world\n')
        f.write('i coded = a bot\n')
        f.write('and I liked it\n')

    config = readOpsirc(filename)

    assert not config


def testIgnoringEmptyValues(filename):
    with open(filename, 'w') as f:
        f.write('username=\n')
        f.write('username = foo\n')
        f.write('username =     \n')

    config = readOpsirc(filename)

    assert len(config) == 1
    assert config['username'] == 'foo'


def testReadingOpsircPath():
    path = getOpsircPath()
    assert '~' not in path

    head, tail = os.path.split(path)
    assert tail == 'opsirc'
    assert head.endswith('.opsi.org')
