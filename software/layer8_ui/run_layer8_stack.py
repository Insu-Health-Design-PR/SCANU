"""Compatibility wrapper for Layer 8 integrated stack runner."""

from .backend.run_layer8_stack import build_parser, main

__all__ = ["build_parser", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
