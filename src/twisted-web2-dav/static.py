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
WebDAV-aware static resources.
"""

__all__ = ["DAVFile"]

import os

from twisted.python import log
from twisted.internet.defer import succeed, deferredGenerator, waitForDeferred
from twisted.web2.static import File
from twisted.web2 import responsecode, dirlist
from twisted.web2.http import RedirectResponse
from OPSI.dav import davxml
from OPSI.dav.resource import DAVResource, davPrivilegeSet
from OPSI.dav.util import bindMethods

try:
    from OPSI.dav.xattrprops import xattrPropertyStore as DeadPropertyStore
except ImportError:
    log.msg("No dead property store available; using nonePropertyStore.")
    log.msg("Setting of dead properties will not be allowed.")
    from OPSI.dav.noneprops import NonePropertyStore as DeadPropertyStore

class DAVFile (DAVResource, File):
    """
    WebDAV-accessible File resource.

    Extends twisted.web2.static.File to handle WebDAV methods.
    """
    def __init__(self, path,
                 defaultType="text/plain",
                 indexNames=None):
        """
        @param path: the path of the file backing this resource.
        @param defaultType: the default mime type (as a string) for this
            resource and (eg. child) resources derived from it.
        @param indexNames: a sequence of index file names.
        @param acl: an L{IDAVAccessControlList} with the .
        """
        super(DAVFile, self).__init__(path,
                                      defaultType = defaultType,
                                      ignoredExts = (),
                                      processors  = None,
                                      indexNames  = indexNames)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.fp.path)

    ##
    # WebDAV
    ##

    def davComplianceClasses(self):
        return ("1", "access-control") # Add "2" when we have locking

    def deadProperties(self):
        if not hasattr(self, "_dead_properties"):
            self._dead_properties = DeadPropertyStore(self)
        return self._dead_properties

    def isCollection(self):
        """
        See L{IDAVResource.isCollection}.
        """
        for child in self.listChildren(): return True
        return self.fp.isdir()

    ##
    # ACL
    ##

    def supportedPrivileges(self, request):
        return succeed(davPrivilegeSet)

    ##
    # Workarounds for issues with File
    ##

    def ignoreExt(self, ext):
        """
        Does nothing; doesn't apply to this subclass.
        """
        pass

    def locateChild(self, req, segments):
        """
        See L{IResource}C{.locateChild}.
        """
        # If getChild() finds a child resource, return it
        child = self.getChild(segments[0])
        if child is not None: return (child, segments[1:])
        
        # If we're not backed by a directory, we have no children.
        # But check for existance first; we might be a collection resource
        # that the request wants created.
        self.fp.restat(False)
        if self.fp.exists() and not self.fp.isdir():
            return (None, ())

        # OK, we need to return a child corresponding to the first segment
        path = segments[0]
        
        if path == "":
            # Request is for a directory (collection) resource
            return (self, ())

        return (self.createSimilarFile(self.fp.child(path).path), segments[1:])

    def createSimilarFile(self, path):
        return self.__class__(path, defaultType=self.defaultType, indexNames=self.indexNames[:])

#
# Attach method handlers to DAVFile
#

import OPSI.dav.method

bindMethods(OPSI.dav.method, DAVFile)
