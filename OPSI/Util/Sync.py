# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2019 uib GmbH <info@uib.de>
# http://www.uib.de/

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""

# forked from: https://github.com/dvas0004/py_rdiff
# inspiration: https://pypi.python.org/pypi/python-librsync/0.1-5
# librsync in c: http://rproxy.samba.org/doxygen/librsync/refman.pdf
# notes: https://docs.python.org/2/library/ctypes.html

import io
import os
import sys
import base64
import ctypes
import ctypes.util
import hashlib
import tempfile
import traceback

from OPSI.Logger import Logger
from OPSI.Types import forceFilename, forceUnicode

RSYNC_STRONG_LENGTH = 8
RSYNC_BLOCK_LENGTH = 2048

_librsync = None
logger = Logger()

if os.name == "posix":
	path = ctypes.util.find_library("rsync")
	if path is None:
		raise ImportError("Could not find librsync, make sure it is installed")
	try:
		_librsync = ctypes.cdll.LoadLibrary(path)
	except OSError:
		raise ImportError(f"Could not load librsync at '{path}'")
elif os.name == "nt":
	try:
		_librsync = ctypes.cdll.librsync
	except:
		raise ImportError("Could not load librsync, make sure it is installed")
else:
	raise NotImplementedError("Librsync is not supported on your platform")

# rs_result rs_sig_file (FILE *old_file, FILE *sig_file, size_t block_len, size_t strong_len, rs_magic_number sig_magic, rs_stats_t *stats)
_librsync.rs_sig_file.restype = ctypes.c_long
_librsync.rs_sig_file.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p]

# rs_result rs_loadsig_file (FILE *sig_file, rs_signature_t **sumset, rs_stats_t *stats)
_librsync.rs_loadsig_file.restype = ctypes.c_long
_librsync.rs_loadsig_file.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

# rs_result rs_build_hash_table(rs_signature_t* sums);
_librsync.rs_build_hash_table.restype = ctypes.c_size_t
_librsync.rs_build_hash_table.argtypes = [ctypes.c_void_p]

# rs_result rs_delta_file (rs_signature_t *, FILE *new_file, FILE *delta_file, rs_stats_t *)
_librsync.rs_delta_file.restype = ctypes.c_long
_librsync.rs_delta_file.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

# rs_result rs_patch_file (FILE *basis_file, FILE *delta_file, FILE *new_file, rs_stats_t *)
_librsync.rs_patch_file.restype = ctypes.c_long
_librsync.rs_patch_file.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]


def librsyncSignature(filename, base64Encoded=True):
	"""
	Get the signature of the file to patch.
	"""
	filename = forceFilename(filename)
	try:
		tf = tempfile.NamedTemporaryFile(delete=False)
		sig_file = tf.name
		tf.close()
		if not os.path.isfile(filename):
			raise FileNotFoundError(f"File '{filename}' not found")
		try:
			fh = _librsync.fopen(filename.encode("utf-8"), "rb")
			sh = _librsync.fopen(sig_file.encode("utf-8"), "wb")
			if _librsync.rs_sig_file(fh, sh, RSYNC_BLOCK_LENGTH, RSYNC_STRONG_LENGTH, None) != 0:
				raise RuntimeError("librsync.rs_sig_file call failed")
		finally:
			if fh:
				_librsync.fclose(fh)
			if sh:
				_librsync.fclose(sh)
		with open(sig_file, "rb") as sh:
			if base64Encoded:
				return base64.encodebytes(sh.read())
			else:
				return sh.read()
	except Exception as sigError:
		raise RuntimeError(f"Failed to get librsync signature from {filename}: {forceUnicode(sigError)}")
	finally:
		os.unlink(sig_file)

def librsyncDeltaFile(filename, signature, deltafile):
	"""
	Create delta file from original file and the signature of the file to patch.
	"""
	filename = forceFilename(filename)
	deltafile = forceFilename(deltafile)
	logger.debug("Creating deltafile %s on base of %s", deltafile, filename)

	try:
		tf = tempfile.NamedTemporaryFile("wb", delete=False)
		sig_file = tf.name
		tf.write(signature)
		tf.close()
		try:
			fh = _librsync.fopen(filename.encode("utf-8"), "rb")
			sh = _librsync.fopen(sig_file.encode("utf-8"), "rb")
			dh = _librsync.fopen(deltafile.encode("utf-8"), "wb")
			sig = ctypes.c_void_p()
			if _librsync.rs_loadsig_file(sh, ctypes.byref(sig), None) != 0:
				raise RuntimeError("librsync.rs_loadsig_file call failed")
			if _librsync.rs_build_hash_table(sig) != 0:
				raise RuntimeError("librsync.rs_build_hash_table call failed")
			if _librsync.rs_delta_file(sig, fh, dh, None) != 0:
				raise RuntimeError("librsync.rs_delta_file call failed")
		finally:
			if fh:
				_librsync.fclose(fh)
			if sh:
				_librsync.fclose(sh)
			if dh:
				_librsync.fclose(dh)
	except Exception as sigError:
		raise RuntimeError(f"Failed to write delta file {deltafile}: {forceUnicode(sigError)}")
	finally:
		os.unlink(sig_file)

def librsyncPatchFile(oldfile, deltafile, newfile):
	"""
	Create the new file from old file and delta file.
	"""
	logger.debug("Librsync patch: old file %s, delta file %s, new file %s", oldfile, deltafile, newfile)
	
	oldfile = forceFilename(oldfile)
	newfile = forceFilename(newfile)
	deltafile = forceFilename(deltafile)

	if oldfile == newfile:
		raise ValueError("oldfile and newfile are the same file")
	if deltafile == newfile:
		raise ValueError("deltafile and newfile are the same file")
	if deltafile == oldfile:
		raise ValueError("oldfile and deltafile are the same file")
	
	try:
		try:
			oh = _librsync.fopen(oldfile.encode("utf-8"), "rb")
			dh = _librsync.fopen(deltafile.encode("utf-8"), "rb")
			nh = _librsync.fopen(newfile.encode("utf-8"), "wb")
			if  _librsync.rs_patch_file(oh, dh, nh, None) != 0:
				raise RuntimeError("librsync.rs_patch_file call failed")
		finally:
			if oh:
				_librsync.fclose(oh)
			if dh:
				_librsync.fclose(dh)
			if nh:
				_librsync.fclose(nh)
	except Exception as patchError:
		raise RuntimeError(f"Failed to patch file {oldfile}: {forceUnicode(patchError)}")
