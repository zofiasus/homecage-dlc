"""Convert Actual Analytics HCA .flv videos to DeepLabCut-friendly .mp4.

Why this is needed
------------------
HCA videos are H.264 High 4:4:4 encoded by an old x264 build that wrote no
version tag into the stream. Old x264 (< build 151) had a 4:4:4 encoding bug
that FFmpeg only compensates for when it can see that tag, so without help
every frame decodes as mostly green/grey garbage. Passing ``-x264_build 150``
tells the decoder to apply the workaround. We then re-encode to standard
yuv420p H.264 so OpenCV (and therefore DeepLabCut) reads it directly.

Usage
-----
    uv run scripts/convert_flv.py                 # data/raw -> data/converted
    uv run scripts/convert_flv.py SRC_DIR DST_DIR
    uv run scripts/convert_flv.py --overwrite

The folder structure under SRC_DIR is mirrored under DST_DIR. Existing outputs
are skipped unless --overwrite is given. Each output is checked: frame count
must match the source and the file must decode without errors.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).resolve().parents[1]


def count_frames(path: Path, decoder_args: list[str]) -> tuple[int, int]:
    """Decode the whole file; return (frames, n_error_lines)."""
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-v", "error", "-stats", *decoder_args,
         "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    frames = 0
    errors = 0
    for line in proc.stderr.replace("\r", "\n").splitlines():
        if line.startswith("frame="):
            frames = int(line.split("=", 1)[1].split()[0])
        elif line.strip():
            errors += 1
    return frames, errors


def convert(src: Path, dst: Path, crf: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".partial.mp4")
    cmd = [
        FFMPEG, "-hide_banner", "-v", "error", "-y",
        "-x264_build", "150",           # the fix: assume old x264 encoder
        "-i", str(src),
        "-map", "0:v:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(tmp),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # The very first frame of HCA files is undecodable (stream starts mid-GOP);
    # FFmpeg reports it but still produces a valid file, so only fail on exit code.
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed on {src}:\n{proc.stderr[-2000:]}")
    tmp.rename(dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("dst", nargs="?", type=Path, default=ROOT / "data" / "converted")
    ap.add_argument("--crf", type=int, default=18, help="x264 quality (lower = better/bigger). Default 18.")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="skip the post-conversion decode check")
    args = ap.parse_args()

    sources = sorted(p for p in args.src.rglob("*.flv") if not p.name.startswith("._"))
    if not sources:
        print(f"No .flv files under {args.src}")
        return 1

    failures = []
    for i, src in enumerate(sources, 1):
        dst = args.dst / src.relative_to(args.src).with_suffix(".mp4")
        tag = f"[{i}/{len(sources)}] {src.relative_to(args.src)}"
        if dst.exists() and not args.overwrite:
            print(f"{tag}: exists, skipping")
            continue
        t0 = time.time()
        try:
            convert(src, dst, args.crf)
        except RuntimeError as e:
            print(f"{tag}: FAILED\n{e}")
            failures.append(src)
            continue
        msg = f"{tag}: converted in {time.time() - t0:.0f}s, {dst.stat().st_size / 1e6:.0f} MB"
        if not args.no_verify:
            n_src, _ = count_frames(src, ["-x264_build", "150"])
            n_dst, err_dst = count_frames(dst, [])
            ok = n_src == n_dst and err_dst == 0
            msg += f" | frames {n_dst}/{n_src}, decode errors {err_dst} -> {'OK' if ok else 'CHECK'}"
            if not ok:
                failures.append(src)
        print(msg, flush=True)

    if failures:
        print(f"\n{len(failures)} file(s) need attention:")
        for f in failures:
            print("  ", f)
        return 1
    print("\nAll done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
