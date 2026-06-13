"""
KOMPLETNY PIPELINE: od nagrań bezechowych do gotowych plików MUSHRA/ViSQOL.

Co robi:
1. Resampluje nagrania bezechowe z 65536 Hz do 48000 Hz
2. Dla każdego z 10 testów MUSHRA generuje:
   - Auralizację z IR 48 kHz (splot bez resamplingu IR)
   - Auralizację z IR 24 kHz (IR resamplowana z 24k do 48k, up=2)
   - Auralizację z IR 12 kHz (IR resamplowana z 12k do 48k, up=4)
   - Kotwicę mono (IR uśredniona do mono, splot, duplikacja kanałów)
3. Resampluje referencje z 65536 Hz do 48000 Hz
4. Zapisuje wszystko w czystej strukturze:
   Magisterka/audio/
     ref/          - referencje 48 kHz
     auraliz_48/   - auralizacje z IR 48 kHz
     auraliz_24/   - auralizacje z IR 24 kHz
     auraliz_12/   - auralizacje z IR 12 kHz
     anchor_mono/  - kotwice mono

Wszystkie pliki wyjściowe: 48000 Hz, stereo (anchor: fake stereo L=R), 32-bit float.
"""

import os
import sys
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve, resample_poly
from math import gcd

# =====================================================
# ŚCIEŻKI - DOSTOSUJ JEŚLI TRZEBA
# =====================================================

PRACA = r"C:\Users\Lenovo\Desktop\Praca_Inżynierska"

ANECHOIC_DIR = os.path.join(PRACA, "Nagrania_Anechoiczne", "komora_bezechowa")
IR_48K_DIR = os.path.join(PRACA, "ImpulseResponseoffic")
IR_24K_DIR = os.path.join(PRACA, "Impulse response 24khz_FLOAT")
IR_12K_DIR = os.path.join(PRACA, "Impulse response 12khz")

# Referencje - z istniejącego testu MUSHRA (płaska struktura, 65536 Hz)
REF_DIR = r"C:\Users\Lenovo\Desktop\MUSHRA_test\SDP_projekt\audio\ref"

# Wyjście
OUTPUT_DIR = r"C:\Users\Lenovo\Desktop\Magisterka\audio"

TARGET_FS = 48000

# =====================================================
# 10 TESTÓW MUSHRA
# =====================================================

