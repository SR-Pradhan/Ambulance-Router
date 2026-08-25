from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.graph_loader import load_road_network, path_length_km
from app.dsa.dijkstra import dijkstra
from app.dsa.astar import astar

router = APIRouter()


@router.get("/route")
def get_route(
    source: int,
    dest: int,
    algo: str = Query("dijkstra", pattern="^(dijkstra|astar|compare)$"),
    hour: int | None = Query(None, ge=0, le=23),
    db: Session = Depends(get_db),
):
    """Shortest road route between two nodes.

    algo=dijkstra (default) | astar | compare

    Edge weights are TRAVEL TIME IN MINUTES (v1.7), so this returns the fastest
    route, not necessarily the shortest one. Both the duration and the physical
    distance are reported, and they can disagree: a longer road that is flowing
    freely beats a short one that is gridlocked.

    `hour` (0 to 23) overrides the time of day used for congestion. Without it
    the current hour is used, which means results legitimately change across the
    day; pass it explicitly for a reproducible answer or to demonstrate rush
    hour against the middle of the night.

    `compare` runs both and reports how many nodes each expanded. Both must
    return the same distance -- A* is an optimisation of the search order, not
    a different answer. The node counts are the only honest way to show A* is
    doing anything, and they only differ once the heuristic is in the same unit
    as the edge weights (see astar.heuristic).
    """
    g, coords = load_road_network(db, hour=hour)

    if source not in g.adj or dest not in g.adj:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node id (valid ids: {min(g.adj)}-{max(g.adj)})",
        )

    if algo == "compare":
        d_stats, a_stats = {}, {}
        d_path, d_dist = dijkstra(g, source, dest, stats=d_stats)
        a_path, a_dist = astar(g, source, dest, coords, stats=a_stats)

        if d_dist == float('inf'):
            return {"error": "no path found"}

        return {
            "path": d_path,
            "duration_minutes": round(d_dist, 2),
            "distance_km": round(path_length_km(d_path, coords), 3),
            "comparison": {
                "dijkstra": {
                    "duration_minutes": round(d_dist, 2),
                    "nodes_expanded": d_stats["nodes_expanded"],
                },
                "astar": {
                    "duration_minutes": round(a_dist, 2),
                    "nodes_expanded": a_stats["nodes_expanded"],
                },
                "same_duration": abs(d_dist - a_dist) < 1e-9,
                "nodes_saved": d_stats["nodes_expanded"] - a_stats["nodes_expanded"],
            },
        }

    stats = {}
    if algo == "astar":
        path, dist = astar(g, source, dest, coords, stats=stats)
    else:
        path, dist = dijkstra(g, source, dest, stats=stats)

    if dist == float('inf'):
        return {"error": "no path found"}

    return {
        "path": path,
        "duration_minutes": round(dist, 2),
        "distance_km": round(path_length_km(path, coords), 3),
        "algorithm": algo,
        "hour": hour if hour is not None else datetime.now().hour,
        "nodes_expanded": stats["nodes_expanded"],
    }
