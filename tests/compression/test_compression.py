# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import random
from typing import Literal

import pytest

from opsi.compression import compress, decompress


@pytest.mark.parametrize(
	"compression",
	("lz4", "deflate", "gz", "gzip", "zstd"),
)
@pytest.mark.parametrize(
	"compression_level",
	(1, 5, 9),
)
def test_compress_decompress(compression: Literal["lz4", "deflate", "gz", "gzip", "zstd"], compression_level: int) -> None:
	data = random.randbytes(50_000)
	comp_data = compress(data=data, compression=compression, compression_level=compression_level)
	assert decompress(data=comp_data, compression=compression) == data


def test_invalid_compression() -> None:
	with pytest.raises(ValueError, match="Invalid compression 'invalid'"):
		compress(data=b"data", compression="invalid")  # type: ignore

	with pytest.raises(ValueError, match="Invalid compression 'invalid'"):
		decompress(data=b"data", compression="invalid")  # type: ignore
