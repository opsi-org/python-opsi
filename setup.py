#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - setup file  =
   = = = = = = = = = = = = = = = = = = = =

   opsiconfd is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org

   Copyright (C) 2010 uib GmbH

   http://www.uib.de/

   All rights reserved.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

   @copyright:	uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

from setuptools import setup, find_packages
import os

f = open("debian/changelog")
VERSION = f.readline().split('(')[1].split('-')[0]
f.close()

cmdclass = {}

try:
	from opsidistutils.commands.osc_cmd import osc_publish as osc
	cmdclass['osc'] = osc
except ImportError, e:
	print("osc integration is not available on this machine. please install opsi-distutils.")


if not VERSION:
    raise Exception(u"Failed to get version info")

f = open("data/version", "w")
f.write(VERSION)
f.close()

data_files=[('/etc/opsi/backendManager', ['data/backendManager/acl.conf.default',
					  'data/backendManager/dispatch.conf.default']),
	    ('/etc/opsi/backendManager/extend.d', ['data/backendManager/extend.d/10_opsi.conf',
						   'data/backendManager/extend.d/20_legacy.conf',
						   'data/backendManager/extend.d/40_groupActions.conf',
						   'data/backendManager/extend.d/70_dynamic_depot.conf']),
	    ('/etc/opsi/backendManager/extend.d/configed', ['data/backendManager/extend.d/configed/30_configed.conf']),
	    ('/etc/opsi/backends/', ['data/backends/dhcpd.conf',
				     'data/backends/file.conf',
				     'data/backends/jsonrpc.conf',
				     'data/backends/ldap.conf',
				     'data/backends/mysql.conf',
				     'data/backends/sqlite.conf',
				     'data/backends/multiplex.conf',
				     'data/backends/hostcontrol.conf',
				     'data/backends/opsipxeconfd.conf']),
	    ('/etc/opsi/', ['data/version','data/opsi.conf']),
	    ('/etc/opsi/hwaudit/', ['data/hwaudit/opsihwaudit.conf']),
	    ('/etc/opsi/hwaudit/locales', ['data/hwaudit/locales/de_DE',
					   'data/hwaudit/locales/en_US',
					   'data/hwaudit/locales/fr_FR'])]

if bool(os.getenv("RPM_BUILD_ROOT")):
	data_files.append( ('/etc/openldap/schema/', ['data/opsi.schema', 'data/opsi-standalone.schema']) )
else:
	data_files.append( ('/etc/ldap/schema/', ['data/opsi.schema', 'data/opsi-standalone.schema']) )

for language in ('de', 'fr'):
    output_path = os.path.join('locale', language, 'LC_MESSAGES')
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    target_file = os.path.join(output_path, 'python-opsi.mo')
    exit_code = os.system(
        'msgfmt -o {output_file} gettext/python-opsi_{lang}.po'.format(
            lang=language,
            output_file=target_file
        )
    )
    if not exit_code:
        data_files.append(
            ('/usr/share/locale/{lang}/LC_MESSAGES', [target_file])
        )
    else:
        print('Generating locale for "{lang}" failed. Is gettext installed?')

setup(
	name='python-opsi',
	version=VERSION,
	license='GPL-2',
	url="http://www.opsi.org",
	description='The opsi python library',
	packages=find_packages(),
	data_files=data_files,
	cmdclass = cmdclass
)
