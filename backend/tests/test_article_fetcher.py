import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.article_fetcher import fetch_article_text


@pytest.mark.asyncio
async def test_fetch_article_text_returns_text_on_success():
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>A man was stabbed in Sofia.</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("services.article_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("services.article_fetcher.trafilatura.extract", return_value="A man was stabbed in Sofia."):
            result = await fetch_article_text("https://example.bg/article/1")

    assert result == "A man was stabbed in Sofia."


@pytest.mark.asyncio
async def test_fetch_article_text_returns_none_on_http_error():
    import httpx
    with patch("services.article_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("timeout"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_article_text("https://example.bg/article/1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_article_text_returns_none_when_trafilatura_extracts_nothing():
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("services.article_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("services.article_fetcher.trafilatura.extract", return_value=None):
            result = await fetch_article_text("https://example.bg/article/1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_article_text_returns_none_on_http_status_error():
    import httpx
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
    )

    with patch("services.article_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_article_text("https://example.bg/article/404")

    assert result is None
