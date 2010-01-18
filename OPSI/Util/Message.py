#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Message   =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
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

__version__ = '3.5'

# Imports
import threading
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory, ClientFactory
from twisted.internet import reactor

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get Logger instance
logger = Logger()

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Subjects                                                                    =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class Subject(object):
	def __init__(self, id, type=u'', title=u'', **args):
		self._id    = forceUnicode(id)
		self._type  = forceUnicode(type)
		self._title = forceUnicode(title)
		self._observers = []
	
	def reset(self):
		pass
	
	def getClass(self):
		return self.__class__.__name__
	
	def getId(self):
		return self._id
	
	def getType(self):
		return self._type
	
	def getTitle(self):
		return self._title
	
	def attachObserver(self, observer):
		if not observer in self._observers:
			self._observers.append(observer)
	
	def detachObserver(self, observer):
		if observer in self._observers:
			self._observers.remove(observer)
	
	def serializable(self):
		return { "id": self.getId(), "type": self.getType(), "title": self.getTitle(), "class": self.getClass() }
	
	def __unicode__(self):
		return u'<%s type: %s, id: %s>' % (self.__class__.__name__, self._type, self._id)
	
	def __str__(self):
		return unicode(self).encode("utf-8")
	
	__repr__ = __unicode__
	
class MessageSubject(Subject):
	def __init__(self, id, type=u'', title=u'', **args):
		Subject.__init__(self, id, type, title, **args)
		self.reset()
		if args.has_key('message'):
			self._message  = forceUnicode(args['message'])
		if args.has_key('severity'):
			self._severity = forceInt(args['severity'])
		logger.debug(u"MessageSubject '%s' created" % self._id)
	
	def reset(self):
		Subject.reset(self)
		self._message  = u''
		self._severity = 0
	
	def setMessage(self, message, severity = 0):
		self._message  = forceUnicode(message)
		self._severity = forceInt(severity)
		self._notifyMessageChanged()
		
	def getMessage(self):
		return self._message
	
	def getSeverity(self):
		return self._severity
	
	def _notifyMessageChanged(self):
		for o in self._observers:
			o.messageChanged(self, self._message)
	
	def serializable(self):
		s = Subject.serializable(self)
		s['message']  = self.getMessage()
		s['severity'] = self.getSeverity()
		return s
	
class ChoiceSubject(MessageSubject):
	def __init__(self, id, type=u'', title=u'', **args):
		MessageSubject.__init__(self, id, type, title, **args)
		self.reset()
		self._callbacks = []
		if args.has_key('choices'):
			self._choices = forceUnicodeList(args['choices'])
		if args.has_key('selectedIndex'):
			self._selectedIndex = forceInt(args['selectedIndex'])
		if args.has_key('callbacks'):
			self._callbacks = args['callbacks']
		logger.debug(u"ChoiceSubject '%s' created" % self._id)
	
	def reset(self):
		MessageSubject.reset(self)
		self._choices = []
		self._selectedIndex = -1
		
	def setSelectedIndex(self, selectedIndex):
		selectedIndex = forceInt(selectedIndex)
		if (selectedIndex > len(self._choices)-1):
			return
		self._selectedIndex = selectedIndex
		self._notifySelectedIndexChanged()
	
	def getSelectedIndex(self):
		return self._selectedIndex
	
	def setChoices(self, choices):
		self._choices = forceUnicodeList(choices)
		if (len(self._choices) > 0) and (self._selectedIndex < 0):
			self._selectedIndex = 0
		self._notifyChoicesChanged()
	
	def getChoices(self):
		return self._choices
	
	def selectChoice(self):
		logger.info(u"ChoiceSubject.selectChoice()")
		if (self._selectedIndex >= 0) and (self._selectedIndex < len(self._callbacks)):
			# Exceute callback
			logger.notice(u"Executing callback %s" % self._callbacks[self._selectedIndex])
			self._callbacks[self._selectedIndex](self)
		
	def setCallbacks(self, callbacks):
		callbacks = forceList(callbacks)
		self._callbacks = callbacks
	
	def _notifySelectedIndexChanged(self):
		for o in self._observers:
			o.selectedIndexChanged(self, self._selectedIndex)
	
	def _notifyChoicesChanged(self):
		for o in self._observers:
			o.choicesChanged(self, self._choices)
	
	def serializable(self):
		s = MessageSubject.serializable(self)
		s['choices']       = self.getChoices()
		s['selectedIndex'] = self.getSelectedIndex()
		return s

