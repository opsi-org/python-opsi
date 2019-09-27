#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
Manual tests for the HTTPConnectionPool.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import time

from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Util.HTTP import HTTPSConnectionPool

LOGGER = Logger()


def main():
	pool = HTTPSConnectionPool(
		host='download.uib.de',
		port=443,
		connectTimeout=5,
		# caCertFile='/tmp/xxx',
		# verifyServerCertByCa=True
	)
	resp = pool.urlopen('GET', url='/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	LOGGER.notice(resp.data)
	time.sleep(5)
	resp = pool.urlopen('GET', url='/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	LOGGER.notice(resp.data)
	resp = pool.urlopen('GET', url='/www/home/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	LOGGER.notice(resp.headers)
	resp = pool.urlopen('GET', url='/www/home/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	LOGGER.notice(resp.data)
	LOGGER.notice(resp.headers)
	LOGGER.notice(resp.status)
	LOGGER.notice(resp.version)
	LOGGER.notice(resp.reason)
	LOGGER.notice(resp.strict)


if __name__ == '__main__':
	LOGGER.setConsoleLevel(LOG_DEBUG)
	LOGGER.setConsoleColor(True)

	main()
