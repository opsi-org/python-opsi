from socket import socket
from httplib import HTTPConnection

class DummySocket(object):

	def __init__(self, *args):
		self._sock = socket(*args)
		
	
	def __getattr__(self, name):
		return getattr(self._sock, name)
		
	
	def sendto(self, *args, **kwargs):
		return True

def dummy_connect_http(self, connectTimeout=0):
	return None

class DummyHttpConnection(object):
	def __init__(self, *args):
		self.con = HTTPConnection(*args)

	def __getattr__(self, name):
		return getattr(self.con, name)
	
	def connect(self, *args):
		self.con.sock = DummySocket(*args)
		
	def send(self, *args):
		return True
	
	def getresponse(self, *args):
		class DummyHTTPResponse(object):
			def read(self):
				return '{' \
						'"id": 1,'\
						'"result": [],'\
						'"error": null'\
					'}'
			def getheader(self, *args):
				return "I am a fake header!"
			
		return DummyHTTPResponse()
	
	def endheaders(self, *args):
		return True
	
	def putrequest(self, *args):
		return True
	
	def putheader(self, *args):
		return True