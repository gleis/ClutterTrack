"""Escaped, standalone HTML reporting over the existing local scan history."""
from html import escape
from analyzer import compute_stats


def render_report(tracker, room):
    sessions = tracker.get_sessions(room)
    rows = "".join(
        f"<tr><td>{escape(s['timestamp'])}</td><td>{s['object_count']}</td>"
        f"<td>{escape(s['image_path'])}</td></tr>" for s in sessions)
    stats = "".join(f"<li>{escape(label)}: {info['frequency']:.0%} of scans</li>"
                    for label, info in compute_stats(tracker, room).items())
    return ("<!doctype html><meta charset='utf-8'><title>ClutterTrack report</title>"
            "<style>body{font:16px system-ui;max-width:960px;margin:3rem auto}"
            "td,th{padding:.6rem;text-align:left;border-bottom:1px solid #ccc}</style>"
            f"<h1>{escape(room)}</h1><p>{len(sessions)} scans. Counts are detection signals, "
            "not a judgement of clutter.</p><table><tr><th>Time</th><th>Objects</th>"
            f"<th>Photo path</th></tr>{rows}</table><h2>Presence across scans</h2><ul>{stats}</ul>")
