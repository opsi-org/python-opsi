# opsi.system is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2021-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from opsi.opsi.service.client import ServiceClient
from opsi.opsi.service.model.object import serialize
from opsi.system.windows_driver import (
	Architecture,
	BinarySource,
	BinarySourceAccessType,
	BinarySourceBinaryType,
	BinarySourceOperationType,
	integrate_windows_drivers,
)
from opsi.testing.helper import http_test_server


@pytest.mark.posix
@pytest.mark.parametrize("http", (True, False))
def test_integrate_windows_drivers(tmp_path: Path, http: bool) -> None:
	product_id = "win11-x64"
	depot_path = tmp_path / "depot"
	dest_path = tmp_path / "driver_integration"
	windows_base_path = tmp_path / "windows"

	driver1_path = depot_path / product_id / "drivers" / "drivers" / "driver1"
	driver1_files: list[Path] = [
		driver1_path / "some_file.inf",
		driver1_path / "some_file.txt",
		driver1_path / "sub1" / "some_file1.txt",
		driver1_path / "sub2" / "some_file2.txt",
	]
	driver2_path = depot_path / product_id / "drivers" / "drivers" / "driver2"
	driver2_files: list[Path] = [
		driver2_path / "other_file.inf",
		driver2_path / "other_file.txt",
		driver2_path / "sub1" / "other file1.bin",
		driver2_path / "sub1" / "sub2" / "other_file2.txt",
	]

	for driver_file in driver1_files + driver2_files:
		driver_file.parent.mkdir(parents=True, exist_ok=True)
		driver_file.write_text(driver_file.name)

	shutil.copy("tests/data/inffile/netkvm.inf", driver1_files[0])
	shutil.copy("tests/data/inffile/vioscsi_amd64.inf", driver2_files[0])

	class MockService(ServiceClient):
		def driver_getSources(self, productId: str, clientId: str, architecture: str, osVersion: str) -> list[BinarySource]:
			sources = [
				BinarySource(
					binary_type=BinarySourceBinaryType.WINDOWS_DRIVER,
					access_type=BinarySourceAccessType.DEPOT,
					operation_type=BinarySourceOperationType.RECURSIVE_COPY,
					url=str(driver_path.relative_to(depot_path)),
					information={
						"inf_file": "some_file.inf" if driver_path == driver1_path else "other_file.inf",
					},
				)
				for driver_path in [driver1_path, driver2_path]
			]
			if http:
				return serialize(sources, deep=True)
			return sources

	mock_service = MockService()

	def mock_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
		assert len(args) == 6
		assert args[0] == "reged"
		assert args[1] == "-C"
		assert args[2] == "-I"
		assert args[3] == str(windows_base_path / "System32/config/SYSTEM")
		assert args[4] == r"HKEY_LOCAL_MACHINE\SYSTEM"
		assert args[5].endswith(".reg")
		reg = Path(args[5]).read_text(encoding="utf-16")
		assert "some_file.inf" not in reg
		assert "other_file.inf" in reg
		return subprocess.CompletedProcess(args=args, returncode=0, stdout="Mocked stdout", stderr="Mocked stderr")

	with patch("subprocess.run", mock_run), http_test_server(serve_directory=tmp_path, generate_cert=True) as server:
		depot = None
		if http:
			depot = ServiceClient(f"https://localhost:{server.port}", verify="accept_all")
			depot._jsonrpc_path = "/"
		integrate_windows_drivers(
			service=mock_service,
			product_id="test_product",
			client_id="test_client",
			architecture=Architecture.X64,
			os_version="10",
			source=Path("/depot") if depot else depot_path,
			destination=dest_path,
			depot=depot,
			add_driver_classes_to_driver_store=["SCSIAdapter"],
			windows_base_path=windows_base_path,
		)

	assert "VirtIO Ethernet Adapter" in (dest_path / "1" / "some_file.inf").read_text()
	assert (dest_path / "1" / "some_file.txt").read_text() == "some_file.txt"
	assert (dest_path / "1" / "sub1" / "some_file1.txt").read_text() == "some_file1.txt"
	assert (dest_path / "1" / "sub2" / "some_file2.txt").read_text() == "some_file2.txt"
	assert "VirtIO SCSI pass-through" in (dest_path / "2" / "other_file.inf").read_text()
	assert (dest_path / "2" / "other_file.txt").read_text() == "other_file.txt"
	assert (dest_path / "2" / "sub1" / "other file1.bin").read_text() == "other file1.bin"
	assert (dest_path / "2" / "sub1" / "sub2" / "other_file2.txt").read_text() == "other_file2.txt"
