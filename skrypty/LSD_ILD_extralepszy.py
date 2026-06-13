import os
import csv
import numpy as np
import soundfile as sf

# =====================================================
# ŚCIEŻKI
# =====================================================

AUDIO_DIR = r"C:\Users\Lenovo\Desktop\Magisterka\audio"
OUTPUT_CSV = r"C:\Users\Lenovo\Desktop\Magisterka\wyniki_LSD_ILD_aligned.csv"

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
    {"id": 10, "name": "Akordeon",            "room": "Korytarz ZEA", "pos": "Oddalone",   "base": "test10_akordeon_korytarz_daleko"},
]

VARIANTS = [
    {"key": "aur48",  "folder": "auraliz_48",  "suffix": "_aur48.wav",  "label": "Auralizacja 48 kHz"},
    {"key": "aur24",  "folder": "auraliz_24",  "suffix": "_aur24.wav",  "label": "Auralizacja 24 kHz"},
    {"key": "aur12",  "folder": "auraliz_12",  "suffix": "_aur12.wav",  "label": "Auralizacja 12 kHz"},
    {"key": "anchor", "folder": "anchor_mono", "suffix": "_anchor.wav", "label": "Kotwica (mono)"},
]

# Pasma oktawowe do analizy ILD
OCTAVE_BANDS = [
    (63, 125),
    (125, 250),
    (250, 500),
    (500, 1000),
    (1000, 2000),
    (2000, 4000),
    (4000, 8000),
    (8000, 16000),
    (16000, 24000),
]

MAX_SHIFT_SECONDS = 0.5
MAX_ANALYZE_SECONDS = 8
DECIMATION = 8

# =====================================================
# FUNKCJE WYRÓWNANIA CZASOWEGO
# =====================================================

def find_best_lag(ref_mono, deg_mono, sr, max_shift_seconds=0.5,
                  max_analyze_seconds=8, decim=8):
    """
    Szybkie wyrównanie przez korelację na skróconym i zdecymowanym sygnale.
    lag > 0  -> deg jest opóźnione względem ref
    lag < 0  -> deg wyprzedza ref
    """
    min_len = min(len(ref_mono), len(deg_mono))
    ref_mono = ref_mono[:min_len]
    deg_mono = deg_mono[:min_len]

    max_len = min(len(ref_mono), int(sr * max_analyze_seconds))
    ref_mono = ref_mono[:max_len]
    deg_mono = deg_mono[:max_len]

    ref_mono = ref_mono - np.mean(ref_mono)
    deg_mono = deg_mono - np.mean(deg_mono)

    ref_ds = ref_mono[::decim]
    deg_ds = deg_mono[::decim]

    corr = np.correlate(deg_ds, ref_ds, mode="full")
    lags = np.arange(-len(ref_ds) + 1, len(deg_ds))

    max_shift = int((sr * max_shift_seconds) / decim)
    mask = np.abs(lags) <= max_shift
    corr = corr[mask]
    lags = lags[mask]

    lag_ds = int(lags[np.argmax(corr)])
    lag = lag_ds * decim
    return lag


def apply_lag_to_stereo(ref_L, ref_R, deg_L, deg_R, lag):
    """
    Zastosuj ten sam lag do obu kanałów.
    """
    if lag > 0:
        deg_L = deg_L[lag:]
        deg_R = deg_R[lag:]
        ref_L = ref_L[:len(deg_L)]
        ref_R = ref_R[:len(deg_R)]
    elif lag < 0:
        shift = -lag
        ref_L = ref_L[shift:]
        ref_R = ref_R[shift:]
        deg_L = deg_L[:len(ref_L)]
        deg_R = deg_R[:len(ref_R)]

    min_len = min(len(ref_L), len(ref_R), len(deg_L), len(deg_R))
    return ref_L[:min_len], ref_R[:min_len], deg_L[:min_len], deg_R[:min_len]

# =====================================================
# FUNKCJE METRYK
# =====================================================

