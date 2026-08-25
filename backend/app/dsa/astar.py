import heapq
import math

def heuristic(node_coords, a, b):
    ax, ay = node_coords[a]
    bx, by = node_coords[b]
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

def astar(graph, source, dest, node_coords):
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
                priority = new_dist + heuristic(node_coords, neighbor, dest)
                heapq.heappush(pq, (priority, neighbor))

    path = []
    node = dest
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    if distances[dest] == float('inf'):
        return None, float('inf')

    return path, distances[dest]