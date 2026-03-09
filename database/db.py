"""
database/db.py – Thread-safe SQLite layer for Market Intelligence Bot.

All CRUD helpers live here.  Every function opens its own short-lived
connection so the module is safe to call from Streamlit's multi-threaded
runtime.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import bcrypt

from config import DB_PATH

logger = logging.getLogger(__name__)

# Ensure the data directory exists before SQLite tries to create the file
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ─────────────────────────────  CONNECTION  ──────────────────────────────────

@contextmanager
def _conn():
    """Yield a WAL-mode, Row-factory connection and auto-commit / rollback."""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ─────────────────────────────  SCHEMA INIT  ─────────────────────────────────

def initialize_database() -> None:
    """Create all tables if they do not already exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        username          TEXT UNIQUE NOT NULL,
        password_hash     TEXT NOT NULL,
        business_name     TEXT NOT NULL,
        city              TEXT NOT NULL,
        shop_type         TEXT NOT NULL,
        clothing_category TEXT NOT NULL,
        avg_price_range   TEXT NOT NULL,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS competitors (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        name       TEXT NOT NULL,
        website    TEXT DEFAULT '',
        location   TEXT DEFAULT '',
        category   TEXT DEFAULT '',
        instagram  TEXT DEFAULT '',
        is_active  INTEGER DEFAULT 1,
        added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS competitor_updates (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        competitor_id    INTEGER NOT NULL,
        competitor_name  TEXT NOT NULL,
        update_type      TEXT NOT NULL,
        title            TEXT NOT NULL,
        description      TEXT DEFAULT '',
        price            REAL DEFAULT 0,
        original_price   REAL DEFAULT 0,
        discount_pct     REAL DEFAULT 0,
        detected_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (competitor_id) REFERENCES competitors(id)
    );

    CREATE TABLE IF NOT EXISTS sales_data (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        sale_date        DATE NOT NULL,
        daily_sales      INTEGER DEFAULT 0,
        revenue          REAL    DEFAULT 0.0,
        inventory_count  INTEGER DEFAULT 0,
        customer_reviews TEXT    DEFAULT '',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, sale_date),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        competitor_id   INTEGER,
        user_id         INTEGER,
        review_source   TEXT DEFAULT 'google',
        reviewer_name   TEXT DEFAULT 'Anonymous',
        review_text     TEXT NOT NULL,
        rating          REAL DEFAULT 0,
        sentiment_label TEXT DEFAULT 'neutral',
        sentiment_score REAL DEFAULT 0,
        review_date     DATE,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS alerts_log (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        alert_type       TEXT NOT NULL,
        title            TEXT NOT NULL,
        message          TEXT NOT NULL,
        competitor_name  TEXT DEFAULT '',
        whatsapp_sent    INTEGER DEFAULT 0,
        is_read          INTEGER DEFAULT 0,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS brochure_analysis (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        filename         TEXT NOT NULL,
        file_type        TEXT NOT NULL,
        extracted_text   TEXT DEFAULT '',
        analysis_result  TEXT DEFAULT '',
        suggestions      TEXT DEFAULT '',
        uploaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS ai_analysis_cache (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key   TEXT UNIQUE NOT NULL,
        result      TEXT NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with _conn() as con:
        con.executescript(ddl)
    logger.info("Database initialised at %s", DB_PATH)


# ─────────────────────────────  USER CRUD  ───────────────────────────────────

def create_user(
    username: str,
    password: str,
    business_name: str,
    city: str,
    shop_type: str,
    clothing_category: str,
    avg_price_range: str,
) -> tuple[bool, str]:
    """Hash password and insert user. Returns (success, message)."""
    try:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with _conn() as con:
            con.execute(
                """INSERT INTO users
                   (username, password_hash, business_name, city, shop_type,
                    clothing_category, avg_price_range)
                   VALUES (?,?,?,?,?,?,?)""",
                (username, pw_hash, business_name, city, shop_type,
                 clothing_category, avg_price_range),
            )
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose another."
    except Exception as exc:
        logger.exception("create_user error")
        return False, f"Error creating account: {exc}"


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Return user dict on valid credentials, else None."""
    try:
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            return dict(row)
        return None
    except Exception:
        logger.exception("verify_user error")
        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ─────────────────────────────  COMPETITOR CRUD  ─────────────────────────────

def add_competitor(
    user_id: int,
    name: str,
    website: str = "",
    location: str = "",
    category: str = "",
    instagram: str = "",
) -> int:
    """Insert a competitor and return its new id."""
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO competitors
               (user_id, name, website, location, category, instagram)
               VALUES (?,?,?,?,?,?)""",
            (user_id, name, website, location, category, instagram),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_competitors(user_id: int) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM competitors WHERE user_id=? AND is_active=1 ORDER BY name",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def competitor_exists(user_id: int, name: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM competitors WHERE user_id=? AND name=?", (user_id, name)
        ).fetchone()
    return row is not None


# ─────────────────────────────  COMPETITOR UPDATES  ──────────────────────────

def add_competitor_update(
    competitor_id: int,
    competitor_name: str,
    update_type: str,
    title: str,
    description: str = "",
    price: float = 0.0,
    original_price: float = 0.0,
    discount_pct: float = 0.0,
) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO competitor_updates
               (competitor_id, competitor_name, update_type, title, description,
                price, original_price, discount_pct)
               VALUES (?,?,?,?,?,?,?,?)""",
            (competitor_id, competitor_name, update_type, title, description,
             price, original_price, discount_pct),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_recent_updates(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            """SELECT cu.*
               FROM competitor_updates cu
               JOIN competitors c ON cu.competitor_id = c.id
               WHERE c.user_id = ?
               ORDER BY cu.detected_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────  SALES DATA  ──────────────────────────────────

def upsert_sales(
    user_id: int,
    sale_date: str,
    daily_sales: int,
    revenue: float,
    inventory_count: int,
    customer_reviews: str = "",
) -> bool:
    try:
        with _conn() as con:
            con.execute(
                """INSERT INTO sales_data
                   (user_id, sale_date, daily_sales, revenue, inventory_count, customer_reviews)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(user_id, sale_date) DO UPDATE SET
                       daily_sales      = excluded.daily_sales,
                       revenue          = excluded.revenue,
                       inventory_count  = excluded.inventory_count,
                       customer_reviews = excluded.customer_reviews""",
                (user_id, sale_date, daily_sales, revenue, inventory_count, customer_reviews),
            )
        return True
    except Exception:
        logger.exception("upsert_sales error")
        return False


def get_sales_data(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM sales_data
               WHERE user_id = ?
               ORDER BY sale_date DESC
               LIMIT ?""",
            (user_id, days),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────  REVIEWS  ─────────────────────────────────────

def add_review(
    competitor_id: Optional[int],
    user_id: Optional[int],
    review_text: str,
    rating: float,
    sentiment_label: str,
    sentiment_score: float,
    review_source: str = "google",
    reviewer_name: str = "Anonymous",
) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO reviews
               (competitor_id, user_id, review_source, reviewer_name, review_text,
                rating, sentiment_label, sentiment_score, review_date)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (competitor_id, user_id, review_source, reviewer_name, review_text,
             rating, sentiment_label, sentiment_score, date.today().isoformat()),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_competitor_reviews(competitor_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM reviews WHERE competitor_id = ?
               ORDER BY review_date DESC LIMIT ?""",
            (competitor_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_reviews_for_user(user_id: int) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            """SELECT r.*, c.name AS competitor_name
               FROM reviews r
               JOIN competitors c ON r.competitor_id = c.id
               WHERE c.user_id = ?
               ORDER BY r.review_date DESC""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_sentiment_summary(user_id: int) -> Dict[str, int]:
    with _conn() as con:
        rows = con.execute(
            """SELECT r.sentiment_label, COUNT(*) AS cnt
               FROM reviews r
               JOIN competitors c ON r.competitor_id = c.id
               WHERE c.user_id = ?
               GROUP BY r.sentiment_label""",
            (user_id,),
        ).fetchall()
    summary: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    for row in rows:
        label = (row["sentiment_label"] or "neutral").lower()
        summary[label] = row["cnt"]
    return summary


# ─────────────────────────────  ALERTS  ──────────────────────────────────────

def log_alert(
    user_id: int,
    alert_type: str,
    title: str,
    message: str,
    competitor_name: str = "",
    whatsapp_sent: bool = False,
) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO alerts_log
               (user_id, alert_type, title, message, competitor_name, whatsapp_sent)
               VALUES (?,?,?,?,?,?)""",
            (user_id, alert_type, title, message, competitor_name, int(whatsapp_sent)),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_alerts(
    user_id: int, limit: int = 30, unread_only: bool = False
) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM alerts_log WHERE user_id=?"
    params: list = [user_id]
    if unread_only:
        sql += " AND is_read=0"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def mark_alerts_read(user_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE alerts_log SET is_read=1 WHERE user_id=?", (user_id,))


def get_unread_count(user_id: int) -> int:
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) AS cnt FROM alerts_log WHERE user_id=? AND is_read=0",
            (user_id,),
        ).fetchone()
    return row["cnt"] if row else 0


# ─────────────────────────────  BROCHURE  ────────────────────────────────────

def save_brochure_analysis(
    user_id: int,
    filename: str,
    file_type: str,
    extracted_text: str,
    analysis_result: str,
    suggestions: str,
) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO brochure_analysis
               (user_id, filename, file_type, extracted_text, analysis_result, suggestions)
               VALUES (?,?,?,?,?,?)""",
            (user_id, filename, file_type, extracted_text, analysis_result, suggestions),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_brochure_analyses(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM brochure_analysis
               WHERE user_id=? ORDER BY uploaded_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────  CACHE  ───────────────────────────────────────

def cache_get(key: str) -> Optional[str]:
    with _conn() as con:
        row = con.execute(
            "SELECT result FROM ai_analysis_cache WHERE cache_key=?", (key,)
        ).fetchone()
    return row["result"] if row else None


def cache_set(key: str, value: str) -> None:
    with _conn() as con:
        con.execute(
            """INSERT INTO ai_analysis_cache (cache_key, result)
               VALUES (?,?)
               ON CONFLICT(cache_key) DO UPDATE SET result=excluded.result,
               created_at=CURRENT_TIMESTAMP""",
            (key, value),
        )
