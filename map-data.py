from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import requests
import shapely
from pyproj import Transformer


DATA_DIR = Path(__file__).resolve().parent / "data"
GRAPH_PATH = DATA_DIR / "austin_shaded_network.graphml"
CANOPY_ARCHIVE_URL = (
    "https://data.austintexas.gov/api/views/943x-7cq5/files/"
    "08a5ed35-868c-40a5-9f8a-6832773c5c8e?filename=Tree_Canopy_2022.zip"
)
CANOPY_ARCHIVE_PATH = DATA_DIR / "Tree_Canopy_2022.zip"
STREET_CRS = "EPSG:32614"
CANOPY_CRS = "EPSG:2277"


def _ensure_canopy_geodatabase():
    existing_gdb = next(DATA_DIR.rglob("*.gdb"), None)
    if existing_gdb:
        return existing_gdb

    partial_path = CANOPY_ARCHIVE_PATH.with_suffix(".zip.part")
    print("Downloading Austin's 2022 tree-canopy dataset (about 386 MB)...", flush=True)
    try:
        with requests.get(
            CANOPY_ARCHIVE_URL, stream=True, timeout=(30, 120)
        ) as response:
            response.raise_for_status()
            total_bytes = int(response.headers.get("content-length", 0))
            downloaded_bytes = 0
            with partial_path.open("wb") as archive_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    archive_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes % (50 * 1024 * 1024) < len(chunk):
                        total = f" of {total_bytes / 1024**2:.0f} MB" if total_bytes else ""
                        print(
                            f"  -> Downloaded {downloaded_bytes / 1024**2:.0f} MB{total}",
                            flush=True,
                        )
        partial_path.replace(CANOPY_ARCHIVE_PATH)
    except Exception:
        if partial_path.exists():
            partial_path.unlink()
        raise

    print("Extracting tree-canopy geodatabase...", flush=True)
    with tempfile.TemporaryDirectory(prefix="canopy_extract_", dir=DATA_DIR) as temp_dir:
        extraction_root = Path(temp_dir).resolve()
        with ZipFile(CANOPY_ARCHIVE_PATH) as archive:
            for member in archive.infolist():
                target = (extraction_root / member.filename).resolve()
                if target != extraction_root and extraction_root not in target.parents:
                    raise RuntimeError("Canopy archive contains an unsafe file path.")
            archive.extractall(extraction_root)

        geodatabases = list(extraction_root.rglob("*.gdb"))
        if not geodatabases:
            raise RuntimeError("The Austin canopy archive did not contain a file geodatabase.")
        geodatabase = DATA_DIR / geodatabases[0].name
        shutil.move(str(geodatabases[0]), str(geodatabase))

    return geodatabase


def _load_street_graph():
    if GRAPH_PATH.exists():
        print(f"Loading street network from {GRAPH_PATH}...", flush=True)
        graph = ox.load_graphml(GRAPH_PATH)
    else:
        place = "Austin, Texas, USA"
        print(f"Downloading pedestrian street network for {place}...", flush=True)
        graph = ox.graph_from_place(place, network_type="walk")

    if str(graph.graph.get("crs")) != STREET_CRS:
        graph = ox.project_graph(graph, to_crs=STREET_CRS)
    return graph


def create_shaded_graph():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    canopy_gdb = _ensure_canopy_geodatabase()
    layers = gpd.list_layers(canopy_gdb)
    canopy_layers = layers[
        layers["name"].str.contains("tree_canopy_2022", case=False, regex=False)
    ]
    if canopy_layers.empty:
        raise RuntimeError(f"No tree_canopy_2022 layer was found in {canopy_gdb}.")
    canopy_layer = canopy_layers.iloc[0]["name"]

    graph = _load_street_graph()
    edges_gdf = ox.graph_to_gdfs(graph, nodes=False)
    edges_buffered = edges_gdf.geometry.buffer(3)
    edge_areas = edges_buffered.area.to_numpy()

    to_canopy_crs = Transformer.from_crs(STREET_CRS, CANOPY_CRS, always_xy=True)
    canopy_bounds = to_canopy_crs.transform_bounds(*edges_gdf.total_bounds)
    print("Loading canopy polygons around the street network...", flush=True)
    canopy_gdf = gpd.read_file(
        canopy_gdb,
        layer=canopy_layer,
        bbox=canopy_bounds,
    ).to_crs(STREET_CRS)
    if canopy_gdf.empty:
        raise RuntimeError(
            "No canopy polygons intersect the street network. "
            "Check that the canopy and street coordinate systems match."
        )
    print(f"Loaded {len(canopy_gdf):,} canopy polygons.", flush=True)

    edge_indices, canopy_indices = canopy_gdf.sindex.query(
        edges_buffered, predicate="intersects"
    )
    overlap_areas = np.zeros(len(edges_gdf), dtype=np.float64)
    if len(edge_indices):
        intersections = shapely.intersection(
            edges_buffered.array.take(edge_indices),
            canopy_gdf.geometry.array.take(canopy_indices),
        )
        overlap_areas = np.bincount(
            edge_indices,
            weights=shapely.area(intersections),
            minlength=len(edges_gdf),
        )

    shade_coverage = np.divide(
        overlap_areas,
        edge_areas,
        out=np.zeros_like(overlap_areas),
        where=edge_areas > 0,
    )
    edges_gdf["shade_coverage"] = np.minimum(shade_coverage, 1.0)
    nx.set_edge_attributes(graph, edges_gdf["shade_coverage"].to_dict(), "shade_coverage")

    temporary_path = GRAPH_PATH.with_name("austin_shaded_network.tmp.graphml")
    ox.save_graphml(graph, filepath=temporary_path)
    temporary_path.replace(GRAPH_PATH)

    coverage = edges_gdf["shade_coverage"]
    shaded_edges = int((coverage > 0).sum())
    print(
        f"Saved shaded street network to {GRAPH_PATH}. "
        f"{shaded_edges:,} of {len(edges_gdf):,} edges have canopy coverage.",
        flush=True,
    )


if __name__ == "__main__":
    create_shaded_graph()
