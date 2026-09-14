"""Validation and sanitization helpers for config flow inputs."""

from __future__ import annotations

from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Validate that a URL is properly formatted."""
    try:
        parsed = urlparse(url.strip())
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except (ValueError, TypeError, AttributeError):
        return False


def validate_discovery_url(url: str) -> bool:
    """Validate that a URL is properly formatted for OIDC discovery."""
    try:
        parsed = urlparse(url.strip())
        return bool(
            parsed.scheme in ("http", "https")
            and parsed.netloc
            and parsed.path.endswith("/.well-known/openid-configuration")
        )
    except (ValueError, TypeError, AttributeError):
        return False


def sanitize_client_secret(secret: str) -> str:
    """Sanitize client secret input."""
    return secret.strip() if secret else ""


def validate_client_id(client_id: str) -> bool:
    """Validate client ID format."""
    return bool(client_id and client_id.strip())


def validate_icon_url(url: str) -> bool:
    """Validate that an icon URL is usable as the source of an image.

    Both an absolute http(s) URL and a path on this Home Assistant instance
    (such as `/local/icon.png` for a file in the `www` folder) are accepted.
    Anything else, such as a `data:` or `javascript:` URL, is rejected, as is a
    protocol relative URL, which does not say which host it points to.
    """
    if not isinstance(url, str):
        return False

    value = url.strip()
    if not value or value.startswith("//"):
        return False

    if value.startswith("/"):
        return True

    return validate_url(value)
