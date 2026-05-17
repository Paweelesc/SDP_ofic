"""
Test MUSHRA (ITU-R BS.1534) — zaktualizowany.
Pliki z folderu Magisterka/audio (48 kHz, znormalizowane -23 LUFS).
7 próbek: aur48, aur24, aur12, aur8, aur4, ukryta referencja, kotwica mono.
"""

import csv
import os
import random
import threading
from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import sounddevice as sd
import soundfile as sf

# =========================
# KONFIGURACJA
# =========================

TASKS = [
    {
        "id": 1,
        "instrument": "Gitara klasyczna",
        "room": "Korytarz ZEA",
        "position": "Na wprost",
        "refFile": "audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test01_gitara_klasyczna_korytarz_wprost_aur48.wav",
            "aur24":      "audio/auraliz_24/test01_gitara_klasyczna_korytarz_wprost_aur24.wav",
            "aur12":      "audio/auraliz_12/test01_gitara_klasyczna_korytarz_wprost_aur12.wav",
            "aur8":       "audio/auraliz_8/test01_gitara_klasyczna_korytarz_wprost_aur8.wav",
            "aur4":       "audio/auraliz_4/test01_gitara_klasyczna_korytarz_wprost_aur4.wav",
            "hidden_ref": "audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav",
            "anchor":     "audio/anchor_mono/test01_gitara_klasyczna_korytarz_wprost_anchor.wav",
        },
    },
    {
        "id": 2,
        "instrument": "Gitara klasyczna",
        "room": "Sala 123",
        "position": "Prawe ucho",
        "refFile": "audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test02_gitara_klasyczna_sala123_praweucho_aur48.wav",
            "aur24":      "audio/auraliz_24/test02_gitara_klasyczna_sala123_praweucho_aur24.wav",
            "aur12":      "audio/auraliz_12/test02_gitara_klasyczna_sala123_praweucho_aur12.wav",
            "aur8":       "audio/auraliz_8/test02_gitara_klasyczna_sala123_praweucho_aur8.wav",
            "aur4":       "audio/auraliz_4/test02_gitara_klasyczna_sala123_praweucho_aur4.wav",
            "hidden_ref": "audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav",
            "anchor":     "audio/anchor_mono/test02_gitara_klasyczna_sala123_praweucho_anchor.wav",
        },
    },
    {
        "id": 3,
        "instrument": "Kontrabas palcami",
        "room": "Korytarz ZEA",
        "position": "Na wprost",
        "refFile": "audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test03_kontrabas_palce_korytarz_wprost_aur48.wav",
            "aur24":      "audio/auraliz_24/test03_kontrabas_palce_korytarz_wprost_aur24.wav",
            "aur12":      "audio/auraliz_12/test03_kontrabas_palce_korytarz_wprost_aur12.wav",
            "aur8":       "audio/auraliz_8/test03_kontrabas_palce_korytarz_wprost_aur8.wav",
            "aur4":       "audio/auraliz_4/test03_kontrabas_palce_korytarz_wprost_aur4.wav",
            "hidden_ref": "audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav",
            "anchor":     "audio/anchor_mono/test03_kontrabas_palce_korytarz_wprost_anchor.wav",
        },
    },
    {
        "id": 4,
        "instrument": "Kontrabas palcami",
        "room": "Studio",
        "position": "Na wprost",
        "refFile": "audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test04_kontrabas_palce_studio_wprost_aur48.wav",
            "aur24":      "audio/auraliz_24/test04_kontrabas_palce_studio_wprost_aur24.wav",
            "aur12":      "audio/auraliz_12/test04_kontrabas_palce_studio_wprost_aur12.wav",
            "aur8":       "audio/auraliz_8/test04_kontrabas_palce_studio_wprost_aur8.wav",
            "aur4":       "audio/auraliz_4/test04_kontrabas_palce_studio_wprost_aur4.wav",
            "hidden_ref": "audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav",
            "anchor":     "audio/anchor_mono/test04_kontrabas_palce_studio_wprost_anchor.wav",
        },
    },
    {
        "id": 5,
        "instrument": "Kontrabas smyczkiem",
        "room": "Studio",
        "position": "Lewe ucho",
        "refFile": "audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test05_kontrabas_smyczek_studio_leweucho_aur48.wav",
            "aur24":      "audio/auraliz_24/test05_kontrabas_smyczek_studio_leweucho_aur24.wav",
            "aur12":      "audio/auraliz_12/test05_kontrabas_smyczek_studio_leweucho_aur12.wav",
            "aur8":       "audio/auraliz_8/test05_kontrabas_smyczek_studio_leweucho_aur8.wav",
            "aur4":       "audio/auraliz_4/test05_kontrabas_smyczek_studio_leweucho_aur4.wav",
            "hidden_ref": "audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav",
            "anchor":     "audio/anchor_mono/test05_kontrabas_smyczek_studio_leweucho_anchor.wav",
        },
    },
    {
        "id": 6,
        "instrument": "Wiolonczela",
        "room": "Korytarz ZEA",
        "position": "Na wprost",
        "refFile": "audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test06_wiolonczela_korytarz_wprost_aur48.wav",
            "aur24":      "audio/auraliz_24/test06_wiolonczela_korytarz_wprost_aur24.wav",
            "aur12":      "audio/auraliz_12/test06_wiolonczela_korytarz_wprost_aur12.wav",
            "aur8":       "audio/auraliz_8/test06_wiolonczela_korytarz_wprost_aur8.wav",
            "aur4":       "audio/auraliz_4/test06_wiolonczela_korytarz_wprost_aur4.wav",
            "hidden_ref": "audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav",
            "anchor":     "audio/anchor_mono/test06_wiolonczela_korytarz_wprost_anchor.wav",
        },
    },
    {
        "id": 7,
        "instrument": "Wiolonczela",
        "room": "Sala 123",
        "position": "Oddalone",
        "refFile": "audio/ref/test07_wiolonczela_sala123_daleko_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test07_wiolonczela_sala123_daleko_aur48.wav",
            "aur24":      "audio/auraliz_24/test07_wiolonczela_sala123_daleko_aur24.wav",
            "aur12":      "audio/auraliz_12/test07_wiolonczela_sala123_daleko_aur12.wav",
            "aur8":       "audio/auraliz_8/test07_wiolonczela_sala123_daleko_aur8.wav",
            "aur4":       "audio/auraliz_4/test07_wiolonczela_sala123_daleko_aur4.wav",
            "hidden_ref": "audio/ref/test07_wiolonczela_sala123_daleko_ref.wav",
            "anchor":     "audio/anchor_mono/test07_wiolonczela_sala123_daleko_anchor.wav",
        },
    },
    {
        "id": 8,
        "instrument": "Flet",
        "room": "Studio",
        "position": "Lewe ucho",
        "refFile": "audio/ref/test08_flet_studio_leweucho_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test08_flet_studio_leweucho_aur48.wav",
            "aur24":      "audio/auraliz_24/test08_flet_studio_leweucho_aur24.wav",
            "aur12":      "audio/auraliz_12/test08_flet_studio_leweucho_aur12.wav",
            "aur8":       "audio/auraliz_8/test08_flet_studio_leweucho_aur8.wav",
            "aur4":       "audio/auraliz_4/test08_flet_studio_leweucho_aur4.wav",
            "hidden_ref": "audio/ref/test08_flet_studio_leweucho_ref.wav",
            "anchor":     "audio/anchor_mono/test08_flet_studio_leweucho_anchor.wav",
        },
    },
    {
        "id": 9,
        "instrument": "Saksofon",
        "room": "Studio",
        "position": "Lewe ucho",
        "refFile": "audio/ref/test09_saksofon_studio_leweucho_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test09_saksofon_studio_leweucho_aur48.wav",
            "aur24":      "audio/auraliz_24/test09_saksofon_studio_leweucho_aur24.wav",
            "aur12":      "audio/auraliz_12/test09_saksofon_studio_leweucho_aur12.wav",
            "aur8":       "audio/auraliz_8/test09_saksofon_studio_leweucho_aur8.wav",
            "aur4":       "audio/auraliz_4/test09_saksofon_studio_leweucho_aur4.wav",
            "hidden_ref": "audio/ref/test09_saksofon_studio_leweucho_ref.wav",
            "anchor":     "audio/anchor_mono/test09_saksofon_studio_leweucho_anchor.wav",
        },
    },
    {
        "id": 10,
        "instrument": "Akordeon",
        "room": "Korytarz ZEA",
        "position": "Oddalone",
        "refFile": "audio/ref/test10_akordeon_korytarz_daleko_ref.wav",
        "stimuli": {
            "aur48":      "audio/auraliz_48/test10_akordeon_korytarz_daleko_aur48.wav",
            "aur24":      "audio/auraliz_24/test10_akordeon_korytarz_daleko_aur24.wav",
            "aur12":      "audio/auraliz_12/test10_akordeon_korytarz_daleko_aur12.wav",
            "aur8":       "audio/auraliz_8/test10_akordeon_korytarz_daleko_aur8.wav",
            "aur4":       "audio/auraliz_4/test10_akordeon_korytarz_daleko_aur4.wav",
            "hidden_ref": "audio/ref/test10_akordeon_korytarz_daleko_ref.wav",
            "anchor":     "audio/anchor_mono/test10_akordeon_korytarz_daleko_anchor.wav",
        },
    },
]

