"""Tests for ai_extractor.py — Stage 1 and Stage 2 DeepSeek calls."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ai_extractor import extract_event, filter_relevant_titles


def _make_completion(content: str):
    """Build a minimal mock openai ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Stage 1 — filter_relevant_titles
# ---------------------------------------------------------------------------


async def test_filter_relevant_titles_returns_indices():
    """Happy path: DeepSeek returns valid JSON with relevant indices."""
    payload = json.dumps({"relevant": [0, 2]})
    mock_create = AsyncMock(return_value=_make_completion(payload))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await filter_relevant_titles([
            {"index": 0, "title": "Мъж е намушкан с нож в София"},
            {"index": 1, "title": "Борсов говори за икономиката"},
            {"index": 2, "title": "Катастрофа на Цариградско шосе"},
        ])

    assert result == [0, 2]
    mock_create.assert_called_once()


async def test_filter_relevant_titles_returns_empty_on_api_error():
    """API exception → empty list, no raise."""
    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))
        mock_get_client.return_value = mock_client

        result = await filter_relevant_titles([{"index": 0, "title": "Some title"}])

    assert result == []


async def test_filter_relevant_titles_returns_empty_on_empty_input():
    """Empty input short-circuits to [] without calling DeepSeek."""
    with patch("services.ai_extractor._get_client") as mock_get_client:
        result = await filter_relevant_titles([])

    assert result == []
    mock_get_client.assert_not_called()


async def test_filter_relevant_titles_handles_malformed_json():
    """Malformed JSON response → empty list, no raise."""
    mock_create = AsyncMock(return_value=_make_completion("not json at all"))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await filter_relevant_titles([{"index": 0, "title": "Нещо"}])

    assert result == []


# ---------------------------------------------------------------------------
# Stage 2 — extract_event
# ---------------------------------------------------------------------------


async def test_extract_event_returns_dict_on_success():
    """Happy path: DeepSeek returns valid structured JSON."""
    payload = json.dumps({
        "city": "Sofia",
        "location_text": "ул. Витоша 15, Лозенец",
        "threat_type": "crime",
        "severity": "high",
        "title_en": "Man stabbed in Lozenets district",
        "summary_en": "A man was stabbed on Vitosha street near the Lozenets district.",
    })
    mock_create = AsyncMock(return_value=_make_completion(payload))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await extract_event("Мъж е намушкан", "Full article text here...")

    assert result is not None
    assert result["city"] == "Sofia"
    assert result["location_text"] == "ул. Витоша 15, Лозенец"
    assert result["threat_type"] == "crime"
    assert result["severity"] == "high"
    assert result["title_en"] == "Man stabbed in Lozenets district"


async def test_extract_event_returns_none_on_missing_location():
    """Empty location_text → None (cannot geocode)."""
    payload = json.dumps({
        "city": "Sofia",
        "location_text": "",
        "threat_type": "crime",
        "severity": "medium",
        "title_en": "Incident in Sofia",
        "summary_en": "An incident occurred somewhere.",
    })
    mock_create = AsyncMock(return_value=_make_completion(payload))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await extract_event("Инцидент в София", "Article text...")

    assert result is None


async def test_extract_event_returns_none_on_api_error():
    """API exception → None, no raise."""
    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("timeout"))
        mock_get_client.return_value = mock_client

        result = await extract_event("Some title", "Some text")

    assert result is None


async def test_extract_event_normalises_invalid_threat_type():
    """Invalid threat_type is normalised to 'crime'."""
    payload = json.dumps({
        "city": "Plovdiv",
        "location_text": "Главна улица",
        "threat_type": "UNKNOWN_TYPE",
        "severity": "low",
        "title_en": "Something happened",
        "summary_en": "Details here.",
    })
    mock_create = AsyncMock(return_value=_make_completion(payload))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await extract_event("Нещо се случи", "Текст...")

    assert result is not None
    assert result["threat_type"] == "crime"


async def test_extract_event_normalises_invalid_severity():
    """Invalid severity is normalised to 'medium'."""
    payload = json.dumps({
        "city": "Varna",
        "location_text": "Морска градина",
        "threat_type": "disturbance",
        "severity": "EXTREME",
        "title_en": "Disturbance at sea garden",
        "summary_en": "A disturbance was reported.",
    })
    mock_create = AsyncMock(return_value=_make_completion(payload))

    with patch("services.ai_extractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client

        result = await extract_event("Безредици", "Текст...")

    assert result is not None
    assert result["severity"] == "medium"
