#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - DHCPD    =
   = = = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

# Imports
import socket, threading

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI import System
from OPSI.Backend.Backend import *
from OPSI.Util.File import DHCPDConfFile

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                    CLASS DHCPDBACKEND                                              =
# ======================================================================================================
class DHCPDBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._dhcpdConfigFile         = u'/etc/dhcp3/dhcpd.conf'
		self._reloadConfigCommand     = u'/usr/bin/sudo /etc/init.d/dhcp3-server restart'
		self._fixedAddressFormat      = u'IP'
		self._defaultClientParameters = { 'next-server': socket.gethostbyname(socket.getfqdn()), 'filename': u'linux/pxelinux.0' }
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('dhcpdconfigfile'):
				self._reloadConfigCommand = value
			elif option in ('reloadconfigcommand'):
				self._reloadConfigCommand = value
			elif option in ('defaultclientparameters'):
				self._defaultClientParameters = value
			elif option in ('fixedaddressformat'):
				if value not in (u'IP', u'FQDN'):
					raise BackendBadValueError(u"Bad value '%s' for fixedAddressFormat, possible values are %s" \
									% (value, u', '.join(['IP', 'FQDN'])) )
				self._fixedAddressFormat = value
		
		if self._defaultClientParameters.get('next-server') and self._defaultClientParameters['next-server'].startswith(u'172'):
			raise BackendBadValueError(u"Refusing to use ip address '%s' as defualt next-server" % self._defaultClientParameters['next-server'])
		
		self._dhcpdConfFile = DHCPDConfFile(self._dhcpdConfigFile)
		self._reloadEvent = threading.Event()
		self._reloadEvent.set()
		self._reloadLock = threading.Lock()
		
	def _triggerReload(self):
		if not self._reloadConfigCommand:
			return
		if not self._reloadEvent.isSet():
			return
		class ReloadThread(threading.Thread):
			def __init__(self, reloadEvent, reloadLock, reloadConfigCommand):
				threading.Thread.__init__(self)
				self._reloadEvent = reloadEvent
				self._reloadLock = reloadLock
				self._reloadConfigCommand = reloadConfigCommand
				
			def run(self):
				self._reloadEvent.clear()
				self._reloadEvent.wait(2)
				self._reloadLock.acquire()
				try:
					result = System.execute(self._reloadConfigCommand)
					for line in result:
						if (line.find(u'error') != -1):
							raise Exception(u'\n'.join(result))
				except Exception, e:
					logger.critical("Failed to restart dhcpd: %s" % e)
				self._reloadLock.release()
				self._reloadEvent.set()
		ReloadThread(self._reloadEvent, self._reloadLock, self._reloadConfigCommand).start()
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		if not isinstance(host, OpsiClient):
			return
		
		logger.debug(u"host_insertObject %s" % host)
		if not host.hardwareAddress:
			logger.warning(u"Cannot insert client %s: hardware address unkown" % host)
			return
		ipAddress = host.ipAddress
		if not ipAddress:
			try:
				logger.info(u"Ip addess of client %s unknown, trying to get host by name" % host)
				ipAddress = socket.gethostbyname(host.id)
				logger.info(u"Client fqdn resolved to '%s'" % ipAddress)
			except Exception, e:
				raise BackendIOError(u"Failed to resolve %s" % host.id)
		
		fixedAddress = ipAddress
		if (self._fixedAddressFormat == 'FQDN'):
			fixedAddress = host.id
		
		self._reloadLock.acquire()
		try:
			self._dhcpdConfFile.parse()
			self._dhcpdConfFile.addHost(
				hostname        = host.id.split('.')[0],
				hardwareAddress = host.hardwareAddress,
				ipAddress       = ipAddress,
				fixedAddress    = fixedAddress,
				parameters      = self._defaultClientParameters)
			self._dhcpdConfFile.generate()
		finally:
			self._reloadLock.release()
		self._triggerReload()
		
	def host_updateObject(self, host):
		if not isinstance(host, OpsiClient):
			return
		
		logger.debug(u"host_updateObject %s" % host)
		self._dhcpdConfFile.parse()
		hostParams = self._dhcpdConfFile.getHost(host.id.split('.')[0])
		if not hostParams:
			logger.debug(u"host %s not found in dhcpd config, nothing to update" % host)
			return
		
		hardwareAddress = host.hardwareAddress
		if not hardwareAddress and hostParams.get('hardware'):
			hardwareAddress = forceHardwareAddress(hostParams['hardware'].split()[-1])
			del hostParams['hardware']
		if not hardwareAddress:
			logger.warning(u"Cannot update client %s: hardware address unkown" % host)
			return
		ipAddress = host.ipAddress
		if not ipAddress and hostParams.get('fixed-address'):
			try:
				ipAddress = forceIPAddress(hostParams['fixed-address'])
			except:
				try:
					ipAddress = forceIPAddress(socket.gethostbyname(hostParams['fixed-address']))
				except:
					pass
			del hostParams['fixed-address']
		if not ipAddress:
			logger.warning(u"Cannot update client %s: ip address unkown" % host)
			return
		
		fixedAddress = ipAddress
		if (self._fixedAddressFormat == 'FQDN'):
			fixedAddress = host.id
		
		self._reloadLock.acquire()
		try:
			self._dhcpdConfFile.addHost(
				hostname        = host.id.split('.')[0],
				hardwareAddress = hardwareAddress,
				ipAddress       = ipAddress,
				fixedAddress    = fixedAddress,
				parameters      = self._defaultClientParameters)
			self._dhcpdConfFile.generate()
		finally:
			self._reloadLock.release()
		self._triggerReload()
		
		
	def host_deleteObjects(self, hosts):
		
		logger.debug(u"host_deleteObjects %s" % hosts)
		
		self._dhcpdConfFile.parse()
		changed = False
		for host in hosts:
			if not isinstance(host, OpsiClient):
				continue
			if self._dhcpdConfFile.getHost(host.id.split('.')[0]):
				self._dhcpdConfFile.deleteHost(host.id.split('.')[0])
				changed = True
		if changed:
			self._triggerReload()
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

