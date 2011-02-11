#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Windows   =
   = = = = = = = = = = = = = = = = = = =
   
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

__version__ = '4.0.1'

# Imports
import re, os, time, socket, sys, locale, subprocess, difflib, threading

# Win32 imports
from ctypes import *
import pywintypes, ntsecuritycon, win32service, win32event, win32con, win32ts, win32process, win32file
import win32api, win32security, win32gui, win32net, win32wnet, win32netcon, _winreg
import win32pdhutil, win32pdh, win32pipe, msvcrt

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get Logger instance
logger = Logger()

# Constants
HKEY_CURRENT_USER = _winreg.HKEY_CURRENT_USER
HKEY_LOCAL_MACHINE = _winreg.HKEY_LOCAL_MACHINE

TH32CS_SNAPPROCESS = 0x00000002
class PROCESSENTRY32(Structure):
     _fields_ = [("dwSize", c_ulong),
                 ("cntUsage", c_ulong),
                 ("th32ProcessID", c_ulong),
                 ("th32DefaultHeapID", c_ulong),
                 ("th32ModuleID", c_ulong),
                 ("cntThreads", c_ulong),
                 ("th32ParentProcessID", c_ulong),
                 ("pcPriClassBase", c_ulong),
                 ("dwFlags", c_ulong),
                 ("szExeFile", c_char * 260)]


class SystemSpecificHook(object):
	def __init__(self):
		pass

hooks = []
def addSystemHook(hook):
	global hooks
	if not hook in hooks:
		hooks.append(hook)

def removeSystemHook(hook):
	global hooks
	if hook in hooks:
		hooks.remove(hook)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                               INFO                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getArchitecture():
	if (2**63-1 == sys.maxint):
		return u'x64'
	return u'x86'

def getOpsiHotfixName():
	arch = getArchitecture()
	major = sys.getwindowsversion()[0]
	minor = sys.getwindowsversion()[1]
	os = u'unknown'
	lang = u'unknown'
	
	if (major == 5):
		loc = locale.getdefaultlocale()[0].split('_')[0]
		if   (loc == 'en'): lang = u'enu'
		elif (loc == 'de'): lang = u'deu'
		elif (loc == 'fr'): lang = u'fra'
		elif (loc == 'it'): lang = u'ita'
		elif (loc == 'ch'): lang = u'chs'
		if (minor == 1):
			os = u'winxp'
		elif (minor == 2):
			if (arch == 'x86'):
				os = u'win2003'
			else:
				os = u'win2003-winxp'
	elif (major == 6):
		lang = u'glb'
		if (minor == 0):
			if (arch == 'x86'):
				os = u'win7'
			else:
				os = u'win7-win2008r2'
		elif (minor == 1):
			os = u'vista-win2008'
		
	return u'mshotfix-%s-%s-%s' % (os, arch, lang)
	
def getHostname():
	return forceHostname(win32api.GetComputerName())

def getFQDN():
	fqdn = socket.getfqdn().lower()
	if ( len(fqdn.split(u'.')) < 2 ):
		return getHostname()
	return forceUnicodeLower(getHostname() + u'.' + u'.'.join(fqdn.split(u'.')[1:]))

def getFileVersionInfo(filename):
	filename = forceFilename(filename)
	(lang, codepage) = win32api.GetFileVersionInfo(filename, u'\\VarFileInfo\\Translation')[0]
	path = u'\\StringFileInfo\\%04X%04X\\%%s' % (lang, codepage)
	info = {
		'CompanyName':      forceUnicode(win32api.GetFileVersionInfo(filename, path % 'CompanyName')),
		'SpecialBuild':     forceUnicode(win32api.GetFileVersionInfo(filename, path % 'SpecialBuild')),
		'Comments':         forceUnicode(win32api.GetFileVersionInfo(filename, path % 'Comments')),
		'FileDescription':  forceUnicode(win32api.GetFileVersionInfo(filename, path % 'FileDescription')),
		'FileVersion':      forceUnicode(win32api.GetFileVersionInfo(filename, path % 'FileVersion')),
		'InternalName':     forceUnicode(win32api.GetFileVersionInfo(filename, path % 'InternalName')),
		'LegalCopyright':   forceUnicode(win32api.GetFileVersionInfo(filename, path % 'LegalCopyright')),
		'LegalTrademarks':  forceUnicode(win32api.GetFileVersionInfo(filename, path % 'LegalTrademarks')),
		'OriginalFilename': forceUnicode(win32api.GetFileVersionInfo(filename, path % 'OriginalFilename')),
		'PrivateBuild':     forceUnicode(win32api.GetFileVersionInfo(filename, path % 'PrivateBuild')),
		'ProductName':      forceUnicode(win32api.GetFileVersionInfo(filename, path % 'ProductName')),
		'ProductVersion':   forceUnicode(win32api.GetFileVersionInfo(filename, path % 'ProductVersion'))
	}
	logger.debug(u"File version info for '%s': %s" % (filename, info))
	return info

def getProgramFilesDir():
	return getRegistryValue(HKEY_LOCAL_MACHINE, u'Software\\Microsoft\\Windows\\CurrentVersion', u'ProgramFilesDir')

def getSystemDrive():
	return forceUnicode(os.getenv('SystemDrive', u'c:'))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            NETWORK                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getNetworkInterfaces():
	try:
		# This code is from Michael Amrhein
		# http://www.mailinglistarchive.com/python-dev@python.org/msg07330.html
		MAX_ADAPTER_DESCRIPTION_LENGTH = 128
		MAX_ADAPTER_NAME_LENGTH = 256
		MAX_ADAPTER_ADDRESS_LENGTH = 8
		class IP_ADDR_STRING(Structure):
			pass
		LP_IP_ADDR_STRING = POINTER(IP_ADDR_STRING)
		IP_ADDR_STRING._fields_ = [
			("next",      LP_IP_ADDR_STRING),
			("ipAddress", c_char * 16),
			("ipMask",    c_char * 16),
			("context",   c_ulong)]
		class IP_ADAPTER_INFO(Structure):
			pass
		LP_IP_ADAPTER_INFO = POINTER(IP_ADAPTER_INFO)
		IP_ADAPTER_INFO._fields_ = [
			("next",                LP_IP_ADAPTER_INFO),
			("comboIndex",          c_ulong),
			("adapterName",         c_char * (MAX_ADAPTER_NAME_LENGTH + 4)),
			("description",         c_char * (MAX_ADAPTER_DESCRIPTION_LENGTH + 4)),
			("addressLength",       c_uint),
			("address",             c_ubyte * MAX_ADAPTER_ADDRESS_LENGTH),
			("index",               c_ulong),
			("type",                c_uint),
			("dhcpEnabled",         c_uint),
			("currentIpAddress",    LP_IP_ADDR_STRING),
			("ipAddressList",       IP_ADDR_STRING),
			("gatewayList",         IP_ADDR_STRING),
			("dhcpServer",          IP_ADDR_STRING),
			("haveWins",            c_uint),
			("primaryWinsServer",   IP_ADDR_STRING),
			("secondaryWinsServer", IP_ADDR_STRING),
			("leaseObtained",       c_ulong),
			("leaseExpires",        c_ulong)
		]
		GetAdaptersInfo = windll.iphlpapi.GetAdaptersInfo
		GetAdaptersInfo.restype = c_ulong
		GetAdaptersInfo.argtypes = [LP_IP_ADAPTER_INFO, POINTER(c_ulong)]
		adapterList = (IP_ADAPTER_INFO * 10)()
		buflen = c_ulong(sizeof(adapterList))
		rc = GetAdaptersInfo(byref(adapterList[0]), byref(buflen))
		return adapterList
	except Exception, e:
		logger.logException(e)
		raise Exception(u"Failed to get network interfaces: %s" % forceUnicode(e))


