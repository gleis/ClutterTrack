"""SQLite-backed usage tracker for detected objects over time."""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from detector import Detection


class ClutterTracker:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id          TEXT PRIMARY KEY,
                    image_path  TEXT NOT NULL,
                    room        TEXT NOT NULL DEFAULT 'default',
                    timestamp   TEXT NOT NULL,
                    object_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS detections (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    label       TEXT NOT NULL,
                    confidence  REAL NOT NULL,
                    x_center    REAL NOT NULL,
                    y_center    REAL NOT NULL,
                    x1 REAL, y1 REAL, x2 REAL, y2 REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_detections_session
                    ON detections(session_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_room
                    ON sessions(room);
            """)

    def record_scan(
        self, image_path: str, room: str, detections: List[Detection]
    ) -> str:
        """Persist a scan session and its detections. Returns the session ID."""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, image_path, room, timestamp, object_count) "
                "VALUES (?,?,?,?,?)",
                (session_id, image_path, room, timestamp, len(detections)),
            )
            conn.executemany(
                "INSERT INTO detections "
                "(session_id, label, confidence, x_center, y_center, x1, y1, x2, y2) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        session_id,
                        d.label,
                        d.confidence,
                        d.x_center,
                        d.y_center,
                        d.x1,
                        d.y1,
                        d.x2,
                        d.y2,
                    )
                    for d in detections
                ],
            )

        return session_id

    def get_session_count(self, room: Optional[str] = None) -> int:
        with self._conn() as conn:
            if room:
                row = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE room=?", (room,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return row[0]

    def get_sessions(self, room: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            if room:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE room=? ORDER BY timestamp", (room,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY timestamp"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_object_stats(
        self, room: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Per-label stats: sessions_seen, first/last_seen, avg position, confidence."""
        with self._conn() as conn:
            if room:
                total_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE room=?", (room,)
                ).fetchone()[0]
                rows = conn.execute(
                    """
                    SELECT
                        d.label,
                        COUNT(DISTINCT d.session_id) AS sessions_seen,
                        MIN(s.timestamp)             AS first_seen,
                        MAX(s.timestamp)             AS last_seen,
                        AVG(d.x_center)              AS avg_x,
                        AVG(d.y_center)              AS avg_y,
                        AVG(d.confidence)            AS avg_confidence,
                        COUNT(*)                     AS total_detections
                    FROM detections d
                    JOIN sessions s ON d.session_id = s.id
                    WHERE s.room = ?
                    GROUP BY d.label
                    """,
                    (room,),
                ).fetchall()
            else:
                total_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions"
                ).fetchone()[0]
                rows = conn.execute(
                    """
                    SELECT
                        d.label,
                        COUNT(DISTINCT d.session_id) AS sessions_seen,
                        MIN(s.timestamp)             AS first_seen,
                        MAX(s.timestamp)             AS last_seen,
                        AVG(d.x_center)              AS avg_x,
                        AVG(d.y_center)              AS avg_y,
                        AVG(d.confidence)            AS avg_confidence,
                        COUNT(*)                     AS total_detections
                    FROM detections d
                    JOIN sessions s ON d.session_id = s.id
                    GROUP BY d.label
                    """
                ).fetchall()

            stats: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                stats[row["label"]] = {
                    "sessions_seen": row["sessions_seen"],
                    "total_sessions": total_sessions,
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "avg_x": row["avg_x"],
                    "avg_y": row["avg_y"],
                    "avg_confidence": row["avg_confidence"],
                    "total_detections": row["total_detections"],
                }
            return stats

    def clear(self, room: Optional[str] = None):
        with self._conn() as conn:
            if room:
                session_ids = [
                    r[0]
                    for r in conn.execute(
                        "SELECT id FROM sessions WHERE room=?", (room,)
                    ).fetchall()
                ]
                if session_ids:
                    placeholders = ",".join("?" * len(session_ids))
                    conn.execute(
                        f"DELETE FROM detections WHERE session_id IN ({placeholders})",
                        session_ids,
                    )
                conn.execute("DELETE FROM sessions WHERE room=?", (room,))
            else:
                conn.execute("DELETE FROM detections")
                conn.execute("DELETE FROM sessions")
