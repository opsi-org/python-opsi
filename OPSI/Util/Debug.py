
from OPSI.Logger import Logger
logger = Logger()

from OPSI.Backend.BackendManager import BackendAccessControl

from zope.interface import implements
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword
from twisted.cred.error import UnauthorizedLogin

from twisted.internet import defer
from twisted.python import failure

from twisted.conch.manhole import ColoredManhole
from twisted.conch.insults import insults
from twisted.conch.telnet import TelnetTransport, TelnetBootstrapProtocol
from twisted.conch.manhole_ssh import ConchFactory, TerminalRealm

from twisted.internet import protocol
from twisted.cred import portal
from twisted.cred import checkers
from twisted.internet import reactor

class OpsiCredentialChecker(object):
	credentialInterfaces = (IUsernamePassword,)
	implements(ICredentialsChecker)
	
	def __init__(self, backend):
		self.backend = backend

	def requestAvatarId(self, credentials):
		
		try:
			auth = BackendAccessControl(backend=self.backend, username=credentials.username, password=credentials.password)
		except:
			return failure.Failure()
		
		if auth.authenticated:
			return defer.succeed(credentials.username)
		else:
			return defer.fail(UnauthorizedLogin("invalid credentials."))
		
class DebugShell(object):
	
	def __init__(self, object, backend, namespace=globals(), port=6222, reactor=reactor):
		self.object = object
		self.backend = backend
		self.namespace = namespace
		self.sshPort=port

		self.reactor=reactor
		self.checker = OpsiCredentialChecker(self.backend)

		self._sshConnection = None


	def getRealm(self):
		
		realm = TerminalRealm()
		realm.chainedProtocolFactory.protocolFactory = lambda x: ColoredManhole(namespace=self.namespace)
		return realm

	def open(self):
		
		rlm = self.getRealm()
		
		f = ConchFactory(portal.Portal(rlm, [self.checker]))
		self._sshConnection = self.reactor.listenTCP(self.sshPort, f)
	
	def close(self):
		self._sshConnection.stopListening()