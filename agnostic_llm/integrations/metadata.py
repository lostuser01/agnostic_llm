"""Non-secret metadata describing OAuth and provider connections."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse


def _validate_url(value: str | None, field_name: str) -> None:
    if value is not None and urlparse(value).scheme not in {"http", "https"}:
        raise ValueError(f"{field_name} must be an HTTP(S) URL")


@dataclass(frozen=True)
class OAuthMetadata:
    authorization_url: str
    token_url: str
    scopes: tuple[str, ...] = ()
    client_id: str | None = None
    redirect_uri: str | None = None
    pkce: bool = True

    def __post_init__(self):
        _validate_url(self.authorization_url, "authorization_url")
        _validate_url(self.token_url, "token_url")
        _validate_url(self.redirect_uri, "redirect_uri")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"scopes": list(self.scopes)}


@dataclass(frozen=True)
class ConnectionMetadata:
    provider: str
    credential_ref: str
    auth_type: str = "api_key"
    oauth: OAuthMetadata | None = None
    account_id: str | None = None
    status: str = "configured"
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.provider.strip() or not self.credential_ref.strip():
            raise ValueError("provider and credential_ref are required")
        if self.auth_type == "oauth" and self.oauth is None:
            raise ValueError("OAuth connections require oauth metadata")

    def to_dict(self) -> dict[str, Any]:
        """Return safe config metadata; credential values are never represented."""
        data = asdict(self)
        data["oauth"] = self.oauth.to_dict() if self.oauth else None
        return data
