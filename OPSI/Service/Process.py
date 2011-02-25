

import sys, os, pwd, signal, re, os
from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed, fail, DeferredList
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessExitedAlready
from twisted.python import reflect
from twisted.internet.task import LoopingCall

from OPSI.Util.AMP import OpsiProcessProtocolFactory, OpsiProcessConnector

from OPSI.Logger import *
logger = Logger()

class SupervisionProtocol(ProcessProtocol):
	
	def __init__(self, daemon):
		self.daemon = daemon
		self.pid = None
		self.defer = None
		self.logRegex = re.compile('^\[([0-9])\]\s*(.*)')
		
	def connectionMade(self):
		self.pid = self.transport.pid
		
	def stop(self):
		if self.transport.pid:
			self.defer = Deferred()
			self.transport.signalProcess(signal.SIGTERM)
			reactor.callLater(15, self.kill)
			return self.defer
		return succeed(None)

	def kill(self):
		if self.transport.pid:
			logger.warning("Process %s did not stop cleanly, killing it." %self.transport.pid )
			self.transport.signalProcess(signal.SIGKILL)

	def errReceived(self, data):
		data = data.strip()
		match = self.logRegex.search(data)
		if match:
			try:
				logLevel = int(match.group(1))
				logMessage = match.group(2)
				logger.log(logLevel, '[worker %s] %s' % (self.pid, logMessage))
				return
			except Exception, e:
				logger.error(e)
		logger.warning(data)
		
	def processEnded(self, reason):
		if self.daemon.allowRestart:
			self.daemon.start()
		elif self.defer is not None:
			self.defer.callback(None)

class OpsiDaemon(object):

	script = None
	user = None
	allowRestart = True
	connector = OpsiProcessConnector

	def __init__(self, args = [], reactor=reactor):

		self._reactor = reactor
		self._connector = self.connector(self.getSocket())
		
		self._env = os.environ.copy()
		
		self._process = None
		self._args = args
		self._checkFailures = 0
		self._childFDs = None
		
		if os.getuid() == 0:
			if not self.user:
				raise RuntimeError("Subclass %s must specifie a daemon user if run as root." % self.script)

			passwd = pwd.getpwnam(self.user)
			self._uid = passwd.pw_uid
			self._gid = passwd.pw_gid
			self._env['USER'] = self.user
			self._env['HOME'] = passwd.pw_dir
		else:
			self._uid, self._gid = None, None

	def start(self):

		self._process = SupervisionProtocol(self)
		script = self.findScript()
		
		args = [script]

		args.extend([str(arg) for arg in self._args])
		
		self._reactor.spawnProcess(self._process, script, args=args,
					env=self._env, uid=self._uid, gid=self._gid, 
					childFDs=self._childFDs)
	def stop(self):
		if not self._process:
			d =  succeed(None)
		else:
			d = self._process.stop()

		return d

	def findScript(self):
		if self.script is None:
			raise RuntimeError("Subclass %s must provide an executable script." % self.script)

		dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
		script = os.path.join(dirname, self.script)
		if not os.path.exists(script) or not os.access(script, os.X_OK):
			raise RuntimeError("Script %s doesn't exist or is not executable." % script)
		return script

	def callRemote(self, method, *args, **kwargs):
		def failure(failure):
			logger.error(failure.getErrorMessage())
			logger.logTraceback(failure.getTracebackObject())
			return failure

		def disconnect(result):
			self._connector.disconnect()
			return result

		connection = self._connector.connect()
		connection.addCallback(lambda remote: getattr(remote, method)(*args, **kwargs))
		
		connection.addErrback(failure)
		connection.addBoth(disconnect)
		
		return connection

	def isRunning(self):
		# FIXME: why is this called out of loop?
		return self.callRemote("isRunning")

	def sendSignal(self, sig):
		def _sendSignal(s):
			self._process.transport.signalProcess(s)
		d = self.isRunning()
		d.addCallback(lambda x, s=sig: _sendSignal(s))
	
	
	def getSocket(self):
		return self.__class__.socket

def runOpsiService(serviceClass, configurationClass, reactorModule):
	import sys

	def probeReactor():
		from twisted.application.reactors import getReactorTypes, installReactor

		for r in getReactorTypes():
			if reactorModule == r.moduleName:
				installReactor(r.shortName)
				return

	#probeReactor()		#TODO: make this work

	from OPSI.Logger import Logger
	logger = Logger()
	logger.setConsoleLevel(LOG_WARNING)
	logger.setFileLevel(LOG_WARNING)
	logger.setLogFormat('[%l] %M (%F|%N)')
	
	from twisted.application.service import Application, Service
	from twisted.application.app import startApplication
	
	from twisted.internet import reactor
	from twisted.python import reflect, runtime
	
	config = reflect.namedAny(configurationClass)(sys.argv[1:-3])
	service = reflect.namedAny(serviceClass)(config)
	application = Application(service.__class__)
	service.setServiceParent(application)
	startApplication(application, False)

	reactor.run()


class OpsiPyDaemon(OpsiDaemon):
	
	MAIN = """\
import sys

from OPSI.Service.Process import runOpsiService

runOpsiService(sys.argv[-1],sys.argv[-2], sys.argv[-3])
"""
	
	script = sys.executable
	
	def __init__(self, socket, args = [], reactor=reactor):
		
		args.extend([reactor.__module__, reflect.qual(self.configurationClass), reflect.qual(self.serviceClass)])
		self.socket = socket
		
		OpsiDaemon.__init__(	self,
					args=["-c", self.MAIN] + args,
					reactor=reactor)
		
	def findScript(self):
		return sys.executable
	
	def getSocket(self):
		return self.socket







