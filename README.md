# Urban Heat Mapper

A beginner-friendly Streamlit app that lets a user search for a city, select it, fetch a recent Landsat Collection 2 Level-2 scene, map land surface temperature, and compare the city against a surrounding land ring.

## What the first version does

1. Searches for cities with OpenStreetMap Nominatim.
2. Lets the user select a matching city.
3. Searches Microsoft Planetary Computer's public STAC catalog for a recent Landsat Collection 2 Level-2 scene.
4. Reads the surface temperature band and QA bands directly from cloud-optimized GeoTIFF assets.
5. Masks clouds, cirrus, cloud shadows, snow, water, and high-uncertainty surface-temperature pixels.
6. Compares the city's median land surface temperature with a 10-km surrounding land ring.
7. Renders a red-hot / blue-cool temperature layer over the map.
8. Reports several measurements, including median city temperature, median ring temperature, city-minus-ring temperature difference, and the share of city pixels above the ring median.

## Why these data sources

USGS says Landsat Collection 2 Surface Temperature measures land surface temperature in Kelvin and is useful for urban heat island studies. The Collection 2 surface-temperature values use `temperature_K = DN * 0.00341802 + 149.0` before converting to Celsius.

Microsoft Planetary Computer provides a public STAC API and hosts Landsat Collection 2 Level-2 as cloud-optimized GeoTIFFs. Its current collection exposes the thermal surface-temperature asset and the QA bands needed to screen cloudy and otherwise unusable pixels.

## Prerequisites

Install Python 3.12 or newer. Current Rasterio documentation supports Python 3.12+.

### Windows / VS Code

Open the project folder in VS Code, then open **Terminal → New Terminal**.

Create a virtual environment:

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use Command Prompt instead:

```bat
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the app:

```powershell
streamlit run app.py
```

Streamlit will print a local URL, normally `http://localhost:8501`.

## Important API note

The Nominatim public service is intended for light use. The app sends a custom User-Agent, and searches should be performed interactively rather than through an automated bulk geocoder. For a larger public deployment, move city search to a hosted geocoder or run your own geocoding service.

## How the heat calculation works

The selected city geometry is projected into a local UTM coordinate system. A surrounding ring is created by buffering the city outward (default 10 km) and subtracting the city itself.

For the selected Landsat scene, the app reads the surface-temperature band and QA_PIXEL band from cloud-optimized GeoTIFFs. Pixels flagged for dilated cloud, cirrus, cloud, cloud shadow, snow, or water are removed. Surface-temperature pixels with uncertainty above 2 K are also removed when the uncertainty band is available.

The main urban-heat metric is:

```text
urban_heat_intensity = median(city_land_surface_temperature)
                       - median(ring_land_surface_temperature)
```

This is deliberately a simple first metric. It is useful for exploration, but it is not a universal scientific threshold for the urban heat island effect.

## Recommended next upgrades

### 1. Multi-date analysis

Instead of one scene, search for 10–30 clear scenes in the same season over several years. Compute the city-minus-ring difference for every scene and report its median, range, and trend.

### 2. Land-cover-aware comparison

A better control area would match urban land with nearby non-urban land while controlling for elevation, vegetation, and water. You can add Sentinel-2 or Landsat surface reflectance to calculate NDVI and separate vegetation-heavy pixels from built-up areas.

### 3. City-to-city comparison

Create a small analysis table for many cities using the exact same date/season rules, buffer size, quality filters, and summary statistics. Then the app can show whether a selected city is hotter than the median of its peer cities.

### 4. Better urban boundaries

Nominatim's city polygons are administrative/place boundaries, which may not correspond to the physically built-up urban footprint. A later version can use a dedicated urban-area dataset for a more consistent definition of “city.”

### 5. Production deployment

For a public website, avoid depending on the public Nominatim server for heavy traffic and add caching, retries, request throttling, and a persistent data layer for already-processed scenes.

## Project layout

```text
urban_heat_mapper/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── src/
    ├── __init__.py
    ├── analysis.py
    ├── geocode.py
    └── landsat.py
```

## Data citations

- USGS Landsat Collection 2 Surface Temperature: https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature
- USGS Landsat Collection 2 Level-2 QA bands: https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
- Microsoft Planetary Computer Landsat Collection 2 Level-2: https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2
- Microsoft Planetary Computer STAC API: https://planetarycomputer.microsoft.com/api/stac/v1
- OpenStreetMap Nominatim: https://nominatim.org/release-docs/develop/api/Search/
