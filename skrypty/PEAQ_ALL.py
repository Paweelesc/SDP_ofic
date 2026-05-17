"""
PEAQ (ITU-R BS.1387) dla wszystkich 10 testów MUSHRA.
Używa aquatk.metrics.PEAQ.peaq_basic.process_audio_files()

Zawiera sanity check: referencja vs referencja (oczekiwany ODG ≈ 0).
"""

import os
import csv
import tempfile
import numpy as np
import soundfile as sf
from aquatk.metrics.PEAQ.peaq_basic import process_audio_files

# =====================================================
# ŚCIEŻKI
# =====================================================

AUDIO_DIR = r"C:\Users\Lenovo\Desktop\Magisterka\audio"
OUTPUT_CSV = r"C:\Users\Lenovo\Desktop\Magisterka\wyniki_PEAQ.csv"

# =====================================================
# 10 TESTÓW
# =====================================================

TASKS = [
    {"id": 1,  "name": "Gitara klasyczna",    "room": "Korytarz ZEA", "pos": "Na wprost",  "base": "test01_gitara_klasyczna_korytarz_wprost"},
    {"id": 2,  "name": "Gitara klasyczna",    "room": "Sala 123",     "pos": "Prawe ucho", "base": "test02_gitara_klasyczna_sala123_praweucho"},
    {"id": 3,  "name": "Kontrabas palcami",   "room": "Korytarz ZEA", "pos": "Na wprost",  "base": "test03_kontrabas_palce_korytarz_wprost"},
    {"id": 4,  "name": "Kontrabas palcami",   "room": "Studio",       "pos": "Na wprost",  "base": "test04_kontrabas_palce_studio_wprost"},
    {"id": 5,  "name": "Kontrabas smyczkiem", "room": "Studio",       "pos": "Lewe ucho",  "base": "test05_kontrabas_smyczek_studio_leweucho"},
    {"id": 6,  "name": "Wiolonczela",         "room": "Korytarz ZEA", "pos": "Na wprost",  "base": "test06_wiolonczela_korytarz_wprost"},
    {"id": 7,  "name": "Wiolonczela",         "room": "Sala 123",     "pos": "Oddalone",   "base": "test07_wiolonczela_sala123_daleko"},
    {"id": 8,  "name": "Flet",                "room": "Studio",       "pos": "Lewe ucho",  "base": "test08_flet_studio_leweucho"},
    {"id": 9,  "name": "Saksofon",            "room": "Studio",       "pos": "Lewe ucho",  "base": "test09_saksofon_studio_leweucho"},
    {"id": 10, "name": "Akordeon",             "room": "Korytarz ZEA", "pos": "Oddalone",   "base": "test10_akordeon_korytarz_daleko"},
]

VARIANTS = [
    {"key": "ref_ref", "folder": "ref",         "suffix": "_ref.wav",    "label": "Ref vs Ref (sanity)"},
    {"key": "aur48",   "folder": "auraliz_48",  "suffix": "_aur48.wav",  "label": "Auralizacja 48 kHz"},
    {"key": "aur24",   "folder": "auraliz_24",  "suffix": "_aur24.wav",  "label": "Auralizacja 24 kHz"},
    {"key": "aur12",   "folder": "auraliz_12",  "suffix": "_aur12.wav",  "label": "Auralizacja 12 kHz"},
    {"key": "anchor",  "folder": "anchor_mono", "suffix": "_anchor.wav", "label": "Kotwica (mono)"},
]


# =====================================================
# FUNKCJE POMOCNICZE
# =====================================================

def to_16bit_mono_tempfile(src_path):
    """Wczytaj, downmix do mono, zapisz jako 16-bit PCM tymczasowy WAV."""
    data, sr = sf.read(src_path)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    peak = np.max(np.abs(data))
    if peak > 1.0:
        data = data / peak
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    sf.write(tmp_path, data, sr, subtype="PCM_16")
    return tmp_path


