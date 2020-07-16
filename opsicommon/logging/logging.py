# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import traceback
import time
import sys
import os
import logging
import colorlog
import warnings
import contextvars
from contextlib import contextmanager
from typing import Dict, Tuple, Any
from logging.handlers import WatchedFileHandler, RotatingFileHandler

from ..utils import Singleton
from .constants import (
	DEFAULT_COLORED_FORMAT, DEFAULT_FORMAT, DATETIME_FORMAT,
	CONTEXT_STRING_MIN_LENGTH, LOG_COLORS, SECRET_REPLACEMENT_STRING,
	LOG_SECRET, LOG_TRACE, LOG_DEBUG, LOG_INFO, LOG_NOTICE, LOG_WARNING,
	LOG_ERROR, LOG_CRITICAL, LOG_ESSENTIAL, LOG_NONE
)

logger = logging.getLogger()
context = contextvars.ContextVar('context', default={})

def secret(self, msg : str, *args, **kwargs):
	"""
	Logging with level SECRET.

	This method calls a log with level logging.SECRET.

	:param msg: Message to log (may contain %-style placeholders).
	:type msg: str
	:param *args: Arguments to fill %-style placeholders with.
	:param **kwargs: Additional keyword-arguments.
	"""
	if self.isEnabledFor(logging.SECRET):
		self._log(logging.SECRET, msg, args, **kwargs)

logging.Logger.secret = secret
logging.Logger.confidential = secret

def trace(self, msg, *args, **kwargs):
	"""
	Logging with level TRACE.

	This method calls a log with level logging.TRACE.

	:param msg: Message to log (may contain %-style placeholders).
	:type msg: str
	:param *args: Arguments to fill %-style placeholders with.
	:param **kwargs: Additional keyword-arguments.
	"""
	if self.isEnabledFor(logging.TRACE):
		self._log(logging.TRACE, msg, args, **kwargs)

logging.Logger.trace = trace
logging.Logger.debug2 = trace

def notice(self, msg, *args, **kwargs):
	"""
	Logging with level NOTICE.

	This method calls a log with level logging.NOTICE.

	:param msg: Message to log (may contain %-style placeholders).
	:type msg: str
	:param *args: Arguments to fill %-style placeholders with.
	:param **kwargs: Additional keyword-arguments.
	"""
	if self.isEnabledFor(logging.NOTICE):
		self._log(logging.NOTICE, msg, args, **kwargs)

logging.Logger.notice = notice

def essential(self, msg, *args, **kwargs):
	"""
	Logging with level ESSENTIAL.

	This method calls a log with level logging.ESSENTIAL.

	:param msg: Message to log (may contain %-style placeholders).
	:type msg: str
	:param *args: Arguments to fill %-style placeholders with.
	:param **kwargs: Additional keyword-arguments.
	"""
	if self.isEnabledFor(logging.ESSENTIAL):
		self._log(logging.ESSENTIAL, msg, args, **kwargs)

logging.Logger.essential = essential
logging.Logger.comment = essential
logging.Logger.devel = essential

def logrecord_init(self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None, **kwargs):
	"""
	New Constructor for LogRecord.

	This overloads the LogRecord constructor to also include the OpsiLogLevel.
	The reason is to have backwards compatibility.

	:param name: Name of the logger to feed.
	:param level: Log level of the message.
	:param pathname: Path of the running module.
	:param lineno: Line number of the call.
	:param msg: Message to log (may contain %-style placeholders).
	:param args: Arguments to fill %-style placeholders with.
	:param exc_info: Traceback information in case of exceptions.
	:param func: Name of the calling function.
	:param sinfo: Call stack information.
	:param **kwargs: Additional keyword-arguments.
	"""
	self.__init_orig__(name, level, pathname, lineno, msg, args, exc_info, func=func, sinfo=sinfo, **kwargs)
	self.opsilevel = logging._levelToOpsiLevel.get(level, level)

logging.LogRecord.__init_orig__ = logging.LogRecord.__init__
logging.LogRecord.__init__ = logrecord_init

try:
	"""
	Compatibility functions.

	These functions realize the OPSI.Logger features utilizing
	python logging methods.
	"""
	# Replace OPSI Logger
	import OPSI.Logger
	def opsi_logger_factory():
		warnings.warn(
			"OPSI.Logger.Logger is deprecated, use opsicommon.logging.logger instead.",
			DeprecationWarning
		)
		return logger
	OPSI.Logger.Logger = opsi_logger_factory

	def setLogFile(logFile, currentThread=False, object=None):
		warnings.warn(
			"OPSI.Logger.setLogFile is deprecated, instead add a FileHandler to logger.",
			DeprecationWarning
		)
		logging_config(log_file=logFile)
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
		logging_config(stderr_level=logLevel)
	logger.setConsoleLevel = setConsoleLevel

	def setFileLevel(logLevel, object=None):
		warnings.warn(
			"OPSI.Logger.setFileLevel is deprecated, instead modify the FileHandler loglevel.",
			DeprecationWarning
		)
		logging_config(file_level=logLevel)
	logger.setFileLevel = setFileLevel
