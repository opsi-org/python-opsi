#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - MessageBus  =
   = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2011 uib GmbH
   
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

import threading, sys
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory, ClientFactory
from twisted.internet import reactor, defer

from sys import version_info
if (version_info >= (2,6)):
	import json
else:
	import simplejson as json

from Queue import Queue, Empty, Full

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Util import randomString, getGlobalConfig

# Get logger instance
logger = Logger()

startReactor = True

def getMessageBusSocket():
	sock = getGlobalConfig('opsi_message_bus_socket')
	if not sock:
		sock = u'/var/run/opsi-message-bus/opsi-message-bus.socket'
	return sock

class MessageQueue(threading.Thread):
	def __init__(self, transport, size, poll = 0.01, additionalTransportArgs = []):
		threading.Thread.__init__(self)
		self.transport = transport
		self.size = forceInt(size)
		self.queue = Queue(self.size)
		self.poll = forceFloat(poll)
		self.additionalTransportArgs = forceList(additionalTransportArgs)
		self.stopped = False
		
	def stop(self):
		self.stopped = True
		
	def add(self, message):
		if self.stopped:
			raise Exception(u"MessageQueue stopped")
		logger.debug(u'Adding message %s to queue (current queue size: %d)' % (message, self.queue.qsize()))
		self.queue.put(message, block = True)
		logger.debug2(u'Added message %s to queue' % message)
	
	def run(self):
		logger.debug(u"MessageQueue started")
		while not self.stopped or not self.queue.empty():
			messages = []
			while not self.queue.empty():
				try:
					messages.append(self.queue.get(block = False))
					if (len(messages) >= self.size):
						break
				except Empty:
					break
			if messages:
				try:
					reactor.callFromThread(self.transport.transmitMessages, messages, *self.additionalTransportArgs)
				except Exception, e:
					logger.logException(e)
					logger.error(u"Failed to transmit, requeuing messages")
					for message in messages:
						self.queue.put(message, block = True)
					time.sleep(1)
			time.sleep(self.poll)
		logger.debug(u"MessageQueue stopped (empty: %s, stopped: %s)" % (self.queue.empty(), self.stopped))

class MessageBusServerProtocol(LineReceiver):
	def connectionMade(self):
		self.factory.connectionMade(self)
		
	def connectionLost(self, reason):
		self.factory.connectionLost(self, reason)
	
	def lineReceived(self, line):
		self.factory.lineReceived(line)
	
class MessageBusServerFactory(ServerFactory):
	protocol = MessageBusServerProtocol
	
	def __init__(self):
		self.clients = {}
	
	def connectionCount(self):
		return len(self.clients)
	
	def connectionMade(self, client):
		logger.info(u"Client connection made")
		clientId = randomString(16)
		messageQueue = MessageQueue(transport = self, size = 10, poll = 0.01, additionalTransportArgs = [ clientId ])
		self.clients[clientId] = { 'connection': client, 'messageQueue': messageQueue, 'registeredForObjectEvents': {} }
		messageQueue.start()
		self.sendMessage({"message_type": "init", "client_id": clientId}, clientId = clientId)
		
	def connectionLost(self, client, reason):
		logger.info(u"Client connection lost")
		for clientId in self.clients.keys():
			if self.clients[clientId]['connection'] is client:
				self.clients[clientId]['messageQueue'].stop()
				self.clients[clientId]['messageQueue'].join(10)
				del self.clients[clientId]
				return
	
	def lineReceived(self, line):
		try:
			for message in forceList(json.loads(line)):
				if message.get('message_type') in ('quit', 'exit', 'bye'):
					client = self.clients.get(message.get('client_id'))
					if client:
						client['connection'].transport.loseConnection()
					
				if (message.get('message_type') == 'register_for_object_events'):
					clientId = message.get('client_id')
					if not clientId:
						raise Exception(u"Attribute 'client_id' missing")
					if not self.clients.has_key(clientId):
						raise Exception(u"Unknown client id '%s'" % clientId)
					operations = forceUnicodeList(message.get('operations', []))
					objTypes = forceUnicodeList(message.get('objTypes', []))
					for op in operations:
						if not op in ('created', 'updated', 'deleted'):
							logger.error(u"Unknown operation '%s' in register_for_object_events of client '%s'" \
								% (op, clientId))
							self.sendError(u"Unknown operation '%s'" % op, clientId = clientId)
					self.clients[clientId]['registeredForObjectEvents'] = {
						'operations': operations,
						'objTypes': objTypes
					}
				elif (message.get('message_type') == 'object_event'):
					operation = forceUnicode(message.get('operation'))
					if not operation in ('created', 'updated', 'deleted'):
						logger.error(u"Unknown operation '%s'" % operation)
					objType = forceUnicode(message.get('objType'))
					ident = message.get('ident')
					message = {
						"message_type": "object_event",
						"operation":    operation,
						"objType":      objType,
						"ident":        ident
					}
					for clientId in self.clients.keys():
						if not self.clients[clientId].get('registeredForObjectEvents'):
							continue
						operations = self.clients[clientId]['registeredForObjectEvents'].get('operations')
						if operations and not operation in operations:
							continue
						objTypes = self.clients[clientId]['registeredForObjectEvents'].get('objTypes')
						if objTypes and not objType in objTypes:
							continue
						self.clients[clientId]['messageQueue'].add(message)
		except Exception, e:
			logger.logException(e)
	
	def sendMessage(self, message, clientId = None):
		if clientId:
			client = self.clients.get(clientId)
			if not client:
				logger.error(u"Failed to send message: client '%s' not connected" % clientId)
				return
			client['messageQueue'].add(message)
		else:
			for client in self.clients.values():
				client['messageQueue'].add(message)
		
	def transmitMessages(self, messages, clientId):
		logger.info(u"Transmitting messages to client '%s'" % clientId)
		messages = json.dumps(messages)
		client = self.clients.get(clientId)
		if not client:
			logger.error(u"Failed to send message: client '%s' not connected" % clientId)
			return
		client['connection'].sendLine(messages)
		
	def sendError(self, errorMessage, clientId = None):
		self.sendMessage({'message_type': 'error', 'message': forceUnicode(errorMessage)}, clientId)
	
