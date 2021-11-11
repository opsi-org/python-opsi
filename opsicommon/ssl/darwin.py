# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
This file is part of opsi - https://www.opsi.org
"""

import os
import tempfile

from OpenSSL import crypto
from OPSI.System import execute

from opsicommon.logging import logger

__all__ = ["install_ca", "remove_ca", "is_in_os_store"]


def install_ca(ca_cert: crypto.X509):
	logger.info("Installing CA '%s' into system store", ca_cert.get_subject().CN)

	pem_file = tempfile.NamedTemporaryFile(mode="wb", delete=False)  # pylint: disable=consider-using-with
	pem_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, ca_cert))
	pem_file.close()
	try:
		execute(f'security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "{pem_file.name}"')
	finally:
		os.remove(pem_file.name)


def load_ca(subject_name: str) -> crypto.X509:
	pem = execute(f'security find-certificate -p -c "{subject_name}" /Library/Keychains/System.keychain').strip()
	if not pem or not pem.strip():
		return None
	return crypto.load_certificate(crypto.FILETYPE_PEM, pem)


def remove_ca(subject_name: str) -> bool:
	ca = load_ca(subject_name)
	if not ca:
		logger.info("CA '%s' not found, nothing to remove", subject_name)
		return

	logger.info("Removing CA '%s'", subject_name)
	pem_file = tempfile.NamedTemporaryFile(mode="wb", delete=False)  # pylint: disable=consider-using-with
	pem_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, ca))
	pem_file.close()
	try:
		execute(f'security remove-trusted-cert -d "{pem_file.name}"')
	finally:
		os.remove(pem_file.name)


def is_in_os_store(ca_cert: crypto.X509) -> bool:
	subject_name = ca_cert.get_subject().CN
	logger.devel("checking signature of %s against entries in system certificate store", subject_name)

	pem = execute(f'security find-certificate -p -c "{subject_name}" /Library/Keychains/System.keychain').strip()
	if pem:
		ca = crypto.load_certificate(crypto.FILETYPE_PEM, pem.encode("utf-8"))
		if ca.digest("sha1") == ca_cert.digest("sha1"):
			logger.devel("Found certificate with matching digest")
			return True

	logger.devel("Did not find certificate with matching digest")
	return False
