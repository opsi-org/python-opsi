# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
opsi python library - Logger
"""
import os
import warnings
import logging

from opsicommon.logging import (  # pylint: disable=unused-import
	logger, get_all_handlers, observable_handler, logging_config, secret_filter,
	ObservableHandler,
	DEFAULT_FORMAT, DEFAULT_COLORED_FORMAT,
	LOG_SECRET, LOG_CONFIDENTIAL, LOG_TRACE, LOG_DEBUG2, LOG_DEBUG,
	LOG_INFO, LOG_NOTICE, LOG_WARNING, LOG_WARN, LOG_ERROR, LOG_CRITICAL,
	LOG_ESSENTIAL, LOG_NONE, LOG_NOTSET, LOG_COMMENT, OPSI_LEVEL_TO_LEVEL
)

if os.name == 'posix':
	COLOR_NORMAL = '\033[0;0;0m'
	COLOR_BLACK = '\033[0;30;40m'
	COLOR_RED = '\033[0;31;40m'
	COLOR_GREEN = '\033[0;32;40m'
	COLOR_YELLOW = '\033[0;33;40m'
	COLOR_BLUE = '\033[0;34;40m'
	COLOR_MAGENTA = '\033[0;35;40m'
	COLOR_CYAN = '\033[0;36;40m'
	COLOR_WHITE = '\033[0;37;40m'
	COLOR_LIGHT_BLACK = '\033[1;30;40m'
	COLOR_LIGHT_RED = '\033[1;31;40m'
	COLOR_LIGHT_GREEN = '\033[1;32;40m'
	COLOR_LIGHT_YELLOW = '\033[1;33;40m'
	COLOR_LIGHT_BLUE = '\033[1;34;40m'
	COLOR_LIGHT_MAGENTA = '\033[1;35;40m'
	COLOR_LIGHT_CYAN = '\033[1;36;40m'
	COLOR_LIGHT_WHITE = '\033[1;37;40m'
else:
	COLOR_NORMAL = ''
	COLOR_BLACK = ''
	COLOR_RED = ''
	COLOR_GREEN = ''
	COLOR_YELLOW = ''
	COLOR_BLUE = ''
	COLOR_MAGENTA = ''
	COLOR_CYAN = ''
	COLOR_WHITE = ''
	COLOR_LIGHT_BLACK = ''
	COLOR_LIGHT_RED = ''
	COLOR_LIGHT_GREEN = ''
	COLOR_LIGHT_YELLOW = ''
	COLOR_LIGHT_BLUE = ''
	COLOR_LIGHT_MAGENTA = ''
	COLOR_LIGHT_CYAN = ''
	COLOR_LIGHT_WHITE = ''

COLORS_AVAILABLE = [
	COLOR_NORMAL, COLOR_BLACK, COLOR_RED, COLOR_GREEN, COLOR_YELLOW,
	COLOR_BLUE, COLOR_MAGENTA, COLOR_CYAN, COLOR_WHITE, COLOR_LIGHT_BLACK,
	COLOR_LIGHT_RED, COLOR_LIGHT_GREEN, COLOR_LIGHT_YELLOW, COLOR_LIGHT_BLUE,
	COLOR_LIGHT_MAGENTA, COLOR_LIGHT_CYAN, COLOR_LIGHT_WHITE
]

DEBUG_COLOR = COLOR_WHITE
INFO_COLOR = COLOR_LIGHT_WHITE
NOTICE_COLOR = COLOR_GREEN
WARNING_COLOR = COLOR_YELLOW
ERROR_COLOR = COLOR_RED
CRITICAL_COLOR = COLOR_LIGHT_RED
CONFIDENTIAL_COLOR = COLOR_LIGHT_YELLOW
ESSENTIAL_COLOR = COLOR_LIGHT_CYAN
COMMENT_COLOR = ESSENTIAL_COLOR

__all__ = (
	'COLORS_AVAILABLE', 'COLOR_BLACK', 'COLOR_BLUE', 'COLOR_CYAN',
	'COLOR_GREEN', 'COLOR_LIGHT_BLACK', 'COLOR_LIGHT_BLUE', 'COLOR_LIGHT_CYAN',
	'COLOR_LIGHT_GREEN', 'COLOR_LIGHT_MAGENTA', 'COLOR_LIGHT_RED',
	'COLOR_LIGHT_WHITE', 'COLOR_LIGHT_YELLOW', 'COLOR_MAGENTA', 'COLOR_NORMAL',
	'COLOR_RED', 'COLOR_WHITE', 'COLOR_YELLOW', 'COMMENT_COLOR',
	'CONFIDENTIAL_COLOR', 'CRITICAL_COLOR', 'DEBUG_COLOR', 'ERROR_COLOR',
	'ESSENTIAL_COLOR', 'INFO_COLOR', 'LOG_COMMENT', 'LOG_CONFIDENTIAL',
	'LOG_CRITICAL', 'LOG_DEBUG', 'LOG_DEBUG2', 'LOG_ERROR', 'LOG_ESSENTIAL',
	'LOG_INFO', 'LOG_NONE', 'LOG_NOTICE', 'LOG_WARNING', 'Logger',
	'NOTICE_COLOR', 'WARNING_COLOR'
)

class Logger:  # pylint: disable=too-few-public-methods
	pass


#
# Compatibility functions.
#
# These functions realize the OPSI.Logger features utilizing python logging methods.
#

# Replace OPSI Logger
def opsi_logger_factory(logFile=None):
	warnings.warn(
		"OPSI.Logger.Logger is deprecated, use opsicommon.logging.logger instead.",
		DeprecationWarning
	)
	if logFile is not None:
		logging_config(log_file=logFile)
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
	secret_filter.clear_secrets()
	secret_filter.add_secrets(*strings)
logger.setConfidentialStrings = setConfidentialStrings

def addConfidentialString(string):
	warnings.warn(
		"OPSI.Logger.addConfidentialString is deprecated, use secret_filter.add_secrets instead.",
		DeprecationWarning
	)
	secret_filter.add_secrets(string)
logger.addConfidentialString = addConfidentialString

def setLogFormat(logFormat, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setLogFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
logger.setLogFormat = setLogFormat

def setConsoleFormat(format, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setConsoleFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
logger.setConsoleFormat = setConsoleFormat

def setComponentName(componentName, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setComponentName is deprecated, use opsicommon.logging.context instead.",
		DeprecationWarning
	)
logger.setComponentName = setComponentName

def logToStdout(stdout):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger.logToStdout is deprecated",
		DeprecationWarning
	)
logger.logToStdout = logToStdout

def setSyslogFormat(format, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setSyslogFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
logger.setSyslogFormat = setSyslogFormat

def setFileFormat(format, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setFileFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
logger.setFileFormat = setFileFormat

def setUniventionFormat(format, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setUniventionFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
logger.setUniventionFormat = setUniventionFormat

def setMessageSubjectFormat(format, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setUniventionFormat is deprecated",
		DeprecationWarning
	)
logger.setMessageSubjectFormat = setMessageSubjectFormat

def setUniventionLogger(logger):  # pylint: disable=unused-argument,redefined-outer-name
	warnings.warn(
		"OPSI.Logger.setUniventionLogger is deprecated",
		DeprecationWarning
	)
logger.setUniventionLogger = setUniventionLogger

def setUniventionClass(c):  # pylint: disable=unused-argument,invalid-name
	warnings.warn(
		"OPSI.Logger.setUniventionClass is deprecated",
		DeprecationWarning
	)
logger.setUniventionClass = setUniventionClass

def getMessageSubject():
	warnings.warn(
		"OPSI.Logger.getMessageSubject is deprecated, use opsicommon.logging.ObservableHandler instead",
		DeprecationWarning
	)
	return observable_handler
logger.getMessageSubject = getMessageSubject

def setColor(color):
	setConsoleColor(color)
logger.setColor = setColor

def setFileColor(color):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger.setFileColor is deprecated, use opsicommon.logging.logging_config instead",
		DeprecationWarning
	)
	logger.setFileColor = setFileColor

def setConsoleColor(color):
	warnings.warn(
		"OPSI.Logger.setConsoleColor is deprecated, use opsicommon.logging.logging_config instead",
		DeprecationWarning
	)
	logging_config(stderr_format=DEFAULT_COLORED_FORMAT if color else DEFAULT_FORMAT)
logger.setConsoleColor = setConsoleColor

def setSyslogLevel(level=LOG_NONE):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger.setSyslogLevel is deprecated",
		DeprecationWarning
	)
logger.setSyslogLevel = setSyslogLevel

def setMessageSubjectLevel(level=LOG_NONE):
	warnings.warn(
		"OPSI.Logger.setMessageSubjectLevel is deprecated, use opsicommon.logging.ObservableHandler instead",
		DeprecationWarning
	)
	for handler in get_all_handlers(ObservableHandler):
		handler.setLevel(OPSI_LEVEL_TO_LEVEL[level])  # pylint: disable=protected-access
logger.setMessageSubjectLevel = setMessageSubjectLevel

def setConsoleLevel(logLevel, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setConsoleLevel is deprecated, instead modify the StreamHandler loglevel.",
		DeprecationWarning
	)
	if logLevel is not None:
		logging_config(stderr_level=OPSI_LEVEL_TO_LEVEL[logLevel])
logger.setConsoleLevel = setConsoleLevel

@staticmethod
def _sanitizeLogLevel(level):
	return level

def getConsoleLevel():
	warnings.warn(
		"OPSI.Logger.getConsoleLevel is deprecated",
		DeprecationWarning
	)
logger.getConsoleLevel = getConsoleLevel

def getFileLevel():
	warnings.warn(
		"OPSI.Logger.getFileLevel is deprecated",
		DeprecationWarning
	)
logger.getFileLevel = getFileLevel

def getLogFile(currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.getLogFile is deprecated",
		DeprecationWarning
	)
logger.getLogFile = getLogFile

def setLogFile(logFile, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setLogFile is deprecated, instead add a FileHandler to logger.",
		DeprecationWarning
	)
	logging_config(log_file=logFile)
logger.setLogFile = setLogFile

def linkLogFile(linkFile, currentThread=False, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.linkLogFile is deprecated",
		DeprecationWarning
	)
logger.linkLogFile = linkLogFile

def setFileLevel(logLevel, object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.setFileLevel is deprecated, instead modify the FileHandler loglevel.",
		DeprecationWarning
	)
	logging_config(file_level=OPSI_LEVEL_TO_LEVEL[logLevel])
logger.setFileLevel = setFileLevel

def exit(object=None):  # pylint: disable=unused-argument,redefined-builtin
	warnings.warn(
		"OPSI.Logger.exit is deprecated",
		DeprecationWarning
	)
logger.exit = exit

def _setThreadConfig(key, value):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger._setThreadConfig is deprecated",
		DeprecationWarning
	)
logger._setThreadConfig = _setThreadConfig  # pylint: disable=protected-access

def _getThreadConfig(key=None):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger._getThreadConfig is deprecated",
		DeprecationWarning
	)
logger._getThreadConfig = _getThreadConfig  # pylint: disable=protected-access

def _setObjectConfig(objectId, key, value):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger._setObjectConfig is deprecated",
		DeprecationWarning
	)
logger._setObjectConfig = _setObjectConfig  # pylint: disable=protected-access

def _getObjectConfig(objectId, key=None):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger._getObjectConfig is deprecated",
		DeprecationWarning
	)
logger._getObjectConfig = _getObjectConfig  # pylint: disable=protected-access

def logException(e, logLevel=logging.CRITICAL):  # pylint: disable=invalid-name
	warnings.warn(
		"OPSI.Logger.logException is deprecated, instead use logger.log with exc_info=True.",
		DeprecationWarning
	)
	logger.log(level=logLevel, msg=e, exc_info=True)
logger.logException = logException

def logFailure(failure, logLevel=LOG_CRITICAL):  # pylint: disable=unused-argument
	warnings.warn(
		"OPSI.Logger.logFailure is deprecated",
		DeprecationWarning
	)
logger.logFailure = logFailure

def logTraceback(tb, logLevel=LOG_CRITICAL):  # pylint: disable=unused-argument,invalid-name
	warnings.warn(
		"OPSI.Logger.logTraceback is deprecated",
		DeprecationWarning
	)
logger.logTraceback = logTraceback

def logWarnings():
	warnings.warn(
		"OPSI.Logger.logWarnings is deprecated",
		DeprecationWarning
	)
logger.logWarnings = logWarnings

def startTwistedLogging():
	warnings.warn(
		"OPSI.Logger.startTwistedLogging is deprecated",
		DeprecationWarning
	)
logger.startTwistedLogging = startTwistedLogging

logger.debug3 = logger.trace
logger.err = logger.error
logger.msg = logger.info
logger.comment = logger.essential
