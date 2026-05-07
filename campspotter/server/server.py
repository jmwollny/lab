import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Import your existing functions (assuming your script is named scout.py)
from scout import (
    scout_agent_run, 
    build_site_summaries, 
    enrich_sites_with_context_metrics,
    llm_wild_camping_criteria,
    llm_select_geom_candidates,
    refine_sites_with_way_geometry
)

app = FastAPI()

# Allow your Svelte app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/analyze")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Receive { "lat": ..., "lon": ..., "radius": ... }
        data = await websocket.receive_text()
        params = json.loads(data)
        origin = (params['lat'], params['lon'])
        radius = params['radius']

        # --- WAVE 1: INITIAL DISCOVERY ---
        await websocket.send_json({"type": "status", "msg": "Retrieving data from OpenStreetMap..."})
        elements = scout_agent_run(origin, radius)
        
        if isinstance(elements, str): # Error message from your script
            await websocket.send_json({"type": "error", "msg": elements})
            return

        sites = build_site_summaries(elements, origin)
        await websocket.send_json({"type": "batch", "sites": sites})

        # --- WAVE 2: ENRICHMENT (Roads/Water) ---
        await websocket.send_json({"type": "status", "msg": "Checking context (roads/water)..."})
        # We run this in a thread to keep the socket responsive
        enriched_sites = await asyncio.to_thread(enrich_sites_with_context_metrics, sites)
        await websocket.send_json({"type": "batch", "sites": enriched_sites})

        # --- WAVE 3: LLM REFINEMENT & GEOMETRY ---
        await websocket.send_json({"type": "status", "msg": "Analysis & Geometry..."})
        
        # Get criteria and top picks
        criteria = await asyncio.to_thread(llm_wild_camping_criteria)
        selected_ids = await asyncio.to_thread(llm_select_geom_candidates, criteria, enriched_sites)
        
        # Fetch actual polygons for the winners
        final_sites = await asyncio.to_thread(refine_sites_with_way_geometry, enriched_sites, origin, selected_ids)
        
        await websocket.send_json({
            "type": "final", 
            "sites": final_sites, 
            "refined_ids": selected_ids
        })
        
        await websocket.send_json({"type": "status", "msg": "Analysis Complete"})

    except Exception as e:
        await websocket.send_json({"type": "error", "msg": str(e)})
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)