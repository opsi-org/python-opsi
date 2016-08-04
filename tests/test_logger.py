#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing our logger.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import sys
import warnings
from contextlib import contextmanager
from io import BytesIO as StringIO

import OPSI.Logger
import pytest

from .helpers import cd, mock, workInTemporaryDirectory, showLogs


# Log level that will result in log output.
LOGGING_LEVELS = [
	OPSI.Logger.LOG_CONFIDENTIAL,
	OPSI.Logger.LOG_DEBUG2,
	OPSI.Logger.LOG_DEBUG,
	OPSI.Logger.LOG_INFO,
	OPSI.Logger.LOG_NOTICE,
	OPSI.Logger.LOG_WARNING,
	OPSI.Logger.LOG_ERROR,
	OPSI.Logger.LOG_CRITICAL,
	OPSI.Logger.LOG_ESSENTIAL,
	OPSI.Logger.LOG_COMMENT
]


@pytest.yield_fixture
def logger():
	logger = OPSI.Logger.LoggerImplementation()

	try:
		yield logger
	finally:
		logger.setConsoleLevel(OPSI.Logger.LOG_NONE)
		logger.setFileLevel(OPSI.Logger.LOG_NONE)


@contextmanager
def catchMessages():
	"Write messages to stdout / stdin into a virtual buffer."

	messageBuffer = StringIO()
	with mock.patch('OPSI.Logger.sys.stdin', messageBuffer):
		with mock.patch('OPSI.Logger.sys.stderr', messageBuffer):
			yield messageBuffer


def testLoggingMessage(logger):
	level = OPSI.Logger.LOG_CONFIDENTIAL
	logger.setConsoleLevel(level)

	with catchMessages() as messageBuffer:
		logger.log(level, "This is not a test!", raiseException=True)

		assert "This is not a test!" in messageBuffer.getvalue()


@pytest.mark.parametrize("logLevel", [OPSI.Logger.LOG_NONE] + LOGGING_LEVELS)
def testChangingConsoleLogLevel(logger, logLevel):
	logger.setConsoleLevel(logLevel)
	assert logLevel == logger.getConsoleLevel()


@pytest.mark.parametrize("logLevel", LOGGING_LEVELS)
def testLoggingUnicode(logger, logLevel):
	logger.setConsoleLevel(logLevel)

	with catchMessages() as messageBuffer:
		logger.log(logLevel, u"Heävy Metäl Ümläüts! Öy!", raiseException=True)

		# Currently this has to be suffice
		# TODO: better check for logged string.
		assert messageBuffer.getvalue()


def test_logTwisted(logger):
	log = pytest.importorskip("twisted.python.log")

	logger.setConsoleLevel(OPSI.Logger.LOG_DEBUG)
	logger.setLogFormat('[%l] %M')

	with catchMessages() as err:
		logger.startTwistedLogging()

		value = err.getvalue()
		assert "" != value
		assert value == "[{0:d}] [twisted] Log opened.\n".format(OPSI.Logger.LOG_DEBUG)
		err.seek(0)
		err.truncate(0)

		log.msg("message")
		value = err.getvalue()
		assert "" != value
		assert value == "[{0:d}] [twisted] message\n".format(OPSI.Logger.LOG_DEBUG)
		err.seek(0)
		err.truncate(0)

		log.err("message")
		value = err.getvalue()
		assert value == "[{0:d}] [twisted] 'message'\n".format(OPSI.Logger.LOG_ERROR)


def testPatchingShowwarnings(logger):
	originalWarningFunction = warnings.showwarning
	assert originalWarningFunction is warnings.showwarning

	try:
		logger.logWarnings()
		assert originalWarningFunction is not warnings.showwarning
	finally:
		# Making sure that the switched function is
		# resetted to it's default.
		warnings.showwarning = originalWarningFunction


def testLoggingFromWarningsModule(logger):
	logger.setConsoleLevel(OPSI.Logger.LOG_WARNING)
	logger.setLogFormat('[%l] %M')

	with catchMessages() as messageBuffer:
		try:
			logger.logWarnings()

			warnings.warn("usermessage")
			warnings.warn("another message", DeprecationWarning)
			warnings.warn("message", DeprecationWarning, stacklevel=2)
		finally:
			# Making sure that the switched function is
			# resetted to it's default.
			warnings.showwarning = OPSI.Logger._showwarning

		value = messageBuffer.getvalue()

	assert value.startswith("[{0:d}]".format(OPSI.Logger.LOG_WARNING))
	assert "UserWarning: usermessage" in value

	if sys.version_info < (2, 7):
		# Changed in version 2.7: DeprecationWarning is ignored by default.
		# Source: https://docs.python.org/2.7/library/warnings.html#warning-categories
		assert "DeprecationWarning: message" in value
		assert "DeprecationWarning: another message" in value


