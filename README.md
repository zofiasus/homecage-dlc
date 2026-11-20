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

## Video / HDF5 facts

- 1200×500, 25 fps, greyscale side view, 15 min = 22,500 frames per file.
- `.hdf5` → `subjects/<RFID tag>/antenna/ant1`: one row per video frame
  (`t` in ms, step 40), with antenna id, antenna position `bx, by`,
  temperature, and pairwise separations to the other mice.
- `data/0`: raw RFID read events (JSON strings).
