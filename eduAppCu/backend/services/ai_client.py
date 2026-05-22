import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

client = (
    OpenAI(
        base_url="https://api.mistral.ai/v1",
        api_key=MISTRAL_API_KEY,
        timeout=60,
    )
    if MISTRAL_API_KEY
    else None
)


def is_ai_available() -> bool:
    return client is not None


def extract_json(content: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", content or "")
    if not match:
        raise ValueError("AI response does not contain JSON")
    return json.loads(match.group())


def chat_completion(
    messages: list[dict],
    *,
    max_tokens: int = 1200,
    temperature: float = 0.3,
) -> str:
    if not client:
        raise RuntimeError("MISTRAL_API_KEY не задан")
    response = client.chat.completions.create(
        model=MISTRAL_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise ValueError("empty AI response")
    return content.strip()


def chat_json(
    messages: list[dict],
    *,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> dict:
    return extract_json(chat_completion(messages, max_tokens=max_tokens, temperature=temperature))
