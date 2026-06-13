"""
Webowy serwer testów odsłuchowych v2: MUSHRA + Parametryczny.
- Wyniki zapisują się na serwerze (wyniki_web/) + słuchacz może pobrać CSV
- Instrukcja udostępniania: patrz INSTRUKCJA.txt obok skryptu

Uruchom:  python web_testy.py
Otwórz:   http://localhost:5000
Udostępnij: ngrok http 5000

Wymaga: pip install flask
"""

import os, json, random, csv, io
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, Response, make_response

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
RESULTS_DIR = os.path.join(BASE_DIR, "wyniki_web")
os.makedirs(RESULTS_DIR, exist_ok=True)

TASKS = [
    {"id":1,"instrument":"Gitara klasyczna","room":"Korytarz ZEA","position":"Na wprost","base":"test01_gitara_klasyczna_korytarz_wprost"},
    {"id":2,"instrument":"Gitara klasyczna","room":"Sala 123","position":"Prawe ucho","base":"test02_gitara_klasyczna_sala123_praweucho"},
    {"id":3,"instrument":"Kontrabas palcami","room":"Korytarz ZEA","position":"Na wprost","base":"test03_kontrabas_palce_korytarz_wprost"},
    {"id":4,"instrument":"Kontrabas palcami","room":"Studio","position":"Na wprost","base":"test04_kontrabas_palce_studio_wprost"},
    {"id":5,"instrument":"Kontrabas smyczkiem","room":"Studio","position":"Lewe ucho","base":"test05_kontrabas_smyczek_studio_leweucho"},
    {"id":6,"instrument":"Wiolonczela","room":"Korytarz ZEA","position":"Na wprost","base":"test06_wiolonczela_korytarz_wprost"},
    {"id":7,"instrument":"Wiolonczela","room":"Sala 123","position":"Oddalone","base":"test07_wiolonczela_sala123_daleko"},
    {"id":8,"instrument":"Flet","room":"Studio","position":"Lewe ucho","base":"test08_flet_studio_leweucho"},
    {"id":9,"instrument":"Saksofon","room":"Studio","position":"Lewe ucho","base":"test09_saksofon_studio_leweucho"},
    {"id":10,"instrument":"Akordeon","room":"Korytarz ZEA","position":"Oddalone","base":"test10_akordeon_korytarz_daleko"},
]

STIMULI_KEYS = ["aur48","aur24","aur12","aur8","aur4","hidden_ref","anchor"]
STIMULI_LABELS = {"aur48":"Auralizacja 48 kHz","aur24":"Auralizacja 24 kHz","aur12":"Auralizacja 12 kHz",
                  "aur8":"Auralizacja 8 kHz","aur4":"Auralizacja 4 kHz","hidden_ref":"Ukryta referencja","anchor":"Kotwica (mono)"}
PARAM_KEYS = ["aur48","aur24","aur12","aur8","aur4","anchor"]

def stim_path(base, key):
    m = {"aur48":("auraliz_48","_aur48.wav"),"aur24":("auraliz_24","_aur24.wav"),
         "aur12":("auraliz_12","_aur12.wav"),"aur8":("auraliz_8","_aur8.wav"),
         "aur4":("auraliz_4","_aur4.wav"),"hidden_ref":("ref","_ref.wav"),
         "anchor":("anchor_mono","_anchor.wav")}
    folder, suffix = m[key]
    return f"{folder}/{base}{suffix}"

@app.route("/")
def index():
    return LANDING_HTML

@app.route("/mushra")
def mushra_page():
    return MUSHRA_HTML

@app.route("/parametryczny")
def param_page():
    return PARAM_HTML

@app.route("/audio/<path:filepath>")
def serve_audio(filepath):
    return send_from_directory(AUDIO_DIR, filepath)

@app.route("/api/mushra_config")
def api_mushra():
    config = []
    for t in TASKS:
        keys = list(STIMULI_KEYS); random.shuffle(keys)
        letters = "ABCDEFG"
        samples = [{"letter":letters[i],"key":k,"url":f"/audio/{stim_path(t['base'],k)}"} for i,k in enumerate(keys)]
        config.append({**t, "refUrl":f"/audio/ref/{t['base']}_ref.wav", "samples":samples})
    return jsonify(config)

