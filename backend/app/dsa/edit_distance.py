def levenshtein(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[n][m]


def suggest(query: str, vocabulary: list[str], max_distance: int = 2, limit: int = 5) -> list[str]:
    scored = []
    for name in vocabulary:
        best = min(levenshtein(query, word) for word in name.split())
        scored.append((name, best))
    scored = [pair for pair in scored if pair[1] <= max_distance]
    scored.sort(key=lambda pair: pair[1])
    return [name for name, _ in scored[:limit]]
