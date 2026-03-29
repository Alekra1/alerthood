"""DeepSeek AI area safety brief generator.

Takes area metadata (name, score, alerts, recent incidents) and produces
a concise 2-3 sentence safety brief in plain English.
"""

import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise neighbourhood safety analyst speaking directly to the user. "
    "Given structured area data, write a 2-3 sentence safety brief addressed to them personally — "
    "use 'you' and 'your' throughout. "
    "Base everything strictly on the provided data: the risk level, safety score, crime rate, "
    "crime trend over the past 7/30/90 days, any active alerts, and recent incidents. "
    "If crime_trend shows rising or falling counts, mention it. "
    "If there are no alerts or incidents, say so plainly — do not invent generic safety tips or clichés. "
    "Do NOT use bullet points or markdown. Plain sentences only. "
    "Respond ONLY with valid JSON: {\"brief\": \"<your 2-3 sentence text>\"}"
)


def _get_client(api_key: str, base_url: str):
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def generate_area_brief(
    area_name: str,
    safety_score: float,
    risk_level: str,
    active_alerts: list[dict],
    recent_incidents: list[dict],
    crime_count: int = 0,
    crime_rate_per_km2: float = 0.0,
    score_updated_at: str | None = None,
    trends: dict | None = None,
) -> str | None:
    """Generate a short AI safety brief for an area.

    Args:
        area_name: Human-readable area name.
        safety_score: 0-100 safety score (higher = safer).
        risk_level: "LOW RISK", "MEDIUM RISK", or "HIGH RISK".
        active_alerts: List of dicts with keys: title, category, severity.
        recent_incidents: List of dicts with keys: title, category, minutesAgo.
        crime_count: Total crime incidents used to compute the current score.
        crime_rate_per_km2: Crime density for the area.
        score_updated_at: ISO timestamp of when the safety score was last computed.
        trends: Dict with keys incidents_7d, incidents_30d, incidents_90d.

    Returns:
        Plain-text brief string, or None on failure.
    """
    payload = {
        "area": area_name,
        "safety_score": round(safety_score, 1),
        "risk_level": risk_level,
        "crime_count": crime_count,
        "crime_rate_per_km2": round(crime_rate_per_km2, 3),
        "score_updated_at": score_updated_at,
        "crime_trend": trends or {},
        "active_alerts": active_alerts,
        "recent_incidents_48h": recent_incidents,
    }

    from config import get_settings
    settings = get_settings()
    client = _get_client(settings.deepseek_api_key, settings.deepseek_base_url)
    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=200,
        )
        content = response.choices[0].message.content or ""
        data = json.loads(content)
        brief = data.get("brief", "").strip()
        return brief if brief else None
    except Exception as e:
        logger.warning("AI area brief generation failed for %r: %s", area_name, e)
        return None
