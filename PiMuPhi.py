import numpy as np
import pyaudio
import math
import pigpio
from time import sleep

class PiMuPhi:
    
    sound_format = pyaudio.paFloat32
    chunk = 1024
    start = 0
    slices = 512
    
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

    def get_permutation(self, b, m, t):
        if(b > t and t > m):
            return 0
        if(b > m and m > t):
            return 1
        if(t > b and b > m):
            return 2
        if(t > m and m > b):
            return 3
        if(m > b and b > t):
            return 4
        if(m > t and t > b):
            return 5
        
    def clampval(self, n):
		if n < 0:
			return 0
		if n > 255:
			return 255
		return n
    
    def bright_conv(self, n):
        if n < 1:
            n = 1
        if n > 13:
            n = 13
        brightness = 255 * ((n - 1)/12)
        return brightness
    
    def mult_conv(self, n):
        if n < 1:
            n = 1
        if n > 13:
            n = 13
        multiplier = (n - 1)/12
        return multiplier
        
    def setcol(self, r, g, b):
		self.pi.set_PWM_dutycycle(23, 255 - self.clampval(r))
		self.pi.set_PWM_dutycycle(24, 255 - self.clampval(g))
		self.pi.set_PWM_dutycycle(25, 255 - self.clampval(b))

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
                
            while True :
                self.spectrum = self.read_audio()
                self.fast_fourier_transform()
                
                bass_val = sum(self.spec_proc[10:172])/162
                mid_val = sum(self.spec_proc[172:400])/228
                treb_val = sum(self.spec_proc[400:])/112
                
                p_val = self.bright_conv(bass_val)
                
                r_mult = self.mult_conv(treb_val)
                g_mult = self.mult_conv(mid_val)
                b_mult = self.mult_conv(bass_val)
                
                self.setcol(
                    p_val * r_mult , 
                    p_val * g_mult, 
                    p_val * b_mult)

                print(self.get_permutation(bass_val, mid_val, treb_val))

                    
                #print bass_val, mid_val, treb_val
                

        except KeyboardInterrupt:
            self.pa.close() 

if __name__ == "__main__":
    light_box = PiMuPhi()
    
