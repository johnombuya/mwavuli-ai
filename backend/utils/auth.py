"""
Role-based access control (RBAC) for Project Mwavuli.

Roles:
  viewer   - read dashboard only
  analyst  - read + update report status + export
  admin    - all + manage alert config + manage API keys + manage users

API keys are mapped to roles via the ``API_KEY_ROLES`` env var:
  API_KEY_ROLES=key1:admin,key2:analyst,key3:viewer

When API_KEYS is empty (auth disabled), all requests are treated as admin.
"""

import os
from typing import Optional

_ROLE_HIERARCHY = {"admin": 3, "analyst": 2, "viewer": 1}

_key_role_map: dict[str, str] = {}


def _load_key_roles():
    global _key_role_map
    raw = os.getenv("API_KEY_ROLES", "")
    if not raw:
        return
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        key, role = pair.rsplit(":", 1)
        _key_role_map[key.strip()] = role.strip().lower()


_load_key_roles()


def get_role_for_key(api_key: Optional[str]) -> str:
    """Return the role for a given API key."""
    if not api_key:
        return "admin"
    return _key_role_map.get(api_key, "viewer")


def has_permission(
    api_key: Optional[str], required_role: str,
) -> bool:
    """Check whether *api_key* meets *required_role*."""
    role = get_role_for_key(api_key)
    cur = _ROLE_HIERARCHY.get(role, 0)
    req = _ROLE_HIERARCHY.get(required_role, 99)
    return cur >= req
