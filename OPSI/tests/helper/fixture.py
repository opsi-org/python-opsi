# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

import os

from testtools.monkey import patch
from fixtures import Fixture
import fixtures

from OPSI.Util.File.Opsi import BackendDispatchConfigFile, HostKeyFile
from OPSI.Util import generateOpsiHostKey

class FQDNFixture(Fixture):
	
	def __init__(self, fqdn="opsi.uib.local", address="172.16.0.1"):
		
		self.hostname = fqdn.split(".")[0]
		self.fqdn = fqdn
		self.address = address
		
	def setUp(self):
		super(FQDNFixture, self).setUp()
		
		def getfqdn(_ignore):
			return self.fqdn
		
		def gethostbyaddr(_ignore):
			return (self.fqdn, [self.hostname], [self.address])
		
		self.useFixture(fixtures.MonkeyPatch('socket.getfqdn', getfqdn))
		self.useFixture(fixtures.MonkeyPatch('socket.gethostbyaddr', gethostbyaddr))

class ConfigFixture(Fixture):
	
	template = None
	name = None
	
	def __init__(self, prefix=None, dir=None):
		
		super(ConfigFixture, self).__init__()
		self.prefix = prefix
		self.dir = dir
		self.data = None
	
		self.config = None
	
	def setUp(self):
		super(ConfigFixture, self).setUp()
		
		if self.dir is None:
			self.dir = self.useFixture(fixtures.TempDir()).path
		if self.prefix is not None:
			self.dir = os.path.join(self.dir, self.prefix)
			if not os.path.exists(self.dir):
				os.mkdir(self.dir)
		self.path = os.path.join(self.dir, self.name)
	
	def _write(self, data):
		self.data = data
		f = file(self.path, "w")
		try:
			f.write(data)
		except Exception, e:
			self.addDetail("conferror", e)
			self.test.fail("Could not generate global.conf.")
		finally:
			f.close()

	
class GlobalConfFixture(ConfigFixture):
	
	template = """[global]
hostname = #hostname#
"""	
	name = "global.conf"
	
	def __init__(self, fqdn="opsi.uib.local", prefix=None, dir=None):
		super(GlobalConfFixture, self).__init__(prefix=prefix, dir=dir)
		self.fqdn = fqdn
		
	def setUp(self):
		super(GlobalConfFixture, self).setUp()
		
		s = self.template.replace("#hostname#", self.fqdn)
		self._write(s)

class DispatchConfigFixture(ConfigFixture):
	
	template = """
	backend_.*         : #backend#, opsipxeconfd, #dhcp#
	host_.*            : #backend#, opsipxeconfd, #dhcp#
	productOnClient_.* : #backend#, opsipxeconfd
	configState_.*     : #backend#, opsipxeconfd
	.*                 : #backend#
	"""
	
	name = "dispatch.conf"
	
	def __init__(self, prefix="backendManager", dir=None):
		super(DispatchConfigFixture, self).__init__(prefix=prefix, dir=dir)
	
	
	def _generateDispatchConf(self, data):
		self._write(data)
		self.config = BackendDispatchConfigFile(self.path)

	def setupFile(self):
		conf = self.template.replace("#backend#", "file")
		self._generateDispatchConf(conf)
		
	def setupMySQL(self):
		conf = self.template.replace("#backend#", "mysql")
		self._generateDispatchConf(conf)
		
	def setupLDAP(self):
		conf = self.template.replace("#backend#", "ldap")
		self._generateDispatchConf(conf)
		
	def setupDHCP(self):
		if self.data is not None:
			conf = self.data.replace("#dhcp#", "dhcpd")
		else:
			conf = self.template.replace("#dhcp#", "dhcpd")
		self._generateDispatchConf(conf)


class OpsiHostKeyFileFixture(ConfigFixture):
	
	template = ""
	name = "pckey"

	def addHostKey(self, hostId, hostkey):
		