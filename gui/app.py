"""
MicMaster Pro — Main Application Window

Professional dark-themed GUI for real-time microphone processing.
"""

import sys
import logging
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import sounddevice as sd

import os
from core.audio_engine import AudioEngine
from core.preset_manager import list_presets, load_preset, save_preset, delete_preset, load_config, save_config
from gui.device_selector import DeviceSelector
from gui.meter_widget import StereoMeter

# Setup logging for startup debugging (writes to local project dir + APPDATA + stdout)
_local_log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'micmaster.log')
_appdata_log_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), 'MicMaster Pro')
os.makedirs(_appdata_log_dir, exist_ok=True)
_appdata_log_file = os.path.join(_appdata_log_dir, 'startup.log')

# Configure logging with local file, AppData file, and console stream handlers
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

# Clear existing handlers to prevent duplicate entries
if logger.hasHandlers():
    logger.handlers.clear()

# File handler 1: local folder
try:
    fh_local = logging.FileHandler(_local_log_file, encoding='utf-8')
    fh_local.setFormatter(formatter)
    logger.addHandler(fh_local)
except Exception:
    pass

# File handler 2: AppData
try:
    fh_appdata = logging.FileHandler(_appdata_log_file, encoding='utf-8')
    fh_appdata.setFormatter(formatter)
    logger.addHandler(fh_appdata)
except Exception:
    pass

# Console handler (prints to standard output)
try:
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
except Exception:
    pass

logging.info(f"MicMaster Pro iniciando. Local log: {_local_log_file}")


# --- Theme Constants ---
BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_CARD_HOVER = "#1c2333"
BORDER = "#30363d"
ACCENT = "#00d4aa"
ACCENT_DIM = "#007a63"
TEXT = "#e6edf3"
TEXT_DIM = "#8b949e"
TEXT_DARK = "#484f58"
GREEN = "#3fb950"
RED = "#f85149"
YELLOW = "#d29922"


class ProcessingModule(ctk.CTkFrame):
    """A collapsible processing module with enable toggle and parameter sliders."""

    def __init__(
        self,
        master,
        title: str,
        module_key: str,
        enabled: bool = True,
        params: list = None,
        on_toggle=None,
        on_param_change=None,
        accent_color=ACCENT,
        **kwargs,
    ):
        super().__init__(master, fg_color=BG_CARD, corner_radius=8, **kwargs)

        self._module_key = module_key
        self._on_toggle = on_toggle
        self._on_param_change = on_param_change
        self._sliders = {}
        self._value_labels = {}

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=36)
        header.pack(fill="x", padx=12, pady=(10, 4))

        self._indicator = ctk.CTkLabel(
            header, text="●", font=("Segoe UI", 10),
            text_color=GREEN if enabled else TEXT_DARK, width=16,
        )
        self._indicator.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            header, text=title, font=("Segoe UI", 12, "bold"),
            text_color=TEXT, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        self._switch_var = ctk.BooleanVar(value=enabled)
        self._switch = ctk.CTkSwitch(
            header,
            text="",
            variable=self._switch_var,
            command=self._handle_toggle,
            width=40,
            height=20,
            switch_width=36,
            switch_height=18,
            fg_color=TEXT_DARK,
            progress_color=accent_color,
            button_color=TEXT,
            button_hover_color="#ffffff",
        )
        self._switch.pack(side="right")

        # Params container
        self._params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._params_frame.pack(fill="x", padx=12, pady=(0, 10))

        if params:
            for p in params:
                self._add_slider(p)

    def _handle_toggle(self):
        enabled = self._switch_var.get()
        color = GREEN if enabled else TEXT_DARK
        self._indicator.configure(text_color=color)
        if self._on_toggle:
            self._on_toggle(self._module_key, enabled)

    def _add_slider(self, param: dict):
        row = ctk.CTkFrame(self._params_frame, fg_color="transparent", height=28)
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row, text=param["label"], font=("Segoe UI", 10),
            text_color=TEXT_DIM, width=80, anchor="w",
        ).pack(side="left")

        value_label = ctk.CTkLabel(
            row, text=self._format_value(param),
            font=("JetBrains Mono", 10), text_color=ACCENT,
            width=70, anchor="e",
        )
        value_label.pack(side="right", padx=(4, 0))

        slider = ctk.CTkSlider(
            row,
            from_=param["min"],
            to=param["max"],
            number_of_steps=param.get("steps", 100),
            command=lambda val, p=param, lbl=value_label: self._slider_changed(val, p, lbl),
            width=160,
            height=14,
            fg_color=BG_DARK,
            progress_color=ACCENT_DIM,
            button_color=ACCENT,
            button_hover_color="#33ffd6",
        )
        slider.set(param["default"])
        slider.pack(side="right", fill="x", expand=True, padx=4)

        self._sliders[param["key"]] = slider
        self._value_labels[param["key"]] = value_label

    def _format_value(self, param: dict, value=None) -> str:
        val = value if value is not None else param["default"]
        suffix = param.get("suffix", "")
        fmt = param.get("format", ".1f")
        if param.get("ratio_display"):
            return f"{val:{fmt}}:1"
        return f"{val:{fmt}} {suffix}".strip()

    def _slider_changed(self, value, param, label):
        label.configure(text=self._format_value(param, value))
        if self._on_param_change:
            self._on_param_change(self._module_key, param["key"], value)

    def set_values(self, values: dict):
        for key, val in values.items():
            if key in self._sliders:
                self._sliders[key].set(val)

    def set_enabled(self, enabled: bool):
        self._switch_var.set(enabled)
        self._handle_toggle()


