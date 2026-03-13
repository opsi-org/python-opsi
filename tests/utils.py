# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from contextlib import contextmanager
from io import StringIO
from typing import Generator

from opsi.logging import use_logging_config


@contextmanager
def log_stream(new_level: int, format: str | None = None) -> Generator[StringIO, None, None]:
	stream = StringIO()
	with use_logging_config(stderr_level=new_level, stderr_format=format, stderr_file=stream):
		yield stream
