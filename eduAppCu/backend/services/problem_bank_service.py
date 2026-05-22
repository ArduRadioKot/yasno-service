import random
import re
import time
from html import unescape
from typing import Any

from services.db import (
    count_problem_bank,
    get_problem_bank_by_topic,
    get_problem_bank_random,
    init_problem_bank_table,
    insert_problem_bank_batch,
)

try:
    from sdamgia import SdamGIA

    _sdamgia = SdamGIA()
    _sdamgia_import_error = None
except ImportError as exc:
    _sdamgia = None
    _sdamgia_import_error = exc
except Exception as exc:
    _sdamgia = None
    _sdamgia_import_error = exc

SUBJECT_TO_SDAMGIA = {
    "physics": "phys",
    "math": "math",
    "russian": "rus",
    "history": "hist",
    "chemistry": "chem",
    "informatics": "inf",
    "biology": "bio",
    "geography": "geo",
    "literature": "lit",
    "french": "fr",
    "social": "soc",
}

SIMILAR_TOPIC_MIN_SCORE = 0.32
_TOPIC_STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "по",
    "к",
    "с",
    "из",
    "для",
    "от",
    "до",
    "при",
    "о",
    "об",
    "the",
    "of",
    "in",
    "on",
    "at",
    "to",
    "часть",
    "задание",
    "задачи",
    "тема",
    "раздел",
}


class ProblemBankError(Exception):
    """Задачи не удалось получить только с sdamgia.ru."""


def _topic_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zа-яё0-9]+", (text or "").casefold())
    return {word for word in words if len(word) >= 3 and word not in _TOPIC_STOPWORDS}


def _matches_topic_filter(*names: str, topic_filter: str) -> bool:
    needle = topic_filter.casefold().strip()
    if not needle:
        return True
    for name in names:
        hay = (name or "").casefold().strip()
        if not hay:
            continue
        if needle in hay or hay in needle:
            return True
    return False


def _topic_match_score(topic_filter: str, *names: str) -> float:
    if not topic_filter:
        return 1.0
    if _matches_topic_filter(*names, topic_filter=topic_filter):
        return 1.0

    needle_tokens = _topic_tokens(topic_filter)
    if not needle_tokens:
        return 0.0

    best = 0.0
    for name in names:
        hay = (name or "").casefold().strip()
        if not hay:
            continue

        hay_tokens = _topic_tokens(hay)
        if hay_tokens:
            overlap = needle_tokens & hay_tokens
            if overlap:
                union = needle_tokens | hay_tokens
                jaccard = len(overlap) / len(union)
                best = max(best, 0.4 + 0.5 * jaccard)

        for token in sorted(needle_tokens, key=len, reverse=True):
            if len(token) >= 4 and token in hay:
                best = max(best, 0.5 + min(0.35, len(token) / max(len(topic_filter), 1)))

        first_word = topic_filter.casefold().split()[0] if topic_filter.split() else ""
        if len(first_word) >= 4 and first_word in hay:
            best = max(best, 0.55)

    return min(best, 0.92)


def _matches_topic_similar(*names: str, topic_filter: str) -> bool:
    return _topic_match_score(topic_filter, *names) >= SIMILAR_TOPIC_MIN_SCORE


