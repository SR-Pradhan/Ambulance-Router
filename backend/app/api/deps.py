"""Shared FastAPI dependencies.

The HTTP half of admin protection lives here rather than in `app/auth.py`,
which stays framework free so it can be tested without a server. This file owns
the header name, the status codes and the messages; `auth.py` owns the key
comparison.
"""

from fastapi import Header, HTTPException

from app.auth import ADMIN_KEY_HEADER, configured_key, key_matches


def require_admin(x_admin_key: str = Header(default=None)):
    """Guard an endpoint behind the admin key.

    Declared as a dependency rather than checked inside each handler, so the
    protection is visible in the route signature and cannot be forgotten
    halfway down a function body.
    """
    expected = configured_key()

    if expected is None:
        # Fails closed: an unconfigured server refuses admin actions rather
        # than performing them unprotected.
        raise HTTPException(
            status_code=503,
            detail=("Admin actions are disabled because ADMIN_KEY is not "
                    "configured on the server."),
        )

    if not key_matches(x_admin_key, expected):
        # Identical message whether the key was missing or wrong. Telling them
        # apart would confirm to an attacker that the header name was correct.
        raise HTTPException(
            status_code=401,
            detail=f"Admin key required. Send it in the {ADMIN_KEY_HEADER} header.",
        )

    return True