def getDefaultNetworkInterfaceName():
	for interface in getNetworkInterfaces():
		if interface.gatewayList.ipAddress:
			return interface.description
	return None

class NetworkPerformanceCounter(threading.Thread):
	def __init__(self, interface):
		threading.Thread.__init__(self)
		self.interface = None
		self._queryHandle = None
		self._inCounterHandle = None
		self._outCounterHandle = None
		self._running = False
		self._stopped = False
		self._inData = []
		self._outData = []
		
		(items, instances) = win32pdh.EnumObjectItems(
						None,
						None,
						win32pdhutil.find_pdh_counter_localized_name('Network Interface'),
						win32pdh.PERF_DETAIL_WIZARD)
		bestRatio = 0.0
		for instance in instances:
			ratio = difflib.SequenceMatcher(None, instance, interface).ratio()
			logger.info(u"NetworkPerformanceCounter: searching for interface '%s', got interface '%s', match ratio: %s" % (interface, instance, ratio))
			if (ratio > bestRatio):
				bestRatio = ratio
				self.interface = instance
		logger.info(u"NetworkPerformanceCounter: using interface '%s' match ratio (%s) with available counters: %s" % (self.interface, bestRatio, items))
		
		# For correct translations (find_pdh_counter_localized_name) see:
		# HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Perflib
		self._queryHandle = win32pdh.OpenQuery()
		self.bytesInPerSecondCounter = win32pdh.MakeCounterPath( (
						None,
						win32pdhutil.find_pdh_counter_localized_name('Network Interface'),
						self.interface,
						None,
						-1,
						win32pdhutil.find_pdh_counter_localized_name('Bytes In/sec') ) )
		self.bytesOutPerSecondCounter = win32pdh.MakeCounterPath( (
						None,
						win32pdhutil.find_pdh_counter_localized_name('Network Interface'),
						self.interface,
						None,
						-1,
						win32pdhutil.find_pdh_counter_localized_name('Bytes Sent/sec') ) )
		try:
			self._inCounterHandle = win32pdh.AddCounter(self._queryHandle, self.bytesInPerSecondCounter)
		except Exception, e:
			raise Exception(u"Failed to add inCounterHandle %s->%s: %s" % (
				win32pdhutil.find_pdh_counter_localized_name('Network Interface'),
				win32pdhutil.find_pdh_counter_localized_name('Bytes In/sec'),
				e
			))
		try:
			self._outCounterHandle = win32pdh.AddCounter(self._queryHandle, self.bytesOutPerSecondCounter)
		except Exception, e:
			raise Exception(u"Failed to add outCounterHandle %s->%s: %s" % (
				win32pdhutil.find_pdh_counter_localized_name('Network Interface'),
				win32pdhutil.find_pdh_counter_localized_name('Bytes Sent/sec'),
				e
			))
		self.start()
		
	def __del__(self):
		self.stop()
	
	def stop(self):
		self._stopped = True
	
	def run(self):
		self._running = True
		
		while not self._stopped:
			win32pdh.CollectQueryData(self._queryHandle)
			(tp, val) = win32pdh.GetFormattedCounterValue(self._inCounterHandle, win32pdh.PDH_FMT_LONG)
			self._inData.append(val)
			print self._inData
			if (len(self._inData) > 3):
				self._inData.pop(0)
			(tp, val) = win32pdh.GetFormattedCounterValue(self._outCounterHandle, win32pdh.PDH_FMT_LONG)
			self._outData.append(val)
			if (len(self._outData) > 3):
				self._outData.pop(0)
			time.sleep(1.0)
		if self._inCounterHandle:
			win32pdh.RemoveCounter(self._inCounterHandle)
		if self._outCounterHandle:
			win32pdh.RemoveCounter(self._outCounterHandle)
		if self._queryHandle:
			win32pdh.CloseQuery(self._queryHandle)
		
	def getBytesInPerSecond(self):
		data = 0.0
		if not self._inData:
			return data
		count = 0.0
		for d in self._inData:
			data += d
			count += 1.0
		return data/count
	
	def getBytesOutPerSecond(self):
		data = 0.0
		if not self._outData:
			return data
		count = 0.0
		for d in self._outData:
			data += d
			count += 1.0
		return data/count
	
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            HELPERS                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def copyACL(src, dest):
	revision = src.GetAclRevision()
	logger.debug2(u"copyACL: ace count is %s" % src.GetAceCount())
	for i in range(src.GetAceCount()):
		logger.debug2(u"copyACL: processing ace #%s" % i)
		ace = src.GetAce(i)
		logger.debug2(u"copyACL: ace: %s" % str(ace))
		# XXX: Not sure if these are actually correct.
		# See http://aspn.activestate.com/ASPN/docs/ActivePython/2.4/pywin32/PyACL__GetAce_meth.html
		if   (ace[0][0] == win32con.ACCESS_ALLOWED_ACE_TYPE):
			dest.AddAccessAllowedAce(revision, ace[1], ace[2])
		elif (ace[0][0] == win32con.ACCESS_DENIED_ACE_TYPE):
			dest.AddAccessDeniedAce(revision, ace[1], ace[2])
		elif (ace[0][0] == win32con.SYSTEM_AUDIT_ACE_TYPE):
			dest.AddAuditAccessAce(revision, ace[1], ace[2], 1, 1)
		elif (ace[0][0] == win32con.ACCESS_ALLOWED_OBJECT_ACE_TYPE):
			dest.AddAccessAllowedObjectAce(revision, ace[0][1], ace[1], ace[2], ace[3], ace[4])
		elif (ace[0][0] == win32con.ACCESS_DENIED_OBJECT_ACE_TYPE):
			dest.AddAccessDeniedObjectAce(revision, ace[0][1], ace[1], ace[2], ace[3], ace[4])
		elif (ace[0][0] == win32con.SYSTEM_AUDIT_OBJECT_ACE_TYPE):
			dest.AddAuditAccessObjectAce(revision, ace[0][1], ace[1], ace[2], ace[3], ace[4], 1, 1)
	return src.GetAceCount()

