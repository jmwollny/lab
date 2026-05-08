# This is an app that uses AI to find suitable camping spots along a route
Currently I am running the LLM locally using Ollama. 
This is run using the command 
```bash
ollama run safe-gemma --keepalive 30m
```

This profile uses the `gemma4:e2b` LLM with a context size of `8192`. This runs happily on my MacBook Air 8gb laptop!

## Mapbox API key
You will need a mapbox API key. Create a `.env` file in the main directory and add the 
`VITE_MAPBOX_TOKEN` key like this `VITE_MAPBOX_TOKEN=thisismykey`.
Register at mapbox then go to https://console.mapbox.com/account/access-tokens/ to create an access token.

## Running the Svelte front end
Remember to run `npm install` before running the UI
```bash
npm run dev
```

## Running the backend

See `/server/README.MD` for information on how to install the server dependencies.

### Backend environment
Create a `server/.env` file with any keys you need for the LLM and Overpass usage, for example:

```bash
GEMINI_API_KEY=...
LOCAL_LLM_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OVERPASS_RETRY_MIN_DELAY_S=0.5
OVERPASS_RETRY_MAX_DELAY_S=1.5
```

### Run the server

```bash
cd server
uv run python server.py
```

## How to use
1. Load a GPX file. I have included the GB divide file here - /public/GBDIVIDE_v400.gpx.
2. Use the slider to set the distance where you want to search i.e. the number of kilometres along the route.
3. Optionally set the search radius. The default is 500m. Note: larger values will slow things down as the OS Maps API will return a lot more data.
4. Click 'Search this area'.

The following processes then happen:
  1. Get the list of possible sites(woods, forests) and red flags(buildings, schools, railways etc.) from Open StreetMap (OSM) - scout_agent_run
  2. The list is summarised and extra information is calculated such as size, distance from the track, distance to nearby red flags
  3. Now the top 10 sites(sorted by size) are enriched with extra information such as the distance to nearby roads or rivers
  4. We ask the LLM to return a list of wild camping criteria based on best practices
  5. This is where the magic happens. We pass the criteria and the top 10 sites along with a carefully crafted prompt to the LLM. This returns three ids
  6. For the top 3 site ids we fetch the full polygons from OSM. At the end of each stage we update the UI using a websocket. This keeps the UI responsive and provides feedback as to the state of the search query.

The user can then click these to show where they are on the map!


![image info](public/sc1.png)

![image info](public/sc2.png)

![image info](public/sc3.png)
