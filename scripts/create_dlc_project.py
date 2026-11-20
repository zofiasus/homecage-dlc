"""Create the multi-animal DeepLabCut project for HCA home-cage videos.

Run once:
    uv run scripts/create_dlc_project.py

Creates dlc_projects/homecage-<experimenter>-<date>/ with videos linked (not
copied) from data/converted, writes our bodyparts/skeleton into config.yaml,
and extracts frames to label with k-means (visually diverse frames).

Design notes
------------
* Individuals are generic (mouse1..3). Identity is assigned *after* tracking by
  matching tracklets to RFID tags from the HCA .hdf5 files. RFID positions are
  only trusted while the mouse is on the floor: the antennas are in the
  baseplate, so when a mouse climbs onto the feeder grate its tag position is
  wrong.
* Bodyparts are chosen for a side view with heavy occlusion. ear_near = the ear
  facing the camera. Leave occluded parts unlabelled; do not guess.
* MALEGr1.BASELINE segments 000286/000287 are excluded: one mouse's RFID tag is
  missing there (probably taken out of the cage).
"""

from pathlib import Path

import deeplabcut
from deeplabcut.utils import auxiliaryfunctions

ROOT = Path(__file__).resolve().parents[1]
CONVERTED = ROOT / "data" / "converted"

EXPERIMENTER = "zofiasus"
INDIVIDUALS = ["mouse1", "mouse2", "mouse3"]
BODYPARTS = ["nose", "head", "ear_near", "body_centre", "tail_base"]
SKELETON = [
    ["nose", "head"],
    ["head", "ear_near"],
    ["head", "body_centre"],
    ["ear_near", "body_centre"],
    ["body_centre", "tail_base"],
]
FRAMES_PER_VIDEO = 20

# Starter set: spread across groups and across the recording; add more later
# with deeplabcut.add_new_videos().
VIDEOS = [
    "ISO.FEMALE.GR2Baseline/1695368175639_000279_ISOFEMALEGr2baseline.mp4",
    "ISO.FEMALE.GR2Baseline/1695368175639_000287_ISOFEMALEGr2baseline.mp4",  # 000283: no motion at all,
    "MALEGr1.BASELINE/1686650679571_000279_MALEGr1CD1BASELINE.mp4",
    "MALEGr1.BASELINE/1686650679571_000283_MALEGr1CD1BASELINE.mp4",
    "MALEGr2ISOX6/1697185307412_000167_MALEGr2ISOX6.mp4",
]


def main() -> None:
    videos = [str(CONVERTED / v) for v in VIDEOS]
    missing = [v for v in videos if not Path(v).exists()]
    if missing:
        raise SystemExit(f"Missing videos (run scripts/convert_flv.py first): {missing}")

    (ROOT / "dlc_projects").mkdir(exist_ok=True)
    config = deeplabcut.create_new_project(
        "homecage",
        EXPERIMENTER,
        videos,
        working_directory=str(ROOT / "dlc_projects"),
        copy_videos=False,
        multianimal=True,
        individuals=INDIVIDUALS,
    )
    if config == "nothingcreated":
        raise SystemExit("DeepLabCut did not create a project (does it already exist?)")

    cfg = auxiliaryfunctions.read_config(config)
    cfg["individuals"] = INDIVIDUALS
    cfg["uniquebodyparts"] = []
    cfg["multianimalbodyparts"] = BODYPARTS
    cfg["bodyparts"] = "MULTI!"
    cfg["skeleton"] = SKELETON
    cfg["numframes2pick"] = FRAMES_PER_VIDEO
    cfg["dotsize"] = 6
    auxiliaryfunctions.write_config(config, cfg)

    deeplabcut.extract_frames(
        config,
        mode="automatic",
        algo="kmeans",
        userfeedback=False,
        cluster_step=5,        # sample every 5th frame for clustering (speed)
        cluster_resizewidth=30,
    )
    print(f"\nProject ready: {config}")


if __name__ == "__main__":
    main()
