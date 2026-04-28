"""Export trained checkpoint to ONNX for TensorRT / trtexec on Jetson."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from weapon_ai.modeling import build_model


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--onnx_out", type=Path, default=Path("trained_models/person_detection/model.onnx"))
    p.add_argument("--image_size", type=int, default=224)
    args = p.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    arch = ck.get("arch", "mobilenet_v3_small")
    model = build_model(arch, num_classes=2)
    model.load_state_dict(ck["model"])
    model.eval()

    dummy = torch.randn(1, 3, args.image_size, args.image_size)
    args.onnx_out.parent.mkdir(parents=True, exist_ok=True)
    export_kw: dict = dict(
        input_names=["image"],
        output_names=["logits"],
        opset_version=17,
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
    )
    # PyTorch 2.5+ defaults to the dynamo exporter (needs onnxscript); legacy is lighter for Jetson prep.
    try:
        torch.onnx.export(
            model,
            dummy,
            str(args.onnx_out),
            dynamo=False,
            **export_kw,
        )
    except TypeError:
        torch.onnx.export(model, dummy, str(args.onnx_out), **export_kw)
    print(f"Wrote {args.onnx_out}")


if __name__ == "__main__":
    main()
