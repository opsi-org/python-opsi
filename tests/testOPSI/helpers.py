# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Helpers for testing opsi.
"""

import os
import shutil
import tempfile
import threading
import socket
from contextlib import closing, contextmanager
import http.server
import socketserver

import unittest.mock as mock

from OPSI.Util.Path import cd



class HTTPFileServerRequestHandler(http.server.SimpleHTTPRequestHandler):
	def do_PUT(self):
		"""Serve a PUT request."""
		path = self.translate_path(self.path)
		length = int(self.headers['Content-Length'])
		with open(path, 'wb') as file:
			file.write(self.rfile.read(length))
		self.send_response(201, "Created")
		self.end_headers()


class HTTPFileServer(threading.Thread):
	def __init__(self, directory):
		super().__init__()
		self.directory = directory
		# Auto select free port
		with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
			sock.bind(('', 0))
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.port = sock.getsockname()[1]
		self.server = None

	def run(self):
		directory = self.directory
		class Handler(HTTPFileServerRequestHandler):
			def __init__(self, *args, **kwargs):
				super().__init__(*args, directory=directory, **kwargs)
		self.server = socketserver.TCPServer(("", self.port), Handler)
		#print("Server started at localhost:" + str(self.port))
		self.server.serve_forever()

	def stop(self):
		if self.server:
			self.server.shutdown()


@contextmanager
def http_file_server(directory):
	server = HTTPFileServer(directory)
	server.daemon = True
	server.start()
	try:
		yield server
	finally:
		server.stop()


@contextmanager
def workInTemporaryDirectory(tempDir=None):
	"""
	Creates a temporary folder to work in. Deletes the folder afterwards.

	:param tempDir: use the given dir as temporary directory. Will not \
be deleted if given.
	"""
	temporary_folder = tempDir or tempfile.mkdtemp()
	with cd(temporary_folder):
		try:
			yield temporary_folder
		finally:
			if not tempDir:
				try:
					shutil.rmtree(temporary_folder)
				except OSError:
					pass



@contextmanager
def createTemporaryTestfile(original, tempDir=None):
	'''Copy `original` to a temporary directory and \
yield the path to the new file.

	The temporary directory can be specified overridden with `tempDir`.'''

	with workInTemporaryDirectory(tempDir) as targetDir:
		shutil.copy(original, targetDir)

		filename = os.path.basename(original)

		yield os.path.join(targetDir, filename)


def getLocalFQDN():
	'Get the FQDN of the local machine.'
	# Lazy imports to not hinder other tests.
	from OPSI.Types import forceHostId
	from OPSI.Util import getfqdn

	return forceHostId(getfqdn())


@contextmanager
def patchAddress(fqdn="opsi.test.invalid", address="172.16.0.1"):
	"""
	Modify the results of socket so that expected addresses are returned.

	:param fqdn: The FQDN to use. Everything before the first '.' will serve\
as hostname.
	:param address: The IP address to use.
	"""
	fqdn = fqdn
	hostname = fqdn.split(".")[0]
	address = address

	def getfqdn(*_):
		return fqdn

	def gethostbyaddr(*_):
		return (fqdn, [hostname], [address])

	with mock.patch('socket.getfqdn', getfqdn):
		with mock.patch('socket.gethostbyaddr', gethostbyaddr):
			yield


@contextmanager
def patchEnvironmentVariables(**environmentVariables):
	"""
	Patches to environment variables to be empty during the context.
	Anything supplied as keyword argument will be added to the environment.
	"""
	originalEnv = os.environ.copy()
	try:
		os.environ.clear()
		for key, value in environmentVariables.items():
			os.environ[key] = value

		yield
	finally:
		os.environ = originalEnv


@contextmanager
def fakeGlobalConf(fqdn="opsi.test.invalid", dir=None):
	"Fake a global.conf and return the path to the file."

	with workInTemporaryDirectory(dir) as tempDir:
		configPath = os.path.join(tempDir, 'global.conf')

		with open(configPath, "w") as conf:
			conf.write("""[global]
hostname = {0}
""".format(fqdn))

		yield configPath


@contextmanager
def showLogs(logLevel=7, color=True):
	"""
	A contextmanager that returns a usable logger that is configured
	to log debug output.
	"""
	from OPSI.Logger import Logger

	logger = Logger()

	logLevelBefore = logger.getConsoleLevel()

	# We might want to have a better log format:
	# logger.setLogFormat(u'[%l] [%D] %M (%F|%N)')

	try:
		logger.setConsoleLevel(logLevel)
		logger.setConsoleColor(color)
		yield logger
	finally:
		logger.setConsoleLevel(logLevelBefore)


@contextmanager
def cleanMandatoryConstructorArgsCache():
	with mock.patch('opsicommon.objects._MANDATORY_CONSTRUCTOR_ARGS_CACHE', {}):
		yield
