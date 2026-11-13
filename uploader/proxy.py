"""Proxy URL validation.

A typo here silently sends credentials to the wrong endpoint or makes every
request fail, so malformed input is rejected loudly instead of guessed at.
"""

from urllib.parse import urlsplit, urlunsplit

SUPPORTED_SCHEMES = ("http", "https", "socks5", "socks5h")


class ProxyError(Exception):
    """Raised when the proxy URL cannot be used as given."""


def normalize_proxy(raw: str | None) -> str | None:
    """Return a validated proxy URL, or None when no proxy is configured."""
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None

    parts = urlsplit(value)
    if not parts.scheme:
        raise ProxyError("Proxy must include a scheme, e.g. http://host:port")
    if parts.scheme.lower() not in SUPPORTED_SCHEMES:
        raise ProxyError(f"Unsupported proxy scheme: {parts.scheme}")
    if not parts.hostname:
        raise ProxyError("Proxy host is missing")
    try:
        port = parts.port
    except ValueError as exc:
        raise ProxyError(f"Invalid proxy port: {exc}") from None
    if not port:
        raise ProxyError("Proxy port is missing, e.g. http://host:3128")

    if parts.scheme.lower().startswith("socks"):
        try:
            import socks  # noqa: F401
        except ImportError:
            raise ProxyError(
                "SOCKS proxies need the PySocks package: pip install 'requests[socks]'"
            ) from None

    return urlunsplit(
        (parts.scheme.lower(), parts.netloc, parts.path, parts.query, parts.fragment)
    )


def redact_proxy(proxy: str | None) -> str:
    """Render a proxy URL safely for logs and error messages."""
    if not proxy:
        return "none"
    parts = urlsplit(proxy)
    if parts.username or parts.password:
        host = parts.hostname or ""
        try:
            port = f":{parts.port}" if parts.port else ""
        except ValueError:
            port = ""
        netloc = f"***:***@{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return proxy