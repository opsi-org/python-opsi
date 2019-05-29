# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2018-2019 uib GmbH <info@uib.de>

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
Asynchronous backend wrapper.

This allows having synchronous backends wrapped for use in an
asynchronous way with async/await.

Please note that this module is considered internal and available
functionality may change at any time without prior notice.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import inspect
import functools
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

__all__ = ('AsyncBackendWrapper', )


class AsyncBackendWrapper:
	def __init__(self, backend, loop=None):
		self.backend = backend

		self.loop = loop or get_event_loop()
		self.pool = ThreadPoolExecutor(max_workers=2)

		self._wrapBackend()

	def _wrapBackend(self):
		def make_async(f):
			@functools.wraps(f)
			async def wrapped(*args, **kwargs):
				partialFunc = functools.partial(f, *args, **kwargs)
				return await self.loop.run_in_executor(self.pool, partialFunc)

			return wrapped

		methods = inspect.getmembers(self.backend, inspect.ismethod)
		for name, funcRef in methods:
			if name.startswith('_'):  # Protected or private
				continue

			if hasattr(self, name):
				continue

			setattr(self, name, make_async(funcRef))

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self._synchronousBackendExit()

	async def backend_exit(self):
		self._synchronousBackendExit()

	def _synchronousBackendExit(self):
		try:
			self.backend.backend_exit()
		except Exception:
			pass

		self.pool.shutdown()