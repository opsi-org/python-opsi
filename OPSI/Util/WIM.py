#!/usr/bin/python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2014-2016 uib GmbH - http://www.uib.de/

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
from OPSI.Util import getfqdn

LOGGER = Logger()

__all__ = ['parseWIM', 'writeImageInformation']


def parseWIM(wimPath):
    Image = namedtuple("Image", 'name languages default_language')

    if not os.path.exists(wimPath):
        raise OSError(u"File {0!r} not found!".format(wimPath))

    try:
        imagex = which('wimlib-imagex')
    except Exception as error:
        LOGGER.logException(error)
        LOGGER.warning("Unable to find 'wimlib-imagex': {0}".format(error))
        LOGGER.warning("Please install 'wimtools'.")
        raise RuntimeError("Unable to find 'wimlib-imagex': {0}".format(error))

    images = []
    imagename = None
    languages = set()
    defaultLanguage = None
    for line in execute("{imagex} info {file!r}".format(imagex=imagex, file=wimPath)):
        if line.startswith('Name:'):
            _, name = line.split(' ', 1)
            imagename = name.strip()
        elif line.startswith('Languages:'):
            _, langs = line.split(' ', 1)
            langs = langs.strip()
            if ' ' in langs:
                langs = langs.split(' ')
            elif ',' in langs:
                langs = langs.split(',')
            else:
                langs = [langs]

            for lang in langs:
                if lang.strip():
                    languages.add(lang.strip())
        elif line.startswith('Default Language:'):
            _, _, defLang = line.split(' ', 2)
            defaultLanguage = defLang.strip()
        elif not line:
            if imagename:
                images.append(Image(imagename, languages, defaultLanguage))

            imagename = None
            languages = set()
            defaultLanguage = None

    if not images:
        raise ValueError('Could not find any images')

    LOGGER.debug('images: {0!r}'.format(images))
    LOGGER.notice("Detected the following images:")
    for image in images:
        LOGGER.notice(image.name)

    return images


def writeImageInformation(backend, productId, imagenames, languages=None, defaultLanguage=None):
    productProperty = _getProductProperty(backend, productId, 'imagename')
    productProperty.possibleValues = imagenames
    backend.productProperty_updateObject(productProperty)
    LOGGER.notice("Wrote imagenames to property 'imagename' product on {0!r}.".format(productId))

    if languages:
        LOGGER.debug("Writing detected languages...")
        productProperty = _getProductProperty(backend, productId, "system_language")
        productProperty.possibleValues = languages

        if defaultLanguage and defaultLanguage in languages:
            LOGGER.debug("Setting language default to {0!r}".format(defaultLanguage))
            productProperty.defaultValues = [defaultLanguage]

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
