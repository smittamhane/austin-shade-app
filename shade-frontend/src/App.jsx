import { useEffect, useRef, useState } from 'react';
import Map, { Source, Layer } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';


function App() {
  // UI State Variables
  const [startAddress, setStartAddress] = useState('');
  const [endAddress, setEndAddress] = useState('');
  const [shadePreference, setShadePreference] = useState(10.0);
 
  // Application State Variables
  const [routeData, setRouteData] = useState(null);
  const [routeCoordinates, setRouteCoordinates] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const mapRef = useRef(null);


  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;


  // Helper function to translate text addresses into GPS coordinates
  const geocode = async (address) => {
    const cleanToken = mapboxToken.trim();
    const searchAddress = /^(?:texas\s+)?(?:state\s+)?capitol$/i.test(address.trim())
      ? '1100 Congress Avenue, Austin, TX'
      : address;
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(searchAddress)}.json?access_token=${cleanToken}&proximity=-97.7431,30.2672&country=US&bbox=-98.05,30.05,-97.52,30.56&limit=1`;

    const response = await fetch(url);
    const data = await response.json();

    console.log(`Geocode raw response for ${address}:`, data);

    if (data.features && data.features.length > 0) {
      return {
        lon: data.features[0].center[0],
        lat: data.features[0].center[1]
      };
    }

    const errorDetail = data.message || 'No results returned by Mapbox';
    throw new Error(`Error for "${address}": ${errorDetail}`);
  };


  useEffect(() => {
    if (!routeCoordinates) return;

    let cancelled = false;
    let controller;

    const timeoutId = setTimeout(async () => {
      controller = new AbortController();
      try {
        const response = await fetch("http://localhost:8000/api/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            start_lat: routeCoordinates.start.lat,
            start_lon: routeCoordinates.start.lon,
            end_lat: routeCoordinates.end.lat,
            end_lon: routeCoordinates.end.lon,
            shade_preference: routeCoordinates.shadePreference
          }),
        });

        if (!response.ok) {
          throw new Error("Backend failed to calculate route. Ensure the route is within the map bounds.");
        }

        const data = await response.json();
        const routes = [data.shortest_route, data.shaded_route];
        if (routes.some((route) =>
          !Array.isArray(route?.coordinates)
          || !Number.isFinite(route.distance_meters)
          || route.distance_meters < 0
          || (route.shade_coverage_percent !== null
            && (!Number.isFinite(route.shade_coverage_percent)
              || route.shade_coverage_percent < 0
              || route.shade_coverage_percent > 100))
        )) {
          throw new Error("Backend returned invalid route details.");
        }
        if (cancelled) return;

        setRouteData(data);
      } catch (error) {
        if (!cancelled && error.name !== 'AbortError') setErrorMsg(error.message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      controller?.abort();
    };
  }, [routeCoordinates]);


  useEffect(() => {
    const coordinates = [
      ...(routeData?.shortest_route?.coordinates ?? []),
      ...(routeData?.shaded_route?.coordinates ?? []),
    ];
    if (!coordinates?.length) return;

    const bounds = coordinates.reduce((result, [longitude, latitude]) => ({
      west: Math.min(result.west, longitude),
      south: Math.min(result.south, latitude),
      east: Math.max(result.east, longitude),
      north: Math.max(result.north, latitude),
    }), {
      west: Infinity,
      south: Infinity,
      east: -Infinity,
      north: -Infinity,
    });

    mapRef.current?.fitBounds(
      [[bounds.west, bounds.south], [bounds.east, bounds.north]],
      { padding: 80, maxZoom: 15, duration: 600 }
    );
  }, [routeData]);


  // Main submission handler
  const handleCalculate = async () => {
    if (!startAddress || !endAddress) {
      setErrorMsg("Please enter both a start and end address.");
      return;
    }


    setIsLoading(true);
    setErrorMsg('');
    setRouteData(null);
    setRouteCoordinates(null);


    try {
      // 1. Geocode both addresses via Mapbox before requesting a route
      const [startCoords, endCoords] = await Promise.all([
        geocode(startAddress),
        geocode(endAddress),
      ]);
      setRouteCoordinates({
        start: startCoords,
        end: endCoords,
        shadePreference: parseFloat(shadePreference)
      });
    } catch (error) {
      setErrorMsg(error.message);
      setIsLoading(false);
    }
  };


  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
     
      {/* Floating Control Panel */}
      <div style={{
        position: 'absolute', top: 20, left: 20, zIndex: 10,
        backgroundColor: 'white', padding: '20px', borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)', width: '320px',
        display: 'flex', flexDirection: 'column', gap: '15px',
        fontFamily: 'sans-serif'
      }}>
        <h3 style={{ margin: 0, color: '#333' }}>BeatTheHeat</h3>

        <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.4, color: '#555' }}>
          Enter a full street address for each location, including the city. Business names alone may match the wrong place.
        </p>
       
        <input
          type="text"
          placeholder="Start address (e.g., 1100 Congress Ave, Austin, TX)"
          value={startAddress}
          onChange={(e) => setStartAddress(e.target.value)}
          style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
       
        <input
          type="text"
          placeholder="End address (e.g., 2100 Barton Springs Rd, Austin, TX)"
          value={endAddress}
          onChange={(e) => setEndAddress(e.target.value)}
          style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
       
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <label style={{ fontSize: '14px', color: '#555' }}>
            Shade Weight (As this value increases, the route will prioritize shaded areas): {shadePreference} %
          </label>
          <input
            type="range"
            min="0" max="100"
            value={shadePreference}
            onChange={(e) => {
              const preference = Number(e.target.value);
              setShadePreference(preference);
              if (routeCoordinates) {
                setIsLoading(true);
                setErrorMsg('');
              }
              setRouteCoordinates((current) => current
                ? { ...current, shadePreference: preference }
                : current);
            }}
            style={{ width: '100%' }}
          />
          <span style={{ fontSize: '12px', color: '#777' }}>
            Adjusting this updates the current route.
          </span>
        </div>
       
        <button
          onClick={handleCalculate}
          disabled={isLoading}
          style={{
            padding: '12px',
            backgroundColor: isLoading ? '#ccc' : '#007cbf',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isLoading ? 'Calculating...' : 'Get Route'}
        </button>


        {errorMsg && (
          <div style={{ color: '#d32f2f', fontSize: '13px', backgroundColor: '#ffebee', padding: '10px', borderRadius: '4px' }}>
            {errorMsg}
          </div>
        )}
        {routeData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', color: '#333', fontSize: '14px' }}>
            {[
              { key: 'shortest_route', label: 'Shortest route', color: '#007cbf' },
              { key: 'shaded_route', label: 'Shade-prioritized route', color: '#24834a' },
            ].map(({ key, label, color }) => {
              const route = routeData[key];
              const routeMiles = route.distance_meters / 1609.344;
              const extraMiles = Math.max(
                routeData.shaded_route.distance_meters - routeData.shortest_route.distance_meters,
                0
              ) / 1609.344;

              return (
                <div key={key} style={{ borderLeft: `4px solid ${color}`, paddingLeft: '10px' }}>
                  <strong>{label}</strong>
                  <div>{routeMiles.toFixed(2)} mi</div>
                  <div style={{ color: '#555', fontSize: '13px' }}>
                    Estimated shade coverage: {route.shade_coverage_percent === null
                      ? 'N/A'
                      : `${route.shade_coverage_percent.toFixed(0)}%`}
                  </div>
                  {key === 'shaded_route' && extraMiles > 0.01 && (
                    <div style={{ color: '#555', fontSize: '13px' }}>
                      {extraMiles.toFixed(2)} mi farther than the shortest route
                    </div>
                  )}
                </div>
              );
            })}
            <div style={{ color: '#777', fontSize: '11px' }}>
              Shade coverage is estimated from the route's distance-weighted street data.
            </div>
          </div>
        )}
      </div>


      {/* Background Map */}
      <Map
        ref={mapRef}
        initialViewState={{ longitude: -97.7431, latitude: 30.2672, zoom: 13 }}
        mapStyle="mapbox://styles/mapbox/outdoors-v12"
        mapboxAccessToken={mapboxToken}
      >
        {routeData && (
          <>
            {routeData.shortest_route.coordinates.length > 1 && (
              <Source
                id="shortest-route-source"
                type="geojson"
                data={{
                  type: 'Feature',
                  properties: {},
                  geometry: { type: 'LineString', coordinates: routeData.shortest_route.coordinates }
                }}
              >
                <Layer
                  id="shortest-route-layer"
                  type="line"
                  paint={{
                    'line-color': '#007cbf',
                    'line-width': 5,
                    'line-opacity': 0.9,
                    'line-offset': -2.5
                  }}
                />
              </Source>
            )}
            {routeData.shaded_route.coordinates.length > 1 && (
              <Source
                id="shaded-route-source"
                type="geojson"
                data={{
                  type: 'Feature',
                  properties: {},
                  geometry: { type: 'LineString', coordinates: routeData.shaded_route.coordinates }
                }}
              >
                <Layer
                  id="shaded-route-layer"
                  type="line"
                  paint={{
                    'line-color': '#24834a',
                    'line-width': 5,
                    'line-opacity': 0.9,
                    'line-offset': 2.5
                  }}
                />
              </Source>
            )}
          </>
        )}
      </Map>
    </div>
  );
}


export default App;
