"""
    Record a voice query and send to Voysis endpoint
"""

import signal
import threading
import time
import wave

import os
import pyaudio
import six

from voysis.device.mic_array import MicArray

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 16000
WAVE_OUTPUT_FILENAME = "/tmp/{0}_{1}_{2}_output.wav".format(int(time.time()), os.getlogin(), os.getpid())
CHUNK = RATE / 100


def record():
    audio = pyaudio.PyAudio()
    is_quit = threading.Event()
    frames = []

    def signal_handler(sig, num):
        waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        waveFile.setnchannels(CHANNELS)
        waveFile.setsampwidth(audio.get_sample_size(FORMAT))
        waveFile.setframerate(RATE)
        waveFile.writeframes(b''.join(frames))
        #waveFile.writeframes(frames)
        waveFile.close()
        is_quit.set()
        print('Quit')

    signal.signal(signal.SIGINT, signal_handler)

    six.moves.input("Press ENTER to start recording, hit control+c to stop")

    with MicArray(16000, CHANNELS) as mic:
        for chunk in mic.read_chunks():
            # direction = mic.get_direction(chunk)
            # print(int(direction))
            frames.append(chunk.tobytes())
            if is_quit.is_set():
                break
    return WAVE_OUTPUT_FILENAME


if __name__ == '__main__':
    print(record())
