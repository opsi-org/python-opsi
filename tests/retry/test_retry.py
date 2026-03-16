# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import pytest

from opsi.retry._common import NoRetry, Retry, RetryConfig, _file_io_backoff_hook, _run_process_backoff_hook, get_retry_config, retry


def test_retry():
	attempts = 0
	for attempt in Retry(RetryConfig(on=ValueError, attempts=4, wait_initial=0.1)):
		with attempt:
			attempts += 1
			if attempts == 3:
				break
			raise ValueError("Test error")

	assert attempts == 3


def test_no_retry():
	attempts = 0
	with pytest.raises(ValueError, match="Test error"):
		for attempt in Retry(NoRetry):
			with attempt:
				attempts += 1
				raise ValueError("Test error")

	assert attempts == 1


def test_retry_decorator():
	attempts = 0

	@retry(RetryConfig(on=ValueError, attempts=4, wait_initial=0.1))
	def test_func():
		nonlocal attempts
		attempts += 1
		if attempts == 3:
			return "Success"
		raise ValueError("Test error")

	result = test_func()
	assert result == "Success"
	assert attempts == 3


def test_get_retry_config():
	config = get_retry_config("file_io")
	assert config.on is _file_io_backoff_hook
	assert config.attempts == 5
	assert config.wait_initial == 0.1

	config = get_retry_config("run_process")
	assert config.on is _run_process_backoff_hook
	assert config.attempts == 5
	assert config.wait_initial == 0.1

	with pytest.raises(ValueError, match="Invalid retry config type: invalid_type"):
		get_retry_config("invalid_type")  # type: ignore[invalid-argument-type]
