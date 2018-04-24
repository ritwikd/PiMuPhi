import numpy as np
import pyaudio
import math
import pigpio
from time import sleep, time

class PiMuPhi:
    
    color_change_enabled = True
    intensity_change_enabled = True
    
    current_index = 0
    change_threshold = 50
    
    sound_format = pyaudio.paFloat32
    chunk = 256
    start = 0
    slices = 100
    
    min_b = 1.5
    max_b = 13
    
    
    bb_vals = [0] * 128
    avg_beat_bass = 0
    
    rti_vals = [0] * 28
    avg_rti = 0
    
    rmi_vals = [0] * 28
    avg_rmi = 0
    
    i_vals = [0] * 10
    avg_intensity = 0
    
    m_vals = [0] * 10
    avg_lvl_mid = 0
    
    t_vals = [0] * 10
    avg_lvl_treble = 0
    
    dc_vals = [0] * 25
    avg_intensity_slow = 0
    
    loop_delay = 0.0
    
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
        self.spec_proc = list(map(lambda f: np.sqrt(f.real ** 2 + f.imag**2), spec_raw))

    def get_color(self, t, i):
        
        base_colors = [
            [0.05, 0.05, 0.95],
            [0.70, 0.05, 0.85],
            [0.89, 0.05, 0.05]
        ]
        
        base_col = [0, 0, 1]
        
        base_col[0] += (self.avg_rti) * 5.0
        
        base_col[1] += (self.avg_rmi) * 3.0
        
        base_col[2] -= ((self.avg_rmi + self.avg_rti)) * 4.0
        
        return self.normalize_color(base_col)
        
        #return self.normalize_color(base_colors[self.current_index])
    
    def normalize_color(self, col):
        col[0] = 0 if col[0] < 0 else col[0]
        col[0] = 1.0 if col[0] > 1 else col[0]
        
        col[1] = 0 if col[1] < 0 else col[1]
        col[1] = 1.0 if col[1] > 1 else col[1]
        
        col[2] = 0 if col[2] < 0 else col[2]
        col[2] = 1.0 if col[2] > 1 else col[2]
        
        return col
    
    def get_running_avg(self, bb, intensity, t, m):
        for i in range(len(self.i_vals) - 1):
            self.i_vals[i] = self.i_vals[i + 1]
        self.i_vals[-1] = intensity
        self.avg_intensity_fast = sum(self.i_vals)/len(self.i_vals)
        
        for i in range(len(self.dc_vals) - 1):
            self.dc_vals[i] = self.dc_vals[i + 1]
        self.dc_vals[-1] = intensity
        self.avg_intensity_slow = sum(self.dc_vals)/len(self.dc_vals)
        
        for i in range(len(self.bb_vals) - 1):
            self.bb_vals[i] = self.bb_vals[i + 1]
        self.bb_vals[-1] = bb
        self.avg_beat_bass = sum(self.bb_vals)/len(self.bb_vals)
        
        for i in range(len(self.t_vals) - 1):
            self.t_vals[i] = self.t_vals[i + 1]
        self.t_vals[-1] = t
        self.avg_lvl_treble = sum(self.t_vals)/len(self.t_vals)
        
        for i in range(len(self.m_vals) - 1):
            self.m_vals[i] = self.m_vals[i + 1]
        self.m_vals[-1] = m
        self.avg_lvl_mid = sum(self.m_vals)/len(self.m_vals)
        
        for i in range(len(self.rti_vals) - 1):
            self.rti_vals[i] = self.rti_vals[i + 1]
        self.rti_vals[-1] = t/i
        self.avg_rti = sum(self.rti_vals)/len(self.rti_vals)
        
        for i in range(len(self.rmi_vals) - 1):
            self.rmi_vals[i] = self.rmi_vals[i + 1]
        self.rmi_vals[-1] = m/i
        self.avg_rmi = sum(self.rmi_vals)/len(self.rmi_vals)
        
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
                
                beat_bass = self.spec_proc[0] + self.spec_proc[1]
                
                intensity = round(sum(self.spec_proc[:25])/20) + 0.001
                midrange = round(sum(self.spec_proc[25:70])/45) + 0.001
                treble = round(sum(self.spec_proc[70:])/30) + 0.001
                
                self.get_running_avg(beat_bass, intensity, treble, midrange)
                self.b_max = self.avg_intensity_slow * 1.5
                
                if self.avg_beat_bass < self.change_threshold/2:
                    self.change_threshold -= 5
                
                if beat_bass > self.change_threshold:
                    self.current_index += 1
                    self.current_index = 0 if self.current_index > 2 else self.current_index
                
                self.change_threshold = self.avg_beat_bass * 2.0
                
                color = self.get_color(treble, intensity)
                color = color if self.color_change_enabled else [1,1,1] 
                
                brightness = self.get_brightness(self.avg_intensity_fast)
                brightness = brightness if self.intensity_change_enabled else 255
                
                r_proc = brightness * color[0]
                g_proc = brightness * color[1]
                b_proc = brightness * color[2]
                #if (beat_bass > self.change_threshold):
                 #   print(beat_bass, self.change_threshold)
                
                self.setcol(r_proc, g_proc, b_proc)
                
                sleep(self.loop_delay)
                
                

        except KeyboardInterrupt:
            print("Exiting PiMuPhi.")
            self.setcol(0,0,0)
            self.stream.close()
            self.pa.terminate() 

if __name__ == "__main__":
    light_box = PiMuPhi()

