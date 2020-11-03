# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import win32crypt as wcrypt
from OpenSSL import crypto
from opsicommon.logging import logger

__all__ = ["install_ca"]

# lpszStoreProvider
CERT_STORE_PROV_SYSTEM = 0x0000000A

# dwFlags
CERT_SYSTEM_STORE_LOCAL_MACHINE = 0x00020000

# cert encoding flags.
CRYPT_ASN_ENCODING= 0x00000001
CRYPT_NDR_ENCODING= 0x00000002
X509_ASN_ENCODING= 0x00000001
X509_NDR_ENCODING= 0x00000002
PKCS_7_ASN_ENCODING= 0x00010000
PKCS_7_NDR_ENCODING= 0x00020000
PKCS_7_OR_X509_ASN_ENCODING= (PKCS_7_ASN_ENCODING | X509_ASN_ENCODING)

# Add certificate/CRL, encoded, context or element disposition values.
CERT_STORE_ADD_NEW= 1
CERT_STORE_ADD_USE_EXISTING= 2
CERT_STORE_ADD_REPLACE_EXISTING= 3
CERT_STORE_ADD_ALWAYS= 4
CERT_STORE_ADD_REPLACE_EXISTING_INHERIT_PROPERTIES = 5
CERT_STORE_ADD_NEWER= 6
CERT_STORE_ADD_NEWER_INHERIT_PROPERTIES= 7


# Specifies the name of the X.509 certificate store to open. Valid values include the following:

# - AddressBook: Certificate store for other users.
# - AuthRoot: Certificate store for third-party certification authorities (CAs).
# - CertificationAuthority: Certificate store for intermediate certification authorities (CAs).
# - Disallowed: Certificate store for revoked certificates.
# - My: Certificate store for personal certificates.
# - Root: Certificate store for trusted root certification authorities (CAs).
# - TrustedPeople: Certificate store for directly trusted people and resources.
# - TrustedPublisher: Certificate store for directly trusted publishers.

# The default is My.

def _open_win_cert_store(store_name):
	store = wcrypt.CertOpenStore(CERT_STORE_PROV_SYSTEM, 0, None, CERT_SYSTEM_STORE_LOCAL_MACHINE, store_name)
	return store

def install_ca(ca_file):
	try:
		store_name = "Root"
		with open(ca_file, "r") as file:
			ca_file_content = file.read()
		ca = crypto.load_certificate(crypto.FILETYPE_PEM, ca_file_content)

		store = _open_win_cert_store(store_name)
		store.CertAddEncodedCertificateToStore(CERT_STORE_ADD_NEW, crypto.dump_certificate(crypto.FILETYPE_ASN1, ca), X509_ASN_ENCODING)
	except Exception as e:
		logger.error("ERROR: %s", e)