def adjustPrivilege(priv, enable = 1):
	# Get the process token.
	flags = ntsecuritycon.TOKEN_ADJUST_PRIVILEGES | ntsecuritycon.TOKEN_QUERY
	htoken = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
	# Get the ID for the system shutdown privilege.
	id = win32security.LookupPrivilegeValue(None, priv)
	# Now obtain the privilege for this process.
	# Create a list of the privileges to be added.
	if enable:
		newPrivileges = [(id, win32security.SE_PRIVILEGE_ENABLED)]
	else:
		newPrivileges = [(id, 0)]
	# and make the adjustment.
	win32security.AdjustTokenPrivileges(htoken, 0, newPrivileges)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                             REGISTRY                                              -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getRegistryValue(key, subKey, valueName, reflection=True):
	hkey = _winreg.OpenKey(key, subKey)
	if not reflection and (getArchitecture() == 'x64'):
		_winreg.DisableReflectionKey(hkey)
	(value, type) = _winreg.QueryValueEx(hkey, valueName)
	if (getArchitecture() == 'x64') and not reflection:
		if _winreg.QueryReflectionKey(hkey):
			_winreg.EnableReflectionKey(hkey)
	return value

def setRegistryValue(key, subKey, valueName, value):
	_winreg.CreateKey(key, subKey)
	hkey = _winreg.OpenKey(key, subKey, 0, _winreg.KEY_WRITE)
	if type(value) is int:
		_winreg.SetValueEx(hkey, valueName, 0, _winreg.REG_DWORD, value)
	else:
		_winreg.SetValueEx(hkey, valueName, 0, _winreg.REG_SZ, value)

def createRegistryKey(key, subKey):
	_winreg.CreateKey(key, subKey)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            FILESYSTEMS                                            -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def getFreeDrive(startLetter = 'a'):
	startLetter = forceUnicodeLower(startLetter)
	startLetterSeen = False
	for letter in ('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'):
		if (startLetter == letter):
			startLetterSeen = True
		if not startLetterSeen:
			continue
		letter += ':'
		if (win32file.GetDriveType(letter) == 1):
			return letter
	raise Exception(u'No free drive available')

def getDiskSpaceUsage(path):
	path = forceUnicode(path)
	if (len(path) == 1):
		path = path + ':'
	info = {
		'capacity':  0,
		'available': 0,
		'used':      0,
		'usage':     0
	}
	#(items, instances) = win32pdh.EnumObjectItems(
	#			None,
	#			None,
	#			win32pdhutil.find_pdh_counter_localized_name('LogicalDisk'),
	#			win32pdh.PERF_DETAIL_WIZARD)
	#
	#for instance in instances:
	#	if path.lower().startswith(instance.lower()):
	(sectPerCluster, bytesPerSector, freeClusters, totalClusters) = win32file.GetDiskFreeSpace(path)
	info['capacity'] = totalClusters * sectPerCluster * bytesPerSector
	info['available'] = freeClusters * sectPerCluster * bytesPerSector
	info['used'] = info['capacity'] - info['available']
	info['usage'] = float(info['used']) / float(info['capacity'])
	#break
	
	logger.info(u"Disk space usage for path '%s': %s" % (path, info))
	return info

