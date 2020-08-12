# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2019 uib GmbH <info@uib.de>

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
opsi python library - Logger

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
import warnings
import logging

import opsicommon.logging
from opsicommon.logging import (logger,
	LOG_SECRET, LOG_CONFIDENTIAL, LOG_TRACE, LOG_DEBUG2, LOG_DEBUG,
	LOG_INFO, LOG_NOTICE, LOG_WARNING, LOG_WARN, LOG_ERROR, LOG_CRITICAL,
	LOG_ESSENTIAL, LOG_NONE, LOG_NOTSET, LOG_COMMENT
)

class Logger:
	pass

"""
Compatibility functions.

These functions realize the OPSI.Logger features utilizing
python logging methods.
"""
# Replace OPSI Logger
def opsi_logger_factory(logFile=None):
	warnings.warn(
		"OPSI.Logger.Logger is deprecated, use opsicommon.logging.logger instead.",
		DeprecationWarning
	)
	if logFile is not None:
		opsicommon.logging.logging_config(log_file=logFile)
	return logger
Logger = opsi_logger_factory

def getStderr():
	pass
logger.getStderr = getStderr

def getStdout():
	pass
logger.getStdout = getStdout

def setConfidentialStrings(strings):
	warnings.warn(
		"OPSI.Logger.setConfidentialStrings is deprecated, use secret_filter.clear_secrets,\
		secret_filter.add_secrets instead.", DeprecationWarning
	)
	opsicommon.logging.secret_filter.clear_secrets()
	opsicommon.logging.secret_filter.add_secrets(*strings)
logger.setConfidentialStrings = setConfidentialStrings

def addConfidentialString(string):
	warnings.warn(
		"OPSI.Logger.addConfidentialString is deprecated, use secret_filter.add_secrets instead.",
		DeprecationWarning
	)
	opsicommon.logging.secret_filter.add_secrets(string)
logger.addConfidentialString = addConfidentialString

def setLogFormat(logFormat, currentThread=False, object=None):
	warnings.warn(
		"OPSI.Logger.setLogFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
	pass
logger.setLogFormat = setLogFormat

def setConsoleFormat(format, currentThread=False, object=None):
	pass
logger.setConsoleFormat = setConsoleFormat

def setComponentName(componentName, currentThread=False, object=None):
	pass
logger.setComponentName = setComponentName

def logToStdout(stdout):
	pass
logger.logToStdout = logToStdout

def setSyslogFormat(format, currentThread=False, object=None):
	pass
logger.setSyslogFormat = setSyslogFormat

def setFileFormat(format, currentThread=False, object=None):
	pass
logger.setFileFormat = setFileFormat

def setUniventionFormat(format, currentThread=False, object=None):
	pass
logger.setUniventionFormat = setUniventionFormat

def setMessageSubjectFormat(format, currentThread=False, object=None):
	pass
logger.setMessageSubjectFormat = setMessageSubjectFormat

def setUniventionLogger(logger):
	pass
logger.setUniventionLogger = setUniventionLogger

def setUniventionClass(c):
	pass
logger.setUniventionClass = setUniventionClass

def getMessageSubject():
	pass
logger.getMessageSubject = getMessageSubject

def setColor(color):
	pass
logger.setColor = setColor

def setFileColor(color):
	pass
logger.setFileColor = setFileColor

def setConsoleColor(color):
	pass
logger.setConsoleColor = setConsoleColor

def setSyslogLevel(level=LOG_NONE):
	pass
logger.setSyslogLevel = setSyslogLevel

def setMessageSubjectLevel(level=LOG_NONE):
	pass
logger.setMessageSubjectLevel = setMessageSubjectLevel

def setConsoleLevel(logLevel, object=None):
	warnings.warn(
		"OPSI.Logger.setConsoleLevel is deprecated, instead modify the StreamHandler loglevel.",
		DeprecationWarning
	)
	opsicommon.logging.logging_config(stderr_level=logLevel)
logger.setConsoleLevel = setConsoleLevel

@staticmethod
def _sanitizeLogLevel(level):
	return level

def getConsoleLevel():
	pass
logger.getConsoleLevel = getConsoleLevel

def getFileLevel():
	pass
logger.getFileLevel = getFileLevel

def getLogFile(currentThread=False, object=None):
	pass
logger.getLogFile = getLogFile

def setLogFile(logFile, currentThread=False, object=None):
	warnings.warn(
		"OPSI.Logger.setLogFile is deprecated, instead add a FileHandler to logger.",
		DeprecationWarning
	)
	opsicommon.logging.logging_config(log_file=logFile)
logger.setLogFile = setLogFile

def linkLogFile(linkFile, currentThread=False, object=None):
	pass
logger.linkLogFile = linkLogFile

def setFileLevel(logLevel, object=None):
	warnings.warn(
		"OPSI.Logger.setFileLevel is deprecated, instead modify the FileHandler loglevel.",
		DeprecationWarning
	)
	opsicommon.logging.logging_config(file_level=logLevel)
logger.setFileLevel = setFileLevel

def exit(object=None):
	pass
logger.exit = exit

def _setThreadConfig(key, value):
	pass
logger._setThreadConfig = _setThreadConfig
 
def _getThreadConfig(key=None):
	pass
logger._getThreadConfig = _getThreadConfig

def _setObjectConfig(objectId, key, value):
	pass
logger._setObjectConfig = _setObjectConfig

def _getObjectConfig(objectId, key=None):
	pass
logger._getObjectConfig = _getObjectConfig


def logException(e, logLevel=logging.CRITICAL):
	warnings.warn(
		"OPSI.Logger.logException is deprecated, instead use logger.log with exc_info=True.",
		DeprecationWarning
	)
	logger.log(level=logLevel, msg=e, exc_info=True)
logger.logException = logException

def logFailure(failure, logLevel=LOG_CRITICAL):
	pass
logger.logFailure = logFailure

def logTraceback(tb, logLevel=LOG_CRITICAL):
	pass
logger.logTraceback = logTraceback

def logWarnings():
	pass
logger.logWarnings = logWarnings

def startTwistedLogging():
	pass
logger.startTwistedLogging = startTwistedLogging

logger.debug3 = logger.trace
logger.err = logger.error
logger.msg = logger.info
logger.comment = logger.essential
