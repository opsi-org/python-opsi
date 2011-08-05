import os, pwd, grp, zlib


from OPSI.Backend import JSONRPC
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.JSONRPC import JSONRPCBackend, json
from OPSI.Backend.Backend import ExtendedConfigDataBackend

from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import FileBackendFixture, SQLiteBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase

import OPSI

from OPSI.Object import *
from OPSI.Util.HTTP import HTTPResponse
from OPSI.Util import deserialize, toJson
from OPSI.Types import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin


class MockResponse(object):
	
	def __init__(self, data):
		self.data = data
		
	def getheader(self, header, default=''):
		return default
	
	def setheader(self, header, value):
		pass
	
class JSONRPCTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    #NonObjectMethodsMixin,
		    #InventoryObjectMethodMixin,
		    #LicenseManagementObjectsMixin,
		    #MultithreadingMixin
		):
	
	backendBackend = None
	
	def _mock_urlopen(self, method, url, body=None, headers={}, retry=True, redirect=True, assert_same_host=True, firstTryTime=None):

		if 'gzip' in headers['content-type']:
			body = zlib.decompress(body)
		d = json.JSONDecoder().decode(body)
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
			method = getattr(self.dataBackend, d['method'])
			if method:
				data = method(*args, **kwargs)
				result = {"id": 1, "result": [], "error": None}
				if data is not None:
					result["result"] = data
				try:
					jsonstr = toJson(result)
				except Exception, e:
					raise e
				return MockResponse(jsonstr)

		except Exception, e:
			raise e
	
	
	def setUp(self):
		super(JSONRPCTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		
		self.patch(OPSI.Util.HTTP.HTTPConnectionPool, "urlopen", self._mock_urlopen)
		self.patch(OPSI.Util.HTTP.HTTPSConnectionPool, "urlopen", self._mock_urlopen)
		
		self.fb = self.useFixture(FileBackendFixture())
		self.dataBackend = self.fb.backend
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, False))
		
		self.backend = JSONRPCBackend(username = 'root', password = 'linux123', address = 'localhost')
		self.addCleanup(self.backend.backend_exit)

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)
