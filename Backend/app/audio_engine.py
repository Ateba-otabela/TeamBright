from __future__ import annotations

import io
import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

MAX_AUDIO_BYTES = 30 * 1024 * 1024
KEY_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _read_wave(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data), "rb") as audio:
        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()
        sample_rate = audio.getframerate()
        frames = audio.readframes(audio.getnframes())
    if sample_width == 1:
        samples = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128) / 128
    elif sample_width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768
    elif sample_width == 3:
        packed = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        values = (
            packed[:, 0].astype(np.int32)
            | (packed[:, 1].astype(np.int32) << 8)
            | (packed[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values - 0x1000000, values)
        samples = values.astype(np.float32) / 8388608
    elif sample_width == 4:
        samples = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648
    else:
        raise ValueError("Unsupported WAV bit depth")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if sample_rate <= 0 or samples.size == 0:
        raise ValueError("Audio file contains no samples")
    return samples, sample_rate


def _read_audio(data: bytes) -> tuple[np.ndarray, int]:
    librosa_error: Exception | None = None
    try:
        import librosa

        samples, sample_rate = librosa.load(io.BytesIO(data), sr=22050, mono=True)
        if samples.size:
            return np.asarray(samples, dtype=np.float32), int(sample_rate)
    except Exception as exc:
        librosa_error = exc

    try:
        import soundfile as sf

        samples, sample_rate = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        mono = samples.mean(axis=1)
        if mono.size:
            return mono, int(sample_rate)
    except (RuntimeError, ValueError, OSError):
        pass

    try:
        return _read_wave(data)
    except (wave.Error, EOFError, ValueError) as exc:
        if librosa_error is not None:
            raise ValueError("Could not decode audio; upload a valid WAV or MP3 file") from librosa_error
        raise ValueError("Could not decode audio; upload a valid WAV or MP3 file") from exc


def _frame_rms(samples: np.ndarray, frame_size: int = 2048, hop: int = 512) -> np.ndarray:
    if samples.size < frame_size:
        samples = np.pad(samples, (0, frame_size - samples.size))
    frames = np.lib.stride_tricks.sliding_window_view(samples, frame_size)[::hop]
    return np.sqrt(np.mean(np.square(frames), axis=1) + 1e-12)


def _fallback_chroma(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    window_size = min(8192, max(1024, 2 ** int(math.floor(math.log2(max(1024, samples.size))))))
    if samples.size < window_size:
        samples = np.pad(samples, (0, window_size - samples.size))
    window = np.hanning(window_size)
    spectra = np.abs(np.fft.rfft(samples[:window_size] * window))
    frequencies = np.fft.rfftfreq(window_size, 1 / sample_rate)
    valid = frequencies > 20
    midi = np.rint(69 + 12 * np.log2(np.maximum(frequencies[valid], 1) / 440)).astype(int)
    chroma = np.zeros(12, dtype=np.float64)
    np.add.at(chroma, midi % 12, spectra[valid])
    return chroma


def _hook_timestamp(rms: np.ndarray, sample_rate: int, hop: int = 512) -> float:
    if rms.size < 2:
        return 0.0
    window_frames = max(1, int(sample_rate / hop))
    if rms.size < window_frames * 2:
        return 0.0
    smoothed = np.convolve(rms, np.ones(window_frames) / window_frames, mode="valid")
    baseline = float(np.percentile(smoothed, 30))
    threshold = max(baseline * 1.65, float(np.percentile(smoothed, 65)))
    sustained_frames = max(1, int(1.0 * sample_rate / hop))
    above = smoothed >= threshold
    run = 0
    for index, active in enumerate(above):
        run = run + 1 if active else 0
        if run >= sustained_frames:
            return max(0.0, (index - run + 1) * hop / sample_rate)
    return 0.0


def extract_audio_dna(data: bytes, filename: str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".wav", ".mp3"}:
        raise ValueError("Audio file must have a .wav or .mp3 extension")
    if not data:
        raise ValueError("Audio file is empty")
    if len(data) > MAX_AUDIO_BYTES:
        raise ValueError("Audio file exceeds the 30 MB upload limit")

    samples, sample_rate = _read_audio(data)
    if samples.size / sample_rate > 600:
        raise ValueError("Audio file must not exceed 10 minutes")
    samples = np.nan_to_num(samples.astype(np.float32))
    samples = np.clip(samples, -1.0, 1.0)
    rms_frames = _frame_rms(samples)
    rms_energy = float(np.sqrt(np.mean(np.square(samples)) + 1e-12))
    power_score = min(100.0, rms_energy * 250.0)
    try:
        import librosa

        chroma = librosa.feature.chroma_stft(y=samples, sr=sample_rate)
        key_energy = np.asarray(chroma).mean(axis=1)
        tempo = librosa.beat.beat_track(y=samples, sr=sample_rate, units="time")[0]
        tempo_bpm = float(np.asarray(tempo).reshape(-1)[0])
        onsets = librosa.onset.onset_detect(y=samples, sr=sample_rate, units="time")
        flow_density = float(len(onsets) / max(samples.size / sample_rate, 1e-6))
        brightness_hz = float(librosa.feature.spectral_centroid(y=samples, sr=sample_rate).mean())
        hook_timestamp_sec = _hook_timestamp(rms_frames, sample_rate)
    except Exception:
        key_energy = _fallback_chroma(samples, sample_rate)
        tempo_bpm = _estimate_tempo(rms_frames, sample_rate)
        flow_density = _estimate_flow(rms_frames, sample_rate)
        brightness_hz = _estimate_brightness(samples, sample_rate)
        hook_timestamp_sec = _hook_timestamp(rms_frames, sample_rate)

    key_index = int(np.argmax(key_energy) % 12)
    if not math.isfinite(tempo_bpm) or tempo_bpm <= 0:
        tempo_bpm = 120.0
    return {
        "musical_key": KEY_NAMES[key_index],
        "key_index": key_index,
        "tempo_bpm": round(float(tempo_bpm), 2),
        "flow_density": round(max(0.0, float(flow_density)), 4),
        "power_score": round(power_score, 2),
        "rms_energy": round(rms_energy, 6),
        "brightness_hz": round(max(0.0, float(brightness_hz)), 2),
        "hook_timestamp_sec": round(max(0.0, float(hook_timestamp_sec)), 2),
    }


def _estimate_tempo(rms: np.ndarray, sample_rate: int) -> float:
    envelope = np.diff(rms, prepend=rms[0])
    envelope -= envelope.mean()
    if envelope.size < 3:
        return 120.0
    correlation = np.correlate(envelope, envelope, mode="full")[envelope.size - 1 :]
    frame_rate = sample_rate / 512
    min_lag = max(1, int(frame_rate * 60 / 220))
    max_lag = min(len(correlation) - 1, int(frame_rate * 60 / 45))
    if max_lag <= min_lag:
        return 120.0
    lag = min_lag + int(np.argmax(correlation[min_lag : max_lag + 1]))
    return frame_rate * 60 / lag


def _estimate_flow(rms: np.ndarray, sample_rate: int) -> float:
    if rms.size < 2:
        return 0.0
    novelty = np.diff(rms, prepend=rms[0])
    threshold = max(float(np.std(novelty)) * 0.8, 1e-6)
    peaks = np.flatnonzero((novelty > threshold) & (novelty >= np.roll(novelty, 1)))
    return len(peaks) / max(len(rms) * 512 / sample_rate, 1e-6)


def _estimate_brightness(samples: np.ndarray, sample_rate: int) -> float:
    analysis_samples = samples[: min(samples.size, 65536)]
    spectrum = np.abs(np.fft.rfft(analysis_samples))
    frequencies = np.fft.rfftfreq(analysis_samples.size, 1 / sample_rate)
    total = float(spectrum.sum())
    return float(np.sum(frequencies * spectrum) / total) if total else 0.0


def _similarity(left: float, right: float, scale: float) -> float:
    if scale <= 0:
        return 100.0 if math.isclose(left, right) else 0.0
    return max(0.0, min(100.0, 100.0 * (1.0 - abs(left - right) / scale)))


def compare_audio_dna(benchmark: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
    key_shift = (int(benchmark["key_index"]) - int(demo["key_index"]) + 6) % 12 - 6
    tone_match = max(0.0, 100.0 - 16.67 * abs(key_shift))
    tempo_match = _similarity(
        float(demo["tempo_bpm"]), float(benchmark["tempo_bpm"]), max(float(benchmark["tempo_bpm"]), 1.0)
    )
    density_match = _similarity(
        float(demo["flow_density"]),
        float(benchmark["flow_density"]),
        max(float(benchmark["flow_density"]), 0.25),
    )
    flow_match = 0.7 * tempo_match + 0.3 * density_match
    rms_match = _similarity(
        float(demo["rms_energy"]), float(benchmark["rms_energy"]), max(float(benchmark["rms_energy"]), 0.05)
    )
    brightness_match = _similarity(
        float(demo["brightness_hz"]),
        float(benchmark["brightness_hz"]),
        max(float(benchmark["brightness_hz"]), 500.0),
    )
    power_match = 0.8 * rms_match + 0.2 * brightness_match
    hook_scale = max(float(benchmark["hook_timestamp_sec"]), 18.0)
    hook_timing_match = _similarity(
        float(demo["hook_timestamp_sec"]), float(benchmark["hook_timestamp_sec"]), hook_scale
    )
    score = 0.25 * tone_match + 0.30 * flow_match + 0.25 * power_match + 0.20 * hook_timing_match
    verdict = "RELEASE_READY" if score >= 80 else "NEEDS_STUDIO_TWEAKS" if score >= 55 else "HIGH_FLOP_RISK"
    rms_boost = max(
        0.0,
        (float(benchmark["rms_energy"]) / max(float(demo["rms_energy"]), 1e-6) - 1.0) * 100.0,
    )
    intro_trim = max(
        0.0, float(demo["hook_timestamp_sec"]) - float(benchmark["hook_timestamp_sec"])
    )
    bpm_change = float(benchmark["tempo_bpm"]) - float(demo["tempo_bpm"])
    fixes = [
        {
            "dimension": "tone",
            "title": "Align the musical key",
            "instruction": f"Shift the demo by {key_shift:+d} semitones to match {benchmark['musical_key']}."
            if key_shift
            else f"Keep the current {benchmark['musical_key']} key.",
            "semitone_shift": key_shift,
        },
        {
            "dimension": "flow",
            "title": "Match the viral groove",
            "instruction": f"Adjust tempo by {bpm_change:+.1f} BPM toward {benchmark['tempo_bpm']:.1f} BPM.",
            "bpm_adjustment": round(bpm_change, 1),
        },
        {
            "dimension": "power",
            "title": "Match broadcast punch",
            "instruction": f"Increase RMS energy by approximately {rms_boost:.0f}%."
            if rms_boost > 0
            else "RMS energy is at or above the benchmark; preserve headroom and avoid clipping.",
            "rms_boost_pct": round(rms_boost, 1),
        },
        {
            "dimension": "hook_timing",
            "title": "Bring the hook forward",
            "instruction": f"Trim approximately {intro_trim:.1f} seconds from the intro."
            if intro_trim > 0
            else "The hook arrives as early as or earlier than the benchmark.",
            "intro_trim_sec": round(intro_trim, 1),
        },
    ]
    return {
        "tone_match": round(tone_match, 1),
        "flow_match": round(flow_match, 1),
        "power_match": round(power_match, 1),
        "hook_timing_match": round(hook_timing_match, 1),
        "hit_readiness_score": round(score, 1),
        "verdict": verdict,
        "studio_fixes": fixes,
    }
