import osmnx as ox
import geopandas as gpd
import networkx as nx
import warnings

warnings.filterwarnings("ignore")

def create_shaded_graph():
    place = "Austin, Texas, USA"
    print(f"1/4: Downloading pedestrian street network for {place}...")

    G = ox.graph_from_place(place, network_type="walk")
    
    G_proj = ox.project_graph(G, to_crs="EPSG:32614")
    edges_gdf = ox.graph_to_gdfs(G_proj, nodes=False)
    

    print("2/4: Loading the District 37 tree canopy data (this will take a moment)...")
    

    district_bounds = tuple(edges_gdf.total_bounds)
    

    canopy_gdf = gpd.read_file("data/Tree_Canopy_2022.gdb", bbox=district_bounds)
    
    canopy_gdf = canopy_gdf.to_crs("EPSG:32614") 
    
    print("3/4: Calculating shade coverage using spatial indexing...")
    edges_gdf['shade_coverage'] = 0.0
    edges_buffered = edges_gdf.geometry.buffer(3)
    
    total_edges = len(edges_gdf)
    count = 0
    
    canopy_sindex = canopy_gdf.sindex
    
    for idx, row in edges_gdf.iterrows():
        count += 1
        if count % 100 == 0:
            print(f"  -> Processing street {count} of {total_edges}...")
            
        edge_geom = edges_buffered.loc[idx]
        
        possible_matches_index = list(canopy_sindex.intersection(edge_geom.bounds))
        possible_matches = canopy_gdf.iloc[possible_matches_index]
        

        precise_matches = possible_matches[possible_matches.intersects(edge_geom)]
        
        if not precise_matches.empty:
            overlap_area = precise_matches.intersection(edge_geom).area.sum()
            total_street_area = edge_geom.area
            
            coverage_ratio = min(overlap_area / total_street_area, 1.0)
            edges_gdf.loc[idx, 'shade_coverage'] = coverage_ratio
    print("4/4: Injecting shade data back into the network map...")

    shade_dict = edges_gdf["shade_coverage"].to_dict()

    nx.set_edge_attributes(G_proj, shade_dict, 'shade_coverage')

    output_path = "data/austin_shaded_network.graphml"
    ox.save_graphml(G_proj, filepath=output_path)

    print(f"Success! Graph saved to {output_path}")

if __name__ == "__main__":
    create_shaded_graph()