class ProgressSubject(MessageSubject):
	def __init__(self, id, type=u'', title=u'', **args):
		MessageSubject.__init__(self, id, type, title, **args)
		self.reset()
		self._fireAlways = True
		if args.has_key('end'):
			self._end = forceInt(args['end'])
			if (self._end < 0): self._end = 0
		if args.has_key('percent'):
			self._percent = args['percent']
		if args.has_key('state'):
			self._state = args['state']
		if args.has_key('timeStarted'):
			self._timeStarted = args['timeStarted']
		if args.has_key('timeSpend'):
			self._timeSpend = args['timeSpend']
		if args.has_key('timeLeft'):
			self._timeLeft = args['timeLeft']
		if args.has_key('timeFired'):
			self._timeFired = args['timeFired']
		if args.has_key('speed'):
			self._speed = args['speed']
		if args.has_key('fireAlways'):
			self._fireAlways = forceBool(args['fireAlways'])
		logger.debug(u"ProgressSubject '%s' created" % self._id)
		
	def reset(self):
		MessageSubject.reset(self)
		self._end         = 0
		self._percent     = 0
		self._state       = 0
		self._timeStarted = long(time.time())
		self._timeSpend   = 0
		self._timeLeft    = 0
		self._timeFired   = 0
		self._speed       = 0
	
	def setEnd(self, end):
		self._end = forceInt(end)
		if (self._end < 0):
			self._end = 0
		self.setState(self._state)
		
	def setState(self, state):
		state = forceInt(state)
		if (state <= 0):
			state = 0
			self._percent = 0
		if (state > self._end):
			state = self._end
			self._percent = 100
		self._state = state
		
		now = long(time.time())
		if self._fireAlways or (self._timeFired != now) or (self._state == self._end):
			if (self._end == 0):
				self._percent = 100
			else:
				self._percent = float(100)*(float(self._state) / float(self._end))
			
			self._timeSpend = now - self._timeStarted
			if self._timeSpend:
				self._speed = int(self._state/self._timeSpend)
				if (self._speed > 0):
					self._timeLeft = ((self._end-self._state)/self._speed)
			
			self._timeFired = now
			self._notifyProgressChanged()
	
	def addToState(self, amount):
		self.setState(self._state + forceInt(amount))
	
	def getEnd(self):
		return self._end
	
	def getState(self):
		return self._state
	
	def getPercent(self):
		return self._percent
	
	def getTimeSpend(self):
		return self._timeSpend
		
	def getTimeLeft(self):
		return self._timeLeft
		
	def getSpeed(self):
		return self._speed
		
	def _notifyProgressChanged(self):
		for o in self._observers:
			o.progressChanged(self, self._state, self._percent, self._timeSpend, self._timeLeft, self._speed)
	
	def serializable(self):
		s = MessageSubject.serializable(self)
		s['end']       = self.getEnd()
		s['state']     = self.getState()
		s['percent']   = self.getPercent()
		s['timeSpend'] = self.getTimeSpend()
		s['timeLeft']  = self.getTimeLeft()
		s['speed']     = self.getSpeed()
		return s

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Observers                                                                   =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class MessageObserver(object):
	def __init__(self):
		pass
	
	def messageChanged(self, subject, message):
		pass

class ChoiceObserver(MessageObserver):
	def __init__(self):
		MessageObserver.__init__(self)
	
	def selectedIndexChanged(self, subject, selectedIndex):
		pass
	
	def choicesChanged(self, subject, choices):
		pass

