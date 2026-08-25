import heapq
 
def dijkstra(graph, source, dest):
    distances = {node: float('inf') for node in graph.adj}
    distances[source] = 0
    prev = {node: None for node in graph.adj}
    visited = set()
 
    pq = [(0, source)]  # (distance, node)
 
    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
 
        if curr_node in visited:
            continue
        visited.add(curr_node)
 
        if curr_node == dest:
            break
 
        for neighbor, weight in graph.get_neighbors(curr_node):
            new_dist = curr_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                prev[neighbor] = curr_node
                heapq.heappush(pq, (new_dist, neighbor))
 
    # reconstruct path
    path = []
    node = dest
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
 
    if distances[dest] == float('inf'):
        return None, float('inf')  # no path found

    return path, distances[dest]


def dijkstra_all(graph, source):
    """Shortest distance from source to EVERY node in the graph.

    Same algorithm as dijkstra() above, with one deliberate difference: there is
    no early exit when a destination is popped, because here every node IS a
    destination. Dijkstra naturally computes distances to all nodes anyway --
    dijkstra() just stops early once it has the one it was asked for.

    Use this when you need distances to several targets at once (e.g. ranking
    every hospital by road distance). Calling dijkstra() once per hospital would
    repeat almost identical work each time.

    Returns (distances, prev) -- pass prev to reconstruct_path() to get a route.
    """
    distances = {node: float('inf') for node in graph.adj}
    distances[source] = 0
    prev = {node: None for node in graph.adj}
    visited = set()

    pq = [(0, source)]

    while pq:
        curr_dist, curr_node = heapq.heappop(pq)

        if curr_node in visited:  # stale duplicate, already finalised
            continue
        visited.add(curr_node)

        for neighbor, weight in graph.get_neighbors(curr_node):
            new_dist = curr_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                prev[neighbor] = curr_node
                heapq.heappush(pq, (new_dist, neighbor))

    return distances, prev


def reconstruct_path(prev, source, dest):
    """Rebuild the route from source to dest by walking the prev chain backwards.

    We need `source` to tell two cases apart that otherwise look identical:
    a node that IS the source (prev is None because nothing precedes it), and a
    node that was never reached (prev is None because it was never relaxed).
    Both produce the one-element list [dest]. Checking that the reconstructed
    path actually starts at the source distinguishes them.

    Returns None if dest is unreachable from source.
    """
    if dest not in prev:
        return None

    path = []
    node = dest
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    if path[0] != source:
        return None  # chain doesn't lead back to the source -> never reached

    return path