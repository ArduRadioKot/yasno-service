import sqlite3
import json
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
    
    conn.commit()
    conn.close()


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
            target_score = targets.get(subject_id, 80)
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
            if key in ["active_subject_id", "streak", "achievements", "completed_task_ids", "last_active_date"]:
                if key == "completed_task_ids" and isinstance(value, list):
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
