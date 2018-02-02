import abc
import six

import voysis.config as config


@six.add_metaclass(abc.ABCMeta)
class Device(object):

    def __init__(self):
        self.chunk_size = config.get_int(config.GENERAL, 'chunk_size', 1024)

    @abc.abstractmethod
    def start_recording(self):
        pass

    @abc.abstractmethod
    def stop_recording(self):
        pass

    @abc.abstractmethod
    def generate_frames(self):
        pass
