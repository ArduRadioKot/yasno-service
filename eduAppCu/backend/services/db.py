"""Database module with PostgreSQL support and premium keys functionality"""

import json
import re
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import uuid

load_dotenv()

# PostgreSQL connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "edu_app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")


@contextmanager
def get_db_connection():
    """Create and return a database connection context manager."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                exam_type TEXT DEFAULT 'ЕГЭ',
                marketing BOOLEAN DEFAULT FALSE,
                premium_key_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create user_subjects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subjects (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                subject_id TEXT NOT NULL,
                target_score INTEGER DEFAULT 80,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, subject_id)
            )
        """)
        
        # Create user_progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                subject_id TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                score_delta INTEGER DEFAULT 0,
                chart TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, subject_id)
            )
        """)
        
        # Create user_settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                active_subject_id TEXT,
                streak INTEGER DEFAULT 0,
                last_active_date TEXT,
                achievements INTEGER DEFAULT 0,
                completed_task_ids TEXT DEFAULT '[]',
                topic_progress TEXT DEFAULT '{}',
                plan_topics TEXT DEFAULT '{}',
                subject_task_progress TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)
        
        # Create premium_keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS premium_keys (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                duration_days INTEGER DEFAULT 30,
                is_active BOOLEAN DEFAULT TRUE,
                is_used BOOLEAN DEFAULT FALSE,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        # Migrate user_settings: plan metadata per subject (forecast, weekly goals)
        cursor.execute("""
            DO $$ BEGIN
                ALTER TABLE user_settings ADD COLUMN plan_meta TEXT DEFAULT '{}';
            EXCEPTION
                WHEN duplicate_column THEN NULL;
            END $$;
        """)

        # Create problem_bank table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS problem_bank (
                id SERIAL PRIMARY KEY,
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
        print("✅ Database initialized successfully")


# ==================== Premium Key Functions ====================

def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Normalize PostgreSQL timestamp values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def generate_premium_key(duration_days: int = 30) -> str:
    """Generate a unique premium key."""
    return f"PREMIUM-{uuid.uuid4().hex.upper()[:16]}"


def create_premium_key(duration_days: int = 30) -> str:
    """Create a new premium key in the database."""
    key = generate_premium_key(duration_days)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO premium_keys (key, duration_days, expires_at)
            VALUES (%s, %s, NULL)
            RETURNING key
        """, (key, duration_days))
        result = cursor.fetchone()
        conn.commit()

    return result[0] if result else key


def validate_premium_key(key: str) -> Dict[str, Any]:
    """Validate a premium key and return its status."""
    normalized_key = key.strip().upper()
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, key, is_active, is_used, user_id, expires_at, created_at
            FROM premium_keys
            WHERE UPPER(key) = %s
        """, (normalized_key,))
        row = cursor.fetchone()

    if not row:
        return {"valid": False, "message": "Ключ не найден"}

    if not row["is_active"]:
        return {"valid": False, "message": "Ключ неактивный"}

    if row["is_used"]:
        expires_at = _parse_timestamp(row["expires_at"])
        if expires_at and expires_at < datetime.now():
            return {"valid": False, "message": "Ключ истёк"}
        return {
            "valid": True,
            "message": "Ключ активен",
            "user_id": row["user_id"],
            "expires_at": row["expires_at"],
        }

    return {
        "valid": True,
        "message": "Ключ доступен для активации",
        "key_id": row["id"],
    }


def activate_premium_key(key: str, user_id: int) -> Dict[str, Any]:
    """Activate a premium key for a user."""
    normalized_key = key.strip().upper()
    validation = validate_premium_key(normalized_key)

    if not validation["valid"]:
        return validation

    if validation.get("user_id"):
        if validation.get("user_id") == user_id:
            return {
                "valid": True,
                "message": "Ключ уже активирован для этого аккаунта",
                "expires_at": validation.get("expires_at"),
            }
        return {"valid": False, "message": "Ключ уже использован другим аккаунтом"}

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            UPDATE premium_keys
            SET
                is_used = TRUE,
                user_id = %s,
                used_at = CURRENT_TIMESTAMP,
                expires_at = CURRENT_TIMESTAMP + (duration_days || ' days')::INTERVAL
            WHERE UPPER(key) = %s AND is_used = FALSE
            RETURNING expires_at
        """, (user_id, normalized_key))
        result = cursor.fetchone()

        if not result:
            return {"valid": False, "message": "Ключ уже использован"}

        cursor.execute("""
            UPDATE users
            SET premium_key_id = (SELECT id FROM premium_keys WHERE UPPER(key) = %s)
            WHERE id = %s
        """, (normalized_key, user_id))
        conn.commit()

    return {
        "valid": True,
        "message": "Ключ успешно активирован",
        "expires_at": result["expires_at"],
    }


