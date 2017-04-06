#!/usr/bin/python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2015-2016 uib GmbH - http://www.uib.de/

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
Working with Windows Imaging Format (WIM) files.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os.path
from collections import namedtuple

from OPSI.Logger import Logger
from OPSI.System import execute, which
from OPSI.Types import forceList, forceProductId
from OPSI.Util import getfqdn

LOGGER = Logger()

__all__ = ('getImageInformation', 'parseWIM', 'writeImageInformation')


def parseWIM(wimPath):
	"""
	Parses the WIM file at the given `path`.

	This requires `wimlib-imagex` to be installed on the server.

	:return: a list of images. These have attributes `name`, `languages` and `default_language`.
	"""
	Image = namedtuple("Image", 'name languages default_language')

	LOGGER.notice("Detected the following images:")
	images = []
	for image in getImageInformation(wimPath):
		LOGGER.notice(image['name'])
		images.append(Image(image['name'], image.get('languages', tuple()), image.get('default language', None)))

	if not images:
		raise ValueError('Could not find any images')

	return images


def getImageInformation(imagePath):
	"""
	Read information from a WIM file at `imagePath`.

	This method acts as a generator that yields information for each image
	in the file as a `dict`. The keys in the dict are all lowercase.
	Every dict has at least the key 'name'.
	"""
	if not os.path.exists(imagePath):
		raise OSError(u"File {0!r} not found!".format(imagePath))

	try:
		imagex = which('wimlib-imagex')
	except Exception as error:
		LOGGER.logException(error)
		LOGGER.warning("Unable to find 'wimlib-imagex': {0}".format(error))
		LOGGER.warning("Please install 'wimtools'.")
		raise RuntimeError("Unable to find 'wimlib-imagex': {0}".format(error))

	imageinfo = {}
	for line in execute("{imagex} info '{file}'".format(imagex=imagex, file=imagePath)):
		if line and ':' in line:
			key, value = line.split(':', 1)
			key = key.strip().lower()
			value = value.strip()

			if key == 'languages':
				langs = value
				if ' ' in langs:
					langs = langs.split(' ')
				elif ',' in langs:
					langs = langs.split(',')
				else:
					langs = [langs]

				languages = set()
				for lang in langs:
					if lang.strip():
						languages.add(lang.strip())

				value = languages

			imageinfo[key] = value
		elif not line and imageinfo:
			if 'name' in imageinfo:  # Do not return file information.
				LOGGER.debug("Collected information {0!r}".format(imageinfo))
				yield imageinfo

			imageinfo = {}


def writeImageInformation(backend, productId, imagenames, languages=None, defaultLanguage=None):
	"""
	Writes information about the `imagenames` to the propert *imagename*
	of the product with the given `productId`.

	If `languages` are given these will be written to the property
	*system_language*. If an additional `defaultLanguage` is given this
	will be selected as the default.
	"""
	if not productId:
		raise ValueError("Not a valid productId: {0!r}".format(productId))
	productId = forceProductId(productId)

	productProperty = _getProductProperty(backend, productId, 'imagename')
	productProperty.possibleValues = imagenames
	if productProperty.defaultValues:
		if productProperty.defaultValues[0] not in imagenames:
			LOGGER.info("Mismatching default value. Setting first imagename as default.")
			productProperty.defaultValues = [imagenames[0]]
	else:
		LOGGER.info("No default values found. Setting first imagename as default.")
		productProperty.defaultValues = [imagenames[0]]

	backend.productProperty_updateObject(productProperty)
	LOGGER.notice("Wrote imagenames to property 'imagename' product on {0!r}.".format(productId))

	if languages:
		LOGGER.debug("Writing detected languages...")
		productProperty = _getProductProperty(backend, productId, "system_language")
		productProperty.possibleValues = forceList(languages)

		if defaultLanguage and defaultLanguage in languages:
			LOGGER.debug("Setting language default to {0!r}".format(defaultLanguage))
			productProperty.defaultValues = [defaultLanguage]

		LOGGER.debug("system_language property is now: {0!r}".format(productProperty))
		LOGGER.debug("system_language possibleValues are: {0}".format(productProperty.possibleValues))
		backend.productProperty_updateObject(productProperty)
		LOGGER.notice("Wrote languages to property 'system_language' product on {0!r}.".format(productId))


def _getProductProperty(backend, productId, propertyId):
	productFilter = {
		"productId": productId,
		"propertyId": propertyId
	}
	properties = backend.productProperty_getObjects(**productFilter)
	LOGGER.debug("Properties: {0}".format(properties))

	if not properties:
		raise RuntimeError("No property {1!r} for product {0!r} found!".format(productId, propertyId))
	elif len(properties) > 1:
		LOGGER.debug("Found more than one property... trying to be more specific")

		serverId = getfqdn()
		prodOnDepot = backend.productOnDepot_getObjects(depotId=serverId, productId=productId)
		if not prodOnDepot:
			raise RuntimeError("Did not find product {0!r} on depot {1!r}".format(productId, serverId))
		elif len(prodOnDepot) > 1:
			raise RuntimeError("Too many products {0!r} on depot {1!r}".format(productId, serverId))

		prodOnDepot = prodOnDepot[0]
		productFilter['packageVersion'] = prodOnDepot.packageVersion
		productFilter['productVersion'] = prodOnDepot.productVersion
		LOGGER.debug('New filter: {0}'.format(productFilter))
		properties = backend.productProperty_getObjects(**productFilter)
		LOGGER.debug("Properties: {0}".format(properties))

		if not properties:
			raise RuntimeError("Unable to find property {1!r} for product {0!r}!".format(productId, propertyId))
		elif len(properties) > 1:
			raise RuntimeError("Too many product properties found - aborting.")

	return properties[0]
