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
from services.content_utils import (
    plain_text_from_content,
    resolve_sdamgia_image_urls,
    rich_content_to_html,
    sdamgia_base_from_url,
)
from services.exam_utils import is_oge as exam_is_oge, normalize_exam_type
from services.oge_sdamgia_client import OgeSdamGIA, SUBJECT_TO_OGE_HOST

_oge_client: OgeSdamGIA | None = None

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


def infer_sdamgia_base_url(
    subject_id: str,
    external_id: str,
    exam_type: str = "ЕГЭ",
    url: str = "",
) -> str:
    base = sdamgia_base_from_url(url)
    if base:
        return base
    pid = external_id[4:] if str(external_id).startswith("oge-") else str(external_id)
    if not subject_id or not pid:
        return ""
    exam_type = normalize_exam_type(exam_type)
    if exam_is_oge(exam_type):
        host = SUBJECT_TO_OGE_HOST.get(subject_id)
    else:
        code = SUBJECT_TO_SDAMGIA.get(subject_id)
        host = f"{code}-ege" if code else None
    return f"https://{host}.sdamgia.ru" if host else ""


def _prepare_problem_row(row: dict, subject_id: str, exam_type: str) -> dict:
    prepared = dict(row)
    external_id = str(prepared.get("external_id") or "")
    base = infer_sdamgia_base_url(
        subject_id,
        external_id,
        exam_type=exam_type,
        url=str(prepared.get("url") or ""),
    )
    if base:
        if prepared.get("condition"):
            prepared["condition"] = resolve_sdamgia_image_urls(
                str(prepared["condition"]), base
            )
        if prepared.get("solution"):
            prepared["solution"] = resolve_sdamgia_image_urls(
                str(prepared["solution"]), base
            )
        if not prepared.get("url"):
            pid = external_id[4:] if external_id.startswith("oge-") else external_id
            prepared["url"] = f"{base}/problem?id={pid}"
    return prepared


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
    """Strip HTML but preserve images and math formulas."""
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
    # Preserve img tags and math formulas (latex, mathml)
    # First, temporarily replace img tags and math content with placeholders
    img_placeholders = []
    def replace_img(match):
        img_placeholders.append(match.group(0))
        return f"__IMG_{len(img_placeholders)-1}__"
    
    math_placeholders = []
    def replace_math(match):
        math_placeholders.append(match.group(0))
        return f"__MATH_{len(math_placeholders)-1}__"
    
    # Replace img tags
    text = re.sub(r'<img[^>]*>', replace_img, text, flags=re.IGNORECASE)
    # Replace math formulas (both $...$ and \[...\] and <math>...</math>)
    text = re.sub(r'\$[^$]+\$', replace_math, text)
    text = re.sub(r'\\\[[^\]]+\\\]', replace_math, text)
    text = re.sub(r'<math[^>]*>.*?</math>', replace_math, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    
    # Restore img tags and math formulas
    for i, img in enumerate(img_placeholders):
        text = text.replace(f"__IMG_{i}__", img)
    for i, math in enumerate(math_placeholders):
        text = text.replace(f"__MATH_{i}__", math)
    
    return text.strip()


def _normalize_problem_row(
    subject_id: str, row: dict, exam_type: str = "ЕГЭ"
) -> dict:
    external_id = str(row.get("external_id") or row.get("id") or "")
    if exam_is_oge(exam_type) and external_id and not external_id.startswith("oge-"):
        external_id = f"oge-{external_id}"

    condition_raw = row.get("conditionHtml") or row.get("condition")
    solution_raw = row.get("solutionHtml") or row.get("solution")
    base_url = sdamgia_base_from_url(str(row.get("url") or ""))
    condition_html = rich_content_to_html(condition_raw, base_url=base_url)
    solution_html = rich_content_to_html(solution_raw, base_url=base_url)

    return {
        "subject_id": subject_id,
        "external_id": external_id,
        "topic": str(row.get("topic") or "Общая тема").strip(),
        "condition": condition_html,
        "solution": solution_html,
        "answer": plain_text_from_content(row.get("answer")) or _strip_html(row.get("answer")),
        "url": str(row.get("url") or "").strip(),
    }


def _get_oge_client() -> OgeSdamGIA:
    global _oge_client
    if _oge_client is None:
        _oge_client = OgeSdamGIA()
    return _oge_client


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
    client: Any,
    api_subject: str,
    subject_id: str,
    candidates: list[tuple[float, str, str, Any]],
    needed: int,
    *,
    use_oge: bool = False,
    exam_type: str = "ЕГЭ",
) -> list[dict]:
    collected: list[dict] = []
    seen_ids: set[str] = set()

    for _score, topic_name, category_name, category_id in candidates:
        if len(collected) >= needed:
            break

        try:
            if use_oge:
                problem_ids = client.get_category_by_id(subject_id, category_id) or []
            else:
                problem_ids = client.get_category_by_id(api_subject, category_id) or []
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
                if use_oge:
                    problem_data = client.get_problem_by_id(subject_id, problem_id)
                else:
                    problem_data = client.get_problem_by_id(api_subject, problem_id)
            except Exception:
                continue

            if not problem_data:
                continue

            condition_raw = problem_data.get("conditionHtml") or problem_data.get("condition")
            base_url = sdamgia_base_from_url(str(problem_data.get("url") or ""))
            condition_html = rich_content_to_html(condition_raw, base_url=base_url)
            condition_plain = plain_text_from_content(condition_raw)
            if len(condition_plain) < 10 and "<img" not in condition_html.lower():
                continue

            seen_ids.add(problem_key)
            collected.append(
                _normalize_problem_row(
                    subject_id,
                    {
                        "external_id": problem_key,
                        "topic": category_name,
                        "condition": condition_raw,
                        "conditionHtml": condition_html,
                        "solution": problem_data.get("solutionHtml") or problem_data.get("solution"),
                        "solutionHtml": problem_data.get("solutionHtml"),
                        "answer": problem_data.get("answer"),
                        "url": problem_data.get("url", ""),
                    },
                    exam_type="ОГЭ" if use_oge else "ЕГЭ",
                )
            )
            time.sleep(0.04)

        time.sleep(0.2)

    return collected


