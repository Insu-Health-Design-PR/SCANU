"""
Multimodal capture dataset: group ``*_capture.json``, ``*_report.json``, and ``.mp4`` by stem
under ``safe/<scenario>/`` and ``unsafe/<scenario>/`` (e.g. ``~/Desktop/collecting_data``).

Produces ML-ready structures:
  - :class:`CaptureSample` — paths + labels + scenario
  - :func:`load_capture_json` — parsed dict
  - :func:`capture_frames_to_feature_matrix` — ``(T, D)`` float32 numpy (tabular / fusion models)

Video pixels are not stored in capture JSON; use :attr:`CaptureSample.mp4_path` with OpenCV
or a separate image pipeline to train YOLO/CNN on cropped thermal panels.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

import numpy as np

SplitName = Literal["safe", "unsafe"]


@dataclass(frozen=True, slots=True)
class CaptureSample:
    """One logical capture: same basename for mp4 / capture / report when present."""

    stem: str
    """File basename without extension (e.g. ``safe_empty_room_5ft_r01_20260406T145713``)."""

    scenario: str
    """Leaf folder name under ``safe`` or ``unsafe`` (e.g. ``empty_room``, ``concealed_weapon``)."""

    split: SplitName
    """``safe`` or ``unsafe``."""

    label_binary: int
    """0 = safe, 1 = unsafe."""

    scenario_index: int
    """Integer id for the scenario string (stable ordering within a scan)."""

    dir_path: Path
    """Directory containing the artifacts."""

    mp4_path: Path | None
    capture_json_path: Path | None
    report_json_path: Path | None

    @property
    def has_capture_json(self) -> bool:
        return self.capture_json_path is not None and self.capture_json_path.is_file()

    @property
    def has_report_json(self) -> bool:
        return self.report_json_path is not None and self.report_json_path.is_file()

    @property
    def has_mp4(self) -> bool:
        return self.mp4_path is not None and self.mp4_path.is_file()

    @property
    def is_complete_triplet(self) -> bool:
        return self.has_capture_json and self.has_report_json and self.has_mp4


def _scenario_index_map(root: Path) -> dict[tuple[SplitName, str], int]:
    """Stable integer id per (split, scenario) for embedding layers."""
    keys: list[tuple[SplitName, str]] = []
    for split in ("safe", "unsafe"):
        d = root / split
        if not d.is_dir():
            continue
        for child in sorted(p for p in d.iterdir() if p.is_dir()):
            keys.append((split, child.name))
    return {k: i for i, k in enumerate(keys)}


def _discover_stems_in_scenario_dir(scenario_dir: Path) -> set[str]:
    stems: set[str] = set()
    for p in scenario_dir.glob("*_capture.json"):
        if p.is_file():
            stems.add(p.name[: -len("_capture.json")])
    for p in scenario_dir.glob("*.mp4"):
        if p.is_file():
            stems.add(p.stem)
    return stems


# Default artifact name when exporting per-clip features (``export_clip_batch_npz``).
DEFAULT_EXPORT_SUFFIX = "_layer3.npz"


def exported_feature_path(
    sample: CaptureSample,
    export_root: Path | str,
    *,
    suffix: str = DEFAULT_EXPORT_SUFFIX,
) -> Path:
    """
    Stable output path for a clip's exported features, mirroring ``safe|unsafe/<scenario>/``.

    Example: ``export_root/unsafe/concealed_weapon/foo_2026_layer3.npz``
    """
    er = Path(export_root).expanduser().resolve()
    return er / sample.split / sample.scenario / f"{sample.stem}{suffix}"


def export_file_exists(
    sample: CaptureSample,
    export_root: Path | str,
    *,
    suffix: str = DEFAULT_EXPORT_SUFFIX,
) -> bool:
    """True if ``exported_feature_path(...)`` is an existing regular file."""
    p = exported_feature_path(sample, export_root, suffix=suffix)
    return p.is_file()


def iter_capture_samples(
    root: Path | str,
    *,
    require_capture_json: bool = False,
    skip_if_export_exists_in: Path | str | None = None,
    export_filename_suffix: str = DEFAULT_EXPORT_SUFFIX,
) -> Iterator[CaptureSample]:
    """
    Walk ``root/safe/<scenario>`` and ``root/unsafe/<scenario>``.

    If ``require_capture_json`` is True, only yields samples that have a ``*_capture.json``.

    If ``skip_if_export_exists_in`` is set, skips any sample whose
    ``exported_feature_path(sample, skip_if_export_exists_in, suffix=export_filename_suffix)``
    already exists (for incremental batch runs).
    """
    root_p = Path(root).expanduser().resolve()
    scen_map = _scenario_index_map(root_p)
    skip_root = Path(skip_if_export_exists_in).expanduser().resolve() if skip_if_export_exists_in else None

    for split in ("safe", "unsafe"):
        split_dir = root_p / split
        if not split_dir.is_dir():
            continue
        label = 0 if split == "safe" else 1
        for scenario_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            scenario = scenario_dir.name
            idx = scen_map.get((split, scenario), -1)
            for stem in sorted(_discover_stems_in_scenario_dir(scenario_dir)):
                cap = scenario_dir / f"{stem}_capture.json"
                rep = scenario_dir / f"{stem}_report.json"
                mp4 = scenario_dir / f"{stem}.mp4"
                cap_p = cap if cap.is_file() else None
                rep_p = rep if rep.is_file() else None
                mp4_p = mp4 if mp4.is_file() else None
                if require_capture_json and cap_p is None:
                    continue
                sample = CaptureSample(
                    stem=stem,
                    scenario=scenario,
                    split=split,
                    label_binary=label,
                    scenario_index=idx,
                    dir_path=scenario_dir,
                    mp4_path=mp4_p,
                    capture_json_path=cap_p,
                    report_json_path=rep_p,
                )
                if skip_root is not None and export_file_exists(
                    sample, skip_root, suffix=export_filename_suffix
                ):
                    continue
                yield sample


def list_capture_samples(
    root: Path | str,
    *,
    require_capture_json: bool = False,
    skip_if_export_exists_in: Path | str | None = None,
    export_filename_suffix: str = DEFAULT_EXPORT_SUFFIX,
) -> list[CaptureSample]:
    return list(
        iter_capture_samples(
            root,
            require_capture_json=require_capture_json,
            skip_if_export_exists_in=skip_if_export_exists_in,
            export_filename_suffix=export_filename_suffix,
        )
    )


def load_capture_json(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def load_report_json(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _f(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _point_stats(points: list[dict[str, Any]]) -> tuple[float, float, float, float, float, float]:
    """mean_snr, std_snr, mean_x, mean_y, mean_doppler, mean_z."""
    if not points:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    snrs = [_f(p.get("snr")) for p in points]
    xs = [_f(p.get("x")) for p in points]
    ys = [_f(p.get("y")) for p in points]
    dops = [_f(p.get("doppler")) for p in points]
    zs = [_f(p.get("z")) for p in points]
    arr_s = np.asarray(snrs, dtype=np.float32)
    return (
        float(np.mean(arr_s)),
        float(np.std(arr_s)) if arr_s.size > 1 else 0.0,
        float(np.mean(xs)),
        float(np.mean(ys)),
        float(np.mean(dops)),
        float(np.mean(zs)),
    )


# Fixed column order for capture_frames_to_feature_matrix (document for training code).
CAPTURE_FRAME_FEATURE_NAMES: tuple[str, ...] = (
    "frame_index_norm",
    "timestamp_ms_norm",
    "mmwave_frame_number_norm",
    "num_points",
    "num_points_log1p",
    "risk_score_mmwave",
    "reflective_fraction",
    "reflective_fraction_ema",
    "torso_point_count",
    "centroid_x",
    "centroid_y",
    "torso_x_min",
    "torso_x_max",
    "torso_y_min",
    "torso_y_max",
    "persist_window",
    "persist_active_count",
    "persist_required_count",
    "persist_is_persistent",
    "thermal_mean_u8_norm",
    "presence_presence_raw",
    "presence_motion_raw",
    "presence_distance_m",
    "presence_available",
    "points_mean_snr",
    "points_std_snr",
    "points_mean_x",
    "points_mean_y",
    "points_mean_doppler",
    "points_mean_z",
)


def frame_dict_to_feature_vector(
    frame: dict[str, Any],
    *,
    num_frames: int,
    t0_ms: float,
    span_ms: float,
) -> np.ndarray:
    """
    Map one ``frames[i]`` entry from rich capture JSON to a fixed-length float32 vector.

    ``num_frames`` is used to normalize ``frame_index``; ``t0_ms`` and ``span_ms`` normalize time
    (if ``span_ms`` <= 0, timestamp channel is 0).
    """
    idx = int(frame.get("index", 0))
    ts = _f(frame.get("timestamp_ms"))
    mm = frame.get("mmwave") or {}
    pts = mm.get("points") or []
    if not isinstance(pts, list):
        pts = []
    rf = mm.get("risk_features") or {}
    torso = rf.get("torso_roi") or {}
    cent = rf.get("centroid")
    pers = rf.get("persistence") or {}
    th = frame.get("thermal") or {}
    pr = frame.get("presence")

    n = max(1, int(num_frames))
    fi_norm = float(idx) / float(n - 1) if n > 1 else 0.0
    t_norm = (ts - t0_ms) / span_ms if span_ms > 1e-6 else 0.0

    fn = mm.get("frame_number")
    fn_f = _f(fn, default=-1.0)

    mean_snr, std_snr, mx, my, mdop, mz = _point_stats(pts)

    cx = cy = 0.0
    if isinstance(cent, dict):
        cx = _f(cent.get("x"))
        cy = _f(cent.get("y"))

    xmin = _f(torso.get("x_min")) if torso.get("x_min") is not None else 0.0
    xmax = _f(torso.get("x_max")) if torso.get("x_max") is not None else 0.0
    ymin = _f(torso.get("y_min")) if torso.get("y_min") is not None else 0.0
    ymax = _f(torso.get("y_max")) if torso.get("y_max") is not None else 0.0
    if torso.get("x_min") is None:
        xmin = xmax = ymin = ymax = 0.0

    tcount = int(_f(torso.get("point_count"), 0.0))

    pres_raw = mot_raw = dist = 0.0
    pres_ok = 0.0
    if isinstance(pr, dict):
        pres_ok = 1.0
        pres_raw = _f(pr.get("presence_raw"))
        mot_raw = _f(pr.get("motion_raw"))
        dist = _f(pr.get("distance_m"))

    vec = np.array(
        [
            fi_norm,
            t_norm,
            fn_f / 10000.0,
            float(len(pts)),
            math.log1p(len(pts)),
            _f(rf.get("risk_score_mmwave")),
            _f(rf.get("reflective_fraction")),
            _f(rf.get("reflective_fraction_ema")),
            float(tcount),
            cx,
            cy,
            xmin,
            xmax,
            ymin,
            ymax,
            _f(pers.get("window")),
            _f(pers.get("active_count")),
            _f(pers.get("required_count")),
            1.0 if pers.get("is_persistent") else 0.0,
            _f(th.get("mean_u8")) / 255.0,
            pres_raw,
            mot_raw,
            dist,
            pres_ok,
            mean_snr,
            std_snr,
            mx,
            my,
            mdop,
            mz,
        ],
        dtype=np.float32,
    )
    assert vec.shape[0] == len(CAPTURE_FRAME_FEATURE_NAMES)
    return vec


def capture_frames_to_feature_matrix(capture: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Build ``X`` of shape ``(T, D)`` from ``capture["frames"]``.

    Returns ``(X, meta)`` where ``meta`` has ``num_frames``, ``feature_names``, ``capture_info``.
    """
    frames = capture.get("frames")
    if not isinstance(frames, list) or not frames:
        return np.zeros((0, len(CAPTURE_FRAME_FEATURE_NAMES)), dtype=np.float32), {
            "num_frames": 0,
            "feature_names": CAPTURE_FRAME_FEATURE_NAMES,
            "capture_info": capture.get("capture_info"),
        }

    t0 = _f(frames[0].get("timestamp_ms"))
    t1 = _f(frames[-1].get("timestamp_ms"))
    span = max(t1 - t0, 1e-3)

    rows = [
        frame_dict_to_feature_vector(fr, num_frames=len(frames), t0_ms=t0, span_ms=span) for fr in frames
    ]
    x = np.stack(rows, axis=0)
    return x, {
        "num_frames": len(frames),
        "feature_names": CAPTURE_FRAME_FEATURE_NAMES,
        "capture_info": capture.get("capture_info"),
    }