class ProgressObserver(MessageObserver):
	def __init__(self):
		pass
	
	def progressChanged(self, subject, state, percent, timeSpend, timeLeft, speed):
		pass

class SubjectsObserver(ChoiceObserver, ProgressObserver):
	def __init__(self):
		self._subjects = []
	
	def setSubjects(self, subjects):
		for subject in self._subjects:
			subject.detachObserver(self)
		self._subjects = subjects
		for subject in self._subjects:
			subject.attachObserver(self)
		self.subjectsChanged(self._subjects)
	
	def addSubject(self, subject):
		if not subject in self._subjects:
			self._subjects.append(subject)
			subject.attachObserver(self)
		self.subjectsChanged(self._subjects)
	
	def removeSubject(self, subject):
		if subject in self._subjects:
			subject.detachObserver(self)
			self._subjects.remove(subject)
		self.subjectsChanged(self._subjects)
	
	def getSubjects(self):
		return self._subjects
	
	def subjectsChanged(self, subjects):
		pass


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Subject proxies                                                             =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class MessageSubjectProxy(ProgressSubject, ProgressObserver, ChoiceSubject, ChoiceObserver):
	def __init__(self, id, type=u'', title=u'', **args):
		ChoiceSubject.__init__(self, id, type, title, **args)
		ChoiceObserver.__init__(self)
		ProgressSubject.__init__(self, id, type, title, **args)
		ProgressObserver.__init__(self)
		self._fireAlways = True
	
	def messageChanged(self, subject, message):
		self.setMessage(message, severity = subject.getSeverity())
	
	def selectedIndexChanged(self, subject, selectedIndex):
		self.setSelectedIndex(selectedIndex)
	
	def choicesChanged(self, subject, choices):
		self.setChoices(choices)
	
	def progressChanged(self, subject, state, percent, timeSpend, timeLeft, speed):
		self._end = subject.getEnd()
		self.setState(state)
	
class ChoiceSubjectProxy(MessageSubjectProxy):
	def __init__(self, id, type=u'', title=u'', **args):
		MessageSubjectProxy.__init__(self, id, type, title, **args)

class ProgressSubjectProxy(MessageSubjectProxy):
	def __init__(self, id, type=u'', title=u'', **args):
		MessageSubjectProxy.__init__(self, id, type, title, **args)
	
	
	

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Notification server                                                         =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class NotificationServerProtocol(LineReceiver):
	def connectionMade(self):
		self.factory.connectionMade(self)
		
	def connectionLost(self, reason):
		self.factory.connectionLost(self, reason)
	
	def lineReceived(self, line):
		self.factory.rpc(self, line)

