"""Constrained outbound HTTP for provider integrations."""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse


class OutboundHTTPError(RuntimeError):
    """Raised when an outbound request violates a safety or resource limit."""


@dataclass(frozen=True)
class OutboundHTTPResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OutboundHTTPError("redirects are not allowed for outbound requests")


def _redact(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, Mapping):
        return {str(k): _redact(v, secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v, secrets) for v in value]
    return value


class ControlledOutboundHTTPClient:
    """HTTP client with allowlisting, SSRF checks, bounded resources, and auditing."""

    def __init__(
        self,
        allowed_domains: set[str] | tuple[str, ...],
        *,
        timeout: float = 10.0,
        max_response_bytes: int = 2 * 1024 * 1024,
        audit_hook: Callable[[dict[str, Any]], None] | None = None,
        secret_values: tuple[str, ...] = (),
    ):
        if timeout <= 0 or max_response_bytes <= 0:
            raise ValueError("timeout and max_response_bytes must be positive")
        self.allowed_domains = {d.lower().lstrip(".") for d in allowed_domains}
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.audit_hook = audit_hook
        self.secret_values = tuple(secret_values)
        self._opener = urllib.request.build_opener(_NoRedirect)

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in {"http", "https"} or not host:
            raise OutboundHTTPError("only HTTP(S) URLs with a hostname are allowed")
        if parsed.username or parsed.password:
            raise OutboundHTTPError("URLs containing credentials are not allowed")
        if not any(host == domain or host.endswith("." + domain) for domain in self.allowed_domains):
            raise OutboundHTTPError("destination domain is not allowlisted")
        try:
            addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise OutboundHTTPError("destination DNS lookup failed") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                raise OutboundHTTPError("destination resolves to a private or local address")

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        body: bytes | str | None = None,
    ) -> OutboundHTTPResponse:
        payload = body.encode() if isinstance(body, str) else body
        safe_headers = dict(headers or {})
        event = {
            "action": "outbound_http",
            "method": method.upper(),
            "url": url,
            "headers": _redact(safe_headers, self.secret_values),
            "body_bytes": len(payload or b""),
        }
        try:
            self._check_url(url)
            request = urllib.request.Request(url, data=payload, headers=safe_headers, method=method.upper())
            with self._opener.open(request, timeout=self.timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > self.max_response_bytes:
                    raise OutboundHTTPError("response exceeds configured size limit")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(min(64 * 1024, self.max_response_bytes - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_response_bytes:
                        raise OutboundHTTPError("response exceeds configured size limit")
                    chunks.append(chunk)
                result = OutboundHTTPResponse(response.status, dict(response.headers.items()), b"".join(chunks))
            event["status"] = result.status
            event["response_bytes"] = len(result.body)
            return result
        except urllib.error.HTTPError as exc:
            event["status"] = exc.code
            raise OutboundHTTPError(f"HTTP request failed with status {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OutboundHTTPError("outbound HTTP request failed") from exc
        finally:
            if self.audit_hook:
                self.audit_hook(_redact(event, self.secret_values))

    def get(self, url: str, **kwargs: Any) -> OutboundHTTPResponse:
        return self.request("GET", url, **kwargs)

    def post_json(self, url: str, value: Any, **kwargs: Any) -> OutboundHTTPResponse:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Content-Type", "application/json")
        return self.request("POST", url, headers=headers, body=json.dumps(value), **kwargs)