except ImportError:
	pass


def handle_log_exception(exc: Exception, record: logging.LogRecord = None, log: bool = True):
	"""
	Handles an exception in logging process.

	This method prints an Exception message and traceback to stderr.

	:param exc: Exception to be logged.
	:type exc: Exception
	:param record: Log record where the exception occured.
	:type record: logging.LogRecord.
	:param log: If true, the Exception is also output by the logger. (Default: True)
	:type log: bool
	"""
	print("Logging error:", file=sys.stderr)
	traceback.print_exc(file=sys.stderr)
	if not log:
		return
	try:
		logger.error(f"Logging error: {exc}", exc_info=True)
		if record:
			logger.error(record.__dict__)
			#logger.error(f"{record.msg} - {record.args}")
	except:
		pass

class ContextFilter(logging.Filter, metaclass=Singleton):
	"""
	class ContextFilter

	This class implements a filter which modifies allows to store context
	for a single thread/task.
	"""
	def __init__(self, filter_dict : Dict=None):
		"""
		ContextFilter Constructor

		This constructor initializes a ContextFilter instance with an
		empty dictionary as context.

		:param filter_dict: Dictionary that must be present in record context
			in order to accept the LogRecord.
		:type filter_dict: Dict
		"""
		super().__init__()
		self.filter_dict = {}
		self.set_filter(filter_dict)

	def get_context(self) -> Dict:
		"""
		Returns context of current thread/task.

		This method requests the thread/task identifier,
		looks up the context stored for it and returns it.

		:returns: Context for currently active thread/task.
		:rtype: Dict
		"""
		return context.get()

	def set_filter(self, filter_dict : Dict=None):
		"""
		Sets a new filter dictionary.

		This method expectes a filter dictionary.
		Records are only allowed to pass if their context has a matching
		key-value entry. None means, every record can pass.

		:param filter_dict: Value that must be present in record context
			in order to accept the LogRecord.
		:type filter_dict: Dict
		"""
		if filter_dict is None:
			self.filter_dict = {}
			return
		if not isinstance(filter_dict, dict):
			raise ValueError("filter_dict must be a python dictionary")

		self.filter_dict = {}
		for (key, value) in filter_dict.items():
			if isinstance(value, list):
				self.filter_dict[key] = value
			else:
				self.filter_dict[key] = [value]

	def filter(self, record : logging.LogRecord) -> bool:
		"""
		Adds context to a LogRecord.

		This method is called by Logger._log and modifies LogRecords.
		It adds the context stored for the current thread/task to the namespace.
		If the records context conforms to the filter, it is passed on.

		:param record: LogRecord to add context to and to filter.
		:type record: LogRecord

		:returns: True, if the record conforms to the filter rules.
		:rtype: bool
		"""
		record.context = context.get()
		for (filter_key, filter_value) in self.filter_dict.items():
			record_value = record.context.get(filter_key)
			#skip if key not present or value not in filter values
			if record_value is None or record_value not in filter_value:
				return False
		return True

class ContextSecretFormatter(logging.Formatter):
	"""
	class ContextSecretFormatter

	This class fulfills two formatting tasks:
	1. It alters the LogRecord to also include a string representation of
		a context dictionary, which can be logged by specifying a log
		format which includes %(contextstring)s
	2. It can replace secret strings specified to a SecretFilter by a
		replacement string, thus censor passwords etc.
	"""
	def __init__(self, orig_formatter: logging.Formatter):
		"""
		ContextSecretFormatter constructor

		This constructor initializes the encapsulated Formatter with
		either one given as parameter or a newly created default one.

		:param orig_formatter: Formatter to encapsulate (my be None).
		:type orig_formatter: logging.Formatter
		"""
		if orig_formatter is None:
			orig_formatter = logging.Formatter()
		self.orig_formatter = orig_formatter
	
	def format(self, record: logging.LogRecord) -> str:
		"""
		Formats a LogRecord.

		This method takes a LogRecord and formats it to produce
		an output string. If context is specified in the LogRecord
		it is used to produce a contextstring which is included in
		the log string if %(contextstring)s is specified in the format.

		:param record: LogRecord to format.
		:type record: logging.LogRecord

		:returns: The formatted log string.
		:rytpe: str
		"""
		if hasattr(record, "context"):
			current_context = record.context
			if isinstance(current_context, dict):
				values = current_context.values()
				record.contextstring = ",".join([str(x) for x in values])
			else:
				record.contextstring = ""
		else:
			record.contextstring = ""
		length = len(record.contextstring)
		if length < CONTEXT_STRING_MIN_LENGTH:
			record.contextstring += " "*(CONTEXT_STRING_MIN_LENGTH - length)
		msg = self.orig_formatter.format(record)
		if record.levelno != logging.SECRET:
			for secret in secret_filter.secrets:
				msg = msg.replace(secret, SECRET_REPLACEMENT_STRING)
		return msg

	def __getattr__(self, attr) -> Any:
		"""
		Retrieves attribute from original formatter.

		This method expects an attribute and returns the valuefor this
		attribute being part of the original formatters namespace.

		:param attr: Any attribute requested from the original formatter.
		:type attr: str

		:returns: Current value of the attribute.
		:rtype: Any
		"""
		return getattr(self.orig_formatter, attr)

