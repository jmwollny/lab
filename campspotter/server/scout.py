import gpxpy

from openai import OpenAI
import os
import math
import json
import logging
import random
from pathlib import Path
from dotenv import load_dotenv

def find_coords_at_distance(gpx_file_path, target_km):
    target_meters = target_km * 1000
    cumulative_dist = 0.0
    
    with open(gpx_file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        for segment in track.segments:
            for i in range(1, len(segment.points)):
                p1 = segment.points[i-1]
                p2 = segment.points[i]
                
                # Calculate distance between these two specific points
                dist = p1.distance_2d(p2)
                cumulative_dist += dist
                
                if cumulative_dist >= target_meters:
                    return p2.latitude, p2.longitude

    return None

import requests

import time

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


def log_step(message):
    logger.info(message)


def sleep_with_jitter(min_seconds=0.5, max_seconds=1.5):
    delay = random.uniform(min_seconds, max_seconds)
    log_step(f"Waiting {delay:.2f}s before next Overpass mirror retry.")
    time.sleep(delay)


def write_overpass_debug_query(query):
    """
    Append Overpass queries for copy/paste debugging.
    Only used when DEBUG logging is enabled.
    """
    debug_filename = os.getenv("OVERPASS_QUERY_DEBUG_FILE", "overpass_query_log.txt")
    debug_path = Path(__file__).resolve().parent / debug_filename
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with debug_path.open("a", encoding="utf-8") as debug_file:
        debug_file.write(f"\n--- {timestamp} ---\n")
        debug_file.write((query or "").strip())
        debug_file.write("\n")
    logger.debug(f"Appended Overpass query to {debug_path}")


def call_overpass_with_retry(query):
    mirrors = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter"
    ]
    query_size = len(query or "")
    log_step(f"Overpass request starting across {len(mirrors)} mirrors (query_size={query_size} chars).")
    if logger.isEnabledFor(logging.DEBUG):
        write_overpass_debug_query(query)
    retry_min_delay_s = float(os.getenv("OVERPASS_RETRY_MIN_DELAY_S", "0.5"))
    retry_max_delay_s = float(os.getenv("OVERPASS_RETRY_MAX_DELAY_S", "1.5"))

    for index, url in enumerate(mirrors):
        mirror_start = time.perf_counter()
        try:
            log_step(f"Overpass request -> {url}")
            response = requests.post(
                url,
                data={"data": query},
                headers={
                    "Accept": "application/json,text/plain,*/*",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "User-Agent": "wild-camping-scout/1.0",
                },
                timeout=100,
            )
            elapsed = time.perf_counter() - mirror_start
            log_step(f"Overpass response <- {url} status={response.status_code} elapsed={elapsed:.2f}s")
            if response.status_code == 200:
                payload = response.json()
                elements = payload.get("elements", []) if isinstance(payload, dict) else []
                log_step(f"Overpass success from {url}: elements={len(elements)}")
                if logger.isEnabledFor(logging.DEBUG):
                    write_overpass_debug_query(json.dumps(payload, indent=2))
                return payload
            elif response.status_code == 406:
                logger.warning(
                    f"Overpass returned 406 Not Acceptable at {url}; "
                    "this may be due to endpoint policy/content negotiation. Trying next mirror."
                )
                continue
            elif response.status_code == 504:
                logger.warning(f"Overpass mirror timed out (504): {url}. Trying next mirror.")
                continue
            elif response.status_code == 400:
                logger.error("Overpass query syntax error (400).")
                logger.error(response.text)
                continue
            else:
                response_excerpt = (response.text or "")[:500]
                logger.warning(
                    f"Overpass mirror returned non-success status={response.status_code} at {url}. "
                    f"Response excerpt: {response_excerpt}"
                )
        except requests.exceptions.Timeout as exc:
            logger.warning(f"Overpass request timeout for {url}: {exc}")
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Overpass request failed for {url}: {exc}")
        except ValueError as exc:
            logger.warning(f"Overpass response JSON decode failed for {url}: {exc}")
        if index < len(mirrors) - 1:
            sleep_with_jitter(retry_min_delay_s, retry_max_delay_s)
    logger.error("Overpass request failed on all mirrors.")
    return None


def fetch_way_geometries(way_ids):
    """
    Fetch full geometry for a list of OSM way ids.
    """
    if not way_ids:
        return {}

    ids_csv = ",".join(str(way_id) for way_id in way_ids)
    logger.info("Fetching way geometries for " + ids_csv)
    query = f"""
    [out:json][timeout:90];
    way(id:{ids_csv});
    out geom;
    """
    response = call_overpass_with_retry(query)
    if not response or "elements" not in response:
        return {}

    geometry_by_id = {}
    for element in response["elements"]:
        if element.get("type") == "way" and element.get("id") is not None:
            geometry_by_id[element["id"]] = element.get("geometry", [])
    return geometry_by_id