@dataclass
class ClipBatch:
    """One clip as tensors/arrays for training."""

    sample: CaptureSample
    """Path grouping and labels."""

    X_frames: np.ndarray
    """Shape ``(T, D)`` — tabular features per frame from capture JSON."""

    feature_names: tuple[str, ...]
    meta: dict[str, Any]

    label_binary: int = field(init=False)
    scenario_index: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_binary", self.sample.label_binary)
        object.__setattr__(self, "scenario_index", self.sample.scenario_index)

    @property
    def T(self) -> int:
        return int(self.X_frames.shape[0])

    @property
    def D(self) -> int:
        return int(self.X_frames.shape[1]) if self.X_frames.ndim == 2 else 0


def load_clip_batch(sample: CaptureSample) -> ClipBatch:
    """Load capture JSON and build the feature matrix; fails if capture JSON is missing."""
    if not sample.has_capture_json:
        raise FileNotFoundError(f"No capture JSON for {sample.stem} in {sample.dir_path}")
    cap = load_capture_json(sample.capture_json_path)  # type: ignore[arg-type]
    x, meta = capture_frames_to_feature_matrix(cap)
    return ClipBatch(
        sample=sample,
        X_frames=x,
        feature_names=meta["feature_names"],
        meta=meta,
    )


def export_clip_batch_npz(
    batch: ClipBatch,
    export_root: Path | str,
    *,
    suffix: str = DEFAULT_EXPORT_SUFFIX,
    mkdir: bool = True,
) -> Path:
    """
    Write ``X_frames`` and labels to ``exported_feature_path(...)`` (compressed ``.npz``).

    Safe to call repeatedly with :func:`iter_capture_samples` and
    ``skip_if_export_exists_in=export_root`` so only new clips are processed.
    """
    path = exported_feature_path(batch.sample, export_root, suffix=suffix)
    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        X_frames=np.ascontiguousarray(batch.X_frames, dtype=np.float32),
        label_binary=np.int64(batch.label_binary),
        scenario_index=np.int64(batch.scenario_index),
        stem=batch.sample.stem,
        scenario=batch.sample.scenario,
        split=batch.sample.split,
        feature_names=np.array(batch.feature_names, dtype=object),
    )
    return path


