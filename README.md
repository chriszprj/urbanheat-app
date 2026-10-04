This Urban Heat Mapper application lets users search for a city, select it, fetch a recent Landsat Collection 2 Level-2 scene, map land surface temperature, and compare the city with a surrounding land ring.

Features of the application: 
1. Searches for cities with OpenStreetMap Nominatim.
2. Lets the user select a matching city.
3. Searches Microsoft Planetary Computer's public STAC catalog for a recent Landsat Collection 2 Level-2 scene.
4. Reads the surface temperature band and QA bands directly from cloud-optimized GeoTIFF assets.
5. Masks clouds, cirrus, cloud shadows, snow, water, and high-uncertainty surface-temperature pixels.
6. Compares the city's median land surface temperature with a 10-km surrounding land ring.
7. Renders a red-hot / blue-cool temperature layer over the map.
8. Reports several measurements, including median city temperature, median ring temperature, city-minus-ring temperature difference, and the share of city pixels above the ring median.

Technologies: Python, Streamlit, Landsat Collection 2, Microsoft Planetary Computer, STAC, and Data Analysis & Visualization Libraries
