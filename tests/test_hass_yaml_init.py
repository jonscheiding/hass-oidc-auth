"""Tests for the YAML config setup of OIDC"""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.auth_oidc import DOMAIN
from custom_components.auth_oidc.config.const import (
    ADDITIONAL_SCOPES,
    DEFAULT_ICON_URL,
    ICON_URL,
)
from custom_components.auth_oidc.tools.helpers import get_icon_url, set_icon_url


async def setup(hass: HomeAssistant, config: dict, expect_success: bool) -> bool:
    """Set up the auth_oidc component."""
    result = await async_setup_component(hass, DOMAIN, {DOMAIN: config})

    if expect_success:
        assert result
        assert DOMAIN in hass.data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config",
    [
        {
            "client_id": "dummy",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
        },
        {
            "client_id": "dummy",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
            ADDITIONAL_SCOPES: "email phone",
        },
        {
            "client_id": "dummy",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
            ICON_URL: "https://example.com/icon.png",
        },
        {
            "client_id": "dummy",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
            ICON_URL: "/local/icon.png",
        },
    ],
)
async def test_setup_success_yaml(hass: HomeAssistant, config: dict):
    """YAML setup should succeed for minimal and optional-scope configurations."""
    await setup(
        hass,
        config,
        True,
    )


@pytest.mark.asyncio
async def test_setup_failure_empty_yaml(hass: HomeAssistant, caplog):
    """Test failure setup of an empty YAML configuration."""
    await setup(hass, {}, False)

    assert "required key 'client_id' not provided" in caplog.text
    assert "required key 'discovery_url' not provided" in caplog.text
    assert (
        "Setup failed for custom integration 'auth_oidc': Invalid config."
        in caplog.text
    )


@pytest.mark.asyncio
async def test_setup_failure_partial_empty_yaml_discovery(hass: HomeAssistant, caplog):
    """Test failure setup of an partial YAML configuration."""
    await setup(
        hass,
        {"discovery_url": "https://example.com/.well-known/openid-configuration"},
        False,
    )

    assert "required key 'client_id' not provided" in caplog.text
    assert "required key 'discovery_url' not provided" not in caplog.text
    assert (
        "Setup failed for custom integration 'auth_oidc': Invalid config."
        in caplog.text
    )


@pytest.mark.asyncio
async def test_setup_failure_partial_empty_yaml_client(hass: HomeAssistant, caplog):
    """Test failure setup of an partial YAML configuration."""

    await setup(
        hass,
        {"client_id": "test"},
        False,
    )

    assert "required key 'client_id' not provided" not in caplog.text
    assert "required key 'discovery_url' not provided" in caplog.text
    assert (
        "Setup failed for custom integration 'auth_oidc': Invalid config."
        in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "icon_url",
    ["javascript:alert(1)", "data:image/png;base64,AAAA", "//example.com/icon.png", ""],
)
async def test_setup_failure_invalid_icon_url(
    hass: HomeAssistant, caplog, icon_url: str
):
    """Only an http(s) URL or a path on this instance may be used as the icon."""
    await setup(
        hass,
        {
            "client_id": "dummy",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
            ICON_URL: icon_url,
        },
        False,
    )

    assert "icon_url must be an http(s) URL" in caplog.text


@pytest.mark.asyncio
async def test_setup_applies_configured_icon(hass: HomeAssistant):
    """The configured icon should be used on the pages we serve, if set."""
    try:
        await setup(
            hass,
            {
                "client_id": "dummy",
                "discovery_url": (
                    "https://example.com/.well-known/openid-configuration"
                ),
                ICON_URL: "/local/icon.png",
            },
            True,
        )
        assert get_icon_url() == "/local/icon.png"
    finally:
        set_icon_url(None)


@pytest.mark.asyncio
async def test_setup_without_icon_uses_default(hass: HomeAssistant):
    """Without an icon configured, the icon of this integration is used."""
    set_icon_url("/local/leftover.png")
    try:
        await setup(
            hass,
            {
                "client_id": "dummy",
                "discovery_url": (
                    "https://example.com/.well-known/openid-configuration"
                ),
            },
            True,
        )
        assert get_icon_url() == DEFAULT_ICON_URL
    finally:
        set_icon_url(None)