@pytest.mark.parametrize("message, logLevel", [
	("my password", OPSI.Logger.LOG_CONFIDENTIAL),
	("beepbeepbeepbeeeeeeeeeep", OPSI.Logger.LOG_DEBUG2),
	("Beep, beep.", OPSI.Logger.LOG_DEBUG),
	("The Stark Tower", OPSI.Logger.LOG_INFO),
	("Hulk not angry", OPSI.Logger.LOG_NOTICE),
	("Loki lifes!", OPSI.Logger.LOG_WARNING),
	("under 9000", OPSI.Logger.LOG_ERROR),
	("over 9000", OPSI.Logger.LOG_CRITICAL),
	("never miss", OPSI.Logger.LOG_ESSENTIAL),
	("my words blabla", OPSI.Logger.LOG_COMMENT),
])
def testLogLevelIsShownInOutput(logger, message, logLevel):
	logger.setConsoleLevel(logLevel)
	logger.setLogFormat('[%l] %M')

	with catchMessages() as messageBuffer:
		logger.log(logLevel, message)
		value = messageBuffer.getvalue()

	assert value.startswith("[{0:d}]".format(logLevel))
	assert message in value
	assert value.rstrip().endswith(message)


def testConfidentialStringsAreNotLogged(logger):
	secretWord = 'mySecr3tP4ssw0rd!'

	logger.addConfidentialString(secretWord)
	logger.setConsoleLevel(OPSI.Logger.LOG_DEBUG2)

	with catchMessages() as messageBuffer:
		logger.notice("Psst... {0}".format(secretWord))

		value = messageBuffer.getvalue()

	assert secretWord not in value
	assert "Psst... " in value
	assert "*** confidential ***" in value


def testConfidentialStringsCanNotBeEmpty(logger):
	with pytest.raises(ValueError):
		logger.addConfidentialString('')


def testLogFormatting(logger):
	logger.setConsoleLevel(OPSI.Logger.LOG_CONFIDENTIAL)
	logger.setLogFormat('[%l - %L] %F %M')

	with catchMessages() as messageBuffer:
		logger.debug("Chocolate Starfish")

		value = messageBuffer.getvalue()

	assert '[7 - debug] test_logger.py Chocolate Starfish', value.strip()


def testSettingConfidentialStrings(logger):
	confidential = ["Momente", "Wahnsinn"]
	logger.setConfidentialStrings(confidential)

	logger.setConsoleLevel(OPSI.Logger.LOG_DEBUG2)

	with catchMessages() as messageBuffer:
		logger.notice("Die Momente, die es wert sind, ziehen so schnell vorbei")
		logger.notice("So schnell, so weit")
		logger.notice("Der Wahnsinn folgt jetzt nicht mehr dem Asphalt")
		logger.notice("Du lässt ihn zurück")

		value = messageBuffer.getvalue()

	for word in confidential:
		assert word not in value
	assert "So schnell, so weit" in value


def testChangingDirectoriesDoesNotChangePathOfLog(logger):
	with workInTemporaryDirectory():
		logger.setLogFile('test.log')
		logger.setFileLevel(OPSI.Logger.LOG_DEBUG)
		logger.warning('abc')

		assert os.path.exists('test.log')

		os.mkdir('subdir')
		with cd('subdir'):
			assert not os.path.exists('test.log')
			logger.warning('def')
			assert not os.path.exists('test.log')


def testSettingLogPathToNone(logger):
	logger.setLogFile(None)


def testCallingLogMethods(logger):
	logger.confidential('test message')
	logger.debug2('test message')
	logger.debug('test message')
	logger.info('test message')
	logger.notice('test message')
	logger.warning('test message')
	logger.error('test message')
	logger.critical('test message')
	logger.essential('test message')
	logger.comment('test message')