class SecretFilter(metaclass=Singleton):
	"""
	class SecretFilter

	This class implements functionality of maintaining a collection
	of secrets which can be used by the ContextSecretFormatter.
	"""
	def __init__(self, min_length: int = 6):
		"""
		SecretFilter constructor.

		This constructor initializes the minimal length of secrets.
		If no value is provided, the default is 6 (characters long).

		:param min_length: Minimal length of a secret string (Default: 6).
		:type min_length: int
		"""
		self._min_length = min_length
		self.secrets = []

	def _initialize_handlers(self):
		"""
		Assign ContextSecretFormatter to Handlers.

		This method iterates of all Handlers of the root logger.
		Each Handler is assigned a ContextSecretFormatter to ensure that
		no secret string is printed into a Log stream.
		"""
		for handler in logging.root.handlers:
			if not isinstance(handler.formatter, ContextSecretFormatter):
				handler.formatter = ContextSecretFormatter(handler.formatter)

	def set_min_length(self, min_length: int):
		"""
		Sets minimal secret length.

		This method assigns a new value to the minimal secret length.
		Any new secret string can only be added, if it has more characters.

		:param min_length: Minimal length of a secret string.
		:type min_length: int
		"""
		self._min_length = min_length

	def clear_secrets(self):
		"""
		Delete all secret strings.

		This method clears the list of secret strings.
		"""
		self.secrets = []

	def add_secrets(self, *secrets: str):
		"""
		Inserts new secret strings.

		This method expects any number of secret strings and adds them to the list.

		:param *secrets: Any number of strings (as individual arguments) to add.
		:type *secrets: str
		"""
		self._initialize_handlers()
		for secret in secrets:
			if secret and len(secret) >= self._min_length and not secret in self.secrets:
				self.secrets.append(secret)

	def remove_secrets(self, *secrets: str):
		"""
		Removes secret strings.

		This method expects any number of secret strings and removes them from the list.

		:param *secrets: Any number of strings (as individual arguments) to remove.
		:type *secrets: str
		"""
		for secret in secrets:
			if secret in self.secrets:
				self.secrets.remove(secret)

last_stderr_format = None
last_file_format = None
def logging_config(
	stderr_level: int = None,
	stderr_format: str = DEFAULT_COLORED_FORMAT,
	log_file: str = None,
	file_level: int = None,
	file_format: str = None
):
	global last_stderr_format
	if stderr_format is None:
		stderr_format = last_stderr_format or DEFAULT_FORMAT
	else:
		last_stderr_format = stderr_format

	global last_file_format
	if file_format is None:
		file_format = last_file_format or DEFAULT_FORMAT
	else:
		last_file_format = file_format

	if stderr_level is not None and stderr_level < 10:
		stderr_level = logging._opsiLevelToLevel[stderr_level]
	if file_level is not None and file_level < 10:
		file_level = logging._opsiLevelToLevel[file_level]

	if log_file:
		remove_all_handlers(logging.FileHandler)
		handler = logging.FileHandler(log_file)
		handler.name = "opsi_file_handler"
		logging.root.addHandler(handler)
	if file_level is not None:
		for handler in get_all_handlers(logging.FileHandler):
			handler.setLevel(file_level)
	if stderr_level is not None:
		remove_all_handlers(logging.StreamHandler)
		handler = logging.StreamHandler(stream = sys.stderr)
		handler.name = "opsi_stderr_handler"
		handler.setLevel(stderr_level)
		logging.root.addHandler(handler)

	if stderr_format and stderr_format.find("(log_color)") != -1 and not sys.stderr.isatty():
		stderr_format = stderr_format.replace('%(log_color)s', '').replace('%(reset)s', '')
	set_format(file_format, stderr_format)

init_logging = logging_config