def get_user_premium_status(user_id: int) -> Dict[str, Any]:
    """Get premium subscription status for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT pk.key, pk.expires_at, pk.is_active
            FROM premium_keys pk
            WHERE pk.user_id = %s AND pk.is_used = TRUE
            ORDER BY pk.used_at DESC NULLS LAST
            LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()

    if not result:
        return {"is_premium": False, "message": "У пользователя нет премиум подписки"}

    expires_at = _parse_timestamp(result["expires_at"])
    is_active = bool(result["is_active"] and expires_at and expires_at > datetime.now())

    return {
        "is_premium": is_active,
        "expires_at": result["expires_at"],
        "days_left": max(0, (expires_at - datetime.now()).days) if is_active and expires_at else 0,
        "message": "Премиум активен" if is_active else "Срок подписки истёк",
    }


def is_user_premium_by_email(email: str) -> bool:
    """Check if user has an active premium subscription."""
    user = get_user_by_email(email)
    if not user:
        return False
    return get_user_premium_status(user["id"]).get("is_premium", False)


def revoke_premium_key(key: str) -> bool:
    """Revoke/deactivate a premium key."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE premium_keys
            SET is_active = FALSE
            WHERE key = %s
            RETURNING id
        """, (key,))
        result = cursor.fetchone()
        conn.commit()
    
    return bool(result)


def list_premium_keys(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List all premium keys (for admin)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, key, is_active, is_used, user_id, expires_at, created_at
            FROM premium_keys
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = cursor.fetchall()
    
    return [dict(row) for row in rows]


# ==================== Problem Bank Functions ====================

def init_problem_bank_table():
    """Ensure problem_bank table exists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS problem_bank (
                id SERIAL PRIMARY KEY,
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


def count_problem_bank(subject_id: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM problem_bank WHERE subject_id = %s",
            (subject_id,),
        )
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def insert_problem_bank_batch(rows: list[dict]) -> None:
    if not rows:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for row in rows:
            try:
                cursor.execute(
                    """
                    INSERT INTO problem_bank
                    (subject_id, external_id, topic, condition, solution, answer, url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (subject_id, external_id) DO UPDATE SET
                        topic = EXCLUDED.topic,
                        condition = EXCLUDED.condition,
                        solution = EXCLUDED.solution,
                        answer = EXCLUDED.answer,
                        url = EXCLUDED.url
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
            except Exception:
                pass
        conn.commit()


def get_problem_bank_random(subject_id: str, count: int) -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT external_id, topic, condition, solution, answer, url
            FROM problem_bank
            WHERE subject_id = %s
            ORDER BY RANDOM()
            LIMIT %s
            """,
            (subject_id, count),
        )
        rows = cursor.fetchall()
    return [dict(r) for r in rows]


def get_problem_bank_by_topic(subject_id: str, topic_filter: str, count: int) -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        needle = topic_filter.strip()
        tokens = [
            token
            for token in re.findall(r"[a-zа-яё0-9]+", needle.casefold())
            if len(token) >= 3
        ]
        
        # Build WHERE clause
        where_clause = "LOWER(topic) ILIKE %s"
        params = [subject_id, f"%{needle}%"]
        
        for token in tokens[:4]:
            where_clause += f" OR LOWER(topic) ILIKE %s"
            params.append(f"%{token}%")
        
        cursor.execute(
            f"""
            SELECT external_id, topic, condition, solution, answer, url
            FROM problem_bank
            WHERE subject_id = %s AND ({where_clause})
            ORDER BY RANDOM()
            LIMIT %s
            """,
            params + [count],
        )
        rows = cursor.fetchall()
    
    return [dict(r) for r in rows]


# ==================== User Functions ====================

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
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO users (email, password, first_name, last_name, exam_type, marketing)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (email, password, first_name, last_name, exam_type, marketing)
            )
            user_id = cursor.fetchone()[0]
            
            # Insert selected subjects with targets
            for subject_id in subjects:
                from services.exam_utils import normalize_target_score
                target_score = normalize_target_score(
                    targets.get(subject_id, 80), exam_type
                )
                cursor.execute(
                    """
                    INSERT INTO user_subjects (user_id, subject_id, target_score)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, subject_id, target_score)
                )
            
            # Initialize progress
            for subject_id in subjects:
                cursor.execute(
                    """
                    INSERT INTO user_progress (user_id, subject_id, score, score_delta, chart)
                    VALUES (%s, %s, 0, 0, %s)
                    """,
                    (user_id, subject_id, json.dumps([]))
                )
            
            # Initialize settings
            active_subject = subjects[0] if subjects else None
            cursor.execute(
                """
                INSERT INTO user_settings (user_id, active_subject_id, streak, achievements, completed_task_ids, last_active_date)
                VALUES (%s, %s, 0, 0, %s, %s)
                """,
                (user_id, active_subject, json.dumps([]), datetime.now().date().isoformat())
            )
            
            conn.commit()
            return user_id
        except Exception as e:
            conn.rollback()
            raise e


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
    
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
    
    return dict(row) if row else None


def get_user_subjects(user_id: int) -> List[str]:
    """Get list of subject IDs for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT subject_id FROM user_subjects WHERE user_id = %s",
            (user_id,)
        )
        rows = cursor.fetchall()
    
    return [row[0] for row in rows]


