"""
Szybki test PEAQ na jednym zestawie:
Test 1 — Gitara klasyczna, Korytarz ZEA, Na wprost
4 warianty: aur48, aur24, aur12, anchor

Używa aquatk.metrics.PEAQ.peaq_basic.process_audio_files()
"""

import os
import tempfile
import numpy as np
import soundfile as sf
from aquatk.metrics.PEAQ.peaq_basic import process_audio_files

AUDIO_DIR = r"C:\Users\Lenovo\Desktop\Magisterka\audio"

ref_rel = r"ref\test01_gitara_klasyczna_korytarz_wprost_ref.wav"

variants = [
    ("aur48",  r"auraliz_48\test01_gitara_klasyczna_korytarz_wprost_aur48.wav"),
    ("aur24",  r"auraliz_24\test01_gitara_klasyczna_korytarz_wprost_aur24.wav"),
    ("aur12",  r"auraliz_12\test01_gitara_klasyczna_korytarz_wprost_aur12.wav"),
    ("anchor", r"anchor_mono\test01_gitara_klasyczna_korytarz_wprost_anchor.wav"),
]


def to_16bit_mono_tempfile(src_path):
    """
    Wczytaj plik, downmixuj do mono, zapisz jako 16-bit PCM WAV w pliku tymczasowym.
    PEAQ może wymagać 16-bit PCM.
    Zwraca ścieżkę do pliku tymczasowego.
    """
    data, sr = sf.read(src_path)

    # Mono
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Normalizacja
    peak = np.max(np.abs(data))
    if peak > 1.0:
        data = data / peak

    # Zapisz jako tymczasowy plik 16-bit PCM
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    sf.write(tmp_path, data, sr, subtype="PCM_16")
    return tmp_path


print("=" * 60)
print("TEST PEAQ — Gitara klasyczna, Korytarz, Na wprost")
print("=" * 60)
print()

ref_path = os.path.join(AUDIO_DIR, ref_rel)
print(f"Referencja: {ref_rel}")
print()

# Przygotuj referencję (tymczasowy plik 16-bit mono)
ref_tmp = to_16bit_mono_tempfile(ref_path)
tmp_files = [ref_tmp]

print(f"{'Wariant':>8}  {'ODG':>8}")
print("-" * 30)

for name, rel_path in variants:
    deg_path = os.path.join(AUDIO_DIR, rel_path)

    # Przygotuj degradowany (tymczasowy plik 16-bit mono)
    deg_tmp = to_16bit_mono_tempfile(deg_path)
    tmp_files.append(deg_tmp)

    print(f"{name:>8}:  obliczam...", end="", flush=True)

    try:
        result = process_audio_files(ref_tmp, deg_tmp)

        # Wynik może być float, tuple, dict lub obiekt — obsłużmy wszystko
        if isinstance(result, (int, float)):
            odg = float(result)
        elif isinstance(result, tuple):
            odg = float(result[0])
        elif isinstance(result, dict):
            odg = float(result.get("ODG", result.get("odg", list(result.values())[0])))
        elif hasattr(result, "odg"):
            odg = float(result.odg)
        elif hasattr(result, "ODG"):
            odg = float(result.ODG)
        else:
            odg = float(result)

        print(f"\r{name:>8}:  {odg:>8.3f}")

    except Exception as e:
        print(f"\r{name:>8}:  BŁĄD -> {e}")

# Sprzątamy pliki tymczasowe
for tmp in tmp_files:
    try:
        os.remove(tmp)
    except:
        pass

print()
print("Skala ODG: 0 = identyczne, -1 = słyszalne,")
print("           -2 = przeszkadza, -3 = irytuje, -4 = fatalne")