import json
import re
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "edu_app.db"


def get_db_connection():
    """Create and return a database connection."""
    # Ensure DB directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            exam_type TEXT DEFAULT 'ЕГЭ',
            marketing BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create user_subjects table for storing selected subjects and targets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id TEXT NOT NULL,
            target_score INTEGER DEFAULT 80,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, subject_id)
        )
    """)
    
    # Create user_progress table for storing progress data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            score_delta INTEGER DEFAULT 0,
            chart TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, subject_id)
        )
    """)
    
    # Create user_settings table for storing general user settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            active_subject_id TEXT,
            streak INTEGER DEFAULT 0,
            last_active_date TEXT,
            achievements INTEGER DEFAULT 0,
            completed_task_ids TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id)
        )
    """)
    
    # Migration: Add last_active_date column if it doesn't exist
    try:
        cursor.execute("SELECT last_active_date FROM user_settings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN last_active_date TEXT")

    try:
        cursor.execute("SELECT topic_progress FROM user_settings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN topic_progress TEXT DEFAULT '{}'")

    try:
        cursor.execute("SELECT plan_topics FROM user_settings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN plan_topics TEXT DEFAULT '{}'")

    try:
        cursor.execute("SELECT subject_task_progress FROM user_settings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN subject_task_progress TEXT DEFAULT '{}'"
        )
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problem_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id TEXT NOT NULL,
            external_id TEXT NOT NULL,
            topic TEXT,
            condition TEXT NOT NULL,
            solution TEXT,
            answer TEXT,
            url TEXT,
            UNIQUE(subject_id, external_id)
        )
    """)

    conn.commit()
    conn.close()


def init_problem_bank_table():
    """Ensure problem_bank table exists (for lazy init from services)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problem_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id TEXT NOT NULL,
            external_id TEXT NOT NULL,
            topic TEXT,
            condition TEXT NOT NULL,
            solution TEXT,
            answer TEXT,
            url TEXT,
            UNIQUE(subject_id, external_id)
        )
    """)
    conn.commit()
    conn.close()


