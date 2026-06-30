"""
Diagnostic: Check if Windows 'Listen to this device' is on for any recording device.
Also checks VB-Cable sample rates.
"""
import sounddevice as sd
import subprocess

print("=== SAMPLE RATES COMPARISON ===")
devices = sd.query_devices()
apis = sd.query_hostapis()
for i, d in enumerate(devices):
    api = apis[d['hostapi']]['name']
    if 'WASAPI' not in api:
        continue
    sr = int(d['default_samplerate'])
    name = d['name']
    tipo = 'IN' if d['max_input_channels'] > 0 else 'OUT'
    if d['max_input_channels'] > 0 and d['max_output_channels'] > 0:
        tipo = 'IN+OUT'
    elif d['max_output_channels'] > 0:
        tipo = 'OUT'
    print(f"  [{i}] {name} ({tipo}) -> {sr}Hz")

print()
print("=== CHECKING 'LISTEN TO THIS DEVICE' (Registry) ===")
import winreg

try:
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(key, i)
            props_path = key_path + "\\" + subkey_name + "\\Properties"
            try:
                props = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, props_path)
                # Device friendly name
                try:
                    name_val = winreg.QueryValueEx(props, "{a45c254e-df1c-4efd-8020-67d146a850e0},2")
                    dev_name = name_val[0]
                except:
                    dev_name = subkey_name[:20]
                # Check for Listen enabled: {24dbb0fc-...},1 contains monitor settings
                try:
                    listen_val = winreg.QueryValueEx(props, "{24dbb0fc-a5c2-4f59-b8fa-f0c6c19b9ce0},1")
                    data = listen_val[0]
                    if isinstance(data, bytes) and len(data) >= 1:
                        is_listening = data[0] != 0
                        if is_listening:
                            print(f"  *** ALERTA: '{dev_name}' tem 'Ouvir Dispositivo' ATIVADO! ***")
                        else:
                            print(f"  OK: '{dev_name}' - Listen desativado")
                except FileNotFoundError:
                    print(f"  OK: '{dev_name}' - sem config de Listen")
                winreg.CloseKey(props)
            except:
                pass
            i += 1
        except OSError:
            break
    winreg.CloseKey(key)
except Exception as e:
    print(f"  Nao foi possivel verificar: {e}")

print()
print("=== SIMPLE PASSTHROUGH TEST ===")
print("Testing direct mic -> cable passthrough for 1 second...")
import numpy as np
import time

# Find fifine mic and CABLE Input
mic_idx = None
cable_idx = None
for i, d in enumerate(devices):
    api = apis[d['hostapi']]['name']
    if 'WASAPI' not in api:
        continue
    if 'fifine' in d['name'].lower() and d['max_input_channels'] > 0:
        mic_idx = i
    if 'cable input' in d['name'].lower() and d['max_output_channels'] > 0:
        cable_idx = i

if mic_idx and cable_idx:
    print(f"  Mic: [{mic_idx}] {devices[mic_idx]['name']}")
    print(f"  Out: [{cable_idx}] {devices[cable_idx]['name']}")
    
    out_sr = int(devices[cable_idx]['default_samplerate'])
    print(f"  Sample rate: {out_sr}Hz")
    
    frame_count = [0]
    
    buf = [None]
    evt = [False]
    
    def in_cb(indata, frames, ti, status):
        if status:
            print(f"  INPUT STATUS: {status}")
        buf[0] = indata[:, 0].copy()
        evt[0] = True
        frame_count[0] += 1
    
    def out_cb(outdata, frames, ti, status):
        if status:
            print(f"  OUTPUT STATUS: {status}")
        outdata[:] = 0
        if evt[0] and buf[0] is not None:
            n = min(frames, len(buf[0]))
            outdata[:n, 0] = buf[0][:n]
            evt[0] = False
    
    ins = sd.InputStream(device=mic_idx, samplerate=out_sr, blocksize=1024, channels=1, dtype=np.float32, callback=in_cb)
    outs = sd.OutputStream(device=cable_idx, samplerate=out_sr, blocksize=1024, channels=1, dtype=np.float32, callback=out_cb)
    ins.start()
    outs.start()
    time.sleep(1.0)
    ins.stop()
    outs.stop()
    ins.close()
    outs.close()
    print(f"  Processed {frame_count[0]} frames in 1 second. No errors = good!")
else:
    print(f"  Could not find devices. mic={mic_idx} cable={cable_idx}")

print()
print("=== DONE ===")
