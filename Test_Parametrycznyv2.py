"""
Test parametryczny (atrybutowy) v2.
Barwa / Przestrzenność / Naturalność — 3 suwaki per próbka.
Fix: seek bez restartu strumienia, kompaktowe UI.
6 bodźców × 10 zadań × 3 atrybuty = 180 wartości na słuchacza.
"""

import csv, os, random, threading
from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sounddevice as sd
import soundfile as sf

TASKS = [
    {"id":1,"instrument":"Gitara klasyczna","room":"Korytarz ZEA","position":"Na wprost",
     "refFile":"audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav","base":"test01_gitara_klasyczna_korytarz_wprost"},
    {"id":2,"instrument":"Gitara klasyczna","room":"Sala 123","position":"Prawe ucho",
     "refFile":"audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav","base":"test02_gitara_klasyczna_sala123_praweucho"},
    {"id":3,"instrument":"Kontrabas palcami","room":"Korytarz ZEA","position":"Na wprost",
     "refFile":"audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav","base":"test03_kontrabas_palce_korytarz_wprost"},
    {"id":4,"instrument":"Kontrabas palcami","room":"Studio","position":"Na wprost",
     "refFile":"audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav","base":"test04_kontrabas_palce_studio_wprost"},
    {"id":5,"instrument":"Kontrabas smyczkiem","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav","base":"test05_kontrabas_smyczek_studio_leweucho"},
    {"id":6,"instrument":"Wiolonczela","room":"Korytarz ZEA","position":"Na wprost",
     "refFile":"audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav","base":"test06_wiolonczela_korytarz_wprost"},
    {"id":7,"instrument":"Wiolonczela","room":"Sala 123","position":"Oddalone",
     "refFile":"audio/ref/test07_wiolonczela_sala123_daleko_ref.wav","base":"test07_wiolonczela_sala123_daleko"},
    {"id":8,"instrument":"Flet","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test08_flet_studio_leweucho_ref.wav","base":"test08_flet_studio_leweucho"},
    {"id":9,"instrument":"Saksofon","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test09_saksofon_studio_leweucho_ref.wav","base":"test09_saksofon_studio_leweucho"},
    {"id":10,"instrument":"Akordeon","room":"Korytarz ZEA","position":"Oddalone",
     "refFile":"audio/ref/test10_akordeon_korytarz_daleko_ref.wav","base":"test10_akordeon_korytarz_daleko"},
]

STIMULI = [
    {"key":"aur48","folder":"auraliz_48","suffix":"_aur48.wav","label":"Auralizacja 48 kHz"},
    {"key":"aur24","folder":"auraliz_24","suffix":"_aur24.wav","label":"Auralizacja 24 kHz"},
    {"key":"aur12","folder":"auraliz_12","suffix":"_aur12.wav","label":"Auralizacja 12 kHz"},
    {"key":"aur8","folder":"auraliz_8","suffix":"_aur8.wav","label":"Auralizacja 8 kHz"},
    {"key":"aur4","folder":"auraliz_4","suffix":"_aur4.wav","label":"Auralizacja 4 kHz"},
    {"key":"anchor","folder":"anchor_mono","suffix":"_anchor.wav","label":"Kotwica (mono)"},
]

ATTRS = [
    {"key":"barwa","label":"Wierność barwy","desc":"Czy brzmienie jest takie samo jak w REF?","color":"#4472C4"},
    {"key":"przestrzennosc","label":"Wierność przestrzenna","desc":"Czy lokalizacja i otoczenie są takie jak w REF?","color":"#E97132"},
    {"key":"naturalnosc","label":"Naturalność","desc":"Czy brzmi jak prawdziwy instrument w pomieszczeniu?","color":"#548235"},
]


