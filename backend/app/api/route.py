from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.graph_loader import load_road_network
from app.dsa.dijkstra import dijkstra
from app.dsa.astar import astar

router = APIRouter()


@router.get("/route")
def get_route(
    source: int,
    dest: int,
    algo: str = Query("dijkstra", pattern="^(dijkstra|astar|compare)$"),
    db: Session = Depends(get_db),
):
    """Shortest road route between two nodes.

    algo=dijkstra (default) | astar | compare

    `compare` runs both and reports how many nodes each expanded. Both must
    return the same distance -- A* is an optimisation of the search order, not
    a different answer. The node counts are the only honest way to show A* is
    doing anything, and they only differ once the heuristic is in the same unit
    as the edge weights (see astar.heuristic).
    """
    g, coords = load_road_network(db)

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
            "distance": d_dist,
            "comparison": {
                "dijkstra": {
                    "distance": d_dist,
                    "nodes_expanded": d_stats["nodes_expanded"],
                },
                "astar": {
                    "distance": a_dist,
                    "nodes_expanded": a_stats["nodes_expanded"],
                },
                "same_distance": abs(d_dist - a_dist) < 1e-9,
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
        "distance": dist,
        "algorithm": algo,
        "nodes_expanded": stats["nodes_expanded"],
    }
