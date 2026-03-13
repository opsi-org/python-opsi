import os
import re
import tempfile
from contextlib import contextmanager
from typing import Generator

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

from opsi.logging import get_logger
from opsi.process import ProcessError, run_command

logger = get_logger("opsi")


@contextmanager
def security_authorization() -> Generator[None, None, None]:
	try:  # Allow to make changes to certificate settings
		run_command(["security", "authorizationdb", "write", "com.apple.trust-settings.admin", "allow"], timeout=10)
		yield
	finally:  # Disallow to make changes to certificate settings
		run_command(["security", "authorizationdb", "remove", "com.apple.trust-settings.admin"], timeout=10)


def install_ca(ca_cert: x509.Certificate) -> None:
	logger.info("Installing CA '%s' into system store", ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value)

	pem_file = tempfile.NamedTemporaryFile(mode="wb", delete=False)
	pem_file.write(ca_cert.public_bytes(encoding=serialization.Encoding.PEM))
	pem_file.close()
	try:
		with security_authorization():
			run_command(
				["security", "add-trusted-cert", "-d", "-r", "trustRoot", "-k", "/Library/Keychains/System.keychain", pem_file.name],
				timeout=10,
			)
	finally:
		os.remove(pem_file.name)


def load_cas(subject_name: str) -> Generator[x509.Certificate, None, None]:
	try:
		pem = run_command(
			["security", "find-certificate", "-a", "-p", "-c", subject_name, "/Library/Keychains/System.keychain"], timeout=10
		).output
	except ProcessError as err:
		if "could not be found" in err.output:
			return
		raise
	for cert_match in re.finditer(r"(-+BEGIN CERTIFICATE-+.*?-+END CERTIFICATE-+)", pem, re.DOTALL):
		try:
			yield x509.load_pem_x509_certificate(cert_match.group(1).encode("utf-8"))
		except Exception as err:
			logger.error("Failed to load certificate: %s", err)


def load_ca(subject_name: str) -> x509.Certificate | None:
	try:
		return next(load_cas(subject_name))
	except StopIteration:
		logger.notice("Did not find CA %r", subject_name)
		return None


def remove_ca(subject_name: str, sha1_fingerprint: str | None = None) -> bool:
	if sha1_fingerprint:
		sha1_fingerprint = sha1_fingerprint.upper()

	remove_cas = []
	for ca_cert in load_cas(subject_name):
		ca_fingerprint = ca_cert.fingerprint(hashes.SHA1()).hex().upper()
		if not sha1_fingerprint or ca_fingerprint == sha1_fingerprint:
			remove_cas.append(ca_fingerprint)

	if not remove_cas:
		logger.info("CA '%s' (%s) not found, nothing to remove", subject_name, sha1_fingerprint)
		return False

	with security_authorization():
		for ca_fingerprint in remove_cas:
			logger.info("Removing CA '%s' (%s)", subject_name, ca_fingerprint)
			run_command(["security", "delete-certificate", "-Z", ca_fingerprint, "/Library/Keychains/System.keychain", "-t"], timeout=10)

	return True