class StreamPlayer:
    def __init__(self):
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.stream = None
        self.sound_file = None
        self.thread = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.samplerate = 48000
        self.finished_callback = None
        self._closing = False

    def stop(self):
        self._closing = True
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        with self._file_lock:
            try:
                if self.stream: self.stream.close()
            except: pass
            self.stream = None
            try:
                if self.sound_file: self.sound_file.close()
            except: pass
            self.sound_file = None
        self.is_playing = False
        self._closing = False

    @property
    def position_seconds(self):
        with self._lock:
            return self.current_frame / self.samplerate if self.samplerate > 0 else 0

    @property
    def duration_seconds(self):
        return self.total_frames / self.samplerate if self.samplerate > 0 else 0

    def seek(self, seconds):
        with self._file_lock:
            if self.sound_file and not self.sound_file.closed:
                frame = max(0, min(int(seconds * self.samplerate), self.total_frames - 1))
                try:
                    self.sound_file.seek(frame)
                    with self._lock:
                        self.current_frame = frame
                except: pass

    def play(self, filepath, finished_callback=None, start_seconds=0):
        self.stop()
        self.stop_event.clear()
        self.finished_callback = finished_callback

        def worker():
            sf_desc = None; stream = None
            try:
                sf_desc = sf.SoundFile(filepath, mode="r")
                with self._file_lock:
                    self.sound_file = sf_desc
                self.samplerate = sf_desc.samplerate
                self.total_frames = sf_desc.frames
                if start_seconds > 0:
                    sf_desc.seek(int(start_seconds * sf_desc.samplerate))
                    with self._lock: self.current_frame = int(start_seconds * sf_desc.samplerate)
                else:
                    with self._lock: self.current_frame = 0

                def callback(outdata, frames, time_info, status):
                    if self.stop_event.is_set() or self._closing:
                        outdata.fill(0); raise sd.CallbackStop()
                    try:
                        with self._file_lock:
                            if sf_desc.closed: outdata.fill(0); raise sd.CallbackStop()
                            data = sf_desc.read(frames, dtype="float32", always_2d=True)
                    except Exception:
                        outdata.fill(0); raise sd.CallbackStop()
                    with self._lock: self.current_frame += len(data)
                    if len(data) == 0: outdata.fill(0); raise sd.CallbackStop()
                    elif len(data) < frames:
                        outdata[:len(data)] = data; outdata[len(data):].fill(0); raise sd.CallbackStop()
                    else: outdata[:] = data

                stream = sd.OutputStream(samplerate=sf_desc.samplerate, channels=sf_desc.channels,
                                         dtype="float32", callback=callback, blocksize=4096)
                with self._file_lock: self.stream = stream
                self.is_playing = True; stream.start()
                while stream.active and not self.stop_event.is_set(): sd.sleep(50)
            except: pass
            finally:
                self.is_playing = False
                try:
                    if stream: stream.close()
                except: pass
                with self._file_lock:
                    self.stream = None
                    try:
                        if sf_desc and not sf_desc.closed: sf_desc.close()
                    except: pass
                    self.sound_file = None
                if not self.stop_event.is_set() and self.finished_callback:
                    self.finished_callback()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()


