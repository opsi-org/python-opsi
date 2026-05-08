# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.util.pattern import Singleton, MappedStrEnum
import pytest
import enum


def test_singleton() -> None:
	class TestSingleton(metaclass=Singleton):
		pass

	assert id(TestSingleton()) == id(TestSingleton())


def test_mapped_str_enum() -> None:
	class Compression(MappedStrEnum):
		DEFLATE = "deflate"
		GZIP = "gzip"
		ZSTD = "ZSTD"

		_NAME = enum.nonmember("Compression Type")
		_ALIASES = enum.nonmember({"gz": "gzip", "zstandard": "zstd"})

	assert Compression("deflate") == Compression.DEFLATE
	assert Compression("Deflate") == Compression.DEFLATE
	assert Compression("gzip") == Compression.GZIP
	assert Compression("GZip") == Compression.GZIP
	assert Compression("gz") == Compression.GZIP
	assert Compression("zstandard") == Compression.ZSTD

	with pytest.raises(ValueError, match="Invalid value 'invalid' for Compression Type, supported values are: 'deflate', 'gzip', 'ZSTD'"):
		Compression("invalid")

	class Compression(MappedStrEnum):
		DEFLATE = "deflate"
		GZIP = "gzip"
		ZSTD = "zstd"

	assert Compression("deflate") == Compression.DEFLATE
	assert Compression("Deflate") == Compression.DEFLATE
	assert Compression("gzip") == Compression.GZIP
	assert Compression("GZip") == Compression.GZIP

	with pytest.raises(ValueError, match="Invalid value 'zstandard' for Compression, supported values are: 'deflate', 'gzip', 'zstd'"):
		Compression("zstandard")


def test_mapped_str_enum_invalid_aliases() -> None:
	with pytest.raises(ValueError, match="Invalid value 'wrong' for _ALIASES, must be a dict mapping alias to value"):

		class Compression(MappedStrEnum):
			DEFLATE = "deflate"

			_ALIASES = enum.nonmember("wrong")


def test_mapped_str_name() -> None:
	class Compression(MappedStrEnum):
		DEFLATE = "deflate"

		_NAME = enum.nonmember(100)

	assert Compression._NAME == "100"

	with pytest.raises(ValueError, match="Invalid value '100' for 100, supported values are: 'deflate'"):
		Compression(Compression._NAME)
