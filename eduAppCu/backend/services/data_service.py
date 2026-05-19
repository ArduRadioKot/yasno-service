import copy
import json
import re
import time
from pathlib import Path

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

    def get_plan(self, subject_id: str):
        plan = self.plans.get(subject_id)
        if not plan:
            return None
        subject = self.get_subject(subject_id)
        progress = self.user["progressBySubject"].get(subject_id, {})
        return {
            "subject": subject,
            "targetScore": subject["targetScore"] if subject else 0,
            "daysToExam": subject["daysToExam"] if subject else 0,
            "currentScore": progress.get("score", 0),
            **plan,
        }

    def get_plan_topics(self, subject_id: str):
        plan = self.plans.get(subject_id, {})
        topics = []
        for section in plan.get("sections", []):
            for item in section.get("items", []):
                topics.append(item["name"])
        return topics

    def update_plan_from_gaps(self, subject_id: str, gaps: list[str], analysis: str = ""):
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
            return self.get_plan(subject_id)

        section = next(
            (
                s
                for s in plan.get("sections", [])
                if s.get("category") == "AI-рекомендации после теста"
            ),
            None,
        )
        if not section:
            section = {
                "category": "AI-рекомендации после теста",
                "priority": "high",
                "items": [],
            }
            plan.setdefault("sections", []).insert(0, section)

        existing = {item["name"].casefold(): item for item in section["items"]}
        for index, name in enumerate(cleaned[:6]):
            key = name.casefold()
            if key in existing:
                existing[key]["progress"] = min(existing[key].get("progress", 30), 35)
                existing[key]["status"] = "in-progress"
                continue

            slug = re.sub(r"[^a-zа-я0-9]+", "-", key, flags=re.IGNORECASE).strip("-")
            section["items"].append(
                {
                    "id": f"ai-{slug or index}",
                    "name": name,
                    "progress": 25,
                    "status": "in-progress",
                    "impact": "+3 балла",
                }
            )

        if analysis:
            plan["forecast"] = analysis
        plan["weeklyGoal"] = (
            "Разбери темы из AI-рекомендаций и реши по 3-5 заданий на каждую."
        )
        plan["weeklyTasksTotal"] = max(plan.get("weeklyTasksTotal", 0), len(cleaned))
        return self.get_plan(subject_id)

    def get_dashboard(self, subject_id: str):
        subject = self.get_subject(subject_id)
        if not subject:
            return None
        progress = self.user["progressBySubject"].get(subject_id, {})
        plan = self.plans.get(subject_id, {})
        weak = []
        for section in plan.get("sections", []):
            if section["priority"] in ("high", "medium"):
                for item in section["items"]:
                    if item["status"] != "completed":
                        weak.append(
                            {
                                "topic": item["name"],
                                "progress": item["progress"],
                                "color": subject["color"],
                            }
                        )
        weak = sorted(weak, key=lambda x: x["progress"])[:3]
        tasks = self.get_tasks(subject_id)
        completed = len(
            [t for t in tasks if t["id"] in self.user["completedTaskIds"]]
        )
        pending_topics = sum(
            1
            for s in plan.get("sections", [])
            for i in s.get("items", [])
            if i["status"] != "completed"
        )
        top_weak = weak[0]["topic"] if weak else "слабым темам"
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
            "recommendation": (
                f"Сегодня стоит уделить внимание теме «{top_weak}» — "
                f"ты близок к прорыву! Решение 5–7 задач поможет закрепить материал."
            ),
            "dailyPlanRemaining": pending_topics,
            "tasksTotal": len(tasks),
            "tasksCompleted": completed,
        }

    def chat_reply(self, message: str, subject_id: str):
        msg = message.lower()
        subject = self.get_subject(subject_id)
        name = subject["name"] if subject else "предмет"
        topics = self.get_plan_topics(subject_id)[:5]
        topic_hint = ", ".join(topics) if topics else "ключевые темы предмета"

        if any(w in msg for w in ("линз", "оптик", "свет")):
            return (
                f"По {name}: линзы — прозрачные тела, собирающие или рассеивающие свет.\n\n"
                "**Собирающая линза** — толще в центре, фокус реальный.\n"
                "**Рассеивающая** — тоньше в центре.\n\n"
                "Формула: 1/F = 1/d + 1/f\n\n"
                "Хочешь мини-тест по этой теме?"
            )
        if any(w in msg for w in ("производн", "дифференц")):
            return (
                f"Производная в {name}: (xⁿ)' = n·xⁿ⁻¹. "
                "Проверь знак и степень после дифференцирования. "
                "Могу подобрать 3 задачи для тренировки."
            )
        if any(w in msg for w in ("дат", "год", "век", "истор")):
            return (
                "Для истории составь таблицу: событие — дата — последствия. "
                "Повтори 1861, 1914, 1917 — они часто встречаются на ЕГЭ."
            )
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
