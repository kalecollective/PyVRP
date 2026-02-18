"""
Minimal test for elevation cost feature.

Creates a simple instance with elevation data and verifies that:
1. Elevation data is stored correctly
2. Elevation gain is computed correctly
3. Routes track elevation cost
4. Solutions aggregate elevation cost from routes
"""

from pyvrp import Model, Solution
from pyvrp._pyvrp import CostEvaluator


def test_elevation_basics():
    """Test basic elevation functionality."""
    print("Testing basic elevation functionality...")

    m = Model()

    # Add depot at elevation 0m
    depot = m.add_depot(x=0, y=0, elevation=0)
    assert depot.elevation == 0, f"Expected depot elevation 0, got {depot.elevation}"
    print(f"✓ Depot created at elevation {depot.elevation}m")

    # Add client at low elevation (10m)
    client1 = m.add_client(x=10, y=0, delivery=20, elevation=10, name="low")
    assert client1.elevation == 10
    print(f"✓ Client 'low' created at elevation {client1.elevation}m")

    # Add client at high elevation (100m)
    client2 = m.add_client(x=0, y=10, delivery=30, elevation=100, name="high")
    assert client2.elevation == 100
    print(f"✓ Client 'high' created at elevation {client2.elevation}m")

    # Create routing profile and edges
    profile = m.add_profile()

    # Add edges for all location pairs
    m.add_edge(depot, client1, distance=1000, duration=1000, profile=profile)
    m.add_edge(client1, depot, distance=1000, duration=1000, profile=profile)
    m.add_edge(depot, client2, distance=1000, duration=1000, profile=profile)
    m.add_edge(client2, depot, distance=1000, duration=1000, profile=profile)
    m.add_edge(client1, client2, distance=1414, duration=1414, profile=profile)
    m.add_edge(client2, client1, distance=1414, duration=1414, profile=profile)

    # Add vehicle with unit elevation cost
    m.add_vehicle_type(
        num_available=1, capacity=100, profile=profile, unit_elevation_cost=1
    )

    # Build problem data
    data = m.data()

    # Test elevation gain computation
    gain_depot_to_low = data.elevation_gain(0, 1)  # 0m -> 10m = +10m
    gain_depot_to_high = data.elevation_gain(0, 2)  # 0m -> 100m = +100m
    gain_high_to_low = data.elevation_gain(2, 1)  # 100m -> 10m = 0 (downhill)
    gain_low_to_high = data.elevation_gain(1, 2)  # 10m -> 100m = +90m

    assert gain_depot_to_low == 10, f"Expected gain 10, got {gain_depot_to_low}"
    assert gain_depot_to_high == 100, f"Expected gain 100, got {gain_depot_to_high}"
    assert gain_high_to_low == 0, f"Expected gain 0 (downhill), got {gain_high_to_low}"
    assert gain_low_to_high == 90, f"Expected gain 90, got {gain_low_to_high}"

    print("✓ Elevation gains computed correctly:")
    print(f"  depot->low: {gain_depot_to_low}m, depot->high: {gain_depot_to_high}m")
    print(f"  high->low: {gain_high_to_low}m, low->high: {gain_low_to_high}m")

    return data


def test_route_elevation_cost():
    """Test that routes compute elevation cost correctly."""
    print("\nTesting route elevation cost...")

    data = test_elevation_basics()

    # Create a route: depot -> low (20kg) -> high (30kg) -> depot
    # Arc costs (load × elevation_gain × unit_elevation_cost):
    #   depot->low:  50kg × 10m × 1 = 500
    #   low->high:   30kg × 90m × 1 = 2700  (20kg delivered at low, 30kg remaining)
    #   high->depot: 0kg × 0m × 1 = 0       (30kg delivered at high, downhill anyway)
    # Total: 3200

    from pyvrp import Route

    route = Route(data, [1, 2], vehicle_type=0)

    print("Route visits: depot -> low -> high -> depot")
    print(f"Route elevation cost (weighted): {route.elevation_cost()}")
    print("  Expected: (50×10 + 30×90 + 0×0) × 1 = (500 + 2700 + 0) × 1 = 3200")

    # The cost is already weighted by unit_elevation_cost from the vehicle type
    assert (
        route.elevation_cost() == 3200
    ), f"Expected 3200, got {route.elevation_cost()}"
    print(f"✓ Route elevation cost computed correctly: {route.elevation_cost()}")

    return data, route


def test_solution_elevation_cost():
    """Test that solutions aggregate elevation cost."""
    print("\nTesting solution elevation cost...")

    data, route = test_route_elevation_cost()

    # Create solution with one route
    solution = Solution(data, [route])

    print(f"Solution elevation cost: {solution.elevation_cost()}")
    assert solution.elevation_cost() == route.elevation_cost()
    print("✓ Solution aggregates route elevation cost correctly")

    return solution


def test_cost_evaluator():
    """Test CostEvaluator with elevation cost."""
    print("\nTesting CostEvaluator with elevation cost...")

    solution = test_solution_elevation_cost()

    # Create evaluator (elevation cost already weighted in routes)
    evaluator = CostEvaluator(load_penalties=[0.0], tw_penalty=0.0, dist_penalty=0.0)

    print("✓ CostEvaluator created (elevation cost handled by VehicleType)")

    # Penalised cost should include weighted elevation cost from routes
    penalised = evaluator.penalised_cost(solution)
    print(f"Solution penalised cost: {penalised}")
    print(f"  Distance cost: {solution.distance_cost()}")
    print(f"  Duration cost: {solution.duration_cost()}")
    print(f"  Elevation cost: {solution.elevation_cost()}")
    print(
        f"  Total: {solution.distance_cost() + solution.duration_cost() + solution.elevation_cost()}"
    )

    expected = (
        solution.distance_cost() + solution.duration_cost() + solution.elevation_cost()
    )
    assert penalised == expected, f"Expected {expected}, got {penalised}"
    print("✓ CostEvaluator includes elevation cost in penalised_cost")


if __name__ == "__main__":
    print("=" * 60)
    print("MINIMAL ELEVATION COST TEST")
    print("=" * 60)

    test_cost_evaluator()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
