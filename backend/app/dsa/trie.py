class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.original = None  # preserves original casing for display


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        node = self.root
        for ch in word.lower():
            node = node.children.setdefault(ch, TrieNode())
        node.is_end = True
        node.original = word

    def _collect(self, node, results):
        if node.is_end:
            results.append(node.original)
        for child in node.children.values():
            self._collect(child, results)

    def starts_with(self, prefix: str, limit: int = 10) -> list[str]:
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return []
            node = node.children[ch]
        results = []
        self._collect(node, results)
        return results[:limit]