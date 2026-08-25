from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import RoadNode, RoadEdge
from app.dsa.graph import Graph
from app.dsa.dijkstra import dijkstra

router = APIRouter()

@router.get("/route")
def get_route(source: int, dest: int, db: Session = Depends(get_db)):
    edges = db.query(RoadEdge).all()

    g = Graph()
    for e in edges:
        g.add_edge(e.from_node_id, e.to_node_id, e.weight)

    path, dist = dijkstra(g, source, dest)

    if dist == float('inf'):
        return {"error": "no path found"}

    return {"path": path, "distance": dist}