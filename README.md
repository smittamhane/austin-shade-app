# BeatTheHeat

## First-time setup

Install Python and Node.js, then run these commands from the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
```

Set `VITE_MAPBOX_TOKEN` in `frontend\.env` to a valid Mapbox public access token.

## Start the app

In VS Code, open the command palette (Ctrl+Shift+P) -> Tasks: Run Task -> Start BeatTheHeat. The task starts the backend and frontend, waits for both to be ready, and opens the app at <http://127.0.0.1:5173/>.

The backend loads the large street-network graph on startup, which can take a minute. The launcher waits for it before opening the app.

The route panel compares the shortest-distance and shade-prioritized routes. It displays each route's distance in miles and its estimated shade coverage, calculated as a distance-weighted summary of the street-network data.

Choose **Walking (shade-aware)** to compare shortest and shade-prioritized routes on the pedestrian network, or **Biking** to calculate and display a cycling route with Mapbox Directions. Biking route directions may use bike paths and trails where available.
