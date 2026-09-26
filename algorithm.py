import osmnx as ox
import networkx as nx

GRAPH_PATH = "data/austin_shaded_network.graphml"
print("Loading Austin street network into memory...")

G_utm = ox.load_graphml(GRAPH_PATH)


G = ox.project_graph(G_utm, to_crs="EPSG:4326")
print("Network ready for routing!")


def calculate_shade_weight(u, v, edge_data, shade_preference):
    data = edge_data[0] if 0 in edge_data else edge_data
    
    distance = float(data.get('length', 1.0))
    
    shade_coverage = float(data.get('shade_coverage', 0.0))
    
    sun_penalty = 1.0 - shade_coverage

    weight = distance + (distance * sun_penalty * shade_preference)
    
    return weight


def get_optimal_route(start_lat, start_lon, end_lat, end_lon, shade_preference=5.0):

    orig_node = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest_node = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)
    
    try:
        route_nodes = nx.shortest_path(
            G, 
            source=orig_node, 
            target=dest_node, 
            weight=lambda u, v, d: calculate_shade_weight(u, v, d, shade_preference)
        )
    except nx.NetworkXNoPath:
        return None 
        
    route_coords = []
    for node in route_nodes:
        lon = G.nodes[node]['x']
        lat = G.nodes[node]['y']
        
        route_coords.append([lon, lat])
        
    return route_coords
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