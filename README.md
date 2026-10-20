# Austin Shade Routing

## First-time setup

Install Python and Node.js, then run these commands from the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd shade-frontend
npm ci
```

Set `VITE_MAPBOX_TOKEN` in `shade-frontend\.env` to a valid Mapbox public access token.

## Start the app

In VS Code, open the Command Palette (`Ctrl+Shift+P`), choose **Tasks: Run Task**, and run **Start Austin Shade App**. The task starts the backend and frontend, waits for both to be ready, and opens the app at <http://127.0.0.1:5173/>.

The backend loads the large street-network graph on startup, which can take a minute. The launcher waits for it before opening the app.

The route panel compares the shortest-distance and shade-prioritized routes. It displays each route's distance in miles and its estimated shade coverage, calculated as a distance-weighted summary of the street-network data.
