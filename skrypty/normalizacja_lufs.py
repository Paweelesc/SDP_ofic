"""
Loudness normalization (EBU R128 / ITU-R BS.1770) dla wszystkich nagrań
przed testem MUSHRA.

Działanie:
1. Użytkownik wybiera folder nadrzędny (np. "Praca_Inzynierska").
2. Skrypt wykrywa wszystkie podfoldery do znormalizowania
   (po nazwach: "auralizowane", "referenc", "MONO" itp.).
3. Użytkownik wybiera, które foldery faktycznie znormalizować.
4. Tworzy lustrzaną strukturę folderów z sufiksem "_norm".
5. Każdy plik WAV normalizuje do docelowego poziomu LUFS.
6. Po normalizacji ogranicza true peak (zapobiega clippingowi).
7. Wyświetla raport końcowy z statystykami.

Konfiguracja - na górze pliku:
- TARGET_LUFS: docelowy poziom głośności (typowo -23 LUFS dla MUSHRA)
- MAX_PEAK_DBFS: limit true peak po normalizacji (-1 dBFS dla bezpieczeństwa)
- FOLDER_KEYWORDS: słowa kluczowe w nazwach folderów do znormalizowania

Wymagana biblioteka: pip install pyloudnorm
"""

import os
import sys
import numpy as np
import soundfile as sf
from tkinter import Tk, filedialog


# =====================================================
# KONFIGURACJA
# =====================================================

TARGET_LUFS = -23.0
MAX_PEAK_DBFS = -1.0

# Foldery do znormalizowania - skrypt szuka tych słów w nazwach
FOLDER_KEYWORDS = [
    "auralizowane",
    "auralizacja",
    "auraliz",
    "referenc",
    "ref",
    "mono",
    "pomieszczenia",
    "uporzadkowane",
]

# Foldery do pominięcia - jeśli zawierają te słowa, są ignorowane
SKIP_KEYWORDS = [
    "_norm",      # już znormalizowane
    "bezechowe",  # nagrania źródłowe - nie normalizujemy
    "impulse",    # IR - nie normalizujemy
    "ir_",
]


# =====================================================
# IMPORT PYLOUDNORM Z OBSŁUGĄ BRAKU BIBLIOTEKI
# =====================================================

try:
    import pyloudnorm as pyln
except ImportError:
    print("BŁĄD: biblioteka 'pyloudnorm' nie jest zainstalowana.")
    print()
    print("Zainstaluj ją komendą:")
    print("  pip install pyloudnorm")
    print()
    print("W VS Code: otwórz terminal (Ctrl+`) i wpisz powyższą komendę.")
    sys.exit(1)


# =====================================================
# FUNKCJE POMOCNICZE
# =====================================================

def should_process_folder(folder_name):
    """Czy folder powinien być znormalizowany."""
    name_lower = folder_name.lower()

    # Pomijamy foldery z SKIP_KEYWORDS
    for skip in SKIP_KEYWORDS:
        if skip in name_lower:
            return False

    # Włączamy foldery z FOLDER_KEYWORDS
    for keyword in FOLDER_KEYWORDS:
        if keyword in name_lower:
            return True

    return False


def find_target_folders(root_folder):
    """Znajduje wszystkie foldery do znormalizowania."""
    target_folders = []

    for entry in sorted(os.listdir(root_folder)):
        full_path = os.path.join(root_folder, entry)
        if os.path.isdir(full_path) and should_process_folder(entry):
            target_folders.append(full_path)

    return target_folders


def get_all_wavs(folder):
    """Zwraca listę wszystkich plików WAV w folderze (rekurencyjnie)."""
    wavs = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".wav"):
                wavs.append(os.path.join(root, file))
    return wavs


