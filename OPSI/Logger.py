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

import codecs
import os
import sys
import threading
import time
import traceback
import warnings

try:
	import thread
except ImportError:
	# Python 3
	import _thread as thread

if os.name == 'nt':
	# Windows imports for file locking
	import win32con
	import win32file
	import pywintypes
elif os.name == 'posix':
	# Posix imports for file locking
	import fcntl

try:
	import syslog
except ImportError:
	syslog = None

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

# Loglevels
LOG_CONFIDENTIAL = 9
LOG_DEBUG2 = 8
LOG_DEBUG = 7
LOG_INFO = 6
LOG_NOTICE = 5
LOG_WARNING = 4
LOG_ERROR = 3
LOG_CRITICAL = 2
LOG_ESSENTIAL = 1
LOG_COMMENT = LOG_ESSENTIAL
LOG_NONE = 0

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

if syslog is not None:
	_SYSLOG_LEVEL_MAPPING = {
		LOG_CONFIDENTIAL: syslog.LOG_DEBUG,
		LOG_DEBUG2: syslog.LOG_DEBUG,
		LOG_DEBUG: syslog.LOG_DEBUG,
		LOG_INFO: syslog.LOG_INFO,
		LOG_NOTICE: syslog.LOG_NOTICE,
		LOG_WARNING: syslog.LOG_WARNING,
		LOG_ERROR: syslog.LOG_ERR,
		LOG_CRITICAL: syslog.LOG_CRIT,
		LOG_COMMENT: syslog.LOG_CRIT
	}

_LOGLEVEL_NAME_AND_COLOR_MAPPING = {
	LOG_CONFIDENTIAL: (u'confidential', CONFIDENTIAL_COLOR),
	LOG_DEBUG2: (u'debug2', DEBUG_COLOR),
	LOG_DEBUG: (u'debug', DEBUG_COLOR),
	LOG_INFO: (u'info', INFO_COLOR),
	LOG_NOTICE: (u'notice', NOTICE_COLOR),
	LOG_WARNING: (u'warning', WARNING_COLOR),
	LOG_ERROR: (u'error', ERROR_COLOR),
	LOG_CRITICAL: (u'critical', CRITICAL_COLOR),
	LOG_ESSENTIAL: (u'essential', COMMENT_COLOR),
}

encoding = sys.getfilesystemencoding()
_showwarning = warnings.showwarning


def forceUnicode(var):
	if isinstance(var, str):
		return var
	elif (os.name == 'nt') and isinstance(var, WindowsError):
		return u"[Error %s] %s" % (var.args[0], var.args[1].decode(encoding))

	try:
		if isinstance(var, bytes):
			return var.decode()
	except Exception:
		pass

	try:
		var = var.__repr__()
		if isinstance(var, str):
			return var
		return str(var, 'utf-8', 'replace')
	except Exception:
		pass

	return str(var)


class LoggerSubject:
	def __init__(self):
		self._observers = []
		self._message = u""
		self._severity = 0

	def getId(self):
		return u'logger'

	def getType(self):
		return u'Logger'

	def getClass(self):
		return u'MessageSubject'

	def setMessage(self, message, severity=0):
		self._message = forceUnicode(message)
		self._severity = severity
		for o in self._observers:
			o.messageChanged(self, message)

	def getMessage(self):
		return self._message

	def getSeverity(self):
		return self._severity

	def attachObserver(self, observer):
		if observer not in self._observers:
			self._observers.append(observer)

	def detachObserver(self, observer):
		if observer in self._observers:
			self._observers.remove(observer)

	def serializable(self):
		return {
			"message": self.getMessage(),
			"severity": self.getSeverity(),
			"id": self.getId(),
			"class": self.getClass(),
			"type": self.getType()
		}


class TwistedLogObserver(object):
	def __init__(self, logger):
		self._logger = logger

	def emit(self, eventDict):
		if eventDict.get('isError'):
			if eventDict.get('failure'):
				self._logger.logTraceback(eventDict['failure'].getTracebackObject())
				self._logger.critical(u"     ==>>> %s" % eventDict['failure'].getErrorMessage())

			for line in eventDict.get('message', ()):
				if "Can't find property" in line:
					# Dav property errors
					self._logger.debug(u"[twisted] %s" % line)
				else:
					self._logger.error(u"[twisted] %s" % line)
		else:
			for line in eventDict.get('message', ()):
				self._logger.debug(u"[twisted] %s" % line)


