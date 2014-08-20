#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Service   =
   = = = = = = = = = = = = = = = = = = =
   
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

import threading

from OPSI.Types import *
from OPSI.Logger import *
from OPSI.Util import randomString

logger = Logger()

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =                                         CLASS SESSION                                             =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class Session:
	def __init__(self, sessionHandler, name = u'OPSISID', sessionMaxInactiveInterval = 120):
		self.sessionHandler = sessionHandler
		self.name = forceUnicode(name)
		self.sessionMaxInactiveInterval = forceInt(sessionMaxInactiveInterval)
		self.created = time.time()
		self.lastModified = time.time()
		self.sessionTimer = None
		self.uid = randomString(32)
		self.ip = u''
		self.userAgent = u''
		self.hostname = u''
		self.user = u''
		self.password = u''
		self.authenticated = False
		self.postpath = []
		self.usageCount = 0
		self.usageCountLock = threading.Lock()
		self.markedForDeletion = False
		self.deleted = False
		self.touch()
		
	def decreaseUsageCount(self):
		if self.deleted:
			return
		self.usageCountLock.acquire()
		self.usageCount -= 1
		self.usageCountLock.release()
		
	def increaseUsageCount(self):
		if self.deleted:
			return
		self.usageCountLock.acquire()
		self.usageCount += 1
		self.touch()
		self.usageCountLock.release()
	
	def touch(self):
		if self.deleted:
			return
		self.lastModified = time.time()
		if self.sessionTimer:
			self.sessionTimer.cancel()
			self.sessionTimer.join(1)
		self.sessionTimer = threading.Timer(self.sessionMaxInactiveInterval, self.expire)
		self.sessionTimer.start()
	
	def setMarkedForDeletion(self):
		self.markedForDeletion = True
	
	def getMarkedForDeletion(self):
		return self.markedForDeletion
	
	def getValidity(self):
		if self.deleted:
			return 0
		return int(self.lastModified - time.time() + self.sessionMaxInactiveInterval)
	
	def expire(self):
		self.sessionHandler.sessionExpired(self)
	
	def delete(self):
		if self.deleted:
			return
		self.deleted = True
		if (self.usageCount > 0):
			logger.warning(u"Deleting session in use: %s" % self)
		if self.sessionTimer:
			try:
				self.sessionTimer.cancel()
				try:
					self.sessionTimer.join(1)
				except:
					pass
				logger.info(u"Session timer %s canceled" % self.sessionTimer)
			except Exception, e:
				logger.error(u"Failed to cancel session timer: %s" % e)
	
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =                                    CLASS SESSION HANDLER                                          =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class SessionHandler:
	def __init__(self, sessionName = u'OPSISID', sessionMaxInactiveInterval = 120, maxSessionsPerIp = 0, sessionDeletionTimeout = 60):
		self.sessionName = forceUnicode(sessionName)
		self.sessionMaxInactiveInterval = forceInt(sessionMaxInactiveInterval)
		self.maxSessionsPerIp = forceInt(maxSessionsPerIp)
		self.sessionDeletionTimeout = forceInt(sessionDeletionTimeout)
		self.sessions = {}
	
	def cleanup(self):
		self.deleteAllSessions()
	
	def getSessions(self, ip=None):
		if not ip:
			return self.sessions
		sessions = []
		for session in self.sessions.values():
			if (session.ip == ip):
				sessions.append(session)
		return sessions
		
	def getSession(self, uid=None, ip=None):
		if uid:
			session = self.sessions.get(uid)
			if session:
				if session.getMarkedForDeletion():
					logger.info(u'Session found but marked for deletion')
				else:
					# Set last modified to current time
					session.increaseUsageCount()
					logger.confidential(u"Returning session: %s (count: %d)" % (session.uid, session.usageCount))
					return session
			else:
				logger.info(u'Failed to get session: session id %s not found' % uid)
		if ip and (self.maxSessionsPerIp > 0):
			sessions = self.getSessions(ip)
			if (len(sessions) >= self.maxSessionsPerIp):
				logger.error(u"Session limit for ip '%s' reached" % ip)
				for session in sessions:
					if (session.usageCount > 0):
						continue
					logger.info(u"Deleting unused session")
					self.deleteSession(session.uid)
				if (len(self.getSessions(ip)) >= self.maxSessionsPerIp):
					raise OpsiAuthenticationError(u"Session limit for ip '%s' reached" % ip)
		
		session = self.createSession()
		session.increaseUsageCount()
		return session
		
	def createSession(self):
		session = Session(self, self.sessionName, self.sessionMaxInactiveInterval)
		self.sessions[session.uid] = session
		logger.notice(u"New session created")
		return session
	
	def sessionExpired(self, session):
		logger.notice(u"Session '%s' from ip '%s', application '%s' expired after %d seconds" \
				% (session.uid, session.ip, session.userAgent, (time.time()-session.lastModified)))
		if (session.usageCount > 0):
			logger.notice(u"Session currently in use, waiting before deletion")
		session.setMarkedForDeletion()
		timeout = self.sessionDeletionTimeout
		while (session.usageCount > 0) and (timeout > 0):
			if not self.sessions.get(session.uid):
				# Session deleted (closed by client)
				return False
			time.sleep(1)
			timeout -= 1
		if (timeout == 0):
			logger.warning(u"Session '%s': timeout occured while waiting for session to get free for deletion" % session.uid)
		self.deleteSession(session.uid)
		return True
		
	def deleteSession(self, uid):
		session = self.sessions.get(uid)
		if not session:
			logger.warning(u'No such session id: %s' % uid)
			return
		try:
			session.delete()
		except:
			pass
		try:
			del self.sessions[uid]
			logger.notice(u"Session '%s' from ip '%s', application '%s' deleted" % (session.uid, session.ip, session.userAgent))
			del session
		except KeyError:
			pass
	
	def deleteAllSessions(self):
		logger.notice(u"Deleting all sessions")
		class SessionDeletionThread(threading.Thread):
			def __init__(self, sessionHandler, uid):
				threading.Thread.__init__(self)
				self._sessionHandler = sessionHandler
				self._uid = uid
			
			def run(self):
				self._sessionHandler.deleteSession(self._uid)
		
		dts = []
		for (uid, session) in self.sessions.items():
			logger.debug(u"Deleting session '%s'" % uid)
			dts.append(SessionDeletionThread(self, uid))
			dts[-1].start()
		for dt in dts:
			dt.join(2)
		self.sessions = {}
	

