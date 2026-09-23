from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db, SessionLocal
from app.models.models import Hospital
from app.dsa.trie import Trie
from app.dsa.edit_distance import suggest

router = APIRouter()

_trie = Trie()
_names_cache: list[str] = []


def build_search_index():
    """Build the hospital-name search index once at startup.

    Uses SessionLocal directly, not the get_db dependency, because this runs
    outside a request -- same reason the road graph is built once and not
    per-request (see weakness #8 in the explainer: don't repeat that mistake
    for search).
    """
    global _trie, _names_cache
    db = SessionLocal()
    try:
        names = [h.name for h in db.query(Hospital.name).all()]
    finally:
        db.close()

    _names_cache = names
    _trie = Trie()
    for name in names:
        _trie.insert(name)


@router.get("/search/hospitals")
def search_hospitals(q: str):
    if not q:
        return {"query": q, "matches": [], "method": None}

    prefix_matches = _trie.starts_with(q)
    if prefix_matches:
        return {"query": q, "matches": prefix_matches, "method": "prefix"}

    fuzzy_matches = suggest(q, _names_cache, max_distance=2)
    return {"query": q, "matches": fuzzy_matches, "method": "edit_distance"}