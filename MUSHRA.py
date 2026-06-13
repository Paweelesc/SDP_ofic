"""
Test MUSHRA (ITU-R BS.1534) — v5.
Fix: seek bez restartu strumienia (brak race condition).
Fix: kompaktowe UI dla 7 kolumn.
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
     "refFile":"audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test01_gitara_klasyczna_korytarz_wprost_aur48.wav","aur24":"audio/auraliz_24/test01_gitara_klasyczna_korytarz_wprost_aur24.wav","aur12":"audio/auraliz_12/test01_gitara_klasyczna_korytarz_wprost_aur12.wav","aur8":"audio/auraliz_8/test01_gitara_klasyczna_korytarz_wprost_aur8.wav","aur4":"audio/auraliz_4/test01_gitara_klasyczna_korytarz_wprost_aur4.wav","hidden_ref":"audio/ref/test01_gitara_klasyczna_korytarz_wprost_ref.wav","anchor":"audio/anchor_mono/test01_gitara_klasyczna_korytarz_wprost_anchor.wav"}},
    {"id":2,"instrument":"Gitara klasyczna","room":"Sala 123","position":"Prawe ucho",
     "refFile":"audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test02_gitara_klasyczna_sala123_praweucho_aur48.wav","aur24":"audio/auraliz_24/test02_gitara_klasyczna_sala123_praweucho_aur24.wav","aur12":"audio/auraliz_12/test02_gitara_klasyczna_sala123_praweucho_aur12.wav","aur8":"audio/auraliz_8/test02_gitara_klasyczna_sala123_praweucho_aur8.wav","aur4":"audio/auraliz_4/test02_gitara_klasyczna_sala123_praweucho_aur4.wav","hidden_ref":"audio/ref/test02_gitara_klasyczna_sala123_praweucho_ref.wav","anchor":"audio/anchor_mono/test02_gitara_klasyczna_sala123_praweucho_anchor.wav"}},
    {"id":3,"instrument":"Kontrabas palcami","room":"Korytarz ZEA","position":"Na wprost",
     "refFile":"audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test03_kontrabas_palce_korytarz_wprost_aur48.wav","aur24":"audio/auraliz_24/test03_kontrabas_palce_korytarz_wprost_aur24.wav","aur12":"audio/auraliz_12/test03_kontrabas_palce_korytarz_wprost_aur12.wav","aur8":"audio/auraliz_8/test03_kontrabas_palce_korytarz_wprost_aur8.wav","aur4":"audio/auraliz_4/test03_kontrabas_palce_korytarz_wprost_aur4.wav","hidden_ref":"audio/ref/test03_kontrabas_palce_korytarz_wprost_ref.wav","anchor":"audio/anchor_mono/test03_kontrabas_palce_korytarz_wprost_anchor.wav"}},
    {"id":4,"instrument":"Kontrabas palcami","room":"Studio","position":"Na wprost",
     "refFile":"audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test04_kontrabas_palce_studio_wprost_aur48.wav","aur24":"audio/auraliz_24/test04_kontrabas_palce_studio_wprost_aur24.wav","aur12":"audio/auraliz_12/test04_kontrabas_palce_studio_wprost_aur12.wav","aur8":"audio/auraliz_8/test04_kontrabas_palce_studio_wprost_aur8.wav","aur4":"audio/auraliz_4/test04_kontrabas_palce_studio_wprost_aur4.wav","hidden_ref":"audio/ref/test04_kontrabas_palce_studio_wprost_ref.wav","anchor":"audio/anchor_mono/test04_kontrabas_palce_studio_wprost_anchor.wav"}},
    {"id":5,"instrument":"Kontrabas smyczkiem","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test05_kontrabas_smyczek_studio_leweucho_aur48.wav","aur24":"audio/auraliz_24/test05_kontrabas_smyczek_studio_leweucho_aur24.wav","aur12":"audio/auraliz_12/test05_kontrabas_smyczek_studio_leweucho_aur12.wav","aur8":"audio/auraliz_8/test05_kontrabas_smyczek_studio_leweucho_aur8.wav","aur4":"audio/auraliz_4/test05_kontrabas_smyczek_studio_leweucho_aur4.wav","hidden_ref":"audio/ref/test05_kontrabas_smyczek_studio_leweucho_ref.wav","anchor":"audio/anchor_mono/test05_kontrabas_smyczek_studio_leweucho_anchor.wav"}},
    {"id":6,"instrument":"Wiolonczela","room":"Korytarz ZEA","position":"Na wprost",
     "refFile":"audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test06_wiolonczela_korytarz_wprost_aur48.wav","aur24":"audio/auraliz_24/test06_wiolonczela_korytarz_wprost_aur24.wav","aur12":"audio/auraliz_12/test06_wiolonczela_korytarz_wprost_aur12.wav","aur8":"audio/auraliz_8/test06_wiolonczela_korytarz_wprost_aur8.wav","aur4":"audio/auraliz_4/test06_wiolonczela_korytarz_wprost_aur4.wav","hidden_ref":"audio/ref/test06_wiolonczela_korytarz_wprost_ref.wav","anchor":"audio/anchor_mono/test06_wiolonczela_korytarz_wprost_anchor.wav"}},
    {"id":7,"instrument":"Wiolonczela","room":"Sala 123","position":"Oddalone",
     "refFile":"audio/ref/test07_wiolonczela_sala123_daleko_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test07_wiolonczela_sala123_daleko_aur48.wav","aur24":"audio/auraliz_24/test07_wiolonczela_sala123_daleko_aur24.wav","aur12":"audio/auraliz_12/test07_wiolonczela_sala123_daleko_aur12.wav","aur8":"audio/auraliz_8/test07_wiolonczela_sala123_daleko_aur8.wav","aur4":"audio/auraliz_4/test07_wiolonczela_sala123_daleko_aur4.wav","hidden_ref":"audio/ref/test07_wiolonczela_sala123_daleko_ref.wav","anchor":"audio/anchor_mono/test07_wiolonczela_sala123_daleko_anchor.wav"}},
    {"id":8,"instrument":"Flet","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test08_flet_studio_leweucho_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test08_flet_studio_leweucho_aur48.wav","aur24":"audio/auraliz_24/test08_flet_studio_leweucho_aur24.wav","aur12":"audio/auraliz_12/test08_flet_studio_leweucho_aur12.wav","aur8":"audio/auraliz_8/test08_flet_studio_leweucho_aur8.wav","aur4":"audio/auraliz_4/test08_flet_studio_leweucho_aur4.wav","hidden_ref":"audio/ref/test08_flet_studio_leweucho_ref.wav","anchor":"audio/anchor_mono/test08_flet_studio_leweucho_anchor.wav"}},
    {"id":9,"instrument":"Saksofon","room":"Studio","position":"Lewe ucho",
     "refFile":"audio/ref/test09_saksofon_studio_leweucho_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test09_saksofon_studio_leweucho_aur48.wav","aur24":"audio/auraliz_24/test09_saksofon_studio_leweucho_aur24.wav","aur12":"audio/auraliz_12/test09_saksofon_studio_leweucho_aur12.wav","aur8":"audio/auraliz_8/test09_saksofon_studio_leweucho_aur8.wav","aur4":"audio/auraliz_4/test09_saksofon_studio_leweucho_aur4.wav","hidden_ref":"audio/ref/test09_saksofon_studio_leweucho_ref.wav","anchor":"audio/anchor_mono/test09_saksofon_studio_leweucho_anchor.wav"}},
    {"id":10,"instrument":"Akordeon","room":"Korytarz ZEA","position":"Oddalone",
     "refFile":"audio/ref/test10_akordeon_korytarz_daleko_ref.wav",
     "stimuli":{"aur48":"audio/auraliz_48/test10_akordeon_korytarz_daleko_aur48.wav","aur24":"audio/auraliz_24/test10_akordeon_korytarz_daleko_aur24.wav","aur12":"audio/auraliz_12/test10_akordeon_korytarz_daleko_aur12.wav","aur8":"audio/auraliz_8/test10_akordeon_korytarz_daleko_aur8.wav","aur4":"audio/auraliz_4/test10_akordeon_korytarz_daleko_aur4.wav","hidden_ref":"audio/ref/test10_akordeon_korytarz_daleko_ref.wav","anchor":"audio/anchor_mono/test10_akordeon_korytarz_daleko_anchor.wav"}},
]

TYPE_LABELS = {"aur48":"Auralizacja 48 kHz","aur24":"Auralizacja 24 kHz","aur12":"Auralizacja 12 kHz",
               "aur8":"Auralizacja 8 kHz","aur4":"Auralizacja 4 kHz","hidden_ref":"Ukryta referencja","anchor":"Kotwica (mono)"}
SAMPLE_LETTERS = ["A","B","C","D","E","F","G"]

@dataclass
class SampleEntry:
    letter: str; sample_type: str; file: str


class StreamPlayer:
    """Odtwarzacz z seekowaniem BEZ restartu strumienia — nie ma race condition."""

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
        # Czekaj aż wątek się zakończy
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
        """Seek BEZ restartu — przesuwa pozycję w otwartym pliku."""
        with self._file_lock:
            if self.sound_file and not self.sound_file.closed:
                frame = int(seconds * self.samplerate)
                frame = max(0, min(frame, self.total_frames - 1))
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
            sf_desc = None
            stream = None
            try:
                sf_desc = sf.SoundFile(filepath, mode="r")
                with self._file_lock:
                    self.sound_file = sf_desc
                self.samplerate = sf_desc.samplerate
                self.total_frames = sf_desc.frames

                if start_seconds > 0:
                    sf_desc.seek(int(start_seconds * sf_desc.samplerate))
                    with self._lock:
                        self.current_frame = int(start_seconds * sf_desc.samplerate)
                else:
                    with self._lock:
                        self.current_frame = 0

                def callback(outdata, frames, time_info, status):
                    if self.stop_event.is_set() or self._closing:
                        outdata.fill(0)
                        raise sd.CallbackStop()
                    try:
                        with self._file_lock:
                            if sf_desc.closed:
                                outdata.fill(0)
                                raise sd.CallbackStop()
                            data = sf_desc.read(frames, dtype="float32", always_2d=True)
                    except Exception:
                        outdata.fill(0)
                        raise sd.CallbackStop()

                    with self._lock:
                        self.current_frame += len(data)

                    if len(data) == 0:
                        outdata.fill(0)
                        raise sd.CallbackStop()
                    elif len(data) < frames:
                        outdata[:len(data)] = data
                        outdata[len(data):].fill(0)
                        raise sd.CallbackStop()
                    else:
                        outdata[:] = data

                stream = sd.OutputStream(
                    samplerate=sf_desc.samplerate, channels=sf_desc.channels,
                    dtype="float32", callback=callback, blocksize=4096)
                with self._file_lock:
                    self.stream = stream
                self.is_playing = True
                stream.start()
                while stream.active and not self.stop_event.is_set():
                    sd.sleep(50)
            except Exception:
                pass
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
                was_stopped = self.stop_event.is_set()
                if not was_stopped and self.finished_callback:
                    self.finished_callback()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()


class MushraApp:
    BG="#f7f4ef"; SF="#ffffff"; SF2="#f2eee8"; BD="#ddd5c9"
    TX="#1f1d1a"; TX2="#6f685f"; TX3="#9d968c"
    AC="#b2552f"; ACD="#8e4023"; AB="#f6e9e1"; RB="#ddb79f"
    HBG="#e7f3ea"; HBD="#a7c9b0"; LBG="#f8e8e8"; LBD="#d9abab"

    def __init__(self, root):
        self.root = root
        self.root.title("Test MUSHRA — Auralizacja")
        self.root.geometry("1500x900")
        self.root.minsize(1200, 800)
        self.root.configure(bg=self.BG)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.player = StreamPlayer()
        self.task_idx = 0
        self.rand_samples = {}
        self.scores = {}
        self.playing_key = None
        self.playing_path = None
        self.seek_dragging = False
        self.participant_name = tk.StringVar()
        self.exp_level = tk.StringVar()
        self.headphone_type = tk.StringVar(value="sluchawki_zamkniete")
        self.headphone_model = tk.StringVar()
        self.debug_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Gotowe")
        self.widgets = {}
        self._randomize()
        self._init_scores()
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

    def abs_path(self,r): return os.path.join(self.base_dir,r)

    def _randomize(self):
        self.rand_samples = {}
        for t in TASKS:
            types = list(t["stimuli"].keys()); random.shuffle(types)
            self.rand_samples[t["id"]] = [SampleEntry(SAMPLE_LETTERS[i],tp,t["stimuli"][tp]) for i,tp in enumerate(types)]

    def _init_scores(self):
        self.scores = {t["id"]:{l:50 for l in SAMPLE_LETTERS} for t in TASKS}

    def _card(self, parent, title=None, pad=10, bg=None, border=None):
        bg=bg or self.SF; border=border or self.BD
        outer=tk.Frame(parent,bg=bg,highlightbackground=border,highlightthickness=1)
        inner=tk.Frame(outer,bg=bg,padx=pad,pady=pad); inner.pack(fill="both",expand=True)
        if title: tk.Label(inner,text=title,bg=bg,fg=self.TX3,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(0,6))
        return outer,inner

    def _build(self):
        self.container=tk.Frame(self.root,bg=self.BG,padx=14,pady=10); self.container.pack(fill="both",expand=True)
        hdr=tk.Frame(self.container,bg=self.BG); hdr.pack(fill="x",pady=(0,8))
        tk.Label(hdr,text="Test MUSHRA — Auralizacja",bg=self.BG,fg=self.TX,font=("Segoe UI",18,"bold")).pack(side="left")
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
    def show_test(self): self.clear(); self.test_frame.pack(fill="both",expand=True); self.render_task()
    def show_results(self): self.clear(); self.results_frame.pack(fill="both",expand=True); self.render_results()

    # ---- INTRO ----
    def _build_intro(self):
        io,i=self._card(self.intro_frame,"INSTRUKCJA",12); io.pack(fill="x",pady=(0,8))
        tk.Label(i,text="Oceniasz zgodność z referencją (REF) na skali 0–100. 7 anonimowych próbek (A–G). "
                 "Suwak pozycji pozwala przeskakiwać do dowolnego momentu. Użyj słuchawek!",
                 bg=self.SF,fg=self.TX2,font=("Segoe UI",10),wraplength=1200,justify="left").pack(anchor="w")
        sr=tk.Frame(i,bg=self.SF); sr.pack(fill="x",pady=(10,0))
        for rng,txt in [("0–20","Zła"),("20–40","Słaba"),("40–60","Dostateczna"),("60–80","Dobra"),("80–100","Doskonała")]:
            c=tk.Frame(sr,bg=self.SF2,highlightbackground=self.BD,highlightthickness=1,padx=6,pady=4)
            c.pack(side="left",fill="x",expand=True,padx=2)
            tk.Label(c,text=rng,bg=self.SF2,fg=self.TX,font=("Consolas",10,"bold")).pack()
            tk.Label(c,text=txt,bg=self.SF2,fg=self.TX2,font=("Segoe UI",8)).pack()
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

    # ---- TEST ----
    def _build_test(self):
        top=tk.Frame(self.test_frame,bg=self.BG); top.pack(fill="x",pady=(0,6))
        self.prog_lbl=tk.Label(top,text="",bg=self.BG,fg=self.TX2,font=("Consolas",9)); self.prog_lbl.pack(side="left")
        ttk.Checkbutton(top,text="Debug",variable=self.debug_var,command=self.render_task).pack(side="right")

        to,tb=self._card(self.test_frame,None,10); to.pack(fill="x",pady=(0,6))
        self.task_title=tk.Label(tb,text="",bg=self.SF,fg=self.TX,font=("Segoe UI",13,"bold")); self.task_title.pack(anchor="w")
        self.task_sub=tk.Label(tb,text="",bg=self.SF,fg=self.TX2,font=("Segoe UI",9)); self.task_sub.pack(anchor="w")

        ro,rb=self._card(self.test_frame,None,10,bg=self.AB,border=self.RB); ro.pack(fill="x",pady=(0,6))
        rr=tk.Frame(rb,bg=self.AB); rr.pack(fill="x")
        self.ref_btn=ttk.Button(rr,text="▶ REF",style="Accent.TButton",command=lambda:self.toggle("ref")); self.ref_btn.pack(side="left")
        self.ref_lbl=tk.Label(rr,text="",bg=self.AB,fg=self.ACD,font=("Segoe UI",9,"bold")); self.ref_lbl.pack(side="left",padx=8)
        # Seek bar
        sf_=tk.Frame(rb,bg=self.AB); sf_.pack(fill="x",pady=(6,0))
        self.seek_time=tk.Label(sf_,text="0:00",bg=self.AB,fg=self.TX2,font=("Consolas",8),width=5); self.seek_time.pack(side="left")
        self.seek_var=tk.DoubleVar(value=0)
        self.seek_scale=tk.Scale(sf_,from_=0,to=1000,orient="horizontal",variable=self.seek_var,
                                  showvalue=False,width=10,bd=0,highlightthickness=0,
                                  troughcolor="#e8e4dd",bg=self.AB,activebackground=self.AC)
        self.seek_scale.pack(side="left",fill="x",expand=True,padx=4)
        self.seek_scale.bind("<ButtonPress-1>",lambda e:setattr(self,'seek_dragging',True))
        self.seek_scale.bind("<ButtonRelease-1>",self._on_seek_release)
        self.seek_dur=tk.Label(sf_,text="0:00",bg=self.AB,fg=self.TX2,font=("Consolas",8),width=5); self.seek_dur.pack(side="right")

        so,sb=self._card(self.test_frame,"PRÓBKI (A–G)",8); so.pack(fill="both",expand=True,pady=(0,6))
        self.grid=tk.Frame(sb,bg=self.SF); self.grid.pack(fill="both",expand=True)

        no,nb=self._card(self.test_frame,None,8); no.pack(fill="x")
        self.prev_btn=ttk.Button(nb,text="← Poprzednie",command=self.prev_task); self.prev_btn.pack(side="left")
        self.next_btn=ttk.Button(nb,text="Następne →",style="Accent.TButton",command=self.next_task); self.next_btn.pack(side="right")

    # ---- RESULTS ----
    def _build_results(self):
        so,self.res_sum=self._card(self.results_frame,"PODSUMOWANIE",10); so.pack(fill="x",pady=(0,6))
        to,tb=self._card(self.results_frame,"WYNIKI",6); to.pack(fill="both",expand=True,pady=(0,6))
        cols=("zad","instr","pom","pr","typ","oc")
        self.tree=ttk.Treeview(tb,columns=cols,show="headings",height=12)
        for c,h,w in zip(cols,["Zad","Instrument","Pomiesz.","Pr.","Typ","Oc"],[40,150,100,35,140,50]):
            self.tree.heading(c,text=h); self.tree.column(c,width=w)
        self.tree.pack(side="left",fill="both",expand=True)
        ttk.Scrollbar(tb,orient="vertical",command=self.tree.yview).pack(side="right",fill="y")
        self.val_lbl=tk.Label(self.results_frame,text="",bg=self.BG,fg=self.TX2,font=("Segoe UI",8)); self.val_lbl.pack(anchor="w",pady=(0,6))
        a=tk.Frame(self.results_frame,bg=self.BG); a.pack(fill="x")
        ttk.Button(a,text="Eksportuj CSV",style="Accent.TButton",command=self.export_csv).pack(side="left")
        ttk.Button(a,text="Nowy test",command=self.reset).pack(side="right")

    # ---- SEEK ----
    def _on_seek_release(self, event):
        self.seek_dragging = False
        if self.player.is_playing:
            dur = self.player.duration_seconds
            if dur > 0:
                target = (self.seek_var.get() / 1000.0) * dur
                self.player.seek(target)

    def _tick(self):
        if self.player.is_playing and not self.seek_dragging:
            pos = self.player.position_seconds
            dur = self.player.duration_seconds
            if dur > 0:
                self.seek_var.set((pos / dur) * 1000)
                self.seek_time.configure(text=f"{int(pos)//60}:{int(pos)%60:02d}")
                self.seek_dur.configure(text=f"{int(dur)//60}:{int(dur)%60:02d}")
        self.root.after(100, self._tick)

    # ---- AUDIO ----
    def _on_finished(self):
        self.root.after(0, self._reset_btns)

    def _reset_btns(self):
        if self.playing_key == "ref":
            self.ref_btn.configure(text="▶ REF")
        elif self.playing_key in self.widgets:
            self.widgets[self.playing_key]["btn"].configure(text=f"▶ {self.playing_key}")
        self.playing_key = None; self.playing_path = None
        self.status_var.set("Gotowe")

    def toggle(self, key):
        if self.playing_key == key and self.player.is_playing:
            self.player.stop(); self._reset_btns(); return
        # Reset old button
        if self.playing_key == "ref": self.ref_btn.configure(text="▶ REF")
        elif self.playing_key in self.widgets: self.widgets[self.playing_key]["btn"].configure(text=f"▶ {self.playing_key}")

        task = TASKS[self.task_idx]
        if key == "ref":
            path = self.abs_path(task["refFile"]); self.ref_btn.configure(text="■ REF")
        else:
            s = next(x for x in self.rand_samples[task["id"]] if x.letter == key)
            path = self.abs_path(s.file); self.widgets[key]["btn"].configure(text=f"■ {key}")
        if not os.path.exists(path):
            messagebox.showerror("Brak pliku",path); self._reset_btns(); return
        self.playing_key = key; self.playing_path = path
        self.seek_var.set(0)
        self.status_var.set(f"▶ {os.path.basename(path)}")
        self.player.play(path, finished_callback=self._on_finished)

    # ---- TASK ----
    def start_test(self):
        if not self.participant_name.get().strip(): messagebox.showerror("Błąd","Podaj imię."); return
        self.show_test()

    def render_task(self):
        self.player.stop()
        self._reset_btns()
        t = TASKS[self.task_idx]
        self.prog_lbl.configure(text=f"Zadanie {self.task_idx+1} z {len(TASKS)}")
        self.task_title.configure(text=f'{t["instrument"]} — {t["room"]}')
        self.task_sub.configure(text=f'Pozycja: {t["position"]}')
        self.ref_lbl.configure(text=f'{t["instrument"]} — {t["room"]}, {t["position"]}')
        self.prev_btn.configure(state="normal" if self.task_idx>0 else "disabled")
        self.next_btn.configure(text="Zakończ →" if self.task_idx==len(TASKS)-1 else "Następne →")

        for ch in self.grid.winfo_children(): ch.destroy()
        self.widgets = {}

        for col,sample in enumerate(self.rand_samples[t["id"]]):
            card=tk.Frame(self.grid,bg=self.SF2,highlightbackground=self.BD,highlightthickness=1,padx=4,pady=6)
            card.grid(row=0,column=col,padx=3,pady=3,sticky="nsew")
            self.grid.columnconfigure(col,weight=1)

            tk.Label(card,text=sample.letter,bg=card["bg"],fg=self.TX,font=("Consolas",13,"bold")).pack(pady=(0,2))
            if self.debug_var.get():
                tk.Label(card,text=TYPE_LABELS[sample.sample_type],bg=card["bg"],fg=self.TX2,font=("Segoe UI",7),wraplength=100).pack(pady=(0,2))
            btn=ttk.Button(card,text=f"▶ {sample.letter}",command=lambda k=sample.letter:self.toggle(k)); btn.pack(pady=(0,6))

            sv=tk.IntVar(value=self.scores[t["id"]][sample.letter])
            vl=tk.Label(card,text=str(sv.get()),bg=card["bg"],fg=self.TX,font=("Consolas",16,"bold")); vl.pack()
            ql=tk.Label(card,text=self._q(sv.get()),bg=card["bg"],fg=self.TX2,font=("Segoe UI",7)); ql.pack(pady=(0,4))

            sc=tk.Scale(card,from_=100,to=0,orient="vertical",length=180,width=14,
                        showvalue=False,bd=0,highlightthickness=0,troughcolor="#cbc5bd",
                        bg=card["bg"],activebackground=self.AC,
                        command=lambda v,tid=t["id"],l=sample.letter,s=sv,vl_=vl,ql_=ql,c=card:self._sl(v,tid,l,s,vl_,ql_,c))
            sc.set(sv.get()); sc.pack()
            self.widgets[sample.letter]={"btn":btn,"card":card}
            self._col(card,sv.get())

    def _q(self,v):
        if v>=80: return "Doskonała"
        if v>=60: return "Dobra"
        if v>=40: return "Dostat."
        if v>=20: return "Słaba"
        return "Zła"

    def _sl(self,v,tid,l,sv,vl,ql,card):
        v=int(round(float(v))); self.scores[tid][l]=v; sv.set(v)
        vl.configure(text=str(v)); ql.configure(text=self._q(v)); self._col(card,v)

    def _col(self,card,v):
        bg=self.HBG if v>=70 else self.LBG if v<=25 else self.SF2
        bd=self.HBD if v>=70 else self.LBD if v<=25 else self.BD
        card.configure(bg=bg,highlightbackground=bd)
        for ch in card.winfo_children():
            if isinstance(ch,(tk.Label,tk.Scale)):
                try: ch.configure(bg=bg)
                except: pass

    def next_task(self):
        self.player.stop()
        if self.task_idx<len(TASKS)-1: self.task_idx+=1; self.render_task()
        else: self.show_results()

    def prev_task(self):
        self.player.stop()
        if self.task_idx>0: self.task_idx-=1; self.render_task()

    # ---- RESULTS ----
    def render_results(self):
        by_type={k:[] for k in TYPE_LABELS}
        for t in TASKS:
            for s in self.rand_samples[t["id"]]: by_type[s.sample_type].append(self.scores[t["id"]][s.letter])
        avg=lambda a: round(sum(a)/len(a)) if a else 0
        for ch in self.res_sum.winfo_children(): ch.destroy()
        w=tk.Frame(self.res_sum,bg=self.SF); w.pack(fill="x")
        for lb,k in [("48k","aur48"),("24k","aur24"),("12k","aur12"),("8k","aur8"),("4k","aur4"),("Ukr.ref","hidden_ref"),("Kotwica","anchor")]:
            c=tk.Frame(w,bg=self.SF2,highlightbackground=self.BD,highlightthickness=1,padx=4,pady=4)
            c.pack(side="left",fill="x",expand=True,padx=2)
            tk.Label(c,text=lb,bg=self.SF2,fg=self.TX2,font=("Segoe UI",7)).pack()
            tk.Label(c,text=str(avg(by_type[k])),bg=self.SF2,fg=self.TX,font=("Consolas",16,"bold")).pack()
        for i in self.tree.get_children(): self.tree.delete(i)
        for t in TASKS:
            for s in self.rand_samples[t["id"]]:
                self.tree.insert("","end",values=(t["id"],t["instrument"],t["room"],s.letter,TYPE_LABELS[s.sample_type],self.scores[t["id"]][s.letter]))
        self.val_lbl.configure(text=f"Uczestnik: {self.participant_name.get().strip()} | {self.exp_level.get() or '—'} | {self.headphone_type.get()}")

    def export_csv(self):
        name=self.participant_name.get().strip() or "uczestnik"
        p=filedialog.asksaveasfilename(title="Zapisz CSV",defaultextension=".csv",
            initialfile=f"mushra_{name.replace(' ','_')}_{datetime.now().strftime('%Y-%m-%d')}.csv",filetypes=[("CSV","*.csv")])
        if not p: return
        with open(p,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument","Pomieszczenie","Pozycja","Probka","Typ","Ocena"])
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for t in TASKS:
                for s in self.rand_samples[t["id"]]:
                    w.writerow([name,self.exp_level.get(),self.headphone_type.get(),self.headphone_model.get(),
                                now,t["id"],t["instrument"],t["room"],t["position"],s.letter,TYPE_LABELS[s.sample_type],self.scores[t["id"]][s.letter]])
        messagebox.showinfo("Gotowe",f"Zapisano:\n{p}")

    def reset(self):
        self.player.stop(); self.task_idx=0; self.playing_key=None; self.playing_path=None
        self._randomize(); self._init_scores(); self.show_intro()

    def on_close(self): self.player.stop(); self.root.destroy()


if __name__=="__main__":
    root=tk.Tk(); MushraApp(root); root.mainloop()