def testLoggingTracebacks():
	with showLogs() as logger:
		with catchMessages() as messageBuffer:
			try:
				raise RuntimeError("Foooock")
			except Exception as e:
				logger.logException(e)

		values = messageBuffer.getvalue().split('\n')
		if not values[-1]:  # removing last, empty line
			values = values[:-1]

		print(repr(values))

		assert len(values) > 1
		assert "traceback" in values[0].lower()
		assert "line" in values[1].lower()
		assert "file" in values[1].lower()
		assert __file__ in values[1]
		assert "Foooock" in values[-1]
		assert '==>>> Fooo' in values[-1]  # startswith does not work because of colors...


def testLoggingTraceBacksFromInsideAFunction():

	def failyMcFailFace():
		raise RuntimeError("Something bad happened!")

	with showLogs() as logger:
		with catchMessages() as messageBuffer:
			try:
				failyMcFailFace()
			except Exception as e:
				logger.logException(e)

		values = messageBuffer.getvalue().split('\n')
		if not values[-1]:  # removing last, empty line
			values = values[:-1]

		print(repr(values))

		assert len(values) > 1
		assert "traceback" in values[0].lower()
		assert "line" in values[1].lower()
		assert "file" in values[1].lower()
		assert __file__ in values[1]
		assert failyMcFailFace.func_name in values[2]
		assert "Something bad happened" in values[-1]


def testLogTracebackCanFail():
	objectWithoutTraceback = object()
	with showLogs() as logger:
		with catchMessages() as messageBuffer:
			logger.logTraceback(objectWithoutTraceback)

	messages = messageBuffer.getvalue()

	print("Messages: {0!r}".format(messages))
	assert 'Failed to log traceback for' in messages
	assert repr(objectWithoutTraceback) in messages
	assert 'object has no attribute' in messages


@pytest.mark.parametrize("loglevel, function_name", [
	(OPSI.Logger.LOG_CONFIDENTIAL, 'confidential'),
	(OPSI.Logger.LOG_DEBUG2, 'debug2'),
	(OPSI.Logger.LOG_DEBUG, 'debug'),
	(OPSI.Logger.LOG_INFO, 'info'),
	(OPSI.Logger.LOG_NOTICE, 'notice'),
	(OPSI.Logger.LOG_WARNING, 'warning'),
	(OPSI.Logger.LOG_ERROR, 'error'),
	(OPSI.Logger.LOG_CRITICAL, 'critical'),
	(OPSI.Logger.LOG_ESSENTIAL, 'essential'),
	(OPSI.Logger.LOG_COMMENT, 'comment'),
])
def testLoggerDoesFormattingIfMessageWillGetLogged(loglevel, function_name):
	with showLogs(logLevel=loglevel) as logger:
		with catchMessages() as messageBuffer:
			logFunc = getattr(logger, function_name)
			logFunc('Backwards compatible text without formatting.')
			logFunc('This {0:.1f} must be shown {1}: {a}{b:>7}', 1, 'here', a='many', b='kwargs')

	messages = messageBuffer.getvalue()

	print("Messages: {0!r}".format(messages))
	assert 'This 1.0 must be shown here: many kwargs' in messages


@pytest.mark.parametrize("replacement", 'DTlLCFN')  # not: Message
@pytest.mark.parametrize("loglevel", [
	OPSI.Logger.LOG_DEBUG2,
	OPSI.Logger.LOG_DEBUG,
	OPSI.Logger.LOG_INFO,
	OPSI.Logger.LOG_NOTICE,
	OPSI.Logger.LOG_WARNING,
	OPSI.Logger.LOG_ERROR,
	OPSI.Logger.LOG_CRITICAL,
	OPSI.Logger.LOG_ESSENTIAL,
	OPSI.Logger.LOG_COMMENT,
])
def testLoggerDoesNotShowSecretWordBeginningWithCapitalisedF(loglevel, replacement):
	assert len(replacement) == 1
	secretWord = "{0}ooBar".format(replacement)
	assert secretWord.startswith(replacement)
	command = 'prog.exe -credentials "username%{0}"'.format(secretWord)

	with showLogs(logLevel=loglevel) as logger:
		logger.setLogFormat('%{formatter} %M'.format(formatter=replacement))
		logger.addConfidentialString(secretWord)

		with catchMessages() as messageBuffer:
			logger.log(loglevel, command)

	message = ''.join(messageBuffer.getvalue())
	assert message
	assert not message.startswith('%')

	print("Message: {0!r}".format(message))

	assert secretWord not in message
	assert secretWord[1:] not in message
