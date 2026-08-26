import sys
import os

# Backend on the path (not backend/app) so `app.auth` resolves as a package.
# app/auth.py imports NO web framework, which is what lets this run under plain
# python3 with nothing installed.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.auth import key_matches, configured_key, ADMIN_KEY_HEADER


def test_correct_key_matches():
    print("Test 1 - Correct key:", key_matches("s3cret", "s3cret"))
    assert key_matches("s3cret", "s3cret") is True


def test_wrong_key_rejected():
    print("Test 2 - Wrong key:", key_matches("wrong", "s3cret"))
    assert key_matches("wrong", "s3cret") is False


def test_missing_key_rejected_without_raising():
    """A caller that sent no header must be handled like a wrong key, not crash."""
    results = [key_matches(None, "s3cret"), key_matches("", "s3cret")]
    print("Test 3 - Missing key:", results)
    assert results == [False, False]


def test_unconfigured_server_rejects_everything():
    """If the server has no key, nothing should match. Fails CLOSED."""
    results = [key_matches("anything", None), key_matches("anything", "")]
    print("Test 4 - Server has no key configured:", results)
    assert results == [False, False]


def test_near_miss_rejected():
    """One character off, and different lengths, must both fail."""
    checks = [
        key_matches("s3crets", "s3cret"),
        key_matches("s3cre", "s3cret"),
        key_matches("S3cret", "s3cret"),
    ]
    print("Test 5 - Near misses (extra char, short, wrong case):", checks)
    assert checks == [False, False, False]


def test_configured_key_reads_environment():
    original = os.environ.get("ADMIN_KEY")
    try:
        os.environ["ADMIN_KEY"] = "  from-env  "
        got = configured_key()
        print("Test 6 - Reads and strips ADMIN_KEY:", repr(got))
        assert got == "from-env", "surrounding whitespace must be stripped"

        os.environ["ADMIN_KEY"] = "   "
        blank = configured_key()
        print("        Whitespace-only treated as unset:", blank)
        assert blank is None

        del os.environ["ADMIN_KEY"]
        print("        Unset:", configured_key())
        assert configured_key() is None
    finally:
        if original is None:
            os.environ.pop("ADMIN_KEY", None)
        else:
            os.environ["ADMIN_KEY"] = original


def test_header_name_is_stable():
    """The frontend hardcodes this name; a rename would silently break it."""
    print("Test 7 - Header name:", ADMIN_KEY_HEADER)
    assert ADMIN_KEY_HEADER == "X-Admin-Key"


if __name__ == "__main__":
    test_correct_key_matches()
    test_wrong_key_rejected()
    test_missing_key_rejected_without_raising()
    test_unconfigured_server_rejects_everything()
    test_near_miss_rejected()
    test_configured_key_reads_environment()
    test_header_name_is_stable()
    print("\nAll auth tests passed.")
