# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from stamina import instrumentation
from stamina import retry as _retry_decorator
from stamina import retry_context as _retry_context
from stamina._core import ExcOrBackoffHook, _RetryContextIterator

from opsi.logging import OPSILogger, get_logger

logger: OPSILogger = get_logger()


@dataclass(kw_only=True, slots=True, frozen=True)
class RetryConfig:
	on: ExcOrBackoffHook
	attempts: int = 5
	timeout: float = 45.0
	wait_initial: float = 0.1
	wait_max: float = 5.0
	wait_jitter: float = 1.0
	wait_exp_base: float = 2


NoRetry = RetryConfig(on=lambda exc: False, attempts=0)


def retry(retry_config: RetryConfig | None = None):
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
	return isinstance(exception, OSError)


def _run_process_backoff_hook(exception: Exception) -> bool:
	from opsi.process import ProcessError

	return not isinstance(exception, (ProcessError, TimeoutError))


def get_retry_config(type: Literal["file_io", "run_process"] = "file_io") -> RetryConfig:
	if type == "file_io":
		return RetryConfig(on=_file_io_backoff_hook, attempts=5, wait_initial=0.1)
	if type == "run_process":
		return RetryConfig(on=_run_process_backoff_hook, attempts=5, wait_initial=0.1)
	raise ValueError(f"Invalid retry config type: {type}")


def logging_hook(details: instrumentation.RetryDetails) -> None:
	logger.notice(
		"A retry has been scheduled: error=%r, retry_num=%d, wait_for=%0.2fs, waited_so_far=%0.2fs",
		details.caused_by,
		details.retry_num,
		details.wait_for,
		details.waited_so_far,
	)


instrumentation.set_on_retry_hooks([logging_hook])