TYPE_LABELS = {
    "aur48": "Auralizacja 48 kHz",
    "aur24": "Auralizacja 24 kHz",
    "aur12": "Auralizacja 12 kHz",
    "aur8":  "Auralizacja 8 kHz",
    "aur4":  "Auralizacja 4 kHz",
    "hidden_ref": "Ukryta referencja",
    "anchor": "Kotwica (mono)",
}
SAMPLE_LETTERS = ["A", "B", "C", "D", "E", "F", "G"]


@dataclass
class SampleEntry:
    letter: str
    sample_type: str
    file: str


class StreamPlayer:
    def __init__(self):
        self.stream = None
        self.sound_file = None
        self.thread = None
        self.stop_event = threading.Event()
        self.is_playing = False
        self.finished_callback = None
        self.error_callback = None

    def stop(self):
        self.stop_event.set()
        try:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        self.stream = None
        try:
            if self.sound_file is not None:
                self.sound_file.close()
        except Exception:
            pass
        self.sound_file = None
        self.is_playing = False

    def play(self, filepath, finished_callback=None, error_callback=None):
        self.stop()
        self.stop_event.clear()
        self.finished_callback = finished_callback
        self.error_callback = error_callback

        def worker():
            try:
                sf_desc = sf.SoundFile(filepath, mode="r")
                self.sound_file = sf_desc

                def callback(outdata, frames, time, status):
                    if self.stop_event.is_set():
                        outdata.fill(0)
                        raise sd.CallbackStop()
                    data = sf_desc.read(frames, dtype="float32", always_2d=True)
                    if len(data) == 0:
                        outdata.fill(0)
                        raise sd.CallbackStop()
                    if len(data) < frames:
                        outdata[:len(data)] = data
                        outdata[len(data):].fill(0)
                        raise sd.CallbackStop()
                    else:
                        outdata[:] = data

                self.stream = sd.OutputStream(
                    samplerate=sf_desc.samplerate,
                    channels=sf_desc.channels,
                    dtype="float32",
                    callback=callback,
                    blocksize=4096,
                )
                self.is_playing = True
                self.stream.start()
                while self.stream.active and not self.stop_event.is_set():
                    sd.sleep(100)
            except Exception as e:
                self.is_playing = False
                if self.error_callback:
                    self.error_callback(str(e))
                return
            finally:
                try:
                    if self.stream is not None:
                        self.stream.close()
                except Exception:
                    pass
                self.stream = None
                try:
                    if self.sound_file is not None:
                        self.sound_file.close()
                except Exception:
                    pass
                self.sound_file = None
                was_stopped = self.stop_event.is_set()
                self.is_playing = False
                if (not was_stopped) and self.finished_callback:
                    self.finished_callback()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()


