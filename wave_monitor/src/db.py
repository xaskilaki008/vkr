import sqlite3
from datetime import datetime

def get_conn(db_path: str):
    return sqlite3.connect(db_path, check_same_thread=False)

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wave_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            beach TEXT NOT NULL,
            wave_index REAL NOT NULL,
            wave_class INTEGER NOT NULL
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wave_beach_ts ON wave_data (beach, ts);")
    conn.commit()

def insert_measurement(conn, ts: datetime, beach: str, wave_index: float, wave_class: int):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wave_data (ts, beach, wave_index, wave_class) VALUES (?, ?, ?, ?)",
        (ts.isoformat(timespec="seconds"), beach, float(wave_index), int(wave_class))
    )
    conn.commit()

def read_measurements(conn, beach: str, limit: int = 300):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts, wave_index, wave_class
        FROM wave_data
        WHERE beach = ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (beach, limit)
    )
    rows = cur.fetchall()
    rows.reverse()  # чтобы на графике было по времени слева-направо
    return rows
говно говно какашка