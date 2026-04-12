"""Simple settings GUI using tkinter (stdlib — no extra dependencies)."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class SettingsGUI:
    """Tkinter-based settings panel for the sign language overlay."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = Path(config_path)
        self.config: dict = {}
        self.root = None

    def load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}
        return self.config

    def save_config(self) -> None:
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config, f, default_flow_style=False, sort_keys=False)
        logger.info("Config saved to %s", self.config_path)

    def show(self) -> None:
        """Open the settings window. Blocks until closed."""
        import tkinter as tk
        from tkinter import ttk

        self.load_config()

        self.root = tk.Tk()
        self.root.title("Sign Language Overlay - Settings")
        self.root.geometry("450x520")
        self.root.resizable(False, False)

        # Variables bound to config values
        display_cfg = self.config.get("display", {})
        whisper_cfg = self.config.get("whisper", {})
        expr_cfg = self.config.get("expressions", {})
        realtime_cfg = self.config.get("realtime", {})

        self._vars: dict[str, tk.Variable] = {}

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        row = 0

        # ── Language ──────────────────────────────────────────────
        lf = ttk.LabelFrame(main_frame, text="Language", padding=5)
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        main_frame.columnconfigure(0, weight=1)

        self._vars["language"] = tk.StringVar(value=self.config.get("language", "asl"))
        ttk.Label(lf, text="Sign language:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            lf, textvariable=self._vars["language"],
            values=["asl", "bsl", "isl", "auslan"], state="readonly", width=15,
        ).grid(row=0, column=1, padx=5)

        row += 1

        # ── Display ───────────────────────────────────────────────
        df = ttk.LabelFrame(main_frame, text="Display", padding=5)
        df.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self._vars["position"] = tk.StringVar(value=display_cfg.get("position", "bottom-right"))
        ttk.Label(df, text="Position:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            df, textvariable=self._vars["position"],
            values=["top-left", "top-right", "bottom-left", "bottom-right"],
            state="readonly", width=15,
        ).grid(row=0, column=1, padx=5)

        self._vars["size"] = tk.IntVar(value=display_cfg.get("size", 200))
        ttk.Label(df, text="Size (px):").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Scale(df, from_=100, to=400, variable=self._vars["size"],
                  orient="horizontal", length=150).grid(row=1, column=1, padx=5)

        self._vars["opacity"] = tk.DoubleVar(value=display_cfg.get("background_opacity", 0.8))
        ttk.Label(df, text="Opacity:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Scale(df, from_=0.1, to=1.0, variable=self._vars["opacity"],
                  orient="horizontal", length=150).grid(row=2, column=1, padx=5)

        self._vars["transition"] = tk.StringVar(value=display_cfg.get("transition", "fade"))
        ttk.Label(df, text="Transition:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Combobox(
            df, textvariable=self._vars["transition"],
            values=["fade", "cut", "slide"], state="readonly", width=15,
        ).grid(row=3, column=1, padx=5)

        self._vars["transition_ms"] = tk.IntVar(value=display_cfg.get("transition_ms", 100))
        ttk.Label(df, text="Transition (ms):").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Scale(df, from_=0, to=500, variable=self._vars["transition_ms"],
                  orient="horizontal", length=150).grid(row=4, column=1, padx=5)

        row += 1

        # ── Whisper ───────────────────────────────────────────────
        wf = ttk.LabelFrame(main_frame, text="Whisper (Speech-to-Text)", padding=5)
        wf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self._vars["whisper_model"] = tk.StringVar(value=whisper_cfg.get("model_size", "base"))
        ttk.Label(wf, text="Model size:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            wf, textvariable=self._vars["whisper_model"],
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly", width=15,
        ).grid(row=0, column=1, padx=5)

        row += 1

        # ── Expressions ──────────────────────────────────────────
        ef = ttk.LabelFrame(main_frame, text="Expressions", padding=5)
        ef.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self._vars["expr_enabled"] = tk.BooleanVar(value=expr_cfg.get("enabled", False))
        ttk.Checkbutton(ef, text="Show expression hints",
                        variable=self._vars["expr_enabled"]).grid(row=0, column=0, sticky="w")

        self._vars["font_size"] = tk.IntVar(value=expr_cfg.get("font_size", 32))
        ttk.Label(ef, text="Font size:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(ef, from_=16, to=64, textvariable=self._vars["font_size"],
                     width=5).grid(row=1, column=1, padx=5, sticky="w")

        row += 1

        # ── Realtime ─────────────────────────────────────────────
        rf = ttk.LabelFrame(main_frame, text="Real-time Audio", padding=5)
        rf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self._vars["chunk_ms"] = tk.IntVar(value=realtime_cfg.get("chunk_duration_ms", 3000))
        ttk.Label(rf, text="Chunk (ms):").grid(row=0, column=0, sticky="w")
        ttk.Scale(rf, from_=1000, to=10000, variable=self._vars["chunk_ms"],
                  orient="horizontal", length=150).grid(row=0, column=1, padx=5)

        row += 1

        # ── Buttons ──────────────────────────────────────────────
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reset", command=self._on_reset).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.root.destroy).pack(side="right", padx=5)

        self.root.mainloop()

    def _on_save(self) -> None:
        self.config["language"] = self._vars["language"].get()
        self.config.setdefault("display", {})
        self.config["display"]["position"] = self._vars["position"].get()
        self.config["display"]["size"] = self._vars["size"].get()
        self.config["display"]["background_opacity"] = round(self._vars["opacity"].get(), 2)
        self.config["display"]["transition"] = self._vars["transition"].get()
        self.config["display"]["transition_ms"] = self._vars["transition_ms"].get()

        self.config.setdefault("whisper", {})
        self.config["whisper"]["model_size"] = self._vars["whisper_model"].get()

        self.config.setdefault("expressions", {})
        self.config["expressions"]["enabled"] = self._vars["expr_enabled"].get()
        self.config["expressions"]["font_size"] = self._vars["font_size"].get()

        self.config.setdefault("realtime", {})
        self.config["realtime"]["chunk_duration_ms"] = self._vars["chunk_ms"].get()

        self.save_config()
        if self.root:
            self.root.destroy()

    def _on_reset(self) -> None:
        self.load_config()
        display_cfg = self.config.get("display", {})
        whisper_cfg = self.config.get("whisper", {})
        expr_cfg = self.config.get("expressions", {})
        realtime_cfg = self.config.get("realtime", {})

        self._vars["language"].set(self.config.get("language", "asl"))
        self._vars["position"].set(display_cfg.get("position", "bottom-right"))
        self._vars["size"].set(display_cfg.get("size", 200))
        self._vars["opacity"].set(display_cfg.get("background_opacity", 0.8))
        self._vars["transition"].set(display_cfg.get("transition", "fade"))
        self._vars["transition_ms"].set(display_cfg.get("transition_ms", 100))
        self._vars["whisper_model"].set(whisper_cfg.get("model_size", "base"))
        self._vars["expr_enabled"].set(expr_cfg.get("enabled", False))
        self._vars["font_size"].set(expr_cfg.get("font_size", 32))
        self._vars["chunk_ms"].set(realtime_cfg.get("chunk_duration_ms", 3000))