class NotificationServerFactory(ServerFactory, SubjectsObserver):
	protocol = NotificationServerProtocol
	
	def __init__(self):
		self.clients   = []
		self._subjects = []
		self._rpcs     = {}
	
	def connectionMade(self, client):
		logger.info(u"client connection made")
		self.clients.append(client)
		self.subjectsChanged(self.getSubjects())
		
	def connectionLost(self, client, reason):
		logger.info(u"client connection lost")
		self.clients.remove(client)
		
	def rpc(self, client, line):
		line = unicode(line, 'utf-8')
		logger.info(u"received line %s" % line)
		id = None
		try:
			if hasattr(json, 'loads'):
				# python 2.6 json module
				rpc = json.loads( line )
			else:
				rpc = json.read( line )
			method = rpc['method']
			id = rpc['id']
			params = rpc['params']
			
			if (method == 'setSelectedIndex'):
				subjectId = params[0]
				selectedIndex = params[1]
				for subject in self.getSubjects():
					if not isinstance(subject, ChoiceSubject) or (subject.getId() != subjectId):
						continue
					result = subject.setSelectedIndex(selectedIndex)
					break
			
			elif (method == 'selectChoice'):
				logger.info(u"selectChoice(%s)" % unicode(params)[1:-1])
				subjectId = params[0]
				for subject in self.getSubjects():
					if not isinstance(subject, ChoiceSubject) or (subject.getId() != subjectId):
						continue
					result = subject.selectChoice()
					break
			
			else:
				raise ValueError(u"unknown method '%s'" % method)
		except Exception, e:
			logger.error(u"Failed to execute rpc: %s" % e)
	
	def messageChanged(self, subject, message):
		if not subject in self.getSubjects():
			logger.info(u"Unknown subject %s passed to messageChanged, automatically adding subject" % subject)
			self.addSubject(subject)
		logger.debug(u"messageChanged: subject id '%s', message '%s'" % (subject.getId(), message))
		self.notify( name = u"messageChanged", params = [subject.serializable(), message] )
	
	def selectedIndexChanged(self, subject, selectedIndex):
		if not subject in self.getSubjects():
			logger.info(u"Unknown subject %s passed to selectedIndexChanged, automatically adding subject" % subject)
			self.addSubject(subject)
		logger.debug(u"selectedIndexChanged: subject id '%s', selectedIndex '%s'" % (subject.getId(), selectedIndex))
		self.notify( name = u"selectedIndexChanged", params = [ subject.serializable(), selectedIndex ] )
	
	def choicesChanged(self, subject, choices):
		if not subject in self.getSubjects():
			logger.info(u"Unknown subject %s passed to choicesChanged, automatically adding subject" % subject)
			self.addSubject(subject)
		logger.debug(u"choicesChanged: subject id '%s', choices %s" % (subject.getId(), choices))
		self.notify( name = u"choicesChanged", params = [ subject.serializable(), choices ] )
	
	def progressChanged(self, subject, state, percent, timeSpend, timeLeft, speed):
		if not subject in self.getSubjects():
			logger.info(u"Unknown subject %s passed to progressChanged, automatically adding subject" % subject)
			self.addSubject(subject)
		logger.debug(u"progressChanged: subject id '%s', state %s, percent %s, timeSpend %s, timeLeft %s, speed %s" \
			% (subject.getId(), state, percent, timeSpend, timeLeft, speed))
		self.notify( name = u"progressChanged", params = [ subject.serializable(), state, percent, timeSpend, timeLeft, speed ] )
	
	def subjectsChanged(self, subjects):
		logger.debug(u"subjectsChanged: subjects %s" % subjects)
		param = []
		for subject in subjects:
			param.append(subject.serializable())
		self.notify( name = u"subjectsChanged", params = [ param ] )
	
	def notify(self, name, params, clients = []):
		if not type(params) is list:
			params = [ params ]
		if not clients:
			clients = self.clients
		if not type(clients) is list:
			clients = [ clients ]
		if not clients:
			logger.info(u"cannot send notification '%s', no client connected" % name)
			return
		logger.info(u"sending notification '%s' to clients" % name)
		for client in self.clients:
			jsonString = ''
			# json-rpc: notifications have id null
			if hasattr(json, 'dumps'):
				# python 2.6 json module
				jsonString = json.dumps( {"id": None, "method": name, "params": params } )
			else:
				jsonString = json.write( {"id": None, "method": name, "params": params } )
			if type(jsonString) is unicode:
				jsonString = jsonString.encode('utf-8')
			client.sendLine(jsonString)


class NotificationServer(threading.Thread, SubjectsObserver):
	def __init__(self, address, port, subjects):
		threading.Thread.__init__(self)
		self._address = forceIpAddress(address)
		if not self._address:
			self._address = u'0.0.0.0'
		self._port = forceInt(port)
		self._factory = NotificationServerFactory()
		self._factory.setSubjects(subjects)
		self._server = None
		
	def getFactory(self):
		return self._factory
	
	def getObserver(self):
		return self._factory
	
	def setSubjects(self, subjects):
		return self._factory.setSubjects(subjects)
		
	def addSubject(self, subject):
		return self._factory.addSubject(subject)
		
	def removeSubject(self, subject):
		return self._factory.removeSubject(subject)
	
	def getSubjects(self):
		return self._factory.getSubjects()
	
	def run(self):
		logger.info(u"Notification server starting")
		try:
			if (self._address == '0.0.0.0'):
				self._server = reactor.listenTCP(self._port, self._factory)
			else:
				self._server = reactor.listenTCP(self._port, self._factory, interface = self._address)
			
			if not reactor.running:
				reactor.run(installSignalHandlers=0)
		except Exception, e:
			logger.logException(e)
	
	def stop(self, stopReactor=True):
		if self._server:
			self._server.stopListening()
		if stopReactor and reactor and reactor.running:
			try:
				reactor.stop()
			except Exception, e:
				logger.error(u"Failed to stop reactor: %s" % e)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Notification client                                                         =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