def stack_clips_padded(
    batches: list[ClipBatch],
    *,
    pad_value: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Pad variable-length clips to a single tensor ``(N, T_max, D)`` with mask ``(N, T_max)``.

    Returns ``(x_padded, mask, y_binary)`` where ``mask`` is 1.0 for valid timesteps.
    """
    if not batches:
        d = len(CAPTURE_FRAME_FEATURE_NAMES)
        return (
            np.zeros((0, 0, d), dtype=np.float32),
            np.zeros((0, 0), dtype=np.float32),
            np.zeros((0,), dtype=np.int64),
        )
    t_max = max(b.T for b in batches)
    d = batches[0].D
    n = len(batches)
    x_out = np.full((n, t_max, d), pad_value, dtype=np.float32)
    mask = np.zeros((n, t_max), dtype=np.float32)
    y = np.zeros((n,), dtype=np.int64)
    for i, b in enumerate(batches):
        t = b.T
        if t > 0:
            x_out[i, :t, :] = b.X_frames
            mask[i, :t] = 1.0
        y[i] = int(b.label_binary)
    return x_out, mask, y


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="List grouped capture artifacts under safe/unsafe.")
    p.add_argument(
        "root",
        type=str,
        nargs="?",
        default=str(Path.home() / "Desktop" / "collecting_data"),
        help="Dataset root containing safe/ and unsafe/",
    )
    p.add_argument("--require-capture", action="store_true", help="Only list samples with capture JSON")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--export-root",
        type=str,
        default=None,
        help="If set, compare against exported .npz paths under this tree (see --export).",
    )
    p.add_argument(
        "--export-suffix",
        type=str,
        default=DEFAULT_EXPORT_SUFFIX,
        help=f"Filename suffix for exported clips (default: {DEFAULT_EXPORT_SUFFIX!r}).",
    )
    p.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When iterating/exporting, skip samples whose export file already exists (default: true).",
    )
    p.add_argument(
        "--export",
        action="store_true",
        help="Export feature .npz for each selected sample into --export-root (requires capture JSON).",
    )
    args = p.parse_args()
    root = Path(args.root).expanduser()
    skip_root = Path(args.export_root).expanduser() if args.export_root else None
    if args.export and skip_root is None:
        p.error("--export requires --export-root")

    all_samples = list_capture_samples(root, require_capture_json=args.require_capture)
    samples = list_capture_samples(
        root,
        require_capture_json=args.require_capture,
        skip_if_export_exists_in=skip_root if (skip_root and args.skip_existing) else None,
        export_filename_suffix=args.export_suffix,
    )
    complete = sum(1 for s in samples if s.is_complete_triplet)
    print(f"root={root.resolve()}")
    if skip_root is not None:
        skipped = len(all_samples) - len(samples)
        print(
            f"export_root={skip_root.resolve()} suffix={args.export_suffix!r} "
            f"skip_existing={args.skip_existing} skipped={skipped}"
        )
    print(f"samples={len(samples)} complete_triplet={complete}")
    if args.export:
        n_ok = 0
        for s in samples:
            try:
                export_clip_batch_npz(load_clip_batch(s), skip_root, suffix=args.export_suffix)
                n_ok += 1
            except Exception as e:
                print(f"ERROR {s.split}/{s.scenario}/{s.stem}: {e}")
        print(f"exported={n_ok}/{len(samples)}")
    for s in samples:
        flags = f"cap={'Y' if s.has_capture_json else '-'} rep={'Y' if s.has_report_json else '-'} mp4={'Y' if s.has_mp4 else '-'}"
        if args.verbose:
            print(f"  [{s.split}] {s.scenario}/{s.stem}  {flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
