# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""
import pytest
import os

import time
import subprocess
import http.server
import socketserver
import ssl
import threading

from opsicommon.ssl import install_ca
from OPSI.System import execute, isCentOS, isDebian, isOpenSUSE, isRHEL, isSLES, isUbuntu




def create_certification():
	print("create_certification")
	openssl = "openssl req -nodes -x509 -newkey rsa:2048 -days 730 -keyout tests/testopsicommon/data/ssl/ca.key -out tests/testopsicommon/data/ssl/ca.crt -new -sha512 -subj /C=DE/ST=RP/L=Mainz/O=uib/OU=root/CN=uib-Signing-Authority"
	print(openssl.split(" "))
	r = subprocess.call(openssl.split(" "), encoding="utf-8")
	print("?", r)
	openssl = "openssl req -nodes -newkey rsa:2048 -keyout tests/testopsicommon/data/ssl/test-server.key -out tests/testopsicommon/data/ssl/test-server.csr -subj /C=DE/ST=RP/L=Mainz/O=uib/OU=root/CN=test-server"
	r = subprocess.call(openssl.split(" "), encoding="utf-8")
	print(r)
	openssl = "openssl ca -batch -config tests/testopsicommon/data/ssl/ca.conf -notext -in tests/testopsicommon/data/ssl/test-server.csr -out tests/testopsicommon/data/ssl/test-server.crt"
	r = subprocess.call(openssl.split(" "), encoding="utf-8")
	print(r)
	openssl = "openssl ca -config ca.conf -gencrl -keyfile tests/testopsicommon/data/ssl/ca.key -cert ca.crt -out tests/testopsicommon/data/ssl/root.crl.pem"
	r = subprocess.call(openssl.split(" "), encoding="utf-8")
	print(r)
	openssl = "openssl crl -inform PEM -in tests/testopsicommon/data/ssl/root.crl.pem -outform DER -out tests/testopsicommon/data/ssl/root.crl"
	r = subprocess.call(openssl.split(" "), encoding="utf-8")
	print(r)
	print("create_certification done...")

@pytest.fixture(scope="function")
def start_httpserver():
	create_certification()
	print("start server")
	PORT = 8080
	Handler = http.server.SimpleHTTPRequestHandler

	httpd = socketserver.TCPServer(("", PORT), Handler)
	httpd.socket = ssl.wrap_socket (httpd.socket, 
        keyfile="tests/testopsicommon/data/ssl/test-server.key", 
        certfile="tests/testopsicommon/data/ssl/test-server.crt", server_side=True)
	thread = threading.Thread(target = httpd.serve_forever)
	thread.daemon = True
	thread.start()
	yield None
	print("shutdown server")
	httpd.shutdown()


def remove_ca():
	print("remove ca")
	if isCentOS() or isRHEL():
		# /usr/share/pki/ca-trust-source/anchors/
		system_cert_path = "/etc/pki/ca-trust/source/anchors"
		cmd = "update-ca-trust"
	elif isDebian() or isUbuntu():
		system_cert_path = "/usr/local/share/ca-certificates"
		cmd = "update-ca-certificates"
	elif isOpenSUSE() or isSLES():
		system_cert_path = "/usr/share/pki/trust/anchors"
		cmd = "update-ca-certificates"
	else:
		print("Failed to set system cert path!")

	r = subprocess.call(["rm", system_cert_path], encoding="utf-8")
	print(r)
	r = subprocess.call([cmd], encoding="utf-8")
	print(r)

def test_curl(start_httpserver):

	time.sleep(5)

	remove_ca()

	r = subprocess.call(["curl", "https://localhost:8080"], encoding="utf-8")
	print(r)
	assert r == 60

	install_ca("tests/testopsicommon/data/ssl/ca.crt")

	r = subprocess.call(["curl", "https://localhost:8080"], encoding="utf-8")
	print(r)
	assert r == 0
