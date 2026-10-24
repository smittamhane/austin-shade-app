import networkx as nx
from pathlib import Path
import osmnx as ox

# networkx helps represent the austin street network as a graph.
#osmnx loads the street graph, finds near roads to start and end points, and helps turn raw map data into a graph.


# Using the graphml file, this lines load the Austin Street Network into memory.  
GRAPH_PATH = Path(__file__).resolve().parent / "data" / "austin_shaded_network.graphml"
print("Loading Austin street network...")
G_utm = ox.load_graphml(GRAPH_PATH)


G = ox.project_graph(G_utm, to_crs="EPSG:4326")
print("Network ready for routing!")

# takes in edge data, shade preference, and whether to prioritize shade.
def _get_best_edge_data(edge_data, shade_preference, prioritize_shade=True):
    # if the edge data is a dictionary with edge attributes, there are several segments to compare.
    if edge_data and all(isinstance(data, dict) for data in edge_data.values()):
        edge_options = edge_data.values()
    else:
        # otherwise it will make a tuple with a single edge data.
        edge_options = (edge_data,)

    # if shade is not prioritized, it will return the pure distance.
    if not prioritize_shade:
        return min(edge_options, key=lambda data: float(data.get("length", 1.0)))

    # choose the edge with the shortest length.
    return min(
        edge_options,
        key=lambda data: _calculate_single_edge_weight(data, shade_preference),
    )


# Takes in the starting node, the neighboring node, the edge data, and shade preference to calculate the shade weight
def calculate_shade_weight(u, v, edge_data, shade_preference):
    return _calculate_single_edge_weight(
        _get_best_edge_data(edge_data, shade_preference), shade_preference
    )

# using data and shade preference, a signle edges weight is calculated. The formula uses sun penalty, shade preference, and distance.
def _calculate_single_edge_weight(data, shade_preference):
    distance = float(data.get('length', 1.0))
    shade_coverage = float(data.get('shade_coverage', 0.0))
    sun_penalty = 1.0 - shade_coverage
    return distance + (distance * sun_penalty * shade_preference)

# using route nodes, shade preference, and shade priority, the route coordinates, distances (in meter) and shade_coverage_percent is calculated.
def _build_route_details(route_nodes, shade_preference, prioritize_shade=True):
    route_coords = [
        [G.nodes[node]["x"], G.nodes[node]["y"]]
        for node in route_nodes
    ]
    route_distance_meters = 0.0
    shaded_distance_meters = 0.0

    for u, v in zip(route_nodes, route_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        selected_edge = _get_best_edge_data(
            edge_data, shade_preference, prioritize_shade
        )
        edge_distance = float(selected_edge.get("length", 1.0))
        edge_shade_coverage = min(
            max(float(selected_edge.get("shade_coverage", 0.0)), 0.0), 1.0
        )
        route_distance_meters += edge_distance
        shaded_distance_meters += edge_distance * edge_shade_coverage

    shade_coverage_percent = (
        shaded_distance_meters / route_distance_meters * 100
        if route_distance_meters > 0
        else None
    )

    return {
        "coordinates": route_coords,
        "distance_meters": route_distance_meters,
        "shade_coverage_percent": shade_coverage_percent,
    }

# compares shortest and shaded route based on shade perference. Returns the coordinates, distance, and shade coverage percent for both routes.
def get_route_comparison(
    start_lat, start_lon, end_lat, end_lon, shade_preference=5.0
):
    orig_node = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest_node = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

    try:
        shortest_nodes = nx.shortest_path(
            G,
            source=orig_node,
            target=dest_node,
            weight=lambda u, v, d: float(
                _get_best_edge_data(d, shade_preference, prioritize_shade=False)
                .get("length", 1.0)
            ),
        )
        shaded_nodes = nx.shortest_path(
            G,
            source=orig_node,
            target=dest_node,
            weight=lambda u, v, d: calculate_shade_weight(
                u, v, d, shade_preference
            ),
        )
    except nx.NetworkXNoPath:
        return None

    return {
        "shortest_route": _build_route_details(
            shortest_nodes, shade_preference, prioritize_shade=False
        ),
        "shaded_route": _build_route_details(
            shaded_nodes, shade_preference, prioritize_shade=True
        ),
    }

# Optimal route is calculated. Coordinates and distance are returned. None is returned if no route is found.
def get_optimal_route_with_distance(
    start_lat, start_lon, end_lat, end_lon, shade_preference=5.0
):
    orig_node = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest_node = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

    try:
        route_nodes = nx.shortest_path(
            G,
            source=orig_node,
            target=dest_node,
            weight=lambda u, v, d: calculate_shade_weight(
                u, v, d, shade_preference
            ),
        )
    except nx.NetworkXNoPath:
        return None

    shaded_route = _build_route_details(route_nodes, shade_preference)
    return shaded_route["coordinates"], shaded_route["distance_meters"]

# simpler result than the previous optimal route function. Only coordinates returned.   
def get_optimal_route(start_lat, start_lon, end_lat, end_lon, shade_preference=5.0):
    route_details = get_optimal_route_with_distance(
        start_lat, start_lon, end_lat, end_lon, shade_preference
    )
    if route_details is None:
        return None
    return route_details[0]

# Checks whether file is being run directly. Sample coordinates test the algorithm.  
if __name__ == "__main__":
    test_start_lat, test_start_lon = 30.2747, -97.7404
    test_end_lat, test_end_lon = 30.2632, -97.7444

    print("Calculating direct route (shade preference 0)...")
    direct_route = get_optimal_route(test_start_lat, test_start_lon, test_end_lat, test_end_lon, shade_preference=0.0)
    
    print("Calculating maximum shade route (shade preference 20)...")
    shade_route = get_optimal_route(test_start_lat, test_start_lon, test_end_lat, test_end_lon, shade_preference=20.0)

    print(f"Direct Route points: {len(direct_route)}")
    print(f"Shaded Route points: {len(shade_route)}")
    
    if len(shade_route) > len(direct_route):
        print("Success! The algorithm correctly took a physically longer path to stay in the shade.")