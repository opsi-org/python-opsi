#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup, Extension

setup (
	name = 'python-opsi',
	version = '3.3.0.25',
	description = 'opsi python library',
	long_description = 'opsi python library.',
	author = "uib GmbH",
	author_email = 'info@uib.de',
	license = 'GPL',
	url='http://www.opsi.org',
	package_dir = {'': 'src'},
	packages = [
		'OPSI',
		'OPSI.Backend',
		'OPSI.System',
		'dav',
		'dav.element',
		'dav.method',
	],
	#data_files=[
	#	('/usr/share/locale/de/LC_MESSAGES opsi_system.mo', ['gettext/opsi_system.mo', 'gettext/opsi_ui.mo'])
	#]
)

