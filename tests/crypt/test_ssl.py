# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
This file is part of opsi - https://www.opsi.org
"""

import ipaddress
from pathlib import Path
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import verification

from opsi.crypt.ssl import (
	as_pem,
	create_ca,
	create_server_cert,
	create_server_cert_signing_request,
	create_x509_name,
	is_self_signed,
	read_certs_from_file,
	read_key_from_file,
	write_certs_to_file,
	x509_name_from_dict,
	x509_name_to_dict,
)
from opsi.crypt.ssl._ssl import subject_to_dict  # type: ignore[deprecated]


def test_x509_name_to_dict() -> None:
	x509_name = x509.Name(
		[
			x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "DE"),
			x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "RLP"),
			x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "Mainz"),
			x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "uib GmbH"),
			x509.NameAttribute(x509.NameOID.ORGANIZATIONAL_UNIT_NAME, "opsi"),
			x509.NameAttribute(x509.NameOID.COMMON_NAME, "opsicn"),
			x509.NameAttribute(x509.NameOID.EMAIL_ADDRESS, "info@opsi.org"),
		]
	)
	subject: dict[str, str | None] = {
		"C": "DE",
		"ST": "RLP",
		"L": "Mainz",
		"O": "uib GmbH",
		"OU": "opsi",
		"CN": "opsicn",
		"emailAddress": "info@opsi.org",
	}
	assert x509_name_to_dict(x509_name) == subject
	with pytest.deprecated_call():
		assert subject_to_dict(x509_name) == subject  # type: ignore[deprecated]
	assert create_x509_name(subject) == x509_name


def test_create_x509_name() -> None:
	subject: dict[str, str | None] = {"emailAddress": "test@test.de"}
	x509_name = create_x509_name(subject)
	assert x509_name.get_attributes_for_oid(x509.NameOID.EMAIL_ADDRESS)[0].value == subject["emailAddress"]
	assert x509_name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "opsi"

	subject = {"emailAddress": None, "CN": "opsi"}
	x509_name = create_x509_name(subject)
	assert not x509_name.get_attributes_for_oid(x509.NameOID.EMAIL_ADDRESS)
	assert x509_name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "opsi"


def test_create_ca() -> None:
	subject_dict: dict[str, str | None] = {"commonName": "opsi CA", "OU": "opsi", "emailAddress": "opsi@opsi.org"}
	subject = x509_name_from_dict(subject_dict)
	ca_cert, ca_key = create_ca(subject=subject, valid_days=100)
	assert isinstance(ca_cert, x509.Certificate)
	assert isinstance(ca_key, rsa.RSAPrivateKey)
	assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == subject_dict["commonName"]
	assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value == subject_dict["OU"]
	assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.EMAIL_ADDRESS)[0].value == subject_dict["emailAddress"]

	permitted_domains = [".mycompany.com", "mycompany.org", "localhost"]
	ca_cert, ca_key = create_ca(subject=subject, valid_days=100, permitted_domains=permitted_domains)

	name_constraints = [extension for extension in ca_cert.extensions if extension.oid == x509.OID_NAME_CONSTRAINTS][0]
	assert name_constraints.critical
	assert name_constraints.value.permitted_subtrees[0].value == "mycompany.com"
	assert name_constraints.value.permitted_subtrees[1].value == "mycompany.org"
	assert name_constraints.value.permitted_subtrees[2].value == "localhost"
	for domain in ["mycompany.com", "sub.mycompany.com", "mycompany.org", "localhost", "other.tld"]:
		srv_cert, _srv_key = create_server_cert(
			subject={"emailAddress": f"opsi@{domain}", "CN": f"server.{domain}"},
			valid_days=100,
			ip_addresses={"172.0.0.1", "::1", "192.168.1.1"},
			hostnames={f"server.{domain}", "localhost"},
			ca_key=ca_key,
			ca_cert=ca_cert,
		)
		store = verification.Store([ca_cert])
		builder = verification.PolicyBuilder().store(store)

		verifier = builder.build_server_verifier(x509.DNSName(f"server.{domain}"))
		if domain in "other.tld":
			with pytest.raises(Exception, match="no permitted name constraints matched SAN"):
				verifier.verify(srv_cert, [])
		else:
			verifier.verify(srv_cert, [])

	subject_dict["commonName"] = None
	subject = x509_name_from_dict(subject_dict)
	with pytest.raises(ValueError):
		create_ca(subject=subject, valid_days=100)


def test_create_intermediate_ca() -> None:
	ca_subject = {"CN": "ACME Root CA", "emailAddress": "ca@acme.org"}
	(ca_crt, ca_key) = create_ca(subject=ca_subject, valid_days=1000)

	intermediate_ca_subject = {"CN": "ACME Intermediate CA", "emailAddress": "ca@opsi.org"}
	(intermediate_ca_crt, _intermediate_ca_key) = create_ca(subject=intermediate_ca_subject, valid_days=500, ca_key=ca_key, ca_cert=ca_crt)

	assert is_self_signed(ca_crt)
	assert not is_self_signed(intermediate_ca_crt)

	assert ca_crt.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == ca_subject["CN"]
	assert intermediate_ca_crt.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == ca_subject["CN"]
	assert intermediate_ca_crt.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == intermediate_ca_subject["CN"]


def test_create_server_cert() -> None:
	subject = {"CN": "opsi CA", "OU": "opsi", "emailAddress": "opsi@opsi.org"}
	ca_cert, ca_key = create_ca(subject=subject, valid_days=1000)
	kwargs: dict[str, Any] = {
		"subject": {"emailAddress": "opsi@opsi.org"},
		"valid_days": 100,
		"ip_addresses": {"172.0.0.1", "::1", ipaddress.ip_address("192.168.1.1")},
		"hostnames": {"localhost", "opsi", "opsi.dom.tld"},
		"ca_key": ca_key,
		"ca_cert": ca_cert,
	}
	with pytest.raises(ValueError) as err:
		cert, key = create_server_cert(**kwargs)
	assert "commonName missing in subject" in str(err)

	kwargs["subject"]["CN"] = "server.dom.tld"
	cert, key = create_server_cert(**kwargs)
	assert isinstance(cert, x509.Certificate)
	assert isinstance(key, rsa.RSAPrivateKey)
	assert cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == kwargs["subject"]["CN"]

	alt_names = [extension for extension in cert.extensions if extension.oid == x509.OID_SUBJECT_ALTERNATIVE_NAME][0]
	assert not alt_names.critical
	assert alt_names.value.get_values_for_type(x509.DNSName) == list(kwargs["hostnames"])
	assert alt_names.value.get_values_for_type(x509.IPAddress) == list(ipaddress.ip_address(ip) for ip in kwargs["ip_addresses"])


def test_create_server_cert_signing_request() -> None:
	kwargs: dict[str, Any] = {
		"subject": {"emailAddress": "opsi@opsi.org"},
		"ip_addresses": {"172.0.0.1", "::1", ipaddress.ip_address("192.168.1.1")},
		"hostnames": {"localhost", "opsi", "opsi.dom.tld"},
	}
	with pytest.raises(ValueError) as err:
		cert, key = create_server_cert_signing_request(**kwargs)
	assert "commonName missing in subject" in str(err)

	kwargs["subject"]["CN"] = "server.dom.tld"
	cert, key = create_server_cert_signing_request(**kwargs)
	assert isinstance(cert, x509.CertificateSigningRequest)
	assert isinstance(key, rsa.RSAPrivateKey)
	assert cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == kwargs["subject"]["CN"]

	alt_names = [extension for extension in cert.extensions if extension.oid == x509.OID_SUBJECT_ALTERNATIVE_NAME][0]
	assert not alt_names.critical
	assert alt_names.value.get_values_for_type(x509.DNSName) == list(kwargs["hostnames"])
	assert alt_names.value.get_values_for_type(x509.IPAddress) == list(ipaddress.ip_address(ip) for ip in kwargs["ip_addresses"])


def test_as_pem() -> None:
	subject = {"CN": "opsi CA", "OU": "opsi", "emailAddress": "opsi@opsi.org"}
	cert, key = create_ca(subject=subject, valid_days=100)

	pem = as_pem(cert, "")
	assert pem.startswith("-----BEGIN CERTIFICATE-----")

	pem = as_pem(cert, None)
	assert pem.startswith("-----BEGIN CERTIFICATE-----")

	with pytest.raises(ValueError):
		pem = as_pem(cert, "password")

	pem = as_pem(key)
	assert pem.startswith("-----BEGIN PRIVATE KEY-----")

	pem = as_pem(key, "password")
	assert pem.startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----")

	with pytest.raises(TypeError):
		as_pem(create_x509_name({}))  # type: ignore[arg-type]


def test_load_key_from_file(tmp_path: Path) -> None:
	key_file = tmp_path / "key.pem"
	key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	key_file.write_text(as_pem(key, passphrase="password"), encoding="utf-8", newline="")
	with pytest.raises(RuntimeError, match=r".*Incorrect password, could not decrypt key.*"):
		read_key_from_file(key_file, "wrongpassword")
	with pytest.raises(TypeError, match=r".*Password was not given but private key is encrypted.*"):
		read_key_from_file(key_file)
	l_key = read_key_from_file(key_file, "password")
	assert l_key.private_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PrivateFormat.TraditionalOpenSSL,
		encryption_algorithm=serialization.NoEncryption(),
	) == key.private_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PrivateFormat.TraditionalOpenSSL,
		encryption_algorithm=serialization.NoEncryption(),
	)


def test_write_certs_to_file_writes_multiple_pem_certificates(tmp_path: Path) -> None:
	cert_file = tmp_path / "certs.pem"
	ca_cert, ca_key = create_ca(subject={"CN": "opsi CA"}, valid_days=100)
	server_cert, _server_key = create_server_cert(
		subject={"CN": "server.opsi.test"},
		valid_days=100,
		ip_addresses=set(),
		hostnames={"server.opsi.test"},
		ca_key=ca_key,
		ca_cert=ca_cert,
	)

	write_certs_to_file([ca_cert, server_cert], cert_file)

	assert cert_file.read_text(encoding="utf-8") == f"{as_pem(ca_cert)}{as_pem(server_cert)}"
	assert [as_pem(cert) for cert in read_certs_from_file(cert_file)] == [as_pem(ca_cert), as_pem(server_cert)]


def test_read_certs_from_file_skips_invalid_pem_blocks(tmp_path: Path) -> None:
	cert_file = tmp_path / "certs.pem"
	ca_cert, _ca_key = create_ca(subject={"CN": "opsi CA"}, valid_days=100)
	cert_file.write_text(
		f"not a certificate\n-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----\n{as_pem(ca_cert)}",
		encoding="utf-8",
	)

	assert [as_pem(cert) for cert in read_certs_from_file(cert_file)] == [as_pem(ca_cert)]