def get_llm_client():
    """
    Create an LLM client for Gemini OpenAI-compatible endpoint.
    Returns None if key is not configured.
    """
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        log_step("Gemini client not configured (missing GEMINI_API_KEY).")
        return None
    log_step("Using Gemini OpenAI-compatible client.")
    return OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=gemini_api_key,
    )


def get_local_llm_client():
    """
    Create an LLM client for a local Ollama OpenAI-compatible endpoint.
    Returns None if local usage is disabled via LOCAL_LLM_ENABLED.
    """
    load_dotenv()
    local_llm_enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if not local_llm_enabled:
        log_step("Local LLM disabled via LOCAL_LLM_ENABLED.")
        return None
    log_step("Using local Ollama OpenAI-compatible client.")
    return OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
    )

def get_camping_and_woods(lat, lon, radius_meters=2000):
    # Ensure variables are floats to avoid formatting errors
    lat = float(lat)
    lon = float(lon)
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    oldquery1 = f"""
    [out:json][timeout:90];
    (
      node["tourism"~"camp_site|wilderness_hut"](around:{radius_meters},{lat},{lon});
      way["tourism"~"camp_site|wilderness_hut"](around:{radius_meters},{lat},{lon});
      node["natural"~"wood|tree_group|scrub"](around:{radius_meters},{lat},{lon});
      way["natural"~"wood|scrub"](around:{radius_meters},{lat},{lon});
      way["landuse"="forest"](around:{radius_meters},{lat},{lon});
    );
    out center bb;
    """

    query = f"""
    [out:json][timeout:90];
    (
    // === TARGET SITES ===
    way["natural"="wood"](around:{radius_meters},{lat},{lon});
    way["landuse"="forest"](around:{radius_meters},{lat},{lon});
    node["natural"~"wood|tree_group"](around:{radius_meters},{lat},{lon});
    )->.targets;

    (
        // === RED FLAGS: CRITICAL (Stay Away) ===
        way["amenity"~"school|prison|police|cemetery|hospital"](around:{radius_meters},{lat},{lon});
        way["landuse"~"military|allotments|quarry|residential|farmyard"](around:{radius_meters},{lat},{lon});
        way["leisure"~"pitch|stadium|golf_course|playground"](around:{radius_meters},{lat},{lon});

        // === BARRIERS (Access & Difficulty) ===
        node["barrier"](around:{radius_meters},{lat},{lon});
        way["barrier"](around:{radius_meters},{lat},{lon});

        // === RED FLAGS: NUISANCE (Noise/People) ===
        node["amenity"~"pub|restaurant|parking"](around:{radius_meters},{lat},{lon});
        way["man_made"~"works|sewage_works|substation"](around:{radius_meters},{lat},{lon});
        way["railway"="rail"](around:{radius_meters},{lat},{lon});
        
        // === BUILDINGS (General Encroachment) ===
        way["building"](around:{radius_meters},{lat},{lon});
        )->.redflags;

    (
    .targets;
    .redflags;
    );
    out center bb;
    """

    oldquery2 = f"""
    [out:json][timeout:90];
    (
    // === TARGET SITES ===
    way["natural"="wood"](around:{radius_meters},{lat},{lon});
    way["landuse"="forest"](around:{radius_meters},{lat},{lon});
    node["natural"~"wood|tree_group"](around:{radius_meters},{lat},{lon});

    // === RED FLAGS: CRITICAL (Stay Away) ===
    way["amenity"~"school|prison|police|cemetery|hospital"](around:{radius_meters},{lat},{lon});
    way["landuse"~"military|allotments|quarry|residential|farmyard"](around:{radius_meters},{lat},{lon});
    way["leisure"~"pitch|stadium|golf_course|playground"](around:{radius_meters},{lat},{lon});

    // === BARRIERS (Access & Difficulty) ===
    node["barrier"](around:{radius_meters},{lat},{lon});
    way["barrier"](around:{radius_meters},{lat},{lon});

    // === RED FLAGS: NUISANCE (Noise/People) ===
    node["amenity"~"pub|restaurant|parking"](around:{radius_meters},{lat},{lon});
    way["man_made"~"works|sewage_works|substation"](around:{radius_meters},{lat},{lon});
    way["railway"="rail"](around:{radius_meters},{lat},{lon});
    
    // === BUILDINGS (General Encroachment) ===
    way["building"](around:{radius_meters},{lat},{lon});
    );
    out center bb;
    """

    return call_overpass_with_retry(query);    
