import numpy as np
import pyaudio
import math
import pigpio
from time import sleep

class PiMuPhi:
    
    sound_format = pyaudio.paFloat32
    chunk = 2048
    start = 0
    slices = 512
    
    min_b = 0.4
    max_b = 14
    
    bass_div = 150
    mid_div  = 80
    treb_div = 240
    
    loop_delay = 0.02
    
    test_on_startup = False

    spec_raw = 0
    spectrum = []

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format = self.sound_format,
            channels = 1, 
            rate = 48000,
            input = True,
            output = False,
            frames_per_buffer = self.chunk)
            
        self.pi = pigpio.pi()
        self.run()
    
    def read_audio(self):
        audio_raw = self.stream.read(self.chunk, exception_on_overflow=False)
        audio = np.fromstring(audio_raw, np.float32)
        return audio

    def fast_fourier_transform(self):
        spec_raw = np.fft.fft(self.spectrum[self.start:self.start + self.slices]) 
        self.spec_proc = list(map(lambda f: np.sqrt(f.real**2 + f.imag**2), spec_raw))

    def get_color(self, b, m, t):
        #base_col = [0.10, 0.15, 0.95]
        base_col = [1.0, 0.0, 0.0]
        return base_col
        
    def normalize_brightness(self, n):
		n = 0 if n < 0 else n
		n = 255 if n > 255 else n
		return n
    
    def get_brightness(self, n):
        n = self.min_b if n < self.min_b else n
        n = self.max_b if n > self.max_b else n
        brightness = 255 * ((n - self.min_b)/(self.max_b - self.min_b))
        return self.normalize_brightness(brightness)
        
    def setcol(self, r, g, b):
		self.pi.set_PWM_dutycycle(23, 255 - r)
		self.pi.set_PWM_dutycycle(24, 255 - g)
		self.pi.set_PWM_dutycycle(25, 255 - b)

    def run(self):
        try:
            if self.test_on_startup:
                print("Welcome to PiMuPhi")
                print("Starting initial test.")
                print("Testing red.")
                self.setcol(255, 0, 0)
                sleep(1.5)
                print("Testing green.")
                self.setcol(0, 255, 0)
                sleep(1.5)
                print("Testing blue.")
                self.setcol(0, 0, 255)
                sleep(1.5)
                print("Testing white.")
                self.setcol(255, 255, 255)
                sleep(1.5)
                for i in range(5):
                    self.setcol(255, 255, 255)
                    sleep(0.08)
                    self.setcol(0,0,0)
                    sleep(0.08)
                print("Testing done, start the music!")
                
            while True:
                self.spectrum = self.read_audio()
                self.fast_fourier_transform()
                
                bass_val = sum(self.spec_proc[ 10:172])/self.bass_div
                mid_val  = sum(self.spec_proc[172:400])/self.mid_div
                treb_val = sum(self.spec_proc[400:512])/self.treb_div
                
                color = self.get_color(bass_val, mid_val, treb_val)
                brightness = self.get_brightness(bass_val)
                
                r_proc = brightness * color[0]
                g_proc = brightness * color[1]
                b_proc = brightness * color[2]
                
                self.setcol(r_proc, g_proc, b_proc)

                print bass_val, mid_val, treb_val
                
                sleep(self.loop_delay)
                

        except KeyboardInterrupt:
            self.pa.close() 

if __name__ == "__main__":
    light_box = PiMuPhi()
    
