# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import multiprocessing
import platform
import queue
import threading
import time
from pathlib import Path

import pytest

from opsi.system.file.lock import LockMethod, lock_file


class Task:
	def __init__(
		self,
		task_id: int,
		file: Path,
		res_queue: queue.Queue,
		exclusive: bool,
		timeout: float,
		lock_method: LockMethod | None,
		wait: float,
	) -> None:
		self.task_id = task_id
		self.file = file
		self.exclusive = exclusive
		self.timeout = timeout
		self.lock_method = lock_method
		self.wait = wait
		self.res_queue = res_queue

	def run(self) -> None:
		start = time.monotonic()
		result: str | Exception | None = None
		try:
			with open(self.file, "a+", encoding="utf8") as test_fh:
				with lock_file(test_fh, exclusive=self.exclusive, timeout=self.timeout, lock_method=self.lock_method):
					test_fh.seek(0)
					data = test_fh.read()
					if self.exclusive:
						test_fh.seek(0)
						test_fh.write(",".join([str(self.task_id)] * 10))
						test_fh.truncate()
					result = data
					time.sleep(self.wait)
		except Exception as err:
			result = err
		self.res_queue.put((result, time.monotonic() - start))


class ThreadTask(threading.Thread):
	def __init__(
		self,
		task_id: int,
		file: Path,
		res_queue: queue.Queue,
		exclusive: bool,
		timeout: float,
		lock_method: LockMethod | None,
		wait: float,
	) -> None:
		threading.Thread.__init__(self)
		self.task = Task(task_id, file, res_queue, exclusive, timeout, lock_method, wait)

	def run(self) -> None:
		self.task.run()


class MultiprocessTask(multiprocessing.Process):
	def __init__(
		self,
		task_id: int,
		file: Path,
		res_queue: queue.Queue,
		exclusive: bool,
		timeout: float,
		lock_method: LockMethod | None,
		wait: float,
	) -> None:
		multiprocessing.Process.__init__(self)
		self.task = Task(task_id, file, res_queue, exclusive, timeout, lock_method, wait)

	def run(self) -> None:
		self.task.run()


@pytest.mark.parametrize(
	"task_type, lock_method",
	# (ThreadTask, MultiprocessTask),
	(
		(MultiprocessTask, LockMethod.FLOCK),
		(ThreadTask, LockMethod.FLOCK),
		(MultiprocessTask, LockMethod.LOCKF),
	)
	if platform.system() == "Linux"
	else (
		(MultiprocessTask, None),
		(ThreadTask, None),
	),
)
def test_lock_file(tmp_path: Path, task_type: type, lock_method: LockMethod | None) -> None:
	test_file = tmp_path / "test.bin"
	res_queue: queue.Queue | multiprocessing.Queue = queue.Queue() if task_type == ThreadTask else multiprocessing.Queue()

	# Exclusive lock / write lock
	num_tasks = 10
	tasks = [
		task_type(task_id=task_id, file=test_file, res_queue=res_queue, exclusive=True, timeout=1.0, lock_method=lock_method, wait=3.0)
		for task_id in range(num_tasks)
	]
	for task in tasks:
		task.start()
	for task in tasks:
		task.join()

	results = [res_queue.get(timeout=5.0) for _ in range(num_tasks)]
	err_results = [r for r in results if isinstance(r[0], Exception)]
	assert len(err_results) == num_tasks - 1
	for res in err_results:
		assert 1.0 < res[1] < 2.0

	task_ids = test_file.read_text(encoding="utf-8").split(",")
	assert len(task_ids) == 10
	for task_id in task_ids:
		assert task_id == task_ids[0]

	file_data = "opsi" * 10
	test_file.write_text(file_data, newline="")

	# Shared lock / read lock
	num_tasks = 10
	tasks = [
		task_type(task_id=task_id, file=test_file, res_queue=res_queue, exclusive=False, timeout=1.0, lock_method=lock_method, wait=3.0)
		for task_id in range(num_tasks)
	]
	for task in tasks:
		task.start()
	for task in tasks:
		task.join()

	results = [res_queue.get(timeout=5.0) for _ in range(num_tasks)]
	success_results = [r for r in results if not isinstance(r[0], Exception)]
	assert len(success_results) == num_tasks
	for res in success_results:
		assert res[0] == file_data
		assert res[0] == file_data
		assert res[0] == file_data