class NotificationClientProtocol(LineReceiver):
	def connectionMade(self):
		self.factory.connectionMade(self)
		
	def lineReceived(self, line):
		self.factory.receive(line)
		
	def connectionLost(self, reason):
		self.factory.connectionLost(reason)

class NotificationClientFactory(ClientFactory):
	protocol = NotificationClientProtocol
	_client = None
	_observer = None
	
	def __init__(self, observer):
		self._observer = observer
		self._rpcs = {}
		self._timeout = 5
	
	#def clientConnectionFailed(self, connector, reason):
	#	logger.error("client connection failed")
	
	#def clientConnectionLost(self, connector, reason):
	#	pass
	
	def connectionLost(self, reason):
		logger.info(u"server connection lost")
	
	def connectionMade(self, client):
		logger.info(u"server connection made")
		self._client = client
	
	def isReady(self):
		return (self._client != None)
	
	def sendLine(self, line):
		logger.debug(u"sending line '%s'" % line)
		self._client.sendLine(line)
	
	def receive(self, rpc):
		logger.debug(u"received rpc '%s'" % rpc)
		id = None
		try:
			if hasattr(json, 'loads'):
				# python 2.6 json module
				rpc = json.loads( rpc )
			else:
				rpc = json.read( rpc )
			id = rpc['id']
			if id:
				# Received rpc answer
				self._rpcs[id] = rpc
			else:
				# Notification
				method = rpc['method']
				params = rpc['params']
				logger.info( u"eval self._observer.%s(%s)" % (method, unicode(params)[1:-1]) )
				eval( "self._observer.%s(**params)" % method )
		except Exception, e:
			logger.error(e)
	
	def execute(self, method, params):
		logger.debug(u"executing method '%s', params %s" % (method, params))
		if not params:
			params = []
		if not type(params) in (list, tuple):
			params = [ params ]
		
		timeout = 0
		while not self.isReady() and (timeout < self._timeout):
			time.sleep(0.1)
			timeout += 0.1
		if (timeout >= self._timeout):
			raise Exception(u"execute timed out after %d seconds" % self._timeout)
		
		rpc = {'id': None, "method": method, "params": params }
		if hasattr(json, 'dumps'):
			# python 2.6 json module
			self.sendLine( json.dumps( rpc ) )
		else:
			self.sendLine( json.write( rpc ) )

class NotificationClient(threading.Thread):
	def __init__(self, address, port, observer):
		threading.Thread.__init__(self)
		self._address = address
		self._port = port
		self._observer = observer
		self._factory = NotificationClientFactory(self._observer)
		self._client = None
		
	def getFactory(self):
		return self._factory
	
	def run(self):
		logger.info(u"Notification client starting")
		try:
			logger.info(u"Connecting to %s:%s" % (self._address, self._port))
			reactor.connectTCP(self._address, self._port, self._factory)
			if not reactor.running:
				reactor.run(installSignalHandlers=0)
		except Exception, e:
			logger.logException(e)
	
	def stop(self, stopReactor=True):
		if self._client:
			self._client.disconnect()
		if stopReactor and reactor and reactor.running:
			reactor.stop()
	
	def setSelectedIndex(self, subjectId, choiceIndex):
		self._factory.execute(method = 'setSelectedIndex', params = [ subjectId, choiceIndex ])
	
	def selectChoice(self, subjectId):
		self._factory.execute(method = 'selectChoice', params = [ subjectId ])



