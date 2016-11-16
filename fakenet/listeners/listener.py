import logging
import abc
import time

class FakeNetBaseListener(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, config = {}, logging_level = logging.DEBUG, name = None):
        name = name if name is not None else self.getclassname()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging_level)

        self.config = config
        self.name = name
        self.local_ip = '0.0.0.0'
        self.server = None
        self.server_thread = None

        self.logger.info('Instantiating...')

        self.logger.debug('Initialized with config:')
        for key, value in config.iteritems():
            self.logger.debug('  %10s: %s', key, value)

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
