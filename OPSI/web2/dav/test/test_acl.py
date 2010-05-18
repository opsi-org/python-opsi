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

import os

from twisted.cred.portal import Portal

from OPSI.web2 import responsecode
from OPSI.web2.auth import basic
from OPSI.web2.stream import MemoryStream
from OPSI.web2.dav import davxml
from OPSI.web2.dav.resource import DAVPrincipalCollectionResource
from OPSI.web2.dav.util import davXMLFromStream
from OPSI.web2.dav.auth import TwistedPasswordProperty, IPrincipal, DavRealm, TwistedPropertyChecker, AuthenticationWrapper

import OPSI.web2.dav.test.util
from OPSI.web2.test.test_server import SimpleRequest
from OPSI.web2.dav.test.util import Site, serialize
from OPSI.web2.dav.test.test_resource import TestResource, TestDAVPrincipalResource

class TestPrincipalsCollection(DAVPrincipalCollectionResource, TestResource):
    def __init__(self, url, children):
        DAVPrincipalCollectionResource.__init__(self, url)
        TestResource.__init__(self, url, children, principalCollections=(self,))
    
    def principalForUser(self, user):
        return self.principalForShortName('users', user)

    def principalForShortName(self, type, shortName):
        typeResource = self.children.get(type, None)
        user = None
        if typeResource:
            user = typeResource.children.get(shortName, None)

        return user