def mount(dev, mountpoint, **options):
	dev = forceUnicode(dev)
	mountpoint = forceUnicode(mountpoint)
	
	fs = u''
	
	match = re.search('^[a-zA-Z]:$', mountpoint)
	if not match:
		logger.error(u"Bad mountpoint '%s'" % mountpoint)
		raise ValueError(u"Bad mountpoint '%s'" % mountpoint)
	
	if dev.lower().startswith('smb://') or dev.lower().startswith('cifs://'):
		match = re.search('^(smb|cifs)://([^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			parts = match.group(2).split('/')
			dev = u'\\\\%s\\%s' % (parts[0], parts[1])
			
			if not 'username' in options:
				options['username'] = None
			
			elif options['username'] and (options['username'].find(u'\\') != -1):
				options['domain'] = options['username'].split(u'\\')[-1]
				options['username'] = options['username'].split(u'\\')[0]
				
			if not 'password' in options:
				options['password'] = None
			else:
				logger.addConfidentialString(options['password'])
			
			if not 'domain' in options:
				options['domain'] = getHostname()
			username = None
			if options['username']:
				username = options['domain'] + u'\\' + options['username']
			
			try:
				try:
					# Remove connection and update user profile (remove persistent connection)
					win32wnet.WNetCancelConnection2(mountpoint, win32netcon.CONNECT_UPDATE_PROFILE, True)
				except pywintypes.error, details:
					if (details[0] == 2250):
						# Not connected
						logger.debug(u"Failed to umount '%s': %s" % (mountpoint, details))
					else:
						raise
				
				logger.notice(u"Mounting '%s' to '%s'" % (dev, mountpoint))
				# Mount not persistent
				win32wnet.WNetAddConnection2(
					win32netcon.RESOURCETYPE_DISK,
					mountpoint,
					dev,
					None,
					username,
					options['password'],
					0
				)
			
			except Exception, e:
				logger.error(u"Failed to mount '%s': %s" % (dev, forceUnicode(e)))
				raise Exception(u"Failed to mount '%s': %s" % (dev, forceUnicode(e)))
		else:
			raise Exception(u"Bad smb/cifs uri '%s'" % dev)
		
	else:
		raise Exception(u"Cannot mount unknown fs type '%s'" % dev)
	
def umount(mountpoint):
	try:
		# Remove connection and update user profile (remove persistent connection)
		win32wnet.WNetCancelConnection2(mountpoint, win32netcon.CONNECT_UPDATE_PROFILE, True)
	except pywintypes.error, details:
		if (details[0] == 2250):
			# Not connected
			logger.warning(u"Failed to umount '%s': %s" % (mountpoint, details))
		else:
			raise
	
	except Exception, e:
		logger.error(u"Failed to umount '%s': %s" % (mountpoint, forceUnicode(e)))
		raise Exception (u"Failed to umount '%s': %s" % (mountpoint, forceUnicode(e)))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                               SESSION / WINSTA / DESKTOP HANDLING                                 -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getActiveConsoleSessionId():
	try:
		return forceInt(windll.kernel32.WTSGetActiveConsoleSessionId())
	except Exception, e:
		logger.warning(u"Failed to get WTSGetActiveConsoleSessionId: %s, returning 0" % forceUnicode(e))
		return 0

def getActiveDesktopName():
	desktop = win32service.OpenInputDesktop(0, True, win32con.MAXIMUM_ALLOWED)
	return forceUnicode(win32service.GetUserObjectInformation(desktop, win32con.UOI_NAME))

def getActiveSessionIds():
	sessionIds = []
	logger.debug(u"Getting active sessions")
	#for s in win32ts.WTSEnumerateSessions():
	#	logger.debug(u"   Found session: %s" % s)
	#	sessionIds.append(forceInt(s['SessionId']))
	for s in win32security.LsaEnumerateLogonSessions():
		sessionData = win32security.LsaGetLogonSessionData(s)
		if not forceInt(sessionData['LogonType']) in (2, 10):
			continue
		sessionId = forceInt(sessionData['Session'])
		if (sessionId == 0) and (sys.getwindowsversion()[0] >= 6):
			# Service session
			continue
		logger.debug(u"   Found session: %s" % sessionData)
		if not sessionId in sessionIds:
			sessionIds.append(sessionId)
	return sessionIds

def getActiveSessionId(verifyProcessRunning = "winlogon.exe"):
	defaultSessionId = getActiveConsoleSessionId()
	if (sys.getwindowsversion()[0] >= 6) and (defaultSessionId == 0):
		defaultSessionId = 1
	sessionIds = []
	newest = None
	for s in win32security.LsaEnumerateLogonSessions():
		sessionData = win32security.LsaGetLogonSessionData(s)
		if not forceInt(sessionData['LogonType']) in (2, 10):
			continue
		sessionId = forceInt(sessionData['Session'])
		if (sessionId == 0) and (sys.getwindowsversion()[0] >= 6):
			# Service session
			continue
		
		logger.debug(u"   Found session: %s" % sessionData)
		
		if verifyProcessRunning and not getPids(verifyProcessRunning, sessionId = sessionId):
			continue
		
		if not sessionId in sessionIds:
			sessionIds.append(sessionId)
		if newest:
			if (forceInt(sessionData['LogonId']) > forceInt(newest['LogonId'])):
				newest = sessionData
		else:
			newest = sessionData
	if (len(sessionIds) == 0):
		return defaultSessionId
	if newest:
		return forceInt(newest['Session'])
	if defaultSessionId in sessionIds:
		return defaultSessionId
	if (sys.getwindowsversion()[0]>= 6) and (sessionIds[0] == 0):
		if (len(sessionIds) > 1):
			return sessionIds[1]
		return defaultSessionId
	return sessionIds[0]
	
def getSessionInformation(sessionId):
	#info = {}
	#for infoClass in ('WTSUserName', 'WTSApplicationName', 'WTSClientDirectory', 'WTSClientName', 'WTSDomainName', 'WTSInitialProgram',
	#                  'WTSOEMId', 'WTSUserName', 'WTSWinStationName', 'WTSWorkingDirectory', 'WTSClientProtocolType', 'WTSClientProductId',
	#                  'WTSClientBuildNumber', 'WTSClientHardwareId', 'WTSSessionId', 'WTSConnectState', 'WTSClientDisplay', 'WTSClientAddress'):
	#	try:
	#		info[infoClass] = win32ts.WTSQuerySessionInformation(None, sessionId, eval('win32ts.%s' % infoClass))
	#	except Exception, e:
	#		info[infoClass] = None
	#		logger.debug(e)
	#return info
	"""
	'UserName': u'Administrator',
	'AuthenticationPackage': u'NTLM',
	'LogonServer': u'COMPUTERNAME',
	'LogonId': 1753269L,
	'Upn': u'',
	'Session': 1,
	'DnsDomainName': u'',
	'Sid': <PySID object at 0x00CD7BA8>,
	'LogonType': 10,
	'LogonDomain': u'COMPUTERNAME',
	'LogonTime': <PyTime:19.04.2010 16:33:07>}
	"""
	for s in win32security.LsaEnumerateLogonSessions():
		sessionData = win32security.LsaGetLogonSessionData(s)
		if (forceInt(sessionData['Session']) == sessionId):
			return sessionData
	return {}

def getActiveSessionInformation():
	info = []
	for sessionId in getActiveSessionIds():
		info.append(getSessionInformation(sessionId))
	return info

def getUserSessionIds(username):
	sessionIds = []
	if not username:
		return sessionIds
	domain = None
	logger.debug(u"Getting sessions of user '%s'" % username)
	if (username.find('\\') != -1):
		domain = username.split('\\')[0]
		username = username.split('\\')[-1]
	for session in getActiveSessionInformation():
		#if ( session.get('WTSUserName') and (session.get('WTSUserName').lower() == username.lower()) and \
		#     (not domain or (session.get('WTSDomainName') and (session.get('WTSDomainName').lower() == domain.lower()))) ):
		#	sessionIds.append(session.get('WTSSessionId'))
		#	logger.debug(u"   Found session id of user '%s': %s" % (username, session.get('WTSSessionId')))
		if ( session.get('UserName') and (session.get('UserName').lower() == username.lower()) and \
		     (not domain or (session.get('LogonDomain') and (session.get('LogonDomain').lower() == domain.lower()))) ):
			sessionIds.append(forceInt(session.get('Session')))
			logger.debug(u"   Found session id of user '%s': %s" % (username, session.get('Session')))
	return sessionIds
	
def logoffCurrentUser():
	logger.notice("Logging off current user")
	#win32api.ExitWindows()
	#win32api.ExitWindowsEx(0)
	## Windows Server 2008 and Windows Vista:  A call to WTSShutdownSystem does not work when Remote Connection Manager (RCM) is disabled. This is the case when the Terminal Services service is stopped.
	#win32ts.WTSShutdownSystem(win32ts.WTS_CURRENT_SERVER_HANDLE, win32ts.WTS_WSD_LOGOFF)
	command = ''
	if (sys.getwindowsversion()[0] == 5):
		if (sys.getwindowsversion()[1] == 0):
			# NT5.0: win2k
			raise NotImplemented(u"Not available on win2k")
		else:
			# NT5.1: XP
			command = u'logoff.exe'
	elif (sys.getwindowsversion()[0] == 6):
		# NT6: Vista, Win7
		command = u'shutdown.exe /l'
	else:
		raise Exception(u"Operating system not supported")
	runCommandInSession(
			command              = command,
			sessionId            = getActiveSessionId(),
			waitForProcessEnding = False )
	
def lockWorkstation():
	#windll.winsta.WinStationConnectW(0, 0, sessionId, "", 0)
	#windll.user32.LockWorkStation()
	runCommandInSession(
			command              = u"rundll32.exe user32.dll,LockWorkStation",
			sessionId            = getActiveSessionId(),
			waitForProcessEnding = False )

def reboot(wait=10):
	logger.notice(u"Rebooting in %s seconds" % wait)
	wait = forceInt(wait)
	adjustPrivilege(ntsecuritycon.SE_SHUTDOWN_NAME)
	win32api.InitiateSystemShutdown(None, u"Opsi reboot", wait, True, True)
	
def shutdown(wait=10):
	logger.notice(u"Shutting down in %s seconds" % wait)
	wait = forceInt(wait)
	adjustPrivilege(ntsecuritycon.SE_SHUTDOWN_NAME)
	win32api.InitiateSystemShutdown(None, u"Opsi shutdown", wait, True, False)

def abortShutdown():
	logger.notice(u"Aborting system shutdown")
	adjustPrivilege(ntsecuritycon.SE_SHUTDOWN_NAME)
	win32api.AbortSystemShutdown(None)

#def blockShutdown():
#	logger.notice(u"Blocking system shutdown")
#	adjustPrivilege(ntsecuritycon.SE_SHUTDOWN_NAME)
#	win32api.ShutdownBlockReasonCreate()
#
#def unblockShutdown():
#	logger.notice(u"Unblocking system shutdown")
#	adjustPrivilege(ntsecuritycon.SE_SHUTDOWN_NAME)
#	win32api.ShutdownBlockReasonDestroy()

def createWindowStation(name):
	name = forceUnicode(name)
	sa = pywintypes.SECURITY_ATTRIBUTES()
	sa.bInheritHandle = 1
	sa.SECURITY_DESCRIPTOR = None
	
	try:
		return win32service.CreateWindowStation(name, 0, win32con.MAXIMUM_ALLOWED, sa)
	except win32service.error, e:
		logger.error(u"Failed to create window station '%s': %s" % (name, forceUnicode(e)))

def createDesktop(name, cmd):
	name = forceUnicode(name)
	cmd = forceUnicode(cmd)
	sa = pywintypes.SECURITY_ATTRIBUTES()
	sa.bInheritHandle = 1
	sa.SECURITY_DESCRIPTOR = None
	
	try:
		hdesk = win32service.CreateDesktop(name, 0, win32con.MAXIMUM_ALLOWED, sa)
	except win32service.error, e:
		logger.error(u"Failed to create desktop '%s': %s" % (name, forceUnicode(e)))
	
	s = win32process.STARTUPINFO()
	s.lpDesktop = name
	prc_info = win32process.CreateProcess(None, cmd, None, None, True, win32con.CREATE_NEW_CONSOLE, None, 'c:\\', s)
	return hdesk

def addUserToDesktop(desktop, userSid):
	'''
	Adds the given PySID representing a user to the given desktop's
	discretionary access-control list. The old security descriptor for
	desktop is returned.
	'''
	
	desktopAll  = 	win32con.DESKTOP_CREATEMENU      | \
			win32con.DESKTOP_CREATEWINDOW    | \
			win32con.DESKTOP_ENUMERATE       | \
			win32con.DESKTOP_HOOKCONTROL     | \
			win32con.DESKTOP_JOURNALPLAYBACK | \
			win32con.DESKTOP_JOURNALRECORD   | \
			win32con.DESKTOP_READOBJECTS     | \
			win32con.DESKTOP_SWITCHDESKTOP   | \
			win32con.DESKTOP_WRITEOBJECTS    | \
			win32con.DELETE                  | \
			win32con.READ_CONTROL            | \
			win32con.WRITE_DAC               | \
			win32con.WRITE_OWNER
	
	securityDesc = win32security.GetUserObjectSecurity(desktop, win32con.DACL_SECURITY_INFORMATION)

	# Get discretionary access-control list (DACL) for desktop.
	acl = securityDesc.GetSecurityDescriptorDacl()
	
	# Create a new access control list for desktop.
	newAcl = win32security.ACL()
	
	if acl:
		copyACL(acl, newAcl)

	# Add the ACE for user_sid to the desktop.
	ace0Index = newAcl.GetAceCount()
	newAcl.AddAccessAllowedAce(win32con.ACL_REVISION, desktopAll, userSid)
	
	# Create a new security descriptor and set its new DACL.
	newSecurityDesc = win32security.SECURITY_DESCRIPTOR()
	newSecurityDesc.SetSecurityDescriptorDacl(True, newAcl, False)
	
	# Set the new security descriptor for desktop.
	win32security.SetUserObjectSecurity(desktop,
			win32con.DACL_SECURITY_INFORMATION,
			newSecurityDesc)
	
	return [ ace0Index ]


def addUserToWindowStation(winsta, userSid):
	'''
	Adds the given PySID representing a user to the given window station's
	discretionary access-control list. The old security descriptor for
	winsta is returned.
	'''
	
	winstaAll  =	win32con.WINSTA_ACCESSCLIPBOARD   | \
			win32con.WINSTA_ACCESSGLOBALATOMS | \
			win32con.WINSTA_CREATEDESKTOP     | \
			win32con.WINSTA_ENUMDESKTOPS      | \
			win32con.WINSTA_ENUMERATE         | \
			win32con.WINSTA_EXITWINDOWS       | \
			win32con.WINSTA_READATTRIBUTES    | \
			win32con.WINSTA_READSCREEN        | \
			win32con.WINSTA_WRITEATTRIBUTES   | \
			win32con.DELETE                   | \
			win32con.READ_CONTROL             | \
			win32con.WRITE_DAC                | \
			win32con.WRITE_OWNER
	
	genericAccess = win32con.GENERIC_READ    | \
			win32con.GENERIC_WRITE   | \
			win32con.GENERIC_EXECUTE | \
			win32con.GENERIC_ALL
	
	# Get the security description for winsta.
	securityDesc = win32security.GetUserObjectSecurity(
						winsta,
						win32con.DACL_SECURITY_INFORMATION)
	
	# Get discretionary access-control list (DACL) for winsta.
	acl = securityDesc.GetSecurityDescriptorDacl()
	
	# Create a new access control list for winsta.
	newAcl = win32security.ACL()
	
	if acl:
		copyACL(acl, newAcl)
	
	# Add the first ACE for userSid to the window station.
	ace0Index = newAcl.GetAceCount()
	aceFlags   = 	win32con.CONTAINER_INHERIT_ACE | \
			win32con.INHERIT_ONLY_ACE      | \
			win32con.OBJECT_INHERIT_ACE
	newAcl.AddAccessAllowedAceEx(win32con.ACL_REVISION, aceFlags, genericAccess, userSid)
	
	# Add the second ACE for userSid to the window station.
	ace1Index = newAcl.GetAceCount()
	aceFlags = win32con.NO_PROPAGATE_INHERIT_ACE
	newAcl.AddAccessAllowedAceEx(win32con.ACL_REVISION, aceFlags, winstaAll, userSid)
	
	# Create a new security descriptor and set its new DACL.
	# NOTE: Simply creating a new security descriptor and assigning it as
	# the security descriptor for winsta (without setting the DACL) is
	# sufficient to allow windows to be opened, but that is probably not
	# providing any kind of security on winsta.
	newSecurityDesc = win32security.SECURITY_DESCRIPTOR()
	newSecurityDesc.SetSecurityDescriptorDacl(True, newAcl, False)
	
	# Set the new security descriptor for winsta.
	win32security.SetUserObjectSecurity(	winsta,
						win32con.DACL_SECURITY_INFORMATION,
						newSecurityDesc)
	
	return [ ace0Index, ace1Index ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                        PROCESS HANDLING                                           -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def which(cmd):
	raise NotImplementedError(u"which() not implemented on windows")

def execute(cmd, waitForEnding=True, getHandle=False, ignoreExitCode=[], exitOnStderr=False, captureStderr=True, encoding=None, timeout=0):
	cmd             = forceUnicode(cmd)
	waitForEnding   = forceBool(waitForEnding)
	getHandle       = forceBool(getHandle)
	exitOnStderr    = forceBool(exitOnStderr)
	captureStderr   = forceBool(captureStderr)
	timeout         = forceInt(timeout)
	
	exitCode = 0
	result = []
	
	startTime = time.time()
	try:
		logger.info(u"Executing: %s" % cmd)
		if getHandle:
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
				encoding = proc.stdout.encoding
				logger.debug(u"proc.stdout.encoding: %s" % encoding)
				if (encoding == 'ascii'): encoding = None
			if not encoding:
				encoding = locale.getpreferredencoding()
				logger.debug(u"locale.getpreferredencoding(): %s" % encoding)
				if (encoding == 'ascii'): encoding = None
			if not encoding:
				encoding = sys.stdout.encoding
				logger.debug(u"sys.stdout.encoding: %s" % encoding)
				if (encoding == 'ascii'): encoding = None
			if not encoding:
				encoding = 'cp850'
			
			logger.info(u"Using encoding '%s'" % encoding)
			
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
								raise IOError(exitCode, u"Command '%s' failed: %s" % (cmd, chunk) )
							data += chunk
					except IOError, e:
						if (e.errno != 11):
							raise
				
				if (timeout > 0) and (time.time() - startTime >= timeout):
					try:
						proc.kill()
					except:
						pass
					raise IOError(exitCode, u"Command '%s' timed out atfer %d seconds" % (cmd, (time.time() - startTime)) )
				
				time.sleep(0.001)
			
			exitCode = ret
			if data:
				lines = data.split('\n')
				for i in range(len(lines)):
					line = lines[i].decode(encoding, 'replace').replace('\r', '')
					if (i == len(lines) - 1) and not line:
						break
					logger.debug(u'>>> %s' % line)
					result.append(line)
		
	except (os.error, IOError), e:
		# Some error occured during execution
		raise IOError(e.errno, u"Command '%s' failed:\n%s" % (cmd, e) )
	
	logger.debug(u"Exit code: %s" % exitCode)
	if exitCode:
		if   type(ignoreExitCode) is bool and ignoreExitCode:
			pass
		elif type(ignoreExitCode) is list and exitCode in ignoreExitCode:
			pass
		else:
			raise IOError(exitCode, u"Command '%s' failed (%s):\n%s" % (cmd, exitCode, u'\n'.join(result)))
	return result
		
	
def getPids(process, sessionId = None):
	process = forceUnicode(process)
	if not sessionId is None:
		sessionId = forceInt(sessionId)
	
	logger.info(u"Searching pids of process name %s (session id: %s)" % (process, sessionId))
	processIds = []
	CreateToolhelp32Snapshot = windll.kernel32.CreateToolhelp32Snapshot
	Process32First = windll.kernel32.Process32First
	Process32Next = windll.kernel32.Process32Next
	CloseHandle = windll.kernel32.CloseHandle
	hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
	pe32 = PROCESSENTRY32()
	pe32.dwSize = sizeof(PROCESSENTRY32)
	logger.debug2(u"Getting first process")
	if ( Process32First(hProcessSnap, byref(pe32)) == win32con.FALSE ):
		logger.error(u"Failed to get first process")
		return
	while True:
		pid = pe32.th32ProcessID
		sid = u'unknown'
		try:
			sid = win32ts.ProcessIdToSessionId(pid)
		except:
			pass
		logger.debug2(u"   got process %s with pid %d in session %s" % (pe32.szExeFile, pid, sid))
		if (pe32.szExeFile.lower() == process.lower()):
			logger.info(u"Found process %s with matching name (pid %d, session %s)" % (pe32.szExeFile.lower(), pid, sid))
			if sessionId is None or (sid == sessionId):
				processIds.append(forceInt(pid))
		if Process32Next(hProcessSnap, byref(pe32)) == win32con.FALSE:
			break
	CloseHandle(hProcessSnap)
	if not processIds:
		logger.debug(u"No process with name %s found (session id: %s)" % (process, sessionId))
	return processIds

def getPid(process, sessionId = None):
	process = forceUnicode(process)
	if not sessionId is None:
		sessionId = forceInt(sessionId)
	
	processId = 0
	processIds = getPids(process, sessionId)
	if processIds:
		processId = processIds[0]
	return processId

def getProcessName(processId):
	processId = forceInt(processId)
	
	logger.notice(u"Searching name of process %d" % processId)
	processName = u''
	CreateToolhelp32Snapshot = windll.kernel32.CreateToolhelp32Snapshot
	Process32First = windll.kernel32.Process32First
	Process32Next = windll.kernel32.Process32Next
	CloseHandle = windll.kernel32.CloseHandle
	hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
	pe32 = PROCESSENTRY32()
	pe32.dwSize = sizeof(PROCESSENTRY32)
	logger.info(u"Getting first process")
	if ( Process32First(hProcessSnap, byref(pe32)) == win32con.FALSE ):
		logger.error(u"Failed getting first process")
		return
	while True:
		#logger.info("Got process %s" % pe32.szExeFile)
		#sid = win32ts.ProcessIdToSessionId(pe32.th32ProcessID)
		pid = pe32.th32ProcessID
		#logger.notice("Found process %s with pid %d in session %d" % (process, pid, sid))
		#logger.notice("Found process %s with pid %d" % (pe32.szExeFile, pid))
		if (pid == processId):
			processName = forceUnicode(pe32.szExeFile)
			break
		if Process32Next(hProcessSnap, byref(pe32)) == win32con.FALSE:
			break
	CloseHandle(hProcessSnap)
	return processName

def getProcessHandle(processId):
	processId = forceInt(processId)
	processHandle = win32api.OpenProcess(1, 0, processId)
	return processHandle

def getProcessWindowHandles(processId):
	processId = forceInt(processId)
	logger.info(u"Getting window handles of process with id %s" % processId)
	def callback (windowHandle, windowHandles):
		#if win32gui.IsWindowVisible(windowHandle) and win32gui.IsWindowEnabled(windowHandle):
		if (win32process.GetWindowThreadProcessId(windowHandle)[1] == processId):
			logger.debug(u"Found window %s of process with id %s" % (windowHandle, processId))
			windowHandles.append(windowHandle)
		return True
	windowHandles = []
	win32gui.EnumWindows(callback, windowHandles)
	return windowHandles

def closeProcessWindows(processId):
	processId = forceInt(processId)
	logger.info("Closing windows of process with id %s" % processId)
	for windowHandle in getProcessWindowHandles(processId):
		logger.debug("Sending WM_CLOSE message to window %s" % windowHandle)
		win32gui.SendMessage(windowHandle, win32con.WM_CLOSE, 0, 0)

def terminateProcess(processHandle=None, processId=None):
	if not processId is None:
		processId = forceInt(processId)
	
	if not processHandle and not processId:
		raise ValueError(u"Neither process handle not process id given")
	exitCode = 0
	if not processHandle:
		processHandle = getProcessHandle(processId)
	win32process.TerminateProcess(processHandle, exitCode)
	return exitCode

def getUserToken(sessionId = None, duplicateFrom = u"winlogon.exe"):
	if not sessionId is None:
		sessionId = forceInt(sessionId)
	duplicateFrom = forceUnicode(duplicateFrom)
	
	if sessionId is None or (sessionId < 0):
		sessionId = getActiveSessionId()
	
	pid = getPid(process = duplicateFrom, sessionId = sessionId)
	if not pid:
		raise Exception(u"Failed to get user token, pid of '%s' not found in session '%s'" % (duplicateFrom, sessionId))
	hProcess = win32api.OpenProcess(win32con.MAXIMUM_ALLOWED, False, pid)
	hPToken = win32security.OpenProcessToken(
				hProcess,
				win32con.TOKEN_ADJUST_PRIVILEGES|win32con.TOKEN_QUERY|\
				win32con.TOKEN_DUPLICATE|win32con.TOKEN_ASSIGN_PRIMARY|\
				win32con.TOKEN_READ|win32con.TOKEN_WRITE) # win32con.TOKEN_ADJUST_SESSIONID
	
	id = win32security.LookupPrivilegeValue(None, win32security.SE_DEBUG_NAME)
	
	newPrivileges = [(id, win32security.SE_PRIVILEGE_ENABLED)]
	
	hUserTokenDup = win32security.DuplicateTokenEx(
		ExistingToken = hPToken,
		DesiredAccess = win32con.MAXIMUM_ALLOWED,
		ImpersonationLevel = win32security.SecurityIdentification,
		TokenType = ntsecuritycon.TokenPrimary,
		TokenAttributes = None )
	
	# Adjust Token privilege
	
	win32security.SetTokenInformation(hUserTokenDup, ntsecuritycon.TokenSessionId, sessionId)
	
	win32security.AdjustTokenPrivileges(hUserTokenDup, 0, newPrivileges)
	
	return hUserTokenDup
	
def runCommandInSession(command, sessionId = None, desktop = u"default", duplicateFrom = u"winlogon.exe", waitForProcessEnding=True, timeoutSeconds=0):
	command = forceUnicode(command)
	if not sessionId is None:
		sessionId = forceInt(sessionId)
	desktop = forceUnicode(desktop)
	if (desktop.find(u'\\') == -1):
		desktop = u'winsta0\\' + desktop
	duplicateFrom = forceUnicode(duplicateFrom)
	waitForProcessEnding = forceBool(waitForProcessEnding)
	timeoutSeconds = forceInt(timeoutSeconds)
	
	logger.debug(u"Session id given: %s" % sessionId)
	if sessionId is None or (sessionId < 0):
		logger.debug(u"No session id given, running in active session")
		sessionId = getActiveSessionId()
	
	userToken = getUserToken(sessionId, duplicateFrom)
	
	dwCreationFlags = win32con.NORMAL_PRIORITY_CLASS#|win32con.CREATE_NEW_CONSOLE
	
	s = win32process.STARTUPINFO()
	s.lpDesktop = desktop
	#s.wShowWindow = win32con.SW_MAXIMIZE
	#s.dwFlags = win32process.STARTF_USESTDHANDLES
	
	logger.notice(u"Executing: '%s' in session '%s' on desktop '%s'" % (command, sessionId, desktop))
	(hProcess, hThread, dwProcessId, dwThreadId) = win32process.CreateProcessAsUser(userToken, None, command, None, None, 1, dwCreationFlags, None, None, s)
	
	logger.info(u"Process startet, pid: %d" % dwProcessId)
	if not waitForProcessEnding:
		return (hProcess, hThread, dwProcessId, dwThreadId)
	logger.info(u"Waiting for process ending: %d (timeout: %d seconds)" % (dwProcessId, timeoutSeconds))
	t = 0.0
	while win32event.WaitForSingleObject(hProcess, timeoutSeconds):
		if (timeoutSeconds > 0):
			if (t >= timeoutSeconds):
				terminateProcess(processId = dwProcessId)
				raise Exception(u"Timed out after %s seconds while waiting for process %d" % (t, dwProcessId))
			t += 0.1
		time.sleep(0.1)
	exitCode = win32process.GetExitCodeProcess(hProcess)
	logger.notice(u"Process %d ended with exit code %d" % (dwProcessId, exitCode))
	return (None, None, None, None)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                     USER / GROUP HANDLING                                         -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def createUser(username, password, groups = []):
	username = forceUnicode(username)
	password = forceUnicode(password)
	groups = forceUnicodeList(groups)
	logger.addConfidentialString(password)
	
	domain = getHostname().upper()
	if (username.find(u'\\') != -1):
		domain = username.split(u'\\')[0]
		username = username.split(u'\\')[-1]
	domain = domain.upper()
	if (domain != getHostname().upper()):
		raise ValueError(u"Can only handle domain %s" % getHostname().upper())
	
	userData = {
		'name':             username,
		'full_name':        u"",
		'password':         password,
		'flags':            win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UF_SCRIPT,
		'priv':             win32netcon.USER_PRIV_USER,
		'home_dir':         None,
		'home_dir_drive':   None,
		'primary_group_id': ntsecuritycon.DOMAIN_GROUP_RID_USERS,
		'password_expired': 0
	}
	
	#win32net.NetUserAdd(domain, 3, userData)
	win32net.NetUserAdd(u"\\\\" + domain, 1, userData)
	if not groups:
		return
	u = { 'domainandname': domain + u'\\' + username }
	for group in groups:
		logger.info(u"Adding user '%s' to group '%s'" % (username, group))
		win32net.NetLocalGroupAddMembers(u"\\\\" + domain, group, 3, [ u ])
		
	
def deleteUser(username):
	username = forceUnicode(username)
	domain = getHostname()
	if (username.find(u'\\') != -1):
		domain = username.split(u'\\')[0]
		username = username.split(u'\\')[-1]
	domain = domain.upper()
	if (domain != getHostname().upper()):
		raise ValueError(u"Can only handle domain %s" % getHostname().upper())
	
	try:
		win32net.NetUserDel(u"\\\\" + domain, username)
	except win32net.error:
		pass

def existsUser(username):
	username = forceUnicode(username)
	domain = getHostname()
	if (username.find(u'\\') != -1):
		domain = username.split(u'\\')[0]
		username = username.split(u'\\')[-1]
	domain = domain.upper()
	if (domain != getHostname().upper()):
		raise ValueError(u"Can only handle domain %s" % getHostname().upper())
	
	for user in win32net.NetUserEnum(u"\\\\" + domain, 0)[0]:
		if (user.get('name').lower() == username.lower()):
			return True
	return False

def getUserSidFromHandle(userHandle):
	tic = win32security.GetTokenInformation(userHandle, ntsecuritycon.TokenGroups)
	for (sid, flags) in tic:
		if (flags & win32con.SE_GROUP_LOGON_ID):
			return sid

def getUserSid(username):
	username = forceUnicode(username)
	domain = getHostname()
	if (username.find(u'\\') != -1):
		domain = username.split(u'\\')[0]
		username = username.split(u'\\')[-1]
	domain = domain.upper()
	return win32security.ConvertSidToStringSid(win32security.LookupAccountName(None, domain + u'\\' + username)[0])

def getAdminGroupName():
	subAuths = ntsecuritycon.SECURITY_BUILTIN_DOMAIN_RID, ntsecuritycon.DOMAIN_ALIAS_RID_ADMINS
	sidAdmins = win32security.SID(ntsecuritycon.SECURITY_NT_AUTHORITY, subAuths)
	groupName = forceUnicode(win32security.LookupAccountSid(None, sidAdmins)[0])
	logger.info(u"Admin group name is '%s'" % groupName)
	return groupName

class Impersonate:
	def __init__(self, username=u"", password=u"", userToken = None, desktop = u"default"):
		if not username and not userToken:
			raise Exception(u"Neither username nor user token given")
		#if username and not existsUser(username):
		#	raise Exception("User '%s' does not exist" % username)
		self.domain = getHostname()
		self.username = forceUnicode(username)
		if (self.username.find('\\') != -1):
			self.domain = self.username.split('\\')[0]
			self.username = self.username.split('\\')[-1]
		self.domain = self.domain.upper()
		self.password = forceUnicode(password)
		if not desktop:
			desktop = u"default"
		if (desktop.find(u'\\') == -1):
			desktop = u'winsta0\\' + desktop
		(self.winsta, self.desktop) = desktop.split('\\', 1)
		self.winsta = forceUnicode(self.winsta)
		self.desktop = forceUnicode(self.desktop)
		self.userToken = userToken
		self.saveWindowStation = None
		self.saveDesktop = None
		self.newWindowStation = None
		self.newDesktop = None
		
	def start(self, logonType=u'INTERACTIVE', newDesktop=False):
		try:
			logonType = forceUnicode(logonType)
			newDesktop = forceBool(newDesktop)
			if (logonType == u'NEW_CREDENTIALS'):
				# Stay who you are but add credentials for network connections
				logonType = win32security.LOGON32_LOGON_NEW_CREDENTIALS
			elif (logonType == u'INTERACTIVE'):
				logonType = win32con.LOGON32_LOGON_INTERACTIVE
			else:
				raise ValueError(u"Unhandled logon type '%s'" % logonType)
			
			if not self.userToken:
				# TODO: Use (UPN) format for username <USER>@<DOMAIN> ?
				logger.debug(u"Logon user: '%s\\%s'" % (self.domain, self.username))
				self.userToken = win32security.LogonUser(
							self.username,
							self.domain,
							self.password,
							logonType,
							win32con.LOGON32_PROVIDER_DEFAULT)
			
			if newDesktop:
				self.saveWindowStation = win32service.GetProcessWindowStation()
				logger.debug(u"Got current window station")
				
				self.saveDesktop = win32service.GetThreadDesktop(win32api.GetCurrentThreadId())
				logger.debug(u"Got current desktop")
				
				self.newWindowStation = win32service.OpenWindowStation(
								self.winsta,
								False,
								win32con.READ_CONTROL |
								win32con.WRITE_DAC)
				
				self.newWindowStation.SetProcessWindowStation()
				logger.debug(u"Process window station set")
					
				self.newDesktop = win32service.OpenDesktop(
								self.desktop,
								win32con.DF_ALLOWOTHERACCOUNTHOOK, #0,
								False,
								win32con.READ_CONTROL |
								win32con.WRITE_DAC |
								win32con.DESKTOP_READOBJECTS |
								win32con.DESKTOP_WRITEOBJECTS)
				self.newDesktop.SetThreadDesktop()
				logger.debug(u"Thread desktop set")
				
				userSid = getUserSidFromHandle(self.userToken)
				if not userSid:
					logger.warning(u"Failed to determine sid of user '%s'" % self.username)
				else:
					logger.debug(u"Got sid of user '%s'" % self.username)
					
					winstaAceIndices = addUserToWindowStation(self.newWindowStation, userSid)
					logger.debug(u"Added user to window station")
						
					desktopAceIndices = addUserToDesktop(self.newDesktop, userSid)
					logger.debug(u"Added user to desktop")
			
			win32security.ImpersonateLoggedOnUser(self.userToken)
			logger.debug(u"User impersonated")
		except Exception, e:
			logger.logException(e)
			self.end()
			raise
	
	def runCommand(self, command, waitForProcessEnding=True, timeoutSeconds=0):
		command = forceUnicode(command)
		waitForProcessEnding = forceBool(waitForProcessEnding)
		timeoutSeconds = forceInt(timeoutSeconds)
		
		dwCreationFlags = win32process.CREATE_NEW_CONSOLE
		
		s = win32process.STARTUPINFO()
		s.dwFlags = win32process.STARTF_USESHOWWINDOW ^ win32con.STARTF_USESTDHANDLES
		s.wShowWindow = win32con.SW_NORMAL
		s.lpDesktop = self.winsta + u'\\' + self.desktop
		
		logger.notice(u"Running command '%s' as user '%s' on desktop '%s'" % (command, self.username, self.desktop))
		
		(hProcess, hThread, dwProcessId, dwThreadId) = win32process.CreateProcessAsUser(
					self.userToken, None, command, None, None, 0, dwCreationFlags, None, None, s)
		logger.info(u"Process startet, pid: %d" % dwProcessId)
		if not waitForProcessEnding:
			return (hProcess, hThread, dwProcessId, dwThreadId)
		logger.info(u"Waiting for process ending: %d (timeout: %d seconds)" % (dwProcessId, timeoutSeconds))
		t = 0.0
		while win32event.WaitForSingleObject(hProcess, timeoutSeconds):
			if (timeoutSeconds > 0):
				if (t >= timeoutSeconds):
					terminateProcess(processId = dwProcessId)
					raise Exception(u"Timed out after %s seconds while waiting for process %d" % (t, dwProcessId))
				t += 0.1
			time.sleep(0.1)
		exitCode = win32process.GetExitCodeProcess(hProcess)
		logger.notice(u"Process %d ended with exit code %d" % (dwProcessId, exitCode))
		return (None, None, None, None)
		
	def end(self):
		if self.userToken: self.userToken.Close()
		win32security.RevertToSelf()
		if self.saveWindowStation: self.saveWindowStation.SetProcessWindowStation()
		if self.saveDesktop:       self.saveDesktop.SetThreadDesktop()
		if self.newWindowStation:  self.newWindowStation.CloseWindowStation()
		if self.newDesktop:        self.newDesktop.CloseDesktop()
	
	def __del__(self):
		self.end()



























