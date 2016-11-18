import logging
from twisted.internet import protocol, reactor
from twisted.cred.portal import Portal
import twisted.internet.threads as ti_threads
import twisted.protocols.ftp as ftp
import twisted.cred.checkers as tc_checkers
import listener

class FakeNetFTP(ftp.FTP):
    def processCommand(self, cmd, *params):
        ret = ftp.FTP.processCommand(self, cmd, *params)
        self.factory.logger.info('%s %s' % (cmd, ' '.join(params)))
        return ret

class FakeNetFTPFactory(ftp.FTPFactory):
    def __init__(self, portal = None, userAnonymous = 'anonymous'):
        ftp.FTPFactory.__init__(self, portal, userAnonymous)
        self.protocol = FakeNetFTP

class FTPListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)
        self.portal = Portal(
            ftp.FTPRealm(self.config.get('ftproot', 'defaultFiles')),
            [tc_checkers.AllowAnonymousAccess()]
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
