# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import io
import pytest
import logging
import re
import time
import threading
import asyncio
import random
from contextlib import contextmanager

from opsicommon.logging import (logger, handle_log_exception, secret_filter,
			ContextSecretFormatter, log_context, set_format, init_logging)

try:
	from OPSI.Logger import Logger as LegacyLogger
except ImportError:
	LegacyLogger = None

@contextmanager
@pytest.fixture
def log_stream():
	stream = io.StringIO()
	handler = logging.StreamHandler(stream)
	try:
		logging.root.addHandler(handler)
		yield stream
	finally:
		logging.root.removeHandler(handler)

def test_levels(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
		set_format(stderr_format="%(message)s")
		expected = ""
		for level in (
			"secret", "confidential", "trace", "debug2", "debug",
			"info", "notice", "warning", "error", "critical", "comment"
		):
			func = getattr(logger, level)
			msg = f"logline {level}"
			func(msg)
			expected += f"{msg}\n"
	
		stream.seek(0)
		assert stream.read().find(expected) >= 0		# not == as other instances might also log

def test_log_exception_handler():
	log_record = logging.LogRecord(name=None, level=logging.ERROR, pathname=None, lineno=1, msg="t", args=None, exc_info=None)
	handle_log_exception(exc=Exception(), record=log_record, log=True)
	handle_log_exception(exc=Exception(), record=None, log=False)

def test_secret_formatter_attr():
	log_record = logging.LogRecord(name=None, level=logging.ERROR, pathname=None, lineno=1, msg="t", args=None, exc_info=None)
	sf = ContextSecretFormatter(logging.Formatter())
	sf.format(log_record)

def test_secret_filter(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
		set_format(stderr_format="[%(asctime)s.%(msecs)03d] %(message)s")

		secret_filter.set_min_length(7)	
		secret_filter.add_secrets("PASSWORD", "2SHORT", "SECRETSTRING")
		logger.info("line 1")
		logger.info("line 2 PASSWORD")
		logger.info("line 3 2SHORT")
		logger.secret("line 4 SECRETSTRING")
		stream.seek(0)
		log = stream.read()
		assert "line 1\n" in log
		assert "line 2 PASSWORD\n" not in log
		assert "line 3 2SHORT\n" in log
		assert "line 4 SECRETSTRING\n" in log

		secret_filter.clear_secrets()
		logger.info("line 5 PASSWORD")
		stream.seek(0)
		log = stream.read()
		assert "line 5 PASSWORD\n" in log

		stream.seek(0)
		stream.truncate()
		secret_filter.add_secrets("SECRETSTRING1", "SECRETSTRING2", "SECRETSTRING3")
		secret_filter.remove_secrets("SECRETSTRING2")
		logger.info("SECRETSTRING1 SECRETSTRING2 SECRETSTRING3")
		stream.seek(0)
		log = stream.read()
		assert "SECRETSTRING1" not in log
		assert "SECRETSTRING2" in log
		assert "SECRETSTRING3" not in log



@pytest.mark.skipif(not LegacyLogger, reason="OPSI.Logger not available.")
def test_legacy_logger(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)

		legacy_logger = LegacyLogger()
		assert legacy_logger == logger
		# This method does nothing
		legacy_logger.setLogFile("/tmp/test.log")
		# This method does nothing
		legacy_logger.setLogFormat("xy")

		secret_filter.set_min_length(7)
		legacy_logger.setConfidentialStrings(["SECRETSTRING1", "SECRETSTRING2"])
		legacy_logger.addConfidentialString("SECRETSTRING3")
		legacy_logger.info("SECRETSTRING1 SECRETSTRING2 SECRETSTRING3")

		stream.seek(0)
		log = stream.read()
		assert "SECRETSTRING1" not in log
		assert "SECRETSTRING2" not in log
		assert "SECRETSTRING3" not in log

		legacy_logger.logException(Exception("LOG_EXCEPTION"), logLevel=logging.CRITICAL)
		stream.seek(0)
		log = stream.read()
		assert "LOG_EXCEPTION" in log

@pytest.mark.skipif(not LegacyLogger, reason="OPSI.Logger not available.")
def test_legacy_logger_file(log_stream):
	with log_stream as stream:
		logger.setLevel(logging.SECRET)

		legacy_logger = LegacyLogger("/tmp/test.log")
		assert legacy_logger == logger
		legacy_logger.info("test should appear")

		stream.seek(0)
		log = stream.read()
		assert "test should appear" in log

	with open("/tmp/test.log") as logfile:
		content = logfile.read()
		assert "test should appear" in content

@pytest.mark.skipif(not LegacyLogger, reason="OPSI.Logger not available.")
def test_legacy_logger_calls(log_stream):
	with log_stream as stream:
		logger.setLevel(logging.NONE)

		legacy_logger = LegacyLogger()
		legacy_logger.getStderr()
		legacy_logger.getStdout()
		legacy_logger.setConfidentialStrings(["topsecret"])
		legacy_logger.addConfidentialString("evenmoresecret")
		legacy_logger.setLogFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setConsoleFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setComponentName("name", currentThread=False, object=None)
		legacy_logger.logToStdout(None)
		legacy_logger.setSyslogFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setFileFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setUniventionFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setMessageSubjectFormat("%s some format %s", currentThread=False, object=None)
		legacy_logger.setUniventionLogger(None)
		legacy_logger.setUniventionClass(None)
		legacy_logger.getMessageSubject()
		legacy_logger.setColor(True)
		legacy_logger.setFileColor(True)
		legacy_logger.setConsoleColor(True)
		legacy_logger.setSyslogLevel(0)
		legacy_logger.setMessageSubjectLevel(0)
		legacy_logger.setConsoleLevel(0)
		legacy_logger.getConsoleLevel()
		legacy_logger.getFileLevel()
		legacy_logger.getLogFile(currentThread=False, object=None)
		legacy_logger.setLogFile("logfile.log", currentThread=False, object=None)
		legacy_logger.linkLogFile("logfile", currentThread=False, object=None)
		legacy_logger.setFileLevel(0)
		legacy_logger.exit(object=None)
		legacy_logger._setThreadConfig(None, None)
		legacy_logger._getThreadConfig(key=None)
		legacy_logger._setObjectConfig(None, None, None)
		legacy_logger._getObjectConfig(None, key=None)
		legacy_logger.logException(None)
		legacy_logger.logFailure(None)
		legacy_logger.logTraceback(None)
		legacy_logger.logWarnings()
		legacy_logger.startTwistedLogging()
		legacy_logger.confidential("mymessage %s", "fill-value")
		legacy_logger.debug3("mymessage %s", "fill-value")
		legacy_logger.debug2("mymessage %s", "fill-value")
		legacy_logger.debug("mymessage %s", "fill-value")
		legacy_logger.info("mymessage %s", "fill-value")
		legacy_logger.msg("mymessage %s", "fill-value")
		legacy_logger.notice("mymessage %s", "fill-value")
		legacy_logger.warning("mymessage %s", "fill-value")
		legacy_logger.error("mymessage %s", "fill-value")
		legacy_logger.err("mymessage %s", "fill-value")
		legacy_logger.critical("mymessage %s", "fill-value")
		legacy_logger.essential("mymessage %s", "fill-value")
		legacy_logger.comment("mymessage %s", "fill-value")
		legacy_logger.log(3, "text %s", raiseException=False, formatArgs=["some format arg"], formatKwargs={})

		stream.seek(0)
		log = stream.read()
		assert log.count("fill-value") == 13

def test_context(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
		set_format(stderr_format="%(log_color)s[%(opsilevel)d] [%(asctime)s.%(msecs)03d]%(reset)s [%(contextstring)s] %(message)s   (%(filename)s:%(lineno)d)")

		logger.info("before setting context")
		with log_context({'whoami' : "first-context"}):
			logger.warning("lorem ipsum")
		with log_context({'whoami' : "second-context"}):
			logger.error("dolor sit amet")
		stream.seek(0)
		log = stream.read()
		assert "first-context" in log
		assert "second-context" in log

def test_context_threads(log_stream):
	def common_work():
		time.sleep(0.2)
		logger.info("common_work")
		time.sleep(0.2)

	class Main():
		def run(self):
			AsyncMain().start()
			for _ in range(5):		#perform 5 iterations
				ts = []
				for i in range(2):
					t = MyModule(client=f"Client-{i}")
					ts.append(t)
					t.start()
				for t in ts:
					t.join()
				time.sleep(1)

	class AsyncMain(threading.Thread):
		def __init__(self):
			super().__init__()
			self._should_stop = False
		
		def stop(self):
			self._should_stop = True
		
		def run(self):
			loop = asyncio.new_event_loop()
			loop.run_until_complete(self.arun())
			loop.close()
		
		async def handle_client(self, client: str):
			with log_context({'whoami' : "handler for " + str(client)}):
				logger.essential("handling client %s", client)
				seconds = random.random() * 1
				await asyncio.sleep(seconds)
				logger.essential("client %s handled after %0.3f seconds", client, seconds)

		async def arun(self):
			while not self._should_stop:
				tasks = []
				for i in range(2):
					tasks.append(self.handle_client(client=f"Client-{i}"))
				await asyncio.gather(*tasks)
				await asyncio.sleep(1)

	class MyModule(threading.Thread):
		def __init__(self, client: str):
			super().__init__()
			self.client = client
			logger.essential("initializing client: %s", client)

		def run(self):
			with log_context({'whoami' : "module " + str(self.client)}):
				logger.essential("MyModule.run")
				common_work()

	#init_logging(stderr_level=logging.INFO)
	set_format(stderr_format="%(contextstring)s %(message)s")
	with log_context({'whoami' : "MAIN"}):
		with log_stream as stream:
			m = Main()
			try:
				m.run()
			except KeyboardInterrupt:
				pass
			for t in threading.enumerate():
				if hasattr(t, "stop"):
					t.stop()
					t.join()
			stream.seek(0)

			log = stream.read()
			print(log)
			assert re.search(r"module Client-1.*MyModule.run", log) is not None
			# to check for corrent handling of async contexti when eventloop is not running in main thread
			assert re.search(r"handler for client Client-0.*handling client Client-1", log) is None
