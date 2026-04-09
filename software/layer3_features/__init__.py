"""Layer 3: feature representation and multimodal dataset helpers."""

from .dataset import (
    CAPTURE_FRAME_FEATURE_NAMES,
    DEFAULT_EXPORT_SUFFIX,
    CaptureSample,
    ClipBatch,
    capture_frames_to_feature_matrix,
    export_clip_batch_npz,
    export_file_exists,
    exported_feature_path,
    frame_dict_to_feature_vector,
    iter_capture_samples,
    list_capture_samples,
    load_capture_json,
    load_clip_batch,
    load_report_json,
    stack_clips_padded,
)

__all__ = [
    "CAPTURE_FRAME_FEATURE_NAMES",
    "DEFAULT_EXPORT_SUFFIX",
    "CaptureSample",
    "ClipBatch",
    "capture_frames_to_feature_matrix",
    "export_clip_batch_npz",
    "export_file_exists",
    "exported_feature_path",
    "frame_dict_to_feature_vector",
    "iter_capture_samples",
    "list_capture_samples",
    "load_capture_json",
    "load_clip_batch",
    "load_report_json",
    "stack_clips_padded",
]