TASKS = [
    {
        "id": 1,
        "name": "gitara_klasyczna_korytarz_wprost",
        "label": "Gitara klasyczna — Korytarz ZEA — Na wprost",
        "anechoic": "nagranie_komora_gitara_klasyczna.wav",
        "ir_48": "Kor  S1R1A0 wprost 48khz.wav",
        "ir_24": "Kor  S1R1A0 wprost 24khz.wav",
        "ir_12": "Kor  S1R1A0 wprost 12khz.wav",
        "ref": "Gitara_klasyczna_Korytarz_wprost_ref.wav",
    },
    {
        "id": 2,
        "name": "gitara_klasyczna_sala123_praweucho",
        "label": "Gitara klasyczna — Sala 123 — Prawe ucho",
        "anechoic": "nagranie_komora_gitara_klasyczna.wav",
        "ir_48": "S123  S1R2A0 praweucho 48khz.wav",
        "ir_24": "S123  S1R2A0 praweucho 24khz.wav",
        "ir_12": "S123  S1R2A0 praweucho 12khz.wav",
        "ref": "Gitara_klasyczna_Sala123_praweucho_ref.wav",
    },
    {
        "id": 3,
        "name": "kontrabas_palce_korytarz_wprost",
        "label": "Kontrabas palcami — Korytarz ZEA — Na wprost",
        "anechoic": "nagranie_komora_kontrabas_palce.wav",
        "ir_48": "Kor  S1R1A0 wprost 48khz.wav",
        "ir_24": "Kor  S1R1A0 wprost 24khz.wav",
        "ir_12": "Kor  S1R1A0 wprost 12khz.wav",
        "ref": "Kontrabas_palce_Korytarz_wprost_ref.wav",
    },
    {
        "id": 4,
        "name": "kontrabas_palce_studio_wprost",
        "label": "Kontrabas palcami — Studio — Na wprost",
        "anechoic": "nagranie_komora_kontrabas_palce.wav",
        "ir_48": "Studio  S1R1A0 wprost 48khz.wav",
        "ir_24": "Studio  S1R1A0 wprost 24khz.wav",
        "ir_12": "Studio  S1R1A0 wprost 12khz.wav",
        "ref": "Kontrabas_palce_Studio_wprost_ref.wav",
    },
    {
        "id": 5,
        "name": "kontrabas_smyczek_studio_leweucho",
        "label": "Kontrabas smyczkiem — Studio — Lewe ucho",
        "anechoic": "nagranie_komora_kontrabas_smyczek.wav",
        "ir_48": "Studio  S1R3A0 leweucho 48khz.wav",
        "ir_24": "Studio  S1R3A0 leweucho 24khz.wav",
        "ir_12": "Studio  S1R3A0 leweucho 12khz.wav",
        "ref": "Kontrabas_smyczek_Studio_leweucho_ref.wav",
    },
    {
        "id": 6,
        "name": "wiolonczela_korytarz_wprost",
        "label": "Wiolonczela — Korytarz ZEA — Na wprost",
        "anechoic": "nagranie_komora_wiolonczela.wav",
        "ir_48": "Kor  S1R1A0 wprost 48khz.wav",
        "ir_24": "Kor  S1R1A0 wprost 24khz.wav",
        "ir_12": "Kor  S1R1A0 wprost 12khz.wav",
        "ref": "Wiolonczela_Korytarz_wprost_ref.wav",
    },
    {
        "id": 7,
        "name": "wiolonczela_sala123_daleko",
        "label": "Wiolonczela — Sala 123 — Oddalone",
        "anechoic": "nagranie_komora_wiolonczela.wav",
        "ir_48": "S123  S1R5A0 daleko 48khz.wav",
        "ir_24": "S123  S1R5A0 daleko 24khz.wav",
        "ir_12": "S123  S1R5A0 daleko 12khz.wav",
        "ref": "Wiolonczela_Sala123_daleko_ref.wav",
    },
    {
        "id": 8,
        "name": "flet_studio_leweucho",
        "label": "Flet — Studio — Lewe ucho",
        "anechoic": "nagranie_komora_flet.wav",
        "ir_48": "Studio  S1R3A0 leweucho 48khz.wav",
        "ir_24": "Studio  S1R3A0 leweucho 24khz.wav",
        "ir_12": "Studio  S1R3A0 leweucho 12khz.wav",
        "ref": "Flet_Studio_leweucho_ref.wav",
    },
    {
        "id": 9,
        "name": "saksofon_studio_leweucho",
        "label": "Saksofon — Studio — Lewe ucho",
        "anechoic": "nagranie_komora_saksofon.wav",
        "ir_48": "Studio  S1R3A0 leweucho 48khz.wav",
        "ir_24": "Studio  S1R3A0 leweucho 24khz.wav",
        "ir_12": "Studio  S1R3A0 leweucho 12khz.wav",
        "ref": "Saksofon_Studio_leweucho_ref.wav",
    },
    {
        "id": 10,
        "name": "akordeon_korytarz_daleko",
        "label": "Akordeon — Korytarz ZEA — Oddalone",
        "anechoic": "nagranie_komora_akordeon.wav",
        "ir_48": "Kor  S1R3A0 daleko 48khz.wav",
        "ir_24": "Kor  S1R3A0 daleko 24khz.wav",
        "ir_12": "Kor  S1R3A0 daleko 12khz.wav",
        "ref": "Akordeon_Korytarz_daleko_ref.wav",
    },
]


# =====================================================
# FUNKCJE
# =====================================================

def resample_to(data, orig_fs, target_fs):
    """Resampluj sygnał do docelowej fs."""
    if orig_fs == target_fs:
        return data
    common = gcd(orig_fs, target_fs)
    up = target_fs // common
    down = orig_fs // common
    if data.ndim == 1:
        return resample_poly(data, up, down)
    else:
        return resample_poly(data, up, down, axis=0)


def load_and_resample(filepath, target_fs):
    """Wczytaj plik audio i resampluj do target_fs."""
    data, sr = sf.read(filepath)
    if sr != target_fs:
        data = resample_to(data, sr, target_fs)
    return data


def normalize_signal(y):
    """Normalizuj do zakresu [-0.9, 0.9]."""
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak * 0.9
    return y


def auralize_stereo(anechoic_mono, ir_stereo):
    """
    Splot nagrania bezechowego (mono) z IR stereo (binauralną).
    Zwraca sygnał stereo (N, 2).
    """
    if ir_stereo.ndim == 1:
        # IR jest mono — splot mono, duplikuj do stereo
        y = normalize_signal(fftconvolve(anechoic_mono, ir_stereo, mode="full"))
        return np.column_stack((y, y))

    ir_L = ir_stereo[:, 0]
    ir_R = ir_stereo[:, 1]

    y_L = fftconvolve(anechoic_mono, ir_L, mode="full")
    y_R = fftconvolve(anechoic_mono, ir_R, mode="full")

    y = np.column_stack((y_L, y_R))
    return normalize_signal(y)


