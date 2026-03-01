from __future__ import annotations

import math
import os
import shutil
import signal
import struct
import subprocess
import threading
from pathlib import Path


class FFMpegSpectrumAnalyzer:
    """Streams PCM from ffmpeg and computes real-time spectrum band levels."""

    def __init__(
        self,
        *,
        sample_rate: int = 11025,
        window_samples: int = 1024,
        bands: int = 24,
    ) -> None:
        self.sample_rate = sample_rate
        self.window_samples = window_samples
        self.bands = bands

        self._ffmpeg_path = shutil.which("ffmpeg")
        self._proc: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._paused = False

        self._levels = [0.0 for _ in range(bands)]
        self._peaks = [0.0 for _ in range(bands)]
        self._band_peaks = [1e-6 for _ in range(bands)]
        self._noise_floor = [0.0 for _ in range(bands)]
        self._band_bins = self._build_band_bins()
        self._window = self._build_window()
        self._tilt = self._build_tilt()
        self._low_baseline = 1e-6
        self._beat_env = 0.0

    def available(self) -> bool:
        return self._ffmpeg_path is not None

    def start(self, track_path: Path) -> None:
        self.stop()
        if not self._ffmpeg_path:
            return

        self._band_peaks = [1e-6 for _ in range(self.bands)]
        self._noise_floor = [0.0 for _ in range(self.bands)]
        self._low_baseline = 1e-6
        self._beat_env = 0.0
        self._paused = False

        self._stop_event.clear()
        self._proc = subprocess.Popen(
            [
                self._ffmpeg_path,
                "-v",
                "error",
                "-re",
                "-i",
                str(track_path),
                "-f",
                "s16le",
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "-",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self._thread = threading.Thread(target=self._run, name="ffmpeg-analyzer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=0.5)

        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=0.5)

        self._proc = None
        self._thread = None
        self._paused = False

        with self._lock:
            self._levels = [v * 0.8 for v in self._levels]
            self._peaks = [v * 0.8 for v in self._peaks]

    def close(self) -> None:
        self.stop()

    def set_paused(self, paused: bool) -> None:
        proc = self._proc
        if not proc or proc.poll() is not None:
            self._paused = False
            return
        if self._paused == paused:
            return
        sig = signal.SIGSTOP if paused else signal.SIGCONT
        os.kill(proc.pid, sig)
        self._paused = paused

    def levels(self) -> list[float]:
        with self._lock:
            return list(self._levels)

    def peaks(self) -> list[float]:
        with self._lock:
            return list(self._peaks)

    def _run(self) -> None:
        proc = self._proc
        if not proc or not proc.stdout:
            return

        chunk_bytes = self.window_samples * 2

        while not self._stop_event.is_set():
            data = proc.stdout.read(chunk_bytes)
            if not data or len(data) < chunk_bytes:
                break

            samples = struct.unpack("<" + "h" * self.window_samples, data)
            raw = self._band_energies(samples)
            targets = self._shape_levels(raw)

            with self._lock:
                for i in range(self.bands):
                    prev = self._levels[i]
                    target = targets[i]

                    # Fast attack, slower release for fluid but punchy movement.
                    if target >= prev:
                        level = prev * 0.35 + target * 0.65
                    else:
                        level = prev * 0.90 + target * 0.10
                    self._levels[i] = level

                    peak = self._peaks[i]
                    if level >= peak:
                        self._peaks[i] = level
                    else:
                        self._peaks[i] = peak * 0.965

        self._proc = None

    def _build_band_bins(self) -> list[tuple[int, int, int]]:
        freqs = self._band_frequencies()
        max_bin = max(2, (self.window_samples // 2) - 1)
        bins: list[tuple[int, int, int]] = []
        for freq in freqs:
            k = int(0.5 + (self.window_samples * freq) / self.sample_rate)
            k = min(max_bin, max(1, k))
            bins.append((max(1, k - 1), k, min(max_bin, k + 1)))
        return bins

    def _build_window(self) -> list[float]:
        if self.window_samples <= 1:
            return [1.0]
        return [
            0.5 - 0.5 * math.cos((2.0 * math.pi * i) / (self.window_samples - 1))
            for i in range(self.window_samples)
        ]

    def _build_tilt(self) -> list[float]:
        # Slight low-end emphasis to counter typical terminal-speaker perception.
        if self.bands <= 1:
            return [1.0]
        out: list[float] = []
        for i in range(self.bands):
            pos = i / (self.bands - 1)
            out.append(1.35 - 0.40 * pos)
        return out

    def _band_frequencies(self) -> list[float]:
        low = 40.0
        high = min(5000.0, self.sample_rate / 2.0 - 50.0)
        if self.bands <= 1:
            return [(low + high) / 2.0]

        out: list[float] = []
        ratio = (high / low) ** (1.0 / (self.bands - 1))
        for i in range(self.bands):
            out.append(low * (ratio**i))
        return out

    def _band_energies(self, samples: tuple[int, ...]) -> list[float]:
        energies: list[float] = []
        for k0, k1, k2 in self._band_bins:
            p0 = self._goertzel_power(samples, k0)
            p1 = self._goertzel_power(samples, k1)
            p2 = self._goertzel_power(samples, k2)
            # Weighted 3-bin blend captures beats between center frequencies.
            energies.append(max(0.0, p0 * 0.22 + p1 * 0.56 + p2 * 0.22))
        return energies

    def _shape_levels(self, raw: list[float]) -> list[float]:
        if not raw:
            return [0.0 for _ in range(self.bands)]

        normed: list[float] = []
        for i in range(self.bands):
            energy = raw[i] * self._tilt[i]

            floor = self._noise_floor[i] * 0.997 + energy * 0.003
            self._noise_floor[i] = floor
            gated = max(0.0, energy - floor * 1.10)

            band_peak = max(self._band_peaks[i] * 0.992, gated, 1e-6)
            self._band_peaks[i] = band_peak

            x = gated / band_peak
            compressed = math.log1p(x * 10.0) / math.log1p(10.0)
            normed.append(min(1.0, max(0.0, compressed**0.82)))

        # Low-end transient envelope to make kick/thump visually obvious.
        low_count = min(4, len(raw))
        low_energy = 0.0
        for i in range(low_count):
            low_energy += raw[i] * self._tilt[i]
        low_energy /= max(1, low_count)

        self._low_baseline = self._low_baseline * 0.985 + low_energy * 0.015
        beat_flux = max(0.0, low_energy - self._low_baseline * 1.08)
        beat_drive = min(1.0, beat_flux / (self._low_baseline + 1e-6))
        self._beat_env = max(self._beat_env * 0.84, beat_drive)

        if self._beat_env > 0:
            for i in range(min(6, len(normed))):
                lift = self._beat_env * (0.34 - 0.05 * i)
                normed[i] = min(1.0, normed[i] + max(0.0, lift))

        # Diffuse neighboring bands slightly for less jagged motion.
        if len(normed) >= 3:
            blurred = [normed[0]]
            for i in range(1, len(normed) - 1):
                blurred.append(
                    normed[i - 1] * 0.22 + normed[i] * 0.56 + normed[i + 1] * 0.22
                )
            blurred.append(normed[-1])
            return blurred
        return normed

    def _goertzel_power(self, samples: tuple[int, ...], k: int) -> float:
        omega = (2.0 * math.pi * k) / self.window_samples
        coeff = 2.0 * math.cos(omega)
        s_prev = 0.0
        s_prev2 = 0.0
        for i, sample in enumerate(samples):
            weighted = float(sample) * self._window[i]
            s = weighted + coeff * s_prev - s_prev2
            s_prev2 = s_prev
            s_prev = s
        return s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2
