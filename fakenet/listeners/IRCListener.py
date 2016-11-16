import logging
from irc.server import *
import irc.client
import listener
import threading

class FN_IRCClient(irc.server.IRCClient):
    def _handle_incoming(self):
        """Only difference here is that we want to see the line before it gets
        handled by Jaraco's IRC implementation.
        """
        try:
            data = self.request.recv(1024)
        except Exception:
            raise self.Disconnect()

        if not data:
            raise self.Disconnect()

        self.buffer.feed(data)
        for line in self.buffer:
            line = line.decode('utf-8')
            self.server.logger.info('Received: {0}'.format(line))
            self._handle_line(line)

    def _send(self, msg):
        """Jaraco's IRC implementation (https://github.com/jaraco/irc) doesn't
        handle broken pipe exceptions sent by socket.send() as of this writing
        (git commit hash 01f1bf4). This results in unwanted exception output in
        the event that a client disconnects before the server can reply to a
        command that normally warrants a reply (e.g. PING). Fixing that in
        Jaraco's IRC project doesn't fix the installed base of stale distros /
        code out there that people may be using for malware analysis, so we'll
        incorporate a fix here. Logging will be different here as well, as we
        will need to use self.server.logger instead of irc.server's global log
        variable.
        """

        self.server.logger.debug('Sending to %s: %s', self.client_ident(), msg)
        try:
            self.request.send(msg.encode('utf-8') + b'\r\n')
        except socket.error:
            raise self.Disconnect()


class IRCListener(listener.FakeNetBaseListener):
    def __init__(self, config = {}, logging_level = logging.DEBUG, name = None):
        listener.FakeNetBaseListener.__init__(self, config, logging_level, name)
        logging.getLogger('irc.server').setLevel(logging.CRITICAL+1)

    def start(self):
        listener.FakeNetBaseListener.start(self)
        self.server = irc.server.IRCServer(('127.0.0.1', 6667), FN_IRCClient)
        self.server.logger = self.logger
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

    def stop(self):
        listener.FakeNetBaseListener.stop(self)
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


if __name__ == '__main__':
    listener.run_standalone(IRCListener)
