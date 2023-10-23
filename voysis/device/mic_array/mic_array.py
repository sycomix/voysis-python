

import sys

import pyaudio

import numpy as np
from voysis.device.mic_array.gcc_phat import gcc_phat
import math
from voysis.device.mic_device import MicDevice


SOUND_SPEED = 343.2

MIC_DISTANCE_6P1 = 0.064
MAX_TDOA_6P1 = MIC_DISTANCE_6P1 / SOUND_SPEED

MIC_DISTANCE_4 = 0.08127
MAX_TDOA_4 = MIC_DISTANCE_4 / SOUND_SPEED


class MicArrayDevice(MicDevice):
    def __init__(self, client):
        super().__init__(self, client)
        for i in range(self.pyaudio_instance.get_device_count()):
            dev = self.pyaudio_instance.get_device_info_by_index(i)
            name = dev['name'].encode('utf-8')
            print(i, name, dev['maxInputChannels'], dev['maxOutputChannels'])
            #if dev['maxInputChannels'] == self.channels:
            if 'ReSpeaker MicArray UAC2.0' in dev['name']:
                print(f'Use {name}')
                self.device_index = i
                break
        if self.device_index is None:
            raise ValueError(f'can not find input device with {self.channels} channel(s)')

    def generate_frames(self):
        self.quit_event.clear()
        while not self.quit_event.is_set():
            if frames := self.queue.get():
                yield np.fromstring(frames, dtype='int16')
            else:
                break

    # def __enter__(self):
    #     self.start()
    #     return self
    #
    # def __exit__(self, type, value, traceback):
    #     if value:
    #         return False
    #     self.stop()

    def get_direction(self, buf):
        best_guess = None
        if self.channels == 8:
            MIC_GROUP_N = 3
            MIC_GROUP = [[1, 4], [2, 5], [3, 6]]

            tau = [0] * MIC_GROUP_N
            theta = [0] * MIC_GROUP_N

            # buf = np.fromstring(buf, dtype='int16')
            for i, v in enumerate(MIC_GROUP):
                tau[i], _ = gcc_phat(buf[v[0]::8], buf[v[1]::8], fs=self.sample_rate, max_tau=MAX_TDOA_6P1, interp=1)
                theta[i] = math.asin(tau[i] / MAX_TDOA_6P1) * 180 / math.pi

            min_index = np.argmin(np.abs(tau))
            if (min_index != 0 and theta[min_index - 1] >= 0) or (min_index == 0 and theta[MIC_GROUP_N - 1] < 0):
                best_guess = (theta[min_index] + 360) % 360
            else:
                best_guess = (180 - theta[min_index])

            best_guess = (best_guess + 120 + min_index * 60) % 360
        elif self.channels == 4:
            MIC_GROUP_N = 2
            MIC_GROUP = [[0, 2], [1, 3]]

            tau = [0] * MIC_GROUP_N
            theta = [0] * MIC_GROUP_N
            for i, v in enumerate(MIC_GROUP):
                tau[i], _ = gcc_phat(buf[v[0]::4], buf[v[1]::4], fs=self.sample_rate, max_tau=MAX_TDOA_4, interp=1)
                theta[i] = math.asin(tau[i] / MAX_TDOA_4) * 180 / math.pi

            if np.abs(theta[0]) < np.abs(theta[1]):
                best_guess = (theta[0] + 360) % 360 if theta[1] > 0 else (180 - theta[0])
            else:
                best_guess = (theta[1] + 360) % 360 if theta[0] < 0 else (180 - theta[1])
                best_guess = (best_guess + 90) % 360


        return best_guess

#
# def test_4mic():
#     import signal
#
#     is_quit = threading.Event()
#
#     def signal_handler(sig, num):
#         is_quit.set()
#         print('Quit')
#
#     signal.signal(signal.SIGINT, signal_handler)
#
#     with MicArray(16000, 4, 16000 / 4)  as mic:
#         for chunk in mic.read_chunks():
#             direction = mic.get_direction(chunk)
#             print(int(direction))
#
#             if is_quit.is_set():
#                 break
#
#
# def test_8mic():
#     import signal
#     #from pixel_ring import pixel_ring
#
#     is_quit = threading.Event()
#
#     def signal_handler(sig, num):
#         is_quit.set()
#         print('Quit')
#
#     signal.signal(signal.SIGINT, signal_handler)
#
#     with MicArray(16000, 8, 16000 / 4)  as mic:
#         for chunk in mic.read_chunks():
#             direction = mic.get_direction(chunk)
#             #pixel_ring.set_direction(direction)
#             print(int(direction))
#
#             if is_quit.is_set():
#                 break
#
#     #pixel_ring.off()
#
# def test_2mic():
#     import signal
#     #from pixel_ring import pixel_ring
#
#     is_quit = threading.Event()
#
#     def signal_handler(sig, num):
#         is_quit.set()
#         print('Quit')
#
#     signal.signal(signal.SIGINT, signal_handler)
#
#     with MicArray(16000, 2, 16000 / 4)  as mic:
#         for chunk in mic.read_chunks():
#             direction = mic.get_direction(chunk)
#             #pixel_ring.set_direction(direction)
#             #print(int(direction))
#             print (len(chunk))
#             print (direction)
#
#             if is_quit.is_set():
#                 break
#
#     #pixel_ring.off()


# if __name__ == '__main__':
#     # test_4mic()
#     test_8mic()
#     #test_2mic()
