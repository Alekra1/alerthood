"""DeepSeek AI client for two-stage crime news relevance filtering and extraction.

Stage 1 — Relevance filter:
  Input:  list of {index, title}
  Output: list of relevant indices

Stage 2 — Structured extraction + English translation:
  Input:  article title + full text
  Output: dict with city, location_text, threat_type, severity, title_en, summary_en
          Returns None if location cannot be extracted confidently.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://openrouter.ai/api/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek/deepseek-chat")

_THREAT_TYPES = {"crime", "disturbance", "infrastructure"}
_SEVERITY_LEVELS = {"low", "medium", "high", "critical"}

_STAGE1_SYSTEM = (
    "You are a Bulgarian crime news classifier. "
    "Given a list of article titles, identify which ones describe crime, violence, accidents, "
    "fires, explosions, or other safety incidents that happened in a specific Bulgarian city or location. "
    "Exclude articles about politics, business, sports, or incidents outside Bulgaria. "
    "Respond with JSON: {\"relevant\": [<indices of relevant articles>]}"
)

_STAGE2_SYSTEM = (
    "You are an expert at extracting structured location and incident data from Bulgarian news articles. "
    "Extract the JSON fields below. If you cannot confidently identify a specific street, district, or "
    "named location within Bulgaria, set location_text to an empty string. "
    "Respond ONLY with valid JSON matching this schema exactly:\n"
    "{\n"
    "  \"city\": \"<Bulgarian city name in English, e.g. Sofia>\",\n"
    "  \"location_text\": \"<specific street or district in original language, or empty string>\",\n"
    "  \"threat_type\": \"<one of: crime, disturbance, infrastructure>\",\n"
    "  \"severity\": \"<one of: low, medium, high, critical>\",\n"
    "  \"title_en\": \"<English translation of the article title>\",\n"
    "  \"summary_en\": \"<2-3 sentence English summary of the incident>\"\n"
    "}"
)


def _get_client():
    """Return a lazily-constructed OpenAI-compatible client pointed at DeepSeek."""
    from openai import AsyncOpenAI  # deferred to avoid import cost when unused

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    return AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


async def filter_relevant_titles(items: list[dict]) -> list[int]:
    """Stage 1: filter article titles to those describing crime/safety incidents in Bulgaria.

    Args:
        items: list of {"index": int, "title": str}

    Returns:
        List of indices deemed relevant. Empty list on any failure.
    """
    if not items:
        return []

    client = _get_client()
    prompt = json.dumps(items, ensure_ascii=False)

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _STAGE1_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        data = json.loads(content)
        indices = data.get("relevant", [])
        return [int(i) for i in indices if isinstance(i, (int, float))]
    except Exception as e:
        logger.exception("Stage 1 DeepSeek call failed: %s", e)
        return []


async def extract_event(title: str, text: str) -> dict | None:
    """Stage 2: extract structured event data + English translation from article.

    Args:
        title: Article title (may be in Bulgarian)
        text:  Full article body text (may be in Bulgarian)

    Returns:
        Dict with keys: city, location_text, threat_type, severity, title_en, summary_en.
        Returns None if DeepSeek cannot extract a location or the API call fails.
    """
    client = _get_client()
    user_content = f"Title: {title}\n\nText:\n{text[:4000]}"  # guard against huge articles

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _STAGE2_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        data = json.loads(content)
    except Exception as e:
        logger.exception("Stage 2 DeepSeek call failed for %r: %s", title[:60], e)
        return None

    # Require a non-empty location to be able to geocode
    if not data.get("location_text", "").strip():
        logger.debug("Stage 2 returned no location_text for %r — skipping", title[:60])
        return None

    # Normalise threat_type and severity to valid enum values
    threat_type = data.get("threat_type", "crime")
    if threat_type not in _THREAT_TYPES:
        threat_type = "crime"

    severity = data.get("severity", "medium")
    if severity not in _SEVERITY_LEVELS:
        severity = "medium"

    return {
        "city": data.get("city", ""),
        "location_text": data["location_text"].strip(),
        "threat_type": threat_type,
        "severity": severity,
        "title_en": data.get("title_en", title),
        "summary_en": data.get("summary_en", ""),
    }
