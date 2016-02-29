#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2010-2016 uib GmbH <info@uib.de>

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
opsi python library - setup file

@copyright:	uib GmbH <info@uib.de>
@author: Christian Kampka <c.kampka@uib.de>
@author: Niko Wenselowski <n.wenselowski@uib.de>
@license: GNU Affero General Public License version 3
"""

from setuptools import setup, find_packages
import os

LANGUAGES = ['da', 'de', 'es', 'fr', 'it', 'ru', 'en', 'pl']

VERSION = None
with open(os.path.join("debian", "changelog")) as changelog:
	VERSION = changelog.readline().split('(')[1].split('-')[0]

if not VERSION:
	raise Exception(u"Failed to get version info")

with open("data/version", "w") as versionFile:
	versionFile.write(VERSION)

data_files = [
	(
		'/etc/opsi/backendManager',
		[
			'data/backendManager/acl.conf.default',
			'data/backendManager/dispatch.conf.default'
		]
	),
	(
		'/etc/opsi/backendManager/extend.d',
		[
			'data/backendManager/extend.d/10_opsi.conf',
			'data/backendManager/extend.d/10_wim.conf',
			'data/backendManager/extend.d/20_legacy.conf',
			'data/backendManager/extend.d/40_groupActions.conf',
			'data/backendManager/extend.d/40_admin_tasks.conf',
			'data/backendManager/extend.d/70_dynamic_depot.conf',
			'data/backendManager/extend.d/70_wan.conf',
		]
	),
	(
		'/etc/opsi/backends/',
		[
			'data/backends/dhcpd.conf',
			'data/backends/file.conf',
			'data/backends/jsonrpc.conf',
			'data/backends/mysql.conf',
			'data/backends/sqlite.conf',
			'data/backends/multiplex.conf',
			'data/backends/hostcontrol.conf',
			'data/backends/opsipxeconfd.conf'
		]
	),
	(
		'/etc/opsi/',
		[
			'data/version',
			'data/opsi.conf'
		]
	),
	(
		'/etc/opsi/hwaudit/',
		['data/hwaudit/opsihwaudit.conf']
	),
	(
		'/etc/opsi/hwaudit/locales',
		[
			'data/hwaudit/locales/de_DE',
			'data/hwaudit/locales/en_US',
			'data/hwaudit/locales/fr_FR',
			'data/hwaudit/locales/da_DA',
		]
	)
]

for language in LANGUAGES:
	languageFile = os.path.join('gettext', 'python-opsi_{0}.po'.format(language))
	if not os.path.exists(languageFile):
		print("Can't find localisation file {0}. Skipping.".format(languageFile))
		continue

	output_path = os.path.join('locale', language, 'LC_MESSAGES')
	if not os.path.exists(output_path):
		os.makedirs(output_path)

	target_file = os.path.join(output_path, 'python-opsi.mo')
	exitCode = os.system(
		'msgfmt --output-file {outputfile} {langFile}'.format(
			langFile=languageFile,
			outputfile=target_file
		)
	)
	if not exitCode:
		data_files.append(
			('/usr/share/locale/%s/LC_MESSAGES' % language, [target_file])
		)
	else:
		print('Generating locale for "{0}" failed. Is gettext installed?'.format(language))


setup(
	name='python-opsi',
	version=VERSION,
	license='AGPL-3',
	url="http://www.opsi.org",
	description='The opsi python library',
	packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
	data_files=data_files,
)
