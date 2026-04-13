#!/usr/bin/env python3
import argparse
import time
import subprocess
import cv2
import numpy as np


def normalize_to_8bit(frame):
    # For 16-bit thermal streams
    if frame.dtype == np.uint16:
        f = frame.astype(np.float32)
        mn, mx = float(np.min(f)), float(np.max(f))
        if mx - mn < 1e-6:
            return np.zeros_like(frame, dtype=np.uint8)
        f = (f - mn) / (mx - mn)
        return (f * 255.0).astype(np.uint8)
    return frame


def main():
    p = argparse.ArgumentParser(description="Thermal camera test")
    p.add_argument("--device", type=int, default=0, help="Video device index (default: 0)")
    p.add_argument("--width", type=int, default=640, help="Requested width")
    p.add_argument("--height", type=int, default=480, help="Requested height")
    p.add_argument("--fps", type=int, default=30, help="Requested FPS")
    p.add_argument("--seconds", type=int, default=10, help="Run duration")
    p.add_argument("--save", type=str, default="thermal_test.jpg", help="Snapshot output path")
    p.add_argument("--video", type=str, default="thermal_test.mp4", help="Video output path")
    p.add_argument("--video-h264", type=str, default="thermal_test_h264.mp4",
                   help="H.264-compatible output video path")
    p.add_argument("--show", action="store_true", help="Show preview window (requires GUI/GTK)")
    args = p.parse_args()

    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: Cannot open /dev/video{args.device}")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    print("Opened camera")
    print("Actual width:", int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    print("Actual height:", int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    print("Actual fps:", cap.get(cv2.CAP_PROP_FPS))

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or args.width
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or args.height
    actual_fps = float(cap.get(cv2.CAP_PROP_FPS))
    if actual_fps <= 0:
        actual_fps = float(args.fps if args.fps > 0 else 9.0)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(args.video, fourcc, actual_fps, (actual_w, actual_h))
    if not video_writer.isOpened():
        print(f"ERROR: Could not open video writer for {args.video}")
        cap.release()
        return 1

    start = time.time()
    frames = 0
    last_frame = None

    while time.time() - start < args.seconds:
        ok, frame = cap.read()
        if not ok:
            print("WARN: frame read failed")
            time.sleep(0.02)
            continue

        frames += 1
        last_frame = frame

        view = frame
        if len(view.shape) == 2:
            view = normalize_to_8bit(view)
            view = cv2.applyColorMap(view, cv2.COLORMAP_INFERNO)
        elif view.dtype == np.uint16:
            gray = normalize_to_8bit(view)
            view = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

        cv2.putText(view, f"Frames: {frames}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        video_writer.write(view)

        if args.show:
            cv2.imshow("Thermal Test", view)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):  # ESC or q
                break

    elapsed = time.time() - start
    print(f"Captured {frames} frames in {elapsed:.2f}s ({frames/elapsed if elapsed>0 else 0:.2f} FPS)")
    print(f"Saved video: {args.video}")

    # Ensure the raw MP4 is finalized before running ffmpeg conversion.
    cap.release()
    video_writer.release()
    cv2.destroyAllWindows()

    # Always convert to H.264 MP4 for wider player compatibility.
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", args.video,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        args.video_h264,
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        print(f"Saved H.264 video: {args.video_h264}")
    except FileNotFoundError:
        print("WARN: ffmpeg not found in PATH; skipped H.264 conversion.")
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip()
        print("WARN: ffmpeg conversion failed; raw MP4 is still available.")
        if err:
            print(f"ffmpeg error: {err}")

    if last_frame is not None:
        out = last_frame
        if len(out.shape) == 2 or out.dtype == np.uint16:
            gray = normalize_to_8bit(out if len(out.shape) == 2 else out[:, :, 0])
            out = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
        cv2.imwrite(args.save, out)
        print(f"Saved snapshot: {args.save}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
