import logging
import abc
import time

# Twisted's reactor must be called once and only once, so to facilitate
# listeners that may use Twisted, FakeNet will check for and evaluate the
# attribute needs_twisted_reactor in each listener class and, if true, will
# import the appropriate modules and start reactor.
class TwistedMixIn(object):
    needs_twisted_reactor = True

class FakeNetBaseListener(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, config = {}, name = None, logging_level = logging.DEBUG):
        name = name if name is not None else self.getclassname()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging_level)

        self.config = config
        self.name = name
        self.local_ip = '0.0.0.0'
        self.server = None
        self.started = False

        self.logger.debug('Initialized with config:')
        for key, value in config.iteritems():
            self.logger.debug('  %10s: %s', key, value)

    def getportno(self, default): return int(self.config.get('port', default))

    def getclassname(self):
        name = type(self).__name__
        if name is None or name == 'instance':
            name = self.__class__.__name__
        return name

    @abc.abstractmethod
    def start(self):
        self.logger.info('Starting...')

    @abc.abstractmethod
    def stop(self):
        self.logger.info('Stopping...')

    def config_present(self, opt): return opt.lower() in self.config.keys()
    def config_true(self, opt): return 'yes' == self.config[opt.lower()].lower()
    def config_false(self, opt): return 'false' == self.config[opt.lower()].lower()
    def config_true_safe(self, opt):
        return self.config_true(opt) if self.config_present(opt.lower()) else False
    def config_false_safe(self, opt): return not self.config_true_safe(opt)


def run_standalone(class_, config = {}):
    logging.basicConfig(format='%(asctime)s [%(name)15s] %(message)s', datefmt='%m/%d/%y %I:%M:%S %p', level=logging.DEBUG)
    listener = class_(config)
    listener.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    listener.stop()
