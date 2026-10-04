from __future__ import annotations

import requests
from functools import lru_cache
from shapely.geometry import shape

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "UrbanHeatMapper/0.1 (local educational project)"


@lru_cache(maxsize=128)
def search_cities(query: str, limit: int = 8) -> list[dict]:
    """Return candidate places from Nominatim.

    Nominatim asks clients to identify themselves with a custom User-Agent and
    to avoid heavy traffic. The Streamlit app only calls this when the user
    submits a search/changes the search result, rather than continuously.
    """
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
        "addressdetails": 1,
        "polygon_geojson": 1,
        "dedupe": 1,
        "featuretype": "city",
    }
    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    results: list[dict] = []
    for item in data:
        geometry = item.get("geojson")
        if not geometry:
            continue
        try:
            geom = shape(geometry)
        except Exception:
            continue
        if geom.is_empty:
            continue

        results.append(
            {
                "label": item.get("display_name", item.get("name", query)),
                "name": item.get("name", query),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "geometry": geom.__geo_interface__,
                "osm_type": item.get("osm_type"),
                "osm_id": item.get("osm_id"),
            }
        )

    return results
