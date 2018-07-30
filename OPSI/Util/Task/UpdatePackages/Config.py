# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2018 uib GmbH - http://www.uib.de/

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
Configuration.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import os.path

from OPSI import __version__
from OPSI.Logger import Logger

__all__ = ('DEFAULT_CONFIG', 'getRepoConfigs')

DEFAULT_CONFIG = {
	"userAgent": 'opsi package updater %s' % __version__,
	"packageDir": '/var/lib/opsi/products',
	"configFile": '/etc/opsi/opsi-package-updater.conf',
	"repositoryConfigDir": '/etc/opsi/package-updater.repos.d',
	"notification": False,
	"smtphost": u'localhost',
	"smtpport": 25,
	"smtpuser": None,
	"smtppassword": None,
	"subject": u'opsi-package-updater',
	"use_starttls": False,
	"sender": u'opsi@localhost',
	"receivers": [],
	"wolAction": False,
	"wolActionExcludeProductIds": [],
	"wolShutdownWanted": False,
	"wolStartGap": 0,
	"installationWindowStartTime": None,
	"installationWindowEndTime": None,
	"installationWindowExceptions": None,
	"repositories": [],
	"repositoryName": None,
	"forceRepositoryActivation": False,
	"installAllAvailable": False,
	"zsyncCommand": None,
	"processProductIds": None,
	"forceChecksumCalculation": False,
	"forceDownload": False,
}

logger = Logger()


def getRepoConfigs(repoDir):
	try:
		for entry in os.listdir(repoDir):
			filePath = os.path.join(repoDir, entry)
			if entry.endswith('.repo') and os.path.isfile(filePath):
				yield filePath
	except OSError as oserr:
		logger.warning("Problem listing {0}: {1}".format(repoDir, oserr))
