import os
import json
import re
from html import unescape
from urllib.parse import urljoin, urlsplit, urlunsplit
from openai import OpenAI
from dotenv import load_dotenv
from schemas.article_schema import ArticleList

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _prepare_html_for_extraction(html: str, max_len: int = 80000) -> str:
    # Remove very noisy sections so the model focuses on content-bearing nodes.
    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<!--([\s\S]*?)-->", " ", cleaned)

    if len(cleaned) <= max_len:
        return cleaned

    # Sample chunks across the whole document so middle-page content is preserved.
    chunk_count = 5
    chunk_size = max_len // chunk_count
    total_len = len(cleaned)
    step = (total_len - chunk_size) // (chunk_count - 1)
    parts = []
    for i in range(chunk_count):
        start = max(0, i * step)
        end = min(total_len, start + chunk_size)
        parts.append(cleaned[start:end])
    return "\n...TRUNCATED...\n".join(parts)


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _looks_like_article_link(href: str) -> bool:
    low = href.lower()
    if low.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False
    article_markers = [
        "/news",
        "/article",
        "/articles",
        "/story",
        "/live",
        "/world",
        "/business",
        "/sport",
        "/technology",
    ]
    return any(marker in low for marker in article_markers)


def _extract_anchor_articles(html: str, source_url: str | None, max_items: int = 30) -> list[dict]:
    nav_words = {
        "home", "news", "sport", "business", "technology", "health", "culture", "arts",
        "travel", "earth", "audio", "video", "live", "sign in", "register", "menu",
    }
    anchor_pattern = re.compile(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
        flags=re.IGNORECASE,
    )

    results: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for href, raw_text in anchor_pattern.findall(html):
        text = unescape(_strip_tags(raw_text))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if len(text) < 28 or len(text) > 220:
            continue
        if text.lower() in nav_words:
            continue
        if not _looks_like_article_link(href):
            continue

        absolute = urljoin(source_url, href) if source_url else href
        normalized = _normalize_url(absolute)
        norm_title = text.lower()

        if normalized in seen_urls or norm_title in seen_titles:
            continue

        seen_urls.add(normalized)
        seen_titles.add(norm_title)
        results.append(
            {
                "title": text,
                "articleUrl": absolute,
                "imageUrl": None,
                "excerpt": None,
            }
        )

        if len(results) >= max_items:
            break

    return results


def _merge_articles(primary: list[dict], fallback: list[dict], max_items: int = 20) -> list[dict]:
    merged: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in primary + fallback:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        article_url = item.get("articleUrl") or ""
        norm_url = _normalize_url(article_url) if article_url else ""
        norm_title = title.lower()

        if norm_url and norm_url in seen_urls:
            continue
        if norm_title in seen_titles:
            continue

        if norm_url:
            seen_urls.add(norm_url)
        seen_titles.add(norm_title)
        merged.append(
            {
                "title": title,
                "articleUrl": article_url or None,
                "imageUrl": item.get("imageUrl"),
                "excerpt": item.get("excerpt"),
            }
        )

        if len(merged) >= max_items:
            break

    return merged


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    # Handle fenced or mixed content by grabbing the first JSON object block.
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None

async def process_with_llm(html, instructions, source_url: str | None = None, truncate=False):
    if not html:
        return None

    max_len = 80000
    content_to_send = _prepare_html_for_extraction(html, max_len=max_len) if truncate else html
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    'role': 'system',
                    'content': f"""
                                        You are an expert web extraction agent.

                                        Extract homepage/news article cards from the provided HTML.
                                        Return ONLY valid JSON with this exact shape:
                                        {{
                                            "articles": [
                                                {{
                                                    "title": "...",
                                                    "articleUrl": "https://absolute-url",
                                                    "imageUrl": "https://absolute-url-or-null",
                                                    "excerpt": "short summary or null"
                                                }}
                                            ]
                                        }}

                                        Rules:
                                        - Prefer real story cards, not nav/menu/footer links.
                                        - Resolve relative links to absolute URLs when possible.
                                        - Deduplicate by articleUrl and title.
                                        - Return up to 20 best results.
                                        - If unsure about image/excerpt, use null.
                    
                    Instructions:
                    {instructions}
                    """
                },
                {"role":"user", "content": content_to_send}
            ],
            temperature = 0.1,
            response_format={"type":"json_object"}
        )

        response_content = completion.choices[0].message.content
        json_payload = _extract_json_object(response_content)
        if not json_payload:
                return None

        if "articles" not in json_payload:
            return None

        llm_articles = json_payload.get("articles") or []
        if not isinstance(llm_articles, list):
            llm_articles = []

        fallback_articles = _extract_anchor_articles(content_to_send, source_url=source_url, max_items=40)
        merged_articles = _merge_articles(llm_articles, fallback_articles, max_items=20)

        if not merged_articles:
            return None

        return ArticleList.model_validate({"articles": merged_articles})
    except Exception as e:
        print(f"Error processing with LLM: {e}")
        return None