def get_user_targets(user_id: int) -> Dict[str, int]:
    """Get target scores for user's subjects."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT subject_id, target_score FROM user_subjects WHERE user_id = %s",
            (user_id,)
        )
        rows = cursor.fetchall()
    
    return {row["subject_id"]: row["target_score"] for row in rows}


def get_user_settings(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user settings."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
    
    if not row:
        return None
    
    result = dict(row)
    # Parse JSON fields
    result["completed_task_ids"] = json.loads(result.get("completed_task_ids", "[]"))
    result["topic_progress"] = json.loads(result.get("topic_progress", "{}"))
    result["plan_topics"] = json.loads(result.get("plan_topics", "{}"))
    result["subject_task_progress"] = json.loads(result.get("subject_task_progress", "{}"))
    result["plan_meta"] = json.loads(result.get("plan_meta", "{}"))
    
    return result


def update_user_settings(
    user_id: int,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """Update user settings."""
    if not kwargs:
        return get_user_settings(user_id)
    
    # Convert list/dict to JSON strings
    for key in ["completed_task_ids", "topic_progress", "plan_topics", "subject_task_progress", "plan_meta"]:
        if key in kwargs and isinstance(kwargs[key], (list, dict)):
            kwargs[key] = json.dumps(kwargs[key])
    
    set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE user_settings SET {set_clause} WHERE user_id = %s",
            values
        )
        conn.commit()
    
    return get_user_settings(user_id)


def get_user_progress(user_id: int, subject_id: str) -> Optional[Dict[str, Any]]:
    """Get user's progress in a subject."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM user_progress WHERE user_id = %s AND subject_id = %s",
            (user_id, subject_id)
        )
        row = cursor.fetchone()
    
    if not row:
        return None
    
    result = dict(row)
    result["chart"] = json.loads(result.get("chart", "[]"))
    return result


def upsert_user_progress(
    user_id: int,
    subject_id: str,
    **kwargs
) -> Dict[str, Any]:
    """Insert or update user progress."""
    # Convert list to JSON
    if "chart" in kwargs and isinstance(kwargs["chart"], list):
        kwargs["chart"] = json.dumps(kwargs["chart"])
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if record exists
        cursor.execute(
            "SELECT id FROM user_progress WHERE user_id = %s AND subject_id = %s",
            (user_id, subject_id)
        )
        exists = cursor.fetchone()
        
        if exists:
            set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id, subject_id]
            cursor.execute(
                f"UPDATE user_progress SET {set_clause} WHERE user_id = %s AND subject_id = %s",
                values
            )
        else:
            keys = ["user_id", "subject_id"] + list(kwargs.keys())
            values = [user_id, subject_id] + list(kwargs.values())
            placeholders = ", ".join(["%s"] * len(keys))
            cursor.execute(
                f"INSERT INTO user_progress ({', '.join(keys)}) VALUES ({placeholders})",
                values
            )
        
        conn.commit()
    
    return get_user_progress(user_id, subject_id) or {}


def get_topic_progress(user_id: int, subject_id: str) -> Optional[Dict[str, Any]]:
    """Get topic progress for a user in a subject."""
    settings = get_user_settings(user_id)
    if not settings:
        return None
    
    topic_progress = settings.get("topic_progress", {})
    return topic_progress.get(subject_id)