class LocalMushraApp:
    BG = "#f7f4ef"
    SURFACE = "#ffffff"
    SURFACE2 = "#f2eee8"
    BORDER = "#ddd5c9"
    TEXT = "#1f1d1a"
    TEXT2 = "#6f685f"
    TEXT3 = "#9d968c"
    ACCENT = "#b2552f"
    ACCENT_DARK = "#8e4023"
    ACCENT_BG = "#f6e9e1"
    REF_BORDER = "#ddb79f"
    HIGH_BG = "#e7f3ea"
    HIGH_BORDER = "#a7c9b0"
    LOW_BG = "#f8e8e8"
    LOW_BORDER = "#d9abab"

    def __init__(self, root):
        self.root = root
        self.root.title("Test MUSHRA — Auralizacja (7 wariantów)")
        self.root.geometry("1600x950")
        self.root.minsize(1400, 860)
        self.root.configure(bg=self.BG)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.player = StreamPlayer()
        self.current_task_index = 0
        self.randomized_samples = {}
        self.scores = {}
        self.currently_playing_key = None

        self.participant_name = tk.StringVar()
        self.exp_level = tk.StringVar()
        self.headphone_type = tk.StringVar(value="sluchawki_zamkniete")
        self.headphone_model = tk.StringVar()
        self.debug_labels_visible = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Gotowe")
        self.sample_widgets = {}

        self._build_randomized_samples()
        self._init_scores()
        self._setup_style()
        self._build_ui()
        self.show_intro()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Accent.TButton",
                   background=[("!disabled", self.ACCENT), ("active", self.ACCENT_DARK)],
                   foreground=[("!disabled", "white")])
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def abs_path(self, rel_path):
        return os.path.join(self.base_dir, rel_path)

    def _build_randomized_samples(self):
        self.randomized_samples = {}
        for task in TASKS:
            types = list(task["stimuli"].keys())
            random.shuffle(types)
            self.randomized_samples[task["id"]] = [
                SampleEntry(letter=SAMPLE_LETTERS[i], sample_type=t, file=task["stimuli"][t])
                for i, t in enumerate(types)
            ]

    def _init_scores(self):
        self.scores = {}
        for task in TASKS:
            self.scores[task["id"]] = {letter: 50 for letter in SAMPLE_LETTERS}

    def _build_ui(self):
        self.container = tk.Frame(self.root, bg=self.BG, padx=18, pady=14)
        self.container.pack(fill="both", expand=True)

        header = tk.Frame(self.container, bg=self.BG)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Test MUSHRA — Auralizacja", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(header, text="7 wariantów · 10 zadań", bg=self.BG, fg=self.TEXT2, font=("Consolas", 10)).pack(side="right")

        self.main = tk.Frame(self.container, bg=self.BG)
        self.main.pack(fill="both", expand=True)

        footer = tk.Frame(self.container, bg=self.BG)
        footer.pack(fill="x", pady=(6, 0))
        tk.Label(footer, textvariable=self.status_var, bg=self.BG, fg=self.TEXT2, font=("Segoe UI", 9)).pack(side="left")

        self.intro_frame = tk.Frame(self.main, bg=self.BG)
        self.test_frame = tk.Frame(self.main, bg=self.BG)
        self.results_frame = tk.Frame(self.main, bg=self.BG)

        self._build_intro_frame()
        self._build_test_frame()
        self._build_results_frame()

    def _card(self, parent, title=None, pad=12, bg=None, border=None):
        bg = bg or self.SURFACE
        border = border or self.BORDER
        outer = tk.Frame(parent, bg=bg, highlightbackground=border, highlightthickness=1)
        inner = tk.Frame(outer, bg=bg, padx=pad, pady=pad)
        inner.pack(fill="both", expand=True)
        if title:
            tk.Label(inner, text=title, bg=bg, fg=self.TEXT3, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        return outer, inner

    def clear_main(self):
        for f in (self.intro_frame, self.test_frame, self.results_frame):
            f.pack_forget()

    def show_intro(self):
        self.clear_main()
        self.intro_frame.pack(fill="both", expand=True)

    def show_test(self):
        self.clear_main()
        self.test_frame.pack(fill="both", expand=True)
        self.render_task()

    def show_results(self):
        self.clear_main()
        self.results_frame.pack(fill="both", expand=True)
        self.render_results()

    def _build_intro_frame(self):
        info_outer, info = self._card(self.intro_frame, "INSTRUKCJA", 14)
        info_outer.pack(fill="x", pady=(0, 10))
        tk.Label(info,
                 text="Oceniasz zgodność z referencją (REF) na skali 0–100. "
                      "Masz 7 anonimowych próbek: 5 wariantów auralizacji (różne pasma IR), "
                      "ukrytą referencję i kotwicę mono. Kolejność losowa.",
                 bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 11),
                 wraplength=1340, justify="left").pack(anchor="w")

        scale_row = tk.Frame(info, bg=self.SURFACE)
        scale_row.pack(fill="x", pady=(12, 0))
        for rng, txt in [("0–20", "Zła"), ("20–40", "Słaba"), ("40–60", "Dostateczna"), ("60–80", "Dobra"), ("80–100", "Doskonała")]:
            cell = tk.Frame(scale_row, bg=self.SURFACE2, highlightbackground=self.BORDER, highlightthickness=1, padx=8, pady=6)
            cell.pack(side="left", fill="x", expand=True, padx=3)
            tk.Label(cell, text=rng, bg=self.SURFACE2, fg=self.TEXT, font=("Consolas", 11, "bold")).pack()
            tk.Label(cell, text=txt, bg=self.SURFACE2, fg=self.TEXT2, font=("Segoe UI", 9)).pack()

        form_outer, form = self._card(self.intro_frame, "DANE UCZESTNIKA", 14)
        form_outer.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(form, bg=self.SURFACE)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Imię / pseudonim *", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10), width=20, anchor="w").pack(side="left")
        ttk.Entry(row1, textvariable=self.participant_name, width=30).pack(side="left", padx=(0, 16))
        tk.Label(row1, text="Doświadczenie", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10), width=14, anchor="w").pack(side="left")
        ttk.Combobox(row1, textvariable=self.exp_level, width=24, state="readonly",
                     values=["", "brak", "amator", "sredniozaawansowany", "zaawansowany", "profesjonalny"]).pack(side="left")

        row2 = tk.Frame(form, bg=self.SURFACE)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Sprzęt odsłuchowy", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10), width=20, anchor="w").pack(side="left")
        ttk.Combobox(row2, textvariable=self.headphone_type, width=30, state="readonly",
                     values=["sluchawki_zamkniete", "sluchawki_otwarte", "sluchawki_douszne", "glosniki"]).pack(side="left", padx=(0, 16))
        tk.Label(row2, text="Model", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10), width=14, anchor="w").pack(side="left")
        ttk.Entry(row2, textvariable=self.headphone_model, width=24).pack(side="left")

        actions = tk.Frame(self.intro_frame, bg=self.BG)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Rozpocznij test", style="Accent.TButton", command=self.start_test).pack(side="left")
        tk.Label(actions, text="10 zadań × 7 próbek · ~40–50 min", bg=self.BG, fg=self.TEXT3, font=("Segoe UI", 9)).pack(side="left", padx=16)

    def _build_test_frame(self):
        top = tk.Frame(self.test_frame, bg=self.BG)
        top.pack(fill="x", pady=(0, 8))
        self.progress_label = tk.Label(top, text="", bg=self.BG, fg=self.TEXT2, font=("Consolas", 10))
        self.progress_label.pack(side="left")
        ttk.Checkbutton(top, text="Debug", variable=self.debug_labels_visible, command=self.render_task).pack(side="right")

        task_outer, task_box = self._card(self.test_frame, None, 12)
        task_outer.pack(fill="x", pady=(0, 8))
        self.task_title = tk.Label(task_box, text="", bg=self.SURFACE, fg=self.TEXT, font=("Segoe UI", 14, "bold"))
        self.task_title.pack(anchor="w")
        self.task_subtitle = tk.Label(task_box, text="", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10))
        self.task_subtitle.pack(anchor="w", pady=(2, 0))

        ref_outer, ref_box = self._card(self.test_frame, None, 12, bg=self.ACCENT_BG, border=self.REF_BORDER)
        ref_outer.pack(fill="x", pady=(0, 8))
        ref_row = tk.Frame(ref_box, bg=self.ACCENT_BG)
        ref_row.pack(fill="x")
        self.ref_play_btn = ttk.Button(ref_row, text="▶ REF", style="Accent.TButton", command=lambda: self.toggle_audio("ref"))
        self.ref_play_btn.pack(side="left")
        self.ref_label = tk.Label(ref_row, text="", bg=self.ACCENT_BG, fg=self.ACCENT_DARK, font=("Segoe UI", 10, "bold"))
        self.ref_label.pack(side="left", padx=10)

        samples_outer, samples_box = self._card(self.test_frame, "PRÓBKI (A–G)", 10)
        samples_outer.pack(fill="both", expand=True, pady=(0, 8))
        self.samples_grid = tk.Frame(samples_box, bg=self.SURFACE)
        self.samples_grid.pack(fill="both", expand=True)

        nav_outer, nav = self._card(self.test_frame, None, 10)
        nav_outer.pack(fill="x")
        self.prev_btn = ttk.Button(nav, text="← Poprzednie", command=self.prev_task)
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(nav, text="Następne zadanie →", style="Accent.TButton", command=self.next_task)
        self.next_btn.pack(side="right")

    def _build_results_frame(self):
        self.results_summary_outer, self.results_summary = self._card(self.results_frame, "PODSUMOWANIE", 12)
        self.results_summary_outer.pack(fill="x", pady=(0, 8))

        table_outer, table_box = self._card(self.results_frame, "SZCZEGÓŁOWE WYNIKI", 8)
        table_outer.pack(fill="both", expand=True, pady=(0, 8))

        columns = ("zadanie", "instrument", "pomieszczenie", "probka", "typ", "ocena")
        self.results_tree = ttk.Treeview(table_box, columns=columns, show="headings")
        headings = {"zadanie": "Zad.", "instrument": "Instrument", "pomieszczenie": "Pomiesz.", "probka": "Pr.", "typ": "Typ", "ocena": "Ocena"}
        widths = {"zadanie": 50, "instrument": 180, "pomieszczenie": 120, "probka": 40, "typ": 160, "ocena": 60}
        for c in columns:
            self.results_tree.heading(c, text=headings[c])
            self.results_tree.column(c, width=widths[c], anchor="center" if c in {"zadanie", "probka", "ocena"} else "w")

        yscroll = ttk.Scrollbar(table_box, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=yscroll.set)
        self.results_tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self.validation_label = tk.Label(self.results_frame, text="", bg=self.BG, fg=self.TEXT2, font=("Segoe UI", 9), justify="left")
        self.validation_label.pack(anchor="w", pady=(0, 8))

        actions = tk.Frame(self.results_frame, bg=self.BG)
        actions.pack(fill="x")
        ttk.Button(actions, text="Eksportuj CSV", style="Accent.TButton", command=self.export_csv).pack(side="left")
        ttk.Button(actions, text="Nowy test", command=self.reset_test).pack(side="right")

    def start_test(self):
        if not self.participant_name.get().strip():
            messagebox.showerror("Błąd", "Podaj imię lub pseudonim.")
            return
        self.show_test()

    def current_task(self):
        return TASKS[self.current_task_index]

    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def on_play_finished(self):
        self.root.after(0, self._on_play_finished_ui)

    def _on_play_finished_ui(self):
        if self.currently_playing_key == "ref":
            self.ref_play_btn.configure(text="▶ REF")
        elif self.currently_playing_key in self.sample_widgets:
            self.sample_widgets[self.currently_playing_key]["play_btn"].configure(text=f"▶ {self.currently_playing_key}")
        self.currently_playing_key = None
        self.set_status("Gotowe")

    def on_play_error(self, msg):
        self.root.after(0, lambda: self._on_play_error_ui(msg))

    def _on_play_error_ui(self, msg):
        self._on_play_finished_ui()
        messagebox.showerror("Błąd odtwarzania", msg)

    def toggle_audio(self, key):
        if self.currently_playing_key == key and self.player.is_playing:
            self.player.stop()
            self._on_play_finished_ui()
            return

        if self.currently_playing_key == "ref":
            self.ref_play_btn.configure(text="▶ REF")
        elif self.currently_playing_key in self.sample_widgets:
            self.sample_widgets[self.currently_playing_key]["play_btn"].configure(text=f"▶ {self.currently_playing_key}")

        task = self.current_task()
        if key == "ref":
            path = self.abs_path(task["refFile"])
            self.ref_play_btn.configure(text="■ REF")
        else:
            sample = next(s for s in self.randomized_samples[task["id"]] if s.letter == key)
            path = self.abs_path(sample.file)
            self.sample_widgets[key]["play_btn"].configure(text=f"■ {key}")

        if not os.path.exists(path):
            messagebox.showerror("Brak pliku", path)
            self._on_play_finished_ui()
            return

        self.currently_playing_key = key
        self.set_status(f"Odtwarzanie: {os.path.basename(path)}")
        self.player.play(path, finished_callback=self.on_play_finished, error_callback=self.on_play_error)

    def render_task(self):
        task = self.current_task()
        self.progress_label.configure(text=f"Zadanie {self.current_task_index + 1} z {len(TASKS)}")
        self.task_title.configure(text=f'{task["instrument"]} — {task["room"]}')
        self.task_subtitle.configure(text=f'Pozycja: {task["position"]}')
        self.ref_label.configure(text=f'{task["instrument"]} — {task["room"]}, {task["position"]}')
        self.prev_btn.configure(state=("normal" if self.current_task_index > 0 else "disabled"))
        self.next_btn.configure(text=("Zakończ →" if self.current_task_index == len(TASKS) - 1 else "Następne →"))

        for child in self.samples_grid.winfo_children():
            child.destroy()
        self.sample_widgets = {}

        samples = self.randomized_samples[task["id"]]
        for col, sample in enumerate(samples):
            card = tk.Frame(self.samples_grid, bg=self.SURFACE2, highlightbackground=self.BORDER, highlightthickness=1, padx=6, pady=8)
            card.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")
            self.samples_grid.columnconfigure(col, weight=1)

            tk.Label(card, text=sample.letter, bg=card["bg"], fg=self.TEXT, font=("Consolas", 14, "bold")).pack(pady=(0, 4))

            debug_text = TYPE_LABELS[sample.sample_type] if self.debug_labels_visible.get() else " "
            tk.Label(card, text=debug_text, bg=card["bg"], fg=self.TEXT2, font=("Segoe UI", 8), wraplength=120, justify="center").pack(pady=(0, 4))

            play_btn = ttk.Button(card, text=f"▶ {sample.letter}", command=lambda k=sample.letter: self.toggle_audio(k))
            play_btn.pack(pady=(0, 8))

            score_var = tk.IntVar(value=self.scores[task["id"]][sample.letter])
            value_label = tk.Label(card, text=str(score_var.get()), bg=card["bg"], fg=self.TEXT, font=("Consolas", 18, "bold"))
            value_label.pack()

            quality_label = tk.Label(card, text=self._quality_text(score_var.get()), bg=card["bg"], fg=self.TEXT2, font=("Segoe UI", 8))
            quality_label.pack(pady=(0, 6))

            scale = tk.Scale(card, from_=100, to=0, orient="vertical", length=250, width=16,
                             showvalue=False, bd=0, highlightthickness=0, troughcolor="#cbc5bd",
                             bg=card["bg"], activebackground=self.ACCENT, fg=self.TEXT,
                             command=lambda v, tid=task["id"], letter=sample.letter, sv=score_var,
                             vl=value_label, ql=quality_label, c=card: self._on_slider(v, tid, letter, sv, vl, ql, c))
            scale.set(score_var.get())
            scale.pack()

            self.sample_widgets[sample.letter] = {"play_btn": play_btn, "score_var": score_var,
                                                   "value_label": value_label, "quality_label": quality_label,
                                                   "scale": scale, "card": card}
            self._apply_card_color(card, score_var.get())

    def _apply_card_color(self, card, value):
        if value >= 70:
            bg, border = self.HIGH_BG, self.HIGH_BORDER
        elif value <= 25:
            bg, border = self.LOW_BG, self.LOW_BORDER
        else:
            bg, border = self.SURFACE2, self.BORDER
        card.configure(bg=bg, highlightbackground=border)
        for child in card.winfo_children():
            if isinstance(child, (tk.Label, tk.Scale)):
                try:
                    child.configure(bg=bg)
                except Exception:
                    pass

    def _on_slider(self, value, task_id, letter, score_var, value_label, quality_label, card):
        v = int(round(float(value)))
        self.scores[task_id][letter] = v
        score_var.set(v)
        value_label.configure(text=str(v))
        quality_label.configure(text=self._quality_text(v))
        self._apply_card_color(card, v)

    def _quality_text(self, v):
        if v >= 80: return "Doskonała"
        if v >= 60: return "Dobra"
        if v >= 40: return "Dostat."
        if v >= 20: return "Słaba"
        return "Zła"

    def next_task(self):
        self.player.stop()
        if self.current_task_index < len(TASKS) - 1:
            self.current_task_index += 1
            self.render_task()
        else:
            self.show_results()

    def prev_task(self):
        self.player.stop()
        if self.current_task_index > 0:
            self.current_task_index -= 1
            self.render_task()

    def render_results(self):
        by_type = {k: [] for k in TYPE_LABELS.keys()}
        for task in TASKS:
            for sample in self.randomized_samples[task["id"]]:
                by_type[sample.sample_type].append(self.scores[task["id"]][sample.letter])

        avg = lambda arr: round(sum(arr) / len(arr)) if arr else 0

        for child in self.results_summary.winfo_children():
            child.destroy()

        stats_wrap = tk.Frame(self.results_summary, bg=self.SURFACE)
        stats_wrap.pack(fill="x")
        for label, key in [("48 kHz", "aur48"), ("24 kHz", "aur24"), ("12 kHz", "aur12"),
                           ("8 kHz", "aur8"), ("4 kHz", "aur4"), ("Ukr. ref", "hidden_ref"), ("Kotwica", "anchor")]:
            card = tk.Frame(stats_wrap, bg=self.SURFACE2, highlightbackground=self.BORDER, highlightthickness=1, padx=6, pady=6)
            card.pack(side="left", fill="x", expand=True, padx=3)
            tk.Label(card, text=label, bg=self.SURFACE2, fg=self.TEXT2, font=("Segoe UI", 8)).pack()
            tk.Label(card, text=str(avg(by_type[key])), bg=self.SURFACE2, fg=self.TEXT, font=("Consolas", 18, "bold")).pack()

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        for task in TASKS:
            for sample in self.randomized_samples[task["id"]]:
                self.results_tree.insert("", "end", values=(
                    task["id"], task["instrument"], task["room"],
                    sample.letter, TYPE_LABELS[sample.sample_type],
                    self.scores[task["id"]][sample.letter]))

        hidden_avg = avg(by_type["hidden_ref"])
        anchor_avg = avg(by_type["anchor"])
        self.validation_label.configure(
            text=f"Walidacja: ukr. ref = {hidden_avg} | kotwica = {anchor_avg} | "
                 f"Uczestnik: {self.participant_name.get().strip()} | "
                 f"Doświadczenie: {self.exp_level.get() or '—'} | Sprzęt: {self.headphone_type.get()}")

    def export_csv(self):
        name = self.participant_name.get().strip() or "uczestnik"
        default_name = f"mushra_{name.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        save_path = filedialog.asksaveasfilename(title="Zapisz CSV", defaultextension=".csv",
                                                  initialfile=default_name, filetypes=[("CSV", "*.csv")])
        if not save_path:
            return

        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Uczestnik", "Doswiadczenie", "Sprzet", "Model", "Data",
                             "Zadanie", "Instrument", "Pomieszczenie", "Pozycja", "Probka", "Typ", "Ocena"])
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for task in TASKS:
                for sample in self.randomized_samples[task["id"]]:
                    writer.writerow([name, self.exp_level.get(), self.headphone_type.get(),
                                     self.headphone_model.get(), now, task["id"], task["instrument"],
                                     task["room"], task["position"], sample.letter,
                                     TYPE_LABELS[sample.sample_type], self.scores[task["id"]][sample.letter]])
        messagebox.showinfo("Gotowe", f"Zapisano:\n{save_path}")

    def reset_test(self):
        self.player.stop()
        self.current_task_index = 0
        self.currently_playing_key = None
        self._build_randomized_samples()
        self._init_scores()
        self.show_intro()

    def on_close(self):
        self.player.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LocalMushraApp(root)
    root.mainloop()