@app.route("/api/param_config")
def api_param():
    config = []
    for t in TASKS:
        keys = list(PARAM_KEYS); random.shuffle(keys)
        stims = [{"key":k,"label":STIMULI_LABELS.get(k,k),"url":f"/audio/{stim_path(t['base'],k)}"} for k in keys]
        config.append({**t, "refUrl":f"/audio/ref/{t['base']}_ref.wav", "stimuli":stims})
    return jsonify(config)

@app.route("/api/submit_mushra", methods=["POST"])
def submit_mushra():
    data = request.json
    name = (data.get("participant","anon") or "anon").replace(" ","_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Zapis na serwerze
    path = os.path.join(RESULTS_DIR, f"mushra_{name}_{ts}.csv")
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument","Pomieszczenie","Pozycja","Probka","Typ","Ocena"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in data.get("results",[]):
            w.writerow([data.get("participant",""),data.get("experience",""),data.get("headphones",""),
                        data.get("model",""),now,row["taskId"],row["instrument"],row["room"],
                        row["position"],row["letter"],STIMULI_LABELS.get(row["key"],row["key"]),row["score"]])
    print(f"[MUSHRA] Zapisano: {path}")
    return jsonify({"ok":True})

@app.route("/api/submit_param", methods=["POST"])
def submit_param():
    data = request.json
    name = (data.get("participant","anon") or "anon").replace(" ","_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"param_{name}_{ts}.csv")
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument","Pomieszczenie","Pozycja","Typ","Typ_kod","Barwa","Przestrzennosc","Naturalnosc"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in data.get("results",[]):
            w.writerow([data.get("participant",""),data.get("experience",""),data.get("headphones",""),
                        data.get("model",""),now,row["taskId"],row["instrument"],row["room"],
                        row["position"],STIMULI_LABELS.get(row["key"],row["key"]),row["key"],
                        row["barwa"],row["przestrzennosc"],row["naturalnosc"]])
    print(f"[PARAM] Zapisano: {path}")
    return jsonify({"ok":True})

@app.route("/api/download_mushra", methods=["POST"])
def download_mushra():
    data = request.json
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument","Pomieszczenie","Pozycja","Probka","Typ","Ocena"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in data.get("results",[]):
        w.writerow([data.get("participant",""),data.get("experience",""),data.get("headphones",""),
                    data.get("model",""),now,row["taskId"],row["instrument"],row["room"],
                    row["position"],row["letter"],STIMULI_LABELS.get(row["key"],row["key"]),row["score"]])
    name = (data.get("participant","anon") or "anon").replace(" ","_")
    resp = make_response(buf.getvalue())
    resp.headers["Content-Disposition"] = f'attachment; filename="mushra_{name}.csv"'
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return resp

@app.route("/api/download_param", methods=["POST"])
def download_param():
    data = request.json
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Uczestnik","Doswiadczenie","Sprzet","Model","Data","Zadanie","Instrument","Pomieszczenie","Pozycja","Typ","Typ_kod","Barwa","Przestrzennosc","Naturalnosc"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in data.get("results",[]):
        w.writerow([data.get("participant",""),data.get("experience",""),data.get("headphones",""),
                    data.get("model",""),now,row["taskId"],row["instrument"],row["room"],
                    row["position"],STIMULI_LABELS.get(row["key"],row["key"]),row["key"],
                    row["barwa"],row["przestrzennosc"],row["naturalnosc"]])
    name = (data.get("participant","anon") or "anon").replace(" ","_")
    resp = make_response(buf.getvalue())
    resp.headers["Content-Disposition"] = f'attachment; filename="parametryczny_{name}.csv"'
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return resp

# =============================================
# HTML
# =============================================

LANDING_HTML = """<!DOCTYPE html>
<html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Testy odsłuchowe — Auralizacja</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#f7f4ef;color:#1f1d1a;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border-radius:12px;padding:40px;max-width:600px;width:90%;box-shadow:0 2px 12px rgba(0,0,0,.08)}
h1{font-size:24px;margin-bottom:8px}p{color:#6f685f;margin-bottom:24px;line-height:1.5}
a.btn{display:block;text-align:center;padding:16px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;margin-bottom:12px;transition:transform .1s}
a.btn:hover{transform:scale(1.02)}
.mushra{background:#b2552f;color:#fff}.param{background:#2d6a4f;color:#fff}
.note{font-size:13px;color:#9d968c;margin-top:16px;text-align:center}
</style></head><body>
<div class="card">
<h1>🎧 Testy odsłuchowe</h1>
<p>Badanie jakości auralizowanych sygnałów akustycznych.<br>Praca magisterska — Paweł Kabała, Politechnika Warszawska</p>
<a class="btn mushra" href="/mushra">Test MUSHRA (~40 min)</a>
<a class="btn param" href="/parametryczny">Test parametryczny (~30 min)</a>
<p class="note">⚠️ Koniecznie użyj słuchawek!<br>Po zakończeniu testu pobierzesz plik z wynikami — wyślij go do mnie.</p>
</div></body></html>"""

MUSHRA_HTML = r"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Test MUSHRA</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#f7f4ef;color:#1f1d1a}
.wrap{max-width:1400px;margin:0 auto;padding:16px}h1{font-size:22px;margin-bottom:12px}
.card{background:#fff;border:1px solid #ddd5c9;border-radius:8px;padding:14px;margin-bottom:12px}
.ref-card{background:#f6e9e1;border-color:#ddb79f}
.btn{padding:10px 18px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;font-size:14px;transition:background .15s}
.btn-ref{background:#b2552f;color:#fff}.btn-ref:hover{background:#8e4023}
.btn-sample{background:#e8e4dd;color:#1f1d1a}.btn-sample:hover{background:#ddd5c9}
.btn-sample.playing{background:#b2552f;color:#fff}
.btn-nav{background:#b2552f;color:#fff;padding:12px 24px}.btn-nav:hover{background:#8e4023}
.btn-nav:disabled{background:#ccc;cursor:default}
.btn-dl{background:#2d6a4f;color:#fff;padding:14px 28px;font-size:16px}.btn-dl:hover{background:#1b4332}
.samples{display:grid;grid-template-columns:repeat(7,1fr);gap:10px}
.sample-card{background:#f2eee8;border:1px solid #ddd5c9;border-radius:8px;padding:10px;text-align:center}
.sample-card.high{background:#e7f3ea;border-color:#a7c9b0}
.sample-card.low{background:#f8e8e8;border-color:#d9abab}
.letter{font-family:Consolas,monospace;font-size:18px;font-weight:bold}
.score-val{font-family:Consolas,monospace;font-size:22px;font-weight:bold;margin:4px 0}
.quality{font-size:11px;color:#6f685f}
input[type=range]{accent-color:#b2552f}
.seek-bar{display:flex;align-items:center;gap:8px;margin-top:8px}
.seek-bar input{flex:1}.seek-bar span{font-family:Consolas;font-size:12px;color:#6f685f;min-width:40px}
.progress{font-family:Consolas;font-size:13px;color:#6f685f;margin-bottom:8px}
.nav{display:flex;justify-content:space-between;margin-top:12px}
.intro{max-width:700px;margin:40px auto}
.intro input,.intro select{padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;width:200px}
.intro label{display:inline-block;width:160px;margin:6px 0;font-size:14px;color:#6f685f}
.scale-row{display:flex;gap:6px;margin:12px 0}
.scale-item{flex:1;background:#f2eee8;border:1px solid #ddd5c9;border-radius:6px;padding:8px;text-align:center}
.scale-item b{font-family:Consolas;font-size:14px}.scale-item span{font-size:11px;color:#6f685f}
.summary{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:16px 0}
.summary-card{background:#f2eee8;border-radius:6px;padding:10px;text-align:center}
.summary-card .val{font-family:Consolas;font-size:24px;font-weight:bold}
.summary-card .lbl{font-size:11px;color:#6f685f}
.hidden{display:none}
.done-msg{background:#e7f3ea;border:2px solid #a7c9b0;border-radius:12px;padding:24px;text-align:center;margin:20px 0}
.done-msg h2{color:#2d6a4f;margin-bottom:8px}
</style></head><body>
<div class="wrap">
<h1>Test MUSHRA — Auralizacja</h1>

<div id="intro" class="intro">
<div class="card">
<h2>Instrukcja</h2>
<p style="color:#6f685f;margin:8px 0">Oceniasz zgodność z referencją (REF) na skali 0–100. Masz 7 anonimowych próbek (A–G). Używaj suwaka pozycji żeby przeskakiwać do dowolnego momentu nagrania. <b>Koniecznie użyj słuchawek!</b></p>
<div class="scale-row">
<div class="scale-item"><b>0–20</b><br><span>Zła</span></div>
<div class="scale-item"><b>20–40</b><br><span>Słaba</span></div>
<div class="scale-item"><b>40–60</b><br><span>Dostat.</span></div>
<div class="scale-item"><b>60–80</b><br><span>Dobra</span></div>
<div class="scale-item"><b>80–100</b><br><span>Doskonała</span></div>
</div></div>
<div class="card">
<h2>Dane uczestnika</h2>
<div><label>Imię / pseudonim *</label><input id="name" placeholder="wymagane"></div>
<div><label>Doświadczenie</label><select id="exp"><option value="">—</option><option>brak</option><option>amator</option><option>średniozaawansowany</option><option>zaawansowany</option><option>profesjonalny</option></select></div>
<div><label>Sprzęt</label><select id="hp"><option>słuchawki zamknięte</option><option>słuchawki otwarte</option><option>słuchawki douszne</option><option>głośniki</option></select></div>
<div><label>Model</label><input id="model" placeholder="opcjonalnie"></div>
<div style="margin-top:16px"><button class="btn btn-nav" onclick="startTest()">Rozpocznij test</button></div>
</div></div>

<div id="test" class="hidden">
<div class="progress" id="progress"></div>
<div class="card" id="task-info"></div>
<div class="card ref-card">
<button class="btn btn-ref" id="ref-btn" onclick="toggleRef()">▶ REF</button>
<span id="ref-label" style="margin-left:10px;font-weight:bold;color:#8e4023"></span>
<div class="seek-bar"><span id="seek-time">0:00</span><input type="range" id="seek" min="0" max="1000" value="0"><span id="seek-dur">0:00</span></div>
</div>
<div class="card"><div class="samples" id="samples"></div></div>
<div class="nav">
<button class="btn btn-nav" id="prev-btn" onclick="prevTask()">← Poprzednie</button>
<button class="btn btn-nav" id="next-btn" onclick="nextTask()">Następne →</button>
</div></div>

<div id="results" class="hidden">
<div class="done-msg">
<h2>✅ Test zakończony!</h2>
<p>Pobierz plik z wynikami i wyślij go do Pawła Kabały.</p>
<button class="btn btn-dl" onclick="downloadCSV()">📥 Pobierz wyniki (CSV)</button>
<p style="font-size:12px;color:#6f685f;margin-top:8px">Plik otworzy się w Excelu. Wyślij go mailem lub komunikatorem.</p>
</div>
<div class="card"><h2>Podsumowanie</h2><div class="summary" id="summary"></div></div>
</div>
</div>

<script>
let config=[],taskIdx=0,scores={},currentAudio=null,currentKey=null,seekInterval=null;
const LABELS={"aur48":"48 kHz","aur24":"24 kHz","aur12":"12 kHz","aur8":"8 kHz","aur4":"4 kHz","hidden_ref":"Ukr.ref","anchor":"Kotwica"};
const LABELS_FULL={"aur48":"Auralizacja 48 kHz","aur24":"Auralizacja 24 kHz","aur12":"Auralizacja 12 kHz","aur8":"Auralizacja 8 kHz","aur4":"Auralizacja 4 kHz","hidden_ref":"Ukryta referencja","anchor":"Kotwica (mono)"};
function q(v){if(v>=80)return"Doskonała";if(v>=60)return"Dobra";if(v>=40)return"Dostat.";if(v>=20)return"Słaba";return"Zła"}

async function startTest(){
  if(!document.getElementById("name").value.trim()){alert("Podaj imię!");return}
  config=await(await fetch("/api/mushra_config")).json();
  config.forEach(t=>{scores[t.id]={};t.samples.forEach(s=>{scores[t.id][s.letter]=50})});
  taskIdx=0;hide("intro");show("test");renderTask();
}
function show(id){document.getElementById(id).classList.remove("hidden")}
function hide(id){document.getElementById(id).classList.add("hidden")}

function renderTask(){
  stopAudio();const t=config[taskIdx];
  document.getElementById("progress").textContent=`Zadanie ${taskIdx+1} z ${config.length}`;
  document.getElementById("task-info").innerHTML=`<b style="font-size:16px">${t.instrument} — ${t.room}</b><br><span style="color:#6f685f">Pozycja: ${t.position}</span>`;
  document.getElementById("ref-label").textContent=`${t.instrument} — ${t.room}, ${t.position}`;
  document.getElementById("prev-btn").disabled=taskIdx===0;
  document.getElementById("next-btn").textContent=taskIdx===config.length-1?"Zakończ →":"Następne →";
  const grid=document.getElementById("samples");grid.innerHTML="";
  t.samples.forEach(s=>{
    const val=scores[t.id][s.letter],cls=val>=70?"high":val<=25?"low":"";
    grid.innerHTML+=`<div class="sample-card ${cls}" id="card-${s.letter}">
      <div class="letter">${s.letter}</div>
      <button class="btn btn-sample" id="btn-${s.letter}" onclick="toggleSample('${s.letter}')">▶ ${s.letter}</button>
      <div class="score-val" id="val-${s.letter}">${val}</div>
      <div class="quality" id="q-${s.letter}">${q(val)}</div>
      <input type="range" min="0" max="100" value="${val}" style="writing-mode:vertical-lr;height:160px;direction:rtl;width:100%"
             oninput="onSlider('${s.letter}',this.value)">
    </div>`;
  });
}
function onSlider(l,v){v=parseInt(v);scores[config[taskIdx].id][l]=v;document.getElementById("val-"+l).textContent=v;document.getElementById("q-"+l).textContent=q(v);
  const c=document.getElementById("card-"+l);c.className="sample-card "+(v>=70?"high":v<=25?"low":"");}

function stopAudio(){if(currentAudio){currentAudio.pause();currentAudio=null}currentKey=null;clearInterval(seekInterval);
  document.querySelectorAll(".btn-sample").forEach(b=>{b.classList.remove("playing");b.textContent=b.textContent.replace("■","▶")});
  document.getElementById("ref-btn").textContent="▶ REF";}

function play(url,key){stopAudio();currentAudio=new Audio(url);currentKey=key;currentAudio.play();currentAudio.onended=()=>stopAudio();
  seekInterval=setInterval(()=>{if(!currentAudio)return;const p=currentAudio.currentTime,d=currentAudio.duration||1;
    document.getElementById("seek").value=(p/d)*1000;document.getElementById("seek-time").textContent=fmt(p);document.getElementById("seek-dur").textContent=fmt(d)},100);}
function fmt(s){return`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`}
document.getElementById("seek").addEventListener("input",function(){if(currentAudio&&currentAudio.duration)currentAudio.currentTime=(this.value/1000)*currentAudio.duration});

function toggleRef(){if(currentKey==="ref"){stopAudio();return}play(config[taskIdx].refUrl,"ref");document.getElementById("ref-btn").textContent="■ REF";}
function toggleSample(l){if(currentKey===l){stopAudio();return}const s=config[taskIdx].samples.find(x=>x.letter===l);play(s.url,l);
  document.getElementById("btn-"+l).classList.add("playing");document.getElementById("btn-"+l).textContent="■ "+l;}

function nextTask(){stopAudio();if(taskIdx<config.length-1){taskIdx++;renderTask()}else showResults();}
function prevTask(){stopAudio();if(taskIdx>0){taskIdx--;renderTask()}}

function getResultsData(){
  const results=[];
  config.forEach(t=>t.samples.forEach(s=>{results.push({taskId:t.id,instrument:t.instrument,room:t.room,position:t.position,letter:s.letter,key:s.key,score:scores[t.id][s.letter]})}));
  return {participant:document.getElementById("name").value,experience:document.getElementById("exp").value,
    headphones:document.getElementById("hp").value,model:document.getElementById("model").value,results};
}

function showResults(){
  hide("test");show("results");
  // Wyślij na serwer (backup)
  fetch("/api/submit_mushra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(getResultsData())});
  // Podsumowanie
  const byType={};config.forEach(t=>t.samples.forEach(s=>{if(!byType[s.key])byType[s.key]=[];byType[s.key].push(scores[t.id][s.letter])}));
  const avg=arr=>Math.round(arr.reduce((a,b)=>a+b,0)/arr.length);
  let html="";["aur48","aur24","aur12","aur8","aur4","hidden_ref","anchor"].forEach(k=>{
    html+=`<div class="summary-card"><div class="val">${avg(byType[k]||[0])}</div><div class="lbl">${LABELS[k]}</div></div>`;});
  document.getElementById("summary").innerHTML=html;
}

async function downloadCSV(){
  const resp=await fetch("/api/download_mushra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(getResultsData())});
  const blob=await resp.blob();
  const url=URL.createObjectURL(blob);const a=document.createElement("a");
  a.href=url;a.download=`mushra_${document.getElementById("name").value.replace(/ /g,"_")}.csv`;a.click();URL.revokeObjectURL(url);
}
</script></body></html>"""

PARAM_HTML = r"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Test parametryczny</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#f4f1ec;color:#1f1d1a}
.wrap{max-width:900px;margin:0 auto;padding:16px}h1{font-size:22px;margin-bottom:12px}
.card{background:#fff;border:1px solid #ddd5c9;border-radius:8px;padding:14px;margin-bottom:12px}
.ref-card{background:#e0efe6;border-color:#a4cbb1}
.btn{padding:10px 18px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;font-size:14px}
.btn-ref{background:#2d6a4f;color:#fff}.btn-ref:hover{background:#1b4332}
.btn-stim{background:#e8e4dd;color:#1f1d1a}.btn-stim:hover{background:#ddd5c9}.btn-stim.playing{background:#2d6a4f;color:#fff}
.btn-nav{background:#2d6a4f;color:#fff;padding:12px 24px}.btn-nav:hover{background:#1b4332}.btn-nav:disabled{background:#ccc}
.btn-dl{background:#b2552f;color:#fff;padding:14px 28px;font-size:16px}.btn-dl:hover{background:#8e4023}
.seek-bar{display:flex;align-items:center;gap:8px;margin-top:8px}
.seek-bar input{flex:1;accent-color:#2d6a4f}.seek-bar span{font-family:Consolas;font-size:12px;color:#6f685f;min-width:40px}
.progress{font-family:Consolas;font-size:13px;color:#6f685f;margin-bottom:8px}
.attr-row{display:flex;align-items:center;padding:12px 0;border-bottom:1px solid #eee;gap:12px}
.attr-label{font-weight:bold;font-size:15px;min-width:180px}
.attr-desc{font-size:12px;color:#6f685f;min-width:200px}
.attr-slider{flex:1}.attr-slider input{width:100%;accent-color:#2d6a4f}
.attr-val{font-family:Consolas;font-size:22px;font-weight:bold;min-width:50px;text-align:right}
.nav{display:flex;justify-content:space-between;margin-top:12px}
.intro{max-width:700px;margin:40px auto}
.intro input,.intro select{padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;width:200px}
.intro label{display:inline-block;width:160px;margin:6px 0;font-size:14px;color:#6f685f}
.hidden{display:none}
.done-msg{background:#e7f3ea;border:2px solid #a7c9b0;border-radius:12px;padding:24px;text-align:center;margin:20px 0}
.done-msg h2{color:#2d6a4f;margin-bottom:8px}
.res-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}
.res-table th,.res-table td{border:1px solid #ddd;padding:6px 8px;text-align:center}.res-table th{background:#f2eee8}
</style></head><body>
<div class="wrap">
<h1>Test parametryczny — Barwa / Przestrzenność / Naturalność</h1>

<div id="intro" class="intro">
<div class="card">
<h2>Instrukcja</h2>
<p style="color:#6f685f;margin:8px 0;line-height:1.6">Słuchasz próbki i porównujesz z referencją (REF). Oceniasz <b>3 atrybuty</b> osobno (0–100):<br>
1. <b style="color:#4472C4">Wierność barwy</b> — czy brzmienie jest takie jak w REF?<br>
2. <b style="color:#E97132">Wierność przestrzenna</b> — czy lokalizacja źródła jest taka jak w REF?<br>
3. <b style="color:#548235">Naturalność</b> — czy brzmi jak prawdziwy instrument?<br><br>
10 zadań × 6 próbek. <b>Koniecznie użyj słuchawek!</b></p></div>
<div class="card">
<h2>Dane uczestnika</h2>
<div><label>Imię / pseudonim *</label><input id="name" placeholder="wymagane"></div>
<div><label>Doświadczenie</label><select id="exp"><option value="">—</option><option>brak</option><option>amator</option><option>średniozaawansowany</option><option>zaawansowany</option><option>profesjonalny</option></select></div>
<div><label>Sprzęt</label><select id="hp"><option>słuchawki zamknięte</option><option>słuchawki otwarte</option><option>słuchawki douszne</option><option>głośniki</option></select></div>
<div><label>Model</label><input id="model" placeholder="opcjonalnie"></div>
<div style="margin-top:16px"><button class="btn btn-nav" onclick="startTest()">Rozpocznij test</button></div>
</div></div>

<div id="test" class="hidden">
<div class="progress" id="progress"></div>
<div class="card" id="task-info"></div>
<div class="card ref-card">
<div style="display:flex;gap:10px;align-items:center">
<button class="btn btn-ref" id="ref-btn" onclick="toggle('ref')">▶ REF</button>
<button class="btn btn-stim" id="stim-btn" onclick="toggle('stim')">▶ PRÓBKA</button>
<span id="stim-label" style="font-weight:bold;color:#1b4332"></span></div>
<div class="seek-bar"><span id="seek-time">0:00</span><input type="range" id="seek" min="0" max="1000" value="0"><span id="seek-dur">0:00</span></div>
</div>
<div class="card" id="attrs"></div>
<div class="nav">
<button class="btn btn-nav" id="prev-btn" onclick="prev()">← Poprzednia</button>
<button class="btn btn-nav" id="next-btn" onclick="next()">Następna →</button>
</div></div>

<div id="results" class="hidden">
<div class="done-msg">
<h2>✅ Test zakończony!</h2>
<p>Pobierz plik z wynikami i wyślij go do Pawła Kabały.</p>
<button class="btn btn-dl" onclick="downloadCSV()">📥 Pobierz wyniki (CSV)</button>
<p style="font-size:12px;color:#6f685f;margin-top:8px">Plik otworzy się w Excelu. Wyślij go mailem lub komunikatorem.</p>
</div>
<div class="card"><h2>Podsumowanie</h2><table class="res-table" id="res-table"><thead><tr><th>Wariant</th><th>Barwa</th><th>Przestrz.</th><th>Natural.</th></tr></thead><tbody></tbody></table></div>
</div>
</div>

<script>
let config=[],taskIdx=0,stimIdx=0,scores={},currentAudio=null,currentKey=null,seekInt=null;
const ATTRS=[{key:"barwa",label:"Wierność barwy",desc:"Czy brzmienie jest takie jak w REF?",color:"#4472C4"},
{key:"przestrzennosc",label:"Wierność przestrzenna",desc:"Czy lokalizacja i otoczenie jak w REF?",color:"#E97132"},
{key:"naturalnosc",label:"Naturalność",desc:"Jak prawdziwy instrument w pomieszczeniu?",color:"#548235"}];
const LABELS={"aur48":"Aur. 48 kHz","aur24":"Aur. 24 kHz","aur12":"Aur. 12 kHz","aur8":"Aur. 8 kHz","aur4":"Aur. 4 kHz","anchor":"Kotwica (mono)"};
function show(id){document.getElementById(id).classList.remove("hidden")}
function hide(id){document.getElementById(id).classList.add("hidden")}

async function startTest(){
  if(!document.getElementById("name").value.trim()){alert("Podaj imię!");return}
  config=await(await fetch("/api/param_config")).json();
  config.forEach(t=>{scores[t.id]={};t.stimuli.forEach(s=>{scores[t.id][s.key]={barwa:50,przestrzennosc:50,naturalnosc:50}})});
  taskIdx=0;stimIdx=0;hide("intro");show("test");render();
}
function curStim(){return config[taskIdx].stimuli[stimIdx]}

function render(){
  stopAudio();const t=config[taskIdx],s=curStim();
  const done=taskIdx*config[0].stimuli.length+stimIdx,total=config.length*config[0].stimuli.length;
  document.getElementById("progress").textContent=`Zadanie ${taskIdx+1}/${config.length} · Próbka ${stimIdx+1}/${t.stimuli.length} · ${done+1}/${total}`;
  document.getElementById("task-info").innerHTML=`<b style="font-size:16px">${t.instrument} — ${t.room}</b><br><span style="color:#6f685f">Pozycja: ${t.position}</span>`;
  document.getElementById("stim-label").textContent=`Próbka ${stimIdx+1} z ${t.stimuli.length}`;
  document.getElementById("prev-btn").disabled=(taskIdx===0&&stimIdx===0);
  document.getElementById("next-btn").textContent=(taskIdx===config.length-1&&stimIdx===t.stimuli.length-1)?"Zakończ →":"Następna →";
  let html="";
  ATTRS.forEach(a=>{const val=scores[t.id][s.key][a.key];
    html+=`<div class="attr-row"><div class="attr-label" style="color:${a.color}">${a.label}</div><div class="attr-desc">${a.desc}</div>
      <div class="attr-slider"><input type="range" min="0" max="100" value="${val}" oninput="onAttr('${a.key}',this.value)"></div>
      <div class="attr-val" id="av-${a.key}">${val}</div></div>`;});
  document.getElementById("attrs").innerHTML=html;
}
function onAttr(key,val){val=parseInt(val);scores[config[taskIdx].id][curStim().key][key]=val;document.getElementById("av-"+key).textContent=val;}

function stopAudio(){if(currentAudio){currentAudio.pause();currentAudio=null}currentKey=null;clearInterval(seekInt);
  document.getElementById("ref-btn").textContent="▶ REF";document.getElementById("stim-btn").textContent="▶ PRÓBKA";document.getElementById("stim-btn").classList.remove("playing");}
function playUrl(url,key){stopAudio();currentAudio=new Audio(url);currentKey=key;currentAudio.play();currentAudio.onended=()=>stopAudio();
  seekInt=setInterval(()=>{if(!currentAudio)return;const p=currentAudio.currentTime,d=currentAudio.duration||1;
    document.getElementById("seek").value=(p/d)*1000;document.getElementById("seek-time").textContent=fmt(p);document.getElementById("seek-dur").textContent=fmt(d)},100);}
function fmt(s){return`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`}
document.getElementById("seek").addEventListener("input",function(){if(currentAudio&&currentAudio.duration)currentAudio.currentTime=(this.value/1000)*currentAudio.duration});
function toggle(w){if(currentKey===w){stopAudio();return}
  if(w==="ref"){playUrl(config[taskIdx].refUrl,"ref");document.getElementById("ref-btn").textContent="■ REF"}
  else{playUrl(curStim().url,"stim");document.getElementById("stim-btn").textContent="■ PRÓBKA";document.getElementById("stim-btn").classList.add("playing")}}

function next(){stopAudio();const t=config[taskIdx];
  if(stimIdx<t.stimuli.length-1)stimIdx++;else if(taskIdx<config.length-1){taskIdx++;stimIdx=0}else{showResults();return}render();}
function prev(){stopAudio();if(stimIdx>0)stimIdx--;else if(taskIdx>0){taskIdx--;stimIdx=config[taskIdx].stimuli.length-1}render();}

function getResultsData(){
  const results=[];
  config.forEach(t=>t.stimuli.forEach(s=>{const sc=scores[t.id][s.key];
    results.push({taskId:t.id,instrument:t.instrument,room:t.room,position:t.position,key:s.key,...sc})}));
  return{participant:document.getElementById("name").value,experience:document.getElementById("exp").value,
    headphones:document.getElementById("hp").value,model:document.getElementById("model").value,results};
}

function showResults(){
  hide("test");show("results");
  fetch("/api/submit_param",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(getResultsData())});
  const byType={};config.forEach(t=>t.stimuli.forEach(s=>{if(!byType[s.key])byType[s.key]={barwa:[],przestrzennosc:[],naturalnosc:[]};
    ATTRS.forEach(a=>byType[s.key][a.key].push(scores[t.id][s.key][a.key]))}));
  const avg=arr=>(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1);
  let rows="";["aur48","aur24","aur12","aur8","aur4","anchor"].forEach(k=>{if(byType[k])
    rows+=`<tr><td>${LABELS[k]}</td><td>${avg(byType[k].barwa)}</td><td>${avg(byType[k].przestrzennosc)}</td><td>${avg(byType[k].naturalnosc)}</td></tr>`});
  document.querySelector("#res-table tbody").innerHTML=rows;
}

async function downloadCSV(){
  const resp=await fetch("/api/download_param",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(getResultsData())});
  const blob=await resp.blob();const url=URL.createObjectURL(blob);const a=document.createElement("a");
  a.href=url;a.download=`parametryczny_${document.getElementById("name").value.replace(/ /g,"_")}.csv`;a.click();URL.revokeObjectURL(url);}
</script></body></html>"""

if __name__ == "__main__":
    print("=" * 60)
    print("  TESTY ODSŁUCHOWE — SERWER WEB")
    print("=" * 60)
    print(f"  Audio:   {AUDIO_DIR}")
    print(f"  Wyniki:  {RESULTS_DIR}")
    print()
    print("  ➜  http://localhost:5000")
    print()
    print("  Żeby udostępnić przez internet:")
    print("  1. pip install pyngrok")
    print("  2. ngrok http 5000")
    print("  3. Skopiuj URL https://xxxx.ngrok-free.app")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)