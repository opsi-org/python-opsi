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
General utility functions.

This module holds various utility functions for the work with opsi.
This includes functions for (de)serialisation, converting classes from
or to JSON, working with librsync and more.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import os
from contextlib import closing

from OPSI.Logger import Logger
from OPSI.Types import forceFilename, forceUnicode

__all__ = (
    'librsyncDeltaFile', 'librsyncPatchFile', 'librsyncSignature',
)

logger = Logger()

if os.name == 'posix':
    from duplicity import librsync
elif os.name == 'nt':
    try:
        import librsync
    except Exception as e:
        logger.error(u"Failed to import librsync: %s" % e)


def librsyncSignature(filename, base64Encoded=True):
    filename = forceFilename(filename)
    try:
        with open(filename, 'rb') as f:
            with closing(librsync.SigFile(f)) as sf:
                sig = sf.read()

                if base64Encoded:
                    sig = base64.encodestring(sig)

                return sig
    except Exception as sigError:
        raise RuntimeError(
            u"Failed to get librsync signature from %s: %s" % (
                filename,
                forceUnicode(sigError)
            )
        )


def librsyncPatchFile(oldfile, deltafile, newfile):
    logger.debug(u"Librsync patch: old file {!r}, delta file {!r}, new file {!r}", oldfile, deltafile, newfile)

    oldfile = forceFilename(oldfile)
    newfile = forceFilename(newfile)
    deltafile = forceFilename(deltafile)

    if oldfile == newfile:
        raise ValueError(u"Oldfile and newfile are the same file")
    if deltafile == newfile:
        raise ValueError(u"deltafile and newfile are the same file")
    if deltafile == oldfile:
        raise ValueError(u"oldfile and deltafile are the same file")

    bufsize = 1024 * 1024
    try:
        with open(oldfile, "rb") as of:
            with open(deltafile, "rb") as df:
                with open(newfile, "wb") as nf:
                    with closing(librsync.PatchedFile(of, df)) as pf:
                        data = True
                        while data:
                            data = pf.read(bufsize)
                            nf.write(data)
    except Exception as patchError:
        logger.debug(
            "Patching {!r} with delta {!r} into {!r} failed: {}",
            oldfile, deltafile, newfile, patchError
        )
        raise RuntimeError(u"Failed to patch file %s: %s" % (oldfile, forceUnicode(patchError)))


def librsyncDeltaFile(filename, signature, deltafile):
    bufsize = 1024 * 1024
    filename = forceFilename(filename)
    deltafile = forceFilename(deltafile)
    logger.debug("Creating deltafile {!r} on base of {!r}", deltafile, filename)
    try:
        with open(filename, "rb") as f:
            with open(deltafile, "wb") as df:
                with closing(librsync.DeltaFile(signature, f)) as ldf:
                    data = True
                    while data:
                        data = ldf.read(bufsize)
                        df.write(data)
    except Exception as e:
        raise RuntimeError(
            u"Failed to write delta file %s: %s" % (deltafile, forceUnicode(e))
        )
