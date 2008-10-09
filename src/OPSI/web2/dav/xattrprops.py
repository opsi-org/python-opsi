##
# Copyright (c) 2005 Apple Computer, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# DRI: Wilfredo Sanchez, wsanchez@apple.com
##

"""
DAV Property store using file system extended attributes.

This API is considered private to static.py and is therefore subject to
change.
"""

__all__ = ["xattrPropertyStore"]

import urllib
import sys
import zlib
from time import sleep
from random import random
from errno import EAGAIN
from zlib import compress, decompress

import xattr

if getattr(xattr, 'xattr', None) is None:
    raise ImportError("wrong xattr package imported")

from twisted.python import log
from OPSI.web2 import responsecode
from OPSI.web2.http import HTTPError, StatusResponse
from OPSI.web2.dav import davxml

class xattrPropertyStore (object):
    """

    This implementation uses Bob Ippolito's xattr package, available from::

        http://undefined.org/python/#xattr

    Note that the Bob's xattr package is specific to Linux and Darwin, at least
    presently.
    """
    #
    # Dead properties are stored as extended attributes on disk.  In order to
    # avoid conflicts with other attributes, prefix dead property names.
    #
    deadPropertyXattrPrefix = "WebDAV:"
 
    # Linux seems to require that attribute names use a "user." prefix.
    # FIXME: Is is a system-wide thing, or a per-filesystem thing?
    #   If the latter, how to we detect the file system?
    if sys.platform == "linux2":
        deadPropertyXattrPrefix = "user."

    def _encode(clazz, name):
        result = urllib.quote("{%s}%s" % name, safe='{}:')
        r = clazz.deadPropertyXattrPrefix + result
        return r

    def _decode(clazz, name):
        name = urllib.unquote(name[len(clazz.deadPropertyXattrPrefix):])

        index = name.find("}")
    
        if (index is -1 or not len(name) > index or not name[0] == "{"):
            raise ValueError("Invalid encoded name: %r" % (name,))
    
        return (name[1:index], name[index+1:])

    _encode = classmethod(_encode)
    _decode = classmethod(_decode)

    def __init__(self, resource):
        self.resource = resource
        self.attrs = xattr.xattr(self.resource.fp.path)

    def get(self, qname):
        try:
            data = self.attrs[self._encode(qname)]
            try:
                value = decompress(data)
            except zlib.error:
                # Value is not compressed; data was stored by old
                # code.  This is easy to handle, so let's keep
                # compatibility here.
                value = data
            del data
        except KeyError:
            raise HTTPError(StatusResponse(
                responsecode.NOT_FOUND,
                "No such property: {%s}%s" % qname
            ))

        try:
            doc = davxml.WebDAVDocument.fromString(value)

            return doc.root_element
        except ValueError:
            msg = "Invalid property value stored on server: {%s}%s %s" % (qname[0], qname[1], value)
            log.err(msg)
            raise HTTPError(StatusResponse(responsecode.INTERNAL_SERVER_ERROR, msg))

    def set(self, property):
        for n in range(20):
            try:
                self.attrs[self._encode(property.qname())] = compress(property.toxml())
            except IOError, error:
                if error.errno != EAGAIN:
                    raise
                sleep(random() / 10) # OMG Brutal Hax
            else:
                break
    

        # Update the resource because we've modified it
        self.resource.fp.restat()

    def delete(self, qname):
        try:
            del(self.attrs[self._encode(qname)])
        except KeyError:
            # RFC 2518 Section 12.13.1 says that removal of
            # non-existing property is not an error.
            pass

    def contains(self, qname):
        try:
            return self._encode(qname) in self.attrs
        except TypeError:
            return False

    def list(self):
        prefix     = self.deadPropertyXattrPrefix
        prefix_len = len(prefix)

        return [ self._decode(name) for name in self.attrs if name.startswith(prefix) ]
