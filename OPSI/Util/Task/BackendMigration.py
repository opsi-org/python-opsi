# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Backend migration tasks
"""

from opsicommon.logging import logger

from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.Replicator import BackendReplicator
from OPSI.Exceptions import BackendConfigurationError
from OPSI.System import execute


def patch_dispatch_conf():
	logger.notice("Patch dispatch.conf to use MySQL backend")
	lines = []
	with open("/etc/opsi/backendManager/dispatch.conf", encoding="utf-8") as file:
		for line in file:
			if line.strip() and not line.strip().startswith("#"):
				match, backends = line.split(":", 1)
				match = match.strip()
				if match == ".*":
					lines.append(f"{match} : mysql\n")
					continue
				backends = list({"mysql" if b.strip() == "file" else b.strip() for b in backends.split(",")})
				if "mysql" in backends:
					if len(backends) == 1:
						continue
					backends.remove("mysql")
					backends.insert(0, "mysql")
				line = f"{match} : {', '.join(backends)}\n"
			lines.append(line)
	with open("/etc/opsi/backendManager/dispatch.conf", mode="w", encoding="utf-8") as file:
		file.writelines(lines)


def migrate_file_to_mysql(restart_services: bool = True):
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
			backends = backend._backends  # pylint: disable=protected-access

	if not backends:
		raise BackendConfigurationError("Failed to get backends from dispatcher")

	if "file" not in backends:
		logger.info("File backend not active, nothing to do")
		return

	service_running = {}
	if restart_services:
		for service in ("opsipxeconfd", "opsiconfd"):
			try:
				execute(["systemctl", "is-active", "--quiet", service])
				service_running[service] = True
			except RuntimeError:
				service_running[service] = False

			try:
				logger.notice("Stopping service %r", service)
				execute(["systemctl", "stop", service])
			except RuntimeError as err:
				logger.warning("Failed to stop service %r: %s", service, err)

	read_backend = backend_manager._loadBackend("file")  # pylint: disable=protected-access
	read_backend.backend_createBase()

	write_backend = backend_manager._loadBackend("mysql")  # pylint: disable=protected-access
	write_backend.unique_hardware_addresses = False
	write_backend.backend_createBase()

	backend_replicator = BackendReplicator(readBackend=read_backend, writeBackend=write_backend, cleanupFirst=True)
	backend_replicator.replicate(audit=False)

	patch_dispatch_conf()

	for service, state in service_running.items():
		if state:
			try:
				logger.notice("Starting service %r", service)
				execute(["systemctl", "start", service])
			except RuntimeError as err:
				logger.warning("Failed to start service %r: %s", service, err)
