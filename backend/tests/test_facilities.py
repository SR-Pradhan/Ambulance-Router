import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from facilities import (FACILITIES, facility_list, hospital_has_facility)


class FakeHospital:
    """Stands in for a SQLAlchemy row. The matcher only reads attributes, so it
    needs no database, which is the point of keeping this module framework
    free."""

    def __init__(self, icu=False, trauma=False, cardiac=False):
        self.has_icu = icu
        self.has_trauma_unit = trauma
        self.has_cardiac_unit = cardiac


def test_no_requirement_matches_everything():
    bare = FakeHospital()
    print("Test 1 - No requirement:", hospital_has_facility(bare, None))
    assert hospital_has_facility(bare, None) is True


def test_matches_when_present():
    h = FakeHospital(cardiac=True)
    print("Test 2 - Has cardiac:", hospital_has_facility(h, "cardiac"))
    assert hospital_has_facility(h, "cardiac") is True


def test_rejects_when_absent():
    h = FakeHospital(icu=True)
    print("Test 3 - ICU hospital asked for cardiac:",
          hospital_has_facility(h, "cardiac"))
    assert hospital_has_facility(h, "cardiac") is False


def test_unknown_facility_matches_nothing():
    """Fails safe. Silently ignoring an unrecognised requirement could send a
    patient to a hospital that cannot treat them."""
    h = FakeHospital(icu=True, trauma=True, cardiac=True)
    print("Test 4 - Unknown facility on a fully equipped hospital:",
          hospital_has_facility(h, "teleportation"))
    assert hospital_has_facility(h, "teleportation") is False


def test_facility_list_is_sorted_and_only_what_is_present():
    h = FakeHospital(cardiac=True, icu=True)
    print("Test 5 - Facility list:", facility_list(h))
    assert facility_list(h) == ["cardiac", "icu"]
    assert facility_list(FakeHospital()) == []


def test_every_declared_facility_is_matchable():
    """Guards against a facility being added to the map but never wired up."""
    for name in FACILITIES:
        equipped = FakeHospital(**{
            "icu": name == "icu",
            "trauma": name == "trauma",
            "cardiac": name == "cardiac",
        })
        assert hospital_has_facility(equipped, name) is True, name
        assert hospital_has_facility(FakeHospital(), name) is False, name
    print("Test 6 - All", len(FACILITIES), "facilities matchable:", list(FACILITIES))


if __name__ == "__main__":
    test_no_requirement_matches_everything()
    test_matches_when_present()
    test_rejects_when_absent()
    test_unknown_facility_matches_nothing()
    test_facility_list_is_sorted_and_only_what_is_present()
    test_every_declared_facility_is_matchable()
    print("\nAll facility tests passed.")