def _strip_html(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        parts = []
        for key in ("text", "content", "html"):
            if key in value and value[key]:
                parts.append(_strip_html(value[key]))
        return " ".join(parts).strip()
    if isinstance(value, list):
        return " ".join(_strip_html(item) for item in value).strip()
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_problem_row(subject_id: str, row: dict) -> dict:
    return {
        "subject_id": subject_id,
        "external_id": str(row.get("external_id") or row.get("id") or ""),
        "topic": str(row.get("topic") or "Общая тема").strip(),
        "condition": _strip_html(row.get("condition")),
        "solution": _strip_html(row.get("solution")),
        "answer": _strip_html(row.get("answer")),
        "url": str(row.get("url") or "").strip(),
    }


def _get_sdamgia_client() -> SdamGIA:
    if _sdamgia is None:
        detail = str(_sdamgia_import_error) if _sdamgia_import_error else "пакет не установлен"
        hint = (
            "Установите правильный пакет из примера sdamgIA_example.py: "
            "pip uninstall -y sdamgia && pip install sdamgia-api==0.1.7"
        )
        if "SdamGIA" in detail or "cannot import name" in detail:
            hint = (
                "Установлен другой пакет «sdamgia» (0.2.x). Нужен sdamgia-api: "
                "pip uninstall -y sdamgia && pip install sdamgia-api==0.1.7"
            )
        raise ProblemBankError(f"Библиотека sdamgia-api недоступна ({detail}). {hint}")
    return _sdamgia


def _collect_category_candidates(
    catalog: list,
    topic_filter: str | None,
) -> list[tuple[float, str, str, Any]]:
    candidates: list[tuple[float, str, str, Any]] = []

    for topic in catalog:
        topic_name = topic.get("topic_name") or "Тема"
        for category in topic.get("categories") or []:
            category_id = category.get("category_id")
            category_name = category.get("category_name") or topic_name
            if not category_id:
                continue

            if topic_filter:
                score = _topic_match_score(topic_filter, topic_name, category_name)
                if score < SIMILAR_TOPIC_MIN_SCORE:
                    continue
            else:
                score = 1.0

            candidates.append((score, topic_name, category_name, category_id))

    candidates.sort(key=lambda item: (-item[0], random.random()))
    return candidates


def _fetch_problems_from_categories(
    sdamgia,
    sdam_subject: str,
    subject_id: str,
    candidates: list[tuple[float, str, str, Any]],
    needed: int,
) -> list[dict]:
    collected: list[dict] = []
    seen_ids: set[str] = set()

    for _score, topic_name, category_name, category_id in candidates:
        if len(collected) >= needed:
            break

        try:
            problem_ids = sdamgia.get_category_by_id(sdam_subject, category_id) or []
        except Exception:
            continue

        if not problem_ids:
            continue

        random.shuffle(problem_ids)
        for problem_id in problem_ids:
            if len(collected) >= needed:
                break

            problem_key = str(problem_id)
            if problem_key in seen_ids:
                continue

            try:
                problem_data = sdamgia.get_problem_by_id(sdam_subject, problem_id)
            except Exception:
                continue

            if not problem_data:
                continue

            condition = _strip_html(problem_data.get("condition"))
            if len(condition) < 10:
                continue

            seen_ids.add(problem_key)
            collected.append(
                _normalize_problem_row(
                    subject_id,
                    {
                        "external_id": problem_key,
                        "topic": category_name,
                        "condition": condition,
                        "solution": problem_data.get("solution"),
                        "answer": problem_data.get("answer"),
                        "url": problem_data.get("url", ""),
                    },
                )
            )
            time.sleep(0.04)

        time.sleep(0.2)

    return collected


def _fetch_from_sdamgia(subject_id: str, needed: int, topic_filter: str | None = None) -> list[dict]:
    sdamgia = _get_sdamgia_client()
    sdam_subject = SUBJECT_TO_SDAMGIA.get(subject_id)
    if not sdam_subject:
        raise ProblemBankError(
            f"Предмет «{subject_id}» не сопоставлен с кодом sdamgia. "
            f"Доступны: {', '.join(SUBJECT_TO_SDAMGIA.keys())}"
        )

    catalog = sdamgia.get_catalog(sdam_subject)
    if not catalog:
        raise ProblemBankError(f"Не удалось получить каталог заданий по предмету {sdam_subject} с sdamgia.ru")

    random.shuffle(catalog)
    candidates = _collect_category_candidates(catalog, topic_filter)
    if topic_filter and not candidates:
        raise ProblemBankError(
            f"На sdamgia.ru не найдено тем, похожих на «{topic_filter}», по предмету «{subject_id}»."
        )

    return _fetch_problems_from_categories(
        sdamgia,
        sdam_subject,
        subject_id,
        candidates,
        needed,
    )


def ensure_problem_bank(subject_id: str, min_count: int = 8) -> None:
    init_problem_bank_table()
    if count_problem_bank(subject_id) >= min_count:
        return

    fetched = _fetch_from_sdamgia(subject_id, min_count)
    if not fetched:
        raise ProblemBankError(
            f"Не удалось загрузить задания с sdamgia.ru для предмета «{subject_id}»"
        )
    insert_problem_bank_batch(fetched)


def get_problems_for_test(
    subject_id: str,
    count: int,
    topic_filter: str | None = None,
) -> list[dict]:
    """
    Возвращает ровно count задач для теста только с sdamgia.ru.
    При topic_filter — задачи из темы и близких по названию разделов каталога.
    """
    count = max(1, min(count, 12))
    topic_filter = (topic_filter or "").strip() or None
    init_problem_bank_table()

    collected: list[dict] = []
    seen: set[str] = set()
    fetch_batch = count * 6 if topic_filter else count

    def add_rows(rows: list[dict]) -> None:
        for row in rows:
            if len(collected) >= count:
                return
            if topic_filter and not _matches_topic_similar(
                row.get("topic", ""), topic_filter=topic_filter
            ):
                continue
            eid = str(row.get("external_id") or "")
            if not eid or eid in seen:
                continue
            condition = row.get("condition") or ""
            if len(condition) < 10:
                continue
            seen.add(eid)
            collected.append(row)

    live = _fetch_from_sdamgia(subject_id, fetch_batch, topic_filter=topic_filter)
    if live:
        insert_problem_bank_batch(live)
        add_rows(live)

    if len(collected) < count:
        db_rows = get_problem_bank_by_topic(subject_id, topic_filter or "", count * 8)
        if topic_filter:
            db_rows = [
                row
                for row in db_rows
                if _matches_topic_similar(row.get("topic", ""), topic_filter=topic_filter)
            ]
        add_rows(db_rows)

    if len(collected) < count and not topic_filter:
        add_rows(get_problem_bank_random(subject_id, count * 5))

    if len(collected) < count:
        extra = _fetch_from_sdamgia(
            subject_id,
            fetch_batch + (count - len(collected)),
            topic_filter=topic_filter,
        )
        if extra:
            insert_problem_bank_batch(extra)
            add_rows(extra)

    if len(collected) < count:
        if topic_filter:
            raise ProblemBankError(
                f"По теме «{topic_filter}» и похожим разделам найдено только {len(collected)} из {count} "
                f"заданий на sdamgia.ru. Попробуйте меньше вопросов или другую тему."
            )
        raise ProblemBankError(
            f"С sdamgia.ru получено только {len(collected)} из {count} заданий "
            f"по предмету «{subject_id}». Проверьте интернет и доступность sdamgia.ru."
        )

    return collected[:count]


def get_random_problems(
    subject_id: str,
    count: int,
    topic_filter: str | None = None,
) -> list[dict]:
    return get_problems_for_test(subject_id, count, topic_filter=topic_filter)
