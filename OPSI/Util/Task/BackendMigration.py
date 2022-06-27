# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Backend migration tasks
"""

from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.Replicator import BackendReplicator
from OPSI.Exceptions import BackendConfigurationError
from opsicommon.logging import logger


def patch_dispatch_conf():
	lines = []
	with open("/etc/opsi/backendManager/dispatch.conf", encoding="utf-8") as file:
		for line in file:
			if line.strip() and not line.strip().startswith("#"):
				match, backends = line.split(":", 1)
				match = match.strip()
				if match == ".*":
					lines.append(f"{match} : mysql\n")
					continue
				backends = list(set(["mysql" if b.strip() == "file" else b.strip() for b in backends.split(",")]))
				if "mysql" in backends:
					if len(backends) == 1:
						continue
					backends.remove("mysql")
					backends.insert(0, "mysql")
				line = f"{match} : {', '.join(backends)}\n"
			lines.append(line)
	with open("/etc/opsi/backendManager/dispatch.conf", mode="w", encoding="utf-8") as file:
		file.writelines(lines)


def migrate_file_to_mysql():
	bm_config = {
		"dispatchConfigFile": "/etc/opsi/backendManager/dispatch.conf",
		"backendConfigDir": "/etc/opsi/backends",
		"extensionConfigDir": "/etc/opsi/backendManager/extend.d",
		"depotBackend": False,
		"dispatchIgnoreModules": ["OpsiPXEConfd", "DHCPD", "HostControl"],
		"unique_hardware_addresses": False
	}
	backend_manager = backend = BackendManager(**bm_config)
	backends = None
	while getattr(backend, "_backend", None):
		backend = backend._backend  # pylint: disable=protected-access
		if backend.__class__.__name__ == "BackendDispatcher":
			backends = backend._backends

	if not backends:
		raise BackendConfigurationError(f"Failed to get backends from dispatcher")

	if not "file" in backends:
		# Nothing to do
		return

	read_backend = backend_manager._loadBackend("file")
	read_backend.backend_createBase()

	write_backend = backend_manager._loadBackend("mysql")
	write_backend.unique_hardware_addresses = False
	write_backend.backend_createBase()

	backend_replicator = BackendReplicator(readBackend=read_backend, writeBackend=write_backend, cleanupFirst=True)
	backend_replicator.replicate(audit=False)

	patch_dispatch_conf()

