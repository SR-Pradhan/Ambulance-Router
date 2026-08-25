"""Triage priority queue - a binary min-heap written from scratch.

Everything else in this project uses Python's `heapq`. This one is implemented
by hand on purpose: the problem statement asks for a priority queue for
emergency requests, and the sift-up / sift-down mechanics are the part worth
being able to explain and to draw on a whiteboard.

The queue answers one question: of the patients still waiting, who gets the
next free ambulance?
"""

# Lower rank = more urgent. These are the only accepted severities.
SEVERITY_RANK = {
    "critical": 0,
    "urgent": 1,
    "standard": 2,
}
DEFAULT_SEVERITY = "standard"

# How long a patient must wait to gain one full severity level.
#
# This is the anti-starvation rule. With pure severity ordering, a standard
# case behind a steady stream of critical ones would NEVER be served -- it
# would sit at the back of the queue forever. Letting priority improve with
# waiting time guarantees every request is eventually served.
#
# At 10 minutes per level, a standard patient (rank 2) who has waited 20
# minutes scores 0 -- the same as a critical patient who just arrived.
AGING_MINUTES_PER_LEVEL = 10.0


def triage_score(severity, waited_minutes):
    """Effective priority. LOWER is served first.

    score = severity rank - (how long they have waited / aging rate)

    Severity sets the starting position; waiting drags it steadily towards the
    front. A score can go negative, which simply means the patient has waited
    long enough to outrank a fresh critical case.
    """
    rank = SEVERITY_RANK.get(severity, SEVERITY_RANK[DEFAULT_SEVERITY])
    return rank - (max(0.0, waited_minutes) / AGING_MINUTES_PER_LEVEL)


class PriorityQueue:
    """Binary min-heap. Smallest priority comes out first.

    Stored as a flat list where, for the node at index i:
        parent      = (i - 1) // 2
        left child  = 2i + 1
        right child = 2i + 2

    That arithmetic is why a heap needs no pointers and no tree nodes -- the
    structure is implied by the indices.

    Items are pushed as (priority, tiebreak, payload). `tiebreak` keeps the
    ordering deterministic when two items have equal priority (we pass the
    request id, so equal-priority patients are served first-come-first-served)
    and it also stops Python ever comparing two payloads, which would raise
    TypeError for dicts.
    """

    def __init__(self):
        self._heap = []

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        return len(self._heap) == 0

    def push(self, priority, tiebreak, payload):
        """Add an item. O(log n) - it sinks in at the bottom, then sifts up."""
        self._heap.append((priority, tiebreak, payload))
        self._sift_up(len(self._heap) - 1)

    def pop(self):
        """Remove and return the highest-priority payload. O(log n).

        The trick: the root is what we want, but removing from the middle of a
        list is expensive. So we move the LAST element into the root and sift it
        back down. That keeps the tree complete and costs only log n swaps.
        """
        if not self._heap:
            raise IndexError("pop from an empty priority queue")

        top = self._heap[0]
        last = self._heap.pop()

        if self._heap:  # if the list is now empty, `last` WAS the root
            self._heap[0] = last
            self._sift_down(0)

        return top[2]

    def peek(self):
        """Look at the next payload without removing it. O(1)."""
        if not self._heap:
            raise IndexError("peek at an empty priority queue")
        return self._heap[0][2]

    def _sift_up(self, i):
        """Move item i up while it is smaller than its parent."""
        while i > 0:
            parent = (i - 1) // 2
            if self._heap[i][:2] < self._heap[parent][:2]:
                self._heap[i], self._heap[parent] = self._heap[parent], self._heap[i]
                i = parent
            else:
                break

    def _sift_down(self, i):
        """Move item i down while a child is smaller than it.

        Must swap with the SMALLER of the two children -- swapping with the
        larger one would leave that child above its own smaller sibling and
        silently break the heap property.
        """
        n = len(self._heap)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i

            if left < n and self._heap[left][:2] < self._heap[smallest][:2]:
                smallest = left
            if right < n and self._heap[right][:2] < self._heap[smallest][:2]:
                smallest = right

            if smallest == i:
                return

            self._heap[i], self._heap[smallest] = self._heap[smallest], self._heap[i]
            i = smallest

    def drain(self):
        """Pop everything, in priority order. Empties the queue."""
        return [self.pop() for _ in range(len(self._heap))]
