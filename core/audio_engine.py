"""
MicMaster Pro - Audio Engine (Version Final)
"""

import queue
import threading
import time
import numpy as np
import sounddevice as sd
import sys
import os
import gc
import logging
from pedalboard import (
    Compressor,
    Gain,
    HighpassFilter,
    HighShelfFilter,
    Limiter,
    LowpassFilter,
    LowShelfFilter,
    PeakFilter,
    Pedalboard,
    load_plugin,
)

class AudioEngine:
    BLOCK_SIZE = 1024

    def __init__(self):
        self.sample_rate = 48000

        # Load RNNoise VST3
        if getattr(sys, 'frozen', False):
            plugin_path = os.path.join(sys._MEIPASS, "core", "plugins", "rnnoise.vst3", "Contents", "x86_64-win", "rnnoise.vst3")
        else:
            plugin_path = os.path.join(os.path.dirname(__file__), "plugins", "rnnoise.vst3", "Contents", "x86_64-win", "rnnoise.vst3")
            
        try:
            self.rnnoise = load_plugin(plugin_path)
            self.rnnoise.vad_threshold = 0.5
            self.rnnoise.vad_grace_period_10ms_per_unit = 20.0
            self.has_rnnoise = True
        except Exception as e:
            print(f"Failed to load RNNoise: {e}")
            self.rnnoise = None
            self.has_rnnoise = False
        self.hpf = HighpassFilter(cutoff_frequency_hz=100.0)
        self.hpf_2 = HighpassFilter(cutoff_frequency_hz=100.0)
        self.lpf = LowpassFilter(cutoff_frequency_hz=16000.0)
        
        # 5-Band Professional Parametric EQ setup
        self.eq_bass = LowShelfFilter(cutoff_frequency_hz=150.0, gain_db=3.0)
        self.eq_boxy = PeakFilter(cutoff_frequency_hz=350.0, gain_db=-3.0, q=1.0)
        self.eq_presence = PeakFilter(cutoff_frequency_hz=3000.0, gain_db=2.0, q=1.5)
        self.eq_treble = HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=2.0)
        
        self.compressor = Compressor(
            threshold_db=-18.0, ratio=4.0, attack_ms=10.0, release_ms=150.0
        )
        self.limiter = Limiter(threshold_db=-1.0)
        self.output_gain = Gain(gain_db=3.0)

        # --- Automatic Gain Control (AGC) state ---
        self.agc_enabled = True
        self._rms_avg = 0.001
        self._agc_gain = 1.0

        self.bypass_all = False
        self.rnnoise_enabled = True
        self.hpf_enabled = True
        self.lpf_enabled = True
        self.eq_enabled = True
        self.comp_enabled = True
        self.limiter_enabled = True

        self.input_level_db = -60.0
        self.input_peak_db = -60.0
        self.output_level_db = -60.0
        self.output_peak_db = -60.0
        self._peak_decay = 0.92

        self._stream = None
        self._monitor_stream = None
        self._running = False
        self._monitoring = False
        self._board = Pedalboard([])
        self._rebuild_board()

        self._mon_q = queue.Queue(maxsize=15)
        self.latency_ms = 0.0

    @property
    def running(self):
        return self._running

    @property
    def monitoring(self):
        return self._monitoring

    def _rebuild_board(self):
        plugins = []
        if self.rnnoise_enabled and self.has_rnnoise: plugins.append(self.rnnoise)
        if self.hpf_enabled: 
            plugins.append(self.hpf)
            plugins.append(self.hpf_2)
        if self.lpf_enabled: plugins.append(self.lpf)
        if self.eq_enabled:
            plugins.append(self.eq_bass)
            plugins.append(self.eq_boxy)
            plugins.append(self.eq_presence)
            plugins.append(self.eq_treble)
        if self.comp_enabled: plugins.append(self.compressor)
        if self.limiter_enabled: plugins.append(self.limiter)
        plugins.append(self.output_gain)
        self._board = Pedalboard(plugins)

    def toggle_module(self, module_name, enabled):
        setattr(self, f"{module_name}_enabled", enabled)
        self._rebuild_board()

    def _compute_levels(self, audio):
        if audio.size == 0:
            return -60.0, -60.0
        rms = np.sqrt(np.mean(audio ** 2) + 1e-10)
        peak = np.max(np.abs(audio)) + 1e-10
        rms_db = float(20.0 * np.log10(rms))
        peak_db = float(20.0 * np.log10(peak))
        return max(rms_db, -60.0), max(peak_db, -60.0)

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        # 1. Clear output buffer to prevent pass-through echoes
        outdata.fill(0)
        
        # 2. Grab mic input
        audio = indata[:, 0].copy()
        
        # Guard against empty buffers (disconnections, driver glitches)
        if frames == 0 or audio.size == 0:
            return

        try:
            t_start = time.perf_counter()

            # Input metering
            in_rms, in_peak = self._compute_levels(audio)
            self.input_level_db = in_rms
            self.input_peak_db = max(in_peak, self.input_peak_db * self._peak_decay)

            # --- Automatic Gain Control (AGC / Auto-Leveler) ---
            if self.agc_enabled and not self.bypass_all:
                current_rms_float = float(np.sqrt(np.mean(audio ** 2) + 1e-10))
                
                # Active speech threshold: -45 dB (0.0056 RMS)
                if current_rms_float > 0.005:
                    # Smooth tracking using EMA
                    self._rms_avg = self._rms_avg * 0.95 + current_rms_float * 0.05
                    # Target RMS: -18 dB (approx 0.125 float RMS)
                    required_gain = 0.125 / self._rms_avg
                    # Safe boundaries: max boost of +12dB (4.0x) and max cut of -6dB (0.5x)
                    required_gain = np.clip(required_gain, 0.5, 4.0)
                    
                    # Attack (fast compression when loud) vs Release (slow boost when quiet)
                    if required_gain < self._agc_gain:
                        self._agc_gain = self._agc_gain * 0.8 + required_gain * 0.2
                    else:
                        self._agc_gain = self._agc_gain * 0.98 + required_gain * 0.02
                else:
                    # Silence: gently return the gain back to 1.0 (neutral) to prevent background noise swelling!
                    self._agc_gain = self._agc_gain * 0.99 + 1.0 * 0.01
                
                # Apply the smoothed AGC gain factor
                audio *= self._agc_gain

            # 3. Apply professional Pedalboard DSP directly 
            if not self.bypass_all:
                audio_2d = audio.reshape(1, -1)
                audio_processed = self._board.process(audio_2d, self.sample_rate, reset=False)
                audio = audio_processed.reshape(-1)

            # Ensure audio matches expected frame count (prevents shape mismatch)
            if audio.size == 0:
                return
            if audio.size < frames:
                audio = np.pad(audio, (0, frames - audio.size), mode='constant')
            elif audio.size > frames:
                audio = audio[:frames]
                
            np.clip(audio, -1.0, 1.0, out=audio)

            # Output metering
            out_rms, out_peak = self._compute_levels(audio)
            self.output_level_db = out_rms
            self.output_peak_db = max(out_peak, self.output_peak_db * self._peak_decay)

            # 4. Write exactly the valid frames to output
            outdata[:frames, 0] = audio[:frames]

            # 5. Save a copy for the monitoring thread 
            if self._monitoring:
                try:
                    self._mon_q.put_nowait(audio.copy())
                except queue.Full:
                    try:
                        self._mon_q.get_nowait()
                        self._mon_q.put_nowait(audio.copy())
                    except: pass

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self.latency_ms = self.latency_ms * 0.9 + elapsed_ms * 0.1
        except Exception as e:
            logging.error(f"Erro no audio callback: {e}", exc_info=True)

    def _monitor_callback(self, outdata, frames, time_info, status):
        try:
            data = self._mon_q.get_nowait()
            n = min(frames, len(data))
            for c in range(outdata.shape[1]):
                outdata[:n, c] = data[:n]
            if n < frames:
                for c in range(outdata.shape[1]):
                    outdata[n:, c].fill(0)
        except queue.Empty:
            outdata.fill(0)

    def get_devices(self):
        devices = sd.query_devices()
        apis = sd.query_hostapis()
        inputs = []
        outputs = []
        for i, dev in enumerate(devices):
            api_name = apis[dev["hostapi"]]["name"]
            if "WASAPI" not in api_name: continue
            name = dev['name']
            if dev["max_input_channels"] > 0:
                inputs.append((i, name, dev["max_input_channels"]))
            if dev["max_output_channels"] > 0:
                outputs.append((i, name, dev["max_output_channels"]))
        return inputs, outputs

    def start(self, input_device_idx, output_device_idx):
        if self._running: return
        self._rebuild_board()

        out_info = sd.query_devices(output_device_idx)
        self.sample_rate = int(out_info['default_samplerate'])

        try:
            # Optimize Python GC: freeze tracking to slash GC pauses in the real-time audio thread
            gc.freeze()
            self._stream = sd.Stream(
                device=(input_device_idx, output_device_idx),
                samplerate=self.sample_rate,
                blocksize=self.BLOCK_SIZE,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback,
                latency='high'  # High is safest against dropouts
            )
            self._stream.start()
            self._running = True
        except Exception as e:
            self._running = False
            raise RuntimeError(f"Falha ao iniciar: {e}") from e

    def stop(self):
        if not self._running: return
        self.stop_monitoring()
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        except: pass
        finally:
            self._stream = None
            self._running = False
            self.input_level_db = -60.0
            self.input_peak_db = -60.0
            self.output_level_db = -60.0
            self.output_peak_db = -60.0
            self.latency_ms = 0.0

    def start_monitoring(self, device_idx):
        if self._monitoring: return
        
        while not self._mon_q.empty():
            try: self._mon_q.get_nowait()
            except: break
            
        # Buffer de elasticidade para evitar craquelados
        silence = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        for _ in range(4):
            self._mon_q.put(silence)
        try:
            dev = sd.query_devices(device_idx)
            ch = min(2, max(1, dev['max_output_channels']))
            self._monitor_stream = sd.OutputStream(
                device=device_idx,
                samplerate=self.sample_rate,
                blocksize=self.BLOCK_SIZE,
                channels=ch,
                dtype=np.float32,
                callback=self._monitor_callback,
                latency='high',
            )
            self._monitor_stream.start()
            self._monitoring = True
        except Exception:
            self._monitoring = False

    def stop_monitoring(self):
        if not self._monitoring: return
        try:
            if self._monitor_stream:
                self._monitor_stream.stop()
                self._monitor_stream.close()
        except: pass
        finally:
            self._monitor_stream = None
            self._monitoring = False

    def apply_preset(self, preset):
        self.rnnoise_enabled = preset.get("rnnoise_enabled", True)
        if self.has_rnnoise:
            self.rnnoise.vad_threshold = preset.get("rnnoise_vad_threshold", 0.5)
            self.rnnoise.vad_grace_period_10ms_per_unit = preset.get("rnnoise_grace_period", 20.0)
        self.hpf_enabled = preset.get("hpf_enabled", True)
        hpf_cut = preset.get("hpf_cutoff", 100.0)
        self.hpf.cutoff_frequency_hz = hpf_cut
        self.hpf_2.cutoff_frequency_hz = hpf_cut
        
        self.lpf_enabled = preset.get("lpf_enabled", True)
        self.lpf.cutoff_frequency_hz = preset.get("lpf_cutoff", 16000.0)
        
        self.eq_enabled = preset.get("eq_enabled", True)
        self.eq_bass.gain_db = preset.get("eq_bass_gain", 3.0)
        self.eq_boxy.gain_db = preset.get("eq_boxy_gain", -3.0)
        self.eq_presence.gain_db = preset.get("eq_presence_gain", 2.0)
        self.eq_treble.gain_db = preset.get("eq_treble_gain", 2.0)
        
        self.comp_enabled = preset.get("comp_enabled", True)
        self.compressor.threshold_db = preset.get("comp_threshold", -18.0)
        self.compressor.ratio = preset.get("comp_ratio", 4.0)
        self.compressor.attack_ms = preset.get("comp_attack", 10.0)
        self.compressor.release_ms = preset.get("comp_release", 150.0)
        self.limiter_enabled = preset.get("limiter_enabled", True)
        self.limiter.threshold_db = preset.get("limiter_threshold", -1.0)
        self.output_gain.gain_db = preset.get("gain_db", 3.0)
        
        self.agc_enabled = preset.get("agc_enabled", True)
        self._rebuild_board()

    def get_current_settings(self):
        return {
            "rnnoise_enabled": self.rnnoise_enabled,
            "rnnoise_vad_threshold": self.rnnoise.vad_threshold if self.has_rnnoise else 0.5,
            "rnnoise_grace_period": self.rnnoise.vad_grace_period_10ms_per_unit if self.has_rnnoise else 20.0,
            "hpf_enabled": self.hpf_enabled,
            "hpf_cutoff": self.hpf.cutoff_frequency_hz,
            "lpf_enabled": self.lpf_enabled,
            "lpf_cutoff": self.lpf.cutoff_frequency_hz,
            "eq_enabled": self.eq_enabled,
            "eq_bass_gain": self.eq_bass.gain_db,
            "eq_boxy_gain": self.eq_boxy.gain_db,
            "eq_presence_gain": self.eq_presence.gain_db,
            "eq_treble_gain": self.eq_treble.gain_db,
            "comp_enabled": self.comp_enabled,
            "comp_threshold": self.compressor.threshold_db,
            "comp_ratio": self.compressor.ratio,
            "comp_attack": self.compressor.attack_ms,
            "comp_release": self.compressor.release_ms,
            "limiter_enabled": self.limiter_enabled,
            "limiter_threshold": self.limiter.threshold_db,
            "gain_db": self.output_gain.gain_db,
            "agc_enabled": self.agc_enabled,
        }
