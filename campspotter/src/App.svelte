<script>
  import { onMount } from "svelte";
  import mapboxgl from "mapbox-gl";
  import togeojson from "@mapbox/togeojson";
  import * as turf from "@turf/turf";

  let connectionStatus = "Disconnected";
  let statusMessage = "";
  let mapContainer;
  let map;
  let mapLoaded = false;
  let errorMessage = "";
  let loading = true;
  let selectedSiteId = null;
  let summaryData = {
    origin_coordinate: null,
    search_radius_m: null,
    refined_candidate_ids: [],
    sites: [],
  };
  let trackData = null; // To store the converted GeoJSON
  let trackDistanceKm = 0;
  let searchDistance = 0;
  let currentCoords = null; // [lng, lat]
  let scoutMarker;
  let searchRadiusM = 500; // Default to 500m
  let currentZoom;

  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;
  const topRankColors = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6"];
  const colorForRank = (rank) =>
    rank >= 1 && rank <= 5 ? topRankColors[rank - 1] : "#64748b";

  // Reactive statement to calculate total distance when trackData changes
  $: if (trackData) {
    const line = trackData.features.find(
      (f) => f.geometry.type === "LineString",
    );
    if (line) {
      trackDistanceKm = turf.length(line, { units: "kilometers" });
    }
  }

  function handleSliderStart() {
    currentZoom = map.getZoom()
    map.flyTo({
      center: currentCoords,
      zoom:12, // Detailed zoom for inspection
      duration: 300, // Snap it in quickly but smoothly
      essential: true,
    });
  }

  // 1. As the user slides, move the map center but DON'T search
  function handleSliderMove() {
    const coords = findCoordsAtDistance(trackData, searchDistance);
    if (coords) {
      currentCoords = coords;
      if (scoutMarker) scoutMarker.setLngLat(currentCoords);

      // Use jumpTo with a FIXED zoom level while moving
      map.jumpTo({
        center: currentCoords,
        // zoom: 12, // A comfortable height to see the track and terrain
      });

      summaryData.origin_coordinate = {
        lat: currentCoords[1],
        lon: currentCoords[0],
      };

      // Clear the sites so lines don't appear during the drag
      summaryData.sites = [];

      // We update the data, but we need to tell updateMapData
      // NOT to move the camera this time.
      updateMapData(true);
    }
  }

  // 2. When they let go, do a nice smooth zoom/fly
  function handleSliderRelease() {
    if (currentCoords) {
      map.flyTo({
        center: currentCoords,
        zoom: currentZoom, // Detailed zoom for inspection
        duration: 800, // Snap it in quickly but smoothly
        essential: true,
      });

      // Final data sync
      updateMapData(true);
    }
  }

  const siteToFeature = (site, index) => ({
    type: "Feature",
    properties: {
      id: String(site.id ?? ""),
      rank: index + 1,
      type: site.type ?? "",
      terrain: site.terrain_description ?? "unknown",
      distance: site.distance_to_bbox_m ?? null,
      areaBand: site.area_size_band ?? "unknown",
      area: site.area_m2 ?? null,
      suitabilityScore: site.suitability_score ?? null,
      suitabilityReason: site.suitability_reason ?? "",
      color: colorForRank(index + 1),
    },
    geometry: {
      type: "Point",
      coordinates: [site.lon, site.lat],
    },
  });

  const lineToNearestBBoxFeature = (origin, site, index) => {
    if (!site.nearest_bbox_point) return null;
    return {
      type: "Feature",
      properties: {
        id: String(site.id ?? ""),
        rank: index + 1,
        color: colorForRank(index + 1),
      },
      geometry: {
        type: "LineString",
        coordinates: [
          [origin.lon, origin.lat],
          [site.nearest_bbox_point.lon, site.nearest_bbox_point.lat],
        ],
      },
    };
  };

  const bboxPolygonFeature = (site) => {
    if (Array.isArray(site.geometry) && site.geometry.length >= 2) {
      const coordinates = site.geometry.map((point) => [point.lon, point.lat]);
      const first = coordinates[0];
      const last = coordinates[coordinates.length - 1];
      const isClosed = first[0] === last[0] && first[1] === last[1];
      if (isClosed && coordinates.length >= 4) {
        return {
          type: "Feature",
          properties: { id: String(site.id ?? "") },
          geometry: {
            type: "Polygon",
            coordinates: [coordinates],
          },
        };
      }
      return {
        type: "Feature",
        properties: { id: String(site.id ?? "") },
        geometry: {
          type: "LineString",
          coordinates,
        },
      };
    }

    if (!site.bounds) return null;
    const b = site.bounds;
    return {
      type: "Feature",
      properties: { id: String(site.id ?? "") },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [b.minlon, b.minlat],
            [b.maxlon, b.minlat],
            [b.maxlon, b.maxlat],
            [b.minlon, b.maxlat],
            [b.minlon, b.minlat],
          ],
        ],
      },
    };
  };

  const shapeFeatureForSite = (site) => bboxPolygonFeature(site);

  const circlePolygonFeature = (origin, radiusMeters, steps = 64) => {
    if (
      !origin ||
      origin.lat == null ||
      origin.lon == null ||
      !radiusMeters ||
      radiusMeters <= 0
    )
      return null;
    const earthRadiusM = 6371000;
    const latRad = (origin.lat * Math.PI) / 180;
    const lonRad = (origin.lon * Math.PI) / 180;
    const angularDistance = radiusMeters / earthRadiusM;
    const ring = [];

    for (let i = 0; i <= steps; i += 1) {
      const bearing = (2 * Math.PI * i) / steps;
      const sinLat = Math.sin(latRad);
      const cosLat = Math.cos(latRad);
      const sinAng = Math.sin(angularDistance);
      const cosAng = Math.cos(angularDistance);

      const pointLat = Math.asin(
        sinLat * cosAng + cosLat * sinAng * Math.cos(bearing),
      );
      const pointLon =
        lonRad +
        Math.atan2(
          Math.sin(bearing) * sinAng * cosLat,
          cosAng - sinLat * Math.sin(pointLat),
        );
      ring.push([(pointLon * 180) / Math.PI, (pointLat * 180) / Math.PI]);
    }

    return {
      type: "Feature",
      properties: { radius_m: radiusMeters },
      geometry: {
        type: "Polygon",
        coordinates: [ring],
      },
    };
  };

  const parseSummary = (data) => {
    const origin = data?.origin_coordinate;
    const sites = Array.isArray(data?.sites) ? data.sites : [];
    const refinedCandidateIds = Array.isArray(data?.refined_candidate_ids)
      ? data.refined_candidate_ids.map((id) => String(id))
      : [];
    if (!origin || origin.lat == null || origin.lon == null) {
      throw new Error(
        "summary.json is missing origin_coordinate with lat/lon.",
      );
    }
    return {
      origin_coordinate: origin,
      search_radius_m:
        typeof data?.search_radius_m === "number" ? data.search_radius_m : null,
      refined_candidate_ids: refinedCandidateIds,
      sites: sites.filter((s) => s.lat != null && s.lon != null),
    };
  };

  const fitMapToData = (origin, sites) => {
    // If there are no sites, don't try to fit the bounds!
    // This prevents the "zoom jump" while sliding.
    if (!sites || sites.length === 0) return;

    const bounds = new mapboxgl.LngLatBounds(
      [origin.lon, origin.lat],
      [origin.lon, origin.lat],
    );
    for (const site of sites) {
      bounds.extend([site.lon, site.lat]);
      // ... (rest of your existing loop)
    }
    map.fitBounds(bounds, { padding: 60, maxZoom: 14 });
  };

  const zoomToSelectedSite = (site) => {
    if (!site || !map) return;

    const bounds = new mapboxgl.LngLatBounds(
      [site.lon, site.lat],
      [site.lon, site.lat],
    );
    let hasExtendedBounds = false;

    if (Array.isArray(site.geometry) && site.geometry.length >= 2) {
      for (const point of site.geometry) {
        if (point?.lon != null && point?.lat != null) {
          bounds.extend([point.lon, point.lat]);
          hasExtendedBounds = true;
        }
      }
    } else if (site.bounds) {
      bounds.extend([site.bounds.minlon, site.bounds.minlat]);
      bounds.extend([site.bounds.maxlon, site.bounds.maxlat]);
      hasExtendedBounds = true;
    }

    if (hasExtendedBounds) {
      map.fitBounds(bounds, { padding: 80, maxZoom: 16, duration: 700 });
    } else {
      map.easeTo({
        center: [site.lon, site.lat],
        zoom: 16,
        duration: 700,
      });
    }
  };

  const updateMapData = (preventCameraMove = false) => {
    if (!map || !mapLoaded || !summaryData.origin_coordinate) return;
    const sites = summaryData.sites;
    const siteFeatures = sites.map((site, index) => siteToFeature(site, index));
    const lineFeatures = sites
      .map((site, index) =>
        lineToNearestBBoxFeature(summaryData.origin_coordinate, site, index),
      )
      .filter(Boolean);
    const bboxFeatures = sites.map(bboxPolygonFeature).filter(Boolean);
    const selectedSite = sites.find(
      (site) => String(site.id) === String(selectedSiteId),
    );
    const selectedShape = selectedSite
      ? shapeFeatureForSite(selectedSite)
      : null;
    const searchRadiusFeature = circlePolygonFeature(
      summaryData.origin_coordinate,
      summaryData.search_radius_m,
    );

    map
      .getSource("sites")
      ?.setData({ type: "FeatureCollection", features: siteFeatures });
    map
      .getSource("nearest-lines")
      ?.setData({ type: "FeatureCollection", features: lineFeatures });
    map
      .getSource("site-bboxes")
      ?.setData({ type: "FeatureCollection", features: bboxFeatures });
    map.getSource("selected-shape")?.setData({
      type: "FeatureCollection",
      features: selectedShape ? [selectedShape] : [],
    });
    map.getSource("search-radius")?.setData({
      type: "FeatureCollection",
      features: searchRadiusFeature ? [searchRadiusFeature] : [],
    });

    // ONLY move the camera if we aren't currently sliding
    if (!preventCameraMove) {
      if (selectedSite) {
        zoomToSelectedSite(selectedSite);
      } else {
        fitMapToData(summaryData.origin_coordinate, sites);
      }
    }
  };

  function handleRadiusMove() {
    // Update the data object for the circle polygon
    summaryData.search_radius_m = searchRadiusM;

    // Refresh the map layers (Redraws the red circle)
    updateMapData(true);
  }

  function handleRadiusRelease() {
    // Optional: You could trigger a re-search here automatically
    // if you want it to be super responsive.
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // 1. CLEAR ALL STATE EXPLICITLY
    summaryData = {
      origin_coordinate: null,
      search_radius_m: searchRadiusM,
      refined_candidate_ids: [],
      sites: [],
    };

    selectedSiteId = null;
    statusMessage = ""; // Clear any "Analysis Complete" text

    const text = await file.text();
    const xml = new DOMParser().parseFromString(text, "text/xml");
    const geojson = togeojson.gpx(xml);

    trackData = geojson;

    // 2. Set initial distance and find starting coords
    searchDistance = 0;
    const startCoords = findCoordsAtDistance(trackData, 0);

    if (startCoords) {
      currentCoords = startCoords;
      summaryData.origin_coordinate = {
        lat: currentCoords[1],
        lon: currentCoords[0],
      };

      if (scoutMarker) {
        scoutMarker.setLngLat(currentCoords);
      }
    }

    if (map && mapLoaded) {
      if (map.getSource("gpx-track")) {
        map.getSource("gpx-track").setData(trackData);
      } else {
        addTrackLayer();
      }

      // Fit map to the new track
      const bounds = new mapboxgl.LngLatBounds();
      geojson.features.forEach((f) => {
        if (f.geometry.type === "LineString") {
          f.geometry.coordinates.forEach((coord) => bounds.extend(coord));
        }
      });
      map.fitBounds(bounds, { padding: 50 });

      // 3. REFRESH THE MAP
      // This will effectively "wipe" the old dots and lines from the map layers
      updateMapData(true);
    }
  };

  const addTrackLayer = () => {
    map.addSource("gpx-track", { type: "geojson", data: trackData });
    map.addLayer(
      {
        id: "gpx-track-layer",
        type: "line",
        source: "gpx-track",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#3b82f6",
          "line-width": 4,
          // "line-dasharray": [2, 1],
        },
      },
      "sites",
    ); // Layer ID "sites" ensures track stays underneath the site markers
  };

  /**
   * Finds the coordinates at a specific distance along a GeoJSON LineString
   * @param {Object} geojson - The GeoJSON FeatureCollection from your GPX
   * @param {number} targetKm - Distance in kilometers
   * @returns {[number, number] | null} [lng, lat] or null
   */
  const findCoordsAtDistance = (geojson, targetKm) => {
    // 1. Get all LineStrings
    const lines = geojson.features.filter(
      (f) => f.geometry && f.geometry.type === "LineString",
    );
    if (lines.length === 0) return null;

    // 2. Flatten EVERY coordinate from EVERY segment into one single array
    // This removes the extra nesting that causes the Turf error
    const allCoords = lines.flatMap((line) =>
      line.geometry.coordinates.map((coord) => [
        Number(coord[0]),
        Number(coord[1]),
      ]),
    );

    // 3. Basic validation: do we have actual numbers?
    if (allCoords.length < 2 || isNaN(allCoords[0][0])) {
      console.error("Invalid coordinate data found");
      return null;
    }

    try {
      // 4. Create a simple LineString (one level of nesting less than MultiLineString)
      const simpleLine = turf.lineString(allCoords);

      // 5. Calculate point along
      const point = turf.along(simpleLine, targetKm, { units: "kilometers" });

      return point.geometry.coordinates;
    } catch (err) {
      console.error("Turf Error:", err.message);
      return null;
    }
  };

  async function connectAndAnalyze(lat, lon, radius) {
    if (connectionStatus === "Connected") return;

    // Clear old results before starting a new search
    summaryData.sites = [];
    summaryData.refined_candidate_ids = [];
    connectionStatus = "Connected";

    const socket = new WebSocket("ws://localhost:8000/ws/analyze");

    socket.onopen = () => {
      console.log("WebSocket connected. Sending search params...");
      socket.send(JSON.stringify({ lat, lon, radius }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "status") {
        statusMessage = data.msg;
      }

      if (data.type === "batch") {
        // Wave 1 & 2: Update the sites list
        // This merges new enrichment data into existing sites or adds new ones
        summaryData.sites = data.sites;
        updateMapData(false);
      }

      if (data.type === "final") {
        const refinedSet = new Set(data.refined_ids.map((id) => String(id)));

        // Sort: Refined sites first, then by suitability score descending
        summaryData.sites = data.sites.sort((a, b) => {
          const aIsRefined = refinedSet.has(String(a.id));
          const bIsRefined = refinedSet.has(String(b.id));

          if (aIsRefined && !bIsRefined) return -1;
          if (!aIsRefined && bIsRefined) return 1;

          // If both are refined (or both aren't), sort by score
          return (b.suitability_score || 0) - (a.suitability_score || 0);
        });

        summaryData.refined_candidate_ids = data.refined_ids;
        updateMapData(false);
      }

      if (data.type === "error") {
        console.error("Backend error:", data.msg);
        statusMessage = "Error: " + data.msg;
      }
    };

    socket.onclose = () => {
      connectionStatus = "Disconnected";
      console.log("WebSocket closed.");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      connectionStatus = "Disconnected";
      statusMessage = "Connection failed.";
    };
  }

  onMount(async () => {
    if (!mapboxToken) {
      errorMessage = "Missing VITE_MAPBOX_TOKEN. Add it to mapper/.env.";
      loading = false;
      return;
    }

    try {
      mapboxgl.accessToken = mapboxToken;
      map = new mapboxgl.Map({
        container: mapContainer,
        style: "mapbox://styles/mapbox/outdoors-v12",
        center: [-4.992869, 50.31721],
        zoom: 10,
      });

      map.on("load", () => {
        scoutMarker = new mapboxgl.Marker({ color: "#3b82f6" })
          .setLngLat([0, 0])
          .addTo(map);

        const sites = summaryData.sites;
        const siteFeatures = sites.map((site, index) =>
          siteToFeature(site, index),
        );
        const lineFeatures = sites
          .map((site, index) =>
            lineToNearestBBoxFeature(
              summaryData.origin_coordinate,
              site,
              index,
            ),
          )
          .filter(Boolean);
        const bboxFeatures = sites.map(bboxPolygonFeature).filter(Boolean);
        const searchRadiusFeature = circlePolygonFeature(
          summaryData.origin_coordinate,
          summaryData.search_radius_m,
        );
        map.addSource("sites", {
          type: "geojson",
          data: { type: "FeatureCollection", features: siteFeatures },
        });
        map.addSource("nearest-lines", {
          type: "geojson",
          data: { type: "FeatureCollection", features: lineFeatures },
        });
        map.addSource("site-bboxes", {
          type: "geojson",
          data: { type: "FeatureCollection", features: bboxFeatures },
        });
        map.addSource("selected-shape", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addSource("search-radius", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: searchRadiusFeature ? [searchRadiusFeature] : [],
          },
        });

        map.addLayer({
          id: "search-radius-fill",
          type: "fill",
          source: "search-radius",
          paint: { "fill-color": "#f43f5e", "fill-opacity": 0.08 },
        });
        map.addLayer({
          id: "search-radius-line",
          type: "line",
          source: "search-radius",
          paint: {
            "line-color": "#f43f5e",
            "line-width": 2,
            "line-opacity": 0.75,
          },
        });
        map.addLayer({
          id: "site-bboxes-line",
          type: "line",
          source: "site-bboxes",
          paint: {
            "line-color": "#00bcd4",
            "line-width": 1.5,
            "line-opacity": 0.7,
          },
        });
        map.addLayer({
          id: "selected-shape-line",
          type: "line",
          source: "selected-shape",
          paint: { "line-color": "red", "line-width": 5, "line-opacity": 0.95 },
        });
        map.addLayer({
          id: "nearest-lines",
          type: "line",
          source: "nearest-lines",
          paint: {
            "line-color": ["coalesce", ["get", "color"], "#ffd54f"],
            "line-width": 2,
            "line-opacity": 0.8,
          },
        });
        map.addLayer({
          id: "sites",
          type: "circle",
          source: "sites",
          paint: {
            "circle-radius": 6,
            "circle-color": ["coalesce", ["get", "color"], "#00e676"],
            "circle-stroke-width": 1,
            "circle-stroke-color": "#0f172a",
          },
        });

        map.on("click", "sites", (event) => {
          const feature = event.features?.[0];
          if (!feature) return;
          const [lng, lat] = feature.geometry.coordinates.slice();
          const properties = feature.properties ?? {};
          selectedSiteId = properties.id ?? null;
          new mapboxgl.Popup()
            .setLngLat([lng, lat])
            .setHTML(
              `
              <strong>Rank ${properties.rank ?? "?"}: Site ${properties.id ?? ""}</strong><br/>
              ${properties.terrain ?? ""}<br/>
              Suitability: ${properties.suitabilityScore ?? "n/a"} / 100<br/>
              Reason: ${properties.suitabilityReason || "n/a"}<br/>
              Distance: ${properties.distance ?? "n/a"} m<br/>
              Area: ${properties.area ?? "n/a"} m² (${properties.areaBand ?? "unknown"})
            `,
            )
            .addTo(map);
        });

        map.on("mouseenter", "sites", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "sites", () => {
          map.getCanvas().style.cursor = "";
        });

        fitMapToData(summaryData.origin_coordinate, sites);
        mapLoaded = true;
        loading = false;
      });
    } catch (error) {
      errorMessage =
        error instanceof Error ? error.message : "Failed to initialize map.";
      loading = false;
    }

    return () => {
      if (map) map.remove();
    };
  });

  $: if (mapLoaded) {
    // We reference these to trigger the update
    summaryData.sites;
    selectedSiteId;
    summaryData.search_radius_m;

    // Crucial change: pass 'true' to PREVENT the camera from jumping
    // while data is streaming in. Only move camera when a site is clicked.
    updateMapData(selectedSiteId ? false : true);
  }
