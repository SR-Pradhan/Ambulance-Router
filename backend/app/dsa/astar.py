import heapq

from .geo import haversine_km


def heuristic(node_coords, a, b):
    """Estimated remaining cost from node a to node b, in KILOMETRES.

    This MUST be in the same unit as the graph's edge weights. That is the
    whole game with A*: the priority is f = g + h, where g is real accumulated
    cost and h is this estimate. If the two are in different units the sum is
    meaningless -- either h is so small it does nothing (and A* silently
    degenerates into Dijkstra), or so large it dominates g (and A* stops
    returning shortest paths at all).

    Straight-line distance is the classic ADMISSIBLE heuristic: no road between
    two points can be shorter than the straight line between them, so this
    never overestimates, which is exactly the condition A* needs to stay
    optimal.

    Note this file imports from geo.py using a RELATIVE import (`.geo`). That
    matters: the app runs it as `app.dsa.astar` while the tests run it as
    `dsa.astar`, and a relative import resolves correctly under both. Both are
    pure algorithm modules with no FastAPI or database dependency, so the dsa/
    layer stays self-contained.
    """
    a_lat, a_lng = node_coords[a]
    b_lat, b_lng = node_coords[b]
    return haversine_km(a_lat, a_lng, b_lat, b_lng)


def astar(graph, source, dest, node_coords, stats=None):
    """Shortest path from source to dest, guided by a straight-line heuristic.

    Identical to Dijkstra except for what goes into the priority queue:
    Dijkstra orders by g (cost so far), A* orders by f = g + h. That bias makes
    it explore towards the destination instead of spreading out evenly.

    Pass a dict as `stats` to receive {"nodes_expanded": n} -- how many nodes
    were actually popped and processed. Comparing that against Dijkstra's count
    is how you demonstrate A* is doing something, since both return the same
    distance by design.
    """
    distances = {node: float('inf') for node in graph.adj}
    distances[source] = 0
    prev = {node: None for node in graph.adj}
    visited = set()

    pq = [(heuristic(node_coords, source, dest), source)]

    while pq:
        _, curr_node = heapq.heappop(pq)

        if curr_node in visited:
            continue
        visited.add(curr_node)

        if curr_node == dest:
            break

        for neighbor, weight in graph.get_neighbors(curr_node):
            new_dist = distances[curr_node] + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                prev[neighbor] = curr_node
                # f = g + h. distances[] keeps pure g -- the heuristic only
                # ever affects ordering, never the reported distance.
                priority = new_dist + heuristic(node_coords, neighbor, dest)
                heapq.heappush(pq, (priority, neighbor))

    if stats is not None:
        stats["nodes_expanded"] = len(visited)

    path = []
    node = dest
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    if distances[dest] == float('inf'):
        return None, float('inf')

    return path, distances[dest]
