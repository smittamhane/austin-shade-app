from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from algorithm import get_route_comparison

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
    Compare the shortest-distance and shade-prioritized routes for the requested points.
    """
    try:
        route_comparison = get_route_comparison(
            request.start_lat, 
            request.start_lon, 
            request.end_lat, 
            request.end_lon, 
            request.shade_preference
        )
        
        if route_comparison is None:
            raise HTTPException(status_code=404, detail="No path found between these points.")

        return route_comparison

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))