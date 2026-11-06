from click.testing import CliRunner
from analyzer import compute_stats, simple_suggestions
from detector import Detection
from main import cli
from report import render_report
from tracker import ClutterTracker


def detection(label):
    return Detection(label, .9, 0, 0, 1, 1, .5, .5)


def test_frequency_counts_sessions_and_room_isolation(tmp_path):
    t = ClutterTracker(tmp_path / "scans.db")
    t.record_scan("one.jpg", "office", [detection("chair"), detection("chair")])
    t.record_scan("two.jpg", "office", [])
    t.record_scan("three.jpg", "kitchen", [detection("bottle")])
    stats = compute_stats(t, "office")
    assert stats["chair"]["frequency"] == .5
    assert stats["chair"]["total_detections"] == 2
    assert "bottle" not in stats
    t.clear("office")
    assert t.get_session_count("office") == 0
    assert t.get_session_count("kitchen") == 1


def test_rule_boundaries():
    result = simple_suggestions({
        "chair": {"frequency": .6, "days_since_last_seen": 31},
        "box": {"frequency": .2, "days_since_last_seen": 30},
        "lamp": {"frequency": .4, "days_since_last_seen": 15}})
    assert result["keep"][0]["item"] == "chair"
    assert result["donate"][0]["item"] == "box"
    assert result["review"][0]["item"] == "lamp"


def test_report_escapes_user_paths_and_room(tmp_path):
    t = ClutterTracker(tmp_path / "scans.db")
    t.record_scan("<script>.jpg", "<office>", [])
    html = render_report(t, "<office>")
    assert "&lt;script&gt;.jpg" in html
    assert "<script>" not in html
    assert "&lt;office&gt;" in html
    output = tmp_path / "report.html"
    result = CliRunner().invoke(cli, ["report", "--room", "<office>", "--db", t.db_path, "--output", str(output)])
    assert result.exit_code == 0
    assert output.read_text() == html