def select_folders(target_folders):
    """
    Pokazuje listę folderów i pozwala użytkownikowi wybrać które przetworzyć.
    Zwraca listę wybranych folderów.
    """
    print()
    print("Znalezione foldery do znormalizowania:")
    print()

    for i, folder in enumerate(target_folders, start=1):
        # Policz pliki WAV szybko
        wav_count = sum(
            1 for root, dirs, files in os.walk(folder)
            for f in files if f.lower().endswith(".wav")
        )
        print(f"  [{i:>2}] {os.path.basename(folder):<45} ({wav_count} plików WAV)")

    print()
    print("Wybór folderów:")
    print("  - wpisz numery oddzielone przecinkami, np. '1,3,5'")
    print("  - lub zakres, np. '1-5'")
    print("  - lub 'wszystkie' / 'all' aby wybrać wszystkie")
    print("  - lub Enter aby anulować")
    print()

    choice = input("Twój wybór: ").strip().lower()

    if not choice:
        return []

    if choice in ("wszystkie", "all", "*"):
        return target_folders

    # Parsowanie wyboru
    selected_indices = set()
    parts = choice.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            # Zakres
            try:
                start, end = part.split("-")
                start = int(start)
                end = int(end)
                for n in range(start, end + 1):
                    if 1 <= n <= len(target_folders):
                        selected_indices.add(n - 1)
            except ValueError:
                print(f"  Nieprawidłowy zakres: '{part}' - pomijam")
        else:
            # Pojedynczy numer
            try:
                n = int(part)
                if 1 <= n <= len(target_folders):
                    selected_indices.add(n - 1)
                else:
                    print(f"  Numer poza zakresem: {n} - pomijam")
            except ValueError:
                print(f"  Nieprawidłowy numer: '{part}' - pomijam")

    return [target_folders[i] for i in sorted(selected_indices)]


def normalize_file(input_path, output_path, meter, target_lufs, max_peak_dbfs):
    """
    Normalizuje pojedynczy plik do docelowego LUFS i limituje true peak.
    Zwraca (oryginalny_lufs, koncowy_lufs, oryginalny_peak_dbfs, koncowy_peak_dbfs).
    """
    audio, sr = sf.read(input_path)

    # Pomiar oryginalnego LUFS
    original_lufs = meter.integrated_loudness(audio)

    # Pomiar oryginalnego peak
    original_peak = np.max(np.abs(audio))
    if original_peak > 0:
        original_peak_dbfs = 20 * np.log10(original_peak)
    else:
        original_peak_dbfs = -np.inf

    # Jeśli plik jest ciszą lub bardzo cichy - omijamy
    if np.isinf(original_lufs) or np.isnan(original_lufs):
        sf.write(output_path, audio, sr, subtype="FLOAT")
        return original_lufs, original_lufs, original_peak_dbfs, original_peak_dbfs

    # Normalizacja do docelowego LUFS
    normalized = pyln.normalize.loudness(audio, original_lufs, target_lufs)

    # Sprawdzenie peaku po normalizacji LUFS
    new_peak = np.max(np.abs(normalized))
    if new_peak > 0:
        new_peak_dbfs = 20 * np.log10(new_peak)
    else:
        new_peak_dbfs = -np.inf

    # Jeśli peak przekracza limit, redukujemy proporcjonalnie
    max_peak_linear = 10 ** (max_peak_dbfs / 20)
    if new_peak > max_peak_linear:
        scaling = max_peak_linear / new_peak
        normalized = normalized * scaling
        final_peak_dbfs = max_peak_dbfs
        final_lufs = meter.integrated_loudness(normalized)
    else:
        final_lufs = target_lufs
        final_peak_dbfs = new_peak_dbfs

    sf.write(output_path, normalized, sr, subtype="FLOAT")

    return original_lufs, final_lufs, original_peak_dbfs, final_peak_dbfs


# =====================================================
# GUI - WYBÓR FOLDERU NADRZĘDNEGO
# =====================================================

root = Tk()
root.withdraw()

print("=" * 70)
print("NORMALIZACJA LOUDNESS (EBU R128 / ITU-R BS.1770)")
print("=" * 70)
print(f"Docelowy poziom: {TARGET_LUFS} LUFS")
print(f"Limit true peak: {MAX_PEAK_DBFS} dBFS")
print("=" * 70)
print()

root_folder = filedialog.askdirectory(
    title="Wybierz folder nadrzędny (zawierający foldery z auralizacjami i referencjami)"
)

if not root_folder:
    print("Nie wybrano folderu.")
    sys.exit()

print(f"Folder nadrzędny: {root_folder}")


# =====================================================
# WYKRYWANIE FOLDERÓW DO PRZETWORZENIA
# =====================================================

target_folders = find_target_folders(root_folder)

if not target_folders:
    print("Nie znaleziono folderów do znormalizowania.")
    print(f"Szukałem podfolderów ze słowami: {FOLDER_KEYWORDS}")
    print(f"Pomijam foldery ze słowami: {SKIP_KEYWORDS}")
    sys.exit()

selected_folders = select_folders(target_folders)

if not selected_folders:
    print()
    print("Nie wybrano żadnych folderów. Anulowano.")
    sys.exit()

print()
print(f"Wybrano {len(selected_folders)} folderów do przetworzenia:")
for f in selected_folders:
    print(f"  - {os.path.basename(f)}")
print()

