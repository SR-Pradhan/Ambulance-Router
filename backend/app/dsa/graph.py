class Graph:
    def __init__(self):
        self.adj = {}  # node -> list of (neighbor, weight)
 
    def add_node(self, node):
        if node not in self.adj:
            self.adj[node] = []
 
    def add_edge(self, u, v, weight):
        self.add_node(u)
        self.add_node(v)
        self.adj[u].append((v, weight))
        self.adj[v].append((u, weight))  # remove this line if roads are one-way
 
    def get_neighbors(self, node):
        return self.adj.get(node, [])