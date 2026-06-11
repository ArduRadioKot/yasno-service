"""Helpers for sdamgia problem text, HTML and formula images."""

from __future__ import annotations

import re
from html import unescape
from typing import Any


def sdamgia_base_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.match(r"(https?://[^/]+)", str(url).strip())
    return match.group(1) if match else ""


def resolve_sdamgia_image_urls(html: str, base_url: str) -> str:
    """Rewrite relative sdamgia /img/ and /get_file paths to absolute URLs."""
    if not html or not base_url:
        return html
    base = base_url.rstrip("/")

    def repl_src(match: re.Match[str]) -> str:
        quote = match.group(1)
        src = match.group(2).strip()
        if src.startswith(("http://", "https://", "data:")):
            return match.group(0)
        if src.startswith("//"):
            return f"src={quote}https:{src}{quote}"
        if src.startswith("/"):
            return f"src={quote}{base}{src}{quote}"
        return f"src={quote}{base}/{src}{quote}"

    return re.sub(
        r'src=(["\'])([^"\']+)\1',
        repl_src,
        html,
        flags=re.IGNORECASE,
    )


def content_images(value: Any) -> list[str]:
    if isinstance(value, dict):
        raw = value.get("images") or []
        if isinstance(raw, list):
            return [str(url).strip() for url in raw if url]
    return []


def content_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("text", "content", "html"):
            if value.get(key):
                return str(value[key])
        return ""
    if isinstance(value, list):
        return " ".join(content_text(item) for item in value).strip()
    return unescape(str(value))


def _preserve_inline_markup(text: str) -> str:
    """Keep img/math tags while stripping other HTML wrappers."""
    img_placeholders: list[str] = []
    math_placeholders: list[str] = []

    def replace_img(match: re.Match[str]) -> str:
        img_placeholders.append(match.group(0))
        return f"__IMG_{len(img_placeholders) - 1}__"

    def replace_math(match: re.Match[str]) -> str:
        math_placeholders.append(match.group(0))
        return f"__MATH_{len(math_placeholders) - 1}__"

    text = re.sub(r"<img[^>]*>", replace_img, text, flags=re.IGNORECASE)
    text = re.sub(r"\$[^$]+\$", replace_math, text)
    text = re.sub(r"\\\[[^\]]+\\\]", replace_math, text)
    text = re.sub(r"<math[^>]*>.*?</math>", replace_math, text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    for index, img in enumerate(img_placeholders):
        text = text.replace(f"__IMG_{index}__", img)
    for index, math in enumerate(math_placeholders):
        text = text.replace(f"__MATH_{index}__", math)

    return text.strip()


def rich_content_to_html(value: Any, *, base_url: str = "") -> str:
    """Convert sdamgia condition/solution payloads to HTML with formula images."""
    if value is None:
        return ""
    if isinstance(value, dict):
        text = content_text(value)
        images = content_images(value)
        html = _preserve_inline_markup(text) if text else ""
        if images:
            resolved_images = [
                resolve_sdamgia_image_urls(url, base_url) if base_url else url
                for url in images
            ]
            imgs = "".join(
                (
                    f'<img src="{url}" alt="" class="sdamgia-formula" '
                    'loading="lazy" referrerpolicy="no-referrer" />'
                )
                for url in resolved_images
            )
            html = (
                f'<div class="sdamgia-content">{html}</div>'
                f'<div class="sdamgia-images">{imgs}</div>'
                if html
                else f'<div class="sdamgia-images">{imgs}</div>'
            )
        return resolve_sdamgia_image_urls(html.strip(), base_url)
    if isinstance(value, list):
        return " ".join(
            rich_content_to_html(item, base_url=base_url) for item in value
        ).strip()

    text = unescape(str(value))
    if "<" in text:
        return resolve_sdamgia_image_urls(_preserve_inline_markup(text), base_url)
    return text.strip()


def plain_text_from_content(value: Any) -> str:
    html = rich_content_to_html(value)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", unescape(text))
    return text.strip()
