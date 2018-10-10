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

from twisted.trial import unittest
from OPSI.web2.dav import util

class Utilities(unittest.TestCase):
    """
    Utilities.
    """
    def test_normalizeURL(self):
        """
        normalizeURL()
        """
        self.assertEqual(util.normalizeURL("http://server//foo"), "http://server/foo")
        self.assertEqual(util.normalizeURL("http://server/foo/.."), "http://server/")
        self.assertEqual(util.normalizeURL("/foo/bar/..//"), "/foo")
        self.assertEqual(util.normalizeURL("/foo/bar/.//"), "/foo/bar")
        self.assertEqual(util.normalizeURL("//foo///bar/../baz"), "/foo/baz")
        self.assertEqual(util.normalizeURL("//foo///bar/./baz"), "/foo/bar/baz")
        self.assertEqual(util.normalizeURL("///../"), "/")
        self.assertEqual(util.normalizeURL("/.."), "/")

    def test_joinURL(self):
        """
        joinURL()
        """
        self.assertEqual(util.joinURL("http://server/foo/"), "http://server/foo/")
        self.assertEqual(util.joinURL("http://server/foo", "/bar"), "http://server/foo/bar")
        self.assertEqual(util.joinURL("http://server/foo", "bar"), "http://server/foo/bar")
        self.assertEqual(util.joinURL("http://server/foo/", "/bar"), "http://server/foo/bar")
        self.assertEqual(util.joinURL("http://server/foo/", "/bar/.."), "http://server/foo")
        self.assertEqual(util.joinURL("http://server/foo/", "/bar/."), "http://server/foo/bar")
        self.assertEqual(util.joinURL("http://server/foo/", "/bar/../"), "http://server/foo/")
        self.assertEqual(util.joinURL("http://server/foo/", "/bar/./"), "http://server/foo/bar/")
        self.assertEqual(util.joinURL("http://server/foo/../", "/bar"), "http://server/bar")
        self.assertEqual(util.joinURL("/foo/"), "/foo/")
        self.assertEqual(util.joinURL("/foo", "/bar"), "/foo/bar")
        self.assertEqual(util.joinURL("/foo", "bar"), "/foo/bar")
        self.assertEqual(util.joinURL("/foo/", "/bar"), "/foo/bar")
        self.assertEqual(util.joinURL("/foo/", "/bar/.."), "/foo")
        self.assertEqual(util.joinURL("/foo/", "/bar/."), "/foo/bar")
        self.assertEqual(util.joinURL("/foo/", "/bar/../"), "/foo/")
        self.assertEqual(util.joinURL("/foo/", "/bar/./"), "/foo/bar/")
        self.assertEqual(util.joinURL("/foo/../", "/bar"), "/bar")
        self.assertEqual(util.joinURL("/foo", "/../"), "/")
        self.assertEqual(util.joinURL("/foo", "/./"), "/foo/")

    def test_parentForURL(self):
        """
        parentForURL()
        """
        self.assertEqual(util.parentForURL("http://server/"), None)
        self.assertEqual(util.parentForURL("http://server//"), None)
        self.assertEqual(util.parentForURL("http://server/foo/.."), None)
        self.assertEqual(util.parentForURL("http://server/foo/../"), None)
        self.assertEqual(util.parentForURL("http://server/foo/."), "http://server/")
        self.assertEqual(util.parentForURL("http://server/foo/./"), "http://server/")
        self.assertEqual(util.parentForURL("http://server/foo"), "http://server/")
        self.assertEqual(util.parentForURL("http://server//foo"), "http://server/")
        self.assertEqual(util.parentForURL("http://server/foo/bar/.."), "http://server/")
        self.assertEqual(util.parentForURL("http://server/foo/bar/."), "http://server/foo/")
        self.assertEqual(util.parentForURL("http://server/foo/bar"), "http://server/foo/")
        self.assertEqual(util.parentForURL("http://server/foo/bar/"), "http://server/foo/")
        self.assertEqual(util.parentForURL("/"), None)
        self.assertEqual(util.parentForURL("/foo/.."), None)
        self.assertEqual(util.parentForURL("/foo/../"), None)
        self.assertEqual(util.parentForURL("/foo/."), "/")
        self.assertEqual(util.parentForURL("/foo/./"), "/")
        self.assertEqual(util.parentForURL("/foo"), "/")
        self.assertEqual(util.parentForURL("/foo"), "/")
        self.assertEqual(util.parentForURL("/foo/bar/.."), "/")
        self.assertEqual(util.parentForURL("/foo/bar/."), "/foo/")
        self.assertEqual(util.parentForURL("/foo/bar"), "/foo/")
        self.assertEqual(util.parentForURL("/foo/bar/"), "/foo/")
