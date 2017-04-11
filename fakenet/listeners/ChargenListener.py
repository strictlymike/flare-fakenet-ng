import logging
from irc.server import *
from twisted.internet import protocol, reactor
from twisted.protocols.wire import Chargen
import irc.client
import random
import listener
import threading
import binascii

class ChargenUDP(protocol.DatagramProtocol):
    """Generate repeating noise (RFC 864)"""
    noise = r'@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~ !"#$%&?'

    def datagramReceived(self, datagram, address):
        n = random.choice(xrange(513))
        self.logger.info('Received %s' % (binascii.hexlify(datagram)))
        self.logger.info('Responding with %d bytes' % (n))
        self.transport.write((self.noise * (512/len(self.noise)))[:n], address)

class FakeNetChargenTCP(Chargen):
    def connectionMade(self):
        self.logger.info('Connection established, sending bytes...')
        Chargen.connectionMade(self)

    def connectionLost(self, reason):
        self.logger.info('Connection lost')

class ChargenFactory(protocol.Factory):
    def buildProtocol(self, addr):
        ret = FakeNetChargenTCP()
        ret.logger = self.logger
        return ret


class ChargenListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)

    def start(self):
        listener.FakeNetBaseListener.start(self)

        if 'tcp' == self.config['protocol'].lower():
            c = ChargenFactory()
            c.logger = self.logger
            reactor.listenTCP(self.getportno(19), c)
        elif 'udp' == self.config['protocol'].lower():
            c = ChargenUDP()
            c.logger = self.logger
            reactor.listenUDP(self.getportno(19), c)
        else:
            raise ValueError('Invalid protocol ' +
                    str(self.config['protocol']))

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        # TwistedMixIn will induce FakeNet to call reactor.stop() for us


if __name__ == '__main__':
    listener.run_standalone(ChargenListener)
