# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2018 uib GmbH <info@uib.de>

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
opsi python library - Util - Task - Certificate

Functionality to work with certificates.
Certificates play an important role in the encrypted communication
between servers and clients.

.. versionadded:: 4.0.4



:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import random
import shutil
from tempfile import NamedTemporaryFile

from OpenSSL import crypto

from OPSI.Logger import Logger
from OPSI.System import which, execute
from OPSI.Types import forceHostId, forceInt
from OPSI.Util import getfqdn

OPSICONFD_CERTFILE = u'/etc/opsi/opsiconfd.pem'
DEFAULT_CERTIFICATE_PARAMETERS = {
	"country": "DE",
	"state": "RP",
	"locality": "Mainz",
	"organization": "uib gmbh",
	"organizationalUnit": "",
	"commonName": forceHostId(getfqdn()),
	"emailAddress": "",
	"expires": 2,
}
LOGGER = Logger()


class NoCertificateError(Exception):
	pass


class CertificateCreationError(Exception):
	pass


class UnreadableCertificateError(Exception):
	pass


def renewCertificate(path=None, yearsUntilExpiration=2, config=None):
	"""
	Renews an existing certificate and creates a backup of the old file

	If an error occurs during the creation of the new certificate the backup
	will be restored.

	:param path: The path of the certificate.
	:type path: str
	:param yearsUntilExpiration: How many years will the certificate be valid? \
Will always overwrite an existing value in ``config``.
	:type yearsUntilExpiration: int
	:param config: Settings for the new certificate. If this is \
`None` the values for the configuration will be read from the \
existing certificate.
	:type config: dict
	:raises NoCertificateError: If no certificate found.
	"""
	if path is None:
		path = OPSICONFD_CERTFILE

	if not os.path.exists(path):
		raise NoCertificateError(u'No certificate found at {0}'.format(path))

	if config is None:
		config = loadConfigurationFromCertificate(path)
	config["expires"] = yearsUntilExpiration

	backupfile = u'{0}.bak'.format(path)
	LOGGER.notice(u"Creating backup of existing certifcate to {0}".format(backupfile))
	shutil.copy(path, backupfile)

	try:
		createCertificate(path, config)
	except CertificateCreationError as error:
		LOGGER.warning(u'Problem during the creation of the certificate: {0}'.format(error))
		LOGGER.notice(u'Restoring backup.')
		shutil.move(backupfile, path)
		raise error


