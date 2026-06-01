#!/usr/bin/env python3
"""Auto-tune CFAR thresholds from recorded ADC data.

Loads one or more ``adc_data.bin`` files with known labels
(weapon / no_weapon) and searches for CFAR parameters that maximise
the separation between weapon and no-weapon scores.

Usage::

    python3 -m layer1_sensor_hub.mmwave_dca.auto_cfar_tune \\
        --weapon captures/weapon_1m.bin \\
        --no-weapon captures/baseline_1m.bin \\
        --chirps 48 --rx 4 --samples 384
"""

from __future__ import annotations

import argparse
import json
import itertools
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np

from .adc_reader import AdcCaptureShape, read_adc_data
from .mmwave_raw_adc_detector import MmweaponCfarParams, RawAdcWeaponDetector


@dataclass
class CfarTuneResult:
    threshold_scale: float
    noise_floor_offset_db: float
    weapon_mean: float
    no_weapon_mean: float
    separation: float
    weapon_scores: list[float] = field(default_factory=list)
    no_weapon_scores: list[float] = field(default_factory=list)


def load_frames(path: Path, chirps: int, rx: int, samples: int, max_frames: int = 0) -> np.ndarray:
    shape = AdcCaptureShape.from_bytes(
        path.stat().st_size, chirps=chirps, rx=rx, samples=samples
    )
    if max_frames > 0 and shape.frames > max_frames:
        shape = AdcCaptureShape(frames=max_frames, chirps=chirps, rx=rx, samples=samples)
    return read_adc_data(path, shape, allow_truncate=True)


def score_all_frames(
    detector: RawAdcWeaponDetector, frames: np.ndarray
) -> list[float]:
    scores: list[float] = []
    for i in range(frames.shape[0]):
        result = detector.detect(frames[i], frame_number=i)
        scores.append(result.weapon_score)
    return scores


def tune(
    weapon_path: Path,
    no_weapon_path: Path,
    chirps: int,
    rx: int,
    samples: int,
    max_frames: int = 200,
    threshold_scales: Optional[list[float]] = None,
    noise_offsets: Optional[list[float]] = None,
) -> list[CfarTuneResult]:
    if threshold_scales is None:
        threshold_scales = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]
    if noise_offsets is None:
        noise_offsets = [0.0, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]

    print(f"Loading weapon data from {weapon_path}...")
    weapon_frames = load_frames(weapon_path, chirps, rx, samples, max_frames)
    print(f"  {weapon_frames.shape[0]} frames")

    print(f"Loading no-weapon data from {no_weapon_path}...")
    no_weapon_frames = load_frames(no_weapon_path, chirps, rx, samples, max_frames)
    print(f"  {no_weapon_frames.shape[0]} frames")

    results: list[CfarTuneResult] = []
    total = len(threshold_scales) * len(noise_offsets)
    idx = 0

    for ts, noff in itertools.product(threshold_scales, noise_offsets):
        idx += 1
        cfar = MmweaponCfarParams(threshold_scale=ts, noise_floor_offset_db=noff)
        detector = RawAdcWeaponDetector(cfar=cfar)

        w_scores = score_all_frames(detector, weapon_frames)
        n_scores = score_all_frames(detector, no_weapon_frames)

        w_mean = float(np.mean(w_scores))
        n_mean = float(np.mean(n_scores))
        separation = w_mean - n_mean

        results.append(CfarTuneResult(
            threshold_scale=ts,
            noise_floor_offset_db=noff,
            weapon_mean=w_mean,
            no_weapon_mean=n_mean,
            separation=separation,
            weapon_scores=w_scores,
            no_weapon_scores=n_scores,
        ))

        bar = "#" * int(idx / total * 30) + "-" * (30 - int(idx / total * 30))
        sys.stdout.write(f"\r  [{bar}] {idx}/{total}  ts={ts:.1f} noff={noff:.1f}  sep={separation:.4f}")
        sys.stdout.flush()

    print()

    results.sort(key=lambda r: r.separation, reverse=True)
    return results


def _main() -> None:
    parser = argparse.ArgumentParser(description="Auto-tune CFAR thresholds")
    parser.add_argument("--weapon", required=True, type=Path, help="Weapon ADC file")
    parser.add_argument("--no-weapon", required=True, type=Path, help="No-weapon ADC file")
    parser.add_argument("--chirps", type=int, default=48)
    parser.add_argument("--rx", type=int, default=4)
    parser.add_argument("--samples", type=int, default=384)
    parser.add_argument("--max-frames", type=int, default=200)
    parser.add_argument("--output", "-o", type=Path, default=None, help="Save results JSON")
    args = parser.parse_args()

    results = tune(
        args.weapon, args.no_weapon,
        chirps=args.chirps, rx=args.rx, samples=args.samples,
        max_frames=args.max_frames,
    )

    print(f"\n{'='*60}")
    print(f"{'Top 10 CFAR parameter sets':^60}")
    print(f"{'='*60}")
    print(f"{'Rank':>5}  {'threshold_scale':>16}  {'noise_offset_db':>16}  {'sep':>8}  {'w_mean':>8}  {'n_mean':>8}")
    print("-" * 70)
    for i, r in enumerate(results[:10]):
        print(f"{i+1:>5}  {r.threshold_scale:>16.2f}  {r.noise_floor_offset_db:>16.2f}  {r.separation:>8.4f}  {r.weapon_mean:>8.4f}  {r.no_weapon_mean:>8.4f}")
    print()

    best = results[0]
    print(f"Best: threshold_scale={best.threshold_scale}, noise_floor_offset_db={best.noise_floor_offset_db}")
    print(f"  Weapon mean:    {best.weapon_mean:.4f}")
    print(f"  No-weapon mean: {best.no_weapon_mean:.4f}")
    print(f"  Separation:     {best.separation:.4f}")

    if args.output:
        data = []
        for r in results:
            data.append({
                "threshold_scale": r.threshold_scale,
                "noise_floor_offset_db": r.noise_floor_offset_db,
                "weapon_mean": r.weapon_mean,
                "no_weapon_mean": r.no_weapon_mean,
                "separation": r.separation,
            })
        args.output.write_text(json.dumps(data, indent=2))
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    _main()
