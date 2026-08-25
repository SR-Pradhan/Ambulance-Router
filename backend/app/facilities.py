"""Hospital facility capabilities and matching.

This lives outside dsa/ on purpose. The dsa/ package is reserved for pure
algorithms (graph search, heaps, geometry); deciding that a cardiac case needs a
cardiac unit is a DOMAIN rule, not an algorithm. It also stays out of api/ so it
can be tested without a server or a database.

A facility is a CAPABILITY, not capacity. A hospital either has a trauma unit or
it does not, and no number of free beds substitutes for one. That is why a
missing facility is a HARD filter, exactly like zero available beds, rather than
a penalty in the ranking score.
"""

# Public name -> the model attribute that records it.
FACILITIES = {
    "icu": "has_icu",
    "trauma": "has_trauma_unit",
    "cardiac": "has_cardiac_unit",
}

FACILITY_LABELS = {
    "icu": "Intensive care",
    "trauma": "Trauma unit",
    "cardiac": "Cardiac unit",
}


def facility_list(hospital):
    """The facilities a hospital has, as a sorted list of public names."""
    return sorted(
        name for name, attr in FACILITIES.items() if getattr(hospital, attr, False)
    )


def hospital_has_facility(hospital, required):
    """Can this hospital treat a case needing `required`?

    `required` of None means the case has no special requirement, so every
    hospital qualifies. An unknown facility name matches nothing, which fails
    safe: better to report that no hospital qualifies than to silently ignore a
    requirement and send a cardiac patient somewhere that cannot treat them.
    """
    if required is None:
        return True
    attr = FACILITIES.get(required)
    if attr is None:
        return False
    return bool(getattr(hospital, attr, False))
