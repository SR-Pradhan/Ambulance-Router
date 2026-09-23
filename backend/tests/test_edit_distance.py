import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.edit_distance import levenshtein, suggest


def test_levenshtein_identical_strings():
    assert levenshtein("ahmed", "ahmed") == 0


def test_levenshtein_one_substitution():
    assert levenshtein("ahmed", "ahmee") == 1


def test_levenshtein_one_insertion():
    assert levenshtein("ahmed", "ahmedd") == 1


def test_levenshtein_one_deletion():
    assert levenshtein("ahmed", "ahme") == 1


def test_levenshtein_case_insensitive():
    assert levenshtein("Ahmed", "ahmed") == 0


def test_suggest_finds_typo_in_multiword_name():
    vocabulary = ["Ahmed Hospital Multi Speciality", "City Care Hospital"]
    result = suggest("ahmedd", vocabulary, max_distance=2)
    assert result == ["Ahmed Hospital Multi Speciality"], result


def test_suggest_no_match_beyond_threshold():
    vocabulary = ["Ahmed Hospital Multi Speciality", "City Care Hospital"]
    result = suggest("zzz", vocabulary, max_distance=2)
    assert result == [], result


def test_suggest_respects_limit():
    vocabulary = [f"Hospital{i}" for i in range(10)]
    result = suggest("Hospitl0", vocabulary, max_distance=3, limit=2)
    assert len(result) <= 2, result


def test_suggest_ranks_closest_first():
    vocabulary = ["Ahmed Hospital", "Ahmedd Hospital"]
    # "Ahmedd Hospital" is an exact word match on "Ahmedd"; "Ahmed Hospital" is 1 edit away
    result = suggest("Ahmedd", vocabulary, max_distance=2)
    assert result[0] == "Ahmedd Hospital", result


if __name__ == "__main__":
    test_levenshtein_identical_strings()
    test_levenshtein_one_substitution()
    test_levenshtein_one_insertion()
    test_levenshtein_one_deletion()
    test_levenshtein_case_insensitive()
    test_suggest_finds_typo_in_multiword_name()
    test_suggest_no_match_beyond_threshold()
    test_suggest_respects_limit()
    test_suggest_ranks_closest_first()
    print("All edit distance tests passed (9)")