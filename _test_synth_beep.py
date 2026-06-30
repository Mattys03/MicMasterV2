import sounddevice as sd
import numpy as np
import scipy.signal
import time

def test_cable_echo():
    print("=== INICIANDO TESTE COM BEEP SINTETICO ===")
    devices = sd.query_devices()
    apis = sd.query_hostapis()
    
    cable_in_idx = None
    cable_out_idx = None
    
    for i, d in enumerate(devices):
        api = apis[d['hostapi']]['name']
        if 'WASAPI' not in api: continue
        name = d['name'].lower()
        if 'cable input' in name and d['max_output_channels'] > 0: cable_in_idx = i
        if 'cable output' in name and d['max_input_channels'] > 0: cable_out_idx = i

    if None in (cable_in_idx, cable_out_idx):
        print("Dispositivos n encontrados.")
        return

    # Generate a pure 440Hz beep of exactly 0.5 seconds
    sr = 48000
    t = np.linspace(0, 0.5, int(0.5 * sr), endpoint=False)
    beep = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # We will write the beep to CABLE INPUT, and simultaneously record from CABLE OUTPUT
    recorded_audio = []
    
    def in_cb(indata, frames, time, status):
        recorded_audio.append(indata[:,0].copy())
        
    in_stream = sd.InputStream(device=cable_out_idx, samplerate=sr, channels=1, blocksize=1024, callback=in_cb)
    in_stream.start()
    
    print("Enviando Beep de 0.5s para o Cable Input...")
    sd.play(beep, samplerate=sr, device=cable_in_idx, blocking=True)
    
    time.sleep(1) # wait for capture
    in_stream.stop()
    in_stream.close()
    
    rec_1d = np.concatenate(recorded_audio)
    
    # Let's count how many distinct "beeps" appear in the recording!
    # A beep has very high energy at 440Hz. We can just use envelope detection.
    envelope = np.abs(rec_1d)
    
    # Find peaks in envelope separated by at least 1000 frames
    peaks, properties = scipy.signal.find_peaks(envelope, height=0.1, distance=sr*0.010)
    
    # To avoid counting every wave of the 440Hz tone, we smooth the envelope
    from scipy.signal import butter, filtfilt
    b, a = butter(1, 10 / (sr / 2), btype='low') # 10Hz lowpass
    smooth_env = filtfilt(b, a, envelope)
    
    peaks, props = scipy.signal.find_peaks(smooth_env, height=0.05, distance=sr*0.2)
    
    print(f"Número de bipes isolados detectados na Gravação do CABLE Output: {len(peaks)}")
    for i, p in enumerate(peaks):
        print(f"   Bipe {i+1} no tempo {p/sr:.3f} segundos")

if __name__ == "__main__":
    test_cable_echo()
