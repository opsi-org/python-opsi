import logging
import threading
import asyncio
import sys

DEFAULT_FORMAT = "%(log_color)s[%(opsilevel)d] [%(asctime)s.%(msecs)03d]%(reset)s %(message)s   (%(filename)s:%(lineno)d)"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class ContextLogger(logging.Logger):
	def __init__(self, name="mylogger", level=logging.INFO):
		logging.basicConfig(stream=sys.stderr, level=level, format=DEFAULT_FORMAT)
		super().__init__(name)
		self._context_lock = threading.Lock()
		self.context = {}

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
				elif thread_id == self.get_identity()[0]:		#only cleanup own thread
					for task_id in list(self.context[thread_id].keys()):
						if not task_id == 0 and task_id not in all_tasks:
							#print("DEBUG: removing from self.context (", thread_id, "-", task_id, ",", self.context[thread_id].pop(task_id, None), ")")
							self.context[thread_id].pop(task_id, None)

	def get_identity(self):
		try:
			task_id = id(asyncio.Task.current_task())
		except:
			task_id = 0
		try:
			thread_id = threading.current_thread().ident
		except:
			thread_id = 0
		return thread_id, task_id

	def context_dict(self):
		return {"context" : self.get_context()}

	def set_context(self, new_context):
		self.clean()
		thread_id, task_id = self.get_identity()
		with self._context_lock:
			if self.context.get(thread_id) is None:
				self.context[thread_id] = {}
			self.context[thread_id][task_id] = new_context

	def get_context(self):
		thread_id, task_id = self.get_identity()
		if self.context.get(thread_id) is None or self.context[thread_id].get(task_id) is None:
			return "DEFAULT CONTEXT"
		return self.context[thread_id][task_id]

	# This relies on Logger.error() etc calling self._log()
	def _log(self, level, msg, *args, **kwargs):
	#	kwargs.update( {'extra' : self.context_dict()} )
		return logging.root._log(level, msg, *args, **kwargs)