def createCertificate(path=None, config=None):
	"""
	Creates a certificate.

	Will overwrite any certificate that may exists in ``path``.

	.. versionchanged:: 4.0.6.2

		Incrementing previously set serial number on re-creation.
		For new certificates a random number will be generated.


	:param path: The path of the certificate. \
If this is `None` the default will be used.
	:type path: str
	:param config: The configuration of the certificate. \
If not given will use a default.
	:type config: dict
	:raises CertificateCreationError: If errors exist in configuration.
	"""
	try:
		which("ucr")
		LOGGER.notice(u"Don't use certificate creation method on UCS-Systems")
		return
	except Exception:
		pass

	if path is None:
		path = OPSICONFD_CERTFILE

	if config is None:
		certparams = DEFAULT_CERTIFICATE_PARAMETERS
	else:
		certparams = config

	try:
		certparams["expires"] = forceInt(certparams["expires"])
	except Exception:
		raise CertificateCreationError(
			u"No valid expiration date given. Must be an integer."
		)

	if certparams["commonName"] != forceHostId(getfqdn()):
		raise CertificateCreationError(
			u"commonName must be the FQDN of the local server"
		)

	LOGGER.notice(u"Creating new opsiconfd cert")
	LOGGER.notice(u"Generating new key pair")
	k = crypto.PKey()
	k.generate_key(crypto.TYPE_RSA, 2048)

	LOGGER.notice(u"Generating new self-signed cert")
	cert = crypto.X509()
	cert.get_subject().C = certparams['country']
	cert.get_subject().ST = certparams['state']
	cert.get_subject().L = certparams['locality']
	cert.get_subject().O = certparams['organization']
	cert.get_subject().CN = certparams['commonName']

	try:
		if certparams['organizationalUnit']:
			cert.get_subject().OU = certparams['organizationalUnit']
		else:
			del certparams['organizationalUnit']
	except KeyError:
		pass

	try:
		if certparams['emailAddress']:
			cert.get_subject().emailAddress = certparams['emailAddress']
		else:
			del certparams['emailAddress']
	except KeyError:
		pass

	LOGGER.notice("Generating new Serialnumber")
	# As described in RFC5280 this value is required and must be a
	# positive and unique integer.
	# Source: http://tools.ietf.org/html/rfc5280#page-19
	#
	# We currently do not have the ability to make the serial unique
	# but we assume that this is called only once in 2-3 years.
	# If we have an old serial number present we increment it by 1.
	# If we do not have an old serial number we create a random one.
	try:
		serialNumber = int(certparams['serialNumber']) + 1
	except (KeyError, ValueError):
		LOGGER.debug(u"Reading in the existing serial number failed.")
		LOGGER.info(u"Creating new random serial number.")
		serialNumber = random.randint(0, pow(2, 16))
	cert.set_serial_number(serialNumber)

	LOGGER.notice(
		u"Setting new expiration date (%d years)" % certparams["expires"]
	)
	cert.gmtime_adj_notBefore(0)
	cert.gmtime_adj_notAfter(certparams["expires"] * 365 * 24 * 60 * 60)

	LOGGER.notice(u"Filling certificate with new data")
	cert.set_issuer(cert.get_subject())
	cert.set_pubkey(k)
	cert.set_version(2)

	LOGGER.notice(u"Signing Certificate")
	cert.sign(k, str('sha512'))

	certcontext = "".join(
		(
			crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
			crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
		)
	)

	LOGGER.notice(u"Beginning to write certificate.")
	with open(path, "wt") as certfile:
		certfile.write(certcontext)

	with NamedTemporaryFile(mode="wt") as randfile:
		LOGGER.notice(u"Generating and filling new randomize string")
		randomBytes = os.urandom(512)
		randfile.write(randomBytes)

		execute(
			u"{command} dhparam -rand {tempfile} 512 >> {target}".format(
				command=which("openssl"), tempfile=randfile.name, target=path
			)
		)

	LOGGER.notice(u'Certificate creation done.')


def loadConfigurationFromCertificate(path=None):
	"""
	Loads certificate configuration from a file.

	:param path: The path to the certificate. \
Uses `OPSICONFD_CERTFILE` if no path is given.
	:type path: str
	:raises NoCertificateError: If no certificate found.
	:raises UnreadableCertificateError: If certificate can not be read.
	:return: The configuration as read from the certificate.
	:rtype: dict
	"""
	if path is None:
		path = OPSICONFD_CERTFILE

	if not os.path.exists(path):
		raise NoCertificateError(u'No certificate found at {path}.'.format(
				path=path
			)
		)

	certparams = {}
	with open(path) as data:
		try:
			cert = crypto.load_certificate(crypto.FILETYPE_PEM, data.read())
		except crypto.Error as error:
			raise UnreadableCertificateError(
				u'Could not read from {path}: {error}'.format(
					path=path,
					error=error
				)
			)

		certparams["country"] = cert.get_subject().C
		certparams["state"] = cert.get_subject().ST
		certparams["locality"] = cert.get_subject().L
		certparams["organization"] = cert.get_subject().O
		certparams["organizationalUnit"] = cert.get_subject().OU
		certparams["commonName"] = cert.get_subject().CN
		certparams["emailAddress"] = cert.get_subject().emailAddress
		certparams["serialNumber"] = cert.get_serial_number()

	return certparams