def count_problem_bank(subject_id: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM problem_bank WHERE subject_id = ?",
        (subject_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return int(row["cnt"]) if row else 0


def insert_problem_bank_batch(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    for row in rows:
        cursor.execute(
            """
            INSERT OR IGNORE INTO problem_bank
            (subject_id, external_id, topic, condition, solution, answer, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["subject_id"],
                row["external_id"],
                row.get("topic"),
                row["condition"],
                row.get("solution"),
                row.get("answer"),
                row.get("url"),
            ),
        )
    conn.commit()
    conn.close()


def get_problem_bank_random(subject_id: str, count: int) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT external_id, topic, condition, solution, answer, url
        FROM problem_bank
        WHERE subject_id = ?
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (subject_id, count),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_problem_bank_by_topic(subject_id: str, topic_filter: str, count: int) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    needle = topic_filter.strip()
    tokens = [
        token
        for token in re.findall(r"[a-zа-яё0-9]+", needle.casefold())
        if len(token) >= 3
    ]
    patterns = [f"%{needle}%", *[f"%{token}%" for token in tokens[:4]]]
    clauses = ["LOWER(topic) LIKE LOWER(?)"] * len(patterns)
    cursor.execute(
        f"""
        SELECT external_id, topic, condition, solution, answer, url
        FROM problem_bank
        WHERE subject_id = ? AND ({' OR '.join(clauses)})
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (subject_id, *patterns, count),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def create_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    exam_type: str = "ЕГЭ",
    marketing: bool = False,
    subjects: List[str] = None,
    targets: Dict[str, int] = None
) -> int:
    """Create a new user and return their ID."""
    if subjects is None:
        subjects = []
    if targets is None:
        targets = {}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert user
        cursor.execute(
            """
            INSERT INTO users (email, password, first_name, last_name, exam_type, marketing)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, password, first_name, last_name, exam_type, marketing)
        )
        user_id = cursor.lastrowid
        
        # Insert selected subjects with targets
        for subject_id in subjects:
            from services.exam_utils import normalize_target_score

            target_score = normalize_target_score(
                targets.get(subject_id, 80), exam_type
            )
            cursor.execute(
                """
                INSERT INTO user_subjects (user_id, subject_id, target_score)
                VALUES (?, ?, ?)
                """,
                (user_id, subject_id, target_score)
            )
        
        # Initialize progress for selected subjects
        for subject_id in subjects:
            cursor.execute(
                """
                INSERT INTO user_progress (user_id, subject_id, score, score_delta, chart)
                VALUES (?, ?, 0, 0, '[]')
                """,
                (user_id, subject_id)
            )
        
        # Initialize user settings
        active_subject = subjects[0] if subjects else None
        cursor.execute(
            """
            INSERT INTO user_settings (user_id, active_subject_id, streak, achievements, completed_task_ids, last_active_date)
            VALUES (?, ?, 0, 0, '[]', DATE('now'))
            """,
            (user_id, active_subject)
        )
        
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_subjects(user_id: int) -> List[str]:
    """Get list of subject IDs for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT subject_id FROM user_subjects WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [row["subject_id"] for row in rows]


def get_user_targets(user_id: int) -> Dict[str, int]:
    """Get target scores for a user's subjects."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT subject_id, target_score FROM user_subjects WHERE user_id = ?",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {row["subject_id"]: row["target_score"] for row in rows}


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get user settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        settings = dict(row)
        # Parse JSON fields
        if settings["completed_task_ids"]:
            settings["completed_task_ids"] = json.loads(settings["completed_task_ids"])
        else:
            settings["completed_task_ids"] = []
        if settings.get("topic_progress"):
            settings["topic_progress"] = json.loads(settings["topic_progress"])
        else:
            settings["topic_progress"] = {}
        if settings.get("plan_topics"):
            settings["plan_topics"] = json.loads(settings["plan_topics"])
        else:
            settings["plan_topics"] = {}
        if settings.get("subject_task_progress"):
            settings["subject_task_progress"] = json.loads(settings["subject_task_progress"])
        else:
            settings["subject_task_progress"] = {}
        return settings
    return {}


def update_user_settings(user_id: int, **kwargs) -> bool:
    """Update user settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build dynamic update query
        update_fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in [
                "active_subject_id",
                "streak",
                "achievements",
                "completed_task_ids",
                "last_active_date",
                "topic_progress",
                "plan_topics",
                "subject_task_progress",
            ]:
                if key in (
                    "completed_task_ids",
                    "topic_progress",
                    "plan_topics",
                    "subject_task_progress",
                ) and isinstance(value, (list, dict)):
                    value = json.dumps(value)
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.append(user_id)
        query = f"UPDATE user_settings SET {', '.join(update_fields)} WHERE user_id = ?"
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_user_progress(user_id: int, subject_id: str) -> Optional[Dict[str, Any]]:
    """Get user progress for a specific subject."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM user_progress WHERE user_id = ? AND subject_id = ?",
        (user_id, subject_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        progress = dict(row)
        # Parse JSON fields
        if progress["chart"]:
            progress["chart"] = json.loads(progress["chart"])
        else:
            progress["chart"] = []
        return progress
    return None


def update_user_progress(user_id: int, subject_id: int, **kwargs) -> bool:
    """Update user progress for a subject."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build dynamic update query
        update_fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ["score", "score_delta", "chart"]:
                if key == "chart" and isinstance(value, list):
                    value = json.dumps(value)
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.extend([subject_id, user_id])
        query = f"UPDATE user_progress SET {', '.join(update_fields)} WHERE subject_id = ? AND user_id = ?"
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_topic_progress(user_id: int, subject_id: str) -> dict:
    settings = get_user_settings(user_id) or {}
    by_subject = settings.get("topic_progress") or {}
    return by_subject.get(subject_id, {})


def get_user_plan_topics(user_id: int, subject_id: str) -> list[dict]:
    settings = get_user_settings(user_id) or {}
    by_subject = settings.get("plan_topics") or {}
    return list(by_subject.get(subject_id, []))


def merge_plan_topics_from_gaps(user_id: int, subject_id: str, gaps: list[str]) -> list[dict]:
    settings = get_user_settings(user_id) or {}
    all_topics = settings.get("plan_topics") or {}
    items = list(all_topics.get(subject_id, []))
    existing = {item["name"].casefold(): item for item in items}

    for index, name in enumerate(gaps):
        label = str(name).strip()
        if not label:
            continue
        key = label.casefold()
        if key in existing:
            topic = existing[key]
            topic["status"] = "in-progress"
            topic["progress"] = min(int(topic.get("progress", 25)), 35)
            continue

        slug = re.sub(r"[^a-zа-я0-9]+", "-", key, flags=re.IGNORECASE).strip("-")
        topic = {
            "id": f"ai-{slug or index}",
            "name": label,
            "progress": 25,
            "status": "in-progress",
            "impact": "из теста",
        }
        items.append(topic)
        existing[key] = topic

    all_topics[subject_id] = items
    update_user_settings(user_id, plan_topics=all_topics)
    return items


def get_subject_task_progress(user_id: int, subject_id: str) -> dict:
    settings = get_user_settings(user_id) or {}
    by_subject = settings.get("subject_task_progress") or {}
    return dict(by_subject.get(subject_id, {}))


def record_test_task_progress(
    user_id: int,
    subject_id: str,
    *,
    correct_count: int,
    total_count: int,
    plan_topic_count: int = 0,
) -> dict:
    settings = get_user_settings(user_id) or {}
    all_progress = settings.get("subject_task_progress") or {}
    entry = dict(all_progress.get(subject_id, {}))

    entry["correct"] = int(entry.get("correct", 0)) + max(0, correct_count)
    entry["answered"] = int(entry.get("answered", 0)) + max(0, total_count)
    entry["tests"] = int(entry.get("tests", 0)) + 1
    entry["goal"] = max(
        int(entry.get("goal", 0)),
        plan_topic_count,
        5,
    )

    all_progress[subject_id] = entry
    update_user_settings(user_id, subject_task_progress=all_progress)
    return entry


def add_completed_task(user_id: int, task_id: str) -> list[str]:
    settings = get_user_settings(user_id) or {}
    completed = list(settings.get("completed_task_ids") or [])
    if task_id not in completed:
        completed.append(task_id)
        update_user_settings(user_id, completed_task_ids=completed)
    return completed


def update_plan_topic_entry(
    user_id: int,
    subject_id: str,
    topic_id: str,
    *,
    status: str,
    progress: int | None = None,
) -> None:
    settings = get_user_settings(user_id) or {}
    all_topics = settings.get("plan_topics") or {}
    items = list(all_topics.get(subject_id, []))
    for item in items:
        if item.get("id") == topic_id:
            item["status"] = status
            if progress is not None:
                item["progress"] = max(0, min(100, int(progress)))
            elif status == "completed":
                item["progress"] = 100
                item["impact"] = "✓"
            elif status == "in-progress" and item.get("progress", 0) < 10:
                item["progress"] = max(item.get("progress", 0), 40)
            break
    all_topics[subject_id] = items
    update_user_settings(user_id, plan_topics=all_topics)


def set_topic_progress(
    user_id: int,
    subject_id: str,
    topic_id: str,
    *,
    status: str,
    progress: int | None = None,
) -> dict:
    settings = get_user_settings(user_id) or {}
    all_progress = settings.get("topic_progress") or {}
    subject_topics = dict(all_progress.get(subject_id, {}))

    entry = dict(subject_topics.get(topic_id, {}))
    entry["status"] = status
    if progress is not None:
        entry["progress"] = max(0, min(100, int(progress)))
    elif status == "completed":
        entry["progress"] = 100
    elif status == "in-progress" and "progress" not in entry:
        entry["progress"] = 50

    subject_topics[topic_id] = entry
    all_progress[subject_id] = subject_topics
    update_user_settings(user_id, topic_progress=all_progress)
    return entry


def upsert_user_progress(user_id: int, subject_id: str, score: int = 0, score_delta: int = 0, chart: list | None = None) -> bool:
    """Insert or update a user_progress row (upsert)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        chart_json = json.dumps(chart or [])
        cursor.execute(
            """
            INSERT INTO user_progress (user_id, subject_id, score, score_delta, chart)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, subject_id) DO UPDATE SET
                score=excluded.score,
                score_delta=excluded.score_delta,
                chart=excluded.chart
            """,
            (user_id, subject_id, score, score_delta, chart_json),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
