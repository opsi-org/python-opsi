import logging
import threading
import asyncio
import sys
import colorlog

DEFAULT_COLORED_FORMAT = "%(log_color)s[%(opsilevel)d] [%(asctime)s.%(msecs)03d]%(reset)s %(context)s %(message)s   (%(filename)s:%(lineno)d)"
DEFAULT_FORMAT = "[%(opsilevel)d] [%(asctime)s.%(msecs)03d] [%(context)s] %(message)s   (%(filename)s:%(lineno)d)"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_COLORS = {
	'SECRET': 'thin_yellow',
	'TRACE': 'thin_white',
	'DEBUG': 'white',
	'INFO': 'bold_white',
	'NOTICE': 'bold_green',
	'WARNING': 'bold_yellow',
	'ERROR': 'red',
	'CRITICAL': 'bold_red',
	'ESSENTIAL': 'bold_cyan'
}

def get_identity():
	try:
		task_id = id(asyncio.Task.current_task())
	except:
		task_id = 0
	try:
		thread_id = threading.current_thread().ident
	except:
		thread_id = 0
	return thread_id, task_id

class ContextFilter(logging.Filter):
	def __init__(self):
		super().__init__()
		self._context_lock = threading.Lock()
		self.context = {}

	def set_context(self, new_context):
		self.clean()
		thread_id, task_id = get_identity()
		with self._context_lock:
			if self.context.get(thread_id) is None:
				self.context[thread_id] = {}
			self.context[thread_id][task_id] = new_context

	def get_context(self):
		thread_id, task_id = get_identity()
		if self.context.get(thread_id) is None or self.context[thread_id].get(task_id) is None:
			return ""	#DEFAULT_CONTEXT
		return self.context[thread_id][task_id]

	def clean(self):
		with self._context_lock:
			try:
				all_tasks = [id(x) for x in asyncio.Task.all_tasks() if not x.done()]
			except:
				all_tasks = []
			all_threads = [x.ident for x in threading.enumerate()]
			#print('\033[93m' + str(self.context) + '\033[0m')
			for thread_id in list(self.context.keys()):
				if thread_id not in all_threads:
					#print("DEBUG: removing from self.context (", thread_id, "- ALL", ",", self.context.pop(thread_id, None), ")")
					self.context.pop(thread_id, None)
				elif thread_id == get_identity()[0]:		#only cleanup own thread
					for task_id in list(self.context[thread_id].keys()):
						if not task_id == 0 and task_id not in all_tasks:
							#print("DEBUG: removing from self.context (", thread_id, "-", task_id, ",", self.context[thread_id].pop(task_id, None), ")")
							self.context[thread_id].pop(task_id, None)


	def filter(self, record):
		if len(self.get_context()) == 0:
			record.context = ""
		else:
			record.context = "[" + self.get_context() + "]"
		return True

class ContextLogger(logging.Logger):
	def __init__(self, name="contextlogger", colored=True):
		super().__init__(name)

		console_formatter = self.get_new_formatter(colored=colored)
		log_handler = logging.StreamHandler(stream=sys.stderr)
		log_handler.setFormatter(console_formatter)
		self.addHandler(log_handler)
		self.cfilter = ContextFilter()
		self.addFilter(self.cfilter)

	def get_new_formatter(self, fmt=DEFAULT_FORMAT, datefmt=DATETIME_FORMAT, log_colors=LOG_COLORS, colored=True):
		if colored:
			return colorlog.ColoredFormatter(fmt, datefmt=datefmt, log_colors=log_colors)
		return logging.Formatter(fmt, datefmt=datefmt)

	def set_format(self, fmt=None, datefmt=None, log_colors=None, colored=True):
		if fmt is None:
			fmt = DEFAULT_FORMAT
		if datefmt is None:
			datefmt = DATETIME_FORMAT
		if log_colors is None:
			log_colors = LOG_COLORS
		for h in self.handlers:
			f = self.get_new_formatter(fmt=fmt, datefmt=datefmt, log_colors=log_colors, colored=colored)
			h.setFormatter(f)

	def set_context(self, new_context):
		self.cfilter.set_context(new_context)