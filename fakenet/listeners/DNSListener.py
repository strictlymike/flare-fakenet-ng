import logging

import threading
import netifaces
import SocketServer
from dnslib import *

import ssl
import socket

class DNSListener():

    def __init__(self, config = {}, name = 'DNSListener', logging_level = logging.INFO):

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging_level)
            
        self.config = config
        self.local_ip = '0.0.0.0'
        self.server = None

        self.logger.info('Starting...')

        self.logger.debug('Initialized with config:')
        for key, value in config.iteritems():
            self.logger.debug('  %10s: %s', key, value)

    def start(self):

        # Start UDP listener  
        if self.config['protocol'].lower() == 'udp':
            self.logger.debug('Starting UDP ...')
            self.server = ThreadedUDPServer((self.local_ip, int(self.config.get('port', 53))), self.config, self.logger, UDPHandler)

        # Start TCP listener
        elif self.config['protocol'].lower() == 'tcp':
            self.logger.debug('Starting TCP ...')
            self.server = ThreadedTCPServer((self.local_ip, int(self.config.get('port', 53))), self.config, self.logger, TCPHandler)

        self.server.nxdomains = int(self.config.get('nxdomains', 0))

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def stop(self):
        self.logger.debug('Stopping...')
        
        # Stop listener
        if self.server:
            self.server.shutdown()
            self.server.server_close()  


class DNSHandler():
           
    def parse(self,data):
        response = ""
    
        try:
            # Parse data as DNS        
            d = DNSRecord.parse(data)

        except Exception, e:
            self.server.logger.error('Error: Invalid DNS Request')
            self.server.logger.info('%s', '-'*80)
            for line in hexdump_table(data):
                self.server.logger.info(line)
            self.server.logger.info('%s', '-'*80,)

        else:                 
            # Only Process DNS Queries
            if QR[d.header.qr] == "QUERY":
                     
                # Gather query parameters
                # NOTE: Do not lowercase qname here, because we want to see
                #       any case request weirdness in the logs.
                qname = str(d.q.qname)
                
                # Chop off the last period
                if qname[-1] == '.': qname = qname[:-1]

                qtype = QTYPE[d.q.qtype]

                # Omit reporting of noisy queries like eth1.localdomain
                if not qname.lower().startswith('eth1'):
                    self.server.logger.info('Received %s request for domain \'%s\'.', qtype, qname)

                # Create a custom response to the query
                response = DNSRecord(DNSHeader(id=d.header.id, bitmap=d.header.bitmap, qr=1, aa=1, ra=1), q=d.q)

                # Get fake record from the configuration or use the external address
                fake_record = self.server.config.get('dnsresponse', None)

                # Using socket.gethostbyname(socket.gethostname()) will return
                # 127.0.1.1 on Ubuntu systems that automatically add this entry
                # to /etc/hosts at install time or at other times. To produce a
                # plug-and-play user experience when using FakeNet for Linux,
                # we can't ask users to maintain /etc/hosts (which may involve
                # resolveconf or other work). Instead, we will give users a
                # choice:
                #
                #  * Configure a static IP, e.g. 192.0.2.123
                #    Returns that IP
                #
                #  * Set the DNS Listener DNSResponse to "GetHostByName"
                #    Returns socket.gethostbyname(socket.gethostname())
                #
                #  * Set the DNS Listener DNSResponse to "GetFirstNonLoopback"
                #    Returns the first non-loopback IP in use by the system
                #
                # If the DNSResponse setting is omitted, the listener will
                # default to getting the first non-loopback IPv4 address (for A
                # records).
                #
                # The DNSResponse setting was previously statically set to
                # 192.0.2.123, which for local scenarios works fine in Windows
                # standalone use cases because all connections to IP addresses
                # are redirected by Diverter. Changing the default setting to 
                #
                # IPv6 is not yet implemented, but when it is, it will be
                # necessary to consider how to get similar behavior to

                if fake_record == 'GetFirstNonLoopback':
                    for iface in netifaces.interfaces():
                        for link in netifaces.ifaddresses(iface)[netifaces.AF_INET]:
                            if 'addr' in link:
                                addr = link['addr']
                                if not addr.startswith('127.'):
                                    fake_record = addr
                                    break
                elif fake_record == 'GetHostByName' or fake_record is None:
                    fake_record = socket.gethostbyname(socket.gethostname())

                if qtype == 'A':

                    if self.server.nxdomains > 0:
                        self.server.logger.info('Ignoring query. NXDomains: %d', self.server.nxdomains)
                        self.server.nxdomains -= 1
                    else:
                        # dnslib doesn't like trailing dots
                        if fake_record[-1] == ".": fake_record = fake_record[:-1]

                        self.server.logger.info('Responding with \'%s\'', fake_record)
                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](fake_record)))

                response = response.pack()
                
        return response  

class UDPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):

        try:
            (data,socket) = self.request
            response = self.parse(data)

            if response:
                socket.sendto(response, self.client_address)

        except socket.error as msg:
            self.server.logger.error('Error: %s', msg.strerror or msg)

        except Exception, e:
            self.server.logger.error('Error: %s', e)

class TCPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):

        # Timeout connection to prevent hanging
        self.request.settimeout(int(self.server.config.get('timeout', 5)))

        try:
            data = self.request.recv(1024)
            
            # Remove the addition "length" parameter used in the
            # TCP DNS protocol
            data = data[2:]
            response = self.parse(data)
            
            if response:
                # Calculate and add the additional "length" parameter
                # used in TCP DNS protocol 
                length = binascii.unhexlify("%04x" % len(response))            
                self.request.sendall(length+response)      

        except socket.timeout:
            self.server.logger.warning('Connection timeout.')

        except socket.error as msg:
            self.server.logger.error('Error: %s', msg.strerror)

        except Exception, e:
            self.server.logger.error('Error: %s', e)

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

    # Override SocketServer.UDPServer to add extra parameters
    def __init__(self, server_address, config, logger, RequestHandlerClass):
        self.config = config
        self.logger = logger
        SocketServer.UDPServer.__init__(self, server_address, RequestHandlerClass)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    
    # Override default value
    allow_reuse_address = True

    # Override SocketServer.TCPServer to add extra parameters
    def __init__(self, server_address, config, logger, RequestHandlerClass):
        self.config = config
        self.logger = logger
        SocketServer.TCPServer.__init__(self,server_address,RequestHandlerClass)

def hexdump_table(data, length=16):

    hexdump_lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_line   = ' '.join(["%02X" % ord(b) for b in chunk ] )
        ascii_line = ''.join([b if ord(b) > 31 and ord(b) < 127 else '.' for b in chunk ] )
        hexdump_lines.append("%04X: %-*s %s" % (i, length*3, hex_line, ascii_line ))
    return hexdump_lines

###############################################################################
# Testing code
def test(config):

    print "\t[DNSListener] Testing 'google.com' A record."
    query = DNSRecord(q=DNSQuestion('google.com',getattr(QTYPE,'A')))
    answer_pkt = query.send('localhost', int(config.get('port', 53)))
    answer = DNSRecord.parse(answer_pkt)

    print '-'*80
    print answer
    print '-'*80


def main():
    logging.basicConfig(format='%(asctime)s [%(name)15s] %(message)s', datefmt='%m/%d/%y %I:%M:%S %p', level=logging.DEBUG)
    
    config = {'port': '53', 'protocol': 'UDP', 'dnsresponse': '127.0.0.1', 'nxdomains': 3 }

    listener = DNSListener(config, logging_level = logging.DEBUG)
    listener.start()


    ###########################################################################
    # Run processing
    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    ###########################################################################
    # Run tests
    test(config)

if __name__ == '__main__':
    main()
