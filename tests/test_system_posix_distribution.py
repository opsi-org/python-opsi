#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Testing Distribution functionality from OPSI.System.Posix

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.System.Posix import Distribution

import pytest


DISTRI_INFOS = [
    (('debian', '7.1', ''), (7, 1)),
    # TODO: add Debian 8
    (('CentOS', '6.4', 'Final'), (6, 4)),
    # TODO: add CentOS 7
    (('Red Hat Enterprise Linux Server', '6.4', 'Santiago'), (6, 4)),
    (('Red Hat Enterprise Linux Server', '7.0', 'Maipo'), (7, 0)),
    (('Ubuntu', '12.04', 'precise'), (12, 4)),
    # TODO: add current Ubuntus: 14.04 and 16.04
    (('"Univention"', '"3.1-1 errata163"', '"Findorff"'), (3, 1)),
    # TODO: add UCS 4.x
    (('SUSE Linux Enterprise Server ', '11', 'x86_64'), (11, ))
    # TODO: add SLES12
    # TODO: add OpenSUSE Leap
]


@pytest.mark.parametrize("dist_info, expected_version", DISTRI_INFOS)
def testDistributionHasVersionSet(dist_info, expected_version):
    dist = Distribution(distribution_information=dist_info)

    assert dist.version
    assert expected_version == dist.version
    assert isinstance(dist.version, tuple)


@pytest.mark.parametrize("dist_info, expected_version", DISTRI_INFOS)
def testDistributionReprContainsAllValues(dist_info, expected_version):
    dist = Distribution(distribution_information=dist_info)

    for part in dist_info:
        assert part.strip() in repr(dist)


@pytest.mark.parametrize("dist_info, expected_version", DISTRI_INFOS)
def testDistributionNameGetsWhitespaceStripped(dist_info, expected_version):
    dist = Distribution(distribution_information=dist_info)

    assert dist.distribution == dist_info[0].strip()


@pytest.mark.parametrize("dist_info, expected_version", DISTRI_INFOS)
def testDistributionHasDistributorSet(dist_info, expected_version):
    dist = Distribution(distribution_information=dist_info)

    assert dist.distributor
