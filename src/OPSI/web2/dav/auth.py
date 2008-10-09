from zope.interface import implements, Interface
from twisted.internet import defer
from twisted.cred import checkers, error, portal
from OPSI.web2.resource import WrapperResource
from OPSI.web2.dav import davxml
from OPSI.web2.dav.davxml import twisted_private_namespace

__all__ = ["PrincipalCredentials", "AuthenticationWrapper"]

class AuthenticationWrapper(WrapperResource):
    def __init__(self, resource, portal, credentialFactories, loginInterfaces):
        """Wrap the given resource and use the parameters to set up the request
        to allow anyone to challenge and handle authentication.

        @param resource: L{DAVREsource} FIXME: This should get promoted to 
            OPSI.web2.auth
        @param portal: The cred portal
        @param credentialFactories: Sequence of credentialFactories that can
            be used to authenticate by resources in this tree.
        @param loginInterfaces: More cred stuff
        """
        super(AuthenticationWrapper, self).__init__(resource)

        self.portal = portal
        self.credentialFactories = dict([(factory.scheme, factory)
                                         for factory in credentialFactories])
        self.loginInterfaces = loginInterfaces

    def hook(self, req):
        req.portal = self.portal
        req.credentialFactories = self.credentialFactories
        req.loginInterfaces = self.loginInterfaces


class IPrincipal(Interface):
    pass

class DavRealm(object):
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IPrincipal in interfaces:
            return IPrincipal, davxml.Principal(davxml.HRef(avatarId))
        
        raise NotImplementedError("Only IPrincipal interface is supported")


class IPrincipalCredentials(Interface):
    pass


class PrincipalCredentials(object):
    implements(IPrincipalCredentials)

    def __init__(self, principal, principalURI, credentials):
        self.principal = principal
        self.principalURI = principalURI
        self.credentials = credentials

    def checkPassword(self, password):
        return self.credentials.checkPassword(password)


class TwistedPropertyChecker:
    implements(checkers.ICredentialsChecker)

    credentialInterfaces = (IPrincipalCredentials,)

    def _cbPasswordMatch(self, matched, principalURI):
        if matched:
            return principalURI
        else:
            raise error.UnauthorizedLogin(
                "Bad credentials for: %s" % (principalURI,))

    def requestAvatarId(self, credentials):
        pcreds = IPrincipalCredentials(credentials)
        pswd = str(pcreds.principal.readDeadProperty(TwistedPasswordProperty))

        d = defer.maybeDeferred(credentials.checkPassword, pswd)
        d.addCallback(self._cbPasswordMatch, pcreds.principalURI)
        return d

##
# Utilities
##

class TwistedPasswordProperty (davxml.WebDAVTextElement):
    namespace = twisted_private_namespace
    name = "password"

davxml.registerElement(TwistedPasswordProperty)
