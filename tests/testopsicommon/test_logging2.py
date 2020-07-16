# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import io
import pytest
import logging
import requests

from contextlib import contextmanager

import opsicommon.logging
from opsicommon.logging import logger, LOG_ERROR

MY_FORMAT = "%(log_color)s[%(opsilevel)d] [%(asctime)s.%(msecs)03d]%(reset)s [%(contextstring)s] %(message)s"
OTHER_FORMAT = "[%(opsilevel)d] [%(asctime)s.%(msecs)03d] [%(contextstring)s] %(message)s   (%(filename)s:%(lineno)d)"

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

def test_simple_colored(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format(MY_FORMAT)
		with opsicommon.logging.log_context({'firstcontext' : 'asdf', 'secondcontext' : 'jkl'}):
			logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "asdf" in log and "jkl" in log

def test_simple_plain(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format(OTHER_FORMAT)
		with opsicommon.logging.log_context({'firstcontext' : 'asdf', 'secondcontext' : 'jkl'}):
			logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "asdf" in log and "jkl" in log

def test_set_context(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format(MY_FORMAT)
		opsicommon.logging.set_context({'firstcontext' : 'asdf', 'secondcontext' : 'jkl'})
		logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "asdf" in log and "jkl" in log
		stream.seek(0)
		stream.truncate()

		opsicommon.logging.set_context({'firstcontext' : 'asdf'})
		logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "asdf" in log and "jkl" not in log

		stream.seek(0)
		stream.truncate()
		opsicommon.logging.set_context({})
		logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "asdf" not in log

		stream.seek(0)
		stream.truncate()
		opsicommon.logging.set_context("suddenly a string")
		logger.error("test message")
		stream.seek(0)
		log = stream.read()
		assert "suddenly a string" not in log	# must be given as dictionary

def test_foreign_logs(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format("%(message)s")
		logger.error("message before request")

		requests.get("http://www.uib.de")

		logger.error("message after request")
		stream.seek(0)
		log = stream.read()
		assert "www.uib.de" in log

def test_filter(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format("%(message)s")
		opsicommon.logging.set_filter({"testkey" : ["t1", "t3"]})
		with opsicommon.logging.log_context({"testkey" : "t1"}):
			logger.warning("test that should appear")
		with opsicommon.logging.log_context({"testkey" : "t2"}):
			logger.warning("test that should not appear")
		stream.seek(0)
		log = stream.read()
		assert "test that should appear" in log
		assert "test that should not appear" not in log

def test_filter_from_string(log_stream):
	with log_stream as stream:
		opsicommon.logging.set_format("%(message)s")
		# as one string (like --log-filter "")
		opsicommon.logging.set_filter_from_string("testkey = t1 , t3 ; alsotest = a1")
		with opsicommon.logging.log_context({"testkey" : "t1", "alsotest" : "a1"}):
			logger.warning("test that should appear")
		with opsicommon.logging.log_context({"testkey" : "t2", "alsotest" : "a1"}):
			logger.warning("test that should not appear")
		with opsicommon.logging.log_context({"testkey" : "t3", "alsotest" : "a2"}):
			logger.warning("test that should not appear")

		# as list of strings (like --log-filter "" --log-filter "")
		opsicommon.logging.set_filter_from_string(["testkey = t1 , t3", "alsotest = a1"])
		with opsicommon.logging.log_context({"testkey" : "t1", "alsotest" : "a1"}):
			logger.warning("test that should also appear")
		with opsicommon.logging.log_context({"testkey" : "t2", "alsotest" : "a1"}):
			logger.warning("test that should not appear")
		with opsicommon.logging.log_context({"testkey" : "t3", "alsotest" : "a2"}):
			logger.warning("test that should not appear")

		stream.seek(0)
		log = stream.read()
		opsicommon.logging.set_filter(None)
		assert "test that should appear" in log
		assert "test that should also appear" in log
		assert "test that should not appear" not in log
		
def test_log_devel(log_stream):
	with log_stream as stream:
		logger.setLevel(LOG_ERROR)
		logger.warning("test that should not appear")
		logger.devel("test that should appear")
		logger.debug("test that should not appear")

		stream.seek(0)
		log = stream.read()
		assert "test that should appear" in log
		assert "test that should not appear" not in log
