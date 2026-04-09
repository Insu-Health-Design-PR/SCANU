"""Compatibility wrapper for Layer 8 backend app."""

from .backend.app import app, create_app

__all__ = ["app", "create_app"]
