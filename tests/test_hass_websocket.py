"""Tests for the websocket commands of the OIDC integration"""

import pytest
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.auth.models import Credentials
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.auth_oidc import DOMAIN
from custom_components.auth_oidc.config.const import CLIENT_ID, DISCOVERY_URL
from custom_components.auth_oidc.websocket import TYPE_USER_CLAIMS

TEST_CLIENT_ID = "https://example.com/app"


async def setup(hass: HomeAssistant) -> None:
    """Set up the auth_oidc component."""
    result = await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CLIENT_ID: "dummy",
                DISCOVERY_URL: "https://example.com/.well-known/openid-configuration",
            }
        },
    )
    assert result


async def create_user(
    hass: HomeAssistant,
    credential_data: dict,
    name: str = "Test Name",
    group_ids: list[str] | None = None,
) -> tuple:
    """Create a user with the given OIDC credential and return an access token."""
    provider = hass.auth.get_auth_providers(DOMAIN)[0]
    credential = provider.async_create_credentials(credential_data)

    user = await hass.auth.async_create_user(name, group_ids=group_ids)
    await hass.auth.async_link_user(user, credential)

    refresh_token = await hass.auth.async_create_refresh_token(
        user, TEST_CLIENT_ID, credential=credential
    )
    return user, hass.auth.async_create_access_token(refresh_token)


async def get_claims(client) -> dict:
    """Ask the connected client for the claims of its own user."""
    await client.send_json_auto_id({"type": TYPE_USER_CLAIMS})
    response = await client.receive_json()

    assert response["success"]
    return response["result"]["claims"]


@pytest.mark.asyncio
async def test_user_claims_returns_captured_claims(hass: HomeAssistant, hass_ws_client):
    """Captured claims should be readable by the user they belong to."""
    await setup(hass)

    _, access_token = await create_user(
        hass,
        {
            "sub": "hashed-subject",
            "claims": {"sub": "subject", "email": "user@example.com"},
        },
    )
    client = await hass_ws_client(hass, access_token)

    assert await get_claims(client) == {
        "sub": "subject",
        "email": "user@example.com",
    }


@pytest.mark.asyncio
async def test_user_claims_empty_when_nothing_was_captured(
    hass: HomeAssistant, hass_ws_client
):
    """Users of an installation without configured claims should get nothing."""
    await setup(hass)

    _, access_token = await create_user(hass, {"sub": "hashed-subject"})
    client = await hass_ws_client(hass, access_token)

    assert await get_claims(client) == {}


@pytest.mark.asyncio
async def test_user_claims_empty_for_other_auth_providers(
    hass: HomeAssistant, hass_ws_client
):
    """Users that signed in with another auth provider should get nothing."""
    await setup(hass)

    # Build a user as the default Home Assistant auth provider would
    user = await hass.auth.async_create_user("Local User")
    credential = Credentials(
        auth_provider_type="homeassistant",
        auth_provider_id=None,
        data={"username": "localuser"},
        is_new=False,
    )
    await hass.auth.async_link_user(user, credential)

    refresh_token = await hass.auth.async_create_refresh_token(
        user, TEST_CLIENT_ID, credential=credential
    )
    client = await hass_ws_client(
        hass, hass.auth.async_create_access_token(refresh_token)
    )

    assert await get_claims(client) == {}


@pytest.mark.asyncio
async def test_user_claims_are_available_to_non_admin_users(
    hass: HomeAssistant, hass_ws_client
):
    """Reading your own claims should not require admin rights."""
    await setup(hass)

    user, access_token = await create_user(
        hass,
        {"sub": "hashed-subject", "claims": {"email": "readonly@example.com"}},
        name="Read Only",
        group_ids=[GROUP_ID_READ_ONLY],
    )
    assert not user.is_admin

    client = await hass_ws_client(hass, access_token)

    assert await get_claims(client) == {"email": "readonly@example.com"}


@pytest.mark.asyncio
async def test_user_claims_does_not_return_claims_of_other_users(
    hass: HomeAssistant, hass_ws_client
):
    """The command should be scoped to the user of the connection."""
    await setup(hass)

    await create_user(
        hass,
        {"sub": "other-subject", "claims": {"email": "other@example.com"}},
        name="Other User",
    )
    _, access_token = await create_user(
        hass,
        {"sub": "hashed-subject", "claims": {"email": "user@example.com"}},
    )
    client = await hass_ws_client(hass, access_token)

    assert await get_claims(client) == {"email": "user@example.com"}
