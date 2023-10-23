"""
    Record a voice query and send to Voysis endpoint
"""

import pyaudio
import time
import os
import wave


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
WAVE_OUTPUT_FILENAME = "/tmp/{0}_{1}_{2}_output.wav".format(int(time.time()), os.getlogin(), os.getpid())


def capture(stream):
    while True:
        yield stream.read(CHUNK)


def record():
    print("Ready to capture your voice query")

    audio = pyaudio.PyAudio()

    input("Press ENTER to start recording")

    # start Recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    print("Recording...hit ctrl-c to stop recording")

    frames = []

    try:
        frames.extend(iter(capture(stream)))
    except KeyboardInterrupt:
        print("Stopped recording")
        stream.stop_stream()
        stream.close()
        audio.terminate()

    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

    return WAVE_OUTPUT_FILENAME

