"""Open the DeepLabCut (napari) labelling window for one video's frames.

    uv run scripts/label.py          # list folders and their labelling status
    uv run scripts/label.py 1        # open folder number 1 from that list
    uv run scripts/label.py <name>   # open a folder by (partial) name

deeplabcut.label_frames() opens napari but does not start its event loop, so
called from a plain script the window closes immediately; we call napari.run().
Save with Cmd+S before closing the window.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = sorted((ROOT / "dlc_projects").glob("*/config.yaml"))


def main() -> None:
    if len(CONFIGS) != 1:
        raise SystemExit(f"Expected one DLC project in dlc_projects/, found {len(CONFIGS)}")
    config = CONFIGS[0]
    folders = sorted(p for p in (config.parent / "labeled-data").iterdir() if p.is_dir())

    if len(sys.argv) < 2:
        print("Labelling folders:")
        for i, f in enumerate(folders, 1):
            n_img = len(list(f.glob("img*.png")))
            labelled = "labelled" if list(f.glob("CollectedData_*.h5")) else "not started"
            print(f"  {i}. {f.name}  ({n_img} frames, {labelled})")
        print("\nOpen one with:  uv run scripts/label.py <number>")
        return

    arg = sys.argv[1]
    if arg.isdigit():
        folder = folders[int(arg) - 1]
    else:
        matches = [f for f in folders if arg in f.name]
        if len(matches) != 1:
            raise SystemExit(f"'{arg}' matches {len(matches)} folders; be more specific.")
        folder = matches[0]

    import deeplabcut
    import napari

    print(f"Opening {folder.name} ... (save with Cmd+S before closing)")
    deeplabcut.label_frames(str(config), folder.name)
    napari.run()


if __name__ == "__main__":
    main()