def set_format(
	file_format: str = DEFAULT_FORMAT,
	stderr_format: str = DEFAULT_COLORED_FORMAT,
	datefmt: str = DATETIME_FORMAT,
	log_colors: Dict = LOG_COLORS
):
	"""
	Assigns ContextSecretFormatter to all Handlers.

	This method takes optional arguments for format, dateformat and log colors
	and creates ContextSecretFormatters considering those.
	Every Handler is assigned such a ContextSecretFormatter.

	:param fmt: Format specification for logging. For documentation see
		https://github.com/python/cpython/blob/3.8/Lib/logging/__init__.py
		Additionally %(contextstring)s may be used to include context.
		If omitted, a default format is used.
	:type fmt: str
	:param datefmt: Date format for logging. If omitted, a default dateformat is used.
	:type datefmt: str
	:param log_colors: Dictionary of colors for different log levels.
		If omitted, a default Color dictionary is used.
	:type log_colors: Dict
	"""
	for handler_type in (logging.StreamHandler, logging.FileHandler):
		for handler in get_all_handlers(handler_type):
			fmt = stderr_format if handler_type is logging.StreamHandler else file_format
			formatter = None
			if fmt.find("(log_color)") >= 0:
				formatter = colorlog.ColoredFormatter(fmt, datefmt=datefmt, log_colors=log_colors)
			else:
				formatter = logging.Formatter(fmt, datefmt=datefmt)
			csformatter = ContextSecretFormatter(formatter)
			handler.setFormatter(csformatter)

@contextmanager
def log_context(new_context : Dict):
	"""
	Contextmanager to set a context.

	This contextmanager sets context to the given one on entering
	and resets to the previous dictionary when leaving.

	:param new_context: new context to set for the section.
	:type new_context: dict
	"""
	try:
		token = set_context(new_context)
		yield
	finally:
		if token is not None:
			context.reset(token)

def set_context(new_context : Dict) -> contextvars.Token:
	"""
	Sets a context.

	This method sets context to the given one and returns a reset-token.

	:param new_context: new context to set.
	:type new_context: dict

	:returns: reset-token for the context (stores previous value).
	:rtype: contextvars.Token
	"""
	if isinstance(new_context, dict):
		return context.set(new_context)

def set_filter(filter_dict : Dict):
	"""
	Sets a new filter dictionary.

	This method expectes a filter dictionary.
	Records are only allowed to pass if their context contains
	this specific dictionary. None means, every record can pass.

	:param filter_dict: Dictionary that must be present in record
		context in order to accept the LogRecord.
	:type filter_dict: Dict
	"""
	for fil in logging.root.filters:
		if isinstance(fil, ContextFilter):
			fil.set_filter(filter_dict)

def set_filter_from_string(filter_string : str):
	"""
	Parses string and sets filter dictionary.

	This method expects a string (e.g. from user input).
	It is parsed to create a dictionary which is set as filter dictionary.
	The parsing rules are:
		*	Entries are separated by ';'.
		*	One entry consists of exactly two strings separated by '='.
		*	The first one is interpreted as key, the second as value(s).
		*	Values of the same key are separated by ','.
	"""
	filter_dict = {}
	if filter_string is None:
		set_filter(None)
		return
	if isinstance(filter_string, str):
		filter_string = filter_string.split(";")
	if not isinstance(filter_string, list):
		raise ValueError("filter_string must be either string or list")
	for part in filter_string:
		entry = part.split("=")
		if len(entry) == 2:
			key = entry[0].strip()
			values = entry[1].split(",")
			filter_dict[key] = [v.strip() for v in values]
	set_filter(filter_dict)

def get_all_loggers():
	return [logging.root] + list(logging.Logger.manager.loggerDict.values())

def get_all_handlers(handler_type = None):
	handlers = []
	for _logger in get_all_loggers():
		if not isinstance(_logger, logging.PlaceHolder):
			for _handler in _logger.handlers:
				if not handler_type or type(_handler) is handler_type:
					handlers.append(_handler)
	return handlers

def remove_all_handlers(handler_type = None):
	for _logger in get_all_loggers():
		if not isinstance(_logger, logging.PlaceHolder):
			for _handler in _logger.handlers:
				if not handler_type or type(_handler) is handler_type:
					_logger.removeHandler(_handler)

def print_logger_info():
	for _logger in get_all_loggers():
		print(f"- Logger: {_logger}", file=sys.stderr)
		if not isinstance(_logger, logging.PlaceHolder):
			for _handler in _logger.handlers:
				print(f"  - Handler: {_handler}", file=sys.stderr)
				print(f"    - Formatter: {_handler.formatter}", file=sys.stderr)

logging_config(stderr_level=logging.WARNING)
#logging_config(stderr_level=logging.NOTSET)
secret_filter = SecretFilter()
context_filter = ContextFilter()
logging.root.addFilter(context_filter)
