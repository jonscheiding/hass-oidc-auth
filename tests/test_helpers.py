"""Tests for the helpers and validation tools"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from aiohttp.test_utils import make_mocked_request
from aiohttp import web

from custom_components.auth_oidc.tools.helpers import (
    STATE_COOKIE_NAME,
    error_response,
    get_icon_url,
    get_state_id,
    get_url,
    get_valid_state_id,
    get_view,
    html_response,
    set_icon_url,
    template_response,
)
from custom_components.auth_oidc.tools.validation import (
    validate_client_id,
    sanitize_client_secret,
    validate_discovery_url,
    validate_icon_url,
    validate_url,
)

from custom_components.auth_oidc.config.const import DEFAULT_ICON_URL, REPO_ROOT_URL


@pytest.mark.asyncio
async def test_get_url():
    """Test the get_url helper."""

    with pytest.raises(RuntimeError) as excinfo:
        get_url("https://example.com", "/test")
    assert str(excinfo.value) == "No current request in context"

    # Mock homeassistant.components.http.current_request.get() to test the force HTTP flag
    with patch("homeassistant.components.http.current_request") as mock_current_request:
        fake_request = make_mocked_request("GET", "http://example.com")
        mock_current_request.get.return_value = fake_request
        result = get_url("/test", True)
        assert result == "https://example.com/test"


@pytest.mark.asyncio
async def test_get_view():
    """Test the get_view helper."""

    data = await get_view("welcome")
    assert data.startswith("<!DOCTYPE html>")


@pytest.mark.asyncio
async def test_get_state_id():
    """State cookie helper should return cookie value when present."""
    request = make_mocked_request(
        "GET", "/", headers={"Cookie": f"{STATE_COOKIE_NAME}=abc"}
    )
    assert get_state_id(request) == "abc"

    request_without_cookie = make_mocked_request("GET", "/")
    assert get_state_id(request_without_cookie) is None


@pytest.mark.asyncio
async def test_get_valid_state_id():
    """Valid-state helper should return only existing and valid cookie states."""
    provider = MagicMock()
    provider.async_is_state_valid = AsyncMock(return_value=True)

    request = make_mocked_request(
        "GET", "/", headers={"Cookie": f"{STATE_COOKIE_NAME}=state-1"}
    )
    state_id = await get_valid_state_id(request, provider)

    assert state_id == "state-1"
    provider.async_is_state_valid.assert_awaited_once_with("state-1")


@pytest.mark.asyncio
async def test_get_valid_state_id_invalid_or_missing_cookie():
    """Valid-state helper should reject missing and invalid states."""
    provider = MagicMock()
    provider.async_is_state_valid = AsyncMock(return_value=False)

    request = make_mocked_request(
        "GET", "/", headers={"Cookie": f"{STATE_COOKIE_NAME}=state-2"}
    )
    assert await get_valid_state_id(request, provider) is None
    provider.async_is_state_valid.assert_awaited_once_with("state-2")

    request_without_cookie = make_mocked_request("GET", "/")
    provider.async_is_state_valid.reset_mock()
    assert await get_valid_state_id(request_without_cookie, provider) is None
    provider.async_is_state_valid.assert_not_called()


@pytest.mark.asyncio
async def test_html_response_and_template_helpers():
    """Response helpers should preserve status and render HTML views."""
    response = html_response("<p>ok</p>", status=418)
    assert isinstance(response, web.Response)
    assert response.status == 418
    assert response.content_type == "text/html"
    assert response.text == "<p>ok</p>"

    with patch(
        "custom_components.auth_oidc.tools.helpers.get_view",
        new=AsyncMock(return_value="<p>rendered</p>"),
    ) as mocked_get_view:
        rendered = await template_response("welcome", {"name": "OIDC"})

    assert rendered.status == 200
    assert rendered.text == "<p>rendered</p>"
    mocked_get_view.assert_awaited_once_with(
        "welcome", {"name": "OIDC", "help_url": REPO_ROOT_URL}
    )


@pytest.mark.asyncio
async def test_error_response():
    """Error response helper should render the shared error template with status."""
    with patch(
        "custom_components.auth_oidc.tools.helpers.get_view",
        new=AsyncMock(return_value="<p>error</p>"),
    ) as mocked_get_view:
        rendered = await error_response("boom", status=500)

    assert rendered.status == 500
    assert rendered.text == "<p>error</p>"
    mocked_get_view.assert_awaited_once_with(
        "error", {"error": "boom", "help_url": REPO_ROOT_URL}
    )


@pytest.mark.asyncio
async def test_validate_url():
    """Test the validate_url helper."""

    assert not validate_url("ftp://example.com")
    assert validate_url("http://example.com")
    assert validate_url("https://example.com")
    assert not validate_url("example.com")
    assert not validate_url(42)
    assert not validate_url([])


@pytest.mark.asyncio
async def test_validate_discovery_url():
    """Test the validate_discovery_url helper."""

    assert not validate_discovery_url("ftp://example.com")
    assert not validate_discovery_url("http://example.com")
    assert not validate_discovery_url("https://example.com")
    assert not validate_discovery_url("example.com")
    assert not validate_discovery_url(
        "https://example.com/.well-known/openid_configuration"
    )
    assert validate_discovery_url(
        "https://example.com/.well-known/openid-configuration"
    )
    assert not validate_discovery_url(2)
    assert not validate_discovery_url([])


@pytest.mark.asyncio
async def test_client_secret():
    """Test the sanitize_client_secret helper."""

    assert sanitize_client_secret("test ") == "test"
    assert sanitize_client_secret("test2") == "test2"


@pytest.mark.asyncio
async def test_client_id():
    """Test the validate_client_id helper."""

    assert not validate_client_id(" ")
    assert validate_client_id("test4")
    assert validate_client_id("test4 ")


@pytest.mark.asyncio
async def test_views_show_the_configured_icon():
    """Every view should show the configured icon, or the default one."""
    try:
        assert get_icon_url() == DEFAULT_ICON_URL
        assert f'src="{DEFAULT_ICON_URL}"' in await get_view("welcome")

        set_icon_url("  https://example.com/icon.png  ")
        assert get_icon_url() == "https://example.com/icon.png"
        for template in ("welcome", "finish", "error"):
            assert 'src="https://example.com/icon.png"' in await get_view(template)

        # An empty configuration value falls back to the bundled icon
        set_icon_url("")
        assert get_icon_url() == DEFAULT_ICON_URL
    finally:
        set_icon_url(None)


@pytest.mark.asyncio
async def test_views_escape_the_configured_icon():
    """The icon URL comes from the configuration, so it is escaped as any value."""
    try:
        set_icon_url('/local/icon.png" onerror="alert(1)')
        rendered = await get_view("welcome")
        assert 'onerror="alert(1)' not in rendered
        assert "&#34; onerror=&#34;alert(1)" in rendered
    finally:
        set_icon_url(None)


def test_validate_icon_url():
    """Only http(s) URLs and paths on this instance are valid icons."""
    assert validate_icon_url("https://example.com/icon.png")
    assert validate_icon_url("http://example.com/icon.png")
    assert validate_icon_url("/local/icon.png?v=2")
    assert validate_icon_url("  /local/icon.png  ")

    assert not validate_icon_url("")
    assert not validate_icon_url("   ")
    assert not validate_icon_url("//example.com/icon.png")
    assert not validate_icon_url("javascript:alert(1)")
    assert not validate_icon_url("data:image/png;base64,AAAA")
    assert not validate_icon_url("local/icon.png")
    assert not validate_icon_url(None)
