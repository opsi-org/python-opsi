
import time,sys
from MySQLdb.constants.ER import DUP_ENTRY
from MySQLdb import IntegrityError

from OPSI import unittest2

class MultithreadingMixin(object):
	
	def test_Multithreading(self):
		
		import threading
		
		class MultiThreadTest(threading.Thread):
			def __init__(self, backendTest):
				threading.Thread.__init__(self)
				self._backendTest = backendTest
				self.exitCode = 0
				self.errorMessage = None
			def run(self):
				try:
					time.sleep(1)
					self._backendTest.backend.host_getObjects()
					self._backendTest.backend.host_deleteObjects(self._backendTest.client1)
					self._backendTest.backend.host_getObjects()
					self._backendTest.backend.host_deleteObjects(self._backendTest.client2)
					self._backendTest.backend.host_createObjects(self._backendTest.client2)
					self._backendTest.backend.host_createObjects(self._backendTest.client1)
					self._backendTest.backend.host_getObjects()
					self._backendTest.backend.host_createObjects(self._backendTest.client1)
					self._backendTest.backend.host_deleteObjects(self._backendTest.client2)
					self._backendTest.backend.host_createObjects(self._backendTest.client1)
					self._backendTest.backend.host_getObjects()
				except IntegrityError,e:
					if e[0] != DUP_ENTRY:
						self.errorMessage = e
						self.exitCode = 1
				except Exception, e:
					self.errorMessage = e
					self.exitCode = 1
					#sys.exit()
		try:
			mtts = []
			for i in range(50):
				mtt = MultiThreadTest(self)
				mtts.append(mtt)
				mtt.start()
			for mtt in mtts:
				mtt.join()
			self.backend.host_createObjects(self.client1)
			while len(mtts) > 0:
				mtt = mtts.pop(0)
				if not mtt.isAlive():
					self.assertEqual(mtt.exitCode, 0, u"Mutlithreading test failed: Exit Code %s: %s"% (mtt.exitCode, mtt.errorMessage))
				else:
					mtts.append(mtt)
		except Exception, e:
			self.fail(str(e))