from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from algorithm import get_route_comparison

# FastAPI creates the web API. CORS controls the web pages that are allowed to make requests to API. Pydantic Base class defines the strucutre of data

app = FastAPI(title="BeatTheHeat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

#Expected format of a request to the endpoint  
class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    shade_preference: float = 5.0  

# Registers handler for POST requests to /api/route  
@app.post("/api/route")
async def calculate_route(request: RouteRequest):
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