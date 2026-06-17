from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import os
import secrets

try:
    from fastapi import Header, HTTPException
except ImportError as exc:  # pragma: no cover - exercised only in minimal installs.
    raise RuntimeError("FastAPI service requires installing the service extra: pip install -e '.[service]'") from exc


ROLE_LEVELS = {
    "viewer": 1,
    "researcher": 2,
    "operator": 3,
}


@dataclass(frozen=True)
class ApiPrincipal:
    api_key_id: str
    role: str


def parse_api_keys(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    keys: dict[str, str] = {}
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        token, separator, role = entry.partition(":")
        token = token.strip()
        role = role.strip()
        if not token or not separator or role not in ROLE_LEVELS:
            raise ValueError("AIQRA_API_KEYS entries must use key:viewer|researcher|operator")
        keys[token] = role
    return keys


@lru_cache(maxsize=1)
def configured_api_keys() -> dict[str, str]:
    return parse_api_keys(os.getenv("AIQRA_API_KEYS"))


def clear_auth_cache() -> None:
    configured_api_keys.cache_clear()


def require_role(required_role: str):
    if required_role not in ROLE_LEVELS:
        raise ValueError(f"unknown API role requirement: {required_role}")

    def dependency(x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None) -> ApiPrincipal:
        try:
            configured = configured_api_keys()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="API auth is misconfigured") from exc
        if not configured:
            raise HTTPException(status_code=503, detail="API auth is not configured")
        if x_api_key is None:
            raise HTTPException(status_code=401, detail="missing API key")
        role = _lookup_role(x_api_key, configured)
        if role is None:
            raise HTTPException(status_code=401, detail="invalid API key")
        if ROLE_LEVELS[role] < ROLE_LEVELS[required_role]:
            raise HTTPException(status_code=403, detail=f"requires {required_role} role")
        return ApiPrincipal(api_key_id=_key_id(x_api_key), role=role)

    return dependency


def _lookup_role(api_key: str, configured: dict[str, str]) -> str | None:
    for candidate, role in configured.items():
        if secrets.compare_digest(api_key, candidate):
            return role
    return None


def _key_id(api_key: str) -> str:
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"
