from twisted.cred import credentials
from twisted.cred.portal import Portal
from twisted.internet import defer
from twisted.internet import protocol, reactor
from twisted.python import filepath
from zope.interface import implements, Interface, Attribute
import listener
import logging
import twisted.cred.checkers as tc_checkers
import twisted.internet.threads as ti_threads
import twisted.protocols.ftp as ftp

class LaxAccess:
    implements(tc_checkers.ICredentialsChecker)
    credentialInterfaces = credentials.IUsernamePassword,

    def requestAvatarId(self, credentials):
        return defer.succeed(credentials.username)


class LaxFTPRealm(ftp.BaseFTPRealm):
    """
    @type anonymousRoot: L{twisted.python.filepath.FilePath}
    @ivar anonymousRoot: Root of the filesystem to which anonymous
        users will be granted access.

    @type userHome: L{filepath.FilePath}
    @ivar userHome: Root of the filesystem containing user home directories.
    """
    def __init__(self, anonymousRoot, userHome = None):
        if userHome is None:
            userHome = anonymousRoot
        ftp.BaseFTPRealm.__init__(self, anonymousRoot)
        self.userHome = filepath.FilePath(userHome)


    def getHomeDirectory(self, avatarId):
        """
        Use C{avatarId} as a single path segment to construct a child of
        C{self.userHome} and return that child.
        """
        return self.userHome


class FakeNetFTP(ftp.FTP):
    def processCommand(self, cmd, *params):
        ret = ftp.FTP.processCommand(self, cmd, *params)
        self.factory.logger.info('%s %s' % (cmd, ' '.join(params)))
        return ret

    def ftp_LIST(self, path=''):
        ret = ftp.FTP.ftp_LIST(self, path)
        return ret


class FakeNetFTPFactory(ftp.FTPFactory):
    def __init__(self, portal = None, userAnonymous = 'anonymous'):
        ftp.FTPFactory.__init__(self, portal, userAnonymous)
        self.protocol = FakeNetFTP


class FTPListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)
        ftproot = self.config.get('ftproot', 'defaultFiles')
        self.portal = Portal(
            LaxFTPRealm(ftproot, ftproot),
            [tc_checkers.AllowAnonymousAccess(), LaxAccess()]
        )

    def start(self):
        listener.FakeNetBaseListener.start(self)

        self.server = FakeNetFTPFactory(self.portal)
        # self.server = ftp.FTPFactory(self.portal)
        self.server.logger = self.logger
        reactor.listenTCP(int(self.config.get('port', 21)), self.server)

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        if not self.server is None:
            self.server = None


if __name__ == '__main__':
    listener.run_standalone(FTPListener)