def auralize_mono_anchor(anechoic_mono, ir_stereo):
    """
    Splot nagrania bezechowego z IR uśrednioną do mono.
    Wynik: stereo z L = R (fake stereo).
    """
    if ir_stereo.ndim == 1:
        ir_mono = ir_stereo
    else:
        ir_mono = np.mean(ir_stereo, axis=1)

    y_mono = fftconvolve(anechoic_mono, ir_mono, mode="full")
    y_mono = normalize_signal(y_mono)

    return np.column_stack((y_mono, y_mono))


def check_file(filepath, label):
    """Sprawdź czy plik istnieje, wypisz błąd jeśli nie."""
    if not os.path.exists(filepath):
        print(f"  BRAK PLIKU [{label}]: {filepath}")
        return False
    return True


# =====================================================
# SPRAWDZENIE ŚCIEŻEK
# =====================================================

print("=" * 70)
print("KOMPLETNY PIPELINE AURALIZACJI — 48 kHz")
print("=" * 70)
print()

# Sprawdź foldery źródłowe
all_ok = True
for label, path in [
    ("Nagrania bezechowe", ANECHOIC_DIR),
    ("IR 48 kHz", IR_48K_DIR),
    ("IR 24 kHz", IR_24K_DIR),
    ("IR 12 kHz", IR_12K_DIR),
    ("Referencje", REF_DIR),
]:
    exists = os.path.isdir(path)
    status = "OK" if exists else "BRAK!"
    print(f"  [{status}] {label}: {path}")
    if not exists:
        all_ok = False

if not all_ok:
    print()
    print("BŁĄD: nie wszystkie foldery źródłowe istnieją. Popraw ścieżki na górze skryptu.")
    sys.exit(1)

print()

# Sprawdź czy wszystkie pliki istnieją
print("Sprawdzanie plików...")
missing = 0
for task in TASKS:
    if not check_file(os.path.join(ANECHOIC_DIR, task["anechoic"]), f"Test {task['id']} anechoic"):
        missing += 1
    if not check_file(os.path.join(IR_48K_DIR, task["ir_48"]), f"Test {task['id']} IR 48k"):
        missing += 1
    if not check_file(os.path.join(IR_24K_DIR, task["ir_24"]), f"Test {task['id']} IR 24k"):
        missing += 1
    if not check_file(os.path.join(IR_12K_DIR, task["ir_12"]), f"Test {task['id']} IR 12k"):
        missing += 1
    if not check_file(os.path.join(REF_DIR, task["ref"]), f"Test {task['id']} ref"):
        missing += 1

if missing > 0:
    print(f"\nBRAKUJE {missing} PLIKÓW. Popraw ścieżki lub nazwy plików.")
    print("Kontynuować mimo to? [t/N]")
    if input().strip().lower() not in ("t", "tak", "y"):
        sys.exit(1)
else:
    print(f"  Wszystkie pliki znalezione ({len(TASKS) * 5} plików)")

print()


# =====================================================
# TWORZENIE FOLDERÓW WYJŚCIOWYCH
# =====================================================

out_ref = os.path.join(OUTPUT_DIR, "ref")
out_48 = os.path.join(OUTPUT_DIR, "auraliz_48")
out_24 = os.path.join(OUTPUT_DIR, "auraliz_24")
out_12 = os.path.join(OUTPUT_DIR, "auraliz_12")
out_anchor = os.path.join(OUTPUT_DIR, "anchor_mono")

for d in [out_ref, out_48, out_24, out_12, out_anchor]:
    os.makedirs(d, exist_ok=True)


# =====================================================
# CACHE: nagrania bezechowe (resamplowane raz)
# =====================================================

print("Resampling nagrań bezechowych z 65536 Hz do 48000 Hz...")

anechoic_cache = {}
needed_anechoic = set(task["anechoic"] for task in TASKS)

for filename in needed_anechoic:
    filepath = os.path.join(ANECHOIC_DIR, filename)
    data, sr = sf.read(filepath)

    # Bezechowe -> mono
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Resample do 48k
    if sr != TARGET_FS:
        common = gcd(sr, TARGET_FS)
        up = TARGET_FS // common
        down = sr // common
        print(f"  {filename}: {sr} Hz -> {TARGET_FS} Hz (up={up}, down={down})")
        data = resample_poly(data, up, down)
    else:
        print(f"  {filename}: już {TARGET_FS} Hz")

    anechoic_cache[filename] = data

