"""Traffic model: turning distance into travel TIME.

Why this exists
---------------
The problem statement says the fastest route is hard to find because of traffic,
distance and hospital availability. Until now the graph was weighted by
DISTANCE, so the router always returned the shortest road, which is only the
fastest road when every road flows equally. Weighting by time is what makes a
congested shortcut lose to a clear detour.

The two speeds, and why the distinction matters
-----------------------------------------------
FREE_FLOW_SPEED_KMH is the fastest an ambulance could possibly go on any road.
It is NOT an average, and it is used for exactly one thing: A*'s heuristic.

A* is only guaranteed to return the shortest path if its heuristic never
overestimates. Now that edge weights are minutes, the heuristic must also be in
minutes, and it must be the most optimistic time possible. Dividing by the
free flow speed gives the shortest conceivable time to cover the straight line
distance, which no real route can beat. Dividing by an AVERAGE speed instead
would overestimate on fast roads, break admissibility, and let A* return a
route that is not actually the fastest.

Traffic factors are always >= 1.0 for the same reason: congestion can only make
a road slower than free flow, never faster, so the heuristic stays a lower
bound no matter what the traffic is doing.
"""

# The fastest possible speed on any road. Used ONLY for the A* heuristic.
FREE_FLOW_SPEED_KMH = 60.0

# What a road with no congestion actually averages, including junctions.
BASE_SPEED_KMH = 45.0

# Traffic can only slow a road down, never speed it up. Enforced, not assumed:
# a factor below 1 would break A*'s admissibility guarantee.
MIN_TRAFFIC_FACTOR = 1.0
MAX_TRAFFIC_FACTOR = 4.0

# Time of day congestion, by hour of a 24 hour clock. A multiplier on top of a
# road's own factor. These are plausible, not measured: this is simulated data.
_RUSH_HOURS = {
    7: 1.5, 8: 1.8, 9: 1.6,          # morning peak
    17: 1.6, 18: 1.9, 19: 1.7,       # evening peak
    12: 1.2, 13: 1.2,                # lunchtime
}
_NIGHT_HOURS = {0: 0.9, 1: 0.9, 2: 0.9, 3: 0.9, 4: 0.9, 5: 0.95}


def time_of_day_multiplier(hour):
    """Congestion multiplier for a given hour, clamped to never go below 1.

    Nights are quieter than the daytime baseline, but the result is still
    clamped at 1.0: allowing a sub 1 multiplier would mean traffic making a road
    FASTER than free flow, which would invalidate the A* heuristic.
    """
    raw = _RUSH_HOURS.get(hour, _NIGHT_HOURS.get(hour, 1.0))
    return max(MIN_TRAFFIC_FACTOR, raw)


def clamp_factor(factor):
    """Keep a road's own traffic factor inside the range the model allows."""
    if factor is None:
        return MIN_TRAFFIC_FACTOR
    return max(MIN_TRAFFIC_FACTOR, min(MAX_TRAFFIC_FACTOR, float(factor)))


def effective_factor(edge_factor, hour=None):
    """A road's own congestion combined with the time of day."""
    factor = clamp_factor(edge_factor)
    if hour is None:
        return factor
    return factor * time_of_day_multiplier(hour)


def travel_time_minutes(distance_km, edge_factor=1.0, hour=None):
    """How long this stretch of road takes, in minutes.

    Free flowing road: distance / BASE_SPEED. Congestion divides the speed, so
    it multiplies the time.
    """
    speed = BASE_SPEED_KMH / effective_factor(edge_factor, hour)
    return (distance_km / speed) * 60.0


def optimistic_time_minutes(distance_km):
    """The fastest that distance could conceivably be covered.

    This is the A* heuristic's unit conversion. It uses FREE_FLOW_SPEED, so it
    can never exceed the true travel time and A* stays admissible.
    """
    return (distance_km / FREE_FLOW_SPEED_KMH) * 60.0
