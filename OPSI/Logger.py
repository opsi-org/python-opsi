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

def setLogFile(logFile, currentThread=False, object=None):
	warnings.warn(
		"OPSI.Logger.setLogFile is deprecated, instead add a FileHandler to logger.",
		DeprecationWarning
	)
	opsicommon.logging.logging_config(log_file=logFile)
logger.setLogFile = setLogFile

def setLogFormat(logFormat, object=None):
	warnings.warn(
		"OPSI.Logger.setLogFormat is deprecated, use opsicommon.logging.set_format instead.",
		DeprecationWarning
	)
	pass
logger.setLogFormat = setLogFormat

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

def logException(e, logLevel=logging.CRITICAL):
	warnings.warn(
		"OPSI.Logger.logException is deprecated, instead use logger.log with exc_info=True.",
		DeprecationWarning
	)
	logger.log(level=logLevel, msg=e, exc_info=True)
logger.logException = logException

def setConsoleLevel(logLevel, object=None):
	warnings.warn(
		"OPSI.Logger.setConsoleLevel is deprecated, instead modify the StreamHandler loglevel.",
		DeprecationWarning
	)
	opsicommon.logging.logging_config(stderr_level=logLevel)
logger.setConsoleLevel = setConsoleLevel

def setFileLevel(logLevel, object=None):
	warnings.warn(
		"OPSI.Logger.setFileLevel is deprecated, instead modify the FileHandler loglevel.",
		DeprecationWarning
	)
	opsicommon.logginglogging_config(file_level=logLevel)
logger.setFileLevel = setFileLevel
