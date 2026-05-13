# ClutterTrack

ClutterTrack is a local command-line tool for tracking what appears in a room over time. It uses YOLOv8 object detection on room photos, stores scan history in SQLite, and turns frequency and recency patterns into practical decluttering suggestions.

## What It Does

- Scans room photos with YOLOv8n object detection.
- Records each scan as a timestamped session.
- Stores detected object labels, confidence, and normalized positions in SQLite.
- Summarizes how often each object appears and when it was last seen.
- Suggests items to keep, donate/remove, or manually review.

## Requirements

- Python 3.10 or newer
- A local Python virtual environment
- Internet access the first time YOLOv8 downloads `yolov8n.pt`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run commands from the repository root.

### Scan a Room

```bash
python main.py scan path/to/photo.jpg --room office
```

This detects objects in the image and records a scan in the default database at `~/.clutter_track.db`.

Optional flags:

```bash
python main.py scan path/to/photo.jpg --room office --conf 0.35
python main.py scan path/to/photo.jpg --room office --db ./clutter.db
```

### Analyze a Room

```bash
python main.py analyze --room office
```

The analysis prints an object frequency table and recommendation groups:

- `Keep`: objects seen frequently or recently.
- `Donate / Remove`: objects seen rarely and not seen recently.
- `Review`: objects with mixed signals.

### View Scan History

```bash
python main.py history
python main.py history --room office --limit 10
```

### Reset Tracking Data

```bash
python main.py reset
python main.py reset --room office
```

`reset` asks for confirmation before deleting tracking data.

## Data Model

ClutterTrack creates two SQLite tables:

- `sessions`: one row per scan, including room, image path, timestamp, and object count.
- `detections`: one row per detected object, including label, confidence, normalized center point, and normalized bounding box.

The default database path is `~/.clutter_track.db`. Pass `--db` to any command to use a project-local or test database.

## Project Layout

- `main.py`: Click CLI commands for scanning, analysis, history, and reset.
- `detector.py`: YOLOv8 object detection wrapper.
- `tracker.py`: SQLite persistence and aggregate queries.
- `analyzer.py`: frequency, recency, and recommendation logic.
- `requirements.txt`: Python runtime dependencies.

## Development Notes

The first scan may take longer because `ultralytics` downloads the YOLOv8n model. The model file is ignored by git so local downloads do not get committed.

Generated files such as `__pycache__/`, `.DS_Store`, local databases, virtual environments, and downloaded model weights are intentionally ignored.
