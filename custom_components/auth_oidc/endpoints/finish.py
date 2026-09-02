"""Finish route to allow the user to view their code."""

from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from ..provider import OpenIDAuthProvider
from ..tools.helpers import (
    error_response,
    get_valid_state_id,
    template_response,
    concat_url_query,
)

PATH = "/auth/oidc/finish"


class OIDCFinishView(HomeAssistantView):
    """OIDC Plugin Finish View."""

    requires_auth = False
    url = PATH
    name = "auth:oidc:finish"

    def __init__(
        self,
        oidc_provider: OpenIDAuthProvider,
        disable_device_code_login: bool,
    ) -> None:
        self.oidc_provider = oidc_provider
        self.disable_device_code_login = disable_device_code_login

    def _login_on_this_device(self, redirect_uri: str) -> web.HTTPFound:
        """Return the redirect that continues the login on the current device."""
        # Redirect to this new URL for login, make sure to skip OIDC to prevent loops
        return web.HTTPFound(
            location=concat_url_query(redirect_uri, "skip_oidc_redirect=true")
        )

    async def get(self, request: web.Request) -> web.Response:
        """Show the finish screen to pick between login & device code."""
        # Get cookie to get the state_id
        state_id = await get_valid_state_id(request, self.oidc_provider)
        if not state_id:
            return await error_response("Missing state cookie, please restart login.")

        # Without device code login there is nothing left to pick on this page,
        # so immediately continue the login here, as if the
        # 'Continue on this device' button had been pressed
        if self.disable_device_code_login:
            # Get redirect_uri from the state
            redirect_uri = await self.oidc_provider.async_get_redirect_uri_for_state(
                state_id
            )

            if not redirect_uri:
                return await error_response("Invalid state, please restart login.")

            raise self._login_on_this_device(redirect_uri)

        return await template_response("finish", {})

    async def post(self, request: web.Request) -> web.Response:
        """Receive response."""

        # Get cookie to get the state_id
        state_id = await get_valid_state_id(request, self.oidc_provider)
        if not state_id:
            return await error_response("Missing state cookie, please restart login.")

        # Get redirect_uri from the state
        redirect_uri = await self.oidc_provider.async_get_redirect_uri_for_state(
            state_id
        )

        if not redirect_uri:
            return await error_response("Invalid state, please restart login.")

        # Get the message body
        data = await request.post()
        device_code = data.get("device_code")

        # We are trying sign-in on this browser
        if not device_code:
            raise self._login_on_this_device(redirect_uri)

        # Codes are never approved when device code login is disabled,
        # as no code should have been handed out in the first place
        if self.disable_device_code_login:
            return await error_response(
                "Device code login is disabled, please restart login."
            )

        # Check if we can link this device
        linked = await self.oidc_provider.async_link_state_to_code(
            state_id, device_code
        )

        if not linked:
            return await error_response(
                "Failed to link state to device code, please restart login."
            )

        return await template_response("device_success", {})
