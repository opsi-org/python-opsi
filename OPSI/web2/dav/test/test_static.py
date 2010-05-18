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

from OPSI.web2.dav.test import util
from OPSI.web2.dav import davxml
from OPSI.web2.stream import readStream
from OPSI.web2.test.test_server import SimpleRequest

class DAVFileTest(util.TestCase):
    def test_renderPrivileges(self):
        request = SimpleRequest(self.site, 'GET', '/')

        def setDir2ACLs(dir2):
            dir2.setAccessControlList(davxml.ACL(
                    davxml.ACE(davxml.Principal(davxml.Authenticated()),
                               davxml.Grant(davxml.Privilege(davxml.All())))))
            return dir2

        def renderRoot(ign):
            d = request.locateResource('/')
            d.addCallback(lambda r: r.render(request))

            return d

        def assertListing(response):
            data = []
            def _collectData(sdata):
                data.append(str(sdata))

            d = readStream(response.stream, _collectData)

            d.addCallback(lambda ign: self.failIf('dir2' in ''.join(data)))

            return d

        d = request.locateResource('/dir2')
        d.addCallback(setDir2ACLs)
        d.addCallback(renderRoot)
        d.addCallback(assertListing)

        return d

    test_renderPrivileges.todo = "We changed the rules here; test needs an update"
