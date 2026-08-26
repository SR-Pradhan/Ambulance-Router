"""Admin key logic. No FastAPI, no HTTP.

Deliberately framework free, for the same reason `dsa/` is: it can then be
tested with plain `python3` and no server. The HTTP side of this (the header,
the status codes, the dependency) lives in `api/deps.py`, because status codes
are an API concern rather than a security one.

What this is, and what it is not
--------------------------------
A single shared secret gating the actions that can break the live demo:
changing a hospital's bed count and completing a trip. It answers "was this
request authorised?" and nothing else.

It is NOT identity. It cannot say WHO acted, it has no roles, and it writes no
audit trail. A real system needs accounts, permissions and a log. Saying so
plainly beats implying this is more than it is.

Fails CLOSED
------------
If ADMIN_KEY is not set, admin actions are REFUSED rather than allowed. The
alternative -- reading "no key configured" as "no protection needed" -- means a
single forgotten environment variable leaves production wide open with nothing
visibly broken to warn you. Refusing is loud and safe.
"""

import os
import secrets

ADMIN_KEY_HEADER = "X-Admin-Key"


def configured_key():
    """The expected key, or None when the deployment has not set one."""
    key = os.environ.get("ADMIN_KEY", "").strip()
    return key or None


def key_matches(provided, expected):
    """Constant-time comparison of two keys.

    `secrets.compare_digest` rather than `==` on purpose. A plain string
    comparison returns as soon as two characters differ, so how long it takes
    leaks how much of the key was correct, and an attacker can recover the
    secret one character at a time. compare_digest always takes the same time
    regardless of where the difference falls.

    Returns False for a missing key rather than raising, so callers can treat
    "no key sent" and "wrong key sent" identically.
    """
    if not provided or not expected:
        return False
    return secrets.compare_digest(str(provided), str(expected))