def scout_agent_run(coordinate, radius):
    if not coordinate or not all(coordinate):
        return "Error: Invalid coordinate passed from Parser."
    
    log_step(f"Running Overpass scout query at lat={coordinate[0]}, lon={coordinate[1]}, radius={radius}m.")
    results = get_camping_and_woods(coordinate[0], coordinate[1], radius)

    if not results:
        logger.error("Scout query failed: no response payload returned from Overpass.")
        return "Scout query failed: Overpass request returned no payload. Check mirror/timeouts in logs."

    if 'elements' not in results:
        logger.error(f"Scout query failed: malformed Overpass response keys={list(results.keys())}")
        return "Scout query failed: malformed Overpass response (missing 'elements')."

    element_count = len(results.get("elements", []))
    log_step(f"Scout query completed with {element_count} elements.")
    if element_count == 0:
        logger.warning("Scout query returned 0 elements. This was a valid response, not a transport failure.")
        # Agentic behavior: If no woods/camps found, try widening the search
        return "No suitable areas found. Try increasing radius?"
    
    return results['elements']

def build_site_summaries_old(elements, origin_coordinate=None):
    """
    Convert raw Overpass elements into compact records for LLM input.
    Keeps only id, type, lat/lon, terrain description and ranking metrics.
    Sort order: nearest first, then largest area.
    """
    if not elements:
        return []

    compact_sites = []
    red_flags = []
    for element in elements:
        tags = element.get("tags", {})

        # Nodes have lat/lon directly; ways/relations usually have center.
        lat = element.get("lat")
        lon = element.get("lon")
        center = element.get("center", {})
        if lat is None:
            lat = center.get("lat")
        if lon is None:
            lon = center.get("lon")
        if lat is None or lon is None:
            bounds = element.get("bounds", {})
            minlat = bounds.get("minlat")
            minlon = bounds.get("minlon")
            maxlat = bounds.get("maxlat")
            maxlon = bounds.get("maxlon")
            if None not in (minlat, minlon, maxlat, maxlon):
                lat = (minlat + maxlat) / 2.0
                lon = (minlon + maxlon) / 2.0

        terrain_parts = []
        if tags.get("tourism"):
            terrain_parts.append(f"tourism:{tags['tourism']}")
        if tags.get("natural"):
            terrain_parts.append(f"natural:{tags['natural']}")
        if tags.get("landuse"):
            terrain_parts.append(f"landuse:{tags['landuse']}")
        if tags.get("name"):
            terrain_parts.append(f"name:{tags['name']}")

        terrain_description = ", ".join(terrain_parts) if terrain_parts else "unknown"
        area_m2 = None
        if element.get("type") == "way":
            area_m2 = calculate_way_area_from_bounds_m2(element.get("bounds"))
        area_size_band = classify_area_size_band(area_m2)
        distance_to_bbox_m = None
        nearest_bbox_point = None
        if origin_coordinate:
            distance_to_bbox_m, nearest_bbox_point = distance_to_element_m(
                origin_coordinate[0],
                origin_coordinate[1],
                element,
                fallback_lat=lat,
                fallback_lon=lon,
    )

    # Find nearby Red Flags within 150 meters
    hazards = []
    for flag in red_flags:
        # Simple Haversine or your get_distance function
        el = flag["element"]
        min_distance_to_hazard = int(os.getenv("MIN_DISTANCE_TO_HAZARD", "150"))
        distance_to_hazard_rounded = round(haversine_distance_m(origin_coordinate[0], origin_coordinate[1], flag["lat"], flag["lon"]))
        if distance_to_hazard_rounded < min_distance_to_hazard:
            hazards.append({
                "type": flag["flag_type"],
                "distance_to_red_flag_m": distance_to_hazard_rounded,
                "tag": flag["tags"].get("barrier") or flag["tags"].get("amenity") or "structure"
            })

    compact_sites.append(
        {
            "id": element.get("id"),
            "type": element.get("type"),
            "lat": round(lat, 6) if lat is not None else None,
            "lon": round(lon, 6) if lon is not None else None,
            "terrain_description": terrain_description,
            "area_m2": round(area_m2, 1) if area_m2 is not None else None,
            "area_size_band": area_size_band,
            "distance_to_bbox_m": round(distance_to_bbox_m, 1) if distance_to_bbox_m is not None else None,
            "bounds": normalize_bounds(element.get("bounds", {})),
            "nearest_bbox_point": nearest_bbox_point,
            "nearby_red_flags": hazards, # This is gold for the LLM
        }
    )

    compact_sites.sort(
        key=lambda site: (
            site["distance_to_bbox_m"] if site["distance_to_bbox_m"] is not None else float("inf"),
            -(site["area_m2"] if site["area_m2"] is not None else 0),
        )
    )

    logger.debug(f"Build site summaries output: {json.dumps(compact_sites)}")
    return compact_sites

