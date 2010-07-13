

import time, threading

from OPSI.Util.ThreadPool import *
from opsidevtools.unittest.lib.unittest2.case import TestCase

class ThreadPoolTestCase(TestCase):
	
	def setUp(self):
		self.pool = ThreadPool(autostart=False)
		self.pool.start()
		
	def test_WorkerCreation(self):
		self.pool.adjustSize(min=10)
		self.assertEqual(10, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" %(10, len(self.pool.worker)))

	def test_stopPool(self):
		self.pool.adjustSize(min=10, max=11)
		self.pool.stop()
		
		for i in range(5):
			time.sleep(1)
		
		self.assertEqual(0, len(self.pool.worker), "Expected %s worker to be in pool, but found %s" %(0, len(self.pool.worker)))
		self.assertFalse(self.pool.started, "Expected pool to have stopped, but it hasn't")
			
	def test_workerCallback(self):
		self.pool.adjustSize(1,2)
		
		result = []
		def assertCallback(success, returned, errors):
			result.append(success)
			result.append(returned)
			result.append(errors)


		self.pool.addJob(function=(lambda: 'test'), callback=assertCallback)
		
		#give thread time to finish
		time.sleep(1)
		
		self.assertTrue(result[0], "Expected callback success to be 'True', but got %s"%result[0])
		self.assertEqual(result[1], 'test', "Expected callback result to be 'test', but got %s"%result[1])
		self.assertIsNone(result[2], "Expected function to run successfully, but got error %s"% result[2])
		
		
	def test_workerCallbackWithException(self):
		self.pool.adjustSize(1,2)
		
		result = []
		def assertCallback(success, returned, errors):
			result.append(success)
			result.append(returned)
			result.append(errors)


		def raiseError():
			raise Exception("TestException")

		self.pool.addJob(function=raiseError, callback=assertCallback)
		
		#give thread time to finish
		time.sleep(1)
		
		self.assertFalse(result[0], "Expected callback success to be 'False', but got %s"%result[0])
		self.assertIsNone(result[1], "Expected callback to return no result, but got %s"%result[1])
		self.assertIsNotNone(result[2], "Expected function to run successfully, but got error %s"% result[2])

	def test_invalidThreadPoolSize(self):
		try:
			self.pool.adjustSize(2,1)
			self.fail("ThreadPool has an invalid size, but no exception was raised.")
		except ThreadPoolException, e:
			return
		except Exception, e:
			self.fail(e)
			
	def test_adjustPoolSize(self):
		self.pool.adjustSize(min=1,max=2)
		self.pool.adjustSize(min=5,max=10)
		
		self.assertEqual(5,self.pool.min, "Expected minimal pool size to be %s, but git %s." % (5 , self.pool.min))
		self.assertEqual(10,self.pool.max, "Expected maximum pool size to be %s, but git %s." % (10 , self.pool.max))
		
		self.assertIn(len(self.pool.worker), range(5,11), "Expected between 5 and 10 worker to be in pool, but found %s" %(len(self.pool.worker)))
	
	def test_floodPool(self):
		self.pool.adjustSize(1,2)
		
		def waitJob():
			for i in range(10):
				time.sleep(1)
			
		for i in range(5):
			self.pool.addJob(waitJob)
			
		self.assertEquals(2, len(self.pool.worker), "Expected %s worker in pool, but got %s" %(2, len(self.pool.worker)))
		self.assertGreater(self.pool.queue.unfinished_tasks, len(self.pool.worker), "Expected more tasks in Queue than workers in pool, but got %s tasks and %s worker" % (self.pool.queue.unfinished_tasks, len(self.pool.worker)))


	def test_globalPool(self):
		from OPSI.Util.ThreadPool import Pool
		self.assertTrue(isinstance(Pool, ThreadPool), "Expected %s to be a ThreadPool instance." % Pool)

	def test_threadFinish(self):
		pool = self.pool
		numThreads = threading.activeCount() - len(self.pool.worker)
		
		def sleepCounter(int):
			for i in range(15):
				print "I'm job %s and i'm alive" %int
				time.sleep(1)
			print "Job %s finished." %int
			print int
		
		
		for i in range(5):
			pool.addJob(None) #sleepCounter(i))
		pool.stop()
		
		for i in range(5):
			time.sleep(1)
		self.assertEqual(threading.activeCount(), numThreads, "Expected only %s thread to be alive, but got %s"% (numThreads, threading.activeCount() ))
	def tearDown(self):
		self.pool.stop()
