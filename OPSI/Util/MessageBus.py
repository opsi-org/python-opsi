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

import base64
import json
import os
import sys
import threading

from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory, ClientFactory
from twisted.internet import reactor, defer
from twisted.internet._sslverify import OpenSSLCertificateOptions

from Queue import Queue, Empty, Full
from OpenSSL import SSL

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Util import randomString, getGlobalConfig
from OPSI.Util.HTTP import hybi10Decode, hybi10Encode, urlsplit

# Get logger instance
logger = Logger()

def getMessageBusSocket():
	sock = getGlobalConfig('opsi_message_bus_socket')
	if not sock:
		sock = u'/var/run/opsi-message-bus/opsi-message-bus.socket'
	return sock

class MessageQueue(threading.Thread):
	def __init__(self, transport, size = 10, poll = 0.3, additionalTransportArgs = []):
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
		logger.debug(u'Adding message %s to queue %s (current queue size: %d)' % (message, self, self.queue.qsize()))
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
		return len(self.clients.keys())

	def connectionMade(self, client, readonly = False):
		logger.debug(u"Client connection made")
		clientId = randomString(16)
		messageQueue = MessageQueue(transport = self, additionalTransportArgs = [ clientId ])
		self.clients[clientId] = { 'readonly': readonly, 'connection': client, 'messageQueue': messageQueue, 'registeredForObjectEvents': {} }
		logger.notice(u"%s client connection made (%s), %d client(s) connected" % (self.__class__.__name__, clientId, self.connectionCount()))
		messageQueue.start()
		self.sendMessage({"message_type": "init", "client_id": clientId}, clientId = clientId)

	def connectionLost(self, client, reason):
		logger.debug(u"Client connection lost")
		clientId = u'unknown'
		for cid in self.clients.keys():
			if self.clients[cid]['connection'] is client:
				clientId = cid
				self.clients[cid]['messageQueue'].stop()
				self.clients[cid]['messageQueue'].join(10)
				del self.clients[cid]
				break
		logger.notice(u"%s client connection lost (%s), %d client(s) connected" % (self.__class__.__name__, clientId, self.connectionCount()))

	def lineReceived(self, line):
		try:
			logger.debug(u"Line received: '%s'" % line)
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
					object_types = forceUnicodeList(message.get('object_types', []))
					for op in operations:
						if not op in ('created', 'updated', 'deleted'):
							logger.error(u"Unknown operation '%s' in register_for_object_events of client '%s'" \
								% (op, clientId))
							self.sendError(u"Unknown operation '%s'" % op, clientId = clientId)
					self.clients[clientId]['registeredForObjectEvents'] = {
						'operations': operations,
						'object_types': object_types
					}
					logger.info(u"Client '%s' now registered for object_types %s, operations %s" \
							% (clientId, object_types, operations))

				elif (message.get('message_type') == 'object_event'):
					clientId = message.get('client_id', 'unknown')
					try:
						if self.clients[clientId]['readonly']:
							raise Exception('readonly')
					except Exception, e:
						logger.warning("Read only client '%s' passed object_event" % clientId)
						return
					object_type = forceUnicode(message.get('object_type'))
					ident = message.get('ident')
					operation = forceUnicode(message.get('operation'))
					self._sendObjectEvent(object_type, ident, operation)
		except Exception, e:
			logger.error(u"Received line '%s'" % line)
			logger.logException(e)

	def _sendObjectEvent(self, object_type, ident, operation):
		if not operation in ('created', 'updated', 'deleted'):
			logger.error(u"Unknown operation '%s'" % operation)
		message = {
			"message_type": "object_event",
			"operation":    operation,
			"object_type":  object_type,
			"ident":        ident
		}
		for clientId in self.clients.keys():
			if not self.clients[clientId].get('registeredForObjectEvents'):
				continue
			operations = self.clients[clientId]['registeredForObjectEvents'].get('operations')
			if operations and not operation in operations:
				continue
			object_types = self.clients[clientId]['registeredForObjectEvents'].get('object_types')
			if object_types and not object_type in object_types:
				continue
			self.clients[clientId]['messageQueue'].add(message)

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
		logger.debug(u"Transmitting messages to client '%s'" % clientId)
		messages = json.dumps(messages)
		client = self.clients.get(clientId)
		if not client:
			logger.error(u"Failed to send message: client '%s' not connected" % clientId)
			return
		client['connection'].sendLine(messages)

	def sendError(self, errorMessage, clientId = None):
		self.sendMessage({'message_type': 'error', 'message': forceUnicode(errorMessage)}, clientId)

