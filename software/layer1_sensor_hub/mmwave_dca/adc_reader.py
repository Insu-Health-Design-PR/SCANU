"""Read raw ADC captures generated through DCA1000EVM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

IqOrder = Literal["ti", "iq"]


@dataclass(frozen=True)
class AdcCaptureShape:
    """Expected dimensions for a raw ADC capture."""

    frames: int
    chirps: int
    rx: int
    samples: int

    @property
    def complex_samples(self) -> int:
        return self.frames * self.chirps * self.rx * self.samples

    @property
    def int16_values(self) -> int:
        return self.complex_samples * 2

    @classmethod
    def from_bytes(cls, nbytes: int, *, chirps: int, rx: int, samples: int) -> AdcCaptureShape:
        frames = nbytes // (2 * chirps * rx * samples * 2)
        return cls(frames=frames, chirps=chirps, rx=rx, samples=samples)


def _to_complex_iq(raw: np.ndarray, iq_order: IqOrder) -> np.ndarray:
    if iq_order == "iq":
        return raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)

    if iq_order != "ti":
        raise ValueError("iq_order must be 'ti' or 'iq'")

    usable = raw.size - (raw.size % 4)
    raw = raw[:usable]
    complex_data = np.empty(raw.size // 2, dtype=np.complex64)
    complex_data[0::2] = raw[0::4].astype(np.float32) + 1j * raw[2::4].astype(np.float32)
    complex_data[1::2] = raw[1::4].astype(np.float32) + 1j * raw[3::4].astype(np.float32)
    return complex_data


def read_adc_data(
    path: str | Path,
    shape: AdcCaptureShape,
    *,
    iq_order: IqOrder = "ti",
    allow_truncate: bool = False,
) -> np.ndarray:
    """Load ``adc_data.bin`` and reshape to ``[frames, chirps, rx, samples]``.

    ``iq_order='ti'`` handles the common DCA1000 complex layout:
    ``I0, I1, Q0, Q1, I2, I3, Q2, Q3...``.

    ``iq_order='iq'`` handles a simple ``I,Q,I,Q...`` layout.
    """

    raw = np.fromfile(Path(path), dtype=np.int16)
    if raw.size < shape.int16_values:
        raise ValueError(
            f"ADC file is too small: got {raw.size} int16 values, expected {shape.int16_values}. "
            "Check frames/chirps/rx/samples or confirm the DCA1000 capture did not drop early."
        )

    if raw.size > shape.int16_values:
        if not allow_truncate:
            raise ValueError(
                f"ADC file has extra data: got {raw.size} int16 values, expected {shape.int16_values}. "
                "Pass allow_truncate=True only if you intentionally captured extra frames."
            )
        raw = raw[: shape.int16_values]

    complex_data = _to_complex_iq(raw, iq_order)
    if complex_data.size != shape.complex_samples:
        raise ValueError(
            f"Complex sample count mismatch: got {complex_data.size}, expected {shape.complex_samples}."
        )
    return complex_data.reshape(shape.frames, shape.chirps, shape.rx, shape.samples)


def range_fft(adc_frame: np.ndarray, *, window: bool = True) -> np.ndarray:
    """Compute range FFT for one frame shaped ``[chirps, rx, samples]``."""

    data = np.asarray(adc_frame, dtype=np.complex64)
    if window:
        data = data * np.hanning(data.shape[-1])[None, None, :]
    return np.fft.fft(data, axis=-1)


def range_doppler_map(adc_frame: np.ndarray, *, window: bool = True) -> np.ndarray:
    """Return RX-combined range-Doppler magnitude in dB for one ADC frame."""

    data = np.asarray(adc_frame, dtype=np.complex64)
    if window:
        data = data * np.hanning(data.shape[-1])[None, None, :]
        data = data * np.hanning(data.shape[0])[:, None, None]

    rfft = np.fft.fft(data, axis=-1)
    dfft = np.fft.fftshift(np.fft.fft(rfft, axis=0), axes=0)
    mag = np.sum(np.abs(dfft), axis=1)
    return 20.0 * np.log10(mag + 1e-6)


def compute_mti(adc_frame: np.ndarray, alpha: float = 0.8) -> np.ndarray:
    """Moving Target Indicator filter via exponential background subtraction.

    Subtracts an exponentially-weighted background estimate from each
    chirp's range profile to suppress static clutter.

    Args:
        adc_frame: complex64 shaped ``[chirps, rx, samples]``.
        alpha: forgetting factor (0..1). Higher = slower adaptation.

    Returns:
        MTI-filtered frame, same shape as input.
    """

    data = np.asarray(adc_frame, dtype=np.complex64)
    bg = np.zeros_like(data[0])
    result = np.empty_like(data)
    for i in range(data.shape[0]):
        result[i] = data[i] - bg
        bg = alpha * bg + (1 - alpha) * data[i]
    return result


def coherence_factor(adc_frame: np.ndarray) -> np.ndarray:
    """Per-range-bin coherence across RX antennas.

    High coherence suggests a compact reflector (like a firearm),
    while distributed body returns have lower coherence.

    Args:
        adc_frame: complex64 shaped ``[chirps, rx, samples]``.

    Returns:
        Coherence per range bin, shape ``[samples]``.
    """

    data = np.asarray(adc_frame, dtype=np.complex64)
    rfft = np.fft.fft(data, axis=-1)
    coherent_sum = np.abs(np.sum(rfft, axis=1))
    incoherent_sum = np.sum(np.abs(rfft), axis=1)
    coherence = coherent_sum / (incoherent_sum + 1e-10)
    return np.mean(coherence, axis=0)
