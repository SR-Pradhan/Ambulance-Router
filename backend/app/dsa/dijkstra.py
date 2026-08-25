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