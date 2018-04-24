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
    
    min_b = 3
    max_b = 13
    
    test_on_startup = False

    spec_raw = 0
    spectrum = []
    
    testspec = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0}
    
    multipliers = {
        0: (0, 0.1, 1),
        1: (1, 0, 0.0),
        2: (0, 0.7, 0.08),
        3: (1, 1, 1),
        4: (1, 0, 0.0),
        5: (1, 0, 0.0)
    }

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
        #self.testspec[perm_val] += 1
        if(b > t and t > m):
            mult = self.multipliers[0]
            delta = (self.max_b - (b - t))/self.max_b 
            return (mult[0] + delta * 0.2, mult[1], mult[2])
        elif(b > m and m > t):
            mult = self.multipliers[1]
            delta = (self.max_b - (b - m))/self.max_b
            return (mult[0], mult[1], mult[2] + delta * 0.3)
        elif(t > b and b > m):
            mult = self.multipliers[2]
            delta = (self.max_b - (t - b))/self.max_b
            return (mult[0] + delta * 0.3, mult[1], mult[2] + delta * 0.3)
        elif(t > m and m > b):
            return self.multipliers[3]
        elif(m > b and b > t):
            return self.multipliers[4]
        elif(m > t and t > b):
            return self.multipliers[5]
        else:
            return self.multipliers[3]
        
    def clampval(self, n):
		n = 0 if n < 0 else n
		n = 255 if n > 255 else n
		return n
    
    def bright_conv(self, n):
        n = self.min_b if n < self.min_b else n
        n = self.max_b if n > self.max_b else n
        brightness = 255 * ((n - self.min_b)/(self.max_b - self.min_b))
        return brightness
        
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
                
                bass_val = sum(self.spec_proc[10:172])/150
                mid_val = sum(self.spec_proc[172:400])/80
                treb_val = sum(self.spec_proc[400:])/260
                
                mult = self.get_permutation(bass_val, mid_val, treb_val)
                
                p_val = self.bright_conv(bass_val)
                
                r_proc = p_val * mult[0]
                g_proc = p_val * mult[1]
                b_proc = p_val * mult[2]
                
                self.setcol(r_proc, g_proc, b_proc)

                print bass_val, mid_val, treb_val
                
                sleep(0.001)
                

        except KeyboardInterrupt:
            print self.testspec
            self.pa.close() 

if __name__ == "__main__":
    light_box = PiMuPhi()
    
