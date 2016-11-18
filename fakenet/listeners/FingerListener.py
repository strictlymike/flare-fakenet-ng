import logging
from twisted.internet import protocol, reactor
from twisted.protocols.finger import Finger
import listener
import time
import threading

class FakeNetFinger(Finger):
    def forwardQuery(self, slash_w, user, host):
        Finger.forwardQuery(self, slash_w, user, host)
        self.logger.info(
            'Forward query slash_w %s user %s host %s' % (slash_w, user, host))

    def getDomain(self, slash_w):
        Finger.getDomain(self, slash_w)
        self.logger.info(
            'Get domain slash_w %s' % (slash_w)
           )

    def getUser(self, slash_w, user):
        Finger.getUser(self, slash_w, user)
        self.logger.info('Get user slash_w %s user %s' % (slash_w, user))


class FingerFactory(protocol.Factory):
    def buildProtocol(self, addr):
        f = FakeNetFinger()
        f.logger = self.logger
        return f

class FingerListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)

    def start(self):
        listener.FakeNetBaseListener.start(self)

        f = FingerFactory()
        f.logger = self.logger
        reactor.listenTCP(self.getportno(79), f)

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        # TwistedMixIn will induce FakeNet to call reactor.stop() for us


if __name__ == '__main__':
    listener.run_standalone(FingerListener)
