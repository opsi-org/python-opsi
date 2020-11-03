# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""


from OPSI.System import execute, isCentOS, isDebian, isOpenSUSE, isRHEL, isSLES, isUbuntu
from opsicommon.logging import logger

from OpenSSL import crypto

from shutil import copyfile
import os

__all__ = ["install_ca"]

def install_ca(ca_file):
	
	try:
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
			logger.error("Failed to set system cert path!")
			raise 

		with open(ca_file, "r") as file:
			ca_file_content = file.read()
		ca = crypto.load_certificate(crypto.FILETYPE_PEM, ca_file_content)
		
		cert_file = f"{ca.get_subject().commonName.replace(' ', '_')}.crt"
		copyfile(ca_file, os.path.join(system_cert_path, cert_file))
		output = execute(cmd)

	except Exception as e:
		logger.error("ERROR: %s", e)
	