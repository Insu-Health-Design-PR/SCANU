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


# ── MIMO helpers (TDM 3 TX × 4 RX = 12 virtual channels) ────────────────

MIMO_LOOPS = 16
MIMO_NUM_TX = 3


def mimo_demux(adc_frame: np.ndarray) -> np.ndarray:
    """Demultiplex a TDM-MIMO frame into ``[loops, tx, rx, samples]``.

    Input shape: ``[loops * num_tx, rx, samples]`` (48 chirps, 4 RX, 384 samples).
    Output shape: ``[loops, num_tx, rx, samples]``.

    The 3 TX chirps fire in sequence per loop: TX1, TX2, TX3.
    """
    total_chirps = adc_frame.shape[0]
    if total_chirps % MIMO_NUM_TX != 0:
        raise ValueError(f"Total chirps {total_chirps} not divisible by {MIMO_NUM_TX} TX")
    loops = total_chirps // MIMO_NUM_TX
    return adc_frame.reshape(loops, MIMO_NUM_TX, *adc_frame.shape[1:])


def mimo_range_doppler(mimo_frame: np.ndarray, tx_idx: int = 0) -> np.ndarray:
    """Range-Doppler map for one TX, sum across RX.

    Uses TX1 by default (index 0). TX1-only gives same noise floor as
    legacy 4-RX processing. TX2/TX3 are used only for angle estimation.

    Input: ``[loops, num_tx, rx, samples]`` (16, 3, 4, 384).
    ``tx_idx``: TX antenna index (0=TX1, 1=TX2, 2=TX3).
    Returns: RX-combined RD map in dB, shape ``[doppler, range]``.
    """
    loops, num_tx, rx, samples = mimo_frame.shape
    data = np.asarray(mimo_frame, dtype=np.complex64)
    data *= np.hanning(samples)[None, None, None, :]
    data *= np.hanning(loops)[:, None, None, None]

    rfft = np.fft.fft(data, axis=-1)
    dfft = np.fft.fftshift(np.fft.fft(rfft, axis=0), axes=0)

    mag = np.sum(np.abs(dfft[:, tx_idx]), axis=1)
    return 20.0 * np.log10(mag + 1e-6)


def mimo_virtual_snapshot(
    mimo_frame: np.ndarray, range_bin: int, doppler_bin: int
) -> np.ndarray:
    """Extract the complex snapshot across the 12 virtual channels.

    The virtual array order: TX1+RX1..RX4, TX2+RX1..RX4, TX3+RX1..RX4.
    Returns: complex64 array of length 12.
    """
    loops, num_tx, rx, samples = mimo_frame.shape
    data = np.asarray(mimo_frame, dtype=np.complex64)

    data *= np.hanning(samples)[None, None, None, :]

    rfft = np.fft.fft(data, axis=-1)
    rfft *= np.hanning(loops)[:, None, None, None]
    dfft = np.fft.fftshift(np.fft.fft(rfft, axis=0), axes=0)

    doppler_idx = dfft.shape[0] // 2 + doppler_bin
    if doppler_idx < 0 or doppler_idx >= dfft.shape[0]:
        doppler_idx = dfft.shape[0] // 2
    if range_bin < 0 or range_bin >= samples:
        range_bin = 0

    snapshot = dfft[doppler_idx, :, :, range_bin]
    return snapshot.flatten()


def mimo_beamform_angle(
    virtual_snapshot: np.ndarray,
    num_virtual: int = 12,
    n_fft: int = 128,
    d_lambda: float = 0.5,
) -> float:
    """Estimate angle from a virtual array snapshot.

    Applies RX phase calibration (180° correction on every other element
    per TX group, matching ``compRangeBiasAndRxChanPhase``) before
    correlation-based angle estimation.

    Uses adjacent-element correlation which is robust to small arrays.
    ``num_virtual=8`` for azimuth (TX1+RX + TX2+RX).

    Returns: angle in degrees.
    """
    x = virtual_snapshot.copy()
    if len(x) < 2:
        return 0.0

    # Apply phase calibration: every other RX element per TX group
    # gets 180° correction (matching compRangeBiasAndRxChanPhase in cfg)
    cal = np.ones(len(x), dtype=np.complex64)
    for group_start in range(0, len(x), 4):
        for i in [1, 3]:
            idx = group_start + i
            if idx < len(x):
                cal[idx] = -1
    x = x * cal

    # Correlation-based angle estimation
    corr = np.mean(x[1:] * np.conj(x[:-1]))
    delta_phi = np.angle(corr)
    if abs(delta_phi) > 1e-6:
        est_sin = delta_phi / (2.0 * np.pi * d_lambda)
        if abs(est_sin) <= 1.0:
            return float(np.rad2deg(np.arcsin(est_sin)))
    return 0.0


def mimo_coherence(mimo_frame: np.ndarray) -> np.ndarray:
    """Per-range-bin coherence — per-TX across 4 RX, then take max across TX.

    This preserves the weapon signature (coherent across RX for a given TX)
    while avoiding TX spatial phase differences from washing out the result.

    Input: ``[loops, num_tx, rx, samples]``.
    Returns: coherence per range bin, shape ``[samples]``.
    """
    data = np.asarray(mimo_frame, dtype=np.complex64)
    rfft = np.fft.fft(data, axis=-1)

    loops, num_tx, rx = rfft.shape[:3]
    max_coherence = np.zeros(rfft.shape[-1], dtype=np.float32)
    for tx in range(num_tx):
        tx_data = rfft[:, tx]
        coherent_sum = np.abs(np.sum(tx_data, axis=1))
        incoherent_sum = np.sum(np.abs(tx_data), axis=1)
        coh = coherent_sum / (incoherent_sum + 1e-10)
        coh_avg = np.mean(coh, axis=0)
        np.maximum(max_coherence, coh_avg, out=max_coherence)
    return max_coherence


def mimo_phase_stability(mimo_frame: np.ndarray) -> np.ndarray:
    """Per-range-bin phase stability — per-TX max across 4 RX.

    Input: ``[loops, num_tx, rx, samples]``.
    Returns: phase stability per range bin, shape ``[samples]``.
    """
    data = np.asarray(mimo_frame, dtype=np.complex64)
    rfft = np.fft.fft(data, axis=-1)

    loops, num_tx, rx = rfft.shape[:3]
    max_pstab = np.zeros(rfft.shape[-1], dtype=np.float32)
    for tx in range(num_tx):
        tx_data = rfft[:, tx]
        sum_v = np.sum(tx_data, axis=1)
        phase = np.angle(sum_v)
        mean_cos = np.mean(np.cos(phase), axis=0)
        mean_sin = np.mean(np.sin(phase), axis=0)
        pstab = np.sqrt(mean_cos ** 2 + mean_sin ** 2)
        np.maximum(max_pstab, pstab, out=max_pstab)
    return max_pstab
