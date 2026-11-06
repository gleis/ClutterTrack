"""ClutterTrack CLI - clutter detection and usage tracking."""
from collections import Counter
from pathlib import Path

import click

from analyzer import compute_stats, simple_suggestions
from detector import detect
from tracker import ClutterTracker

DEFAULT_DB = Path.home() / ".clutter_track.db"


@click.group()
def cli():
    """ClutterTrack: scan your space, track objects, and review decluttering signals."""
    pass


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("image", type=click.Path(exists=True))
@click.option("--room", default="default", show_default=True, help="Room label for tracking")
@click.option("--db", default=str(DEFAULT_DB), show_default=True, help="Database file path")
@click.option(
    "--conf",
    default=0.25,
    show_default=True,
    type=float,
    help="Minimum YOLO detection confidence",
)
@click.option("--model", default="yolo11n.pt", show_default=True, help="YOLO weights name or local path")
def scan(image, room, db, conf, model):
    """Scan IMAGE and record detected objects to the tracking database.

    Run this command repeatedly over days/weeks to build usage history.
    """
    click.echo(f"Scanning '{image}' for room '{room}'...")

    tracker = ClutterTracker(db)
    detections = detect(image, conf_threshold=conf, model_name=model)

    if not detections:
        click.echo("No objects detected. Try a clearer photo or lower --conf.")

    session_id = tracker.record_scan(image, room, detections)

    counts = Counter(d.label for d in detections)
    click.echo(f"Detected {len(detections)} object(s):")
    for label, count in sorted(counts.items()):
        click.echo(f"  • {label} x{count}")

    total = tracker.get_session_count(room)
    click.echo(f"\nRecorded (session {session_id[:8]}). Total scans for '{room}': {total}")


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--room", default="default", show_default=True, help="Room to analyze")
@click.option("--db", default=str(DEFAULT_DB), show_default=True, help="Database file path")
def analyze(room, db):
    """Analyze tracked history and suggest what to keep, donate, or rearrange.

    Recommendations are based on object frequency and recency across scans.
    """
    tracker = ClutterTracker(db)
    total_sessions = tracker.get_session_count(room)

    if total_sessions == 0:
        click.echo(
            f"No scans found for room '{room}'. Run:\n\n"
            f"  python main.py scan <photo.jpg> --room {room}\n"
        )
        return

    click.echo(f"Analyzing {total_sessions} scan(s) for room '{room}'...")
    stats = compute_stats(tracker, room)

    # Always show frequency table
    click.echo("\n\U0001f4ca Object Frequency Summary:")
    for label, info in sorted(stats.items(), key=lambda x: -x[1]["frequency"]):
        bar = _freq_bar(info["frequency"])
        days = info["days_since_last_seen"]
        click.echo(f"  {bar} {label:20s} {int(info['frequency']*100):3d}%  last: {days:.0f}d ago")

    _print_suggestions(simple_suggestions(stats))


def _freq_bar(freq: float) -> str:
    filled = round(freq * 5)
    return "[" + "█" * filled + "░" * (5 - filled) + "]"


def _print_suggestions(result: dict):
    if result.get("summary"):
        click.echo(f"\n\U0001f4dd Summary: {result['summary']}")

    if result.get("keep"):
        click.echo("\n\u2705 Keep:")
        for item in result["keep"]:
            click.echo(f"  • {item['item']}: {item['reason']}")

    if result.get("donate"):
        click.echo("\n\U0001f5d1\ufe0f  Donate / Remove:")
        for item in result["donate"]:
            click.echo(f"  • {item['item']}: {item['reason']}")

    if result.get("review"):
        click.echo("\n\U0001f914 Review:")
        for item in result["review"]:
            click.echo(f"  • {item['item']}: {item['reason']}")

    if result.get("layout"):
        click.echo("\n\U0001f4d0 Layout Improvements:")
        for item in result["layout"]:
            click.echo(f"  • {item['suggestion']}")


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--room", default=None, help="Filter by room name")
@click.option("--db", default=str(DEFAULT_DB), show_default=True, help="Database file path")
@click.option("--limit", default=20, show_default=True, help="Max sessions to display")
def history(room, db, limit):
    """Show recent scan history."""
    tracker = ClutterTracker(db)
    sessions = tracker.get_sessions(room)

    if not sessions:
        label = f"room '{room}'" if room else "any room"
        click.echo(f"No scan history found for {label}.")
        return

    room_filter = f" for '{room}'" if room else ""
    click.echo(f"Scan history{room_filter} (showing last {limit} of {len(sessions)}):")

    for s in sessions[-limit:]:
        ts = s["timestamp"][:19]
        click.echo(
            f"  [{ts}]  room={s['room']:<12}  objects={s['object_count']:<4}  {s['image_path']}"
        )


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--room", default=None, help="Clear a specific room only (default: all)")
@click.option("--db", default=str(DEFAULT_DB), show_default=True, help="Database file path")
@click.confirmation_option(prompt="This will permanently delete tracking data. Continue?")
def reset(room, db):
    """Delete tracking data from the database."""
    tracker = ClutterTracker(db)
    tracker.clear(room)
    target = f"room '{room}'" if room else "all rooms"
    click.echo(f"Cleared tracking data for {target}.")


@cli.command()
@click.option("--room", default="default", show_default=True)
@click.option("--db", default=str(DEFAULT_DB), show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("clutter-report.html"))
def report(room, db, output):
    """Export a room's scan trend and photo paths to a standalone HTML page."""
    from report import render_report
    output.write_text(render_report(ClutterTracker(db), room), encoding="utf-8")
    click.echo(f"Wrote {output}")


if __name__ == "__main__":
    cli()