class MessageBusServer(threading.Thread):
	def __init__(self, port = None,):
		threading.Thread.__init__(self)
		if not port:
			port = getMessageBusSocket()
		self._port = forceFilename(port)
		self._factory = MessageBusServerFactory()
		self._server = None
		self._startReactor = False
		self._stopping = False

	def isStopping(self):
		return self._stopping

	def start(self, startReactor=True):
		self._startReactor = startReactor
		logger.notice(u"Creating unix socket '%s'" % self._port)
		if os.path.exists(self._port):
			logger.warning(u"Unix socket '%s' already exists" % self._port)
			os.unlink(self._port)
		self._server = reactor.listenUNIX(self._port, self._factory)
		threading.Thread.start(self)

	def run(self):
		logger.info(u"Notification server starting")
		try:
			if self._startReactor and not reactor.running:
				reactor.run(installSignalHandlers = False)
			else:
				while not self._stopping:
					time.sleep(1)
		except Exception, e:
			logger.logException(e)

	def stop(self, stopReactor=True):
		self._stopping = True
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

	def clientConnectionFailed(self, client, reason):
		self.messageBusClient.connectionFailed(reason)

class MessageBusClient(threading.Thread):
	def __init__(self, port = None, autoReconnect = True):
		threading.Thread.__init__(self)
		if not port:
			port = getMessageBusSocket()
		self._port = forceFilename(port)
		self._autoReconnect = forceBool(autoReconnect)
		self._reconnectionAttemptInterval = 2
		self._reconnecting = False
		self._factory = MessageBusClientFactory(self)
		self._client = None
		self._connection = None
		self._clientId = None
		self._messageQueue = MessageQueue(transport = self)
		self._reactorStopPending = False
		self._stopping = False
		self._registeredForObjectEvents = {}
		self._startReactor = False
		self._initialized = threading.Event()

	def isStopping(self):
		return self._stopping

	def start(self, startReactor=True):
		self._startReactor = startReactor
		threading.Thread.start(self)

	def connectionFailed(self, reason):
		if self._reconnecting:
			logger.debug(u"Failed to reconnect %s '%s': %s" % (self._client, self._port, reason))
		else:
			logger.error(u"Failed to connect %s '%s': %s" % (self._client, self._port, reason))
			self.stop()

	def _connect(self):
		logger.info(u"Connecting to socket: %s" % self._port)
		self._client = reactor.connectUNIX(self._port, self._factory, timeout=1)

	def run(self):
		logger.info(u"MessageBus client is starting")
		self._connect()
		self._messageQueue.start()
		try:
			if self._startReactor and not reactor.running:
				reactor.run(installSignalHandlers = False)
			else:
				while not self.isStopping():
					time.sleep(1)
		except Exception, e:
			logger.logException(e)

		logger.debug2(u"MessageBus client stopping messageQueue %s" % self._messageQueue)
		self._messageQueue.stop()
		self._messageQueue.join(5)
		logger.debug2(u"MessageBus client exiting")

	def _disconnect(self):
		logger.debug(u"MessageBusClient disconnecting (%s)" % self._client)
		reactor.callFromThread(self._client.disconnect)

	def stop(self, stopReactor=True):
		self._stopping = True
		logger.debug(u"MessageBusClient is stopping")
		if self._connection:
			if stopReactor:
				logger.debug(u"MessageBusClient should stop reactor")
				self._reactorStopPending = True
			self._disconnect()
		elif stopReactor and reactor and reactor.running:
			logger.debug(u"MessageBusClient is stopping reactor")
			reactor.stop()

	def connectionMade(self, connection):
		logger.debug(u"Connected to socket %s" % self._port)
		self._connection = connection
		self._reconnecting = False

	def connectionLost(self, reason):
		logger.info(u"Connection to server lost, stopping: %s, auto reconnect: %s" % (self.isStopping(), self._autoReconnect))
		self._initialized.clear()
		self._connection = None
		self._clientId = None
		if self._reactorStopPending and reactor and reactor.running:
			try:
				reactor.stop()
			except:
				pass
		if not self.isStopping() and self._autoReconnect:
			self._reconnecting = True
			reactor.callLater(1, self._reconnect)

	def waitInitialized(self, timeout = 0.0):
		return self._initialized.wait(timeout = timeout)

	def isInitialized(self):
		return self._initialized.isSet()

	def initialized(self):
		logger.info(u"Initialized")
		self._initialized.set()

	def _reconnect(self):
		logger.debug2(u"Reconnect")
		self._reconnecting = True
		if self._connection:
			if self._registeredForObjectEvents:
				self.registerForObjectEvents(
					object_types   = self._registeredForObjectEvents['object_types'],
					operations = self._registeredForObjectEvents['operations'])
			return
		try:
			self._connect()
		except Exception, e:
			pass
		reactor.callLater(self._reconnectionAttemptInterval, self._reconnect)

	def lineReceived(self, line):
		if self.isStopping():
			return
		try:
			line = line.rstrip()
			for message in forceList(json.loads(line)):
				if (message.get('message_type') == 'error'):
					logger.error(u"Received error message: %s" % message.get('message'))
				elif (message.get('message_type') == 'init'):
					self._clientId = message.get('client_id', self._clientId)
					reactor.callLater(0.001, self.initialized)
				elif (message.get('message_type') == 'object_event'):
					operation = forceUnicode(message.get('operation'))
					if not operation in ('created', 'updated', 'deleted'):
						logger.error(u"Unknown operation '%s'" % operation)
					object_type = forceUnicode(message.get('object_type'))
					ident = message.get('ident')
					logger.info(u"Object event received: %s %s %s" % (object_type, forceUnicode(ident), operation))
					self.objectEventReceived(object_type, ident, operation)
		except Exception, e:
			logger.error(line)
			logger.logException(e)

	def objectEventReceived(self, object_type, ident, operation):
		pass

	def sendLine(self, line):
		if not self._connection:
			if self.isStopping():
				return
			raise Exception(u"Cannot send line: not connected")
		self._connection.sendLine(line)

	def transmitMessages(self, messages):
		logger.info(u"Transmitting messages: %s" % messages)
		self.sendLine(json.dumps(messages))

	def notifyObjectEvent(self, operation, obj):
		if self.isStopping():
			return
		self._messageQueue.add({
			"client_id":    self._clientId,
			"message_type": "object_event",
			"operation":    operation,
			"object_type":  obj.getType(),
			"ident":        obj.getIdent('dict')
		})

	def notifyObjectCreated(self, obj):
		self.notifyObjectEvent('created', obj)

	def notifyObjectUpdated(self, obj):
		self.notifyObjectEvent('updated', obj)

	def notifyObjectDeleted(self, obj):
		self.notifyObjectEvent('deleted', obj)

	def registerForObjectEvents(self, object_types = [], operations = []):
		if self.isStopping():
			return
		self._messageQueue.add({
			"client_id":    self._clientId,
			"message_type": "register_for_object_events",
			"operations":   forceUnicodeList(operations),
			"object_types": forceUnicodeList(object_types)
		})
		self._registeredForObjectEvents = { 'object_types': object_types, 'operations': operations }

