# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import gc
import sys
import os
import platform
import threading
from contextlib import contextmanager
from io import StringIO
from typing import Generator, Mapping, TextIO

from psutil import Process

from opsi.logging import use_logging_config


class MemoryUsageMonitor(threading.Thread):
	def __init__(self, interval: float = 1.0) -> None:
		super().__init__(daemon=True)
		self._interval = max(interval, 0.01)
		self._process = Process(os.getpid())
		self._should_stop = threading.Event()
		self._system = platform.system()
		self.started = threading.Event()
		self.stopped = threading.Event()
		self.rss_values: list[float] = []

	def _memory_cleanup(self) -> None:
		gc.collect()
		if self._system == "Linux":
			ctypes.CDLL("libc.so.6").malloc_trim(0)

	def run(self) -> None:
		self._memory_cleanup()
		self.rss_values.append(self._process.memory_info().rss)
		self.started.set()
		while not self._should_stop.wait(self._interval):
			self.rss_values.append(self._process.memory_info().rss)
		self._memory_cleanup()
		self.rss_values.append(self._process.memory_info().rss)
		self.stopped.set()

	def stop(self) -> None:
		self._should_stop.set()
		self.stopped.wait(self._interval + 1.0)

	def print_stats(self, file: TextIO | None = None) -> None:
		file = file or sys.stdout
		print("Memory usage statistics:", file=file)
		print(f"  Start RSS: {self.start_rss / 1_000_000:.2f} MB", file=file)
		print(f"  End RSS: {self.end_rss / 1_000_000:.2f} MB", file=file)
		print(f"  Min RSS: {self.min_rss / 1_000_000:.2f} MB", file=file)
		print(f"  Max RSS: {self.max_rss / 1_000_000:.2f} MB", file=file)
		print(f"  Avg RSS: {self.avg_rss / 1_000_000:.2f} MB", file=file)
		print(f"  Max increase RSS: {self.max_increase_rss / 1024 / 1024:.2f} MB", file=file)

	@property
	def max_increase_rss(self) -> float:
		return (max(self.rss_values) - self.start_rss) if self.rss_values else 0.0

	@property
	def max_rss(self) -> float:
		return max(self.rss_values) if self.rss_values else 0.0

	@property
	def min_rss(self) -> float:
		return min(self.rss_values) if self.rss_values else 0.0

	@property
	def avg_rss(self) -> float:
		return (sum(self.rss_values) / len(self.rss_values)) if self.rss_values else 0.0

	@property
	def start_rss(self) -> float:
		return self.rss_values[0] if self.rss_values else 0.0

	@property
	def end_rss(self) -> float:
		return self.rss_values[-1] if self.rss_values else 0.0


@contextmanager
def memory_usage_monitor(interval: float = 1.0) -> Generator[MemoryUsageMonitor, None, None]:
	monitor = MemoryUsageMonitor(interval)
	monitor.start()
	monitor.started.wait(5.0)
	try:
		yield monitor
	finally:
		if monitor.is_alive():
			monitor.stop()


@contextmanager
def environment(env_vars: Mapping[str, str]) -> Generator[dict[str, str], None, None]:
	old_environ = os.environ.copy()
	os.environ.update(env_vars)
	try:
		yield dict(os.environ.items())
	finally:
		os.environ.clear()
		os.environ.update(old_environ)


@contextmanager
def log_stream(new_level: int, format: str | None = None) -> Generator[StringIO, None, None]:
	stream = StringIO()
	with use_logging_config(stderr_level=new_level, stderr_format=format, stderr_file=stream):
		yield stream
