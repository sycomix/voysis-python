from voysis.device.device import Device

class FileDevice(Device):
    def __init__(self, wav_file=None):
        Device.__init__(self)
        self.wav_file = wav_file

    def start_recording(self):
        self.frames = []
        self.wav_to_frames()

    def stop_recording(self):
        self.frames = []

    def generate_frames(self):
        return iter(self.frames)

    def wav_to_frames(self):
        while True:
            data = self.wav_file.read(self.chunk_size)
            if not data:
                break
            self.frames.append(data)
