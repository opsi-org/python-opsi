import os, pwd, grp, json

from ConnectionHelper import *

from OPSI.Backend import JSONRPC
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Backend.File import FileBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Object import *
from OPSI.Util import deserialize, toJson
from OPSI.Types import *
from BackendTest import BackendTestCase
from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin

class DummyJSONRPCConnection(DummyHttpConnection):
	data = None

	def getresponse(self, *args):
		class RPCResult(object):
			def __init__(self, data = None):
				self.data = data
			def read(self):
				result = {"id": 1, "result": [], "error": None}
				if self.data is not None:
					result["result"] = self.data
				try:
					jsonstr = toJson(result)
				except Exception, e:
					raise e
				return jsonstr
			def getheader(self, *args):
				return "I am a fake header!"

		return RPCResult(self.data)
	def send(self, *args):
		d = json.JSONDecoder().decode(args[0])
		##### FIXME
		params = d["params"]
		args=[]
		kwargs={}
		
		if len(params) == 2:
			args.append(params[0])
			kwargs.update(params[1])
		elif len(params) == 1:
			if params[0].__class__ == "dict":
				kwargs.update(params[0])
			else:
				args.append(params[0])
		try:
			method = getattr(self.getBackend(), d['method'], None)
			if method:
				self.data = method(*args, **kwargs)
		except Exception, e:
			raise e
			#pass



class JSONRPCTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    #NonObjectMethodsMixin,
		    #InventoryObjectMethodMixin,
		    #LicenseManagementObjectsMixin,
		    MultithreadingMixin
		):
	
	backendBackend = None
	
	@classmethod
	def setUpClass(cls):
		JSONRPC.socket.socket = DummySocket
		JSONRPC.non_blocking_connect_http = dummy_connect_http
		JSONRPC.non_blocking_connect_https = dummy_connect_http
		JSONRPC.httplib.HTTPConnection = DummyJSONRPCConnection
		JSONRPC.httplib.HTTPSConnection = DummyJSONRPCConnection
		
	def createBackend(self):
		
		self.backendBackend = ExtendedConfigDataBackend(FileBackend(baseDir = u'/tmp/opsi-file-backend-test', hostKeyFile = u'/tmp/opsi-file-backend-test/pckeys'))
		self.backendBackend.backend_createBase()
		DummyJSONRPCConnection.getBackend = (lambda x: self.backendBackend)
		self.backend = JSONRPCBackend(username = 'root', password = 'linux123', address = 'localhost')
		
	def tearDown(self):
		self.backendBackend.backend_deleteBase()
		self.backend.backend_exit()

