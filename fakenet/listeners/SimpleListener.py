"""Supports echo and discard
"""
import logging
from irc.server import *
from twisted.internet import protocol, reactor
import irc.client
import listener
import threading

STATIC_QOTD = 'Quote of the day\n'

def _strip_cr_lf(s): return s.rstrip('\r\n').rstrip('\n') # For display

class Echo(protocol.Protocol):
    def connectionMade(self):
        if self.application == 'qotd':
            self.logger.info('Connection established, writing %s and closing' %
                    (STATIC_QOTD))
            self.transport.write(STATIC_QOTD)
            self.transport.loseConnection()

    def dataReceived(self, data):
        self.logger.info('Received %s' % (_strip_cr_lf(data)))
        if self.application == 'echo':
            self.transport.write(data)

class EchoUDP(protocol.DatagramProtocol):
    def datagramReceived(self, datagram, address):
        self.logger.info('Received %s' % (_strip_cr_lf(datagram)))
        if self.application == 'echo':
            self.transport.write(datagram, address)
        elif self.application == 'qotd':
            self.transport.write(STATIC_QOTD, address)

class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        ret = Echo()
        ret.logger = self.logger
        ret.application = self.application
        return ret

supported_app_layer_protos = [
    'echo',
    'discard',
    'qotd',
]

class EchoListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)

    def start(self):
        listener.FakeNetBaseListener.start(self)

        application = 'echo'
        if 'application' in self.config.keys():
            application = self.config['application'].lower()

        if application not in supported_app_layer_protos:
            raise ValueError('Invalid application layer protocol %s' %
                    (application))

        if 'tcp' == self.config['protocol'].lower():
            e = EchoFactory()
            e.logger = self.logger
            e.application = application
            reactor.listenTCP(self.getportno(7), e)
        elif 'udp' == self.config['protocol'].lower():
            e = EchoUDP()
            e.logger = self.logger
            e.application = application
            reactor.listenUDP(self.getportno(7), e)
        else:
            raise ValueError('Invalid protocol ' +
                    str(self.config['protocol']))

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        # TwistedMixIn will induce FakeNet to call reactor.stop() for us


if __name__ == '__main__':
    listener.run_standalone(EchoListener)