print()


# =====================================================
# GŁÓWNA PĘTLA: 10 TESTÓW × 4 WARIANTY + REFERENCJA
# =====================================================

for task in TASKS:
    print(f"--- Test {task['id']:>2}: {task['label']} ---")

    # Nagranie bezechowe (z cache, mono, 48 kHz)
    x = anechoic_cache[task["anechoic"]]

    # Nazwa bazowa pliku wyjściowego
    base = f"test{task['id']:02d}_{task['name']}"

    # ----- REFERENCJA -----
    ref_src = os.path.join(REF_DIR, task["ref"])
    if os.path.exists(ref_src):
        ref_data = load_and_resample(ref_src, TARGET_FS)
        ref_dst = os.path.join(out_ref, f"{base}_ref.wav")
        sf.write(ref_dst, ref_data, TARGET_FS, subtype="FLOAT")
        print(f"  ref:     OK")
    else:
        print(f"  ref:     BRAK PLIKU")

    # ----- AURALIZACJA 48 kHz -----
    ir_path = os.path.join(IR_48K_DIR, task["ir_48"])
    if os.path.exists(ir_path):
        ir = load_and_resample(ir_path, TARGET_FS)
        y = auralize_stereo(x, ir)
        dst = os.path.join(out_48, f"{base}_aur48.wav")
        sf.write(dst, y, TARGET_FS, subtype="FLOAT")
        print(f"  aur48:   OK (IR: {ir.shape}, fs po resample: 48k)")
    else:
        print(f"  aur48:   BRAK IR")

    # ----- AURALIZACJA 24 kHz -----
    ir_path = os.path.join(IR_24K_DIR, task["ir_24"])
    if os.path.exists(ir_path):
        ir = load_and_resample(ir_path, TARGET_FS)
        y = auralize_stereo(x, ir)
        dst = os.path.join(out_24, f"{base}_aur24.wav")
        sf.write(dst, y, TARGET_FS, subtype="FLOAT")
        print(f"  aur24:   OK")
    else:
        print(f"  aur24:   BRAK IR")

    # ----- AURALIZACJA 12 kHz -----
    ir_path = os.path.join(IR_12K_DIR, task["ir_12"])
    if os.path.exists(ir_path):
        ir = load_and_resample(ir_path, TARGET_FS)
        y = auralize_stereo(x, ir)
        dst = os.path.join(out_12, f"{base}_aur12.wav")
        sf.write(dst, y, TARGET_FS, subtype="FLOAT")
        print(f"  aur12:   OK")
    else:
        print(f"  aur12:   BRAK IR")

    # ----- KOTWICA MONO -----
    ir_path = os.path.join(IR_48K_DIR, task["ir_48"])
    if os.path.exists(ir_path):
        ir = load_and_resample(ir_path, TARGET_FS)
        y = auralize_mono_anchor(x, ir)
        dst = os.path.join(out_anchor, f"{base}_anchor.wav")
        sf.write(dst, y, TARGET_FS, subtype="FLOAT")
        print(f"  anchor:  OK")
    else:
        print(f"  anchor:  BRAK IR")

    print()


# =====================================================
# PODSUMOWANIE
# =====================================================

print("=" * 70)
print("GOTOWE!")
print("=" * 70)
print()
print(f"Pliki wyjściowe w: {OUTPUT_DIR}")
print()

# Policz pliki
total = 0
for subdir in ["ref", "auraliz_48", "auraliz_24", "auraliz_12", "anchor_mono"]:
    path = os.path.join(OUTPUT_DIR, subdir)
    count = len([f for f in os.listdir(path) if f.endswith(".wav")]) if os.path.isdir(path) else 0
    total += count
    print(f"  {subdir + '/':.<20} {count} plików")

print(f"  {'RAZEM':.<20} {total} plików")
print()
print(f"Wszystkie pliki: {TARGET_FS} Hz, stereo, 32-bit float")
print()
print("NASTĘPNE KROKI:")
print("  1. Uruchom normalizację LUFS (normalizacja_lufs.py) na folderze Magisterka/audio")
print("  2. Zaktualizuj ścieżki w teście MUSHRA")
print("  3. Uruchom ViSQOL (przygotuj_visqol.py z nowym folderem)")