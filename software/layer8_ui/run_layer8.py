"""Compatibility wrapper for Layer 8 backend runner."""

from .backend.run_layer8 import build_parser, main

__all__ = ["build_parser", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
