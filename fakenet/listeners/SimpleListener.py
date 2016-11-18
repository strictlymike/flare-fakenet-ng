from irc.server import *
from twisted.internet import protocol, reactor
from twisted.protocols.wire import Chargen
import binascii
import irc.client
import listener
import logging
import random
import struct
import threading
import time

NM_ECHO = 'echo'
NM_DISCARD = 'discard'
NM_QOTD = 'qotd'
NM_DAYTIME = 'daytime'
NM_TIME = 'time'
NM_CHARGEN = 'chargen'

SUPPORTED_APP_LAYER_PROTOS = [
    NM_ECHO,
    NM_DISCARD,
    NM_QOTD,
    NM_CHARGEN,
    NM_DAYTIME,
    NM_TIME,
]

# Can't seem to find the original qotd.txt or whatever.
QOTDS = [
    'Don\'t forget to FLOSS! http://flosseveryday.info\n',
]

NOISE = r'@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~ !"#$%&?'

PREVIEW_LEN = 15

def _strip_cr_lf(s): return s.rstrip('\r\n').rstrip('\n') # For display

def _rand_qotd(l): return random.choice(l)
def _truncate(q): return q[:PREVIEW_LEN] + '...' if len(q) > PREVIEW_LEN else q
def _preview(q): return _truncate(q).replace('|', '\\n').replace('\t','\\t')
def _gentime(): return struct.pack('!i', int(time.time()))
def _gendatetime(): return time.asctime(time.gmtime(time.time())) + '\r\n'

class SimpleUDP(protocol.DatagramProtocol):
    def datagramReceived(self, datagram, address):
        global QOTDS
        global NOISE
        self.logger.info('Received %s (0000: %s)' %
                (_strip_cr_lf(datagram), binascii.hexlify(datagram)))
        if self.application == NM_ECHO:
            self.transport.write(datagram, address)
        elif self.application == NM_QOTD:
            qotd = _rand_qotd(QOTDS)
            self.logger.info('Writing "%s"' % (_preview(qotd)))
            self.transport.write(qotd.replace('|', '\n'), address)
        elif self.application == NM_CHARGEN:
            n = random.choice(xrange(513))
            self.logger.info('Responding with %d bytes' % (n))
            self.transport.write((NOISE * (512/len(NOISE)))[:n],
                    address)
        elif self.application == NM_DAYTIME:
            s = _gendatetime()
            self.logger.info('Writing "%s"' % (_strip_cr_lf(s)))
            self.transport.write(s, address)
        elif self.application == NM_TIME:
            t = _gentime()
            self.logger.info('Writing 0x%s' % (binascii.hexlify(t)))
            self.transport.write(t, address)

class SimpleTCP(protocol.Protocol, Chargen):
    def connectionMade(self):
        global QOTDS
        self.logger.info('Connection established')
        if self.application == NM_QOTD:
            qotd = _rand_qotd(QOTDS)
            self.logger.info('Writing "%s" and closing connection' % (_preview(qotd)))
            self.transport.write(qotd.replace('|', '\n'))
            self.transport.loseConnection()
        elif self.application == NM_CHARGEN:
            self.logger.info('Sending bytes...')
            Chargen.connectionMade(self)
        elif self.application == NM_DAYTIME:
            s = _gendatetime()
            self.logger.info('Writing "%s" and closing connection' %
                    (_strip_cr_lf(s)))
            self.transport.write(s)
            self.transport.loseConnection()
        elif self.application == NM_TIME:
            t = _gentime()
            self.logger.info('Writing 0x%s and closing connection' %
                    (binascii.hexlify(t)))
            self.transport.write(t)
            self.transport.loseConnection()

    def connectionLost(self, reason):
        self.logger.info('Connection lost')

    def dataReceived(self, data):
        self.logger.info('Received %s (0000: %s)' %
                (_strip_cr_lf(data), binascii.hexlify(data)))
        if self.application == NM_ECHO:
            self.transport.write(data)

class SimpleFactory(protocol.Factory):
    def buildProtocol(self, addr):
        ret = SimpleTCP()
        ret.logger = self.logger
        ret.application = self.application
        return ret

class SimpleListener(listener.FakeNetBaseListener, listener.TwistedMixIn):
    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        global QOTDS
        listener.FakeNetBaseListener.__init__(self, config, name, logging_level)

        self.application = NM_ECHO
        if 'application' in self.config.keys():
            self.application = self.config['application'].lower()

        if self.application not in SUPPORTED_APP_LAYER_PROTOS:
            raise ValueError('Invalid application layer protocol %s' %
                    (self.application))

        if NM_QOTD == self.application:
            qotdfile = str(self.config.get('qotdfile', 'listeners/qotd.txt'))
            QOTDS = open(qotdfile, 'r').readlines()


    def start(self):
        listener.FakeNetBaseListener.start(self)

        if 'tcp' == self.config['protocol'].lower():
            e = SimpleFactory()
            e.logger = self.logger
            e.application = self.application
            reactor.listenTCP(self.getportno(7), e)
        elif 'udp' == self.config['protocol'].lower():
            e = SimpleUDP()
            e.logger = self.logger
            e.application = self.application
            reactor.listenUDP(self.getportno(7), e)
        else:
            raise ValueError('Invalid protocol ' +
                    str(self.config['protocol']))

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        # TwistedMixIn will induce FakeNet to call reactor.stop() for us


if __name__ == '__main__':
    listener.run_standalone(SimpleListener)