def build_site_summaries(elements, origin_coordinate=None):
    if not elements:
        return []

    target_sites = []
    red_flags = []

    # --- PASS 1: Categorize Everything ---
    for el in elements:
        tags = el.get("tags", {})
        
        # Get coordinates using your existing logic
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        
        if lat is None or lon is None:
            bounds = el.get("bounds", {})
            if all(k in bounds for k in ["minlat", "maxlat", "minlon", "maxlon"]):
                lat = (bounds["minlat"] + bounds["maxlat"]) / 2.0
                lon = (bounds["minlon"] + bounds["maxlon"]) / 2.0
        
        if lat is None: continue

        # Identify if it's a Target or a Flag
        is_target = any(k in tags for k in ["natural", "tourism"]) or tags.get("landuse") == "forest"
        # Specifically exclude "Red Flag" types from being targets (e.g., a wood inside a school)
        if tags.get("amenity") == "school" or tags.get("leisure") == "pitch":
            is_target = False

        item = {
            "id": el.get("id"),
            "lat": lat,
            "lon": lon,
            "tags": tags,
            "element": el # Keep reference for area/dist calcs
        }

        if is_target:
            target_sites.append(item)
        else:
            # Classify the flag type
            flag_type = "BUILDING"
            if "barrier" in tags: flag_type = "BARRIER"
            elif tags.get("amenity") == "school": flag_type = "SCHOOL"
            elif tags.get("leisure") == "pitch": flag_type = "PLAYGROUND"
            elif tags.get("railway"): flag_type = "RAILWAY"
            
            item["flag_type"] = flag_type
            red_flags.append(item)

    # --- PASS 2: Build Compact Records & Check Proximity ---
    final_output = []
    for site in target_sites:
        el = site["element"]
        tags = site["tags"]
        
        # Your existing Terrain Description Logic
        terrain_parts = []
        for key in ["tourism", "natural", "landuse", "name"]:
            if tags.get(key): terrain_parts.append(f"{key}:{tags[key]}")
        
        terrain_description = ", ".join(terrain_parts) if terrain_parts else "unknown"
        
        # Area and Distance calcs (using your existing helper functions)
        area_m2 = calculate_way_area_from_bounds_m2(el.get("bounds")) if el.get("type") == "way" else None
        
        distance_to_bbox_m = None
        nearest_bbox_point = None
        if origin_coordinate:
            distance_to_bbox_m, nearest_bbox_point = distance_to_element_m(
                origin_coordinate[0], origin_coordinate[1], el,
                fallback_lat=site["lat"], fallback_lon=site["lon"]
            )

        # NEW: Find nearby Red Flags within 150 meters
        hazards = []
        for flag in red_flags:
            # Simple Haversine or your get_distance function
            el = flag["element"]
            # distance_to_red_flag_bbox_m = None
            # nearest_red_flag_bbox_point = None
            # if origin_coordinate:
            #     distance_to_red_flag_bbox_m, nearest_red_flag_bbox_point = distance_to_element_m(
            #     origin_coordinate[0], origin_coordinate[1], el,
            #     fallback_lat=flag["lat"], fallback_lon=flag["lon"]
            # )
            min_distance_to_hazard = int(os.getenv("MIN_DISTANCE_TO_HAZARD", "150"))
            distance_to_hazard_rounded = round(haversine_distance_m(origin_coordinate[0], origin_coordinate[1], flag["lat"], flag["lon"]))
            # distance_to_hazard_rounded = round(distance_to_red_flag_bbox_m, 1)
            if distance_to_hazard_rounded < min_distance_to_hazard:
                hazards.append({
                    "type": flag["flag_type"],
                    "distance_to_red_flag_m": distance_to_hazard_rounded,
                    "tag": flag["tags"].get("barrier") or flag["tags"].get("amenity") or "structure"
                })

        final_output.append({
            "id": site["id"],
            "type": el.get("type"),
            "lat": round(site["lat"], 6),
            "lon": round(site["lon"], 6),
            "terrain_description": terrain_description,
            "area_m2": round(area_m2, 1) if area_m2 else None,
            "area_size_band": classify_area_size_band(area_m2),
            "distance_to_bbox_m": round(distance_to_bbox_m, 1) if distance_to_bbox_m else None,
            "nearby_red_flags": hazards, # This is gold for the LLM
            "bounds": normalize_bounds(el.get("bounds", {})),
            "nearest_bbox_point": nearest_bbox_point,
        })

    # Sort nearest first
    final_output.sort(key=lambda s: (s["distance_to_bbox_m"] or float("inf"), -(s["area_m2"] or 0)))

    return final_output


