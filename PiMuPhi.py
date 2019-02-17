import numpy as np
import pyaudio
import math
import pigpio
from time import sleep, time
import os

class PiMuPhi:
    
    color_change_enabled = True
    intensity_change_enabled = True
    test_on_startup = False
    
    current_index = 0
    change_threshold = 50
    
    sound_format = pyaudio.paFloat32
    chunk = 128
    start = 0
    slices = 100
    
    min_b = 50 #original: 1.5
    max_b = 2500
    
    
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
    
    dc_vals = [0] * 10
    avg_intensity_slow = 0
    
    sorted_spec_vals = [0] * 5
    sorted_spec_avg = 0
    
    total_averages = 0
    
    loop_delay = 0.00

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
        
        base_col = [[1, 0, 0], [0, 1.0, 0], [0, 0.0, 1]]
        
        final_col = [0,0,0]
        
        treb_fac = (self.avg_lvl_treble/ self.total_averages) * 0.75
        mid_fac = (self.avg_lvl_mid / self.total_averages) * 0.6
        bass_fac = (self.avg_intensity_fast / self.total_averages) * 0.75
        
        #~ if mid_fac > treb_fac * 0.25 or mid_fac > bass_fac * 0.25:
            #~ mid_fac *= 2.5
            #~ treb_fac *= 0.25
            #~ bass_fac *= 0.25
        #~ else:
            #~ if treb_fac > bass_fac * 1.0:
                #~ bass_fac *= 0.15
                #~ mid_fac *= 1.5
            #~ elif bass_fac > treb_fac * 0.8:
                #~ treb_fac *= 0.6
                #~ mid_fac *= 1.25
                
        if treb_fac > bass_fac * 0.5:
            treb_fac *= 1.25
            mid_fac *= 1.5
            bass_fac *= 0.1
        
        
        final_col  = [sum(x) for x in zip(final_col, [e * treb_fac for e in base_col[0]])]
        final_col  = [sum(x) for x in zip(final_col, [e * mid_fac for e in base_col[1]])]
        final_col  = [sum(x) for x in zip(final_col, [e * bass_fac for e in base_col[2]])]
        
        return self.normalize_color(final_col)
        
        #return self.normalize_color(base_colors[self.current_index])
    
    def normalize_color(self, col):
        col[0] = 0 if col[0] < 0 else col[0]
        col[0] = 1.0 if col[0] > 1 else col[0]
        
        col[1] = 0 if col[1] < 0 else col[1]
        col[1] = 1.0 if col[1] > 1 else col[1]
        
        col[2] = 0 if col[2] < 0 else col[2]
        col[2] = 1.0 if col[2] > 1 else col[2]
        
        return col
    
    def get_running_avg(self, bb, intensity, t, m, sorted_spec):
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

        for i in range(len(self.sorted_spec_vals) - 1):
            self.sorted_spec_vals[i] = self.sorted_spec_vals[i + 1]
        self.sorted_spec_vals[-1] = sorted_spec
        self.sorted_spec_avg = sum(self.sorted_spec_vals)/len(self.sorted_spec_vals)
        
        self.total_averages = self.avg_lvl_treble + self.avg_lvl_mid + self.avg_intensity_fast
        
    def normalize_brightness(self, n):
        n = 0 if n < 0 else n
        n = 255 if n > 255 else n
        return n
    
    def get_brightness(self, n):
        n = self.min_b if n < self.min_b else n
        n = self.max_b if n > self.max_b else n
        brightness = 255 * ((n - self.min_b)/(self.max_b - self.min_b))
        #if brightness > 155: brightness *=0.65
        return self.normalize_brightness(brightness)
        
    def setcol(self, r, g, b):
        self.pi.set_PWM_dutycycle(23, 255 - r)
        self.pi.set_PWM_dutycycle(24, 255 - g)
        self.pi.set_PWM_dutycycle(25, 255 - b)

    def run(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Welcome to PiMuPhi")
            if self.test_on_startup:
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
                
                sorted_spec = sorted(self.spec_proc)
                sss = sum(sorted_spec[50:])          
                beat_bass = self.spec_proc[0] + self.spec_proc[1]
                os.system('cls' if os.name == 'nt' else 'clear')
                whole_spec = sum(self.spec_proc) + 0.001
                if whole_spec < 0.1: whole_spec = 0.1
                whole_spec = (math.log(whole_spec, 1.5) - 10) * 10
                whole_spec = 0.1 if whole_spec < 0.1 else whole_spec
                #print(whole_spec)
                
                #print('\t'.join(list(map(lambda q: str(round(q)), self.spec_proc[:20]))))
                intensity = round(sum(self.spec_proc[:25])/20) + 0.001
                midrange = round(sum(self.spec_proc[25:70])/45) + 0.001
                treble = round(sum(self.spec_proc[70:])/30) + 0.001
                
                self.get_running_avg(beat_bass, intensity, treble, midrange, sss)
                
                if self.avg_beat_bass < self.change_threshold/2:
                    self.change_threshold -= 5
                
                if beat_bass > self.change_threshold:
                    self.current_index += 1
                    self.current_index = 0 if self.current_index > 2 else self.current_index
                
                self.change_threshold = self.avg_beat_bass * 2.0
                
                color = self.get_color(treble, intensity)
                color = color if self.color_change_enabled else [1,1,1] 
                
                brightness = self.get_brightness(self.sorted_spec_avg)
                brightness = brightness if self.intensity_change_enabled else 255
                
                r_proc = brightness * color[0]
                g_proc = brightness * color[1]
                b_proc = brightness * color[2]
                    
                if r_proc < 0: r_proc = 0
                if g_proc < 0: g_proc = 0
                if b_proc < 0: b_proc = 0
                
                self.setcol(r_proc, g_proc, b_proc)
                
                sleep(self.loop_delay)
                
                

        except KeyboardInterrupt:
            print("Exiting PiMuPhi.")
            self.setcol(0,0,0)
            self.stream.close()
            self.pa.terminate() 

if __name__ == "__main__":
    light_box = PiMuPhi()

