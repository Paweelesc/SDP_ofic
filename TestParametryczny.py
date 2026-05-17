"""
Test parametryczny (atrybutowy) — ocena barwy, przestrzenności i naturalności.
Dla każdej próbki słuchacz ocenia 3 atrybuty osobno (0–100).
Pozwala skorelować LSD z oceną barwy, ILD error z oceną przestrzenności.

6 bodźców na zadanie (bez ukrytej referencji): aur48, aur24, aur12, aur8, aur4, anchor.
10 zadań × 6 bodźców = 60 ocen × 3 atrybuty = 180 wartości na słuchacza.
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
    {"id": 1,  "instrument": "Gitara klasyczna",    "room": "Korytarz ZEA", "position": "Na wprost",
     "refFile": "audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav",
     "base": "test01_gitara_klasyczna_korytarz_wprost"},
    {"id": 2,  "instrument": "Gitara klasyczna",    "room": "Sala 123",     "position": "Prawe ucho",
     "refFile": "audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav",
     "base": "test02_gitara_klasyczna_sala123_praweucho"},
    {"id": 3,  "instrument": "Kontrabas palcami",   "room": "Korytarz ZEA", "position": "Na wprost",
     "refFile": "audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav",
     "base": "test03_kontrabas_palce_korytarz_wprost"},
    {"id": 4,  "instrument": "Kontrabas palcami",   "room": "Studio",       "position": "Na wprost",
     "refFile": "audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav",
     "base": "test04_kontrabas_palce_studio_wprost"},
    {"id": 5,  "instrument": "Kontrabas smyczkiem", "room": "Studio",       "position": "Lewe ucho",
     "refFile": "audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav",
     "base": "test05_kontrabas_smyczek_studio_leweucho"},
    {"id": 6,  "instrument": "Wiolonczela",         "room": "Korytarz ZEA", "position": "Na wprost",
     "refFile": "audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav",
     "base": "test06_wiolonczela_korytarz_wprost"},
    {"id": 7,  "instrument": "Wiolonczela",         "room": "Sala 123",     "position": "Oddalone",
     "refFile": "audio/ref/test07_wiolonczela_sala123_daleko_ref.wav",
     "base": "test07_wiolonczela_sala123_daleko"},
    {"id": 8,  "instrument": "Flet",                "room": "Studio",       "position": "Lewe ucho",
     "refFile": "audio/ref/test08_flet_studio_leweucho_ref.wav",
     "base": "test08_flet_studio_leweucho"},
    {"id": 9,  "instrument": "Saksofon",            "room": "Studio",       "position": "Lewe ucho",
     "refFile": "audio/ref/test09_saksofon_studio_leweucho_ref.wav",
     "base": "test09_saksofon_studio_leweucho"},
    {"id": 10, "instrument": "Akordeon",             "room": "Korytarz ZEA", "position": "Oddalone",
     "refFile": "audio/ref/test10_akordeon_korytarz_daleko_ref.wav",
     "base": "test10_akordeon_korytarz_daleko"},
]

STIMULI_TYPES = [
    {"key": "aur48",  "folder": "auraliz_48",  "suffix": "_aur48.wav",  "label": "Auralizacja 48 kHz"},
    {"key": "aur24",  "folder": "auraliz_24",  "suffix": "_aur24.wav",  "label": "Auralizacja 24 kHz"},
    {"key": "aur12",  "folder": "auraliz_12",  "suffix": "_aur12.wav",  "label": "Auralizacja 12 kHz"},
    {"key": "aur8",   "folder": "auraliz_8",   "suffix": "_aur8.wav",   "label": "Auralizacja 8 kHz"},
    {"key": "aur4",   "folder": "auraliz_4",   "suffix": "_aur4.wav",   "label": "Auralizacja 4 kHz"},
    {"key": "anchor", "folder": "anchor_mono", "suffix": "_anchor.wav", "label": "Kotwica (mono)"},
]

ATTRIBUTES = [
    {"key": "barwa",         "label": "Wierność barwy",
     "desc": "Czy brzmienie (jasność, ciepło, pełnia) jest takie samo jak w referencji?"},
    {"key": "przestrzennosc", "label": "Wierność przestrzenna",
     "desc": "Czy lokalizacja źródła i otoczenie przestrzenne są takie same jak w referencji?"},
    {"key": "naturalnosc",   "label": "Naturalność",
     "desc": "Czy dźwięk brzmi naturalnie, jak prawdziwy instrument w prawdziwym pomieszczeniu?"},
]


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
                self.stream = sd.OutputStream(samplerate=sf_desc.samplerate, channels=sf_desc.channels,
                                              dtype="float32", callback=callback, blocksize=4096)
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
                    if self.stream: self.stream.close()
                except: pass
                self.stream = None
                try:
                    if self.sound_file: self.sound_file.close()
                except: pass
                self.sound_file = None
                was_stopped = self.stop_event.is_set()
                self.is_playing = False
                if (not was_stopped) and self.finished_callback:
                    self.finished_callback()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()


class ParametricTestApp:
    BG = "#f4f1ec"
    SURFACE = "#ffffff"
    SURFACE2 = "#eeebe5"
    BORDER = "#ddd5c9"
    TEXT = "#1f1d1a"
    TEXT2 = "#6f685f"
    TEXT3 = "#9d968c"
    ACCENT = "#2d6a4f"
    ACCENT_DARK = "#1b4332"
    ACCENT_BG = "#e0efe6"
    REF_BORDER = "#a4cbb1"
    TIMBRE_COLOR = "#4472C4"
    SPATIAL_COLOR = "#E97132"
    NATURAL_COLOR = "#548235"

    def __init__(self, root):
        self.root = root
        self.root.title("Test parametryczny — Barwa / Przestrzenność / Naturalność")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 750)
        self.root.configure(bg=self.BG)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.player = StreamPlayer()
        self.currently_playing_key = None

        self.participant_name = tk.StringVar()
        self.exp_level = tk.StringVar()
        self.headphone_type = tk.StringVar(value="sluchawki_zamkniete")
        self.headphone_model = tk.StringVar()
        self.debug_visible = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Gotowe")

        self.current_task_idx = 0
        self.current_stim_idx = 0

        # Losowa kolejność bodźców per zadanie
        self.randomized_stimuli = {}
        for task in TASKS:
            indices = list(range(len(STIMULI_TYPES)))
            random.shuffle(indices)
            self.randomized_stimuli[task["id"]] = indices

        # Wyniki: scores[task_id][stim_key][attr_key] = value
        self.scores = {}
        for task in TASKS:
            self.scores[task["id"]] = {}
            for st in STIMULI_TYPES:
                self.scores[task["id"]][st["key"]] = {a["key"]: 50 for a in ATTRIBUTES}

        self._setup_style()
        self._build_ui()
        self.show_intro()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_style(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except: pass
        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Accent.TButton",
                   background=[("!disabled", self.ACCENT), ("active", self.ACCENT_DARK)],
                   foreground=[("!disabled", "white")])

    def abs_path(self, rel):
        return os.path.join(self.base_dir, rel)

    def _build_ui(self):
        self.container = tk.Frame(self.root, bg=self.BG, padx=18, pady=14)
        self.container.pack(fill="both", expand=True)

        header = tk.Frame(self.container, bg=self.BG)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Test parametryczny", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(header, text="barwa · przestrzenność · naturalność", bg=self.BG, fg=self.TEXT2, font=("Consolas", 10)).pack(side="right")

        self.main = tk.Frame(self.container, bg=self.BG)
        self.main.pack(fill="both", expand=True)

        footer = tk.Frame(self.container, bg=self.BG)
        footer.pack(fill="x", pady=(6, 0))
        tk.Label(footer, textvariable=self.status_var, bg=self.BG, fg=self.TEXT2, font=("Segoe UI", 9)).pack(side="left")

        self.intro_frame = tk.Frame(self.main, bg=self.BG)
        self.test_frame = tk.Frame(self.main, bg=self.BG)
        self.results_frame = tk.Frame(self.main, bg=self.BG)

        self._build_intro()
        self._build_test()
        self._build_results()

    def _card(self, parent, title=None, pad=12, bg=None, border=None):
        bg = bg or self.SURFACE
        border = border or self.BORDER
        outer = tk.Frame(parent, bg=bg, highlightbackground=border, highlightthickness=1)
        inner = tk.Frame(outer, bg=bg, padx=pad, pady=pad)
        inner.pack(fill="both", expand=True)
        if title:
            tk.Label(inner, text=title, bg=bg, fg=self.TEXT3, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        return outer, inner

    def show_intro(self):
        self.intro_frame.pack(fill="both", expand=True)
        self.test_frame.pack_forget()
        self.results_frame.pack_forget()

    def show_test(self):
        self.intro_frame.pack_forget()
        self.test_frame.pack(fill="both", expand=True)
        self.results_frame.pack_forget()
        self.render_stimulus()

    def show_results(self):
        self.intro_frame.pack_forget()
        self.test_frame.pack_forget()
        self.results_frame.pack(fill="both", expand=True)
        self.render_results()

    def _build_intro(self):
        info_outer, info = self._card(self.intro_frame, "INSTRUKCJA", 14)
        info_outer.pack(fill="x", pady=(0, 10))
        tk.Label(info, text=(
            "Słuchasz próbki i porównujesz ją z referencją (REF). "
            "Oceniasz TRZY atrybuty osobno na skali 0–100:\n\n"
            "1. WIERNOŚĆ BARWY — czy brzmienie (jasność, ciepło, pełnia dźwięku) jest takie jak w REF?\n"
            "2. WIERNOŚĆ PRZESTRZENNA — czy lokalizacja źródła i otoczenie przestrzenne są takie jak w REF?\n"
            "3. NATURALNOŚĆ — czy dźwięk brzmi naturalnie, jak prawdziwy instrument w prawdziwym pomieszczeniu?\n\n"
            "Masz 10 zadań × 6 próbek = 60 ocen. Każda próbka to inna wersja auralizacji.\n"
            "Kolejność próbek jest losowa. Możesz wielokrotnie przełączać między REF a próbką."
        ), bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 11), wraplength=1100, justify="left").pack(anchor="w")

        form_outer, form = self._card(self.intro_frame, "DANE UCZESTNIKA", 14)
        form_outer.pack(fill="x", pady=(0, 10))
        row1 = tk.Frame(form, bg=self.SURFACE)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Imię / pseudonim *", bg=self.SURFACE, fg=self.TEXT2, width=20, anchor="w").pack(side="left")
        ttk.Entry(row1, textvariable=self.participant_name, width=30).pack(side="left", padx=(0, 16))
        tk.Label(row1, text="Doświadczenie", bg=self.SURFACE, fg=self.TEXT2, width=14, anchor="w").pack(side="left")
        ttk.Combobox(row1, textvariable=self.exp_level, width=24, state="readonly",
                     values=["", "brak", "amator", "sredniozaawansowany", "zaawansowany", "profesjonalny"]).pack(side="left")

        row2 = tk.Frame(form, bg=self.SURFACE)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Sprzęt odsłuchowy", bg=self.SURFACE, fg=self.TEXT2, width=20, anchor="w").pack(side="left")
        ttk.Combobox(row2, textvariable=self.headphone_type, width=30, state="readonly",
                     values=["sluchawki_zamkniete", "sluchawki_otwarte", "sluchawki_douszne", "glosniki"]).pack(side="left", padx=(0, 16))
        tk.Label(row2, text="Model", bg=self.SURFACE, fg=self.TEXT2, width=14, anchor="w").pack(side="left")
        ttk.Entry(row2, textvariable=self.headphone_model, width=24).pack(side="left")

        actions = tk.Frame(self.intro_frame, bg=self.BG)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Rozpocznij test", style="Accent.TButton", command=self.start_test).pack(side="left")
        tk.Label(actions, text="10 zadań × 6 próbek × 3 atrybuty · ~30–40 min", bg=self.BG, fg=self.TEXT3, font=("Segoe UI", 9)).pack(side="left", padx=16)

    def _build_test(self):
        # Progress
        top = tk.Frame(self.test_frame, bg=self.BG)
        top.pack(fill="x", pady=(0, 8))
        self.progress_label = tk.Label(top, text="", bg=self.BG, fg=self.TEXT2, font=("Consolas", 10))
        self.progress_label.pack(side="left")
        ttk.Checkbutton(top, text="Debug", variable=self.debug_visible).pack(side="right")

        # Task info
        task_outer, task_box = self._card(self.test_frame, None, 12)
        task_outer.pack(fill="x", pady=(0, 8))
        self.task_title = tk.Label(task_box, text="", bg=self.SURFACE, fg=self.TEXT, font=("Segoe UI", 14, "bold"))
        self.task_title.pack(anchor="w")
        self.task_subtitle = tk.Label(task_box, text="", bg=self.SURFACE, fg=self.TEXT2, font=("Segoe UI", 10))
        self.task_subtitle.pack(anchor="w", pady=(2, 0))

        # Audio controls
        audio_outer, audio_box = self._card(self.test_frame, None, 12, bg=self.ACCENT_BG, border=self.REF_BORDER)
        audio_outer.pack(fill="x", pady=(0, 8))
        audio_row = tk.Frame(audio_box, bg=self.ACCENT_BG)
        audio_row.pack(fill="x")
        self.ref_btn = ttk.Button(audio_row, text="▶ REF", style="Accent.TButton", command=lambda: self.toggle_audio("ref"))
        self.ref_btn.pack(side="left", padx=(0, 12))
        self.stim_btn = ttk.Button(audio_row, text="▶ PRÓBKA", command=lambda: self.toggle_audio("stim"))
        self.stim_btn.pack(side="left", padx=(0, 16))
        self.stim_label = tk.Label(audio_row, text="", bg=self.ACCENT_BG, fg=self.ACCENT_DARK, font=("Segoe UI", 11, "bold"))
        self.stim_label.pack(side="left")
        self.debug_label = tk.Label(audio_row, text="", bg=self.ACCENT_BG, fg=self.TEXT3, font=("Consolas", 9))
        self.debug_label.pack(side="right")

        # Rating sliders
        rating_outer, self.rating_box = self._card(self.test_frame, "OCENA ATRYBUTÓW (0–100)", 14)
        rating_outer.pack(fill="both", expand=True, pady=(0, 8))

        self.attr_widgets = {}
        colors = [self.TIMBRE_COLOR, self.SPATIAL_COLOR, self.NATURAL_COLOR]
        for idx, attr in enumerate(ATTRIBUTES):
            frame = tk.Frame(self.rating_box, bg=self.SURFACE, pady=10)
            frame.pack(fill="x", pady=4)

            label = tk.Label(frame, text=attr["label"], bg=self.SURFACE, fg=colors[idx],
                             font=("Segoe UI", 13, "bold"), width=24, anchor="w")
            label.pack(side="left")

            desc = tk.Label(frame, text=attr["desc"], bg=self.SURFACE, fg=self.TEXT2,
                            font=("Segoe UI", 9), wraplength=400, justify="left")
            desc.pack(side="left", padx=(0, 16))

            val_label = tk.Label(frame, text="50", bg=self.SURFACE, fg=self.TEXT,
                                 font=("Consolas", 20, "bold"), width=4)
            val_label.pack(side="right", padx=(10, 0))

            scale = tk.Scale(frame, from_=0, to=100, orient="horizontal", length=300, width=18,
                             showvalue=False, bd=0, highlightthickness=0, troughcolor="#cbc5bd",
                             bg=self.SURFACE, activebackground=colors[idx], fg=self.TEXT,
                             command=lambda v, a=attr["key"], vl=val_label: self._on_attr_slider(v, a, vl))
            scale.set(50)
            scale.pack(side="right")

            self.attr_widgets[attr["key"]] = {"scale": scale, "value_label": val_label}

        # Navigation
        nav_outer, nav = self._card(self.test_frame, None, 10)
        nav_outer.pack(fill="x")
        self.prev_stim_btn = ttk.Button(nav, text="← Poprzednia próbka", command=self.prev_stimulus)
        self.prev_stim_btn.pack(side="left")
        self.next_stim_btn = ttk.Button(nav, text="Następna próbka →", style="Accent.TButton", command=self.next_stimulus)
        self.next_stim_btn.pack(side="right")

    def _build_results(self):
        res_outer, self.res_box = self._card(self.results_frame, "WYNIKI", 12)
        res_outer.pack(fill="both", expand=True, pady=(0, 8))

        self.res_text = tk.Text(self.res_box, bg=self.SURFACE, fg=self.TEXT, font=("Consolas", 10),
                                wrap="none", state="disabled")
        self.res_text.pack(fill="both", expand=True)

        actions = tk.Frame(self.results_frame, bg=self.BG)
        actions.pack(fill="x")
        ttk.Button(actions, text="Eksportuj CSV", style="Accent.TButton", command=self.export_csv).pack(side="left")
        ttk.Button(actions, text="Nowy test", command=self.reset_test).pack(side="right")

    # ---- Logic ----

    def start_test(self):
        if not self.participant_name.get().strip():
            messagebox.showerror("Błąd", "Podaj imię lub pseudonim.")
            return
        self.current_task_idx = 0
        self.current_stim_idx = 0
        self.show_test()

    def current_task(self):
        return TASKS[self.current_task_idx]

    def current_stim_type(self):
        task = self.current_task()
        rand_idx = self.randomized_stimuli[task["id"]][self.current_stim_idx]
        return STIMULI_TYPES[rand_idx]

    def total_stimuli_done(self):
        return self.current_task_idx * len(STIMULI_TYPES) + self.current_stim_idx

    def total_stimuli(self):
        return len(TASKS) * len(STIMULI_TYPES)

    def render_stimulus(self):
        self.player.stop()
        self.currently_playing_key = None
        self.ref_btn.configure(text="▶ REF")
        self.stim_btn.configure(text="▶ PRÓBKA")

        task = self.current_task()
        stim = self.current_stim_type()

        done = self.total_stimuli_done()
        total = self.total_stimuli()
        self.progress_label.configure(text=f"Zadanie {self.current_task_idx+1}/{len(TASKS)} · Próbka {self.current_stim_idx+1}/{len(STIMULI_TYPES)} · Ogółem {done+1}/{total}")

        self.task_title.configure(text=f'{task["instrument"]} — {task["room"]}')
        self.task_subtitle.configure(text=f'Pozycja: {task["position"]}')
        self.stim_label.configure(text=f'Próbka {self.current_stim_idx + 1} z {len(STIMULI_TYPES)}')

        if self.debug_visible.get():
            self.debug_label.configure(text=f'[{stim["key"]}]')
        else:
            self.debug_label.configure(text="")

        # Load existing scores for this stimulus
        for attr in ATTRIBUTES:
            val = self.scores[task["id"]][stim["key"]][attr["key"]]
            self.attr_widgets[attr["key"]]["scale"].set(val)
            self.attr_widgets[attr["key"]]["value_label"].configure(text=str(val))

        # Navigation
        is_first = (self.current_task_idx == 0 and self.current_stim_idx == 0)
        is_last = (self.current_task_idx == len(TASKS) - 1 and self.current_stim_idx == len(STIMULI_TYPES) - 1)
        self.prev_stim_btn.configure(state="disabled" if is_first else "normal")
        self.next_stim_btn.configure(text="Zakończ i pokaż wyniki →" if is_last else "Następna próbka →")

    def _on_attr_slider(self, value, attr_key, val_label):
        v = int(round(float(value)))
        val_label.configure(text=str(v))
        task = self.current_task()
        stim = self.current_stim_type()
        self.scores[task["id"]][stim["key"]][attr_key] = v

    def toggle_audio(self, key):
        if self.currently_playing_key == key and self.player.is_playing:
            self.player.stop()
            self._reset_buttons()
            return

        self._reset_buttons()
        task = self.current_task()

        if key == "ref":
            path = self.abs_path(task["refFile"])
            self.ref_btn.configure(text="■ REF")
        else:
            stim = self.current_stim_type()
            path = self.abs_path(f'audio/{stim["folder"]}/{task["base"]}{stim["suffix"]}')
            self.stim_btn.configure(text="■ PRÓBKA")

        if not os.path.exists(path):
            messagebox.showerror("Brak pliku", path)
            self._reset_buttons()
            return

        self.currently_playing_key = key
        self.status_var.set(f"Odtwarzanie: {os.path.basename(path)}")
        self.player.play(path, finished_callback=lambda: self.root.after(0, self._reset_buttons),
                         error_callback=lambda msg: self.root.after(0, lambda: messagebox.showerror("Błąd", msg)))

    def _reset_buttons(self):
        self.ref_btn.configure(text="▶ REF")
        self.stim_btn.configure(text="▶ PRÓBKA")
        self.currently_playing_key = None
        self.status_var.set("Gotowe")

    def next_stimulus(self):
        self.player.stop()
        if self.current_stim_idx < len(STIMULI_TYPES) - 1:
            self.current_stim_idx += 1
        elif self.current_task_idx < len(TASKS) - 1:
            self.current_task_idx += 1
            self.current_stim_idx = 0
        else:
            self.show_results()
            return
        self.render_stimulus()

    def prev_stimulus(self):
        self.player.stop()
        if self.current_stim_idx > 0:
            self.current_stim_idx -= 1
        elif self.current_task_idx > 0:
            self.current_task_idx -= 1
            self.current_stim_idx = len(STIMULI_TYPES) - 1
        self.render_stimulus()

    def render_results(self):
        self.res_text.configure(state="normal")
        self.res_text.delete("1.0", "end")

        # Per-type averages
        by_type = {st["key"]: {a["key"]: [] for a in ATTRIBUTES} for st in STIMULI_TYPES}
        for task in TASKS:
            for st in STIMULI_TYPES:
                for attr in ATTRIBUTES:
                    by_type[st["key"]][attr["key"]].append(self.scores[task["id"]][st["key"]][attr["key"]])

        avg = lambda arr: round(sum(arr) / len(arr), 1) if arr else 0

        header = f"{'Wariant':<25} {'Barwa':>8} {'Przestrz.':>10} {'Natural.':>10}\n"
        self.res_text.insert("end", "ŚREDNIE PER WARIANT:\n\n")
        self.res_text.insert("end", header)
        self.res_text.insert("end", "-" * 55 + "\n")
        for st in STIMULI_TYPES:
            b = avg(by_type[st["key"]]["barwa"])
            p = avg(by_type[st["key"]]["przestrzennosc"])
            n = avg(by_type[st["key"]]["naturalnosc"])
            self.res_text.insert("end", f'{st["label"]:<25} {b:>8.1f} {p:>10.1f} {n:>10.1f}\n')

        self.res_text.insert("end", f"\nUczestnik: {self.participant_name.get().strip()}\n")
        self.res_text.configure(state="disabled")

    def export_csv(self):
        name = self.participant_name.get().strip() or "uczestnik"
        default_name = f"parametryczny_{name.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        save_path = filedialog.asksaveasfilename(title="Zapisz CSV", defaultextension=".csv",
                                                  initialfile=default_name, filetypes=[("CSV", "*.csv")])
        if not save_path:
            return

        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Uczestnik", "Doswiadczenie", "Sprzet", "Model", "Data",
                             "Zadanie", "Instrument", "Pomieszczenie", "Pozycja",
                             "Typ", "Typ_kod", "Barwa", "Przestrzennosc", "Naturalnosc"])
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for task in TASKS:
                for st in STIMULI_TYPES:
                    s = self.scores[task["id"]][st["key"]]
                    writer.writerow([name, self.exp_level.get(), self.headphone_type.get(),
                                     self.headphone_model.get(), now, task["id"], task["instrument"],
                                     task["room"], task["position"], st["label"], st["key"],
                                     s["barwa"], s["przestrzennosc"], s["naturalnosc"]])
        messagebox.showinfo("Gotowe", f"Zapisano:\n{save_path}")

    def reset_test(self):
        self.player.stop()
        self.current_task_idx = 0
        self.current_stim_idx = 0
        self.currently_playing_key = None
        for task in TASKS:
            for st in STIMULI_TYPES:
                self.scores[task["id"]][st["key"]] = {a["key"]: 50 for a in ATTRIBUTES}
        for task in TASKS:
            indices = list(range(len(STIMULI_TYPES)))
            random.shuffle(indices)
            self.randomized_stimuli[task["id"]] = indices
        self.show_intro()

    def on_close(self):
        self.player.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ParametricTestApp(root)
    root.mainloop()