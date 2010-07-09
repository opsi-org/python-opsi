

import time

from OPSI.Util.ThreadPool import ThreadPool, ThreadPoolException
from opsidevtools.unittest.lib.unittest2.case import TestCase

class ThreadPoolTestCase(TestCase):
	
	def setUp(self):
		pass
	
	def test_WorkerCreation(self):
		pool = ThreadPool(min=10)
		self.assertEqual(10, len(pool.worker), "Expected %s worker to be in pool, but found %s" %(10, len(pool.worker)))
	
	def test_stopPool(self):
		pool = ThreadPool(min=10)
		pool.stop()
		
		self.assertEqual(0, len(pool.worker), "Expected %s worker to be in pool, but found %s" %(0, len(pool.worker)))
		self.assertFalse(pool.started, "Expected pool to have stopped, but it hasn't")
			
	def test_workerCallback(self):
		pool = ThreadPool(0,1)
		
		result = []
		def assertCallback(success, returned, errors):
			result.append(success)
			result.append(returned)
			result.append(errors)


		pool.addJob(function=(lambda: 'test'), callback=assertCallback)
		
		#give thread time to finish
		time.sleep(1)
		
		self.assertTrue(result[0], "Expected callback success to be 'True', but got %s"%result[0])
		self.assertEqual(result[1], 'test', "Expected callback result to be 'test', but got %s"%result[1])
		self.assertIsNone(result[2], "Expected function to run successfully, but got error %s"% result[2])
		
		
	def test_workerCallbackWithException(self):
		pool = ThreadPool(0,1)
		
		result = []
		def assertCallback(success, returned, errors):
			result.append(success)
			result.append(returned)
			result.append(errors)


		def raiseError():
			raise Exception("TestException")

		pool.addJob(function=raiseError, callback=assertCallback)
		
		#give thread time to finish
		time.sleep(1)
		
		self.assertFalse(result[0], "Expected callback success to be 'False', but got %s"%result[0])
		self.assertIsNone(result[1], "Expected callback to return no result, but got %s"%result[1])
		self.assertIsNotNone(result[2], "Expected function to run successfully, but got error %s"% result[2])

	def test_invalidThreadPoolSize(self):
		try:
			pool = ThreadPool(2,1)
			self.fail("ThreadPool has an invalid size, but no exception was raised.")
		except ThreadPoolException, e:
			return
		except Exception, e:
			self.fail(e)
			
	def test_adjustPoolSize(self):
		pool = ThreadPool(1,2)
		pool.adjustSize(5,10)
		
		self.assertEqual(5,pool.min, "Expected minimal pool size to be %s, but git %s." % (5 , pool.min))
		self.assertEqual(10,pool.max, "Expected maximum pool size to be %s, but git %s." % (10 , pool.max))
		
		self.assertEqual(5, len(pool.worker), "Expected %s worker to be in pool, but found %s" %(10, len(pool.worker)))
	
	def test_floodPool(self):
		pool = ThreadPool(1,2)
		
		def waitJob():
			time.sleep(10)
			
		for i in range(5):
			pool.addJob(waitJob)
			
		self.assertEquals(2, len(pool.worker), "Expected %s worker in pool, but got %s" %(2, len(pool.worker)))
		self.assertGreater(pool.queue.unfinished_tasks, len(pool.worker), "Expected more tasks in Queue than workers in pool, but got %s tasks and %s worker" % (pool.queue.unfinished_tasks, len(pool.worker)))