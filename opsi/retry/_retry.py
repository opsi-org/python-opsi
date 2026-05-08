# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations


from dataclasses import dataclass

from stamina import retry as _retry_decorator
from stamina import retry_context as _retry_context
from stamina._core import ExcOrBackoffHook, _RetryContextIterator
from stamina.instrumentation import RetryDetails, RetryHook, get_on_retry_hooks, set_on_retry_hooks
from opsi.util.pattern import MappedStrEnum
from opsi.logging import get_logger
import enum

logger = get_logger("opsi")


"""
Retry helpers and predefined retry configurations.

This module wraps stamina retry primitives used across opsi and provides
shared retry presets for common retry scenarios.
"""


class RetryConfigType(MappedStrEnum):
	FILE_IO = "file_io"
	RUN_PROCESS = "run_process"

	_NAME = enum.nonmember("retry config type")


@dataclass(kw_only=True, slots=True, frozen=True)
class RetryConfig:
	"""
	Configuration for retry decorators and retry contexts.

	Attributes
	----------
	on : ExcOrBackoffHook
		Callable deciding whether an exception should trigger a retry.

	attempts : int, default: 5
		Number of total attempts including the initial attempt.

	timeout : float, default: 45.0
		Maximum total time in seconds for all attempts.

	wait_initial : float, default: 0.1
		Minimum backoff time in seconds before the first retry.

	wait_max : float, default: 5.0
		Maximum backoff time in seconds between retries at any time.

	wait_jitter : float, default: 1.0
		Maximum jitter that is added to retry backoff delays in seconds.
		The actual jitter added is a random number between 0 and <wait_jitter>.

	wait_exp_base : float, default: 2
		The exponential base used to compute the retry backoff.
	"""

	on: ExcOrBackoffHook
	attempts: int = 5
	timeout: float = 45.0
	wait_initial: float = 0.1
	wait_max: float = 5.0
	wait_jitter: float = 1.0
	wait_exp_base: float = 2


NoRetry = RetryConfig(on=lambda exc: False, attempts=0)


def retry(retry_config: RetryConfig | None = None):
	"""
	Create a retry decorator from a retry configuration.

	Parameters
	----------
	retry_config : RetryConfig, optional
		Retry settings to apply. If omitted, default retry settings are used.

	Returns
	-------
	Callable
		A configured stamina retry decorator.
	"""
	return _retry_decorator(
		on=retry_config.on if retry_config else OSError,
		attempts=retry_config.attempts if retry_config else 5,
		timeout=retry_config.timeout if retry_config else 45.0,
		wait_initial=retry_config.wait_initial if retry_config else 0.1,
		wait_max=retry_config.wait_max if retry_config else 5.0,
		wait_jitter=retry_config.wait_jitter if retry_config else 1.0,
		wait_exp_base=retry_config.wait_exp_base if retry_config else 2,
	)


def Retry(retry_config: RetryConfig) -> _RetryContextIterator:
	"""
	Create a retry context iterator from a retry configuration.

	Parameters
	----------
	retry_config : RetryConfig
		Retry settings to apply.

	Returns
	-------
	_RetryContextIterator
		A configured retry context iterator.
	"""
	return _retry_context(
		on=retry_config.on,
		attempts=retry_config.attempts,
		timeout=retry_config.timeout,
		wait_initial=retry_config.wait_initial,
		wait_max=retry_config.wait_max,
		wait_jitter=retry_config.wait_jitter,
		wait_exp_base=retry_config.wait_exp_base,
	)


def _file_io_backoff_hook(exception: Exception) -> bool:
	"""
	Return whether a file I/O exception should be retried.
	"""
	if isinstance(exception, OSError):
		winerror = getattr(exception, "winerror", None)
		if winerror and winerror >= 4390 and winerror <= 4394:
			# Windows REPARSE errors will persist
			return False
		return True
	return False


def _run_process_backoff_hook(exception: Exception) -> bool:
	"""
	Return whether a process execution exception should be retried.
	"""
	from opsi.process import ProcessError

	# TODO: Retry on FileNotFoundError on Windows?
	return not isinstance(exception, (ProcessError, FileNotFoundError, TimeoutError))


def get_retry_config(type: RetryConfigType | str = RetryConfigType.FILE_IO) -> RetryConfig:
	"""
	Return a predefined retry configuration.

	Parameters
	----------
	type : RetryConfigType, default: RetryConfigType.FILE_IO
		Name of the retry configuration preset.

	Returns
	-------
	RetryConfig
		The requested retry configuration.

	Raises
	------
	ValueError
		If the retry configuration type is unknown.
	"""
	type = RetryConfigType(type)
	if type == RetryConfigType.FILE_IO:
		return RetryConfig(on=_file_io_backoff_hook, attempts=5, wait_initial=0.1)
	if type == RetryConfigType.RUN_PROCESS:
		return RetryConfig(on=_run_process_backoff_hook, attempts=5, wait_initial=0.1)
	raise ValueError(f"Invalid retry config type: {type}")


def logging_hook(details: RetryDetails) -> None:
	"""
	Log information about a scheduled retry.

	Parameters
	----------
	details : RetryDetails
		Retry metadata provided by stamina.
	"""
	logger.notice(
		"A retry has been scheduled: error=%r, retry_num=%d, wait_for=%0.2fs, waited_so_far=%0.2fs",
		details.caused_by,
		details.retry_num,
		details.wait_for,
		details.waited_so_far,
	)


def add_retry_hook(hook: RetryHook) -> None:
	"""
	Add a hook to be called after a retry has been scheduled.

	Parameters
	----------
	hook : RetryHook
		Hook to call after a retry has been scheduled. To deactivate instrumentation, pass an empty iterable to set_on_retry_hooks.
	"""
	current_hooks = get_on_retry_hooks()
	if hook in current_hooks:
		return  # Avoid adding the same hook multiple times
	set_on_retry_hooks(current_hooks + (hook,))


def get_retry_hooks() -> tuple[RetryHook, ...]:
	"""
	Return the currently registered retry hooks.

	Returns
	-------
	tuple[RetryHook, ...]
		Currently registered retry hooks.
	"""
	return get_on_retry_hooks()


def remove_retry_hook(hook: RetryHook) -> None:
	"""
	Remove a previously added retry hook.

	Parameters
	----------
	hook : RetryHook
		Hook to remove from the list of hooks called after a retry has been scheduled.
	"""
	current_hooks = get_on_retry_hooks()
	new_hooks = tuple(h for h in current_hooks if h != hook)
	if len(new_hooks) == len(current_hooks):
		return  # Hook was not found, no changes needed
	set_on_retry_hooks(new_hooks)


add_retry_hook(logging_hook)
