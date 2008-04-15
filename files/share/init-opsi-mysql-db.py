#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = =
   =   init-opsi-mysql-db.py   =
   = = = = = = = = = = = = = = =
   
   This script is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '1.0'

import MySQLdb, sys, os, getpass
from _mysql_exceptions import *

from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Logger import *
from OPSI import Tools

logger = Logger()
logger.setConsoleLevel(LOG_NOTICE)
logger.setConsoleColor(True)

backendConfigFile = '/etc/opsi/backendManager.d/21_mysql.conf'
databaseHost = 'localhost'
databaseName = 'opsi'
databaseUser = 'opsi'
databasePass = 'opsi'
adminUser = 'root'
adminPass = 'password'

try:
	print ""
	print "*******************************************************************************"
	print "*  This tool will create an initial mysql database for use as opsi backend.   *"
	print "* The config file " +        backendConfigFile         + " will be recreated. *"
	print "*                 =>>> Press <CTRL> + <C> to abort <<<=                       *"
	print "*******************************************************************************"
	print ""
	
	# Ask config
	print " Database host [%s]: " % databaseHost,
	uin = sys.stdin.readline().strip()
	if uin: databaseHost = uin
	
	print "Database admin user [%s]: " % adminUser,
	uin = sys.stdin.readline().strip()
	if uin: adminUser = uin
	
	print "Database admin password [%s]: " % adminPass,
	uin = getpass.getpass('')
	if uin: adminPass = uin
	
	print " Opsi database name [%s]: " % databaseName,
	uin = sys.stdin.readline().strip()
	if uin: databaseName = uin
	
	print "Opsi database user [%s]: " % databaseUser,
	uin = sys.stdin.readline().strip()
	if uin: databaseUser = uin
	
	print "Opsi database password [%s]: " % databasePass,
	uin = getpass.getpass('')
	if uin: databasePass = uin
	
	print ""
	
	# Connect to database host
	logger.notice("Connecting to host '%s' as user '%s'" % (databaseHost, adminUser))
	db = MySQLdb.connect( host = databaseHost, user = adminUser, passwd = adminPass )
	
	# Create opsi database and user
	logger.notice("Creating database '%s' and user '%s'" % (databaseName, databaseUser))
	try:
		db.query('CREATE DATABASE %s DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_bin;' % databaseName)
	except ProgrammingError, e:
		if (e[0] != 1007):
			# 1007: database exists
			raise
	db.query('USE %s;' % databaseName)
	db.query('GRANT ALL ON %s .* TO %s@%s IDENTIFIED BY \'%s\'' \
			% (databaseName, databaseUser, databaseHost, databasePass));
	db.query('FLUSH PRIVILEGES;')
	
	# Disconnect from database
	db.close()
	
	# Test connection / credentials
	logger.notice("Testing connection")
	db = MySQLdb.connect( host = databaseHost, user = databaseUser, passwd = databasePass, db = databaseName)
	db.close()
	logger.notice("Connection / credentials ok!")
	
	# Connection ok, write backend config
	logger.notice("Creating mysql backend config file %s" % backendConfigFile)
	if os.path.exists(backendConfigFile):
		os.system('cp %s %s.sav' % (backendConfigFile, backendConfigFile))
		os.system('chmod 600 %s.sav' % backendConfigFile)
	f = open(backendConfigFile, 'w')
	print >> f, "''' - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
	print >> f, "-     MySQL backend                                                       -"
	print >> f, "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - '''"
	print >> f, "global BACKEND_MYSQL"
	print >> f, "BACKEND_MYSQL = 'MySQL'"
	print >> f, ""
	print >> f, "self.backends[BACKEND_MYSQL] = {"
	print >> f, "    'load': True"
	print >> f, "}"
	print >> f, ""
	print >> f, "self.backends[BACKEND_MYSQL]['config'] = {"
	print >> f, '	 "host":       "%s",' % databaseHost
	print >> f, '	 "database":   "%s",' % databaseName
	print >> f, '	 "username":   "%s",' % databaseUser
	print >> f, '	 "password":   "%s"'  % databasePass
	print >> f, "}"
	print >> f, ""
	f.close()
	
	# Create initial database tables
	backend = MySQLBackend( username = databaseUser, password = databasePass, address = databaseHost, args = { 'database': databaseName } )
	backend.createOpsiBase()
except KeyboardInterrupt:
	pass
except Exception, e:
	logger.logException(e)
	print >> sys.stderr, "ERROR: %s" % e

print ""
sys.exit(0)

