# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path
from typing import Literal

import pytest

from opsi.crypt.hash import compute_file_hash, verify_file_hash


@pytest.mark.parametrize("algorithm", ("md5", "blake3"))
@pytest.mark.parametrize("progress", (True, False))
def test_file_hash(tmp_path: Path, algorithm: Literal["md5", "blake3"], progress: bool) -> None:
	progress_values = []

	def progress_callback(position: int, total: int) -> None:
		nonlocal progress_values
		progress_values.append((position, total))

	file_path = tmp_path / "testfile.bin"
	data = b"Test data for hashing.\n" * 1000
	data_size = len(data)
	file_path.write_bytes(data)

	assert compute_file_hash(file_path, algorithm, progress_callback=progress_callback if progress else None) == (
		"1ec7769251775e55268a584de164f320" if algorithm == "md5" else "20294ccbccc9eb04e6c8245213920d3be812de6ed1fb7e727526de4189acc5a9"
	)
	if progress:
		assert len(progress_values) > 1
		assert progress_values[0] == (0, data_size)
		assert progress_values[-1] == (data_size, data_size)
	else:
		assert len(progress_values) == 0

	assert verify_file_hash(
		"1ec7769251775e55268a584de164f320" if algorithm == "md5" else "20294ccbccc9eb04e6c8245213920d3be812de6ed1fb7e727526de4189acc5a9",
		file_path,
		algorithm,
		progress_callback=progress_callback if progress else None,
	)

	assert not verify_file_hash(
		"04e6c8245213920d3be812de6ed1fb7e", file_path, algorithm, progress_callback=progress_callback if progress else None
	)

	with pytest.raises(ValueError, match="Invalid value 'sha256' for hash algorithm, supported values are: 'blake3', 'md5'"):
		compute_file_hash(file_path, "sha256")
		verify_file_hash("somehash", file_path, "sha256")
