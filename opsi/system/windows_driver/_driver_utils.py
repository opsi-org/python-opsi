# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from opsi.file.inf import INFFile, INFTargetOSVersion
from opsi.logging import get_logger
from opsi.opsi.service.client import ServiceClient
from opsi.opsi.service.model.type import Architecture

logger = get_logger(__name__)


class BinarySourceBinaryType(StrEnum):
	WINDOWS_DRIVER = "windows_driver"


class BinarySourceAccessType(StrEnum):
	DEPOT = "depot"


class BinarySourceOperationType(StrEnum):
	RECURSIVE_COPY = "recursive_copy"


@dataclass(kw_only=True, slots=True)
class BinarySource:
	binary_type: BinarySourceBinaryType
	access_type: BinarySourceAccessType
	operation_type: BinarySourceOperationType
	url: str
	information: dict[str, Any] = field(default_factory=dict)

	def as_dict(self) -> dict[str, Any]:
		"""
		Convert the BinarySource to a dictionary.
		"""
		return asdict(self)


def integrate_windows_drivers(
	*,
	service: ServiceClient,
	source: Path,
	destination: Path,
	product_id: str,
	client_id: str,
	architecture: Architecture,
	os_version: str | None = None,
	depot: ServiceClient | None = None,
	add_driver_classes_to_driver_store: list[str] | None = None,
	windows_base_path: Path | None = None,
) -> None:
	if add_driver_classes_to_driver_store and not windows_base_path:
		raise ValueError("windows_base_path must be provided if add_driver_classes_to_driver_store is specified")

	sources = service.driver_getSources(  # type: ignore[attr-defined]
		productId=product_id,
		clientId=client_id,
		architecture=architecture,
		osVersion=os_version,
	)
	for idx, src in enumerate(sources):
		if not isinstance(src, BinarySource):
			sources[idx] = BinarySource(**src)

	logger.debug("Integrating Windows drivers from sources: %r", sources)
	destination.mkdir(parents=True, exist_ok=True)
	driver_number = 0
	inf_files: list[Path] = []
	for src in sources:
		logger.debug("Processing source: %r", src)
		if src.binary_type != BinarySourceBinaryType.WINDOWS_DRIVER:
			logger.debug("Skipping non-Windows driver source: %r", src)
			continue
		if src.access_type != BinarySourceAccessType.DEPOT:
			logger.error("Binary access type %r is not supported", src.access_type)
			continue
		if src.operation_type != BinarySourceOperationType.RECURSIVE_COPY:
			logger.error("Binary operation type %r is not supported", src.operation_type)
			continue

		driver_number += 1
		driver_destination = destination / str(driver_number)
		inf_file = src.information.get("inf_file")
		if inf_file:
			inf_files.append(driver_destination / inf_file)
		else:
			logger.error("No INF file information found for driver source: %r", src)

		src_path = source / src.url.lstrip("/")
		if depot:
			driver_destination.mkdir()
			depot.download(str(src_path), driver_destination, preserve_source_dir=False)
		else:
			shutil.copytree(src_path, driver_destination)

	if add_driver_classes_to_driver_store and windows_base_path:
		add_drivers_to_driver_store(
			inf_files=inf_files,
			windows_base_path=windows_base_path,
			architecture=architecture,
			driver_classes=add_driver_classes_to_driver_store,
		)


def add_drivers_to_driver_store(
	inf_files: list[Path], windows_base_path: Path, architecture: Architecture, driver_classes: list[str] | None = None
) -> None:
	registry = ""
	for file_path in inf_files:
		logger.debug("Processing inf file: %s", file_path)
		driver_path = file_path.parent
		inf_file = INFFile(file_path)
		inf_file.parse()
		if driver_classes and inf_file.version and inf_file.version.Class not in driver_classes:
			continue

		logger.info("Adding driver to driver store: %s", inf_file.inf_name)

		driver_store_path = (
			windows_base_path / "System32/DriverStore/FileRepository" / inf_file.get_driver_database_dir_name(arch=architecture)
		)
		logger.info("Copy driver '%s' into driver store '%s'", driver_path, driver_store_path)
		shutil.copytree(driver_path, driver_store_path)

		win_drivers_path = windows_base_path / "System32/drivers"
		for sys_file in driver_path.glob("*.[sS][yY][sS]"):
			logger.info("Copy sys file '%s' into windows drivers '%s'", sys_file, win_drivers_path)
			shutil.copy(sys_file, win_drivers_path)
		try:
			target_os_version = INFTargetOSVersion(Architecture=architecture)
			registry += inf_file.get_driver_database_reg(target_os_version=target_os_version, oem_inf_name=inf_file.inf_name)
			registry += inf_file.get_services_reg(target_os_version=target_os_version)
		except Exception as err:
			logger.error(err, exc_info=True)

	if registry:
		logger.info("Adding to registry: %s", registry)
		temp_file = NamedTemporaryFile(mode="w", encoding="utf-16", suffix=".reg", delete=False)
		try:
			temp_file.write(rf"Windows Registry Editor Version 5.00\r\n\r\n{registry}")
			temp_file.close()
			reg_system = windows_base_path / "System32/config/SYSTEM"
			proc = subprocess.run(
				["reged", "-C", "-I", str(reg_system), r"HKEY_LOCAL_MACHINE\SYSTEM", temp_file.name],
				text=True,
				encoding="utf-8",
				errors="replace",
				capture_output=True,
				check=False,
			)
		finally:
			Path(temp_file.name).unlink(missing_ok=True)
		out = (proc.stdout or "") + (proc.stderr or "")
		logger.debug("Registry command exit code %d output: %s", proc.returncode, out)
		if proc.returncode not in (0, 2):
			raise RuntimeError(f"Failed to add registry entries: {out}")