def refine_top_sites_with_way_geometry(sites, origin_coordinate, top_n=3):
    """
    For top N ranked way candidates, fetch full geometry and refine nearest distance.
    """
    if not sites or not origin_coordinate:
        return sites

    top_way_ids = [
        site["id"]
        for site in sites[:top_n]
        if site.get("type") == "way" and site.get("id") is not None
    ]
    geometry_by_id = fetch_way_geometries(top_way_ids)
    if not geometry_by_id:
        return sites

    for site in sites[:top_n]:
        if site.get("type") != "way":
            continue
        way_geometry = geometry_by_id.get(site.get("id"))
        if not way_geometry:
            continue

        nearest_point, distance_m = nearest_point_on_way_geometry(
            origin_coordinate[0],
            origin_coordinate[1],
            way_geometry,
        )
        if nearest_point:
            site["nearest_bbox_point"] = nearest_point
        if distance_m is not None:
            site["distance_to_bbox_m"] = round(distance_m, 1)
        site["geometry"] = [
            {"lat": round(point["lat"], 6), "lon": round(point["lon"], 6)}
            for point in way_geometry
            if "lat" in point and "lon" in point
        ]

    sites.sort(
        key=lambda site: (
            site["distance_to_bbox_m"] if site["distance_to_bbox_m"] is not None else float("inf"),
            -(site["area_m2"] if site["area_m2"] is not None else 0),
        )
    )
    return sites


def refine_sites_with_way_geometry(sites, origin_coordinate, selected_site_ids):
    """
    Fetch geometry only for selected way ids and refine nearest distance.
    """
    if not sites or not origin_coordinate or not selected_site_ids:
        return sites

    selected_id_set = {int(site_id) for site_id in selected_site_ids}
    way_ids = [
        site["id"]
        for site in sites
        if site.get("type") == "way" and site.get("id") in selected_id_set
    ]
    geometry_by_id = fetch_way_geometries(way_ids)
    if not geometry_by_id:
        return sites

    for site in sites:
        if site.get("type") != "way" or site.get("id") not in selected_id_set:
            continue
        way_geometry = geometry_by_id.get(site["id"])
        if not way_geometry:
            continue

        nearest_point, distance_m = nearest_point_on_way_geometry(
            origin_coordinate[0],
            origin_coordinate[1],
            way_geometry,
        )
        if nearest_point:
            site["nearest_bbox_point"] = nearest_point
        if distance_m is not None:
            site["distance_to_bbox_m"] = round(distance_m, 1)
        site["geometry"] = [
            {"lat": round(point["lat"], 6), "lon": round(point["lon"], 6)}
            for point in way_geometry
            if "lat" in point and "lon" in point
        ]

    return sites


def get_element_coordinate(element):
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is not None and lon is not None:
        return lat, lon
    center = element.get("center", {})
    lat = center.get("lat")
    lon = center.get("lon")
    if lat is not None and lon is not None:
        return lat, lon
    return None


def compute_site_context_metrics_from_elements(lat, lon, elements):
    """
    Compute nearest road/water distances for one site from pre-fetched elements.
    """
    distance_to_road = None
    distance_to_water = None
    for element in elements:
        coord = get_element_coordinate(element)
        if not coord:
            continue
        dist = haversine_distance_m(lat, lon, coord[0], coord[1])
        tags = element.get("tags", {})
        is_road = tags.get("highway") in {"motorway", "trunk", "primary", "secondary"}
        is_water = (
            tags.get("waterway") in {"river", "stream", "canal", "drain", "ditch"}
            or tags.get("natural") == "water"
        )

        if is_road and (distance_to_road is None or dist < distance_to_road):
            distance_to_road = dist
        if is_water and (distance_to_water is None or dist < distance_to_water):
            distance_to_water = dist

    return {
        "distance_to_major_road_m": round(distance_to_road, 1) if distance_to_road is not None else None,
        "distance_to_water_m": round(distance_to_water, 1) if distance_to_water is not None else None,
    }