class MessageBusServer(threading.Thread):
	def __init__(self, port = None):
		threading.Thread.__init__(self)
		if not port:
			port = getMessageBusSocket()
		self._port = forceFilename(port)
		self._factory = MessageBusServerFactory()
		self._server = None
	
	def run(self):
		logger.info(u"Notification server starting")
		try:
			logger.notice(u"Creating unix socket '%s'" % self._port)
			if os.path.exists(self._port):
				logger.warning(u"Unix socket '%s' already exists" % self._port)
				os.unlink(self._port)
			self._server = reactor.listenUNIX(self._port, self._factory)
			if startReactor and not reactor.running:
				reactor.run(installSignalHandlers=0)
		except Exception, e:
			logger.logException(e)
	
	def stop(self, stopReactor=True):
		self._server.stopListening()
		if stopReactor and reactor and reactor.running:
			try:
				reactor.stop()
			except:
				pass
		if os.path.exists(self._port):
			os.unlink(self._port)
	
class MessageBusClientProtocol(LineReceiver):
	def connectionMade(self):
		logger.debug(u"Connection made")
		self.factory.messageBusClient.connectionMade(self)
		
	def connectionLost(self, reason):
		logger.debug(u"Connection lost")
		self.factory.messageBusClient.connectionLost(reason)
	
	def lineReceived(self, line):
		logger.debug(u"Line received")
		self.factory.messageBusClient.lineReceived(line)
		
class MessageBusClientFactory(ClientFactory):
	protocol = MessageBusClientProtocol
	
	def __init__(self, messageBusClient):
		self.messageBusClient = messageBusClient

