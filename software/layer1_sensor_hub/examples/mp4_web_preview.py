"""
Re-encode OpenCV-written MP4 (usually MPEG-4 Part 2 / mp4v) to H.264 yuv420p
with faststart so browsers, Cursor, and HTML <video> can play them.

Requires ffmpeg on PATH. Same idea as:
  ffmpeg -i in.mp4 -c:v libx264 -pix_fmt yuv420p out.mp4
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def reencode_mp4_for_web(path: str | Path, *, quiet: bool = True) -> bool:
    path = Path(path).resolve()
    if not path.is_file():
        return False
    if shutil.which("ffmpeg") is None:
        print(
            "Note: ffmpeg not on PATH; leaving OpenCV mp4v file "
            "(may not play in browser / Cursor — install ffmpeg or use --no-reencode knowingly)."
        )
        return False

    tmp = path.with_name(path.stem + "._web_.mp4")
    loglevel = "error" if quiet else "info"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        loglevel,
        "-i",
        str(path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=quiet, text=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        err = ""
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            err = exc.stderr.strip()[:500]
        print(f"Warning: ffmpeg re-encode failed; left original file. {err}")
        return False

    try:
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False

    print("Re-encoded for web preview: H.264 yuv420p + faststart")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 mp4_web_preview.py <file.mp4> [--quiet]", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    quiet = "--quiet" in sys.argv
    ok = reencode_mp4_for_web(path, quiet=quiet)
    sys.exit(0 if ok else 1)