</script>

<main>
  <h1>Wild Camping Mapper</h1>
  <div class="status">
    <button
      class="primary-btn"
      on:click={() =>
        connectAndAnalyze(currentCoords[1], currentCoords[0], searchRadiusM)}
      disabled={connectionStatus === "Connected" || !trackData}
    >Search this area
    </button>
    <br/>
    <div class="message">
      {#if connectionStatus === "Connected"}
        <span class="spinner"></span>
      {/if}
      <span>{statusMessage}</span>
    </div>
  </div>
  <div class="layout">
    <div class="map" bind:this={mapContainer}></div>
    <aside class="panel">
      <h2>Route Track</h2>
      <input type="file" accept=".gpx" on:change={handleFileUpload} />
      <hr />
      {#if trackData}
        <div class="search-control">
          <h3>Route Scout</h3>
          <p>Distance: {searchDistance.toFixed(2)} km</p>

          <input
            type="range"
            min="0"
            max={trackDistanceKm}
            step="0.1"
            bind:value={searchDistance}
            on:mousedown={handleSliderStart}
            on:touchstart={handleSliderStart}
            on:input={handleSliderMove}
            on:change={handleSliderRelease}
            on:mouseup={handleSliderRelease}
          />
        </div>
        <h3>Search Radius</h3>
        <p>
          Radius: {searchRadiusM} meters ({(searchRadiusM / 1000).toFixed(1)} km)
        </p>

        <input
          type="range"
          min="100"
          max="2000"
          step="50"
          bind:value={searchRadiusM}
          on:input={handleRadiusMove}
          on:change={handleRadiusRelease}
        />
        <hr />
      {/if}
      {#if loading}
        <p>Loading map and summary data...</p>
      {:else if errorMessage}
        <p class="error">{errorMessage}</p>
      {:else}
        <h2>Ranked Sites</h2>
        <ul>
          {#each summaryData.sites as site, i (site.id)}
            {@const isRefined = summaryData.refined_candidate_ids.includes(
              site.id,
            )}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <li
              class:selected={String(site.id) === String(selectedSiteId)}
              class:refined-highlight={isRefined}
              on:click={() => (selectedSiteId = site.id)}
              style={`
                background: ${isRefined ? colorForRank(i + 1) + "15" : "#f8fafc"};
                border-left: 5px solid ${colorForRank(i + 1)};
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
                box-shadow: ${isRefined ? "0 2px 8px rgba(0,0,0,0.05)" : "none"};
              `}
            >
              <div
                style="display: flex; justify-content: space-between; align-items: start;"
              >
                <div>
                  {#if isRefined}
                    <span class="badge">TOP PICK</span>
                  {/if}
                  <p>#{site.id}</p>
                  <strong style="display: block; margin-top: 4px;">
                    {site.terrain_description.replace("natural:", "")}
                  </strong>
                </div>
                <div style="text-align: right;display:flex;">
                  <span
                    class="score-pill"
                    style={`background: ${colorForRank(i + 1)}`}
                  >
                    {#if connectionStatus === "Connected"}
                      <span class="spinner"></span>Calculating score...
                    {:else}
                      {site.suitability_score}%
                    {/if}
                  </span>
                </div>
              </div>
              <p style="margin: 8px 0; font-size: 0.8rem; color: #475569;">
                <strong>{Math.round(site.distance_to_bbox_m)}m</strong> away •
                <strong>{site.area_size_band}</strong> area
              </p>

              {#if site.suitability_reason && site.suitability_reason !== "heuristic fallback"}
                <p class="reason-text">"{site.suitability_reason}"</p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </aside>
  </div>
</main>