def fetch_context_elements_for_sites(sites, radius_meters=1200):
    """
    Fetch roads/water once for all candidate sites using a padded bbox query.
    """
    site_coords = [
        (site.get("lat"), site.get("lon"))
        for site in sites
        if site.get("lat") is not None and site.get("lon") is not None
    ]
    if not site_coords:
        return []

    min_lat = min(lat for lat, _ in site_coords)
    max_lat = max(lat for lat, _ in site_coords)
    min_lon = min(lon for _, lon in site_coords)
    max_lon = max(lon for _, lon in site_coords)

    mid_lat = (min_lat + max_lat) / 2.0
    lat_padding = radius_meters / 111320.0
    lon_padding = radius_meters / max(1.0, 111320.0 * abs(math.cos(math.radians(mid_lat))))

    south = min_lat - lat_padding
    west = min_lon - lon_padding
    north = max_lat + lat_padding
    east = max_lon + lon_padding
    log_step(
        "Context batch bbox "
        f"(south={south:.6f}, west={west:.6f}, north={north:.6f}, east={east:.6f}) "
        f"for {len(site_coords)} sites at radius={radius_meters}m."
    )

    query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"motorway|trunk|primary|secondary"]({south},{west},{north},{east});
      way["waterway"~"river|stream|canal|drain|ditch"]({south},{west},{north},{east});
      node["waterway"~"river|stream|canal|drain|ditch"]({south},{west},{north},{east});
      way["natural"="water"]({south},{west},{north},{east});
    );
    out center;
    """
    response = call_overpass_with_retry(query)
    if not response or "elements" not in response:
        logger.warning("Context batch query returned no elements payload.")
        return []
    elements = response["elements"]
    log_step(f"Context batch query fetched {len(elements)} elements for {len(site_coords)} sites.")
    return elements


def enrich_sites_with_context_metrics(sites, max_sites=10, radius_meters=1200):
    target_sites = sites[:max_sites]
    context_elements = fetch_context_elements_for_sites(target_sites, radius_meters=radius_meters)

    for site in target_sites:
        lat = site.get("lat")
        lon = site.get("lon")
        if lat is None or lon is None:
            continue
        metrics = compute_site_context_metrics_from_elements(lat, lon, context_elements)
        site.update(metrics)
    return sites


def compute_heuristic_suitability(site):
    """
    Fallback suitability score when LLM is unavailable.
    """
    score = 50.0
    area_m2 = site.get("area_m2")
    road_m = site.get("distance_to_major_road_m")
    water_m = site.get("distance_to_water_m")
    terrain = (site.get("terrain_description") or "").lower()

    if area_m2 is not None:
        score += min(20.0, area_m2 / 5000.0)
    if road_m is not None:
        if road_m < 100:
            score -= 20
        elif road_m < 250:
            score -= 8
        else:
            score += 8
    if water_m is not None:
        if water_m < 30:
            score -= 10
        elif water_m <= 500:
            score += 8
    if "wood" in terrain or "forest" in terrain or "scrub" in terrain:
        score += 10
    if "camp_site" in terrain:
        score += 5

    return max(0.0, min(100.0, round(score, 1)))


def parse_json_object_from_text(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None

def llm_wild_camping_criteria():
    default_criteria = "1. Flat, even ground for comfortable sleeping and stable pitching. 2. Proximity to a water source (rivers or lakes) for drinking and cooking. 3. Natural shelter from wind, such as bushes, depressions, or treelines. 4. Visual concealment from roads, trails, and nearby dwellings. 5. Distance from livestock to avoid noise, mess, and curiosity."
    message = "What is the criteria for a good overnight wild camping spot? Make a bulleted list with no other text. Ignore any legal considerations because the intention is to arrive late, leave early and leave no trace."
    local_llm_client = get_local_llm_client()
    llm_client = local_llm_client or get_llm_client()
    llm_model = (
        os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        if local_llm_client
        else "gemini-2.0-flash"
    )
    log_step(
        "Getting wild camping criteria"
    )
    if not llm_client:
        log_step("No LLM client available; using fixed crieria.")
        return default_criteria
    messages = [{"role": "user", "content": message}]
    logger.debug(f"LLM prompt: {messages}")

    try:
        llm_start = time.perf_counter()
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=messages,
            temperature=0.1,
        )
        log_step(f"LLM criteria completed in {time.perf_counter() - llm_start:.2f}s.")
        content = response.choices[0].message.content or ""
        logger.info(f"LLM response for wild camping criteria: {content}")
        return content
    except Exception as exc:
        logger.exception(f"LLM criteria retriecal failed with {exc}")
        return default_criteria

def llm_select_geom_candidates(criteria, sites, max_candidates=3):
    """
    Ask LLM to select which candidates should get geometry refinement.
    Returns selected ids and per-site suitability scores.
    """
    max_eval_sites = int(os.getenv("LLM_CANDIDATE_POOL_SIZE", "10"))
    if max_eval_sites < 1:
        max_eval_sites = 1
    candidate_sites = sites[:max_eval_sites]
    local_llm_client = get_local_llm_client()
    llm_client = local_llm_client or get_llm_client()
    llm_model = (
        os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        if local_llm_client
        else "gemini-2.0-flash"
    )
    log_step(
        f"Selecting geometry candidates from {len(candidate_sites)} sites "
        f"(pool_limit={max_eval_sites}) using model '{llm_model}'."
    )

    if not llm_client:
        log_step("No LLM client available; using heuristic fallback.")
        for site in candidate_sites:
            site["suitability_score"] = compute_heuristic_suitability(site)
            site["suitability_reason"] = "heuristic fallback"
        selected_ids = [site["id"] for site in sorted(candidate_sites, key=lambda s: s["suitability_score"], reverse=True)[:max_candidates]]
        return selected_ids

    prompt_payload = []
    for site in candidate_sites:
        prompt_payload.append(
            {
                "id": site.get("id"),
                "type": site.get("type"),
                "terrain_description": site.get("terrain_description"),
                "area_m2": site.get("area_m2"),
                "distance_to_origin_m": site.get("distance_to_bbox_m"),
                "distance_to_major_road_m": site.get("distance_to_major_road_m"),
                "distance_to_water_m": site.get("distance_to_water_m"),
            }
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are evaluating wild camping suitability."
                f"Use this wild camping criteria to help select the best sites: {criteria}.\n"
                "Prefer discreet terrain (wood/forest/scrub)"
                "Return valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evaluate these candidate sites and pick up to {max_candidates} ids that should receive detailed geometry refinement.\n"
                "Schema:  keys: selected_ids (array of ids), evaluations. evaluations is an array of objects with these keys - id, suitability_score(range 0-100), reason).\n"
                f"Candidate sites: {json.dumps(prompt_payload)}\n"
                "Return JSON only"
            ),
        },
    ]
    logger.debug(f"LLM select geom candidates prompt: {messages}")

    try:
        llm_start = time.perf_counter()
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=messages,
            temperature=0.1,
        )
        log_step(f"LLM selection completed in {time.perf_counter() - llm_start:.2f}s.")
        content = response.choices[0].message.content or ""
        parsed = parse_json_object_from_text(content)
        logger.debug(f"LLM response: {parsed}")
        if not parsed:
            raise ValueError(f"Could not parse LLM response {content}")

        evaluations = parsed.get("evaluations", [])
        eval_map = {item.get("id"): item for item in evaluations if item.get("id") is not None}
        for site in candidate_sites:
            evaluation = eval_map.get(site.get("id"))
            if evaluation:
                site["suitability_score"] = evaluation.get("suitability_score")
                site["suitability_reason"] = evaluation.get("reason")
            else:
                site["suitability_score"] = compute_heuristic_suitability(site)
                site["suitability_reason"] = "heuristic fallback"

        selected_ids = [int(site_id) for site_id in parsed.get("selected_ids", []) if site_id is not None]
        if not selected_ids:
            selected_ids = [
                site["id"]
                for site in sorted(candidate_sites, key=lambda s: s.get("suitability_score", 0), reverse=True)[:max_candidates]
            ]
        return selected_ids[:max_candidates]
    except Exception as exc:
        logger.exception(f"LLM selection failed, using heuristic fallback: {exc}")
        for site in candidate_sites:
            site["suitability_score"] = compute_heuristic_suitability(site)
            site["suitability_reason"] = "heuristic fallback"
        selected_ids = [site["id"] for site in sorted(candidate_sites, key=lambda s: s["suitability_score"], reverse=True)[:max_candidates]]
        return selected_ids


def calculate_way_area_from_bounds_m2(bounds):
    """
    Fast approximate area (m^2) from Overpass way bounding box.
    Much lighter than requesting full geometry for every way.
    """
    if not bounds:
        return None

    minlat = bounds.get("minlat")
    minlon = bounds.get("minlon")
    maxlat = bounds.get("maxlat")
    maxlon = bounds.get("maxlon")
    if None in (minlat, minlon, maxlat, maxlon):
        return None

    mid_lat_rad = math.radians((minlat + maxlat) / 2.0)
    meters_per_deg_lat = 111320.0
    meters_per_deg_lon = 111320.0 * math.cos(mid_lat_rad)

    height_m = (maxlat - minlat) * meters_per_deg_lat
    width_m = (maxlon - minlon) * meters_per_deg_lon
    if height_m <= 0 or width_m <= 0:
        return None

    return height_m * width_m


def classify_area_size_band(area_m2):
    """
    Convert numeric area to a simple qualitative size band.
    """
    if area_m2 is None:
        return "unknown"
    if area_m2 < 5000:
        return "small"
    if area_m2 < 50000:
        return "medium"
    return "large"


def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters between two coordinates."""
    earth_radius_m = 6371000.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def normalize_bounds(bounds):
    if not bounds:
        return None
    minlat = bounds.get("minlat")
    minlon = bounds.get("minlon")
    maxlat = bounds.get("maxlat")
    maxlon = bounds.get("maxlon")
    if None in (minlat, minlon, maxlat, maxlon):
        return None
    return {
        "minlat": round(minlat, 6),
        "minlon": round(minlon, 6),
        "maxlat": round(maxlat, 6),
        "maxlon": round(maxlon, 6),
    }


