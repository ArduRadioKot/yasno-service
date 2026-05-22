import copy
import json
import re
import time
from pathlib import Path

TEST_TOPICS_CATEGORY = "Темы после тестов"
LEGACY_TOPIC_CATEGORIES = {
    "Критические темы",
    "AI-рекомендации после теста",
    "Критические темы и AI-рекомендации",
    TEST_TOPICS_CATEGORY,
}
IN_PROGRESS_CATEGORY = "В процессе"
COMPLETED_CATEGORY = "Освоенные темы"
PRIORITY_SECTION_CATEGORY = "Требуют внимания"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class DataService:
    def __init__(self):
        self.subjects = _load_json("subjects.json")
        self.tasks = _load_json("tasks.json")
        self.plans = _load_json("plans.json")
        self.user = copy.deepcopy(_load_json("user_defaults.json"))

    def get_subjects(self):
        return self.subjects

    def get_subject(self, subject_id: str):
        return next((s for s in self.subjects if s["id"] == subject_id), None)

    def set_active_subject(self, subject_id: str):
        if not self.get_subject(subject_id):
            return None
        self.user["activeSubjectId"] = subject_id
        return self.get_subject(subject_id)

    def get_active_subject_id(self):
        return self.user["activeSubjectId"]

    def get_tasks(self, subject_id: str | None = None, topic: str | None = None):
        items = self.tasks
        if subject_id:
            items = [t for t in items if t["subjectId"] == subject_id]
        if topic:
            items = [t for t in items if topic.lower() in t["topic"].lower()]
        return items

    def get_task(self, task_id: str):
        return next((t for t in self.tasks if t["id"] == task_id), None)

    def add_generated_task(self, subject_id: str, task: dict):
        generated = copy.deepcopy(task)
        generated["id"] = f"ai-{subject_id}-{int(time.time() * 1000)}"
        generated["subjectId"] = subject_id
        self.tasks.insert(0, generated)
        return generated

    def task_for_client(self, task: dict, index: int, total: int):
        return {
            "id": task["id"],
            "subjectId": task["subjectId"],
            "topic": task["topic"],
            "difficulty": task["difficulty"],
            "question": task["question"],
            "given": task.get("given", []),
            "answers": [{"id": a["id"], "text": a["text"]} for a in task["answers"]],
            "index": index,
            "total": total,
        }

    def check_answer(self, task_id: str, answer_id: int):
        task = self.get_task(task_id)
        if not task:
            return None
        correct = next((a for a in task["answers"] if a["isCorrect"]), None)
        chosen = next((a for a in task["answers"] if a["id"] == answer_id), None)
        if not chosen:
            return None
        is_correct = chosen["isCorrect"]
        if is_correct and task_id not in self.user["completedTaskIds"]:
            self.user["completedTaskIds"].append(task_id)
        return {
            "correct": is_correct,
            "correctAnswerId": correct["id"] if correct else None,
            "explanation": task["explanation"],
        }

    def _apply_topic_override(self, item: dict, overrides: dict) -> dict:
        topic = copy.deepcopy(item)
        override = overrides.get(topic["id"]) or overrides.get(topic["name"].casefold())
        if not override:
            return topic
        if override.get("status"):
            topic["status"] = override["status"]
        if override.get("progress") is not None:
            topic["progress"] = int(override["progress"])
        if topic["status"] == "completed":
            topic["progress"] = max(topic.get("progress", 0), 100)
            topic["impact"] = "✓"
        return topic

    def _collect_test_topic_items(self, plan: dict, stored_topics: list[dict] | None = None) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        def add_item(raw_item: dict) -> None:
            key = raw_item.get("id") or raw_item.get("name", "").casefold()
            if not key or key in seen:
                return
            seen.add(key)
            items.append(copy.deepcopy(raw_item))

        if stored_topics:
            for raw_item in stored_topics:
                add_item(raw_item)

        for section in plan.get("sections", []):
            if section.get("category") in LEGACY_TOPIC_CATEGORIES:
                for raw_item in section.get("items", []):
                    add_item(raw_item)
        return items

    def _build_plan_sections(
        self,
        topic_items: list[dict],
        topic_overrides: dict | None = None,
    ) -> list:
        overrides = topic_overrides or {}
        priority_items: list[dict] = []
        in_progress_items: list[dict] = []
        completed_items: list[dict] = []
        seen_priority: set[str] = set()
        seen_in_progress: set[str] = set()
        seen_completed: set[str] = set()

        for raw_item in topic_items:
            item = self._apply_topic_override(raw_item, overrides)
            key = item["id"]
            status = item.get("status", "pending")
            progress = int(item.get("progress", 0))

            if status == "completed" or progress >= 90:
                if key not in seen_completed:
                    seen_completed.add(key)
                    completed_items.append(item)
                continue

            if status == "in-progress" or progress > 0:
                if key not in seen_in_progress:
                    seen_in_progress.add(key)
                    in_progress_items.append(item)
                continue

            if key not in seen_priority:
                seen_priority.add(key)
                priority_items.append(item)

        sections = []
        if priority_items:
            sections.append(
                {
                    "category": PRIORITY_SECTION_CATEGORY,
                    "priority": "high",
                    "items": priority_items,
                }
            )
        sections.append(
            {
                "category": IN_PROGRESS_CATEGORY,
                "priority": "medium",
                "items": sorted(in_progress_items, key=lambda x: -x.get("progress", 0)),
            }
        )
        sections.append(
            {
                "category": COMPLETED_CATEGORY,
                "priority": "completed",
                "items": sorted(completed_items, key=lambda x: -x.get("progress", 0)),
            }
        )
        return sections

    def get_plan(
        self,
        subject_id: str,
        topic_overrides: dict | None = None,
        stored_topics: list[dict] | None = None,
    ):
        plan = self.plans.get(subject_id)
        if not plan:
            return None
        subject = self.get_subject(subject_id)
        progress = self.user["progressBySubject"].get(subject_id, {})
        plan_copy = copy.deepcopy(plan)
        topic_items = self._collect_test_topic_items(plan_copy, stored_topics)
        plan_copy["sections"] = self._build_plan_sections(topic_items, topic_overrides)
        return {
            "subject": subject,
            "targetScore": subject["targetScore"] if subject else 0,
            "daysToExam": subject["daysToExam"] if subject else 0,
            "currentScore": progress.get("score", 0),
            **plan_copy,
        }

    def update_topic_status(
        self,
        subject_id: str,
        topic_id: str,
        status: str,
        *,
        progress: int | None = None,
    ) -> dict | None:
        plan = self.plans.get(subject_id)
        if not plan:
            return None
        valid_statuses = {"completed", "in-progress", "pending"}
        if status not in valid_statuses:
            raise ValueError("Invalid status")

        for section in plan.get("sections", []):
            for item in section.get("items", []):
                if item["id"] == topic_id:
                    item["status"] = status
                    if progress is not None:
                        item["progress"] = max(0, min(100, int(progress)))
                    elif status == "completed":
                        item["progress"] = 100
                        item["impact"] = "✓"
                    elif status == "in-progress" and item.get("progress", 0) < 10:
                        item["progress"] = max(item.get("progress", 0), 40)
                    return copy.deepcopy(item)
        return None

    def get_plan_topics(
        self,
        subject_id: str,
        topic_overrides: dict | None = None,
        stored_topics: list[dict] | None = None,
    ):
        plan = self.get_plan(
            subject_id,
            topic_overrides=topic_overrides,
            stored_topics=stored_topics,
        )
        if not plan:
            return []
        return [item["name"] for section in plan.get("sections", []) for item in section.get("items", [])]

    def _merge_gaps_into_items(self, items: list[dict], gaps: list[str]) -> list[dict]:
        merged = copy.deepcopy(items)
        existing = {item["name"].casefold(): item for item in merged}
        for index, name in enumerate(gaps[:8]):
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
            merged.append(topic)
            existing[key] = topic
        return merged

    def update_plan_from_gaps(
        self,
        subject_id: str,
        gaps: list[str],
        analysis: str = "",
        *,
        user_id: int | None = None,
        stored_topics: list[dict] | None = None,
    ):
        plan = self.plans.get(subject_id)
        if not plan:
            return None

        cleaned = []
        seen = set()
        for gap in gaps:
            name = str(gap).strip()
            if not name:
                continue
            key = name.casefold()
            if key not in seen:
                cleaned.append(name)
                seen.add(key)

        if not cleaned:
            return self.get_plan(
                subject_id,
                stored_topics=stored_topics,
            )

        if user_id is not None:
            from services.db import merge_plan_topics_from_gaps

            merged_items = merge_plan_topics_from_gaps(user_id, subject_id, cleaned)
        else:
            base_items = self._collect_test_topic_items(plan, stored_topics)
            merged_items = self._merge_gaps_into_items(base_items, cleaned)
            plan["sections"] = [
                {
                    "category": TEST_TOPICS_CATEGORY,
                    "priority": "high",
                    "items": merged_items,
                }
            ]

        if analysis:
            plan["forecast"] = analysis
        plan["weeklyGoal"] = (
            f"Закрепи {len(cleaned)} тем из последнего теста — по 3–5 заданий на каждую."
        )
        plan["weeklyTasksTotal"] = max(len(merged_items), len(cleaned))
        plan["weeklyTasksDone"] = min(
            int(plan.get("weeklyTasksDone", 0)) + 1,
            plan["weeklyTasksTotal"],
        )
        plan["weeklyProgress"] = (
            round(plan["weeklyTasksDone"] / plan["weeklyTasksTotal"] * 100)
            if plan["weeklyTasksTotal"]
            else 0
        )
        return self.get_plan(
            subject_id,
            stored_topics=merged_items if user_id is not None else None,
        )

    def list_plan_topics(
        self,
        subject_id: str,
        topic_overrides: dict | None = None,
        stored_topics: list[dict] | None = None,
    ) -> list:
        plan = self.get_plan(
            subject_id,
            topic_overrides=topic_overrides,
            stored_topics=stored_topics,
        )
        if not plan:
            return []
        topics = []
        for section in plan.get("sections", []):
            for item in section.get("items", []):
                topics.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "progress": item.get("progress", 0),
                        "status": item.get("status", "pending"),
                        "priority": section.get("priority", "medium"),
                        "section": section.get("category", ""),
                    }
                )
        return topics

    def record_test_task_progress(
        self,
        subject_id: str,
        *,
        correct_count: int,
        total_count: int,
        plan_topic_count: int = 0,
    ) -> None:
        by_subject = self.user.setdefault("taskProgressBySubject", {})
        entry = dict(by_subject.get(subject_id, {}))
        entry["correct"] = int(entry.get("correct", 0)) + max(0, correct_count)
        entry["answered"] = int(entry.get("answered", 0)) + max(0, total_count)
        entry["tests"] = int(entry.get("tests", 0)) + 1
        entry["goal"] = max(int(entry.get("goal", 0)), plan_topic_count, 5)
        by_subject[subject_id] = entry

    def _task_progress_metrics(
        self,
        subject_id: str,
        all_topics: list,
        tasks: list,
        done_ids: set[str],
        subject_task_stats: dict | None = None,
    ) -> tuple[int, int]:
        static_done = len([t for t in tasks if t["id"] in done_ids])
        topics_done = len([t for t in all_topics if t.get("status") == "completed"])
        stats = subject_task_stats or {}
        local_stats = (self.user.get("taskProgressBySubject") or {}).get(subject_id, {})
        test_correct = int(stats.get("correct") or local_stats.get("correct") or 0)

        tasks_total = max(
            len(tasks),
            len(all_topics),
            int(stats.get("goal") or local_stats.get("goal") or 0),
            1,
        )
        tasks_completed = min(
            max(static_done, topics_done, test_correct),
            tasks_total,
        )
        return tasks_completed, tasks_total

    def get_dashboard(
        self,
        subject_id: str,
        topic_overrides: dict | None = None,
        stored_topics: list[dict] | None = None,
        completed_task_ids: list[str] | None = None,
        subject_task_stats: dict | None = None,
    ):
        subject = self.get_subject(subject_id)
        if not subject:
            return None
        progress = self.user["progressBySubject"].get(subject_id, {})
        all_topics = self.list_plan_topics(
            subject_id,
            topic_overrides=topic_overrides,
            stored_topics=stored_topics,
        )
        weak = [
            {
                "id": t["id"],
                "topic": t["name"],
                "progress": t["progress"],
                "color": subject["color"],
            }
            for t in all_topics
            if t.get("status") != "completed"
        ]
        weak = sorted(weak, key=lambda x: x["progress"])[:3]
        tasks = self.get_tasks(subject_id)
        done_ids = set(completed_task_ids or self.user["completedTaskIds"])
        tasks_completed, tasks_total = self._task_progress_metrics(
            subject_id,
            all_topics,
            tasks,
            done_ids,
            subject_task_stats=subject_task_stats,
        )
        pending_topics = len([t for t in all_topics if t.get("status") != "completed"])
        top_weak = weak[0]["topic"] if weak else None
        return {
            "userName": self.user["userName"],
            "subject": subject,
            "score": progress.get("score", 0),
            "scoreDelta": progress.get("scoreDelta", 0),
            "chart": [
                {"day": i + 1, "score": v}
                for i, v in enumerate(progress.get("chart", []))
            ],
            "streak": self.user["streak"],
            "achievements": self.user["achievements"],
            "weakTopics": weak,
            "allTopics": all_topics,
            "recommendation": (
                f"Сегодня стоит уделить внимание теме «{top_weak}» — "
                f"ты близок к прорыву! Решение 5–7 задач поможет закрепить материал."
                if top_weak
                else "Пройди AI-тест — после разбора ответов слабые темы появятся в плане и на главной."
            ),
            "dailyPlanRemaining": pending_topics,
            "tasksTotal": tasks_total,
            "tasksCompleted": tasks_completed,
        }

    def chat_reply(self, message: str, subject_id: str):
        msg = message.lower()
        subject = self.get_subject(subject_id)
        name = subject["name"] if subject else "предмет"
        topics = self.get_plan_topics(subject_id)[:5]
        topic_hint = ", ".join(topics) if topics else "темы из вашего плана после тестов"

        if any(w in msg for w in ("тест", "мини")):
            tasks = self.get_tasks(subject_id)[:3]
            titles = ", ".join(t["topic"] for t in tasks)
            if titles:
                return f"Мини-тест по {name}: темы — {titles}. Открой вкладку «Задания»!"
            return (
                f"Для диагностики по {name} нажми «Начать занятие» на главной. "
                f"Я проверю темы: {topic_hint}, а затем добавлю слабые места в план."
            )
        if any(w in msg for w in ("проще", "объясни")):
            return (
                f"Упрощённо по {name}: разбей тему на 3 шага — "
                "определение, формула/правило, пример из жизни. "
                "Напиши, какую именно тему разобрать."
            )
        return (
            f"Отличный вопрос по {name}! "
            f"Могу разобрать одну из тем: {topic_hint}. "
            "Напиши тему или пришли задачу, и я объясню решение по шагам."
        )


data_service = DataService()
