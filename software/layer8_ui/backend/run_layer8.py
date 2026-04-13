"""Runner for Layer 8 FastAPI backend."""

from __future__ import annotations

import argparse

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 8 API service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    uvicorn.run(
        "software.layer8_ui.backend.app:app",
        host=args.host,
        port=args.port,
        reload=bool(args.reload),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
