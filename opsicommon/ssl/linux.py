# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import os
from shutil import copyfile
from OpenSSL import crypto

from OPSI.System import execute, isCentOS, isDebian, isOpenSUSE, isRHEL, isSLES, isUbuntu

from opsicommon.logging import logger

__all__ = ["install_ca"]

def install_ca(ca_file):

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
		logger.error("Failed to set system cert path")
		raise RuntimeError("Failed to set system cert path")

	with open(ca_file, "r") as file:
		ca = crypto.load_certificate(crypto.FILETYPE_PEM,  file.read())

	logger.info(
		"Installing CA '%s' from '%s' into system store",
		ca.get_subject().commonName, ca_file
	)

	cert_file = f"{ca.get_subject().commonName.replace(' ', '_')}.crt"
	copyfile(ca_file, os.path.join(system_cert_path, cert_file))
	output = execute(cmd)
	logger.debug("Output of '%s': %s", cmd, output)
