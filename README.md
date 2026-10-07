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

Technologies:
The application uses OpenStreetMap Nominatim for city search and geographic location information.

Satellite imagery is obtained from the USGS Landsat Collection 2 Level-2 dataset through the Microsoft Planetary Computer STAC API.

Landsat Collection 2 Level-2 provides surface temperature products that can be used to study the thermal characteristics of the Earth's surface. The application uses Landsat 8/Landsat 9 scenes when suitable data are available.

Analysis:
1) City Search and Boundary Retrieval: The user enters a city name, and the application uses OpenStreetMap Nominatim to search for matching locations. The selected result provides the geographic coordinates and city boundary used for the analysis.
2) Landsat Scene Search: The application searches the Microsoft Planetary Computer STAC catalog for Landsat 8 and Landsat 9 scenes that intersect the selected city. Scenes are filtered using a configurable date window and maximum cloud-cover threshold. Multiple candidate scenes can be tested so that one poor-quality scene does not automatically prevent the analysis.
3) Surface Temperature Calculation: The application reads the Landsat surface-temperature raster and converts the stored digital-number values into temperature in Celsius using the Landsat Collection 2 surface-temperature scale and offset.
4) Quality Filtering: Landsat quality-assessment information is used to remove pixels affected by clouds, cirrus, cloud shadows, snow, water, missing data, and other unreliable observations. Surface-temperature uncertainty is also used to exclude pixels with excessive uncertainty.
5) City and Surrounding Area Comparison: A surrounding comparison ring is created outside the selected city boundary. By default, this ring extends 10 kilometers from the city boundary. Surface temperatures are calculated separately for the city and the surrounding land area.
6) Urban Heat Intensity: The application calculates the difference between the city's median surface temperature and the surrounding area's median surface temperature:

Urban Heat Intensity = City Median Surface Temperature - Surrounding Median Surface Temperature

A positive value indicates that the city has a higher median land surface temperature than the surrounding comparison area for the analyzed satellite scene.

7) Additional Heat Statistics: The application also calculates mean surface temperature, 90th-percentile temperature, the percentage of city pixels hotter than the surrounding median, and the percentage of city pixels hotter than the surrounding area's 90th percentile.