def set_topic_progress(
    user_id: int,
    subject_id: str,
    topic_id: str,
    status: str = None,
    progress: int = None
) -> None:
    """Set progress for a specific topic."""
    settings = get_user_settings(user_id) or {}
    topic_progress = settings.get("topic_progress", {})
    
    if subject_id not in topic_progress:
        topic_progress[subject_id] = {}
    
    if topic_id not in topic_progress[subject_id]:
        topic_progress[subject_id][topic_id] = {}
    
    if status:
        topic_progress[subject_id][topic_id]["status"] = status
    if progress is not None:
        topic_progress[subject_id][topic_id]["progress"] = progress
    
    update_user_settings(user_id, topic_progress=topic_progress)


def get_user_plan_topics(user_id: int, subject_id: str) -> List[Dict[str, Any]]:
    """Get plan topics for a user in a subject."""
    settings = get_user_settings(user_id)
    if not settings:
        return []
    
    plan_topics = settings.get("plan_topics", {})
    return plan_topics.get(subject_id, [])


def update_plan_topic_entry(
    user_id: int,
    subject_id: str,
    topic_id: str,
    status: str = None,
    progress: int = None
) -> None:
    """Update a plan topic entry."""
    settings = get_user_settings(user_id) or {}
    plan_topics = settings.get("plan_topics", {})
    
    if subject_id not in plan_topics:
        plan_topics[subject_id] = []
    
    topics_list = plan_topics[subject_id]
    found = False
    
    for topic in topics_list:
        if topic.get("id") == topic_id:
            if status:
                topic["status"] = status
            if progress is not None:
                topic["progress"] = progress
            found = True
            break
    
    if not found:
        new_topic = {"id": topic_id}
        if status:
            new_topic["status"] = status
        if progress is not None:
            new_topic["progress"] = progress
        topics_list.append(new_topic)
    
    plan_topics[subject_id] = topics_list
    update_user_settings(user_id, plan_topics=plan_topics)


def add_completed_task(user_id: int, task_id: str) -> None:
    """Add a completed task to user's list."""
    settings = get_user_settings(user_id) or {}
    completed = settings.get("completed_task_ids", [])
    
    if task_id not in completed:
        completed.append(task_id)
        update_user_settings(user_id, completed_task_ids=completed)


def get_subject_task_progress(user_id: int, subject_id: str) -> Optional[Dict[str, Any]]:
    """Get task progress for a subject."""
    settings = get_user_settings(user_id)
    if not settings:
        return None
    
    task_progress = settings.get("subject_task_progress", {})
    return task_progress.get(subject_id)


def get_user_plan_meta(user_id: int, subject_id: str) -> Dict[str, Any]:
    """Get persisted plan metadata (forecast, weekly goals) for a subject."""
    settings = get_user_settings(user_id)
    if not settings:
        return {}
    plan_meta = settings.get("plan_meta", {})
    return plan_meta.get(subject_id, {})


def save_user_plan_meta(user_id: int, subject_id: str, meta: Dict[str, Any]) -> None:
    """Persist plan metadata for a subject."""
    settings = get_user_settings(user_id) or {}
    plan_meta = settings.get("plan_meta", {})
    existing = plan_meta.get(subject_id, {})
    existing.update(meta)
    plan_meta[subject_id] = existing
    update_user_settings(user_id, plan_meta=plan_meta)


def merge_plan_topics_from_gaps(user_id: int, subject_id: str, gaps: list[str]) -> list[dict]:
    """Merge AI-detected gaps into the user's plan topics."""
    settings = get_user_settings(user_id) or {}
    all_topics = settings.get("plan_topics") or {}
    items = list(all_topics.get(subject_id, []))
    existing = {item["name"].casefold(): item for item in items if item.get("name")}

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


def record_test_task_progress(
    user_id: int,
    subject_id: str,
    correct_count: int,
    total_count: int,
    plan_topic_count: int = 0
) -> None:
    """Record test task progress."""
    settings = get_user_settings(user_id) or {}
    task_progress = settings.get("subject_task_progress", {})
    
    if subject_id not in task_progress:
        task_progress[subject_id] = {
            "correct": 0,
            "total": 0,
            "accuracy": 0,
            "goal": 5,
        }
    
    task_progress[subject_id]["correct"] += correct_count
    task_progress[subject_id]["total"] += total_count
    task_progress[subject_id]["goal"] = max(
        int(task_progress[subject_id].get("goal", 0)),
        plan_topic_count,
        5,
    )
    
    if task_progress[subject_id]["total"] > 0:
        accuracy = (task_progress[subject_id]["correct"] / task_progress[subject_id]["total"]) * 100
        task_progress[subject_id]["accuracy"] = round(accuracy)
    
    update_user_settings(user_id, subject_task_progress=task_progress)