class MicMasterApp(ctk.CTk):
    """Main application window."""

    def __init__(self, is_startup=False):
        super().__init__()

        ctk.set_appearance_mode("dark")
        self.is_startup = is_startup
        self._startup_retry_count = 0
        self._startup_max_retries = 8
        # Delays in ms: 2s, 3s, 5s, 8s, 10s, 15s, 20s, 30s
        self._startup_retry_delays = [2000, 3000, 5000, 8000, 10000, 15000, 20000, 30000]

        logging.info(f"MicMaster Pro starting (startup_mode={is_startup})")

        self.title("MicMaster Pro")
        self.geometry("720x740")
        self.minsize(680, 700)
        self.configure(fg_color=BG_DARK)

        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'MicMaster.ico')
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'MicMaster.ico')
            self.iconbitmap(default=icon_path)
        except Exception:
            pass

        self.engine = AudioEngine()

        self._build_ui()
        self._load_devices()
        self._load_presets()
        self._load_app_config()

        self._meter_job = None
        self._start_meter_updates()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Note: auto-start is handled inside _load_app_config() which is called above

    def _build_ui(self):
        # ═══ HEADER ═══
        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=16, fill="y")

        ctk.CTkLabel(
            title_frame, text="🎙️ MICMASTER PRO",
            font=("Segoe UI", 16, "bold"), text_color=ACCENT,
        ).pack(side="left", pady=12)

        ctk.CTkLabel(
            title_frame, text="  v1.0",
            font=("Segoe UI", 10), text_color=TEXT_DARK,
        ).pack(side="left", pady=12)

        # ═══ PRESET ROW IN HEADER ═══
        preset_frame = ctk.CTkFrame(header, fg_color="transparent")
        preset_frame.pack(side="right", padx=16, fill="y")

        ctk.CTkLabel(
            preset_frame, text="Preset:", font=("Segoe UI", 10),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(0, 6), pady=12)

        self._preset_var = ctk.StringVar(value="Voz Divina (Auto)")
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            variable=self._preset_var,
            values=["Voz Divina (Auto)", "YouTube / Podcast"],
            command=self._on_preset_change,
            width=180, height=28,
            font=("Segoe UI", 10),
            fg_color="#161b22",
            button_color="#21262d",
            button_hover_color="#30363d",
            dropdown_fg_color="#161b22",
            dropdown_hover_color="#1c2333",
            text_color=TEXT,
            dropdown_text_color=TEXT,
        )
        self.preset_menu.pack(side="left", padx=(0, 4), pady=12)

        self.save_preset_btn = ctk.CTkButton(
            preset_frame, text="Salvar", command=self._save_current_preset,
            width=50, height=28, font=("Segoe UI", 10, "bold"),
            fg_color="#161b22", hover_color="#30363d",
            text_color=TEXT,
        )
        self.save_preset_btn.pack(side="left", padx=(4, 0), pady=12)

        self.delete_preset_btn = ctk.CTkButton(
            preset_frame, text="Deletar", command=self._delete_current_preset,
            width=50, height=28, font=("Segoe UI", 10, "bold"),
            fg_color="#161b22", hover_color="#30363d",
            text_color="#f85149",
        )
        self.delete_preset_btn.pack(side="left", padx=(4, 0), pady=12)

        # ═══ DEVICE SELECTION BAR ═══
        device_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        device_bar.pack(fill="x", pady=(1, 0))

        device_inner = ctk.CTkFrame(device_bar, fg_color="transparent")
        device_inner.pack(fill="both", expand=True, padx=16, pady=8)

        top_row = ctk.CTkFrame(device_inner, fg_color="transparent")
        top_row.pack(fill="x")

        self.input_selector = DeviceSelector(
            top_row, label="Entrada:", devices=[], on_change=None
        )
        self.input_selector.pack(side="left", fill="x", expand=True, padx=(0, 8))

        arrow = ctk.CTkLabel(
            top_row, text="→", font=("Segoe UI", 16, "bold"),
            text_color=ACCENT, width=24,
        )
        arrow.pack(side="left", padx=4)

        self.output_selector = DeviceSelector(
            top_row, label="Enviar para:", devices=[], on_change=None
        )
        self.output_selector.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Output Hint
        hint_row = ctk.CTkFrame(device_inner, fg_color="transparent")
        hint_row.pack(fill="x", pady=(2, 6))
        
        ctk.CTkLabel(
            hint_row, text="DICA: Coloque 'CABLE Input' acima se for enviar para o OBS/Discord. Se colocar seu Fone, terá duplo áudio!",
            font=("Segoe UI", 9, "bold"), text_color=YELLOW, anchor="w",
        ).pack(side="left", padx=(0, 0))

        # Controls row
        ctrl_row = ctk.CTkFrame(device_inner, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(6, 0))

        self.engine_var = ctk.BooleanVar(value=False)
        self.engine_switch = ctk.CTkSwitch(
            ctrl_row, text="Ativar Microfone", variable=self.engine_var,
            command=self._toggle_processing, font=("Segoe UI", 12, "bold"),
            text_color=TEXT, button_color=ACCENT, progress_color=ACCENT,
        )
        self.engine_switch.pack(side="left")

        # Bypass Switch
        self.bypass_var = ctk.BooleanVar(value=False)
        self.bypass_switch = ctk.CTkSwitch(
            ctrl_row, text="Desativar Efeitos", variable=self.bypass_var,
            command=self._on_bypass_toggle, font=("Segoe UI", 10),
            text_color=TEXT_DIM, button_hover_color="#ffffff",
        )
        self.bypass_switch.pack(side="left", padx=(16, 0))

        # Monitor Switch (hear your own processed voice)
        self.monitor_var = ctk.BooleanVar(value=False)
        self.monitor_switch = ctk.CTkSwitch(
            ctrl_row, text="\U0001f3a7 Ouvir Minha Voz", variable=self.monitor_var,
            command=self._on_monitor_toggle, font=("Segoe UI", 10),
            text_color=TEXT_DIM, button_hover_color="#ffffff",
        )
        self.monitor_switch.pack(side="left", padx=(16, 0))

        # Preserve auto-start checkbox logic
        self.startup_var = ctk.BooleanVar(value=False)
        self.startup_checkbox = ctk.CTkCheckBox(
            ctrl_row, text="Ligar c/ PC", variable=self.startup_var,
            command=self._on_startup_toggle, font=("Segoe UI", 10),
            text_color=TEXT_DIM, width=80,
        )
        self.startup_checkbox.pack(side="left", padx=(16, 0))

        # Cleaned up preset area

        # ═══ MAIN CONTENT ═══
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        # Left: VU Meters
        meter_frame = ctk.CTkFrame(content, fg_color=BG_CARD, corner_radius=8, width=110)
        meter_frame.pack(side="left", fill="y", padx=(0, 8))
        meter_frame.pack_propagate(False)

        ctk.CTkLabel(
            meter_frame, text="LEVELS", font=("Segoe UI", 9, "bold"),
            text_color=TEXT_DARK,
        ).pack(pady=(10, 4))

        self.meters = StereoMeter(meter_frame)
        self.meters.pack(padx=6, pady=(0, 8))

        # Level numbers
        self._in_level_label = ctk.CTkLabel(
            meter_frame, text="-∞ dB", font=("JetBrains Mono", 9),
            text_color=TEXT_DIM,
        )
        self._in_level_label.pack()

        self._out_level_label = ctk.CTkLabel(
            meter_frame, text="-∞ dB", font=("JetBrains Mono", 9),
            text_color=TEXT_DIM,
        )
        self._out_level_label.pack(pady=(2, 8))

        # Right: Processing modules (scrollable)
        modules_scroll = ctk.CTkScrollableFrame(
            content, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#21262d",
            scrollbar_button_hover_color="#30363d",
        )
        modules_scroll.pack(side="left", fill="both", expand=True)

        # --- MODULE: AI Noise Suppressor ---
        self.rnnoise_module = ProcessingModule(
            modules_scroll, title="IA: REMOÇÃO DE RUÍDO", module_key="rnnoise",
            enabled=True, on_toggle=self._on_module_toggle,
            on_param_change=self._on_param_change,
            params=[
                {"key": "rnnoise_vad_threshold", "label": "Sensibilidade", "min": 0.0, "max": 1.0, "default": 0.5, "format": ".2f", "steps": 100},
                {"key": "rnnoise_grace_period", "label": "Suavidade", "min": 0.0, "max": 100.0, "default": 20.0, "suffix": "ms", "steps": 100},
            ],
        )
        self.rnnoise_module.pack(fill="x", pady=(0, 6))

        # --- MODULE: Cortes (Filtros) ---
        self.cuts_module = ProcessingModule(
            modules_scroll, title="CORTES (ANTI-BATIDA E CHIADO)", module_key="hpf",
            enabled=True, on_toggle=self._on_module_toggle,
            on_param_change=self._on_param_change,
            params=[
                {"key": "hpf_cutoff", "label": "Anti-Batida (Rumble)", "min": 20, "max": 200, "default": 100, "suffix": "Hz", "steps": 90},
                {"key": "lpf_cutoff", "label": "Corte de Chiado", "min": 4000, "max": 20000, "default": 16000, "suffix": "Hz", "steps": 80, "format": ".0f"},
            ],
        )
        self.cuts_module.pack(fill="x", pady=(0, 6))

        # --- MODULE: Equalizador ---
        self.eq_module = ProcessingModule(
            modules_scroll, title="EQUALIZADOR (RÁDIO FM)", module_key="eq",
            enabled=True, on_toggle=self._on_module_toggle,
            on_param_change=self._on_param_change,
            accent_color="#238636",
            params=[
                {"key": "eq_bass_gain", "label": "Peso (Graves)", "min": -10, "max": 10, "default": 3, "suffix": "dB", "steps": 40},
                {"key": "eq_treble_gain", "label": "Brilho (Agudos)", "min": -10, "max": 10, "default": 2, "suffix": "dB", "steps": 40},
            ],
        )
        self.eq_module.pack(fill="x", pady=(0, 6))

        # --- MODULE: Compressor ---
        self.comp_module = ProcessingModule(
            modules_scroll, title="COMPRESSOR", module_key="comp",
            enabled=True, on_toggle=self._on_module_toggle,
            on_param_change=self._on_param_change,
            accent_color="#d29922",
            params=[
                {"key": "comp_threshold", "label": "Threshold", "min": -60, "max": 0, "default": -18, "suffix": "dB", "steps": 120},
                {"key": "comp_ratio", "label": "Ratio", "min": 1, "max": 20, "default": 4, "ratio_display": True, "steps": 38},
                {"key": "comp_attack", "label": "Attack", "min": 0.1, "max": 100, "default": 10, "suffix": "ms", "steps": 100},
                {"key": "comp_release", "label": "Release", "min": 10, "max": 1000, "default": 150, "suffix": "ms", "steps": 99},
            ],
        )
        self.comp_module.pack(fill="x", pady=(0, 6))

        # --- MODULE: Limiter ---
        self.limiter_module = ProcessingModule(
            modules_scroll, title="LIMITER", module_key="limiter",
            enabled=True, on_toggle=self._on_module_toggle,
            on_param_change=self._on_param_change,
            accent_color="#f85149",
            params=[
                {"key": "limiter_threshold", "label": "Ceiling", "min": -20, "max": 0, "default": -1, "suffix": "dB", "steps": 40},
            ],
        )
        self.limiter_module.pack(fill="x", pady=(0, 6))

        # --- MODULE: Output Gain ---
        gain_frame = ctk.CTkFrame(modules_scroll, fg_color=BG_CARD, corner_radius=8)
        gain_frame.pack(fill="x", pady=(0, 6))

        gain_header = ctk.CTkFrame(gain_frame, fg_color="transparent", height=36)
        gain_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            gain_header, text="●", font=("Segoe UI", 10),
            text_color=GREEN, width=16,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            gain_header, text="OUTPUT GAIN", font=("Segoe UI", 12, "bold"),
            text_color=TEXT, anchor="w",
        ).pack(side="left")

        gain_body = ctk.CTkFrame(gain_frame, fg_color="transparent")
        gain_body.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            gain_body, text="Gain", font=("Segoe UI", 10),
            text_color=TEXT_DIM, width=80, anchor="w",
        ).pack(side="left")

        self._gain_val_label = ctk.CTkLabel(
            gain_body, text="+3.0 dB",
            font=("JetBrains Mono", 10), text_color=ACCENT,
            width=70, anchor="e",
        )
        self._gain_val_label.pack(side="right")

        self._gain_slider = ctk.CTkSlider(
            gain_body, from_=-12, to=24, number_of_steps=72,
            command=self._on_gain_change,
            height=14, fg_color=BG_DARK,
            progress_color=ACCENT_DIM, button_color=ACCENT,
            button_hover_color="#33ffd6",
        )
        self._gain_slider.set(3.0)
        self._gain_slider.pack(side="right", fill="x", expand=True, padx=4)

        # ═══ STATUS BAR ═══
        self.status_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=32)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        status_inner = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        status_inner.pack(fill="both", expand=True, padx=12)

        self._status_dot = ctk.CTkLabel(
            status_inner, text="●", font=("Segoe UI", 10),
            text_color=TEXT_DARK, width=16,
        )
        self._status_dot.pack(side="left")

        self._status_text = ctk.CTkLabel(
            status_inner, text="Parado",
            font=("Segoe UI", 10), text_color=TEXT_DIM,
        )
        self._status_text.pack(side="left", padx=(4, 16))

        self._latency_label = ctk.CTkLabel(
            status_inner, text="Latência: — ms",
            font=("JetBrains Mono", 9), text_color=TEXT_DARK,
        )
        self._latency_label.pack(side="left", padx=(0, 16))

        kill_btn = ctk.CTkButton(
            status_inner, text="Desligar e Fechar", width=100, height=20,
            font=("Segoe UI", 9), fg_color="#da3633", hover_color="#8b1c1c",
            command=self._destroy_completely
        )
        kill_btn.pack(side="right")

    # ----- Device Management -----

    def _load_devices(self):
        inputs, outputs = self.engine.get_devices()
        
        # Store for config matching
        self._device_inputs = inputs
        self._device_outputs = outputs
        
        self.input_selector.update_devices(inputs, is_input=True)
        self.output_selector.update_devices(outputs, is_input=False)
        
        # Handle select event to save config
        self.input_selector.on_change = lambda idx: self._save_app_config()
        self.output_selector.on_change = lambda idx: self._save_app_config()

    # ----- App Config & Boot -----

    def _load_app_config(self):
        self._config = load_config()
        
        # Restore devices
        in_name = self._config.get("in_name")
        if in_name:
            self.input_selector.set_by_raw_name(in_name)
                    
        out_name = self._config.get("out_name")
        if out_name:
            self.output_selector.set_by_raw_name(out_name)

        # Restore auto-startup checkbox state
        try:
            startup_script = os.path.join(
                os.environ['APPDATA'], 
                r'Microsoft\Windows\Start Menu\Programs\Startup\MicMaster_Pro_Startup.vbs'
            )
            self.startup_var.set(os.path.exists(startup_script))
        except:
            pass
            
        # Restore bypass and monitoring states
        if self._config.get("bypass_active"):
            self.bypass_var.set(True)
            self._on_bypass_toggle()
            
        if self._config.get("monitor_active"):
            self.monitor_var.set(True)
            # Will evaluate properly during auto_start if engine hits.

        # Restore state
        last_state = self._config.get("last_state")
        preset_name = self._config.get("preset_name")
        
        if last_state and isinstance(last_state, dict) and "gain_db" in last_state:
            self._apply_preset_to_ui(last_state)
            self.engine.apply_preset(last_state)
            if preset_name:
                self._preset_var.set(preset_name)
        elif preset_name:
            self._on_preset_change(preset_name)
        else:
            self._apply_default_preset()
            
        # IMPORTANT: auto-start processing with restored devices
        should_start = self._config.get("engine_active") or self.is_startup
        if should_start and self._config.get("in_name"):
            if self.is_startup:
                # In startup mode, always try to start (that's the whole point of boot startup)
                self.after(3000, self._startup_retry_audio)
            else:
                self.after(600, self._auto_start_processing)

    def _save_app_config(self):
        in_name = self.input_selector.get_selected_raw_name()
        out_name = self.output_selector.get_selected_raw_name()
        preset_name = self._preset_var.get()
        
        config = {
            "in_name": in_name,
            "out_name": out_name,
            "preset_name": preset_name,
            "engine_active": self.engine_var.get(),
            "bypass_active": self.bypass_var.get(),
            "monitor_active": self.monitor_var.get(),
            "last_state": self.engine.get_current_settings()
        }
        save_config(config)

    def _on_startup_toggle(self):
        enable = self.startup_var.get()
        self._delay_save_config()
        try:
            startup_script = os.path.join(
                os.environ['APPDATA'], 
                r'Microsoft\Windows\Start Menu\Programs\Startup\MicMaster_Pro_Startup.vbs'
            )
            if enable:
                is_frozen = getattr(sys, 'frozen', False)
                
                if is_frozen:
                    # Running as PyInstaller .exe — just call the exe directly
                    exe_path = sys.executable
                    vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
                    vbs_content += f'WshShell.Run chr(34) & "{exe_path}" & chr(34) & " --startup", 0\n'
                    vbs_content += 'Set WshShell = Nothing\n'
                else:
                    # Running as Python script — use venv pythonw
                    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    venv_pythonw = os.path.join(project_dir, '.venv', 'Scripts', 'pythonw.exe')
                    
                    # Fallback to system pythonw if venv doesn't exist
                    if not os.path.exists(venv_pythonw):
                        venv_pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
                    
                    main_path = os.path.join(project_dir, 'main.py')
                    
                    vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
                    vbs_content += f'WshShell.CurrentDirectory = "{project_dir}"\n'
                    vbs_content += f'WshShell.Run chr(34) & "{venv_pythonw}" & chr(34) & " " & chr(34) & "{main_path}" & chr(34) & " --startup", 0\n'
                    vbs_content += 'Set WshShell = Nothing\n'
                
                with open(startup_script, "w", encoding="ansi") as f:
                    f.write(vbs_content)
            else:
                if os.path.exists(startup_script):
                    os.remove(startup_script)
        except Exception as e:
            messagebox.showerror("Erro de Permissão", f"Não foi possível modificar a pasta Startup do Windows: {e}")

    def _on_bypass_toggle(self):
        self.engine.bypass_all = self.bypass_var.get()
        if self.engine.bypass_all:
            self.bypass_switch.configure(text_color=YELLOW)
        else:
            self.bypass_switch.configure(text_color=TEXT_DIM)
        self._delay_save_config()

    def _on_monitor_toggle(self):
        if self.monitor_var.get():
            if not self.engine.running:
                self.monitor_var.set(False)
                messagebox.showwarning("MicMaster Pro", "Ative o microfone primeiro!")
                return
            
            monitor_idx = self._find_monitor_device()
            if monitor_idx is not None:
                self.engine.start_monitoring(monitor_idx)
                if self.engine.monitoring:
                    self.monitor_switch.configure(text_color=GREEN)
                else:
                    self.monitor_var.set(False)
                    messagebox.showwarning("Erro", "Não foi possível abrir o fone.")
            else:
                self.monitor_var.set(False)
                messagebox.showwarning("Aviso", "Nenhum fone/caixa de som encontrado.")
        else:
            self.engine.stop_monitoring()
            self.monitor_switch.configure(text_color=TEXT_DIM)
        self._delay_save_config()

    def _find_monitor_device(self):
        """Find the best WASAPI output for headphone monitoring."""
        _, outputs = self.engine.get_devices()
        
        # Phase 1: Look for headphones/speakers (not cable, not NVIDIA monitors)
        priority_keywords = ['alto-falante', 'headphone', 'fone', 'speaker', 'realtek', 'fifine']
        skip_keywords = ['cable', 'virtual', 'nvidia']
        
        for idx, name, channels in outputs:
            name_lower = name.lower()
            if any(skip in name_lower for skip in skip_keywords):
                continue
            if any(kw in name_lower for kw in priority_keywords):
                return idx
        
        # Phase 2: Any non-cable, non-nvidia device
        for idx, name, channels in outputs:
            name_lower = name.lower()
            if any(skip in name_lower for skip in skip_keywords):
                continue
            return idx
        
        # Phase 3: Windows default output
        try:
            default = sd.query_devices(kind='output')
            if default:
                return default.get('index')
        except Exception:
            pass
        return None

    # ----- Presets -----

    def _load_presets(self):
        self._presets = list_presets()
        names = [p.get("name", p.get("_filename", "?")) for p in self._presets]
        if names:
            self.preset_menu.configure(values=names)

    def _apply_default_preset(self):
        preset_data = load_preset("divine_voice_auto")
        if not preset_data:
            preset_data = load_preset("youtube_podcast")
        if preset_data:
            self._apply_preset_to_ui(preset_data)
            self.engine.apply_preset(preset_data)
            self._preset_var.set(preset_data.get("name", "Voz Divina (Auto)"))

    def _on_preset_change(self, name: str):
        for p in self._presets:
            if p.get("name") == name:
                self._apply_preset_to_ui(p)
                self.engine.apply_preset(p)
                self._preset_var.set(name)
                self._save_app_config()
                break

    def _apply_preset_to_ui(self, preset: dict):
        self.rnnoise_module.set_enabled(preset.get("rnnoise_enabled", True))
        self.rnnoise_module.set_values({
            "rnnoise_vad_threshold": preset.get("rnnoise_vad_threshold", 0.5),
            "rnnoise_grace_period": preset.get("rnnoise_grace_period", 20.0),
        })

        self.cuts_module.set_enabled(preset.get("hpf_enabled", True))
        self.cuts_module.set_values({
            "hpf_cutoff": preset.get("hpf_cutoff", 100),
            "lpf_cutoff": preset.get("lpf_cutoff", 16000)
        })

        self.eq_module.set_enabled(preset.get("eq_enabled", True))
        self.eq_module.set_values({
            "eq_bass_gain": preset.get("eq_bass_gain", 3.0),
            "eq_treble_gain": preset.get("eq_treble_gain", 2.0)
        })

        self.comp_module.set_enabled(preset.get("comp_enabled", True))
        self.comp_module.set_values({
            "comp_threshold": preset.get("comp_threshold", -18),
            "comp_ratio": preset.get("comp_ratio", 4),
            "comp_attack": preset.get("comp_attack", 10),
            "comp_release": preset.get("comp_release", 150),
        })

        self.limiter_module.set_enabled(preset.get("limiter_enabled", True))
        self.limiter_module.set_values({
            "limiter_threshold": preset.get("limiter_threshold", -1),
        })

        self._gain_slider.set(preset.get("gain_db", 3))
        self._on_gain_change(preset.get("gain_db", 3))

    def _save_current_preset(self):
        name = simpledialog.askstring(
            "Salvar Preset", "Nome do preset:",
            parent=self,
        )
        if not name:
            return
        settings = self.engine.get_current_settings()
        save_preset(name, settings)
        self._load_presets()
        self._preset_var.set(name)

    def _delete_current_preset(self):
        current = self._preset_var.get()
        # Find if it is custom
        target = next((p for p in self._presets if p.get("name") == current), None)
        if not target:
            return
        if not target.get("_custom"):
            messagebox.showwarning("Aviso", "Você não pode deletar presets de fábrica.")
            return
        if messagebox.askyesno("Deletar Preset", f"Tem certeza que deseja deletar o preset '{current}'?"):
            if delete_preset(target["_filename"]):
                self._load_presets()
                self._apply_default_preset()
            else:
                messagebox.showerror("Erro", "Erro ao tentar deletar o preset.")

    # ----- Module Callbacks -----

    def _on_module_toggle(self, module_key: str, enabled: bool):
        self.engine.toggle_module(module_key, enabled)
        self._delay_save_config()

    def _on_param_change(self, module_key: str, param_key: str, value: float):
        engine = self.engine
        
        def set_rnnoise_param(attr, val):
            if engine.has_rnnoise:
                setattr(engine.rnnoise, attr, val)
                
        param_map = {
            "rnnoise_vad_threshold": lambda v: set_rnnoise_param("vad_threshold", v),
            "rnnoise_grace_period": lambda v: set_rnnoise_param("vad_grace_period_10ms_per_unit", v),
            "hpf_cutoff": lambda v: [setattr(engine.hpf, "cutoff_frequency_hz", v), setattr(engine.hpf_2, "cutoff_frequency_hz", v)],
            "lpf_cutoff": lambda v: setattr(engine.lpf, "cutoff_frequency_hz", v),
            "eq_bass_gain": lambda v: setattr(engine.eq_bass, "gain_db", v),
            "eq_treble_gain": lambda v: setattr(engine.eq_treble, "gain_db", v),
            "comp_threshold": lambda v: setattr(engine.compressor, "threshold_db", v),
            "comp_ratio": lambda v: setattr(engine.compressor, "ratio", v),
            "comp_attack": lambda v: setattr(engine.compressor, "attack_ms", v),
            "comp_release": lambda v: setattr(engine.compressor, "release_ms", v),
            "limiter_threshold": lambda v: setattr(engine.limiter, "threshold_db", v),
        }
        handler = param_map.get(param_key)
        if handler:
            handler(value)
            engine._rebuild_board()
            self._delay_save_config()

    def _on_gain_change(self, value):
        self.engine.output_gain.gain_db = value
        self.engine._rebuild_board()
        sign = "+" if value >= 0 else ""
        self._gain_val_label.configure(text=f"{sign}{value:.1f} dB")
        self._delay_save_config()

    def _delay_save_config(self):
        if hasattr(self, '_save_job'):
            self.after_cancel(self._save_job)
        self._save_job = self.after(1000, self._save_app_config)

    # ----- Start / Stop -----

    def _startup_retry_audio(self):
        """Robust startup: retry audio engine init with increasing delays for boot scenarios."""
        self._startup_retry_count += 1
        logging.info(f"Startup attempt {self._startup_retry_count}/{self._startup_max_retries}")

        # Re-scan devices each attempt (drivers may have loaded since last try)
        try:
            self._load_devices()
        except Exception as e:
            logging.warning(f"Device scan failed: {e}")

        # Restore saved device selections
        config = load_config()
        in_name = config.get("in_name")
        out_name = config.get("out_name")
        if in_name:
            self.input_selector.set_by_raw_name(in_name)
        if out_name:
            self.output_selector.set_by_raw_name(out_name)

        in_idx = self.input_selector.get_selected_index()
        out_idx = self.output_selector.get_selected_index()

        if in_idx is None or out_idx is None:
            logging.warning(f"Devices not found yet (in={in_name}, out={out_name})")
            if self._startup_retry_count < self._startup_max_retries:
                delay = self._startup_retry_delays[min(self._startup_retry_count - 1, len(self._startup_retry_delays) - 1)]
                logging.info(f"Retrying in {delay}ms...")
                self.after(delay, self._startup_retry_audio)
            else:
                logging.error("Max retries reached. Audio devices not available.")
            return

        # Devices found — try to start
        try:
            if not self.engine.running:
                # Apply saved preset/settings
                last_state = config.get("last_state")
                if last_state and isinstance(last_state, dict) and "gain_db" in last_state:
                    self.engine.apply_preset(last_state)

                self.engine.start(in_idx, out_idx)
                self.engine_var.set(True)
                self.engine_switch.select()
                self._status_dot.configure(text_color=GREEN)
                self._status_text.configure(text="Processando", text_color=GREEN)
                logging.info(f"Audio engine started successfully on attempt {self._startup_retry_count}")

                if self.monitor_var.get() and not self.engine.monitoring:
                    m_idx = self._find_monitor_device()
                    if m_idx is not None:
                        self.engine.start_monitoring(m_idx)

        except Exception as e:
            logging.error(f"Engine start failed: {e}")
            if self._startup_retry_count < self._startup_max_retries:
                delay = self._startup_retry_delays[min(self._startup_retry_count - 1, len(self._startup_retry_delays) - 1)]
                logging.info(f"Retrying in {delay}ms...")
                self.after(delay, self._startup_retry_audio)
            else:
                logging.error("Max retries reached. Could not start audio engine.")

    def _auto_start_processing(self):
        in_idx = self.input_selector.get_selected_index()
        out_idx = self.output_selector.get_selected_index()

        if in_idx is None or out_idx is None:
            return

        if not self.engine.running:
            try:
                self.engine.start(in_idx, out_idx)
                self.engine_var.set(True)
                self.engine_switch.select()
                self._status_dot.configure(text_color=GREEN)
                self._status_text.configure(text="Processando", text_color=GREEN)
                
                if self.monitor_var.get() and not self.engine.monitoring:
                    m_idx = self._find_monitor_device()
                    if m_idx is not None:
                        self.engine.start_monitoring(m_idx)
                        if self.engine.monitoring:
                            self.monitor_switch.configure(text_color=GREEN)
                        else:
                            self.monitor_var.set(False)
                            self.monitor_switch.configure(text_color=TEXT_DIM)
            except: pass

    def _toggle_processing(self):
        if self.engine_var.get():
            in_idx = self.input_selector.get_selected_index()
            out_idx = self.output_selector.get_selected_index()

            if in_idx is None or out_idx is None:
                messagebox.showerror(
                    "MicMaster Pro",
                    "Selecione os dispositivos de entrada e saída!",
                )
                self.engine_var.set(False)
                return
            
            try:
                self.engine.start(in_idx, out_idx)
                self.engine_switch.select()
                self._status_dot.configure(text_color=GREEN)
                self._status_text.configure(text="Processando", text_color=GREEN)
                
                # Check monitor automatically if it was active
                if self.monitor_var.get() and not self.engine.monitoring:
                    m_idx = self._find_monitor_device()
                    if m_idx is not None:
                        self.engine.start_monitoring(m_idx)
                        if self.engine.monitoring:
                            self.monitor_switch.configure(text_color=GREEN)
                        else:
                            self.monitor_var.set(False)
                            self.monitor_switch.configure(text_color=TEXT_DIM)
            except Exception as e:
                self.engine_var.set(False)
                messagebox.showerror("Erro", f"Falha ao iniciar: {e}")
        else:
            self.engine.stop()
            self.engine_var.set(False)
            self._status_dot.configure(text_color=TEXT_DARK)
            self._status_text.configure(text="Parado", text_color=TEXT_DIM)
            self._latency_label.configure(text="Latência: — ms")
            
            if self.monitor_var.get():
                self.monitor_var.set(False)
                self.monitor_switch.configure(text_color=TEXT_DIM)
                
        self._delay_save_config()

    # ----- Meter Updates -----

    def _start_meter_updates(self):
        self._update_meters()

    def _update_meters(self):
        if self.engine.running:
            self.meters.update_meters(
                self.engine.input_level_db,
                self.engine.input_peak_db,
                self.engine.output_level_db,
                self.engine.output_peak_db,
            )

            in_db = self.engine.input_level_db
            out_db = self.engine.output_level_db
            in_txt = f"{in_db:.1f} dB" if in_db > -59 else "-∞ dB"
            out_txt = f"{out_db:.1f} dB" if out_db > -59 else "-∞ dB"
            self._in_level_label.configure(text=f"IN: {in_txt}")
            self._out_level_label.configure(text=f"OUT: {out_txt}")

            lat = self.engine.latency_ms
            self._latency_label.configure(text=f"Latência: {lat:.1f} ms")

        self._meter_job = self.after(33, self._update_meters)  # ~30fps

    # ----- Cleanup -----

    def _on_close(self):
        self.withdraw()  # Esconde como daemon

    def _destroy_completely(self):
        self.engine.stop()
        if self._meter_job:
            self.after_cancel(self._meter_job)
        self.quit()
        self.destroy()
