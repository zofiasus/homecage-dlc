# homecage-dlc

DeepLabCut (multi-animal) pose tracking of group-housed mice (3 per cage) from
**Actual Analytics HCA** home-cage recordings, with RFID tracks from the HCA
`.hdf5` files available for identity.

## Setup

Uses [uv](https://docs.astral.sh/uv/). Python is pinned to 3.11.

```bash
uv sync                 # core tools: video conversion, HDF5 reading
uv sync --extra dlc     # + DeepLabCut 3 (PyTorch) and its GUI
```

No system ffmpeg needed: `imageio-ffmpeg` ships one.

## Data layout (not in git)

```
data/
  raw/<group>/        HCA .flv video + matching .hdf5 (RFID) per 15-min segment
  raw/_zips/          original zip downloads
  converted/<group>/  .mp4 versions for DeepLabCut (same names)
```

Keep raw data on the lab drive / backup; only code and notes live in git.

## Converting HCA videos

HCA `.flv` files are H.264 4:4:4 from an old x264 build with no version tag.
Opened normally (FFmpeg, OpenCV, DeepLabCut) almost every frame is green
garbage. Decoding with `-x264_build 150` fixes it. The script does that and
re-encodes to standard MP4:

```bash
uv run scripts/convert_flv.py            # data/raw -> data/converted, skips existing
```

It checks every output: frame count must match the source and decode cleanly.

## DeepLabCut project

Created by `uv run scripts/create_dlc_project.py` in `dlc_projects/homecage-zofiasus-2026-11-20/`.

- Multi-animal, individuals `mouse1–3` (generic; identity comes from RFID later).
- Bodyparts: `nose, head, ear_near, body_centre, tail_base` (`ear_near` = ear
  facing the camera). Mice are often heavily occluded: only label what you can
  see, never guess.
- Starter set: 5 videos (000279 + 000283 of each baseline group, plus
  MALEGr2ISOX6 000167), 20 k-means frames each = 100 frames.

Label:

```bash
uv run python -m deeplabcut      # Load project → Label frames
```

## Identity via RFID (plan)

Match DLC tracklets to RFID tags using the per-frame antenna position in the
`.hdf5`. Antennas are in the baseplate, so a tag position is only a valid
anchor while the mouse is **on the floor**; when it climbs the feeder grate the
RFID location is wrong and must be ignored (e.g. gate on DLC y-position).

## Known data issues

- `MALEGr1.BASELINE` 000286/000287: mouse `…6299` absent from RFID (likely
  taken out). Excluded from the DLC training set.
- `MALEGr1.BASELINE` 000287 is 22,497 frames (video and HDF5 agree).

## Video / HDF5 facts

- 1200×500, 25 fps, greyscale side view, 15 min = 22,500 frames per file.
- `.hdf5` → `subjects/<RFID tag>/antenna/ant1`: one row per video frame
  (`t` in ms, step 40), with antenna id, antenna position `bx, by`,
  temperature, and pairwise separations to the other mice.
- `data/0`: raw RFID read events (JSON strings).
