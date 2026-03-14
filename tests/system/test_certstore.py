# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from opsi.crypt.ssl import as_pem, create_ca, create_server_cert
from opsi.process import ProcessError, run_command, run_script
from opsi.system.certstore import install_ca, load_ca, load_cas, remove_ca
from opsi.system.info import is_windows
from opsi.testing.helper import http_test_server
from opsi.logging import use_logging_config

@pytest.mark.admin_permissions
def test_install_load_remove_ca() -> None:
	subject_name = "python-opsi test ca"
	remove_ca(subject_name)
	all_cas = list(load_cas(subject_name))
	assert len(list(all_cas)) == 0

	ca_cert1, _ca_key = create_ca(subject={"CN": subject_name}, valid_days=3)
	install_ca(ca_cert1)
	try:
		loaded_ca_cert = load_ca(subject_name)
		assert loaded_ca_cert
		assert loaded_ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == subject_name

		all_cas = list(load_cas(subject_name))
		assert len(list(all_cas)) == 1

		remove_ca(subject_name, ca_cert1.fingerprint(hashes.SHA1()).hex().upper())

		assert not load_ca(subject_name)

		all_cas = list(load_cas(subject_name))
		assert len(list(all_cas)) == 0

		# Install again and remove without supplying fingerprint
		install_ca(ca_cert1)

		loaded_ca_cert = load_ca(subject_name)
		assert loaded_ca_cert
		assert loaded_ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == subject_name

		all_cas = list(load_cas(subject_name))
		assert len(list(all_cas)) == 1

		remove_ca(subject_name)

		assert not load_ca(subject_name)

		all_cas = list(load_cas(subject_name))
		assert len(list(all_cas)) == 0

		# CA with same subject but other fingerprint
		ca_cert2, _ca_key = create_ca(subject={"CN": subject_name}, valid_days=3)
		install_ca(ca_cert1)
		install_ca(ca_cert2)

		if is_windows():
			# On Windows multiple CAs with the same subject can be installed
			all_cas = list(load_cas(subject_name))
			assert len(list(all_cas)) == 2

			loaded_ca_cert = load_ca(subject_name)
			assert loaded_ca_cert
			assert loaded_ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == subject_name

			remove_ca(subject_name, ca_cert1.fingerprint(hashes.SHA1()).hex().upper())

			all_cas = list(load_cas(subject_name))
			assert len(list(all_cas)) == 1
			assert all_cas[0].fingerprint(hashes.SHA1()).hex().upper() == ca_cert2.fingerprint(hashes.SHA1()).hex().upper()

			install_ca(ca_cert1)
			all_cas = list(load_cas(subject_name))
			assert len(list(all_cas)) == 2

			remove_ca(subject_name)
			all_cas = list(load_cas(subject_name))
			assert len(list(all_cas)) == 0

	finally:
		remove_ca(subject_name)


@pytest.mark.admin_permissions
def test_curl(tmp_path: Path) -> None:
	ca_cert, ca_key = create_ca(subject={"CN": "python-opsi test ca"}, valid_days=3)
	cert, key = create_server_cert(
		subject={"CN": "python-opsi test server cert"},
		valid_days=3,
		ip_addresses={"172.0.0.1", "::1"},
		hostnames={"localhost", "ip6-localhost"},
		ca_key=ca_key,
		ca_cert=ca_cert,
	)

	server_cert = tmp_path / "server_cert.pem"
	server_key = tmp_path / "server_key.pem"
	server_cert.write_text(as_pem(cert), encoding="utf-8", newline="")
	server_key.write_text(as_pem(key), encoding="utf-8", newline="")

	with http_test_server(server_key=server_key, server_cert=server_cert) as server:
		with use_logging_config(stderr_level=7):
			install_ca(ca_cert)
			try:
				if is_windows():
					assert (
						run_script(
							[f"Invoke-WebRequest -UseBasicParsing https://localhost:{server.port}"],
							interpreter="powershell",
							exit_on_error=True,
						).exit_code
						== 0
					)
				else:
					assert run_command(["curl", f"https://localhost:{server.port}"]).exit_code == 0
			finally:
				common_name = ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
				if not isinstance(common_name, str):
					common_name = common_name.decode("utf-8")
				remove_ca(common_name)
				if is_windows():
					with pytest.raises(ProcessError) as exc_info:
						run_script(
							[f"Invoke-WebRequest -UseBasicParsing https://localhost:{server.port}"],
							interpreter="powershell",
							exit_on_error=True,
						)
					assert exc_info.value.exit_code == 1
				else:
					with pytest.raises(ProcessError) as exc_info:
						proc = run_command(["curl", f"https://localhost:{server.port}"])
						print(proc.exit_code)
						print(proc.output)
					assert exc_info.value.exit_code == 60
