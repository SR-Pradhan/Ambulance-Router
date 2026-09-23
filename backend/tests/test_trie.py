import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.trie import Trie


def test_insert_and_exact_prefix():
    t = Trie()
    t.insert("Ahmed Hospital Multi Speciality")
    t.insert("City Care Hospital")
    t.insert("Green Valley Clinic")

    result = t.starts_with("ah")
    assert result == ["Ahmed Hospital Multi Speciality"], result


def test_prefix_no_match_returns_empty():
    t = Trie()
    t.insert("Ahmed Hospital Multi Speciality")

    result = t.starts_with("zzz")
    assert result == [], result


def test_prefix_matches_multiple():
    t = Trie()
    t.insert("City Care Hospital")
    t.insert("City General Hospital")
    t.insert("Green Valley Clinic")

    result = t.starts_with("city")
    assert set(result) == {"City Care Hospital", "City General Hospital"}, result


def test_case_insensitive_lookup():
    t = Trie()
    t.insert("Ahmed Hospital Multi Speciality")

    result = t.starts_with("AH")
    assert result == ["Ahmed Hospital Multi Speciality"], result


def test_original_casing_preserved():
    t = Trie()
    t.insert("Ahmed Hospital Multi Speciality")

    result = t.starts_with("ahmed")
    assert result[0] == "Ahmed Hospital Multi Speciality", result


def test_empty_trie_returns_empty():
    t = Trie()
    result = t.starts_with("a")
    assert result == [], result


def test_limit_caps_results():
    t = Trie()
    for i in range(5):
        t.insert(f"Care Hospital {i}")

    result = t.starts_with("care", limit=3)
    assert len(result) == 3, result


if __name__ == "__main__":
    test_insert_and_exact_prefix()
    test_prefix_no_match_returns_empty()
    test_prefix_matches_multiple()
    test_case_insensitive_lookup()
    test_original_casing_preserved()
    test_empty_trie_returns_empty()
    test_limit_caps_results()
    print("All trie tests passed (7)")