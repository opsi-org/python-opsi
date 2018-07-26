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
Handling repositories.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import os.path
import htmllib

from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceUnicode, forceUnicodeList

logger = Logger()


def getRepoConfigs(repoDir):
	try:
		for entry in os.listdir(repoDir):
			filePath = os.path.join(repoDir, entry)
			if entry.endswith('.repo') and os.path.isfile(filePath):
				yield filePath
	except OSError as oserr:
		logger.warning("Problem listing {0}: {1}".format(repoDir, oserr))


class ProductRepositoryInfo(object):
	def __init__(self, name, baseUrl, dirs=[], username=u"", password=u"", opsiDepotId=None, autoInstall=False, autoUpdate=True, autoSetup=False, proxy=None, excludes=[], includes=[], active=False):
		self.name = forceUnicode(name)
		self.baseUrl = forceUnicode(baseUrl)
		self.dirs = forceUnicodeList(dirs)
		self.excludes = excludes
		self.includes = includes
		self.username = forceUnicode(username)
		self.password = forceUnicode(password)
		self.autoInstall = autoInstall
		self.autoUpdate = autoUpdate
		self.autoSetup = autoSetup
		self.opsiDepotId = opsiDepotId
		self.onlyDownload = None
		self.inheritProductProperties = None
		self.description = ''
		self.active = forceBool(active)

		self.proxy = None
		if proxy:
			self.proxy = proxy
		if self.baseUrl.startswith('webdav'):
			self.baseUrl = u'http%s' % self.baseUrl[6:]

	def getDownloadUrls(self):
		urls = set()
		for directory in self.dirs:
			if directory in (u'', u'/', u'.'):
				url = self.baseUrl
			else:
				url = u'%s/%s' % (self.baseUrl, directory)

			urls.add(url)

		return urls


class LinksExtractor(htmllib.HTMLParser):
	def __init__(self, formatter):
		htmllib.HTMLParser.__init__(self, formatter)
		self.links = set()

	def start_a(self, attrs):
		if len(attrs) > 0:
			for attr in attrs:
				if attr[0] != "href":
					continue

				link = attr[1]
				if link.startswith('/'):
					# Fix for IIS repos
					link = link[1:]

				self.links.add(link)

	def getLinks(self):
		return self.links
