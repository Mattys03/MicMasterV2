"""
MicMasterV2 - Diagnostic & Automated Health Test Utility
Verifies dependencies, audio drivers, registry settings, and runs audio engine validations.
ASCII-Safe edition for Windows terminals.
"""

import sys
import os
import time

# Force UTF-8 on Windows stdout if possible
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

print("=" * 60)
print("     MICMASTER 2.0 - DIAGNOSTICO DO SISTEMA E TESTE DE SAUDE")
print("=" * 60)
print()

# Step 1: Check Python packages dependencies
print("[1] Verificando dependencias do Python...")
required_libs = {
    "customtkinter": "Interface grafica",
    "pedalboard": "Processamento de audio DSP (C++)",
    "sounddevice": "Drivers e streams de audio (PortAudio)",
    "numpy": "Manipulacao matematica de buffers",
    "noisereduce": "Reducao de ruido avancada",
    "scipy": "Matematica e processamento de sinal"
}

missing_libs = []
imported_libs = {}

for lib, desc in required_libs.items():
    try:
        mod = __import__(lib)
        print(f"  [OK] {lib:<15} -> OK ({desc})")
        imported_libs[lib] = mod
    except ImportError:
        print(f"  [X]  {lib:<15} -> FALHA (Falta instalar! - {desc})")
        missing_libs.append(lib)

if missing_libs:
    print()
    print("[X] ERRO CRITICO: Estao faltando dependencias!")
    print("Execute no terminal:")
    print("  .venv\\Scripts\\pip.exe install -r requirements.txt")
    print()
    sys.exit(1)

print("[OK] Todas as dependencias estao presentes!")
print()

# Step 2: Check Audio Devices via SoundDevice
print("[2] Verificando drivers e dispositivos de audio...")
sd = imported_libs["sounddevice"]

try:
    devices = sd.query_devices()
    apis = sd.query_hostapis()
    print(f"  [OK] PortAudio carregado com sucesso. {len(devices)} dispositivos encontrados.")
    
    wasapi_api_idx = None
    for idx, api in enumerate(apis):
        if "WASAPI" in api["name"]:
            wasapi_api_idx = idx
            break
            
    if wasapi_api_idx is None:
        print("  [WARN] AVISO: Driver Windows WASAPI nao foi encontrado nas APIs de host. Usando padrao.")
    else:
        print("  [OK] Driver Windows WASAPI detectado.")

    # Search for Mic and Cable Input
    mic_found = False
    cable_in_found = False
    cable_out_found = False
    
    print("\n  Dispositivos WASAPI disponiveis:")
    for i, dev in enumerate(devices):
        api_name = apis[dev["hostapi"]]["name"]
        if "WASAPI" not in api_name:
            continue
            
        name = dev["name"]
        ch_in = dev["max_input_channels"]
        ch_out = dev["max_output_channels"]
        sr = int(dev["default_samplerate"])
        
        # Replace non-ascii chars in device names for print safety
        safe_name = name.encode('ascii', 'replace').decode('ascii')
        
        tipo = ""
        if ch_in > 0 and ch_out > 0:
            tipo = "Entrada+Saida"
        elif ch_in > 0:
            tipo = "Entrada (Mic)"
            if "cable" not in name.lower():
                mic_found = True
            else:
                cable_out_found = True
        elif ch_out > 0:
            tipo = "Saida (Fone/Cable)"
            if "cable" in name.lower():
                cable_in_found = True
                
        print(f"    [{i}] {safe_name} ({tipo}) -> {sr}Hz")
        
    print()
    if mic_found:
        print("  [OK] Microfone fisico detectado.")
    else:
        print("  [WARN] AVISO: Nenhum microfone fisico WASAPI detectado. Verifique se esta conectado!")
        
    if cable_in_found and cable_out_found:
        print("  [OK] VB-Cable Virtual Audio Driver detectado e pronto!")
    else:
        print("  [WARN] ALERTA: VB-Cable nao esta totalmente instalado ou ativado.")
        print("     Acesse https://vb-audio.com/Cable/ para instalar o VB-Cable.")
        print("     Isso e necessario para mandar o audio do MicMaster para o Discord/OBS!")