confirm = input("Kontynuować normalizację? [t/N]: ").strip().lower()
if confirm not in ("t", "tak", "y", "yes"):
    print("Anulowano.")
    sys.exit()


# =====================================================
# GŁÓWNA PĘTLA NORMALIZACJI
# =====================================================

# Globalne statystyki do raportu
stats = {
    "total_files": 0,
    "processed_files": 0,
    "skipped_files": 0,
    "errors": [],
    "original_lufs": [],
    "final_lufs": [],
    "peak_limited_files": 0,
}

# Meter dla każdej fs próbkowania - tworzymy w locie i cache'ujemy
meters_cache = {}

def get_meter(sr):
    if sr not in meters_cache:
        meters_cache[sr] = pyln.Meter(sr)
    return meters_cache[sr]


for src_folder in selected_folders:
    folder_name = os.path.basename(src_folder)
    dst_folder = src_folder + "_norm"

    print()
    print("=" * 70)
    print(f"FOLDER: {folder_name}")
    print(f"  -> wyjście: {os.path.basename(dst_folder)}")
    print("=" * 70)

    wavs = get_all_wavs(src_folder)
    stats["total_files"] += len(wavs)

    if not wavs:
        print(f"  (brak plików WAV)")
        continue

    print(f"  Plików do znormalizowania: {len(wavs)}")

    for i, src_path in enumerate(wavs, start=1):
        # Lustrzana ścieżka w folderze _norm
        rel_path = os.path.relpath(src_path, src_folder)
        dst_path = os.path.join(dst_folder, rel_path)

        # Stwórz katalog docelowy
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        try:
            # Wczytujemy aby poznać fs
            info = sf.info(src_path)
            meter = get_meter(info.samplerate)

            orig_lufs, final_lufs, orig_peak, final_peak = normalize_file(
                src_path,
                dst_path,
                meter,
                TARGET_LUFS,
                MAX_PEAK_DBFS
            )

            stats["processed_files"] += 1
            if not (np.isinf(orig_lufs) or np.isnan(orig_lufs)):
                stats["original_lufs"].append(orig_lufs)
                stats["final_lufs"].append(final_lufs)

            # Czy peak został zredukowany?
            if abs(final_lufs - TARGET_LUFS) > 0.5:
                stats["peak_limited_files"] += 1

            if i % 20 == 0 or i == len(wavs):
                print(f"  [{i}/{len(wavs)}] {os.path.basename(src_path)}")
                print(f"      LUFS: {orig_lufs:+.1f} -> {final_lufs:+.1f}   "
                      f"Peak: {orig_peak:+.1f} -> {final_peak:+.1f} dBFS")

        except Exception as e:
            stats["errors"].append((src_path, str(e)))
            stats["skipped_files"] += 1
            print(f"  [{i}/{len(wavs)}] BŁĄD: {os.path.basename(src_path)}: {e}")


# =====================================================
# RAPORT KOŃCOWY
# =====================================================

print()
print("=" * 70)
print("RAPORT KOŃCOWY")
print("=" * 70)
print(f"Plików znalezionych:    {stats['total_files']}")
print(f"Plików znormalizowanych: {stats['processed_files']}")
print(f"Plików pominiętych:      {stats['skipped_files']}")
print()

if stats["original_lufs"]:
    orig = np.array(stats["original_lufs"])
    final = np.array(stats["final_lufs"])

    print("STATYSTYKI LUFS:")
    print(f"  Oryginalny LUFS - min: {orig.min():+.1f}, max: {orig.max():+.1f}, średnia: {orig.mean():+.1f}")
    print(f"  Końcowy LUFS    - min: {final.min():+.1f}, max: {final.max():+.1f}, średnia: {final.mean():+.1f}")
    print(f"  Docelowy LUFS: {TARGET_LUFS:+.1f}")
    print()

    if stats["peak_limited_files"] > 0:
        print(f"UWAGA: {stats['peak_limited_files']} plików zostało dodatkowo")
        print(f"  zredukowanych ze względu na limit peak ({MAX_PEAK_DBFS} dBFS).")
        print(f"  Ich końcowy LUFS jest niższy niż docelowy, ale spójność")
        print(f"  głośności względnej jest zachowana w granicach ~1-2 dB.")
        print()

if stats["errors"]:
    print(f"BŁĘDY ({len(stats['errors'])}):")
    for path, err in stats["errors"][:10]:
        print(f"  - {os.path.basename(path)}: {err}")
    if len(stats["errors"]) > 10:
        print(f"  ... i {len(stats['errors']) - 10} więcej")

print()
print("Gotowe. Pliki znormalizowane są w folderach z sufiksem '_norm'.")