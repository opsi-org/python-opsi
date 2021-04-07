#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Manual tests for the HTTPConnectionPool.
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
