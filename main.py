from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from algorithm import get_optimal_route

app = FastAPI(title="Austin Shade Routing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    shade_preference: float = 5.0  

@app.post("/api/route")
async def calculate_route(request: RouteRequest):
    """
    Receives start/end coordinates, runs the shade algorithm, 
    and returns a path of coordinates for the map to draw.
    """
    try:
        route_coords = get_optimal_route(
            request.start_lat, 
            request.start_lon, 
            request.end_lat, 
            request.end_lon, 
            request.shade_preference
        )
        
        if route_coords is None:
            raise HTTPException(status_code=404, detail="No path found between these points.")
            
        return {"coordinates": route_coords}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))