import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.traffic import (travel_time_minutes, optimistic_time_minutes,
                         time_of_day_multiplier, effective_factor, clamp_factor,
                         FREE_FLOW_SPEED_KMH, BASE_SPEED_KMH,
                         MIN_TRAFFIC_FACTOR, MAX_TRAFFIC_FACTOR)


def test_free_road_uses_base_speed():
    t = travel_time_minutes(45.0, 1.0)
    print(f"Test 1 - 45 km on a clear road at {BASE_SPEED_KMH} km/h: {t:.1f} min")
    assert abs(t - 60.0) < 1e-9


def test_congestion_multiplies_time():
    clear = travel_time_minutes(10.0, 1.0)
    heavy = travel_time_minutes(10.0, 2.0)
    print(f"Test 2 - Same 10 km: clear {clear:.1f} min, factor 2.0 {heavy:.1f} min")
    assert abs(heavy - clear * 2) < 1e-9


def test_factor_is_clamped_both_ends():
    print("Test 3 - Clamping:", clamp_factor(0.1), clamp_factor(99), clamp_factor(None))
    assert clamp_factor(0.1) == MIN_TRAFFIC_FACTOR
    assert clamp_factor(99) == MAX_TRAFFIC_FACTOR
    assert clamp_factor(None) == MIN_TRAFFIC_FACTOR


def test_rush_hour_is_slower_than_midnight():
    morning = time_of_day_multiplier(8)
    night = time_of_day_multiplier(3)
    print(f"Test 4 - 08:00 multiplier {morning}, 03:00 multiplier {night}")
    assert morning > night


def test_time_of_day_never_speeds_a_road_up():
    """A multiplier below 1 would mean traffic making a road faster than free
    flow, which would break the A* heuristic's lower bound."""
    worst = min(time_of_day_multiplier(h) for h in range(24))
    print(f"Test 5 - Lowest multiplier across all 24 hours: {worst}")
    assert worst >= MIN_TRAFFIC_FACTOR


def test_heuristic_never_exceeds_real_travel_time():
    """The admissibility guarantee, checked directly.

    For every distance, every road factor and every hour of the day, the
    optimistic time must be <= the real time. If this ever fails, A* can return
    a route that is not the fastest.
    """
    worst_ratio = 0.0
    for distance in (0.5, 2.0, 7.5, 30.0):
        optimistic = optimistic_time_minutes(distance)
        for factor in (1.0, 1.3, 2.5, MAX_TRAFFIC_FACTOR):
            for hour in range(24):
                real = travel_time_minutes(distance, factor, hour)
                assert optimistic <= real + 1e-9, (
                    f"INADMISSIBLE: {distance} km, factor {factor}, hour {hour}: "
                    f"heuristic {optimistic:.3f} > real {real:.3f}"
                )
                worst_ratio = max(worst_ratio, optimistic / real)
    print(f"Test 6 - Admissible in all {4*4*24} combinations; "
          f"closest the heuristic ever gets to the real time: "
          f"{worst_ratio*100:.0f}%")


def test_free_flow_is_faster_than_base_speed():
    """The heuristic's speed must be optimistic relative to the real one."""
    print(f"Test 7 - Free flow {FREE_FLOW_SPEED_KMH} km/h vs base "
          f"{BASE_SPEED_KMH} km/h")
    assert FREE_FLOW_SPEED_KMH > BASE_SPEED_KMH


def test_effective_factor_combines_road_and_hour():
    road_only = effective_factor(2.0)
    at_rush = effective_factor(2.0, 8)
    print(f"Test 8 - Road factor 2.0 alone {road_only}, at 08:00 {at_rush}")
    assert at_rush > road_only


def test_zero_distance_takes_no_time():
    print("Test 9 - Zero distance:", travel_time_minutes(0.0, 3.0, 8))
    assert travel_time_minutes(0.0, 3.0, 8) == 0.0


if __name__ == "__main__":
    test_free_road_uses_base_speed()
    test_congestion_multiplies_time()
    test_factor_is_clamped_both_ends()
    test_rush_hour_is_slower_than_midnight()
    test_time_of_day_never_speeds_a_road_up()
    test_heuristic_never_exceeds_real_travel_time()
    test_free_flow_is_faster_than_base_speed()
    test_effective_factor_combines_road_and_hour()
    test_zero_distance_takes_no_time()
    print("\nAll traffic tests passed.")
