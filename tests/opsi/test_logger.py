from testtools import TestCase
from fixtures import Fixture

import sys, warnings
try:
	from io import BytesIO as StringIO
except ImportError:
	from StringIO import StringIO

from OPSI.Logger import LoggerImplementation, LOG_WARNING, LOG_ERROR, LOG_DEBUG

class LoggerTestCase(TestCase):
	
	def setUp(self):
		super(LoggerTestCase, self).setUp()
		self.logger = LoggerImplementation()
		
	def test_logWarningsModule(self):
		
		buffer = StringIO()
		
		self.patch(sys, "stdout", buffer)
		self.patch(sys, "stderr", buffer)
		
		self.logger.setConsoleLevel(LOG_WARNING)
		self.logger.setLogFormat('[%l] %M')
		self.logger.logWarnings()
		warnings.warn("message", DeprecationWarning, stacklevel=2)

		value = buffer.getvalue()
		self.assertNotEquals("", value)
		self.assertTrue(value.startswith("[%d]" % LOG_WARNING))
		self.assertTrue(value.find("DeprecationWarning: message"))

	def test_logTwisted(self):

		err = StringIO()
		
		self.patch(sys, "stdout", err)
		self.patch(sys, "stderr", err)
		
		self.logger.setConsoleLevel(LOG_DEBUG)
		self.logger.setLogFormat('[%l] %M')
		self.logger.startTwistedLogging()
		
		try:
			from twisted.python import log
			
			value = err.getvalue()
			self.assertNotEquals("", value)
			self.assertEquals("[%d] [twisted] Log opened.\n" % LOG_DEBUG, value)
			err.seek(0)
			err.truncate(0)
			
			log.msg("message")
			
			value = err.getvalue()
			self.assertNotEquals("", value)
			self.assertEquals("[%d] [twisted] message\n" % LOG_DEBUG, value)
			err.seek(0)
			err.truncate(0)
			
			log.err("message")
			
			value = err.getvalue()
			#self.assertNotEquals("", value)
			self.assertEquals("[%d] [twisted] 'message'\n" % LOG_ERROR, value)
			err.seek(0)
			err.truncate(0)
			
		except ImportError:
			self.skipTest("Could not import twisted log module.")
		

		
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)