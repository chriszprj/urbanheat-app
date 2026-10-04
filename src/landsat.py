from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil

from matplotlib import colormaps
import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
from pyproj import Transformer
from rasterio.mask import mask
from rasterio.transform import array_bounds
from rasterio.warp import reproject, transform_bounds
from rasterio.enums import Resampling
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "landsat-c2-l2"
ST_SCALE = 0.00341802
ST_OFFSET_K = 149.0


def _stac_client():
    return pystac_client.Client.open(STAC_URL, modifier=pc.sign_inplace)


def find_candidate_scenes(city_geometry: dict, days_back: int, max_cloud: float, limit: int = 12):
    """Return several recent Landsat 8/9 candidates so a cloudy scene does not block the analysis."""
    geom = shape(city_geometry)
    bbox = geom.bounds
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)

    catalog = _stac_client()
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={
            "eo:cloud_cover": {"lte": max_cloud},
            "platform": {"in": ["landsat-8", "landsat-9"]},
        },
        max_items=max(limit, 40),
    )
    items = list(search.items())
    if not items:
        raise RuntimeError(
            "No Landsat 8/9 scenes met the date/cloud filters. Increase the look-back window or cloud threshold."
        )

    # Rank by scene cloud cover first, then prefer newer acquisitions.
    items.sort(
        key=lambda item: (
            float(item.properties.get("eo:cloud_cover", 100.0)),
            -(item.datetime.timestamp() if item.datetime else 0.0),
        )
    )
    return items[:limit]


def find_best_scene(city_geometry: dict, days_back: int, max_cloud: float):
    """Backward-compatible helper returning the first candidate scene."""
    return find_candidate_scenes(city_geometry, days_back, max_cloud, limit=1)[0]


def _utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def _utm_geometry(geometry, centroid_lon: float, centroid_lat: float):
    epsg = _utm_epsg(centroid_lon, centroid_lat)
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True).transform
    from_utm = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True).transform
    return shapely_transform(to_utm, geometry), epsg, from_utm


def _read_masked(asset_href: str, geometry_utm, crop_geometry_utm):
    with rasterio.open(asset_href) as src:
        shape_in_src = shapely_transform(
            Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform,
            geometry_utm,
        )
        crop_in_src = shapely_transform(
            Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform,
            crop_geometry_utm,
        )
        data, transform = mask(src, [mapping(crop_in_src)], crop=True, filled=True)
        return data[0], transform, src.crs, src.nodata


