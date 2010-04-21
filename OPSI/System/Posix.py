#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - Posix   =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH
   
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
import os, sys, subprocess, locale, threading, time

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get Logger instance
logger = Logger()

# Constants
BIN_WHICH   = '/usr/bin/which'
WHICH_CACHE = {}

def which(cmd):
	if not WHICH_CACHE.has_key(cmd):
		w = os.popen(u'%s "%s" 2>/dev/null' % (BIN_WHICH, cmd))
		path = w.readline().strip()
		w.close()
		if not path:
			raise Exception(u"Command '%s' not found in PATH" % cmd)
		WHICH_CACHE[cmd] = path
		logger.debug(u"Command '%s' found at: '%s'" % (cmd, WHICH_CACHE[cmd]))
	
	return WHICH_CACHE[cmd]

def execute(cmd, nowait=False, getHandle=False, ignoreExitCode=[], exitOnStderr=False, captureStderr=True, encoding=None):
	"""
	Executes a command and returns output lines as list
	"""
	
	nowait          = forceBool(nowait)
	getHandle       = forceBool(getHandle)
	exitOnStderr    = forceBool(exitOnStderr)
	captureStderr   = forceBool(captureStderr)
	
	exitCode = 0
	result = []
	
	try:
		logger.info(u"Executing: %s" % cmd)
		
		if nowait:
			os.spawnv(os.P_NOWAIT, which('bash'), [which('bash'), '-c', cmd])
			return []
		
		elif getHandle:
			if captureStderr:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)).stdout
			else:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None)).stdout
		
		else:
			data = ''
			stderr = None
			if captureStderr:
				stderr	= subprocess.PIPE
			proc = subprocess.Popen(
				cmd,
				shell	= True,
				stdin	= subprocess.PIPE,
				stdout	= subprocess.PIPE,
				stderr	= stderr,
			)
			if not encoding:
				encoding = proc.stdin.encoding
			if not encoding:
				encoding = locale.getpreferredencoding()
			
			flags = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
			fcntl.fcntl(proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			
			if captureStderr:
				flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
				fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			
			ret = None
			while ret is None:
				ret = proc.poll()
				try:
					chunk = proc.stdout.read()
					if (len(chunk) > 0):
						data += chunk
				except IOError, e:
					if (e.errno != 11):
						raise
				
				if captureStderr:
					try:
						chunk = proc.stderr.read()
						if (len(chunk) > 0):
							if exitOnStderr:
								raise Exception(u"Command '%s' failed: %s" % (cmd, chunk) )
							data += chunk
					except IOError, e:
						if (e.errno != 11):
							raise
				
				time.sleep(0.001)
			
			exitCode = ret
			if data:
				lines = data.split('\n')
				for i in range(len(lines)):
					line = lines[i].decode(encoding)
					if (i == len(lines) - 1) and not line:
						break
					logger.debug(u'>>> %s' % line)
					result.append(line)
			
	except (os.error, IOError), e:
		# Some error occured during execution
		raise Exception(u"Command '%s' failed:\n%s" % (cmd, e) )
	
	logger.debug(u"Exit code: %s" % exitCode)
	if exitCode:
		if   type(ignoreExitCode) is bool and ignoreExitCode:
			pass
		elif type(ignoreExitCode) is list and exitCode in ignoreExitCode:
			pass
		else:
			raise Exception(u"Command '%s' failed (%s):\n%s" % (cmd, exitCode, u'\n'.join(result)) )
	return result

def mount(dev, mountpoint, **options):
	dev = forceUnicode(dev)
	mountpoint = forceFilename(mountpoint)
	if not os.path.isdir(mountpoint):
		os.makedirs(mountpoint)
	for (key, value) in options.items():
		options[key] = forceUnicode(value)
	
	fs = u''
	if dev.lower().startswith('smb://'):
		match = re.search('^smb://([^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = u'-t cifs'
			parts = match.group(1).split('/')
			dev = u'//%s/%s' % (parts[0], parts[1])
			if not 'username' in options:
				options['username'] = u'guest'
			if not 'password' in options:
				options['password'] = u''
		else:
			raise Exception(u"Bad smb uri '%s'" % dev)
		
	elif dev.lower().startswith('webdav://') or dev.lower().startswith('webdavs://') or \
	     dev.lower().startswith('http://') or dev.lower().startswith('https://'):
		match = re.search('^(http|webdav)(s*)(://[^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = '-t davfs'
			dev = 'http' + match.group(2) + match.group(3)
		else:
			raise Exception(u"Bad webdav url '%s'" % dev)
		
		if not 'username' in options:
			options['username'] = u''
		if not 'password' in options:
			options['password'] = u''
		if not 'servercert' in options:
			options['servercert'] = u''
		
		f = open("/etc/davfs2/certs/trusted.pem", "w")
		f.write(options['servercert'])
		f.close()
		os.chmod("/etc/davfs2/certs/trusted.pem", 0644)
		
		f = open("/etc/davfs2/secrets", "r")
		lines = f.readlines()
		f.close()
		f = open("/etc/davfs2/secrets", "w")
		for line in lines:
			if re.search("^%s\s+" % dev, line):
				f.write("#")
			f.write(line)
		f.write('%s "%s" "%s"\n' % (dev, options['username'], options['password']))
		f.close()
		os.chmod("/etc/davfs2/secrets", 0600)
		
		f = open("/etc/davfs2/davfs2.conf", "r")
		lines = f.readlines()
		f.close()
		f = open("/etc/davfs2/davfs2.conf", "w")
		for line in lines:
			if re.search("^servercert\s+", line):
				f.write("#")
			f.write(line)
		f.write("servercert /etc/davfs2/certs/trusted.pem\n")
		f.close()
		
		del options['username']
		del options['password']
		del options['servercert']
		
	elif dev.lower().startswith('/'):
		pass
	
	elif dev.lower().startswith('file://'):
		dev = dev[7:]
	
	else:
		raise Exception(u"Cannot mount unknown fs type '%s'" % dev)
	
	optString = u''
	for (key, value) in options.items():
		key   = forceUnicode(key)
		value = forceUnicode(value)
		if value:
			optString += u',%s=%s' % (key, value)
		else:
			optString += u',%s' % key
	if optString:
		optString = u'-o "%s"' % optString[1:].replace('"', '\\"')
	
	try:
		result = execute(u"%s %s %s %s %s" % (which('mount'), fs, optString, dev, mountpoint))
	except Exception, e:
		logger.error(u"Failed to mount '%s': %s" % (dev, e))
		raise Exception(u"Failed to mount '%s': %s" % (dev, e))
	
def getKernelParams():
	"""
	Reads the kernel cmdline and returns a dict
	containing all key=value pairs.
	keys are converted to lower case
	"""
	params = {}
	cmdline = None
	f = None
	try:
		logger.debug(u'Reading /proc/cmdline')
		f = codes.open("/proc/cmdline", "r", "utf-8")
		cmdline = f.readline()
		cmdline = cmdline.strip()
		f.close()
	except IOError, e:
		if f: f.close()
		raise Exception(u"Error reading '/proc/cmdline': %s" % e)
	if cmdline:
		for option in cmdline.split():
			keyValue = option.split(u"=")
			if ( len(keyValue) < 2 ):
				params[keyValue[0].strip().lower()] = u''
			else:
				params[keyValue[0].strip().lower()] = keyValue[1].strip()
	return params

def getDiskSpaceUsage(path):
	disk = os.statvfs(path)
	info = {}
	info['capacity'] = disk.f_bsize * disk.f_blocks
	info['available'] = disk.f_bsize * disk.f_bavail
	info['used'] = disk.f_bsize * (disk.f_blocks - disk.f_bavail)
	info['usage'] = float(disk.f_blocks - disk.f_bavail) / float(disk.f_blocks)
	logger.info(u"Disk space usage for path '%s': %s" % (path, info))
	return info

def getEthernetDevices():
	devices = []
	f = open("/proc/net/dev")
	try:
		for line in f.readlines():
			line = line.strip()
			if not line or (line.find(':') == -1):
				continue
			device = line.split(':')[0].strip()
			if device.startswith('eth') or device.startswith('tr') or device.startswith('br'):
				logger.info(u"Found ethernet device: '%s'" % device)
				devices.append(device)
	finally:
		f.close()
	return devices

def getNetworkInterfaces():
	interfaces = []
	for device in getEthernetDevices():
		interfaces.append(getNetworkDeviceConfig(device))
	return interfaces
	
def getNetworkDeviceConfig(device):
	if not device:
		raise Exception(u"No device given")
	
	result = {
		'device':          device,
		'hardwareAddress': None,
		'ipAddress':       None,
		'broadcast':       None,
		'netmask':         None,
		'gateway':         None
	}
	for line in execute(u"%s %s" % (which(u'ifconfig'), device)):
		line = line.lower().strip()
		match = re.search('\s([\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}).*', line)
		if match:
			result['hardwareAddress'] = forceHardwareAddress(match.group(1))
			continue
		if line.startswith('inet '):
			parts = line.split(':')
			if (len(parts) != 4):
				logger.error(u"Unexpected ifconfig line '%s'" % line)
				continue
			result['ipAddress'] = forceIpAddress(parts[1].split()[0].strip())
			result['broadcast'] = forceIpAddress(parts[2].split()[0].strip())
			result['netmask']   = forceIpAddress(parts[3].split()[0].strip())
	
	for line in execute(u"%s route" % which(u'ip')):
		line = line.lower().strip()
		match = re.search('via\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\sdev\s(\S+)\s', line)
		if match and (match.group(2).lower() == device.lower()):
			result['gateway'] = forceIpAddress(match.group(1))
	return result

def getDefaultNetworkInterfaceName():
	for interface in getNetworkInterfaces():
		if interface['gateway']:
			return interface['device']
	return None

class NetworkPerformanceCounter(threading.Thread):
	def __init__(self, interface):
		threading.Thread.__init__(self)
		if not interface:
			raise ValueError(u"No interface given")
		self.interface = interface
		self._lastBytesIn = 0
		self._lastBytesOut = 0
		self._lastTime = None
		self._bytesInPerSecond = 0
		self._bytesOutPerSecond = 0
		self._regex = re.compile('\s*(\S+)\:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')
		self._running = False
		self._stopped = False
		self.start()
		
	def __del__(self):
		self.stop()
	
	def stop(self):
		self._stopped = True
		
	def run(self):
		self._running = True
		while not self._stopped:
			self._getStatistics()
			time.sleep(1)
		
	def _getStatistics(self):
		f = open('/proc/net/dev', 'r')
		try:
			for line in f.readlines():
				line = line.strip()
				match = self._regex.search(line)
				if match and (match.group(1) == self.interface):
					#       |   Receive                                                |  Transmit
					# iface: bytes    packets errs drop fifo frame compressed multicast bytes    packets errs drop fifo colls carrier compressed
					now = time.time()
					bytesIn = int(match.group(2))
					bytesOut = int(match.group(10))
					timeDiff = 1
					if self._lastTime:
						timeDiff = now - self._lastTime
					if self._lastBytesIn:
						self._bytesInPerSecond = (bytesIn - self._lastBytesIn)/timeDiff
						if (self._bytesInPerSecond < 0):
							self._bytesInPerSecond = 0
					if self._lastBytesOut:
						self._bytesOutPerSecond = (bytesOut - self._lastBytesOut)/timeDiff
						if (self._bytesOutPerSecond < 0):
							self._bytesOutPerSecond = 0
					self._lastBytesIn = bytesIn
					self._lastBytesOut = bytesOut
					self._lastTime = now
					break
		finally:
			f.close()
		
	def getBytesInPerSecond(self):
		return self._bytesInPerSecond
	
	def getBytesOutPerSecond(self):
		return self._bytesOutPerSecond

def getDHCPResult(device):
	"""
	Reads DHCP result from pump
	returns possible key/values:
	ip, netmask, bootserver, nextserver, gateway, bootfile, hostname, domain.
	keys are converted to lower case
	"""
	if not device:
		raise Exception(u"No device given")
	
	dhcpResult = {}
	try:
		for line in execute( u'%s -s -i %s' % (which('pump'), device) ):
			line = line.strip()
			keyValue = line.split(u":")
			if ( len(keyValue) < 2 ):
				# No ":" in pump output after "boot server" and "next server"
				if line.lstrip().startswith(u'Boot server'):
					keyValue[0] = u'Boot server'
					keyValue.append(line.split()[2])
				elif line.lstrip().startswith(u'Next server'):
					keyValue[0] = u'Next server'
					keyValue.append(line.split()[2])
				else:
					continue
			# Some DHCP-Servers are returning multiple domain names seperated by whitespace,
			# so we split all values at whitespace and take the first element
			dhcpResult[keyValue[0].replace(u' ',u'').lower()] = keyValue[1].strip().split()[0]
	except Exception, e:
		logger.warning(e)
	return dhcpResult
	
def ifconfig(device, address, netmask=None):
	cmd = u'%s %s %s' % (which('ifconfig'), device, forceIpAddress(address))
	if netmask:
		cmd += u' netmask %s' % forceNetmask(netmask)
	execute(cmd)
















##########################



def hardwareInventory(filename=None, config=None):
	from OPSI.Util import objectToBeautifiedText, removeUnit
	import xml.dom.minidom
	import copy as pycopy
	
	
	if not config:
		logger.error("hardwareInventory: no config given")
		return {}
	
	
	
	opsiValues = {}
	
	def getAttribute(dom, tagname, attrname):
		nodelist = dom.getElementsByTagName(tagname)
		if nodelist:
			return nodelist[0].getAttribute(attrname).strip()
		else:
			return ""
	
	def getElementsByAttributeValue(dom, tagName, attributeName, attributeValue):
		elements = []
		for element in dom.getElementsByTagName(tagName):
			if re.search(attributeValue , element.getAttribute(attributeName)):
				elements.append(element)
		return elements
	
	# Read output from lshw
	xmlOut = '\n'.join(execute("%s -xml 2>/dev/null" % which("lshw"), captureStderr=False))
	xmlOut = re.sub('[%c%c%c%c%c%c%c%c%c%c%c%c%c]' % (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0xbd, 0xbf, 0xef, 0xdd), '.', xmlOut)
	dom = xml.dom.minidom.parseString( xmlOut.decode('utf-8', 'replace').encode('utf-8') )
	
	# Read output from lspci
	lspci = {}
	busId = None
	devRegex = re.compile('([\d\.:a-f]+)\s+([\da-f]+):\s+([\da-f]+):([\da-f]+)\s*(\(rev ([^\)]+)\)|)')
	subRegex = re.compile('\s*Subsystem:\s+([\da-f]+):([\da-f]+)\s*')
	for line in execute("%s -vn" % which("lspci")):
		if not line.strip():
			continue
		match = re.search(devRegex, line)
		if match:
			busId = match.group(1)
			lspci[busId] = { 	'vendorId':		match.group(3),
						'deviceId':		match.group(4),
						'subsystemVendorId':	'',
						'subsystemDeviceId':	'',
						'revision':		match.group(6) or '' }
			continue
		match = re.search(subRegex, line)
		if match:
			lspci[busId]['subsystemVendorId'] = match.group(1)
			lspci[busId]['subsystemDeviceId'] = match.group(2)
	logger.debug("Parsed lspci info:")
	logger.debug(objectToBeautifiedText(lspci))
	
	# Read hdaudio information from alsa
	hdaudio = {}
	if os.path.exists('/proc/asound'):
		for card in os.listdir('/proc/asound'):
			if not re.search('^card\d$', card):
				continue
			logger.debug("Found hdaudio card '%s'" % card)
			for codec in os.listdir('/proc/asound/' + card):
				if not re.search('^codec#\d$', codec):
					continue
				if not os.path.isfile('/proc/asound/' + card + '/' + codec):
					continue
				f = open('/proc/asound/' + card + '/' + codec)
				logger.debug("   Found hdaudio codec '%s'" % codec)
				hdaudioId = card + codec
				hdaudio[hdaudioId] = {}
				for line in f.readlines():
					if   line.startswith('Codec:'):
						hdaudio[hdaudioId]['codec'] = line.split(':', 1)[1].strip()
					elif line.startswith('Address:'):
						hdaudio[hdaudioId]['address'] = line.split(':', 1)[1].strip()
					elif line.startswith('Vendor Id:'):
						vid = line.split('x', 1)[1].strip()
						hdaudio[hdaudioId]['vendorId'] = vid[0:4]
						hdaudio[hdaudioId]['deviceId'] = vid[4:8]
					elif line.startswith('Subsystem Id:'):
						sid = line.split('x', 1)[1].strip()
						hdaudio[hdaudioId]['subsystemVendorId'] = sid[0:4]
						hdaudio[hdaudioId]['subsystemDeviceId'] = sid[4:8]
					elif line.startswith('Revision Id:'):
						hdaudio[hdaudioId]['revision'] = line.split('x', 1)[1].strip()
				f.close()
				logger.debug("      Codec info: '%s'" % hdaudio[hdaudioId])
	
	# Read output from lsusb
	lsusb = {}
	busId = None
	devId = None
	indent = -1
	currentKey = None
	status = False
	
	devRegex = re.compile('^Bus\s+(\d+)\s+Device\s+(\d+)\:\s+ID\s+([\da-fA-F]{4})\:([\da-fA-F]{4})\s*(.*)$')
	descriptorRegex = re.compile('^(\s*)(.*)\s+Descriptor\:\s*$')
	deviceStatusRegex = re.compile('^(\s*)Device\s+Status\:\s+(\S+)\s*$')
	deviceQualifierRegex = re.compile('^(\s*)Device\s+Qualifier\s+.*\:\s*$')
	keyRegex = re.compile('^(\s*)([^\:]+)\:\s*$')
	keyValueRegex = re.compile('^(\s*)(\S+)\s+(.*)$')
	
	try:
		for line in execute("%s -v" % which("lsusb")):
			if not line.strip() or (line.find('** UNAVAILABLE **') != -1):
				continue
			line = line.decode('ISO-8859-15', 'replace').encode('utf-8', 'replace')
			match = re.search(devRegex, line)
			if match:
				busId = match.group(1)
				devId = match.group(2)
				descriptor = None
				indent = -1
				currentKey = None
				status = False
				logger.debug("Device: %s:%s" % (busId, devId))
				lsusb[busId+":"+devId] = {
					'device': {},
					'configuration': {},
					'interface': {},
					'endpoint': [],
					'hid device': {},
					'hub': {},
					'qualifier': {},
					'status': {}
				}
				continue
			
			if status:
				lsusb[busId+":"+devId]['status'].append(line.strip())
				continue
			
			match = re.search(deviceStatusRegex, line)
			if match:
				status = True
				lsusb[busId+":"+devId]['status'] = [ match.group(2) ]
				continue
			
			match = re.search(deviceQualifierRegex, line)
			if match:
				descriptor = 'qualifier'
				logger.debug("Qualifier")
				currentKey = None
				indent = -1
				continue
			
			match = re.search(descriptorRegex, line)
			if match:
				descriptor = match.group(2).strip().lower()
				logger.debug("Descriptor: %s" % descriptor)
				if type(lsusb[busId+":"+devId][descriptor]) is list:
					lsusb[busId+":"+devId][descriptor].append({})
				currentKey = None
				indent = -1
				continue
			
			if not descriptor:
				logger.error("No descriptor")
				continue
			
			if not lsusb[busId+":"+devId].has_key(descriptor):
				logger.error("Unknown descriptor '%s'" % descriptor)
				continue
			
			(key, value) = ('', '')
			match = re.search(keyRegex, line)
			if match:
				key = match.group(2)
				indent = len(match.group(1))
			else:
				match = re.search(keyValueRegex, line)
				if match:
					if (indent >= 0) and (len(match.group(1)) > indent):
						key = currentKey
						value = match.group(0).strip()
					else:
						(key, value) = (match.group(2), match.group(3).strip())
						indent = len(match.group(1))
			
			logger.debug("key: '%s', value: '%s'" % (key, value))
			
			if not key or not value:
				continue
			
			currentKey = key
			if type(lsusb[busId+":"+devId][descriptor]) is list:
				if not lsusb[busId+":"+devId][descriptor][-1].has_key(key):
					lsusb[busId+":"+devId][descriptor][-1][key] = [ ]
				lsusb[busId+":"+devId][descriptor][-1][key].append(value)
			
			else:
				if not lsusb[busId+":"+devId][descriptor].has_key(key):
					lsusb[busId+":"+devId][descriptor][key] = [ ]
				lsusb[busId+":"+devId][descriptor][key].append(value)
			
			
		logger.debug("Parsed lsusb info:")
		logger.debug(objectToBeautifiedText(lsusb))
	except Exception, e:
		logger.error(e)
	
	# Read output from dmidecode
	dmidecode = {}
	dmiType = None
	header = True
	option = None
	optRegex = re.compile('(\s+)([^:]+):(.*)')
	for line in execute(which("dmidecode")):
		try:
			if not line.strip():
				continue
			if line.startswith('Handle'):
				dmiType = None
				header = False
				option = None
				continue
			if header:
				continue
			if not dmiType:
				dmiType = line.strip()
				if (dmiType.lower() == 'end of table'):
					break
				if not dmidecode.has_key(dmiType):
					dmidecode[dmiType] = []
				dmidecode[dmiType].append({})
			else:
				match = re.search(optRegex, line)
				if match:
					option = match.group(2).strip()
					value = match.group(3).strip()
					dmidecode[dmiType][-1][option] = removeUnit(value)
				elif option:
					if not type(dmidecode[dmiType][-1][option]) is list:
						if dmidecode[dmiType][-1][option]:
							dmidecode[dmiType][-1][option] = [ dmidecode[dmiType][-1][option] ]
						else:
							dmidecode[dmiType][-1][option] = []
					dmidecode[dmiType][-1][option].append(removeUnit(line.strip()))
		except Exception, e:
			logger.error("Error while parsing dmidecode output '%s': %s" % (line.strip(), e))
	logger.debug("Parsed dmidecode info:")
	logger.debug(objectToBeautifiedText(dmidecode))
	
	# Build hw info structure
	for hwClass in config:
		
		if not hwClass.get('Class') or not hwClass['Class'].get('Opsi') or not hwClass['Class'].get('Linux'):
			continue
		
		opsiClass = hwClass['Class']['Opsi']
		linuxClass = hwClass['Class']['Linux']
		
		logger.debug( "Processing class '%s' : '%s'" % (opsiClass, linuxClass) )
		
		if linuxClass.startswith('[lshw]'):
			# Get matching xml nodes
			devices = []
			for hwclass in linuxClass[6:].split('|'):
				hwid = ''
				filter = None
				if (hwclass.find(':') != -1):
					(hwclass, hwid) = hwclass.split(':', 1)
					if (hwid.find(':') != -1):
						(hwid, filter) = hwid.split(':', 1)
				
				logger.debug( "Class is '%s', id is '%s', filter is: %s" % (hwClass, hwid, filter) )
				
				devs = getElementsByAttributeValue(dom, 'node', 'class', hwclass)
				for dev in devs:
					if dev.hasChildNodes():
						for child in dev.childNodes:
							if (child.nodeName == "businfo"):
								busInfo = child.firstChild.data.strip()
								if busInfo.startswith('pci@'):
									logger.debug("Getting pci bus info for '%s'" % busInfo)
									pciBusId = busInfo.split('@')[1]
									if pciBusId.startswith('0000:'):
										pciBusId = pciBusId[5:]
									pciInfo = lspci.get(pciBusId, {})
									for (key, value) in pciInfo.items():
										elem = dom.createElement(key)
										elem.childNodes.append( dom.createTextNode(value) )
										dev.childNodes.append( elem )
								break
				if hwid:
					filtered = []
					for dev in devs:
						if re.search(hwid, dev.getAttribute('id')):
							if not filter:
								filtered.append(dev)
							else:
								(attr, method) = filter.split('.', 1)
								if dev.getAttribute(attr):
									if eval("dev.getAttribute(attr).%s" % method):
										filtered.append(dev)
								elif dev.hasChildNodes():
									for child in dev.childNodes:
										if (child.nodeName == attr) and child.hasChildNodes():
											if eval("child.firstChild.data.strip().%s" % method):
												filtered.append(dev)
												break
										try:
											if child.hasAttributes() and child.getAttribute(attr):
												if eval("child.getAttribute(attr).%s" % method):
													filtered.append(dev)
													break
										except:
											pass
					devs = filtered
				
				logger.debug2( "Found matching devices: %s" % devs)
				devices.extend(devs)
			
			# Process matching xml nodes
			for i in range(len(devices)):
				
				if not opsiValues.has_key(opsiClass):
					opsiValues[opsiClass] = []
				opsiValues[opsiClass].append({})
				
				if not hwClass.get('Values'):
					break
				
				for attribute in hwClass['Values']:
					elements = [ devices[i] ]
					if not attribute.get('Opsi') or not attribute.get('Linux'):
						continue
					logger.debug2( "Processing attribute '%s' : '%s'" % (attribute['Linux'], attribute['Opsi']) )
					for attr in attribute['Linux'].split('||'):
						attr = attr.strip()
						method = None
						data = None
						for part in attr.split('/'):
							if (part.find('.') != -1):
								(part, method) = part.split('.', 1)
							nextElements = []
							for element in elements:
								for child in element.childNodes:
									try:
										if (child.nodeName == part):
											nextElements.append(child)
										elif child.hasAttributes() and \
										     ((child.getAttribute('class') == part) or (child.getAttribute('id').split(':')[0] == part)):
											nextElements.append(child)
									except:
										pass
							if not nextElements:
								logger.warning("Attribute part '%s' not found" % part)
								break
							elements = nextElements
						
						if not data:
							if not elements:
								opsiValues[opsiClass][i][attribute['Opsi']] = ''
								logger.warning("No data found for attribute '%s' : '%s'" % (attribute['Linux'], attribute['Opsi']))
								continue
							
							for element in elements:
								if element.getAttribute(attr):
									data = element.getAttribute(attr).strip()
								elif element.getAttribute('value'):
									data = element.getAttribute('value').strip()
								elif element.hasChildNodes():
									data = element.firstChild.data.strip()
						if method and data:
							try:
								logger.debug("Eval: %s.%s" % (data, method))
								data = eval("data.%s" % method)
							except Exception, e:
								logger.error("Failed to excecute '%s.%s': %s" % (data, method, e))
						logger.debug2("Data: %s" % data)
						opsiValues[opsiClass][i][attribute['Opsi']] = data
						if data:
							break
		
		# Get hw info from dmidecode
		elif linuxClass.startswith('[dmidecode]'):
			opsiValues[opsiClass] = []
			for hwclass in linuxClass[11:].split('|'):
				(filterAttr, filterExp) = (None, None)
				if (hwclass.find(':') != -1):
					(hwclass, filter) = hwclass.split(':', 1)
					if (filter.find('.') != -1):
						(filterAttr, filterExp) = filter.split('.', 1)
				
				for dev in dmidecode.get(hwclass, []):
					if filterAttr and dev.get(filterAttr) and not eval("str(dev.get(filterAttr)).%s" % filterExp):
						continue
					device = {}
					for attribute in hwClass['Values']:
						if not attribute.get('Linux'):
							continue
						for aname in attribute['Linux'].split('||'):
							aname = aname.strip()
							method = None
							if (aname.find('.') != -1):
								(aname, method) = aname.split('.', 1)
							if method:
								try:
									logger.debug("Eval: %s.%s" % (dev.get(aname, ''), method))
									device[attribute['Opsi']] = eval("dev.get(aname, '').%s" % method)
								except Exception, e:
									device[attribute['Opsi']] = ''
									logger.error("Failed to excecute '%s.%s': %s" % (dev.get(aname, ''), method, e))
							else:
								device[attribute['Opsi']] = dev.get(aname)
							if device[attribute['Opsi']]:
								break
					opsiValues[hwClass['Class']['Opsi']].append(device)
		
		# Get hw info from alsa hdaudio info
		elif linuxClass.startswith('[hdaudio]'):
			opsiValues[opsiClass] = []
			for (hdaudioId, dev) in hdaudio.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux') or not dev.has_key(attribute['Linux']):
						continue
					try:
						device[attribute['Opsi']] = dev[attribute['Linux']]
					except Exception, e:
						logger.warning(e)
						device[attribute['Opsi']] = ''
				opsiValues[opsiClass].append(device)
		
		# Get hw info from lsusb
		elif linuxClass.startswith('[lsusb]'):
			opsiValues[opsiClass] = []
			for (busId, dev) in lsusb.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux'):
						continue
					try:
						value = pycopy.deepcopy(dev)
						for key in (attribute['Linux'].split('/')):
							method = None
							if (key.find('.') != -1):
								(key, method) = key.split('.', 1)
							if not type(value) is dict or not value.has_key(key):
								logger.error("Key '%s' not found" % key)
								value = ''
								break
							value = value[key]
							if type(value) is list:
								value = ', '.join(value)
							if method:
								value = eval("value.%s" % method)
							
						device[attribute['Opsi']] = value
					except Exception, e:
						logger.warning(e)
						device[attribute['Opsi']] = ''
				opsiValues[opsiClass].append(device)
	
	opsiValues['SCANPROPERTIES'] = [ { "scantime": time.strftime("%Y-%m-%d %H:%M:%S") } ]
	
	logger.debug("Result of hardware inventory:\n" + objectToBeautifiedText(opsiValues))
	
	return opsiValues