def compute_lsd(ref, deg, sr, n_fft=4096, hop=2048):
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]

    if len(ref) < n_fft or len(deg) < n_fft:
        return np.nan

    def stft_power(x):
        window = np.hanning(n_fft)
        n_frames = (len(x) - n_fft) // hop + 1
        power = np.zeros((n_frames, n_fft // 2 + 1))
        for i in range(n_frames):
            frame = x[i * hop:i * hop + n_fft] * window
            fft = np.fft.rfft(frame)
            power[i] = np.abs(fft) ** 2
        return power

    P_ref = stft_power(ref)
    P_deg = stft_power(deg)

    eps = 1e-10
    log_ref = 10 * np.log10(P_ref + eps)
    log_deg = 10 * np.log10(P_deg + eps)

    lsd_per_frame = np.sqrt(np.mean((log_ref - log_deg) ** 2, axis=1))
    return float(np.mean(lsd_per_frame))


def compute_lsd_per_band(ref, deg, sr, bands, n_fft=4096, hop=2048):
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]

    if len(ref) < n_fft or len(deg) < n_fft:
        return {band: np.nan for band in bands}

    window = np.hanning(n_fft)
    n_frames = (len(ref) - n_fft) // hop + 1
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    eps = 1e-10
    results = {}

    for lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        if not np.any(mask):
            results[(lo, hi)] = np.nan
            continue

        lsd_frames = []
        for i in range(n_frames):
            frame_ref = ref[i * hop:i * hop + n_fft] * window
            frame_deg = deg[i * hop:i * hop + n_fft] * window

            fft_ref = np.abs(np.fft.rfft(frame_ref)) ** 2
            fft_deg = np.abs(np.fft.rfft(frame_deg)) ** 2

            log_r = 10 * np.log10(fft_ref[mask] + eps)
            log_d = 10 * np.log10(fft_deg[mask] + eps)
            lsd_frames.append(np.sqrt(np.mean((log_r - log_d) ** 2)))

        results[(lo, hi)] = float(np.mean(lsd_frames))

    return results


def compute_ild(left, right, sr, bands):
    min_len = min(len(left), len(right))
    left = left[:min_len]
    right = right[:min_len]

    freqs = np.fft.rfftfreq(len(left), 1.0 / sr)
    fft_L = np.abs(np.fft.rfft(left)) ** 2
    fft_R = np.abs(np.fft.rfft(right)) ** 2

    eps = 1e-20
    results = {}

    for lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        if not np.any(mask):
            results[(lo, hi)] = 0.0
            continue

        energy_L = np.sum(fft_L[mask])
        energy_R = np.sum(fft_R[mask])
        ild = 10 * np.log10((energy_L + eps) / (energy_R + eps))
        results[(lo, hi)] = float(ild)

    return results


def compute_ild_error(ref_left, ref_right, deg_left, deg_right, sr, bands):
    ild_ref = compute_ild(ref_left, ref_right, sr, bands)
    ild_deg = compute_ild(deg_left, deg_right, sr, bands)

    errors = {}
    for band in bands:
        errors[band] = abs(ild_ref[band] - ild_deg[band])

    avg_error = np.mean(list(errors.values()))
    return float(avg_error), errors, ild_ref, ild_deg

# =====================================================
# GŁÓWNA PĘTLA
# =====================================================

print("=" * 75)
print("METRYKI OBIEKTYWNE: LSD + ILD ERROR (Z WYRÓWNANIEM CZASOWYM)")
print("=" * 75)
print()

all_results = []

for task in TASKS:
    print(f"--- Test {task['id']:>2}: {task['name']} — {task['room']} — {task['pos']} ---")

    ref_path = os.path.join(AUDIO_DIR, "ref", task["base"] + "_ref.wav")
    if not os.path.exists(ref_path):
        print(f"  BRAK REFERENCJI: {ref_path}")
        continue

    ref_data, sr = sf.read(ref_path)
    if ref_data.ndim == 1:
        print("  UWAGA: referencja jest mono, ILD nie ma pełnego sensu")
        ref_L = ref_data
        ref_R = ref_data
    else:
        ref_L = ref_data[:, 0]
        ref_R = ref_data[:, 1]

    ref_mono = (ref_L + ref_R) / 2.0

    for var in VARIANTS:
        deg_path = os.path.join(AUDIO_DIR, var["folder"], task["base"] + var["suffix"])
        if not os.path.exists(deg_path):
            print(f"  BRAK: {deg_path}")
            continue

        print(f"  {var['key']:>6}: szukam laga...", flush=True)

        deg_data, sr_d = sf.read(deg_path)
        if sr_d != sr:
            print(f"  {var['key']:>6}: POMINIĘTO (różne fs: ref={sr}, deg={sr_d})")
            continue

        if deg_data.ndim == 1:
            deg_L = deg_data
            deg_R = deg_data
        else:
            deg_L = deg_data[:, 0]
            deg_R = deg_data[:, 1]

        deg_mono = (deg_L + deg_R) / 2.0

        lag = find_best_lag(
            ref_mono,
            deg_mono,
            sr,
            max_shift_seconds=MAX_SHIFT_SECONDS,
            max_analyze_seconds=MAX_ANALYZE_SECONDS,
            decim=DECIMATION
        )

        ref_L_al, ref_R_al, deg_L_al, deg_R_al = apply_lag_to_stereo(
            ref_L, ref_R, deg_L, deg_R, lag
        )

        lsd_L = compute_lsd(ref_L_al, deg_L_al, sr)
        lsd_R = compute_lsd(ref_R_al, deg_R_al, sr)
        lsd_avg = (lsd_L + lsd_R) / 2

        lsd_bands_L = compute_lsd_per_band(ref_L_al, deg_L_al, sr, OCTAVE_BANDS)
        lsd_bands_R = compute_lsd_per_band(ref_R_al, deg_R_al, sr, OCTAVE_BANDS)

        ild_error_avg, ild_errors, ild_ref, ild_deg = compute_ild_error(
            ref_L_al, ref_R_al, deg_L_al, deg_R_al, sr, OCTAVE_BANDS
        )

        print(
            f"  {var['key']:>6}: lag={lag:>6} próbek | "
            f"LSD_L={lsd_L:.2f} dB  LSD_R={lsd_R:.2f} dB  "
            f"LSD_avg={lsd_avg:.2f} dB  |  ILD_err={ild_error_avg:.2f} dB"
        )

        row = {
            "task_id": task["id"],
            "instrument": task["name"],
            "pomieszczenie": task["room"],
            "pozycja": task["pos"],
            "typ": var["label"],
            "typ_kod": var["key"],
            "lag_samples": lag,
            "lag_ms": round(1000.0 * lag / sr, 3),
            "LSD_L": round(lsd_L, 3) if not np.isnan(lsd_L) else "",
            "LSD_R": round(lsd_R, 3) if not np.isnan(lsd_R) else "",
            "LSD_avg": round(lsd_avg, 3) if not np.isnan(lsd_avg) else "",
            "ILD_error_avg": round(ild_error_avg, 3),
        }

        for band in OCTAVE_BANDS:
            lo, hi = band
            lsd_b = (lsd_bands_L[band] + lsd_bands_R[band]) / 2
            row[f"LSD_{lo}-{hi}Hz"] = round(lsd_b, 3) if not np.isnan(lsd_b) else ""

        for band in OCTAVE_BANDS:
            lo, hi = band
            row[f"ILD_err_{lo}-{hi}Hz"] = round(ild_errors[band], 3)

        all_results.append(row)

    print()

# =====================================================
# ZAPIS CSV
# =====================================================

if all_results:
    fieldnames = list(all_results[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_results)

print()
print("=" * 75)
print("PODSUMOWANIE")
print("=" * 75)
print()

by_type = {}
for row in all_results:
    key = row["typ_kod"]
    if key not in by_type:
        by_type[key] = {"lsd": [], "ild": [], "lag_ms": []}

    if row["LSD_avg"] != "":
        by_type[key]["lsd"].append(float(row["LSD_avg"]))
    by_type[key]["ild"].append(float(row["ILD_error_avg"]))
    by_type[key]["lag_ms"].append(abs(float(row["lag_ms"])))

print(f"{'Typ':<25} {'Śr. LSD (dB)':>14} {'Śr. ILD err (dB)':>18} {'Śr. |lag| (ms)':>16}")
print("-" * 80)

for key in ["aur48", "aur24", "aur12", "anchor"]:
    if key in by_type and len(by_type[key]["ild"]) > 0:
        lsd_avg = np.mean(by_type[key]["lsd"]) if len(by_type[key]["lsd"]) > 0 else np.nan
        ild_avg = np.mean(by_type[key]["ild"])
        lag_avg = np.mean(by_type[key]["lag_ms"])
        label = [v["label"] for v in VARIANTS if v["key"] == key][0]
        print(f"{label:<25} {lsd_avg:>14.2f} {ild_avg:>18.2f} {lag_avg:>16.2f}")

print()
print(f"Wyniki zapisane: {OUTPUT_CSV}")
print()
print("INTERPRETACJA:")
print("  LSD: im NIŻSZE tym lepsze odwzorowanie barwy (0 = identyczne)")
print("  ILD error: im NIŻSZE tym lepsze odwzorowanie przestrzenności (0 = identyczne)")
print("  lag: wykryte przesunięcie czasowe próbki względem referencji")