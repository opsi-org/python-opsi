# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from collections.abc import Generator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN, flock, lockf
from time import monotonic, sleep
from typing import IO, BinaryIO, TextIO

from opsi.logging import get_logger
from opsi.system.file.lock._common import LockMethod

LD_LIBRARY_EXCLUDE_LIST = ["/usr/lib/opsiclientd"]

logger = get_logger("opsi")


@contextmanager
def lock_file(
	file: TextIO | BinaryIO | IO, exclusive: bool = False, timeout: float = 5.0, lock_method: LockMethod | None = None
) -> Generator[None]:
	"""
	Lock a file using either flock or lockf.
	:param file: The file to lock.
	:param exclusive: If True, acquire an exclusive lock; otherwise, a shared lock.
	:param timeout: Maximum time to wait for the lock in seconds.
	:param lock_method: Use LockMethod.FLOCK (default) for fcntl.flock or LockMethod.LOCKF for fcntl.lockf.
	:raises TimeoutError: If the lock cannot be acquired within the specified timeout.
	:raises ValueError: If an invalid lock_method is specified.
	"""
	lock_flags = LOCK_NB | (LOCK_EX if exclusive else LOCK_SH)
	start = monotonic()
	lock_meth = lockf if lock_method == LockMethod.LOCKF else flock
	while True:
		try:
			lock_meth(file, lock_flags)
			break
		except (OSError, BlockingIOError):
			if monotonic() >= start + timeout:
				raise TimeoutError(f"Failed to lock file after {timeout:0.2f} seconds") from None
			sleep(0.1)
	try:
		yield
		file.flush()
	finally:
		lock_meth(file, LOCK_UN)