class MessageBusClient(threading.Thread):
	def __init__(self, port = None, autoReconnect = True):
		threading.Thread.__init__(self)
		if not port:
			port = getMessageBusSocket()
		self._port = forceFilename(port)
		self._autoReconnect = forceBool(autoReconnect)
		self._factory = MessageBusClientFactory(self)
		self._client = None
		self._connection = None
		self._clientId = None
		self._messageQueue = MessageQueue(transport = self, size = 10, poll = 0.01)
		self._connected = threading.Event()
		self._clientIdReceived = threading.Event()
		self._reactorStopPending = False
		self._stopping = False
		self._registeredForObjectEvents = {}
		
	def run(self):
		logger.info(u"MessageBus client is starting")
		self._messageQueue.start()
		try:
			self._client = reactor.connectUNIX(self._port, self._factory)
			if startReactor and not reactor.running:
				reactor.run(installSignalHandlers=0)
		except Exception, e:
			logger.logException(e)
		self._messageQueue.join(10)
		
	def stop(self, stopReactor=True):
		self._stopping = True
		self._waitForConnection()
		if not self._connection:
			self._messageQueue.stop()
			if stopReactor and reactor and reactor.running:
				reactor.stop()
			return
		self._messageQueue.add({
			"client_id":    self._clientId,
			"message_type": "quit"
		})
		self._messageQueue.stop()
		self._client.disconnect()
		self._reactorStopPending = stopReactor
	
	def messageBusConnectionError(self, error):
		pass
	
	def connectionMade(self, connection):
		self._connection = connection
		self._connected.set()
	
	def connectionLost(self, reason):
		self._connection = None
		self._connected.clear()
		self._clientId = None
		self._clientIdReceived.clear()
		if self._stopping and self._reactorStopPending and reactor and reactor.running:
			try:
				reactor.stop()
			except:
				pass
		if not self._stopping and self._autoReconnect:
			reactor.callLater(1, self._reconnect)
		
	def _reconnect(self):
		if self._connection:
			if self._registeredForObjectEvents:
				self.registerForObjectEvents(
					objTypes   = self._registeredForObjectEvents['objTypes'],
					operations = self._registeredForObjectEvents['operations'])
			return
		try:
			self._client.connect()
		except Exception, e:
			pass
		self._connected.wait(1)
		reactor.callLater(1, self._reconnect)
		
	def _waitForConnection(self, timeout = 5):
		self._connected.wait(timeout)
		if not self._connection:
			error = u"Connect timed out after %d seconds" % timeout
			logger.error(error)
			self.messageBusConnectionError(error)
		
	def _waitForClientId(self, timeout = 5):
		self._clientIdReceived.wait(timeout)
		if not self._clientId:
			logger.error(u"Wait for client id timed out after %d seconds" % timeout)
		
	def lineReceived(self, line):
		try:
			for message in forceList(json.loads(line)):
				if (message.get('message_type') == 'error'):
					logger.error(u"Received error message: %s" % message.get('message'))
				elif (message.get('message_type') == 'init'):
					self._clientId = message.get('client_id', self._clientId)
					if self._clientId:
						self._clientIdReceived.set()
				elif (message.get('message_type') == 'object_event'):
					operation = forceUnicode(message.get('operation'))
					if not operation in ('created', 'updated', 'deleted'):
						logger.error(u"Unknown operation '%s'" % operation)
					objType = forceUnicode(message.get('objType'))
					ident = message.get('ident')
					logger.info(u"%s %s %s" % (objType, ident, operation))
					self.objectEventReceived(objType, ident, operation)
		except Exception, e:
			logger.logException(e)
	
	def objectEventReceived(self, objType, ident, operation):
		pass
	
	def sendLine(self, line):
		self._waitForConnection()
		if not self._connection:
			return
		self._connection.sendLine(line)
	
	def transmitMessages(self, messages):
		logger.info(u"Transmitting messages")
		self.sendLine(json.dumps(messages))
		
	def notifyObjectEvent(self, operation, obj):
		self._waitForClientId()
		self._messageQueue.add({
			"client_id":    self._clientId,
			"message_type": "object_event",
			"operation":    operation,
			"objType":      obj.getType(),
			"ident":        obj.getIdent('dict')
		})
		
	def notifyObjectCreated(self, obj):
		self.notifyObjectEvent('created', obj)
	
	def notifyObjectUpdated(self, obj):
		self.notifyObjectEvent('updated', obj)
	
	def notifyObjectDeleted(self, obj):
		self.notifyObjectEvent('deleted', obj)
	
	def registerForObjectEvents(self, objTypes = [], operations = []):
		self._waitForClientId()
		self._messageQueue.add({
			"client_id":    self._clientId,
			"message_type": "register_for_object_events",
			"operations":   forceUnicodeList(operations),
			"objTypes":     forceUnicodeList(objTypes)
		})
		self._registeredForObjectEvents = { 'objTypes': objTypes, 'operations': operations }
		
if (__name__ == '__main__'):
	logger.setConsoleLevel(LOG_DEBUG)
	if sys.argv[1] == 'server':
		mb = MessageBusServer()
		mb.start()
		while True:
			time.sleep(1)
		
	else:
		mb = MessageBusClient()
		mb.start()
		#mb.registerForObjectEvents(objTypes = ['OpsiHost'], operations = ['xxxxxxx'])
		mb.registerForObjectEvents(objTypes = ['OpsiHost', 'OpsiClient'], operations = ['created', 'deleted', 'updated'])
		mb.join()

