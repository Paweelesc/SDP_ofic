"""
Usuwanie ciszy z początku nagrań + opcjonalnie przerwy między gamą a 'Sto lat'.
Przetwarza WSZYSTKIE pliki WAV w folderze audio/.
"""

import os
import numpy as np
import soundfile as sf

AUDIO_DIR = r"C:\Users\Lenovo\Desktop\Magisterka\audio"

# Parametry detekcji
THRESHOLD_DB = -40.0        # Próg RMS w dB (poniżej = cisza)
WINDOW_S = 0.05             # Okno analizy (50 ms)
MARGIN_BEFORE_S = 0.15      # Zostawić 150ms przed pierwszym dźwiękiem
MIN_SILENCE_S = 0.8         # Min. długość ciszy w środku żeby ją wykryć
CROSSFADE_S = 0.02          # Crossfade 20ms przy cięciu w środku

threshold_lin = 10 ** (THRESHOLD_DB / 20)


def find_onset(data, sr):
    """Znajdź moment, gdzie RMS przekracza próg."""
    if data.ndim > 1:
        mono = np.max(np.abs(data), axis=1)
    else:
        mono = np.abs(data)

    win = int(WINDOW_S * sr)
    for i in range(0, len(mono) - win, win // 2):
        chunk = mono[i:i + win]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms > threshold_lin:
            # Cofnij się o margines
            onset = max(0, i - int(MARGIN_BEFORE_S * sr))
            return onset
    return 0


def find_silence_gaps(data, sr):
    """Znajdź przerwy ciszy w środku nagrania (np. między gamą a 'Sto lat')."""
    if data.ndim > 1:
        mono = np.max(np.abs(data), axis=1)
    else:
        mono = np.abs(data)

    win = int(WINDOW_S * sr)
    min_gap_wins = int(MIN_SILENCE_S / WINDOW_S)

    # Oblicz RMS per okno
    n_wins = len(mono) // win
    is_quiet = []
    for i in range(n_wins):
        chunk = mono[i * win:(i + 1) * win]
        rms = np.sqrt(np.mean(chunk ** 2))
        is_quiet.append(rms < threshold_lin)

    # Znajdź ciągłe fragmenty ciszy
    gaps = []
    gap_start = None
    for i, q in enumerate(is_quiet):
        if q and gap_start is None:
            gap_start = i
        elif not q and gap_start is not None:
            gap_len = i - gap_start
            if gap_len >= min_gap_wins:
                # Ignoruj pierwsze 2 sekundy (to początkowa cisza, nie środkowa)
                start_s = gap_start * WINDOW_S
                if start_s > 2.0:
                    gaps.append((gap_start * win, i * win))
            gap_start = None

    # Handle gap that extends to the very end of the file
    if gap_start is not None:
        gap_len = len(is_quiet) - gap_start
        if gap_len >= min_gap_wins and gap_start * WINDOW_S > 2.0:
            gaps.append((gap_start * win, len(mono)))

    return gaps


def trim_file(filepath, trim_start=True, trim_middle=True):
    """Przytnij plik: usuń ciszę z początku i opcjonalnie z środka."""
    data, sr = sf.read(filepath)
    original_len = len(data) / sr

    # 1. Trim początku
    if trim_start:
        onset = find_onset(data, sr)
        if onset > 0:
            data = data[onset:]

    # 2. Trim środka (przerwy ciszy)
    if trim_middle:
        gaps = find_silence_gaps(data, sr)
        if gaps:
            # Usuń przerwy od końca (żeby indeksy się nie przesunęły)
            cf_samples = int(CROSSFADE_S * sr)
            for gap_start, gap_end in reversed(gaps):
                # Crossfade: fade out przed przerwą, fade in po przerwie
                if gap_start > cf_samples and gap_end + cf_samples < len(data):
                    before = data[:gap_start]
                    after = data[gap_end:]

                    # Krótki crossfade
                    fade_out = np.linspace(1, 0, cf_samples).reshape(-1, 1) if data.ndim > 1 else np.linspace(1, 0, cf_samples)
                    fade_in = np.linspace(0, 1, cf_samples).reshape(-1, 1) if data.ndim > 1 else np.linspace(0, 1, cf_samples)

                    before[-cf_samples:] = before[-cf_samples:] * fade_out
                    after[:cf_samples] = after[:cf_samples] * fade_in

                    data = np.concatenate([before, after])

    new_len = len(data) / sr
    return data, sr, original_len, new_len


# =====================================================
# GŁÓWNA PĘTLA
# =====================================================

print("=" * 70)
print("TRIMOWANIE CISZY Z NAGRAŃ")
print("=" * 70)
print(f"Próg:    {THRESHOLD_DB} dB")
print(f"Margines: {MARGIN_BEFORE_S*1000:.0f} ms przed atakiem")
print(f"Min. przerwa w środku: {MIN_SILENCE_S} s")
print()

total_saved = 0
total_files = 0

folders = [f for f in os.listdir(AUDIO_DIR)
           if os.path.isdir(os.path.join(AUDIO_DIR, f))]

for folder in sorted(folders):
    folder_path = os.path.join(AUDIO_DIR, folder)
    wavs = [f for f in os.listdir(folder_path) if f.endswith('.wav')]

    if not wavs:
        continue

    print(f"--- {folder}/ ({len(wavs)} plików) ---")

    for wav_name in sorted(wavs):
        filepath = os.path.join(folder_path, wav_name)
        data, sr, old_len, new_len = trim_file(filepath, trim_start=True, trim_middle=True)

        saved = old_len - new_len
        total_saved += saved
        total_files += 1

        sf.write(filepath, data, sr, subtype="FLOAT")

        if saved > 0.1:
            print(f"  {wav_name}: {old_len:.1f}s → {new_len:.1f}s (usunięto {saved:.1f}s)")
        else:
            print(f"  {wav_name}: {old_len:.1f}s (bez zmian)")

    print()

print("=" * 70)
print(f"Przetworzone: {total_files} plików")
print(f"Łącznie usunięto: {total_saved:.1f}s ciszy")
print("=" * 70)
print()
print("Testy MUSHRA i parametryczny nie wymagają zmian — te same pliki, krótsze.")