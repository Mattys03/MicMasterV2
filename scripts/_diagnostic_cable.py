import sounddevice as sd
import numpy as np
import scipy.signal
import time
from core.audio_engine import AudioEngine

def test_cable_recording():
    print("=== INICIANDO TESTE ISOLADO DO CABLE OUTPUT ===")
    engine = AudioEngine()
    
    devices = sd.query_devices()
    apis = sd.query_hostapis()
    
    mic_idx = None
    cable_in_idx = None
    cable_out_idx = None
    
    for i, d in enumerate(devices):
        api = apis[d['hostapi']]['name']
        if 'WASAPI' not in api: continue
        name = d['name'].lower()
        if 'fifine' in name and d['max_input_channels'] > 0:
            mic_idx = i
        if 'cable input' in name and d['max_output_channels'] > 0:
            cable_in_idx = i
        if 'cable output' in name and d['max_input_channels'] > 0:
            cable_out_idx = i

    if None in (mic_idx, cable_in_idx, cable_out_idx):
        print(f"Dispositivos nao encontrados. Mic={mic_idx}, CabIn={cable_in_idx}, CabOut={cable_out_idx}")
        return

    print("Iniciando o MicMaster (Microfone -> Filtros -> Cable Input)...")
    engine.start(mic_idx, cable_in_idx)
    
    print("Gravando EXATAMENTE o que esta saindo no 'CABLE Output' via Python...")
    print(">>> FALE AGORA NO MICROFONE DURANTE 4 SEGUNDOS <<<")
    
    # Record exactly what comes out of CABLE Output
    recording = sd.rec(int(4 * 48000), samplerate=48000, channels=1, device=cable_out_idx, dtype=np.float32)
    sd.wait()
    
    print("Gravacao concluida! Desligando MicMaster...")
    engine.stop()
    
    print("Analisando o áudio capturado matematicamente...")
    rec_1d = recording[:, 0]
    
    corr = scipy.signal.correlate(rec_1d, rec_1d, mode='full')
    corr = corr[len(corr)//2:]
    
    min_lag = int(0.040 * 48000) # 40ms (ignores human voice pitch)
    max_lag = int(0.500 * 48000) # 500ms
    
    peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
    delay_ms = (peak_lag / 48000.0) * 1000.0
    
    peak_amplitude = corr[peak_lag]
    base_amplitude = corr[0]
    
    ratio = peak_amplitude / base_amplitude
    
    print(f"--- RESULTADO MATEMÁTICO DO SINAL REAL DO CABLE ---")
    print(f"Maior pico secundário (Acima de 40ms): delay de ~{delay_ms:.2f} ms")
    print(f"Força do eco detectado: {ratio*100:.2f}% do sinal original")
    
    if ratio > 0.15:
        print("=> ERRO GRAVE: O eco está ocorrendo DENTRO do fluxo principal do Windows/Cable.")
        print("Isso significa que o Windows está alimentando o Cable Input com duas fontes.")
    else:
        print("=> SINAL LIMPO: O 'CABLE Output' não tem NENHUM eco no núcleo do sistema.")
        print("Isso COMPROVA que o Audacity / oCam está gravando o Fifine cru de alguma forma (Ex: Stereo Mix, Multi-Input).")
        
if __name__ == "__main__":
    test_cable_recording()
