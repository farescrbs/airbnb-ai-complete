import sqlite3
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            guest_name TEXT,
            guest_email TEXT,
            check_in DATE,
            check_out DATE,
            num_guests INTEGER,
            num_nights INTEGER,
            total_price REAL,
            status TEXT DEFAULT 'pending',
            platform TEXT DEFAULT 'airbnb',
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id TEXT,
            direction TEXT,
            content TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            auto_generated INTEGER DEFAULT 0,
            FOREIGN KEY (reservation_id) REFERENCES reservations(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS blocked_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date DATE,
            end_date DATE,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id TEXT,
            guest_rating REAL,
            guest_comment TEXT,
            host_response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reservation_id) REFERENCES reservations(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id TEXT,
            task_type TEXT,
            scheduled_for DATETIME,
            completed INTEGER DEFAULT 0,
            completed_at DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ── Reservations ──────────────────────────────────────────

def add_reservation(data: dict) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO reservations
        (id, guest_name, guest_email, check_in, check_out, num_guests, num_nights, total_price, status, platform, notes)
        VALUES (:id, :guest_name, :guest_email, :check_in, :check_out, :num_guests, :num_nights, :total_price, :status, :platform, :notes)
    """, data)
    conn.commit()
    conn.close()
    return data["id"]


def get_reservation(reservation_id: str):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_reservations(status: str = None, from_date: str = None, to_date: str = None) -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT * FROM reservations WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if from_date:
        query += " AND check_out >= ?"
        params.append(from_date)
    if to_date:
        query += " AND check_in <= ?"
        params.append(to_date)
    query += " ORDER BY check_in ASC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_reservation_status(reservation_id: str, status: str, notes: str = None):
    conn = get_conn()
    c = conn.cursor()
    if notes:
        c.execute("UPDATE reservations SET status=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                  (status, notes, reservation_id))
    else:
        c.execute("UPDATE reservations SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                  (status, reservation_id))
    conn.commit()
    conn.close()


def is_available(check_in: str, check_out: str, exclude_id: str = None) -> bool:
    conn = get_conn()
    c = conn.cursor()
    query = """
        SELECT COUNT(*) FROM reservations
        WHERE status NOT IN ('cancelled', 'rejected')
        AND check_in < ? AND check_out > ?
    """
    params = [check_out, check_in]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    count = c.execute(query, params).fetchone()[0]

    blocked = c.execute("""
        SELECT COUNT(*) FROM blocked_dates
        WHERE start_date < ? AND end_date > ?
    """, (check_out, check_in)).fetchone()[0]

    conn.close()
    return count == 0 and blocked == 0


# ── Messages ──────────────────────────────────────────────

def save_message(reservation_id: str, direction: str, content: str, auto_generated: bool = False):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (reservation_id, direction, content, auto_generated)
        VALUES (?, ?, ?, ?)
    """, (reservation_id, direction, content, int(auto_generated)))
    conn.commit()
    conn.close()


def get_messages(reservation_id: str) -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM messages WHERE reservation_id = ? ORDER BY sent_at ASC",
                     (reservation_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Blocked dates ─────────────────────────────────────────

def block_dates(start_date: str, end_date: str, reason: str = "Maintenance"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO blocked_dates (start_date, end_date, reason) VALUES (?, ?, ?)",
              (start_date, end_date, reason))
    conn.commit()
    conn.close()


def get_blocked_dates() -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM blocked_dates ORDER BY start_date ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Reviews ───────────────────────────────────────────────

def save_review(reservation_id: str, rating: float, comment: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO reviews (reservation_id, guest_rating, guest_comment) VALUES (?, ?, ?)",
              (reservation_id, rating, comment))
    conn.commit()
    conn.close()


def save_host_response(reservation_id: str, response: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reviews SET host_response=? WHERE reservation_id=?",
              (response, reservation_id))
    conn.commit()
    conn.close()


def get_reviews() -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Tasks ─────────────────────────────────────────────────

def add_task(reservation_id: str, task_type: str, scheduled_for: str, notes: str = None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (reservation_id, task_type, scheduled_for, notes) VALUES (?, ?, ?, ?)",
              (reservation_id, task_type, scheduled_for, notes))
    conn.commit()
    conn.close()


def get_pending_tasks(before_datetime: str = None) -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    if before_datetime:
        rows = c.execute("""
            SELECT t.*, r.guest_name FROM tasks t
            LEFT JOIN reservations r ON t.reservation_id = r.id
            WHERE t.completed = 0 AND t.scheduled_for <= ?
            ORDER BY t.scheduled_for ASC
        """, (before_datetime,)).fetchall()
    else:
        rows = c.execute("""
            SELECT t.*, r.guest_name FROM tasks t
            LEFT JOIN reservations r ON t.reservation_id = r.id
            WHERE t.completed = 0
            ORDER BY t.scheduled_for ASC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_task(task_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed=1, completed_at=CURRENT_TIMESTAMP WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


# ── Stats ─────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_conn()
    c = conn.cursor()

    total = c.execute("SELECT COUNT(*) FROM reservations WHERE status='confirmed'").fetchone()[0]
    revenue = c.execute("SELECT SUM(total_price) FROM reservations WHERE status='confirmed'").fetchone()[0] or 0
    avg_rating = c.execute("SELECT AVG(guest_rating) FROM reviews").fetchone()[0] or 0
    upcoming = c.execute("""
        SELECT COUNT(*) FROM reservations
        WHERE status='confirmed' AND check_in >= date('now')
    """).fetchone()[0]

    conn.close()
    return {
        "total_confirmed": total,
        "total_revenue": round(revenue, 2),
        "average_rating": round(avg_rating, 2),
        "upcoming_reservations": upcoming,
    }
