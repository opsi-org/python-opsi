# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2018-2019 uib GmbH - http://www.uib.de/

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
Utility functions for package updates.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Exceptions import NoActiveRepositoryError

from OPSI.Logger import Logger
from OPSI.Util import compareVersions


__all__ = ('getUpdatablePackages', )

logger = Logger()


def getUpdatablePackages(updater):
	"""
	Returns information about updatable packages from the given `updater`.


	:raises NoActiveRepositoryError: If not active repositories are found.
	:param updater: The update to use.
	:type updater: OpsiPackageUpdater
	:returns: A dict containing the productId as key and the value is \
another dict with the keys _productId_, _newVersion_, _oldVersion_ and \
_repository_.
	:rtype: {str: {}
	"""
	if not any(updater.getActiveRepositories()):
		raise NoActiveRepositoryError("No active repository configured.")

	updates = {}
	try:
		installedProducts = updater.getInstalledProducts()
		downloadablePackages = updater.getDownloadablePackages()
		downloadablePackages = updater.onlyNewestPackages(downloadablePackages)
		downloadablePackages = updater._filterProducts(downloadablePackages)

		for availablePackage in downloadablePackages:
			productId = availablePackage['productId']
			for product in installedProducts:
				if product['productId'] == productId:
					logger.debug(u"Product '%s' is installed" % productId)
					logger.debug(u"Available product version is '%s', installed product version is '%s-%s'" % (availablePackage['version'], product['productVersion'], product['packageVersion']))
					updateAvailable = compareVersions(availablePackage['version'], '>', '%s-%s' % (product['productVersion'], product['packageVersion']))

					if updateAvailable:
						updates[productId] = {
							"productId": productId,
							"newVersion": "{version}".format(**availablePackage),
							"oldVersion": "{productVersion}-{packageVersion}".format(**product),
							"repository": availablePackage['repository'].name
						}
					break
	except Exception as error:
		raise error

	return updates
