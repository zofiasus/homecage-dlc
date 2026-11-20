"""Re-pick frames to label, favouring moments when mice are moving.

DeepLabCut's k-means picks frames that look different as whole images. In
these home-cage videos the mice rest out of sight most of the time, so k-means
mostly returns near-identical empty frames. This script instead:

  1. computes a motion score for every 5th frame (pixels that changed vs. the
     previous sample, on a small blurred greyscale copy),
  2. picks the most active frames, at least MIN_GAP_S seconds apart so they
     cover different bouts,
  3. adds a few quiet frames (no visible motion) as negatives / resting poses,
  4. replaces the PNGs in that video's labeled-data folder.

Folders that already contain labels (CollectedData_*.h5) are never touched.

    uv run scripts/pick_active_frames.py                 # all unlabelled folders
    uv run scripts/pick_active_frames.py 2 3             # by number (see label.py)
    uv run scripts/pick_active_frames.py --n-active 17 --n-quiet 3
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STEP = 5            # analyse every 5th frame (0.2 s)
MIN_GAP_S = 10      # active picks at least this far apart
DIFF_THRESH = 18    # grey-level change counted as motion


def motion_scores(video: Path) -> tuple[np.ndarray, np.ndarray, int]:
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idx, scores, prev = [], [], None
    for i in range(n):
        if i % STEP:
            if not cap.grab():
                break
            continue
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(f, (300, 125)), cv2.COLOR_BGR2GRAY), (5, 5), 0)
        if prev is not None:
            idx.append(i)
            scores.append(int((cv2.absdiff(g, prev) > DIFF_THRESH).sum()))
        prev = g
    cap.release()
    return np.array(idx), np.array(scores, dtype=float), n


def pick(idx, scores, n_active, n_quiet, fps, rng):
    # smooth over ~1 s so single-frame noise doesn't win
    k = max(1, int(fps / STEP))
    sm = np.convolve(scores, np.ones(k) / k, mode="same")
    gap = int(MIN_GAP_S * fps)
    chosen = []
    for j in np.argsort(sm)[::-1]:
        if sm[j] <= 0:
            break
        if all(abs(idx[j] - c) >= gap for c in chosen):
            chosen.append(int(idx[j]))
        if len(chosen) == n_active:
            break
    if len(chosen) < n_active:
        # too little motion: top up with evenly spaced frames away from the picks
        for c in np.linspace(idx[0], idx[-1], 4 * n_active).astype(int):
            if len(chosen) == n_active:
                break
            if all(abs(c - x) >= gap for x in chosen):
                chosen.append(int(c))
    quiet_pool = idx[sm <= np.percentile(sm, 30)]
    quiet_pool = np.array([q for q in quiet_pool if all(abs(q - c) >= gap for c in chosen)])
    quiet = []
    if len(quiet_pool) and n_quiet:
        # spread quiet picks across the recording
        for part in np.array_split(np.sort(quiet_pool), n_quiet):
            if len(part):
                quiet.append(int(rng.choice(part)))
    return sorted(chosen), sorted(quiet), sm


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="*", help="folder numbers as listed by scripts/label.py (default: all unlabelled)")
    ap.add_argument("--n-active", type=int, default=17)
    ap.add_argument("--n-quiet", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    config = next((ROOT / "dlc_projects").glob("*/config.yaml"))
    project = config.parent
    folders = sorted(p for p in (project / "labeled-data").iterdir() if p.is_dir())
    if args.folders:
        folders = [folders[int(a) - 1] for a in args.folders]
    rng = np.random.default_rng(args.seed)

    for folder in folders:
        if list(folder.glob("CollectedData_*.h5")):
            print(f"{folder.name}: has labels, skipping")
            continue
        video = project / "videos" / f"{folder.name}.mp4"
        idx, scores, n = motion_scores(video)
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        active, quiet, sm = pick(idx, scores, args.n_active, args.n_quiet, fps, rng)
        width = int(np.ceil(np.log10(n)))  # DeepLabCut's img naming convention

        for old in folder.glob("img*.png"):
            old.unlink()
        for fi in sorted(active + quiet):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, frame = cap.read()
            if ok:
                cv2.imwrite(str(folder / f"img{fi:0{width}d}.png"), frame)
        cap.release()
        n_moving = sum(sm[min(np.searchsorted(idx, a), len(sm) - 1)] > 50 for a in active)
        print(f"{folder.name}: {len(active) + len(quiet)} frames, {n_moving} with clear motion"
              + ("  <- very quiet video, consider another segment" if n_moving < len(active) // 2 else ""),
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
