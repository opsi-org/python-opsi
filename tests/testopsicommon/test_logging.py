# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import io
import pytest
import logging

import time
import threading
import asyncio
from contextlib import contextmanager

from opsicommon.logging import logger, handle_log_exception, secret_filter, SecretFormatter

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
		logger.addHandler(handler)
		yield stream
	finally:
		logger.removeHandler(handler)

@pytest.fixture
def log_stream_handler():
	stream = io.StringIO()
	handler = logging.StreamHandler(stream)
	return (handler, stream)

def test_levels(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
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
		assert stream.read() == expected

def test_log_exception_handler():
	log_record = logging.LogRecord(name=None, level=logging.ERROR, pathname=None, lineno=1, msg="t", args=None, exc_info=None)
	handle_log_exception(exc=Exception(), record=log_record, log=True)
	handle_log_exception(exc=Exception(), record=None, log=False)

def test_secret_formatter_attr():
	log_record = logging.LogRecord(name=None, level=logging.ERROR, pathname=None, lineno=1, msg="t", args=None, exc_info=None)
	sf = SecretFormatter(logging.Formatter())
	sf.format(log_record)

def test_secret_filter(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
		logger.set_format("[%(asctime)s.%(msecs)03d] %(message)s", colored=False)

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

def test_context(log_stream):
	with log_stream as stream:
		#handler.setLevel(logging.SECRET)
		logger.setLevel(logging.SECRET)
		logger.set_format()

		logger.info("before setting context")
		logger.set_context("first-context")
		logger.warning("lorem ipsum")
		logger.set_context("second-context")
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
		
		async def handle_client(self, client: str):
			logger.set_context("handler for " + str(client))
			logger.info("handling client %s", client)

			seconds = random.random() * 1
			await asyncio.sleep(seconds)
			logger.info("client %s handled after %0.3f seconds", client, seconds)

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
			logger.warning("initializing client: %s", client)

		def run(self):
			logger.set_context("module " + str(self.client))
			logger.info("MyModule.run")
			common_work()

	logger.set_format("%(context)s %(message)s")
	logger.set_context("MAIN")
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
		assert "[module Client-1] MyModule.run" in log
		# to check for corrent handling of async contexti when eventloop is not running in main thread
		assert "[handler for client Client-0] handling client Client-1" not in log
