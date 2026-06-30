import numpy as np
import scipy.signal
from pedalboard.io import AudioFile

mp3_path = r"C:\Users\jv05g\OneDrive\Documentos\oCam\Som_2026_04_19_14_05_16_863.mp3"

try:
    print(f"Loading {mp3_path}...")
    with AudioFile(mp3_path) as f:
        sr = f.samplerate
        audio = f.read(f.frames)
        # Convert stereo to mono if needed
        if audio.shape[0] > 1:
            y = np.mean(audio, axis=0)
        else:
            y = audio[0]
            
    print(f"Loaded successfully. Sample rate = {sr}Hz, Duration = {len(y)/sr:.2f}s")
    
    print("Analyzing echo delay...")
    # Analyze middle 2 seconds to avoid silence at start/end
    segment = y[sr:sr*3] if len(y) > sr*3 else y
    
    # Simple autocorrelation
    corr = scipy.signal.correlate(segment, segment, mode='full')
    corr = corr[len(corr)//2:]  # Keep only positive lags
    
    # Find next highest peak (ignore main peak at lag=0)
    min_lag = int(0.005 * sr)  # 5ms
    max_lag = int(0.500 * sr)  # 500ms
    
    peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
    delay_ms = (peak_lag / sr) * 1000.0
    
    print(f"!!! MATH RESULTS !!!")
    print(f"Echo Delay Detected: ~{delay_ms:.2f} milliseconds")
    
    # Match the delay to suspects
    if 20 <= delay_ms <= 45:
        print("Suspect: Audio Engine Python internal buffering (Blocksize latency).")
    elif 46 <= delay_ms <= 120:
        print("Suspect: Windows WASAPI / VB-Cable Mixer routing loop.")
    elif delay_ms < 20:
        print("Suspect: Hardware comb filtering / Full-duplex pass-through.")
    else:
        print("Suspect: Software Playthrough (e.g., Audacity 'Listen' is checked).")
        
except Exception as e:
    print(f"Erro: {e}")
