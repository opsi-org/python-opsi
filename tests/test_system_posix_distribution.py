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
Testing Distribution functionality from OPSI.System.Posix

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.System.Posix import Distribution

import pytest


# The first tuple is retrieved by running platform.linux_distribution()
# or distro.linux_distribution() on the corresponding version.
DISTRI_INFOS = [
    (('debian', '8.11', ''), (8, 11)),
    (('debian', '10.0', ''), (10, 0)),
    # TODO: add CentOS 7
    (('Red Hat Enterprise Linux Server', '7.0', 'Maipo'), (7, 0)),
    (('Ubuntu', '16.04', 'xenial'), (16, 4)),
    (('Ubuntu', '19.04', 'disco'), (19, 4)),
    (('Univention', '"4.4-0 errata175"', 'Blumenthal'), (4, 4)),
    # TODO: add SLES12
    (('openSUSE project', '42.3', 'n/a'), (42, 3)),
    (('openSUSE', '15.0', 'n/a'), (15, 0)),
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