class LoggerImplementation:
	''' Implementation of the singleton interface '''

	def __init__(self, logFile=None):
		self.__syslogLevel = LOG_NONE
		self.__consoleLevel = LOG_NONE
		self.__fileLevel = LOG_NONE
		self.__messageSubjectLevel = LOG_NONE
		self.__fileColor = False
		self.__consoleColor = False
		self.__logFile = logFile
		self.__syslogFormat = u'%M'
		self.__consoleFormat = u'%M'
		self.__consoleStdout = False
		self.__fileFormat = u'%D [%L] %M (%F|%N)'
		self.__messageSubjectFormat = u'%M'
		self.univentionLogger_priv = None
		self.__univentionClass = None
		self.__univentionFormat = u'opsi: %M'
		self.__confidentialStrings = set()
		self.__componentName = u''
		self.__threadConfig = {}
		self.__objectConfig = {}
		self.__stdout = VirtFile(self, LOG_NOTICE)
		self.__stderr = VirtFile(self, LOG_ERROR)
		self.__lock = threading.Lock()
		self.__loggerSubject = LoggerSubject()

	def getStderr(self):
		return self.__stderr

	def getStdout(self):
		return self.__stdout

	def setConfidentialStrings(self, strings):
		if not isinstance(strings, (list, tuple)):
			strings = [strings]

		self.__confidentialStrings = set()
		for string in strings:
			self.addConfidentialString(string)

	def addConfidentialString(self, string):
		string = forceUnicode(string)
		if not string:
			raise ValueError(u"Cannot use empty string as confidential string")
		self.__confidentialStrings.add(string)

	def setLogFormat(self, format, currentThread=False, object=None):
		self.setConsoleFormat(format, currentThread, object)
		self.setSyslogFormat(format, currentThread, object)
		self.setFileFormat(format, currentThread, object)

	def setConsoleFormat(self, format, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('consoleFormat', format)
		elif object:
			self._setObjectConfig(id(object), 'consoleFormat', format)
		else:
			self.__consoleFormat = format

	def setComponentName(self, componentName, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('componentName', componentName)
		elif object:
			self._setObjectConfig(id(object), 'componentName', componentName)
		else:
			self.__componentName = componentName

	def logToStdout(self, stdout):
		self.__consoleStdout = stdout

	def setSyslogFormat(self, format, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('syslogFormat', format)
		elif object:
			self._setObjectConfig(id(object), 'syslogFormat', format)
		else:
			self.__syslogFormat = format

	def setFileFormat(self, format, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('fileFormat', format)
		elif object:
			self._setObjectConfig(id(object), 'fileFormat', format)
		else:
			self.__fileFormat = format

	def setUniventionFormat(self, format, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('univentionFormat', format)
		elif object:
			self._setObjectConfig(id(object), 'univentionFormat', format)
		else:
			self.__univentionFormat = format

	def setMessageSubjectFormat(self, format, currentThread=False, object=None):
		if currentThread:
			self._setThreadConfig('messageSubjectFormat', format)
		elif object:
			self._setObjectConfig(id(object), 'messageSubjectFormat', format)
		else:
			self.__messageSubjectFormat = format

	def setUniventionLogger(self, logger):
		self.univentionLogger_priv = logger

	def setUniventionClass(self, c):
		self.__univentionClass = c

	def getMessageSubject(self):
		return self.__loggerSubject

	def setColor(self, color):
		'''
		Enable or disable ansi color output in all outputs.

		If `color` is `True`, then output will be colored.

		:type color: bool
		'''
		self.__fileColor = self.__consoleColor = color

	def setFileColor(self, color):
		'''
		Enable or disable ANSI color output for files.

		If `color` is `True`, then output will be colored.

		:type color: bool
		'''
		self.__fileColor = color

	def setConsoleColor(self, color):
		'''
		Enable or disable ANSI color output for console.

		If `color` is `True`, then output will be colored.

		:type color: bool
		'''
		self.__consoleColor = color

	def setSyslogLevel(self, level=LOG_NONE):
		'''
		Maximum level of messages to log by syslog.

		Set `level` to LOG_NONE to disable syslog (default).
		:type level: int
		'''
		level = self._sanitizeLogLevel(level)

		self.__syslogLevel = level
		if syslog is not None:
			if self.__syslogLevel != LOG_NONE:
				# Set ident string for syslog
				ident = 'opsi'
				try:
					raise Exception
				except Exception:
					# Go back 2 frames
					frame = sys.exc_traceback.tb_frame.f_back.f_back
					# Get caller's filename
					filename = frame.f_code.co_filename
					ident = filename.split('/')[-1]
				syslog.openlog(ident, syslog.LOG_CONS, syslog.LOG_DAEMON)

	def setMessageSubjectLevel(self, level=LOG_NONE):
		self.__messageSubjectLevel = self._sanitizeLogLevel(level)

	def setConsoleLevel(self, level=LOG_NONE):
		'''
		Maximum level of messages to print to stderr.

		Set `level` to LOG_NONE to disable output to stderr (default).

		:type level: int
		'''
		self.__consoleLevel = self._sanitizeLogLevel(level)

	@staticmethod
	def _sanitizeLogLevel(level):
		if level < LOG_NONE:
			return LOG_NONE
		elif level > LOG_CONFIDENTIAL:
			return LOG_CONFIDENTIAL
		else:
			return level

	def getConsoleLevel(self):
		return self.__consoleLevel

	def getFileLevel(self):
		return self.__fileLevel

	def getLogFile(self, currentThread=False, object=None):
		if currentThread:
			return self._getThreadConfig('logFile')
		elif object:
			return self._getObjectConfig(id(object), 'logFile')

		return self.__logFile

	def setLogFile(self, logFile, currentThread=False, object=None):
		'''
		Set the filename of logfile.

		:param logFile: The path to the logfile. Setting this to `None` \
will disable logging to a file.
		'''
		if logFile is not None:
			logFile = os.path.abspath(logFile)

		if currentThread:
			self._setThreadConfig('logFile', logFile)
			self.debug(u"Now using log-file '%s' for thread %s" \
				% (logFile, thread.get_ident()))
		elif object:
			self._setObjectConfig(id(object), 'logFile', logFile)
			self.debug(u"Now using log-file '%s' for object 0x%x" % (logFile, id(object)))
		else:
			self.__logFile = logFile
			self.debug(u"Now using log-file '%s'" % self.__logFile)

	def linkLogFile(self, linkFile, currentThread=False, object=None):
		''' Link the current logfile to ``linkfile``. '''
		logFile = None
		if currentThread:
			logFile = self._getThreadConfig('logFile')
		elif object:
			logFile = self._getObjectConfig(id(object), 'logFile')
		else:
			logFile = self.__logFile

		if not logFile:
			self.error(u"Cannot create symlink {0!r}: log-file unknown", linkFile)
			return

		if not os.path.isabs(linkFile):
			linkFile = os.path.join(os.path.dirname(logFile), linkFile)

		try:
			if logFile == linkFile:
				raise ValueError(u'logFile and linkFile are the same file!')

			try:
				os.unlink(linkFile)
			except FileNotFoundError:
				pass
			except OSError as oserr:
				self.debug2(u"Failed to remove link {0!r}: {1}", linkFile, oserr)

			os.symlink(logFile, linkFile)
		except Exception as error:
			self.error(u"Failed to create symlink from {0!r} to {1!r}: {2}", logFile, linkFile, error)

	def setFileLevel(self, level=LOG_NONE):
		'''
		Maximum level of messages to appear in logfile.

		Set `level` to LOG_NONE to disable output to logfile (default).

		:type level: int
		'''
		self.__fileLevel = self._sanitizeLogLevel(level)

	def exit(self, object=None):
		if object:
			if id(object) in self.__objectConfig:
				self.debug(u"Deleting config of object 0x%x" % id(object))
				del self.__objectConfig[id(object)]

			for objectId in self.__objectConfig:
				self.debug2(u"Got special config for object 0x%x" % objectId)

		threadId = thread.get_ident()
		if threadId in self.__threadConfig:
			self.debug(u"Deleting config of thread %s" % threadId)
			del self.__threadConfig[threadId]

		for threadId in self.__threadConfig:
			self.debug2(u"Got special config for thread %s" % threadId)

	def _setThreadConfig(self, key, value):
		threadId = thread.get_ident()

		try:
			self.__threadConfig[threadId][key] = value
		except KeyError:
			self.__threadConfig[threadId] = {key: value}

	def _getThreadConfig(self, key=None):
		threadId = thread.get_ident()
		if threadId not in self.__threadConfig:
			return None

		if not key:
			return self.__threadConfig[threadId]

		return self.__threadConfig[threadId].get(key)

	def _setObjectConfig(self, objectId, key, value):
		try:
			self.__objectConfig[objectId][key] = value
		except KeyError:
			self.__objectConfig[objectId] = {key: value}

	def _getObjectConfig(self, objectId, key=None):
		if objectId not in self.__objectConfig:
			return None

		if not key:
			return self.__objectConfig[objectId]

		return self.__objectConfig[objectId].get(key)

	def log(self, level, message, raiseException=False, formatArgs=[], formatKwargs={}):
		'''
		Log a message with the given level.

		:param level: The log level of this message.
		:param message: The message to log.
		:param raiseException: True raises an exception if any error occurs. \
False suppresses exceptions.
		:type raiseException: bool
		'''
		if (level > self.__messageSubjectLevel and
			level > self.__consoleLevel and
			level > self.__fileLevel and
			level > self.__syslogLevel and
			not self.univentionLogger_priv):

			return

		def formatMessage(unformattedMessage, removeConfidential=False):
			tempMessage = str(unformattedMessage)
			tempMessage = tempMessage.replace(u'%M', message)

			if removeConfidential:
				for string in self.__confidentialStrings:
					tempMessage = tempMessage.replace(string, u'*** confidential ***')

			tempMessage = tempMessage.replace(u'%D', datetime)
			tempMessage = tempMessage.replace(u'%T', threadId)
			tempMessage = tempMessage.replace(u'%l', str(level))
			tempMessage = tempMessage.replace(u'%L', levelname)
			tempMessage = tempMessage.replace(u'%C', componentname)
			tempMessage = tempMessage.replace(u'%F', filename)
			tempMessage = tempMessage.replace(u'%N', linenumber)
			return tempMessage

		try:
			if not isinstance(message, str):
				message = str(message, 'utf-8', 'replace')

			try:
				message = message.format(*formatArgs, **formatKwargs)
			except KeyError as e:
				if 'missing format for key ' not in str(e).lower():
					raise e
			except ValueError as e:
				if 'invalid conversion specification' not in str(e).lower():
					raise e

			componentname = self.__componentName
			datetime = time.strftime(u"%b %d %H:%M:%S", time.localtime())
			threadId = str(thread.get_ident())
			specialConfig = None

			try:
				levelname, color = _LOGLEVEL_NAME_AND_COLOR_MAPPING[level]
			except KeyError:
				levelname = u''
				color = COLOR_NORMAL

			try:
				filename = str(os.path.basename(sys._getframe(2).f_code.co_filename))
				linenumber = str(sys._getframe(2).f_lineno)

				specialConfig = self._getThreadConfig()
				if not specialConfig and self.__objectConfig:
					# Ouch, this hurts...
					f = sys._getframe(2)
					while f is not None:
						obj = f.f_locals.get('self')
						if obj:
							c = self._getObjectConfig(id(obj))
							if c:
								specialConfig = c
								break
						f = f.f_back
			except Exception:
				# call stack not deep enough?
				try:
					filename
				except NameError:
					filename = u''

				try:
					linenumber
				except NameError:
					linenumber = u''

			if specialConfig:
				componentname = specialConfig.get('componentName', componentname)

			if level <= self.__messageSubjectLevel:
				m = self.__messageSubjectFormat
				if specialConfig:
					m = specialConfig.get('messageSubjectFormat', m)
				m = formatMessage(m, removeConfidential=self.__messageSubjectLevel < LOG_CONFIDENTIAL)

				self.__loggerSubject.setMessage(m, level)

			if level <= self.__consoleLevel:
				# Log to terminal
				m = self.__consoleFormat
				if specialConfig:
					m = specialConfig.get('consoleFormat', m)
				m = formatMessage(m, removeConfidential=self.__consoleLevel < LOG_CONFIDENTIAL)

				if self.__consoleStdout:
					fh = sys.stdout
				else:
					fh = sys.stderr

				if self.__consoleColor:
					m = u"%s%s%s\n" % (color, m, COLOR_NORMAL)
				else:
					m = u"%s\n" % m
				fh.write(m)

			if level <= self.__fileLevel:
				# Log to file
				logFile = self.__logFile
				if specialConfig:
					logFile = specialConfig.get('logFile', logFile)
				if logFile:
					m = self.__fileFormat
					if specialConfig:
						m = specialConfig.get('fileFormat', m)
					m = formatMessage(m, removeConfidential=self.__fileLevel < LOG_CONFIDENTIAL)

					try:
						lf = codecs.open(logFile, 'a+', 'utf-8', 'replace')
					except Exception as err:
						lf = None

					if lf:
						timeout = 0
						locked = False
						while not locked and timeout < 2000:
							# While not timed out and not locked
							try:
								# Try to lock file
								if os.name == 'nt':
									hfile = win32file._get_osfhandle(lf.fileno())
									win32file.LockFileEx(hfile, win32con.LOCKFILE_EXCLUSIVE_LOCK, 0, -0x7fff0000, pywintypes.OVERLAPPED())
									# win32file.LockFileEx(hfile, flags, 0, -0x10000, __overlapped)
								elif os.name == 'posix':
									# Flags for exclusive, non-blocking lock
									fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
							except IOError as err:
								# Locking failed
								# increase timeout counter, sleep 100 millis
								timeout += 100
								time.sleep(0.1)
							else:
								# File successfully locked
								locked = True

						if locked:
							if self.__fileColor:
								m = u"%s%s%s" % (color, m, COLOR_NORMAL)
							m += u'\n'
							if os.name == 'nt':
								m = m.replace(u'\n', u'\r\n')
							lf.write(m)
							lf.close()

			if syslog is not None and level <= self.__syslogLevel:
				# Log to syslog
				m = self.__syslogFormat
				if specialConfig:
					m = specialConfig.get('syslogFormat', m)
				m = formatMessage(m, removeConfidential=self.__syslogLevel < LOG_CONFIDENTIAL)

				try:
					syslog.syslog(_SYSLOG_LEVEL_MAPPING[level], m)
				except KeyError:
					# No known log level - ignoring.
					pass

			if self.univentionLogger_priv:
				# univention log
				m = self.__univentionFormat
				if specialConfig:
					m = specialConfig.get('univentionFormat', m)
				m = formatMessage(m, removeConfidential=True)

				if level in (LOG_DEBUG2, LOG_DEBUG, LOG_INFO):
					univentionLevel = self.univentionLogger_priv.ALL
				elif level == LOG_NOTICE:
					univentionLevel = self.univentionLogger_priv.INFO
				elif level == LOG_WARNING:
					univentionLevel = self.univentionLogger_priv.WARN
				elif level in (LOG_ERROR, LOG_CRITICAL, LOG_COMMENT):
					univentionLevel = self.univentionLogger_priv.ERROR
				else:
					univentionLevel = None

				if univentionLevel:
					self.univentionLogger_priv.debug(self.__univentionClass, univentionLevel, m)
		except Exception as err:
			if raiseException:
				raise err

	def logException(self, e, logLevel=LOG_CRITICAL):
		self.logTraceback(sys.exc_info()[2], logLevel)
		message = forceUnicode(e)
		self.log(logLevel, u'     ==>>> %s' % message)

	def logFailure(self, failure, logLevel=LOG_CRITICAL):
		self.logTraceback(failure.getTracebackObject(), logLevel)
		message = forceUnicode(failure.getErrorMessage())
		self.log(logLevel, u'     ==>>> %s' % message)

	def logTraceback(self, tb, logLevel=LOG_CRITICAL):
		'''
		Log an traceback.

		This will log the call trace from the given traceback.
		'''
		self.log(logLevel, u'Traceback:')
		try:
			for tbInfo in traceback.format_tb(tb):
				self.log(logLevel, tbInfo)
		except AttributeError as attrError:
			self.log(LOG_CRITICAL, u"    Failed to log traceback for {0!r}: {1}".format(tb, attrError))

	def logWarnings(self):
		"""
		Use OPSI.Logger to log warning messages.

		This redirects messages emitted to the ``warnings`` modules to
		the opsi logger.
		"""
		def _logWarning(message, category, filename, lineno, file=None, line=None):
			formattedMessage = warnings.formatwarning(message, category, filename, lineno, line)
			self.warning(formattedMessage)

		warnings.showwarning = _logWarning

	def startTwistedLogging(self):
		from twisted.python import log
		observer = TwistedLogObserver(self)
		log.startLoggingWithObserver(observer.emit, setStdout=0)

	def confidential(self, message, *args, **kwargs):
		''' Log a confidential message. '''
		self.log(LOG_CONFIDENTIAL, message, formatArgs=args, formatKwargs=kwargs)

	def debug3(self, message, *args, **kwargs):
		''' Log a debug message. '''
		self.debug2(message, *args, **kwargs)

	def debug2(self, message, *args, **kwargs):
		''' Log a debug message. '''
		self.log(LOG_DEBUG2, message, formatArgs=args, formatKwargs=kwargs)

	def debug(self, message, *args, **kwargs):
		''' Log a debug message. '''
		self.log(LOG_DEBUG, message, formatArgs=args, formatKwargs=kwargs)

	def info(self, message, *args, **kwargs):
		''' Log a info message. '''
		self.log(LOG_INFO, message, formatArgs=args, formatKwargs=kwargs)

	def msg(self, message, *args, **kwargs):
		''' Log a info message. '''
		self.info(message, *args, **kwargs)

	def notice(self, message, *args, **kwargs):
		''' Log a notice message. '''
		self.log(LOG_NOTICE, message, formatArgs=args, formatKwargs=kwargs)

	def warning(self, message, *args, **kwargs):
		''' Log a warning message. '''
		self.log(LOG_WARNING, message, formatArgs=args, formatKwargs=kwargs)

	def error(self, message, *args, **kwargs):
		''' Log a error message. '''
		self.log(LOG_ERROR, message, formatArgs=args, formatKwargs=kwargs)

	def err(self, message):
		''' Log a error message. '''
		self.error(message)

	def critical(self, message, *args, **kwargs):
		''' Log a critical message. '''
		self.log(LOG_CRITICAL, message, formatArgs=args, formatKwargs=kwargs)

	def essential(self, message, *args, **kwargs):
		''' Log a essential message. '''
		self.log(LOG_ESSENTIAL, message, formatArgs=args, formatKwargs=kwargs)

	def comment(self, message, *args, **kwargs):
		''' Log a comment message. '''
		self.essential(message, *args, **kwargs)


class Logger(LoggerImplementation):
	'''
	This class implements a SINGLETON used for logging to console, \
file or syslog.
	'''

	# Storage for the instance reference
	__instance = None

	def __init__(self, logFile=None):
		""" Create singleton instance """

		# Check whether we already have an instance
		if Logger.__instance is None:
			# Create and remember instance
			Logger.__instance = LoggerImplementation()

		# Store instance reference as the only member in the handle
		self.__dict__['_Logger__instance'] = Logger.__instance

	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)

	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
		return setattr(self.__instance, attr, value)


class VirtFile:

	def __init__(self, logger, level):
		self.logger = logger
		self.level = level
		self.encoding = 'utf-8'

	def write(self, s):
		self.logger.log(self.level, s)

	def flush(self):
		return
