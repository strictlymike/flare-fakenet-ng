import logging
from irc.server import *
from twisted.internet import protocol, reactor
import irc.client
import listener
import threading

class Echo(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()

class EchoListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)

    def start(self):
        listener.FakeNetBaseListener.start(self)
        portno = int(self.config.get('port', 7))

        self.server = EchoFactory()
        self.server.logger = self.logger
        reactor.listenTCP(portno, self.server)

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        if not self.server is None:
            self.server = None


if __name__ == '__main__':
    listener.run_standalone(EchoListener)