class MessageBusWebsocketClientProtocol(MessageBusClientProtocol):
	def rawDataReceived(self, data):
		self.lineReceived(hybi10Decode(data))

	def lineReceived(self, line):
		logger.debug(u"Line received")
		line = line.rstrip()
		self.factory.messageBusClient.lineReceived(line)
		if self.line_mode and self.factory.messageBusClient.isWebsocketHandshakeDone():
			self.setRawMode()

class MessageBusWebsocketClientFactory(MessageBusClientFactory):
	protocol = MessageBusWebsocketClientProtocol

class MessageBusWebsocketClient(MessageBusClient):
	def __init__(self, url = 'https://localhost:4447/omb', autoReconnect = True):
		MessageBusClient.__init__(self, port = None, autoReconnect = autoReconnect)
		self._url = url
		self._reconnectionAttemptInterval = 10
		self._factory = MessageBusWebsocketClientFactory(self)
		self.__wsVersion = 8
		self.__wsHandshakeDone = False
		self.__headers = {}

		(self._scheme, self._host, self._port, self._baseUrl, self.__username, self.__password) = urlsplit(self._url)

	def isWebsocketHandshakeDone(self):
		return self.__wsHandshakeDone

	def _connect(self):
		logger.info(u"Connecting to host: %s" % self._host)
		contextFactory = OpenSSLCertificateOptions(
			privateKey          = None,
			certificate         = None,
			method              = SSL.SSLv3_METHOD,
			verify              = False,
			caCerts             = [],
			verifyDepth         = 2,
			requireCertificate  = False,
			verifyOnce          = False,
			enableSingleUseKeys = False,
			enableSessions      = False,
			fixBrokenPeers      = True)
		self._client = reactor.connectSSL(self._host, self._port, self._factory, contextFactory, timeout = 10)

	def connectionMade(self, connection):
		logger.debug(u"Connected to host: %s" % self._host)
		self._connection = connection
		self.__wsHandshakeDone = False

		self.__wsKey = base64.b64encode(os.urandom(16))

		headers = 'GET %s HTTP/1.1\r\n' % self._baseUrl
		if self.__username and self.__password:
			auth = (self.__username + u':' + self.__password).encode('latin-1')
			headers += 'Authorization: Basic ' + base64.encodestring(auth).strip()
		headers += 'Upgrade: websocket\r\n'
		headers += 'Connection: Upgrade\r\n'
		headers += 'Host: %s:%d\r\n' % (self._host, self._port)
		headers += 'Sec-WebSocket-Origin: %s%s:%d%s\r\n' % (self._scheme, self._host, self._port, self._baseUrl)
		headers += 'Sec-WebSocket-Key: %s\r\n' % self.__wsKey
		headers += 'Sec-WebSocket-Version: %d\r\n' % self.__wsVersion

		self.sendLine(str(headers))

	def _websocketHandshake(self):
		self.__wsHandshakeDone = True

	def lineReceived(self, line):
		line = line.rstrip()
		#logger.debug2("lineReceived: %s" % line)
		if not self.__wsHandshakeDone:
			line = line.strip()
			if line:
				if line.startswith('HTTP/') and (line.find(' 101 ') != -1):
					return
				if (line.find(':') == -1):
					raise Exception(u"Bad header: %s" % line)
				(k, v) = line.split(':', 1)
				self.__headers[k.strip().lower()] = v.strip()
			else:
				self._websocketHandshake()
		else:
			MessageBusClient.lineReceived(self, line)

	def sendLine(self, line):
		if self.isWebsocketHandshakeDone():
			line = hybi10Encode(line)
		MessageBusClient.sendLine(self, line)

if (__name__ == '__main__'):
	import signal
	mb = None
	logger = Logger()
	logger.setConsoleLevel(LOG_DEBUG)
	logger.setConsoleColor(True)

	def signalHandler(signo, stackFrame):
		if not mb:
			return
		if signo in (signal.SIGHUP, signal.SIGINT):
			mb.stop()

	signal.signal(signal.SIGHUP, signalHandler)
	signal.signal(signal.SIGINT, signalHandler)

	if (len(sys.argv) > 1) and (sys.argv[1] == 'server'):
		mb = MessageBusServer()
	else:
		class PrintingMessageBusClient(MessageBusWebsocketClient):
		#class PrintingMessageBusClient(MessageBusClient):
			def objectEventReceived(self, object_type, ident, operation):
				print u"%s %s %s" % (object_type, ident, operation)

			def initialized(self):
				MessageBusClient.initialized(self)
				self._register()

			def _register(self):
				self.registerForObjectEvents(object_types = ['OpsiClient'], operations = ['updated', 'created'])

		mb = PrintingMessageBusClient(url = 'https://192.168.1.14:4447/omb')
	mb.start()
	while not mb.isStopping():
		time.sleep(1)
	mb.join()





