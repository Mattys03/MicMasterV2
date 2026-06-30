"""
MicMaster Pro — VU Meter Widget

Animated vertical VU meter using tkinter Canvas.
Shows RMS level (solid bar) and peak hold (thin marker).
Gradient: green → yellow → red.
"""

import tkinter as tk


class VUMeter(tk.Canvas):
    """Vertical VU meter with gradient and peak hold."""

    COLOR_BG = "#0d1117"
    COLOR_BORDER = "#30363d"
    COLOR_OFF = "#161b22"
    COLORS = [
        (-60, "#1a472a"),
        (-36, "#22663d"),
        (-24, "#2ea043"),
        (-18, "#3fb950"),
        (-12, "#7ee787"),
        (-9, "#d29922"),
        (-6, "#e3b341"),
        (-3, "#f85149"),
        (0, "#da3633"),
    ]

    def __init__(self, master, width=28, height=220, label="IN", **kwargs):
        super().__init__(
            master,
            width=width,
            height=height + 24,
            bg=self.COLOR_BG,
            highlightthickness=0,
            **kwargs,
        )

        self._width = width
        self._height = height
        self._label = label
        self._level_db = -60.0
        self._peak_db = -60.0
        self._peak_hold = -60.0
        self._peak_decay_counter = 0
        self._segments = 32
        self._segment_gap = 2
        self._db_min = -60.0
        self._db_max = 0.0

        self._draw_static()

    def _db_to_y(self, db: float) -> float:
        db = max(self._db_min, min(self._db_max, db))
        ratio = (db - self._db_min) / (self._db_max - self._db_min)
        return self._height - (ratio * self._height)

    def _db_to_color(self, db: float) -> str:
        for i in range(len(self.COLORS) - 1, -1, -1):
            if db >= self.COLORS[i][0]:
                return self.COLORS[i][1]
        return self.COLORS[0][1]

    def _draw_static(self):
        self.delete("all")
        self.create_text(
            self._width // 2,
            self._height + 14,
            text=self._label,
            fill="#8b949e",
            font=("Segoe UI", 8, "bold"),
            anchor="center",
        )

        self._bar_ids = []
        seg_h = (self._height - (self._segments - 1) * self._segment_gap) / self._segments
        padding_x = 3

        for i in range(self._segments):
            y_bottom = self._height - i * (seg_h + self._segment_gap)
            y_top = y_bottom - seg_h
            
            rect_id = self.create_rectangle(
                padding_x, y_top, self._width - padding_x, y_bottom,
                fill=self.COLOR_OFF, outline="",
            )
            self._bar_ids.append(rect_id)

        # Draw peak line off-screen initially
        self._peak_line_id = self.create_rectangle(
            padding_x, -10, self._width - padding_x, -8,
            fill="#e6edf3", outline="",
        )

    def update_level(self, level_db: float, peak_db: float):
        self._level_db = max(self._db_min, min(self._db_max, level_db))
        self._peak_db = max(self._db_min, min(self._db_max, peak_db))

        if self._peak_db > self._peak_hold:
            self._peak_hold = self._peak_db
            self._peak_decay_counter = 12
        else:
            self._peak_decay_counter -= 1
            if self._peak_decay_counter <= 0:
                self._peak_hold = max(self._peak_hold - 1.5, self._db_min)

        self._redraw()

    def _redraw(self):
        # Update each segment's color based on level
        for i, rect_id in enumerate(self._bar_ids):
            seg_db = self._db_min + (i / self._segments) * (self._db_max - self._db_min)
            if seg_db <= self._level_db:
                color = self._db_to_color(seg_db)
            else:
                color = self.COLOR_OFF
            self.itemconfig(rect_id, fill=color)

        # Update peak line position dynamically
        padding_x = 3
        if self._peak_hold > self._db_min + 3:
            peak_y = self._db_to_y(self._peak_hold)
            self.coords(self._peak_line_id, padding_x, peak_y - 1, self._width - padding_x, peak_y + 1)
        else:
            # Hide it offscreen
            self.coords(self._peak_line_id, padding_x, -10, self._width - padding_x, -8)


class StereoMeter(tk.Frame):
    """Dual VU meter (Input + Output) with dB scale."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#0d1117", **kwargs)

        self._db_labels_frame = tk.Frame(self, bg="#0d1117")
        self._db_labels_frame.pack(side="left", padx=(0, 2))

        db_marks = [0, -6, -12, -18, -24, -36, -48, -60]
        meter_h = 220
        for db in db_marks:
            ratio = (db - (-60)) / (0 - (-60))
            y_pos = meter_h - (ratio * meter_h)
            lbl = tk.Label(
                self._db_labels_frame,
                text=f"{db}",
                fg="#484f58",
                bg="#0d1117",
                font=("Segoe UI", 7),
                anchor="e",
                width=4,
            )
            lbl.place(x=0, y=y_pos - 6)

        self._db_labels_frame.configure(width=30, height=meter_h + 24)

        self.input_meter = VUMeter(self, label="IN", width=28, height=meter_h)
        self.input_meter.pack(side="left", padx=1)

        self.output_meter = VUMeter(self, label="OUT", width=28, height=meter_h)
        self.output_meter.pack(side="left", padx=1)

    def update_meters(self, in_level, in_peak, out_level, out_peak):
        self.input_meter.update_level(in_level, in_peak)
        self.output_meter.update_level(out_level, out_peak)
