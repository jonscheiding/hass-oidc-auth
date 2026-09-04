"""Websocket commands to allow clients to read their own captured claims."""

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .provider import PROVIDER_TYPE

TYPE_USER_CLAIMS = "auth_oidc/user_claims"


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the websocket commands of this integration."""
    websocket_api.async_register_command(hass, websocket_user_claims)


@websocket_api.websocket_command({vol.Required("type"): TYPE_USER_CLAIMS})
@callback
def websocket_user_claims(
    _hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Return the claims that were captured for the connected user.

    The claims are always taken from the user of this connection, so this
    command does not require admin rights: everyone can read their own claims
    and nobody can read the claims of anyone else.
    """
    # Users that signed in with another auth provider don't have any claims,
    # as the claims are stored on the OIDC credential
    claims = next(
        (
            credential.data.get("claims", {})
            for credential in connection.user.credentials
            if credential.auth_provider_type == PROVIDER_TYPE
        ),
        {},
    )

    connection.send_result(msg["id"], {"claims": claims})