class ParametricApp:
    BG="#f4f1ec"; SF="#ffffff"; SF2="#eeebe5"; BD="#ddd5c9"
    TX="#1f1d1a"; TX2="#6f685f"; TX3="#9d968c"
    AC="#2d6a4f"; ACD="#1b4332"; AB="#e0efe6"; RB="#a4cbb1"

    def __init__(self, root):
        self.root = root
        self.root.title("Test parametryczny — Barwa / Przestrzenność / Naturalność")
        self.root.geometry("1200x820")
        self.root.minsize(1000, 720)
        self.root.configure(bg=self.BG)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.player = StreamPlayer()
        self.playing_key = None
        self.seek_dragging = False

        self.participant_name = tk.StringVar()
        self.exp_level = tk.StringVar()
        self.headphone_type = tk.StringVar(value="sluchawki_zamkniete")
        self.headphone_model = tk.StringVar()
        self.debug_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Gotowe")

        self.task_idx = 0
        self.stim_idx = 0

        self.rand_stim = {}
        for t in TASKS:
            idx = list(range(len(STIMULI))); random.shuffle(idx)
            self.rand_stim[t["id"]] = idx

        self.scores = {}
        for t in TASKS:
            self.scores[t["id"]] = {}
            for s in STIMULI:
                self.scores[t["id"]][s["key"]] = {a["key"]: 50 for a in ATTRS}

        self._setup_style()
        self._build()
        self.show_intro()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick()

    def _setup_style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except: pass
        s.configure("TFrame", background=self.BG)
        s.configure("TLabel", background=self.BG, foreground=self.TX, font=("Segoe UI",10))
        s.configure("Accent.TButton", font=("Segoe UI",10,"bold"), padding=8)
        s.map("Accent.TButton", background=[("!disabled",self.AC),("active",self.ACD)], foreground=[("!disabled","white")])

    def abs_path(self, r): return os.path.join(self.base_dir, r)

    def _card(self, parent, title=None, pad=10, bg=None, border=None):
        bg=bg or self.SF; border=border or self.BD
        outer=tk.Frame(parent,bg=bg,highlightbackground=border,highlightthickness=1)
        inner=tk.Frame(outer,bg=bg,padx=pad,pady=pad); inner.pack(fill="both",expand=True)
        if title: tk.Label(inner,text=title,bg=bg,fg=self.TX3,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(0,6))
        return outer, inner

    def _build(self):
        self.container=tk.Frame(self.root,bg=self.BG,padx=14,pady=10); self.container.pack(fill="both",expand=True)
        hdr=tk.Frame(self.container,bg=self.BG); hdr.pack(fill="x",pady=(0,8))
        tk.Label(hdr,text="Test parametryczny",bg=self.BG,fg=self.TX,font=("Segoe UI",18,"bold")).pack(side="left")
        tk.Label(hdr,text="barwa · przestrzenność · naturalność",bg=self.BG,fg=self.TX2,font=("Consolas",9)).pack(side="right")
        self.main=tk.Frame(self.container,bg=self.BG); self.main.pack(fill="both",expand=True)
        ftr=tk.Frame(self.container,bg=self.BG); ftr.pack(fill="x",pady=(4,0))
        tk.Label(ftr,textvariable=self.status_var,bg=self.BG,fg=self.TX2,font=("Segoe UI",9)).pack(side="left")
        self.intro_frame=tk.Frame(self.main,bg=self.BG)
        self.test_frame=tk.Frame(self.main,bg=self.BG)
        self.results_frame=tk.Frame(self.main,bg=self.BG)
        self._build_intro(); self._build_test(); self._build_results()

    def clear(self):
        for f in (self.intro_frame,self.test_frame,self.results_frame): f.pack_forget()
    def show_intro(self): self.clear(); self.intro_frame.pack(fill="both",expand=True)
    def show_test(self): self.clear(); self.test_frame.pack(fill="both",expand=True); self.render_stim()
    def show_results(self): self.clear(); self.results_frame.pack(fill="both",expand=True); self.render_results()

    # ---- INTRO ----
    def _build_intro(self):
        io,i=self._card(self.intro_frame,"INSTRUKCJA",12); io.pack(fill="x",pady=(0,8))
        tk.Label(i,text=(
            "Słuchasz próbki i porównujesz z referencją (REF). Oceniasz TRZY atrybuty osobno (0–100):\n\n"
            "1. WIERNOŚĆ BARWY — czy brzmienie jest takie jak w REF?\n"
            "2. WIERNOŚĆ PRZESTRZENNA — czy lokalizacja źródła i otoczenie są takie jak w REF?\n"
            "3. NATURALNOŚĆ — czy brzmi jak prawdziwy instrument w prawdziwym pomieszczeniu?\n\n"
            "10 zadań × 6 próbek = 60 ocen. Kolejność losowa. Użyj słuchawek!"
        ),bg=self.SF,fg=self.TX2,font=("Segoe UI",10),wraplength=1100,justify="left").pack(anchor="w")

        fo,f=self._card(self.intro_frame,"DANE UCZESTNIKA",12); fo.pack(fill="x",pady=(0,8))
        r1=tk.Frame(f,bg=self.SF); r1.pack(fill="x",pady=3)
        tk.Label(r1,text="Imię/pseudonim *",bg=self.SF,fg=self.TX2,width=18,anchor="w").pack(side="left")
        ttk.Entry(r1,textvariable=self.participant_name,width=28).pack(side="left",padx=(0,12))
        tk.Label(r1,text="Doświadczenie",bg=self.SF,fg=self.TX2,width=12,anchor="w").pack(side="left")
        ttk.Combobox(r1,textvariable=self.exp_level,width=22,state="readonly",
                     values=["","brak","amator","sredniozaawansowany","zaawansowany","profesjonalny"]).pack(side="left")
        r2=tk.Frame(f,bg=self.SF); r2.pack(fill="x",pady=3)
        tk.Label(r2,text="Sprzęt",bg=self.SF,fg=self.TX2,width=18,anchor="w").pack(side="left")
        ttk.Combobox(r2,textvariable=self.headphone_type,width=28,state="readonly",
                     values=["sluchawki_zamkniete","sluchawki_otwarte","sluchawki_douszne","glosniki"]).pack(side="left",padx=(0,12))
        tk.Label(r2,text="Model",bg=self.SF,fg=self.TX2,width=12,anchor="w").pack(side="left")
        ttk.Entry(r2,textvariable=self.headphone_model,width=22).pack(side="left")

        a=tk.Frame(self.intro_frame,bg=self.BG); a.pack(fill="x",pady=(6,0))
        ttk.Button(a,text="Rozpocznij test",style="Accent.TButton",command=self.start_test).pack(side="left")
        tk.Label(a,text="10 zadań × 6 próbek × 3 atrybuty · ~30–40 min",bg=self.BG,fg=self.TX3,font=("Segoe UI",8)).pack(side="left",padx=12)

    # ---- TEST ----
    def _build_test(self):
        top=tk.Frame(self.test_frame,bg=self.BG); top.pack(fill="x",pady=(0,6))
        self.prog_lbl=tk.Label(top,text="",bg=self.BG,fg=self.TX2,font=("Consolas",9)); self.prog_lbl.pack(side="left")
        ttk.Checkbutton(top,text="Debug",variable=self.debug_var).pack(side="right")

        to,tb=self._card(self.test_frame,None,10); to.pack(fill="x",pady=(0,6))
        self.task_title=tk.Label(tb,text="",bg=self.SF,fg=self.TX,font=("Segoe UI",13,"bold")); self.task_title.pack(anchor="w")
        self.task_sub=tk.Label(tb,text="",bg=self.SF,fg=self.TX2,font=("Segoe UI",9)); self.task_sub.pack(anchor="w")

        # Audio + seek
        ao,ab=self._card(self.test_frame,None,10,bg=self.AB,border=self.RB); ao.pack(fill="x",pady=(0,6))
        ar=tk.Frame(ab,bg=self.AB); ar.pack(fill="x")
        self.ref_btn=ttk.Button(ar,text="▶ REF",style="Accent.TButton",command=lambda:self.toggle("ref")); self.ref_btn.pack(side="left",padx=(0,8))
        self.stim_btn=ttk.Button(ar,text="▶ PRÓBKA",command=lambda:self.toggle("stim")); self.stim_btn.pack(side="left",padx=(0,12))
        self.stim_lbl=tk.Label(ar,text="",bg=self.AB,fg=self.ACD,font=("Segoe UI",10,"bold")); self.stim_lbl.pack(side="left")
        self.debug_lbl=tk.Label(ar,text="",bg=self.AB,fg=self.TX3,font=("Consolas",8)); self.debug_lbl.pack(side="right")

        sf_=tk.Frame(ab,bg=self.AB); sf_.pack(fill="x",pady=(6,0))
        self.seek_time=tk.Label(sf_,text="0:00",bg=self.AB,fg=self.TX2,font=("Consolas",8),width=5); self.seek_time.pack(side="left")
        self.seek_var=tk.DoubleVar(value=0)
        self.seek_scale=tk.Scale(sf_,from_=0,to=1000,orient="horizontal",variable=self.seek_var,
                                  showvalue=False,width=10,bd=0,highlightthickness=0,
                                  troughcolor="#d5e8dd",bg=self.AB,activebackground=self.AC)
        self.seek_scale.pack(side="left",fill="x",expand=True,padx=4)
        self.seek_scale.bind("<ButtonPress-1>",lambda e:setattr(self,'seek_dragging',True))
        self.seek_scale.bind("<ButtonRelease-1>",self._on_seek_release)
        self.seek_dur=tk.Label(sf_,text="0:00",bg=self.AB,fg=self.TX2,font=("Consolas",8),width=5); self.seek_dur.pack(side="right")

        # Atrybuty
        ro,self.rating_box=self._card(self.test_frame,"OCENA ATRYBUTÓW (0–100)",12); ro.pack(fill="both",expand=True,pady=(0,6))
        self.attr_widgets = {}
        for attr in ATTRS:
            fr=tk.Frame(self.rating_box,bg=self.SF,pady=8); fr.pack(fill="x",pady=3)
            tk.Label(fr,text=attr["label"],bg=self.SF,fg=attr["color"],
                     font=("Segoe UI",12,"bold"),width=22,anchor="w").pack(side="left")
            tk.Label(fr,text=attr["desc"],bg=self.SF,fg=self.TX2,
                     font=("Segoe UI",8),wraplength=350,justify="left").pack(side="left",padx=(0,12))
            vl=tk.Label(fr,text="50",bg=self.SF,fg=self.TX,font=("Consolas",18,"bold"),width=4); vl.pack(side="right",padx=(8,0))
            sc=tk.Scale(fr,from_=0,to=100,orient="horizontal",length=280,width=16,
                        showvalue=False,bd=0,highlightthickness=0,troughcolor="#cbc5bd",
                        bg=self.SF,activebackground=attr["color"],
                        command=lambda v,a=attr["key"],vl_=vl:self._on_attr(v,a,vl_))
            sc.set(50); sc.pack(side="right")
            self.attr_widgets[attr["key"]] = {"scale":sc,"vl":vl}

        # Nav
        no,nb=self._card(self.test_frame,None,8); no.pack(fill="x")
        self.prev_btn=ttk.Button(nb,text="← Poprzednia",command=self.prev_stim); self.prev_btn.pack(side="left")
        self.next_btn=ttk.Button(nb,text="Następna →",style="Accent.TButton",command=self.next_stim); self.next_btn.pack(side="right")

    # ---- RESULTS ----
    def _build_results(self):
        ro,rb=self._card(self.results_frame,"WYNIKI",10); ro.pack(fill="both",expand=True,pady=(0,6))
        self.res_text=tk.Text(rb,bg=self.SF,fg=self.TX,font=("Consolas",10),wrap="none",state="disabled",height=18)
        self.res_text.pack(fill="both",expand=True)
        a=tk.Frame(self.results_frame,bg=self.BG); a.pack(fill="x")
        ttk.Button(a,text="Eksportuj CSV",style="Accent.TButton",command=self.export_csv).pack(side="left")
        ttk.Button(a,text="Nowy test",command=self.reset).pack(side="right")

    # ---- SEEK ----
    def _on_seek_release(self, event):
        self.seek_dragging = False
        if self.player.is_playing:
            dur = self.player.duration_seconds
            if dur > 0:
                self.player.seek((self.seek_var.get() / 1000.0) * dur)

    def _tick(self):
        if self.player.is_playing and not self.seek_dragging:
            pos = self.player.position_seconds
            dur = self.player.duration_seconds
            if dur > 0:
                self.seek_var.set((pos/dur)*1000)
                self.seek_time.configure(text=f"{int(pos)//60}:{int(pos)%60:02d}")
                self.seek_dur.configure(text=f"{int(dur)//60}:{int(dur)%60:02d}")
        self.root.after(100, self._tick)

    # ---- AUDIO ----
    def _reset_btns(self):
        self.ref_btn.configure(text="▶ REF"); self.stim_btn.configure(text="▶ PRÓBKA")
        self.playing_key = None; self.status_var.set("Gotowe")

    def toggle(self, key):
        if self.playing_key == key and self.player.is_playing:
            self.player.stop(); self._reset_btns(); return
        self._reset_btns()
        task = TASKS[self.task_idx]
        if key == "ref":
            path = self.abs_path(task["refFile"]); self.ref_btn.configure(text="■ REF")
        else:
            stim = STIMULI[self.rand_stim[task["id"]][self.stim_idx]]
            path = self.abs_path(f'audio/{stim["folder"]}/{task["base"]}{stim["suffix"]}')
            self.stim_btn.configure(text="■ PRÓBKA")
        if not os.path.exists(path):
            messagebox.showerror("Brak pliku",path); self._reset_btns(); return
        self.playing_key = key; self.seek_var.set(0)
        self.status_var.set(f"▶ {os.path.basename(path)}")
        self.player.play(path, finished_callback=lambda:self.root.after(0,self._reset_btns))

    # ---- LOGIC ----
    def start_test(self):
        if not self.participant_name.get().strip(): messagebox.showerror("Błąd","Podaj imię."); return
        self.task_idx=0; self.stim_idx=0; self.show_test()

    def cur_stim(self):
        return STIMULI[self.rand_stim[TASKS[self.task_idx]["id"]][self.stim_idx]]

    def _on_attr(self, v, attr_key, vl):
        v=int(round(float(v))); vl.configure(text=str(v))
        t=TASKS[self.task_idx]; s=self.cur_stim()
        self.scores[t["id"]][s["key"]][attr_key]=v

    def render_stim(self):
        self.player.stop(); self._reset_btns()
        task=TASKS[self.task_idx]; stim=self.cur_stim()
        done=self.task_idx*len(STIMULI)+self.stim_idx
        total=len(TASKS)*len(STIMULI)
        self.prog_lbl.configure(text=f"Zadanie {self.task_idx+1}/{len(TASKS)} · Próbka {self.stim_idx+1}/{len(STIMULI)} · Ogółem {done+1}/{total}")
        self.task_title.configure(text=f'{task["instrument"]} — {task["room"]}')
        self.task_sub.configure(text=f'Pozycja: {task["position"]}')
        self.stim_lbl.configure(text=f'Próbka {self.stim_idx+1} z {len(STIMULI)}')
        self.debug_lbl.configure(text=f'[{stim["key"]}]' if self.debug_var.get() else "")

        for attr in ATTRS:
            val=self.scores[task["id"]][stim["key"]][attr["key"]]
            self.attr_widgets[attr["key"]]["scale"].set(val)
            self.attr_widgets[attr["key"]]["vl"].configure(text=str(val))

        is_first=(self.task_idx==0 and self.stim_idx==0)
        is_last=(self.task_idx==len(TASKS)-1 and self.stim_idx==len(STIMULI)-1)
        self.prev_btn.configure(state="disabled" if is_first else "normal")
        self.next_btn.configure(text="Zakończ →" if is_last else "Następna →")

    def next_stim(self):
        self.player.stop()
        if self.stim_idx<len(STIMULI)-1: self.stim_idx+=1
        elif self.task_idx<len(TASKS)-1: self.task_idx+=1; self.stim_idx=0
        else: self.show_results(); return
        self.render_stim()

    def prev_stim(self):
        self.player.stop()
        if self.stim_idx>0: self.stim_idx-=1
        elif self.task_idx>0: self.task_idx-=1; self.stim_idx=len(STIMULI)-1
        self.render_stim()

    # ---- RESULTS ----
    def render_results(self):
        self.res_text.configure(state="normal"); self.res_text.delete("1.0","end")
        by_type={s["key"]:{a["key"]:[] for a in ATTRS} for s in STIMULI}
        for t in TASKS:
            for s in STIMULI:
                for a in ATTRS:
                    by_type[s["key"]][a["key"]].append(self.scores[t["id"]][s["key"]][a["key"]])
        avg=lambda arr:round(sum(arr)/len(arr),1) if arr else 0
        self.res_text.insert("end","ŚREDNIE PER WARIANT:\n\n")
        self.res_text.insert("end",f"{'Wariant':<25} {'Barwa':>8} {'Przestrz.':>10} {'Natural.':>10}\n")
        self.res_text.insert("end","-"*55+"\n")
        for s in STIMULI:
            b=avg(by_type[s["key"]]["barwa"]); p=avg(by_type[s["key"]]["przestrzennosc"]); n=avg(by_type[s["key"]]["naturalnosc"])
            self.res_text.insert("end",f'{s["label"]:<25} {b:>8.1f} {p:>10.1f} {n:>10.1f}\n')
        self.res_text.insert("end",f"\nUczestnik: {self.participant_name.get().strip()}\n")
        self.res_text.configure(state="disabled")

    def export_csv(self):
        name=self.participant_name.get().strip() or "uczestnik"
        p=filedialog.asksaveasfilename(title="Zapisz CSV",defaultextension=".csv",
            initialfile=f"parametryczny_{name.replace(' ','_')}_{datetime.now().strftime('%Y-%m-%d')}.csv",
            filetypes=[("CSV","*.csv")])
        if not p: return
        with open(p,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument",
                         "Pomieszczenie","Pozycja","Typ","Typ_kod","Barwa","Przestrzennosc","Naturalnosc"])
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for t in TASKS:
                for s in STIMULI:
                    sc=self.scores[t["id"]][s["key"]]
                    w.writerow([name,self.exp_level.get(),self.headphone_type.get(),self.headphone_model.get(),
                                now,t["id"],t["instrument"],t["room"],t["position"],
                                s["label"],s["key"],sc["barwa"],sc["przestrzennosc"],sc["naturalnosc"]])
        messagebox.showinfo("Gotowe",f"Zapisano:\n{p}")

    def reset(self):
        self.player.stop(); self.task_idx=0; self.stim_idx=0; self.playing_key=None
        for t in TASKS:
            for s in STIMULI: self.scores[t["id"]][s["key"]]={a["key"]:50 for a in ATTRS}
            idx=list(range(len(STIMULI))); random.shuffle(idx); self.rand_stim[t["id"]]=idx
        self.show_intro()

    def on_close(self): self.player.stop(); self.root.destroy()


if __name__=="__main__":
    root=tk.Tk(); ParametricApp(root); root.mainloop()