def distance_to_element_m(origin_lat, origin_lon, element, fallback_lat=None, fallback_lon=None):
    """
    Distance from origin coordinate to nearest point of element bounding box.
    Falls back to point distance when bounds are unavailable.
    """
    bounds = element.get("bounds", {})
    minlat = bounds.get("minlat")
    minlon = bounds.get("minlon")
    maxlat = bounds.get("maxlat")
    maxlon = bounds.get("maxlon")

    if None not in (minlat, minlon, maxlat, maxlon):
        nearest_lat = clamp(origin_lat, minlat, maxlat)
        nearest_lon = clamp(origin_lon, minlon, maxlon)
        distance = haversine_distance_m(origin_lat, origin_lon, nearest_lat, nearest_lon)
        return distance, {
            "lat": round(nearest_lat, 6),
            "lon": round(nearest_lon, 6),
        }

    if fallback_lat is not None and fallback_lon is not None:
        distance = haversine_distance_m(origin_lat, origin_lon, fallback_lat, fallback_lon)
        return distance, {
            "lat": round(fallback_lat, 6),
            "lon": round(fallback_lon, 6),
        }

    return None, None


def nearest_point_on_way_geometry(origin_lat, origin_lon, geometry):
    """
    Find nearest point on way polyline/polygon to origin.
    Uses local equirectangular projection for fast approximation.
    """
    if not geometry or len(geometry) < 2:
        return None, None

    origin_lat_rad = math.radians(origin_lat)
    meters_per_deg_lat = 111320.0
    meters_per_deg_lon = 111320.0 * math.cos(origin_lat_rad)

    def to_xy(lat, lon):
        return (
            (lon - origin_lon) * meters_per_deg_lon,
            (lat - origin_lat) * meters_per_deg_lat,
        )

    def to_latlon(x, y):
        lat = origin_lat + (y / meters_per_deg_lat)
        lon = origin_lon + (x / meters_per_deg_lon) if meters_per_deg_lon else origin_lon
        return lat, lon

    xy_points = [to_xy(point["lat"], point["lon"]) for point in geometry]
    min_distance_sq = float("inf")
    nearest_xy = None

    for i in range(len(xy_points) - 1):
        x1, y1 = xy_points[i]
        x2, y2 = xy_points[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        segment_len_sq = (dx * dx) + (dy * dy)
        if segment_len_sq == 0:
            proj_x, proj_y = x1, y1
        else:
            t = ((-x1 * dx) + (-y1 * dy)) / segment_len_sq
            t = clamp(t, 0.0, 1.0)
            proj_x = x1 + (t * dx)
            proj_y = y1 + (t * dy)

        distance_sq = (proj_x * proj_x) + (proj_y * proj_y)
        if distance_sq < min_distance_sq:
            min_distance_sq = distance_sq
            nearest_xy = (proj_x, proj_y)

    if nearest_xy is None:
        return None, None

    nearest_lat, nearest_lon = to_latlon(nearest_xy[0], nearest_xy[1])
    return (
        {"lat": round(nearest_lat, 6), "lon": round(nearest_lon, 6)},
        math.sqrt(min_distance_sq),
    )


def export_summary_to_mapper(origin_lat, origin_lon, sites, search_radius_m=None, refined_candidate_ids=None):
    """
    Export summary payload for the Svelte mapper app.
    Writes to mapper/public/summary.json.
    """
    output_path = Path(__file__).resolve().parent / "mapper" / "public" / "summary.json"
    payload = {
        "origin_coordinate": {
            "lat": round(origin_lat, 6),
            "lon": round(origin_lon, 6),
        },
        "search_radius_m": search_radius_m,
        "refined_candidate_ids": refined_candidate_ids or [],
        "sites": sites,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported mapper summary to {output_path}")