def parse_peaq_result(result):
    """
    process_audio_files zwraca listę — wyciągamy DI i ODG.
    Format: lista z dwoma elementami [DI, ODG] lub zagnieżdżona struktura.
    """
    if isinstance(result, (int, float)):
        return None, float(result)

    if isinstance(result, (list, tuple)):
        # Spłaszcz zagnieżdżone listy
        flat = []
        for item in result:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            else:
                flat.append(item)

        if len(flat) >= 2:
            return float(flat[0]), float(flat[1])  # DI, ODG
        elif len(flat) == 1:
            return None, float(flat[0])

    return None, float(result)


# =====================================================
# GŁÓWNA PĘTLA
# =====================================================

print("=" * 75)
print("PEAQ (ITU-R BS.1387) — WSZYSTKIE TESTY")
print("=" * 75)
print()

all_results = []
tmp_files = []

for task in TASKS:
    print(f"--- Test {task['id']:>2}: {task['name']} — {task['room']} — {task['pos']} ---")

    ref_path = os.path.join(AUDIO_DIR, "ref", task["base"] + "_ref.wav")
    if not os.path.exists(ref_path):
        print(f"  BRAK REFERENCJI: {ref_path}")
        continue

    ref_tmp = to_16bit_mono_tempfile(ref_path)
    tmp_files.append(ref_tmp)

    for var in VARIANTS:
        if var["key"] == "ref_ref":
            # Sanity check: referencja vs referencja
            deg_path = ref_path
        else:
            deg_path = os.path.join(AUDIO_DIR, var["folder"], task["base"] + var["suffix"])

        if not os.path.exists(deg_path):
            print(f"  {var['key']:>8}: BRAK PLIKU")
            continue

        deg_tmp = to_16bit_mono_tempfile(deg_path)
        tmp_files.append(deg_tmp)

        print(f"  {var['key']:>8}: obliczam...", end="", flush=True)

        try:
            result = process_audio_files(ref_tmp, deg_tmp)
            di, odg = parse_peaq_result(result)
            print(f"\r  {var['key']:>8}: ODG = {odg:>7.3f}" + (f"  (DI = {di:.3f})" if di is not None else ""))

            all_results.append({
                "task_id": task["id"],
                "instrument": task["name"],
                "pomieszczenie": task["room"],
                "pozycja": task["pos"],
                "typ": var["label"],
                "typ_kod": var["key"],
                "ODG": round(odg, 4),
                "DI": round(di, 4) if di is not None else "",
            })

        except Exception as e:
            print(f"\r  {var['key']:>8}: BŁĄD -> {e}")

    print()

# Sprzątanie
for tmp in tmp_files:
    try:
        os.remove(tmp)
    except:
        pass

# =====================================================
# ZAPIS CSV
# =====================================================

if all_results:
    fieldnames = list(all_results[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_results)

# =====================================================
# PODSUMOWANIE
# =====================================================

print("=" * 75)
print("PODSUMOWANIE")
print("=" * 75)
print()

by_type = {}
for row in all_results:
    key = row["typ_kod"]
    if key not in by_type:
        by_type[key] = []
    by_type[key].append(row["ODG"])

print(f"{'Typ':<25} {'Śr. ODG':>10} {'Min':>8} {'Max':>8} {'N':>4}")
print("-" * 58)
for key in ["ref_ref", "aur48", "aur24", "aur12", "anchor"]:
    if key in by_type:
        vals = by_type[key]
        avg = np.mean(vals)
        label = [v["label"] for v in VARIANTS if v["key"] == key][0]
        print(f"{label:<25} {avg:>10.3f} {min(vals):>8.3f} {max(vals):>8.3f} {len(vals):>4}")

print()
print(f"Wyniki zapisane: {OUTPUT_CSV}")
print()
print("Skala ODG: 0 = identyczne, -1 = słyszalne, -2 = lekko przeszkadza,")
print("           -3 = przeszkadza, -4 = bardzo przeszkadza")