def analyze_city_heat(
    city_geometry: dict,
    scene,
    buffer_km: float,
    min_clear_percent: float,
    st_uncertainty_k: float = 3.0,
) -> dict:
    city_wgs84 = shape(city_geometry)
    city_utm, epsg, from_utm = _utm_geometry(
        city_wgs84, city_wgs84.centroid.x, city_wgs84.centroid.y
    )
    outer = city_utm.buffer(buffer_km * 1000)
    ring = outer.difference(city_utm)

    assets = scene.assets
    st_asset = assets.get("lwir11") or assets.get("lwir")
    qa_asset = assets.get("qa_pixel")
    stqa_asset = assets.get("qa")
    if st_asset is None or qa_asset is None:
        raise RuntimeError("The selected scene is missing required surface-temperature or QA assets.")

    # Crop the satellite reads once to the outer analysis footprint.
    with rasterio.open(st_asset.href) as st_src:
        crop_in_src = shapely_transform(
            Transformer.from_crs(f"EPSG:{epsg}", st_src.crs, always_xy=True).transform,
            outer,
        )
        st_raw, out_transform = mask(st_src, [mapping(crop_in_src)], crop=True, filled=True)
        st_raw = st_raw[0]
        source_crs = st_src.crs
        st_nodata = st_src.nodata

    def read_aligned(asset_href: str) -> np.ndarray:
        with rasterio.open(asset_href) as src:
            crop_in_src = shapely_transform(
                Transformer.from_crs(f"EPSG:{epsg}", src.crs, always_xy=True).transform,
                outer,
            )
            src_arr, src_transform = mask(src, [mapping(crop_in_src)], crop=True, filled=True)
            src_arr = src_arr[0]
            if src_arr.shape == st_raw.shape and src_transform == out_transform and src.crs == source_crs:
                return src_arr

            aligned = np.full(st_raw.shape, 0, dtype=src_arr.dtype)
            reproject(
                source=src_arr,
                destination=aligned,
                src_transform=src_transform,
                src_crs=src.crs,
                dst_transform=out_transform,
                dst_crs=source_crs,
                resampling=Resampling.nearest,
            )
            return aligned

    qa_raw = read_aligned(qa_asset.href)

    st_uncertainty = None
    if stqa_asset is not None:
        try:
            stqa_raw = read_aligned(stqa_asset.href)
            st_uncertainty = stqa_raw.astype("float32") * 0.01
        except Exception:
            st_uncertainty = None

    temp_c = st_raw.astype("float32") * ST_SCALE + ST_OFFSET_K - 273.15

    valid = np.isfinite(temp_c) & (st_raw != 0)
    if st_nodata is not None:
        valid &= st_raw != st_nodata

    # Landsat 8-9 QA_PIXEL bits: dilated cloud, cirrus, cloud, shadow, snow, water.
    reject_bits = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 7)
    valid &= (qa_raw.astype("uint16") & reject_bits) == 0

    if st_uncertainty is not None:
        valid &= st_uncertainty <= st_uncertainty_k

    rows, cols = st_raw.shape
    # The crop is aligned to the thermal raster CRS, which is what we need for masks.
    city_src = shapely_transform(
        Transformer.from_crs(f"EPSG:{epsg}", source_crs, always_xy=True).transform,
        city_utm,
    )
    ring_src = shapely_transform(
        Transformer.from_crs(f"EPSG:{epsg}", source_crs, always_xy=True).transform,
        ring,
    )

    from rasterio.features import geometry_mask

    city_mask = geometry_mask([mapping(city_src)], out_shape=(rows, cols), transform=out_transform, invert=True)
    ring_mask = geometry_mask([mapping(ring_src)], out_shape=(rows, cols), transform=out_transform, invert=True)

    city_valid = valid & city_mask
    ring_valid = valid & ring_mask

    city_values = temp_c[city_valid]
    ring_values = temp_c[ring_valid]
    all_valid = valid
    clear_percent = float(all_valid.sum() / all_valid.size * 100.0)

    if city_values.size < 25 or ring_values.size < 25:
        raise RuntimeError(
            f"Not enough valid land-temperature pixels in this scene (city={city_values.size}, ring={ring_values.size})."
        )
    if clear_percent < min_clear_percent:
        raise RuntimeError(
            f"Only {clear_percent:.1f}% of the analysis footprint has usable pixels, below the {min_clear_percent:.0f}% threshold."
        )

    city_median = float(np.median(city_values))
    ring_median = float(np.median(ring_values))
    city_mean = float(np.mean(city_values))
    ring_mean = float(np.mean(ring_values))
    ring_p90 = float(np.percentile(ring_values, 90))
    city_p90 = float(np.percentile(city_values, 90))
    median_delta = city_median - ring_median
    mean_delta = city_mean - ring_mean
    hot_fraction = float(np.mean(city_values > ring_median) * 100.0)
    above_ring_p90 = float(np.mean(city_values > ring_p90) * 100.0)

    # Build a compact RGBA image for the map. High relative temperatures are red.
    display_temp = temp_c.copy()
    display_temp[~valid] = np.nan
    lo = float(np.nanpercentile(ring_values, 5))
    hi = float(np.nanpercentile(ring_values, 95))
    lo = min(lo, float(np.nanpercentile(city_values, 5)))
    hi = max(hi, float(np.nanpercentile(city_values, 95)))
    if hi <= lo:
        hi = lo + 1.0

    norm = np.clip((display_temp - lo) / (hi - lo), 0, 1)
    rgba = (colormaps["RdYlBu_r"](np.nan_to_num(norm, nan=0.0)) * 255).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 200, 0).astype(np.uint8)

    # Keep the Streamlit HTML payload manageable.
    step = max(1, ceil(max(rgba.shape[0], rgba.shape[1]) / 450))
    rgba_small = rgba[::step, ::step]
    full_bounds = array_bounds(rows, cols, out_transform)
    minx, miny, maxx, maxy = full_bounds
    map_bounds = transform_bounds(source_crs, "EPSG:4326", minx, miny, maxx, maxy, densify_pts=21)

    ring_wgs84 = shapely_transform(from_utm, ring)

    return {
        "stats": {
            "city_mean_c": city_mean,
            "city_median_c": city_median,
            "city_p90_c": city_p90,
            "ring_mean_c": ring_mean,
            "ring_median_c": ring_median,
            "ring_p90_c": ring_p90,
            "median_delta_c": median_delta,
            "mean_delta_c": mean_delta,
            "city_hot_fraction_pct": hot_fraction,
            "city_above_ring_p90_pct": above_ring_p90,
            "city_pixel_count": int(city_values.size),
            "ring_pixel_count": int(ring_values.size),
            "clear_percent": clear_percent,
        },
        "rgba_image": rgba_small,
        "map_bounds": [[map_bounds[1], map_bounds[0]], [map_bounds[3], map_bounds[2]]],
        "ring_geometry": ring_wgs84.__geo_interface__,
        "scene_date": scene.datetime.date().isoformat() if scene.datetime else "unknown",
        "platform": scene.properties.get("platform", "Landsat"),
        "cloud_cover_pct": float(scene.properties.get("eo:cloud_cover", np.nan)),
        "scene_id": scene.id,
    }


def summarize_temperatures(stats: dict) -> dict:
    return {
        "delta": stats["median_delta_c"],
        "hot_fraction": stats["city_hot_fraction_pct"],
    }
