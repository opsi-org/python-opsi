# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import gzip
import time
import zlib
from typing import Literal

import lz4.frame
from zstandard import ZstdCompressor, ZstdDecompressor

from opsi.logging import get_logger

logger = get_logger("opsi")

ZSTD_DEFAULT_COMPRESS_LEVEL = 3
LZ4_DEFAULT_COMPRESS_LEVEL = 0
GZIP_DEFAULT_COMPRESS_LEVEL = 9
ZLIB_DEFAULT_COMPRESS_LEVEL = 6


def decompress(data: bytes, compression: Literal["lz4", "deflate", "gz", "gzip", "zstd"]) -> bytes:
	"""
	Decompress data using the specified compression method.

	Args:
		data (bytes): The compressed data.
		compression (Literal["lz4", "deflate", "gz", "gzip", "zstd"]): The compression method.
	Returns:
		bytes: The decompressed data.

	Raises:
		ValueError: If the compression method is unsupported.
	"""
	compressed_size = len(data)

	decompress_start = time.perf_counter()
	if compression == "lz4":
		data = lz4.frame.decompress(data)
	elif compression == "deflate":
		data = zlib.decompress(data)
	elif compression in ("gz", "gzip"):
		data = gzip.decompress(data)
	elif compression == "zstd":
		data = ZstdDecompressor().decompress(data)
	else:
		raise ValueError(f"Invalid compression {compression!r}")
	decompress_end = time.perf_counter()

	uncompressed_size = len(data)
	logger.debug(
		"%s decompression ratio: %d => %d = %0.2f%%, time: %0.2fms",
		compression,
		compressed_size,
		uncompressed_size,
		100 - 100 * (compressed_size / uncompressed_size),
		1000 * (decompress_end - decompress_start),
	)
	return data


def compress(
	data: bytes,
	compression: Literal["lz4", "deflate", "gz", "gzip", "zstd"],
	*,
	compression_level: int | None = None,
	block_linked: bool | None = None,
) -> bytes:
	"""
	Compress data using the specified compression method.

	Args:
		data (bytes): The data to compress.
		compression (Literal["lz4", "deflate", "gz", "gzip", "zstd"]): The compression method.
		compression_level (int): The compression level.
		block_linked (bool): Whether to use block linking.

	Returns:
		bytes: The compressed data.

	Raises:
		ValueError: If the compression method is unsupported.
	"""
	uncompressed_size = len(data)

	compress_start = time.perf_counter()
	if compression == "lz4":
		if block_linked is None:
			block_linked = True
		if compression_level is None:
			compression_level = LZ4_DEFAULT_COMPRESS_LEVEL
		if compression_level < 0 or compression_level > 16:
			raise ValueError(f"Invalid compression level {compression_level} for lz4, must be between 0 and 16")
		data = lz4.frame.compress(data, compression_level=compression_level, block_linked=block_linked)
	elif compression == "deflate":
		if compression_level is None:
			compression_level = ZLIB_DEFAULT_COMPRESS_LEVEL
		if compression_level < 0 or compression_level > 9:
			raise ValueError(f"Invalid compression level {compression_level} for deflate, must be between 0 and 9")
		data = zlib.compress(data, level=compression_level)
	elif compression in ("gz", "gzip"):
		if compression_level is None:
			compression_level = GZIP_DEFAULT_COMPRESS_LEVEL
		if compression_level < 0 or compression_level > 9:
			raise ValueError(f"Invalid compression level {compression_level} for gzip, must be between 0 and 9")
		data = gzip.compress(data, compresslevel=compression_level)
	elif compression == "zstd":
		if compression_level is None:
			compression_level = ZSTD_DEFAULT_COMPRESS_LEVEL
		if compression_level < -7 or compression_level > 22:
			raise ValueError(f"Invalid compression level {compression_level} for zstd, must be between -7 and 22")
		data = ZstdCompressor(level=compression_level).compress(data)
	else:
		raise ValueError(f"Invalid compression {compression!r}")
	compress_end = time.perf_counter()

	compressed_size = len(data)
	logger.debug(
		"%s compression ratio: %d => %d = %0.2f%%, time: %0.2fms",
		compression,
		uncompressed_size,
		compressed_size,
		100 - 100 * (compressed_size / uncompressed_size),
		1000 * (compress_end - compress_start),
	)
	return data
