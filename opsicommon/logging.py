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
import threading
import asyncio
import warnings

from typing import Dict, Tuple, Any
from logging.handlers import WatchedFileHandler, RotatingFileHandler

from .utils import Singleton
from .loggingconstants import (DEFAULT_COLORED_FORMAT, DEFAULT_FORMAT, DATETIME_FORMAT,
			CONTEXT_STRING_MIN_LENGTH, LOG_COLORS, SECRET_REPLACEMENT_STRING,
			LOG_SECRET, LOG_TRACE, LOG_DEBUG, LOG_INFO, LOG_NOTICE, LOG_WARNING,
			LOG_ERROR, LOG_CRITICAL, LOG_ESSENTIAL, LOG_NONE)

logger = logging.getLogger()

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
		handler = logging.FileHandler(logFile)
		logging.root.addHandler(handler)
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
		for handler in logging.root.handlers:
			if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
				handler.setLevel(logLevel)
	logger.setConsoleLevel = setConsoleLevel

	def setFileLevel(logLevel, object=None):
		warnings.warn(
			"OPSI.Logger.setFileLevel is deprecated, instead modify the FileHandler loglevel.",
			DeprecationWarning
		)
		for handler in logging.root.handlers:
			if isinstance(handler, logging.FileHandler):
				handler.setLevel(logLevel)
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

class ContextFilter(logging.Filter):
	"""
	class ContextFilter

	This class implements a filter which modifies allows to store context
	for a single thread/task.
	"""
	def __init__(self, filter_value : Any=None):
		"""
		ContextFilter Constructor

		This constructor initializes a ContextFilter instance with an
		empty dictionary as context.

		:param filter_value: Value that must be present in record context
			in order to accept the LogRecord.
		:type filter_value: Any
		"""
		super().__init__()
		self._context_lock = threading.Lock()
		self.context = {}
		self.filter_value = filter_value

	def get_identity(self) -> Tuple:
		"""
		Creates identifier for task/process.

		This method collects information about the currently active
		task/thread and returns both the thread_id and the task_id.
		If any of these are not available, 0 is returned instead.

		:returns: thread_id and task_id of running task/thread
		:rtype: Tuple
		"""
		try:
			task_id = id(asyncio.current_task())
		except:
			task_id = 0
		try:
			thread_id = threading.current_thread().ident
		except:
			thread_id = 0
		return thread_id, task_id

	def set_context(self, new_context : Dict):
		"""
		Sets context dictionary for thread/task.
		
		This method expects a context dictionary as argument and stores
		it in the instance context dictionary und a key consisting of
		first the thread id and then the task id of the currently
		running thread/task.

		:param new_context: Context dictionary to assign.
		:type new_context: Dict
		"""
		if not isinstance(new_context, dict):
			return
		self.clean()
		thread_id, task_id = self.get_identity()
		with self._context_lock:
			if self.context.get(thread_id) is None:
				self.context[thread_id] = {}
			self.context[thread_id][task_id] = new_context

	def get_context(self) -> Dict:
		"""
		Returns context of current thread/task.

		This method requests the thread/task identifier,
		looks up the context stored for it and returns it.

		:returns: Context for currently active thread/task.
		:rtype: Dict
		"""
		thread_id, task_id = self.get_identity()
		if self.context.get(thread_id) is None or self.context[thread_id].get(task_id) is None:
			return {}	#DEFAULT_CONTEXT
		return self.context[thread_id][task_id]

	def clean(self):
		"""
		Cleans deprecated context entries.

		This method iterates over the list of stored contexti.
		If the associated thread id and task id are not active any more,
		the entry is deleted. This makes use of a mutex.
		"""
		with self._context_lock:
			try:
				all_tasks = [id(x) for x in asyncio.all_tasks() if not x.done()]
			except:
				all_tasks = []
			all_threads = [x.ident for x in threading.enumerate()]
			#print('\033[93m' + str(self.context) + '\033[0m')
			for thread_id in list(self.context.keys()):
				if thread_id not in all_threads:
					#print("DEBUG: removing from self.context (", thread_id, "- ALL", ",", self.context.pop(thread_id, None), ")")
					self.context.pop(thread_id, None)
				elif thread_id == self.get_identity()[0]:		#only cleanup own thread
					for task_id in list(self.context[thread_id].keys()):
						if not task_id == 0 and task_id not in all_tasks:
							#print("DEBUG: removing from self.context (", thread_id, "-", task_id, ",", self.context[thread_id].pop(task_id, None), ")")
							self.context[thread_id].pop(task_id, None)

	def set_filter_value(self, filter_value : Any=None):
		"""
		Sets a new filter value.

		This method expectes a filter value of any type.
		Records are only allowed to pass if their context contains
		this specific value. None means, every record can pass.

		:param filter_value: Value that must be present in record context
			in order to accept the LogRecord.
		:type filter_value: Any
		"""
		self.filter_value = filter_value

	def filter(self, record : logging.LogRecord) -> bool:
		"""
		Adds context to a LogRecord.

		This method is called by Logger._log and modifies LogRecords.
		It adds the context stored for the current thread/task to the namespace.

		:param record: LogRecord to add context to.
		:type record: LogRecord

		:returns: Always true (if the LogRecord should be kept)
		:rtype: bool
		"""
		my_context = self.get_context()
		record.context = my_context
		if self.filter_value is None or self.filter_value in my_context.values():
			return True
		return False

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
			context = record.context
			if isinstance(context, dict):
				values = context.values()
				record.contextstring = ",".join(values)
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

def init_logging():
	"""
	Initializes logging.

	This method adds a ContextFilter to the root logger.
	Additionally it adds a StreamHandler and makes sure that every
	present Handler is equipped with a ContextSecretFormatter.
	"""
	logging.root.addFilter(ContextFilter())
	if len(logging.root.handlers) == 0:
		handler = logging.StreamHandler(stream=sys.stderr)
		handler.setLevel(logging.NOTICE)
		logging.root.addHandler(handler)
	set_format()

def set_format(fmt : str=DEFAULT_FORMAT, datefmt : str=DATETIME_FORMAT, log_colors : Dict=LOG_COLORS):
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
	colored = (fmt.find("(log_color)") >= 0)
	for handler in logging.root.handlers:
		if colored:
			formatter = colorlog.ColoredFormatter(fmt, datefmt=datefmt, log_colors=log_colors)
		else:
			formatter = logging.Formatter(fmt, datefmt=datefmt)
		csformatter = ContextSecretFormatter(formatter)

		handler.setFormatter(csformatter)

def set_context(new_context : Dict):
	"""
	Sets context for current thread/task.

	This method expects a dictionary of Context. It is added to the
	Context dictionary of the ContextFilter under a key corresponding
	to the thread id and task id of the currently active thread/task.

	:param new_context: New value for the own context.
	:type new_context: Dict
	"""
	for fil in logging.root.filters:
		if isinstance(fil, ContextFilter):
			fil.set_context(new_context)

def set_filter_value(new_value : Any):
	"""
	Sets a new filter value.

	This method expectes a filter value of any type.
	Records are only allowed to pass if their context contains
	this specific value. None means, every record can pass.

	:param filter_value: Value that must be present in record context
		in order to accept the LogRecord.
	:type filter_value: Any
	"""
	for fil in logging.root.filters:
		if isinstance(fil, ContextFilter):
			fil.set_filter_value(new_value)

init_logging()
secret_filter = SecretFilter()