def _fetch_from_sdamgia(
    subject_id: str,
    needed: int,
    topic_filter: str | None = None,
    exam_type: str = "ЕГЭ",
) -> list[dict]:
    exam_type = normalize_exam_type(exam_type)

    if exam_is_oge(exam_type):
        if subject_id not in SUBJECT_TO_OGE_HOST:
            raise ProblemBankError(
                f"Предмет «{subject_id}» недоступен для ОГЭ. "
                f"Доступны: {', '.join(SUBJECT_TO_OGE_HOST.keys())}"
            )
        client = _get_oge_client()
        catalog = client.get_catalog(subject_id)
        bank_label = "банка заданий ОГЭ"
    else:
        client = _get_sdamgia_client()
        api_subject = SUBJECT_TO_SDAMGIA.get(subject_id)
        if not api_subject:
            raise ProblemBankError(
                f"Предмет «{subject_id}» не сопоставлен с кодом sdamgia. "
                f"Доступны: {', '.join(SUBJECT_TO_SDAMGIA.keys())}"
            )
        catalog = client.get_catalog(api_subject)
        bank_label = "банка заданий"

    if not catalog:
        raise ProblemBankError(
            f"Не удалось получить каталог заданий по предмету «{subject_id}» ({bank_label})."
        )

    random.shuffle(catalog)
    candidates = _collect_category_candidates(catalog, topic_filter)
    if topic_filter and not candidates:
        raise ProblemBankError(
            f"Не найдено тем, похожих на «{topic_filter}», по предмету «{subject_id}»."
        )

    return _fetch_problems_from_categories(
        client,
        subject_id if exam_is_oge(exam_type) else SUBJECT_TO_SDAMGIA[subject_id],
        subject_id,
        candidates,
        needed,
        use_oge=exam_is_oge(exam_type),
        exam_type=exam_type,
    )


def ensure_problem_bank(subject_id: str, min_count: int = 8, exam_type: str = "ЕГЭ") -> None:
    init_problem_bank_table()
    if count_problem_bank(subject_id) >= min_count:
        return

    fetched = _fetch_from_sdamgia(subject_id, min_count, exam_type=exam_type)
    if not fetched:
        raise ProblemBankError(
            f"Не удалось загрузить задания для предмета «{subject_id}»"
        )
    insert_problem_bank_batch(fetched)


def get_problems_for_test(
    subject_id: str,
    count: int,
    topic_filter: str | None = None,
    exam_type: str = "ЕГЭ",
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
            condition_plain = plain_text_from_content(condition)
            if len(condition_plain) < 10 and "<img" not in condition.lower():
                continue
            seen.add(eid)
            collected.append(_prepare_problem_row(row, subject_id, exam_type))

    live = _fetch_from_sdamgia(
        subject_id, fetch_batch, topic_filter=topic_filter, exam_type=exam_type
    )
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
            exam_type=exam_type,
        )
        if extra:
            insert_problem_bank_batch(extra)
            add_rows(extra)

    if len(collected) < count:
        if topic_filter:
            raise ProblemBankError(
                f"По теме «{topic_filter}» и похожим разделам найдено только {len(collected)} из {count} "
                f"заданий. Попробуйте меньше вопросов или другую тему."
            )
        raise ProblemBankError(
            f"Получено только {len(collected)} из {count} заданий "
            f"по предмету «{subject_id}». Проверьте интернет."
        )

    return collected[:count]


def get_random_problems(
    subject_id: str,
    count: int,
    topic_filter: str | None = None,
    exam_type: str = "ЕГЭ",
) -> list[dict]:
    return get_problems_for_test(
        subject_id, count, topic_filter=topic_filter, exam_type=exam_type
    )
