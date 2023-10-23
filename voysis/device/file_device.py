import datetime
import sys
import time
import voysis.config as config
from voysis.device.device import Device

if sys.version[0] == '2':
    import Queue as queue
else:
    import queue


class FileDevice(Device):
    def __init__(self, wav_file=None):
        Device.__init__(self)
        self.time_between_chunks = config.get_float(config.GENERAL, 'time_between_chunks', 0.08)
        self._queue = queue.Queue()
        self._last_chunk_time = datetime.datetime.utcfromtimestamp(0)
        self.wav_file = wav_file

    def start_recording(self):
        self._queue.queue.clear()
        self.wav_to_frames()

    def stop_recording(self):
        self._queue.queue.clear()

    def is_recording(self):
        return not(self._queue.empty())

    def generate_frames(self):
        while not self._queue.empty():
            if data := self._queue.get_nowait():
                now = datetime.datetime.utcnow()
                seconds_since_last = (now - self._last_chunk_time).total_seconds()
                if seconds_since_last < self.time_between_chunks:
                    time.sleep(self.time_between_chunks - seconds_since_last)
                self._last_chunk_time = now
                yield data

    def wav_to_frames(self):
        while True:
            if data := self.wav_file.read(self.chunk_size):
                self._queue.put(data)
            else:
                break

    def audio_type(self):
        return 'audio/pcm;bits=16;rate=16000'