class ACL(OPSI.web2.dav.test.util.TestCase):
    """
    RFC 3744 (WebDAV ACL) tests.
    """
    def setUp(self):
        if not hasattr(self, "docroot"):
            self.docroot = self.mktemp()
            os.mkdir(self.docroot)

            userResource = TestDAVPrincipalResource("/principals/users/user01")
            userResource.writeDeadProperty(TwistedPasswordProperty("user01"))

            principalCollection = TestPrincipalsCollection(
                "/principals/", 
                children={"users": TestPrincipalsCollection(
                        "/principals/users/",
                        children={"user01": userResource})})

            rootResource = self.resource_class(self.docroot, principalCollections=(principalCollection,))

            portal = Portal(DavRealm())
            portal.registerChecker(TwistedPropertyChecker())

            credentialFactories = (basic.BasicCredentialFactory(""),)

            loginInterfaces = (IPrincipal,)

            self.site = Site(AuthenticationWrapper(
                rootResource, 
                portal,
                credentialFactories,
                loginInterfaces
            ))

            rootResource.setAccessControlList(self.grant(davxml.All()))

        for name, acl in (
            ("none"       , self.grant()),
            ("read"       , self.grant(davxml.Read())),
            ("read-write" , self.grant(davxml.Read(), davxml.Write())),
            ("unlock"     , self.grant(davxml.Unlock())),
            ("all"        , self.grant(davxml.All())),
        ):
            filename = os.path.join(self.docroot, name)
            if not os.path.isfile(filename):
                file(filename, "w").close()
            resource = self.resource_class(filename)
            resource.setAccessControlList(acl)

        for name, acl in (
            ("nobind" , self.grant()),
            ("bind"   , self.grant(davxml.Bind())),
            ("unbind" , self.grant(davxml.Bind(), davxml.Unbind())),
        ):
            dirname = os.path.join(self.docroot, name)
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            resource = self.resource_class(dirname)
            resource.setAccessControlList(acl)

    def test_COPY_MOVE_source(self):
        """
        Verify source access controls during COPY and MOVE.
        """
        # Restore starter files
        self.setUp()

        def work():
            dst_path = os.path.join(self.docroot, "copy_dst")
            dst_uri = "/" + os.path.basename(dst_path)

            for src, rcode in (
                ("nobind", responsecode.FORBIDDEN),
                ("bind",   responsecode.FORBIDDEN),
                ("unbind", responsecode.CREATED),
            ):
                src_path = os.path.join(self.docroot, "src_" + src)
                src_uri = "/" + os.path.basename(src_path)
                if not os.path.isdir(src_path):
                    os.mkdir(src_path)
                src_resource = self.resource_class(src_path)
                src_resource.setAccessControlList({
                    "nobind": self.grant(),
                    "bind"  : self.grant(davxml.Bind()),
                    "unbind": self.grant(davxml.Bind(), davxml.Unbind())
                }[src])
                for name, acl in (
                    ("none"       , self.grant()),
                    ("read"       , self.grant(davxml.Read())),
                    ("read-write" , self.grant(davxml.Read(), davxml.Write())),
                    ("unlock"     , self.grant(davxml.Unlock())),
                    ("all"        , self.grant(davxml.All())),
                ):
                    filename = os.path.join(src_path, name)
                    if not os.path.isfile(filename):
                        file(filename, "w").close()
                    resource = self.resource_class(filename)
                    resource.setAccessControlList(acl)

                for method in ("COPY", "MOVE"):
                    for name, code in (
                        ("none"       , {"COPY": responsecode.FORBIDDEN, "MOVE": rcode}[method]),
                        ("read"       , {"COPY": responsecode.CREATED,   "MOVE": rcode}[method]),
                        ("read-write" , {"COPY": responsecode.CREATED,   "MOVE": rcode}[method]),
                        ("unlock"     , {"COPY": responsecode.FORBIDDEN, "MOVE": rcode}[method]),
                        ("all"        , {"COPY": responsecode.CREATED,   "MOVE": rcode}[method]),
                    ):
                        path = os.path.join(src_path, name)
                        uri = src_uri + "/" + name
    
                        request = SimpleRequest(self.site, method, uri)
                        request.headers.setHeader("destination", dst_uri)
                        _add_auth_header(request)
    
                        def test(response, code=code, path=path):
                            if os.path.isfile(dst_path):
                                os.remove(dst_path)
    
                            if response.code != code:
                                d = davXMLFromStream(response.stream)
                                d.addCallback(self.oops, request, response, code, method, name)
                                return d
    
                        yield (request, test)

        return serialize(self.send, work())

    def test_COPY_MOVE_dest(self):
        """
        Verify destination access controls during COPY and MOVE.
        """
        def work():
            path = os.path.join(self.docroot, "read")
            uri  = "/" + os.path.basename(path)

            for method in ("COPY", "MOVE"):
                for name, code in (
                    ("nobind" , responsecode.FORBIDDEN),
                    ("bind"   , responsecode.CREATED),
                    ("unbind" , responsecode.CREATED),
                ):
                    collection_path = os.path.join(self.docroot, name)
                    dst_path = os.path.join(collection_path, "dst")

                    request = SimpleRequest(self.site, method, uri)
                    request.headers.setHeader("destination", "/" + name + "/dst")
                    _add_auth_header(request)

                    def test(response, code=code, dst_path=dst_path):
                        if os.path.isfile(dst_path):
                            os.remove(dst_path)

                        if response.code != code:
                            d = davXMLFromStream(response.stream)
                            d.addCallback(self.oops, request, response, code, method, name)
                            return d

                    # Restore starter files
                    self.setUp()

                    yield (request, test)

        return serialize(self.send, work())

    def test_DELETE(self):
        """
        Verify access controls during DELETE.
        """
        # Restore starter files
        self.setUp()

        def work():
            for name, code in (
                ("nobind" , responsecode.FORBIDDEN),
                ("bind"   , responsecode.FORBIDDEN),
                ("unbind" , responsecode.NO_CONTENT),
            ):
                collection_path = os.path.join(self.docroot, name)
                path = os.path.join(collection_path, "dst")

                file(path, "w").close()

                request = SimpleRequest(self.site, "DELETE", "/" + name + "/dst")
                _add_auth_header(request)

                def test(response, code=code, path=path):
                    if response.code != code:
                        d = davXMLFromStream(response.stream)
                        d.addCallback(self.oops, request, response, code, "DELETE", name)
                        return d

                yield (request, test)

        return serialize(self.send, work())

    def test_UNLOCK(self):
        """
        Verify access controls during UNLOCK of unowned lock.
        """
        raise NotImplementedError()

    test_UNLOCK.todo = "access controls on UNLOCK unimplemented"

    def test_MKCOL_PUT(self):
        """
        Verify access controls during MKCOL.
        """
        # Restore starter files
        self.setUp()

        for method in ("MKCOL", "PUT"):
            def work():
                for name, code in (
                    ("nobind" , responsecode.FORBIDDEN),
                    ("bind"   , responsecode.CREATED),
                    ("unbind" , responsecode.CREATED),
                ):
                    collection_path = os.path.join(self.docroot, name)
                    path = os.path.join(collection_path, "dst")

                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        os.rmdir(path)

                    request = SimpleRequest(self.site, method, "/" + name + "/dst")
                    _add_auth_header(request)

                    def test(response, code=code, path=path):
                        if response.code != code:
                            d = davXMLFromStream(response.stream)
                            d.addCallback(self.oops, request, response, code, method, name)
                            return d

                    yield (request, test)

        return serialize(self.send, work())

    def test_PUT_exists(self):
        """
        Verify access controls during PUT of existing file.
        """
        # Restore starter files
        self.setUp()

        def work():
            for name, code in (
                ("none"       , responsecode.FORBIDDEN),
                ("read"       , responsecode.FORBIDDEN),
                ("read-write" , responsecode.NO_CONTENT),
                ("unlock"     , responsecode.FORBIDDEN),
                ("all"        , responsecode.NO_CONTENT),
            ):
                path = os.path.join(self.docroot, name)

                request = SimpleRequest(self.site, "PUT", "/" + name)
                _add_auth_header(request)

                def test(response, code=code, path=path):
                    if response.code != code:
                        d = davXMLFromStream(response.stream)
                        d.addCallback(self.oops, request, response, code, "PUT", name)
                        return d

                yield (request, test)

        return serialize(self.send, work())

    def test_PROPFIND(self):
        """
        Verify access controls during PROPFIND.
        """
        raise NotImplementedError()

    test_PROPFIND.todo = "access controls on PROPFIND unimplemented"

    def test_PROPPATCH(self):
        """
        Verify access controls during PROPPATCH.
        """
        # Restore starter files
        self.setUp()

        def work():
            for name, code in (
                ("none"       , responsecode.FORBIDDEN),
                ("read"       , responsecode.FORBIDDEN),
                ("read-write" , responsecode.MULTI_STATUS),
                ("unlock"     , responsecode.FORBIDDEN),
                ("all"        , responsecode.MULTI_STATUS),
            ):
                path = os.path.join(self.docroot, name)

                request = SimpleRequest(self.site, "PROPPATCH", "/" + name)
                request.stream = MemoryStream(
                    davxml.WebDAVDocument(davxml.PropertyUpdate()).toxml()
                )
                _add_auth_header(request)

                def test(response, code=code, path=path):
                    if response.code != code:
                        d = davXMLFromStream(response.stream)
                        d.addCallback(self.oops, request, response, code, "PROPPATCH", name)
                        return d

                yield (request, test)

        return serialize(self.send, work())

    def test_GET_REPORT(self):
        """
        Verify access controls during GET and REPORT.
        """
        # Restore starter files
        self.setUp()

        def work():
            for method in ("GET", "REPORT"):
                if method == "GET":
                    ok = responsecode.OK
                elif method == "REPORT":
                    ok = responsecode.MULTI_STATUS
                else:
                    raise AssertionError("We shouldn't be here.  (method = %r)" % (method,))

                for name, code in (
                    ("none"       , responsecode.FORBIDDEN),
                    ("read"       , ok),
                    ("read-write" , ok),
                    ("unlock"     , responsecode.FORBIDDEN),
                    ("all"        , ok),
                ):
                    path = os.path.join(self.docroot, name)

                    request = SimpleRequest(self.site, method, "/" + name)
                    if method == "REPORT":
                        request.stream = MemoryStream(davxml.PrincipalPropertySearch().toxml())

                    _add_auth_header(request)

                    def test(response, code=code, path=path):
                        if response.code != code:
                            d = davXMLFromStream(response.stream)
                            d.addCallback(self.oops, request, response, code, method, name)
                            return d

                    yield (request, test)

        return serialize(self.send, work())

    def oops(self, doc, request, response, code, method, name):
        if doc is None:
            doc_xml = None
        else:
            doc_xml = doc.toxml()
    
        def gotResource(resource):
            return resource.accessControlList(request)

        def fail(acl):
            self.fail("Incorrect status code %s (!= %s) for %s of resource %s with %s ACL: %s\nACL: %s"
                      % (response.code, code, method, request.uri, name, doc_xml, acl.toxml()))

        d = request.locateResource(request.uri)
        d.addCallback(gotResource)
        d.addCallback(fail)

        return d

def _add_auth_header(request):
    request.headers.setHeader(
        "authorization",
        ("basic", "user01:user01".encode("base64"))
    )
