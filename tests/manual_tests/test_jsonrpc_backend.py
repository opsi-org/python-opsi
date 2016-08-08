#! /usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

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
Manual tests for the JSONRPCBackend.

:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import time
import threading
from OPSI.Logger import Logger, LOG_INFO
from OPSI.Backend.JSONRPC import JSONRPCBackend


logger = Logger()


def checkIfMultipleCallsSucceed():
	be = JSONRPCBackend(
		address='192.168.105.1',
		username='exp-40-wks-001.test.invalid',
		password='352360038fb824baf836a6b448845745'
	)
	first = be.backend_info()
	second = be.backend_info()
	third = be.backend_info()

	assert first == second
	assert second == third


def checkIfConnectionWithCertWorks():
	be = JSONRPCBackend(
		address='192.168.1.14',
		username='stb-40-wks-120.test.invalid',
		password='8ca221eee05e574c58fcc1d3d99de17c',
		serverCertFile='/tmp/server-cert.pem',
		verifyServerCert=True
	)


def checkAsynchronosProcessing():
	be = JSONRPCBackend(
		address='192.168.1.14',
		username = 'someone',
		password = '123'
	)
	print(be.authenticated())

	def callback(jsonrpc):
		print(jsonrpc.result)

	class Thread(threading.Thread):
		def __init__(self, be):
			threading.Thread.__init__(self)
			self.be = be

		def run(self):
			for i in range(5):
				be.authenticated().setCallback(callback)
				time.sleep(0.3)

	be = JSONRPCBackend(
		address='192.168.1.14',
		username='stb-40-wks-120.test.invalid',
		password='8ca221eee05e574c58fcc1d3d99de17c',
		deflate=True,
		connectionPoolSize=30
	)

	be.setAsync(True)

	threads = [Thread(be) for i in range(20)]
	[t.start() for t in threads]
	[t.join() for t in threads]

	runs = 0
	while runs < 10:
		print(be.authenticated())
		print(be.group_getIdents())
		print(be.host_getIdents())
		time.sleep(2)
		runs += 1

	be.setAsync(True)

	#jsonrpc1 = JSONRPC(jsonrpcBackend = be, baseUrl = be._baseUrl, method = 'authenticated', params = [], retry = False)
	be.authenticated().setCallback(callback)
	#jsonrpc2 = JSONRPC(jsonrpcBackend = be, baseUrl = be._baseUrl, method = 'group_getIdents', params = [], retry = False)
	be.group_getIdents().setCallback(callback)
	#jsonrpc3 = JSONRPC(jsonrpcBackend = be, baseUrl = be._baseUrl, method = 'host_getIdents', params = [], retry = False)
	be.host_getIdents().setCallback(callback)
	be.host_getIdents().setCallback(callback)
	be.host_getIdents().setCallback(callback)
	be.host_getIdents().setCallback(callback)
	be.host_getIdents().setCallback(callback)

	be.setAsync(False)
	print("===", be.host_getIdents())

	be.backend_exit()


def main():
	checkIfMultipleCallsSucceed()
	checkIfConnectionWithCertWorks()
	checkAsynchronosProcessing()


if __name__ == '__main__':

	logger.setConsoleLevel(LOG_INFO)
	logger.setConsoleColor(True)

	main()