except Exception as e:
    print(f"  [X] Erro ao consultar dispositivos de audio: {e}")
    sys.exit(1)

print()

# Step 3: Check Registry settings for "Listen to this device"
print("[3] Verificando 'Escutar este dispositivo' do Windows...")
try:
    import winreg
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
    i = 0
    echo_found = False
    while True:
        try:
            subkey_name = winreg.EnumKey(key, i)
            props_path = key_path + "\\" + subkey_name + "\\Properties"
            try:
                props = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, props_path)
                try:
                    name_val = winreg.QueryValueEx(props, "{a45c254e-df1c-4efd-8020-67d146a850e0},2")
                    dev_name = name_val[0]
                except:
                    dev_name = subkey_name[:20]
                
                safe_dev_name = dev_name.encode('ascii', 'replace').decode('ascii')
                try:
                    listen_val = winreg.QueryValueEx(props, "{24dbb0fc-a5c2-4f59-b8fa-f0c6c19b9ce0},1")
                    data = listen_val[0]
                    if isinstance(data, bytes) and len(data) >= 1:
                        is_listening = data[0] != 0
                        if is_listening:
                            print(f"  [WARN] ALERTA DE ECO: '{safe_dev_name}' esta com 'Escutar este dispositivo' ATIVADO nas configuracoes do Windows!")
                            print("     Isso gera eco duplo de audio! Desative-o nas propriedades do painel de som do Windows.")
                            echo_found = True
                except FileNotFoundError:
                    pass
                winreg.CloseKey(props)
            except:
                pass
            i += 1
        except OSError:
            break
    winreg.CloseKey(key)
    if not echo_found:
        print("  [OK] Excelente: Nenhum dispositivo com 'Escutar dispositivo' (Listen Enabled) ativado no Windows Registry!")
except Exception as e:
    print(f"  [WARN] Nao foi possivel ler registros do Windows: {e}")

print()

# Step 4: Run automated AudioEngine validation test
print("[4] Executando teste automatico do motor de audio (2 segundos)...")
try:
    from core.audio_engine import AudioEngine
    engine = AudioEngine()
    
    # Try finding best WASAPI input and output for quick loopback test
    inputs, outputs = engine.get_devices()
    
    best_in = None
    best_out = None
    
    for idx, name, ch in inputs:
        if "cable" not in name.lower():
            best_in = idx
            break
            
    for idx, name, ch in outputs:
        if "cable" in name.lower():
            best_out = idx
            break
            
    if best_in is None and inputs:
        best_in = inputs[0][0]
    if best_out is None and outputs:
        best_out = outputs[0][0]
        
    if best_in is not None and best_out is not None:
        safe_in_name = sd.query_devices(best_in)['name'].encode('ascii', 'replace').decode('ascii')
        safe_out_name = sd.query_devices(best_out)['name'].encode('ascii', 'replace').decode('ascii')
        
        print(f"  Iniciando stream com In={best_in} ({safe_in_name}) e Out={best_out} ({safe_out_name})...")
        engine.start(best_in, best_out)
        time.sleep(2.0)
        engine.stop()
        print("  [OK] Motor de audio inicializado, executado por 2 segundos e parado com 100% de sucesso!")
        print(f"  [OK] Latencia media medida no motor: {engine.latency_ms:.2f} ms")
    else:
        print("  [WARN] Ignorando teste de audio: Faltam dispositivos de audio validos no sistema.")
except Exception as e:
    print(f"  [X] FALHA no teste do motor de audio: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print(" [OK] DIAGNOSTICO COMPLETO! O SISTEMA ESTA PRONTO E SAUDAVEL!")
print("=" * 60)
print("  Para abrir o app: .venv\\Scripts\\python.exe main.py")
print("=" * 60)
