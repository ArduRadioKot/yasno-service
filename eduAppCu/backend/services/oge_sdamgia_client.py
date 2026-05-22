"""
Клиент банка заданий ОГЭ на sdamgia.ru (поддомены *-oge.sdamgia.ru).
Структура каталога совпадает с ЕГЭ-версией sdamgia-api.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

# Коды хостов: https://math-oge.sdamgia.ru, https://inf-oge.sdamgia.ru и т.д.
SUBJECT_TO_OGE_HOST = {
    "physics": "phys-oge",
    "math": "math-oge",
    "russian": "rus-oge",
    "history": "hist-oge",
    "chemistry": "chem-oge",
    "informatics": "inf-oge",
    "biology": "bio-oge",
    "geography": "geo-oge",
    "literature": "lit-oge",
    "french": "fr-oge",
    "social": "soc-oge",
}


class OgeSdamGIA:
    def _base_url(self, subject_id: str) -> str:
        host = SUBJECT_TO_OGE_HOST.get(subject_id)
        if not host:
            raise ValueError(
                f"Предмет «{subject_id}» не поддерживается для ОГЭ. "
                f"Доступны: {', '.join(SUBJECT_TO_OGE_HOST.keys())}"
            )
        return f"https://{host}.sdamgia.ru"

    def get_catalog(self, subject_id: str) -> list[dict]:
        page = requests.get(f"{self._base_url(subject_id)}/prob_catalog", timeout=30)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
        catalog = []

        for block in soup.find_all("div", {"class": "cat_category"}):
            try:
                block["data-id"]
            except Exception:
                catalog.append(block)

        result = []
        for topic in catalog[1:]:
            name_el = topic.find("b", {"class": "cat_name"})
            if not name_el:
                continue
            parts = name_el.text.split(". ", 1)
            topic_id = parts[0].strip()
            topic_name = parts[1].strip() if len(parts) > 1 else topic_id
            if topic_id.startswith(" "):
                topic_id = topic_id[2:]
            if topic_id.startswith("Задания "):
                topic_id = topic_id.replace("Задания ", "")

            children = topic.find("div", {"class": "cat_children"})
            categories = []
            if children:
                for child in children.find_all("div", {"class": "cat_category"}):
                    link = child.find("a", {"class": "cat_name"})
                    if not child.get("data-id") or not link:
                        continue
                    categories.append(
                        {
                            "category_id": child["data-id"],
                            "category_name": link.text.strip(),
                        }
                    )

            result.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "categories": categories,
                }
            )
        return result

    def get_category_by_id(self, subject_id: str, category_id: str, page: int = 1) -> list[str]:
        url = (
            f"{self._base_url(subject_id)}/test?&filter=all"
            f"&theme={category_id}&page={page}"
        )
        page_resp = requests.get(url, timeout=30)
        page_resp.raise_for_status()
        soup = BeautifulSoup(page_resp.content, "html.parser")
        ids = []
        for span in soup.find_all("span", {"class": "prob_nums"}):
            parts = span.text.split()
            if parts:
                ids.append(parts[-1].rstrip(".)"))
        return ids

    def _extract_text(self, element) -> str:
        if element is None:
            return ""
        return re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()

    def get_problem_by_id(self, subject_id: str, problem_id: str) -> dict | None:
        base = self._base_url(subject_id)
        resp = requests.get(f"{base}/problem?id={problem_id}", timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        prob_block = soup.find("div", {"class": "prob_maindiv"})
        if not prob_block:
            return None

        bodies = prob_block.find_all("div", {"class": "pbody"})
        condition = self._extract_text(bodies[0]) if bodies else ""
        solution = self._extract_text(bodies[1]) if len(bodies) > 1 else ""

        answer_el = prob_block.find("div", {"class": "answer"})
        answer = self._extract_text(answer_el)
        if not answer and "Ответ:" in prob_block.get_text():
            match = re.search(r"Ответ:\s*([^\n]+)", prob_block.get_text())
            if match:
                answer = match.group(1).strip()

        topic = ""
        nums = prob_block.find("span", {"class": "prob_nums"})
        if nums:
            topic = nums.text.strip()

        return {
            "id": str(problem_id),
            "topic": topic,
            "condition": condition,
            "solution": solution,
            "answer": answer,
            "url": f"{base}/problem?id={problem_id}",
        }
