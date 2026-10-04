import streamlit as st
import folium
from streamlit_folium import st_folium

from src.analysis import build_analysis_text
from src.geocode import search_cities
from src.landsat import analyze_city_heat, find_candidate_scenes

st.set_page_config(page_title="Urban Heat Mapper", page_icon="🌡️", layout="wide")

st.title("Urban Heat Mapper")
st.caption("Explore satellite-derived land surface temperature and compare a city with its surrounding area.")

with st.sidebar:
    st.header("Analysis settings")
    days_back = st.slider("Look back (days)", min_value=30, max_value=1095, value=730, step=30)
    max_cloud = st.slider("Maximum scene cloud cover (%)", min_value=5, max_value=80, value=40, step=5)
    buffer_km = st.slider("Surrounding comparison ring (km)", min_value=2, max_value=25, value=10, step=1)
    min_clear = st.slider("Minimum clear land pixels (%)", min_value=10, max_value=95, value=30, step=5)
    st.divider()
    st.caption("Data: USGS Landsat Collection 2 Level-2 via Microsoft Planetary Computer. City search: OpenStreetMap Nominatim.")

query = st.text_input("Search for a city", placeholder="Try: Phoenix, New York, Tokyo, Nairobi")

if query:
    with st.spinner("Finding matching cities…"):
        try:
            results = search_cities(query, limit=8)
        except Exception as exc:
            st.error(f"City search failed: {exc}")
            results = []

    if not results:
        st.warning("No city matches were found. Try adding a country or state, such as “Austin, Texas”.")
    else:
        labels = [r["label"] for r in results]
        choice = st.selectbox("Choose a city", labels)
        selected = results[labels.index(choice)]

        st.write(f"**Selected:** {selected['label']}")
        st.write(f"Coordinates: {selected['lat']:.4f}, {selected['lon']:.4f}")

        if st.button("Analyze urban heat", type="primary", use_container_width=True):
            with st.spinner("Searching Landsat scenes and calculating temperatures…"):
                try:
                    candidates = find_candidate_scenes(
                        city_geometry=selected["geometry"],
                        days_back=days_back,
                        max_cloud=max_cloud,
                        limit=10,
                    )
                    analysis = None
                    failures = []
                    for scene in candidates:
                        try:
                            analysis = analyze_city_heat(
                                city_geometry=selected["geometry"],
                                scene=scene,
                                buffer_km=buffer_km,
                                min_clear_percent=min_clear,
                            )
                            break
                        except RuntimeError as scene_exc:
                            failures.append(f"{scene.id}: {scene_exc}")

                    if analysis is None:
                        detail = failures[-1] if failures else "No candidate scene could be analyzed."
                        raise RuntimeError(
                            "No qualifying Landsat scene had enough usable land-temperature pixels for a stable city/ring comparison. "
                            f"Last attempt: {detail} Try increasing the look-back window, raising the cloud threshold, or lowering the minimum clear-pixel setting."
                        )
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")
                    st.stop()

            st.session_state["analysis"] = analysis
            st.session_state["selected_city"] = selected

analysis = st.session_state.get("analysis")
selected_city = st.session_state.get("selected_city")

if analysis and selected_city:
    stats = analysis["stats"]
    m = folium.Map(
        location=[selected_city["lat"], selected_city["lon"]],
        zoom_start=10,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.GeoJson(
        selected_city["geometry"],
        name="City boundary",
        style_function=lambda _: {
            "color": "#222222",
            "weight": 2,
            "fillOpacity": 0.0,
        },
    ).add_to(m)

    folium.GeoJson(
        analysis["ring_geometry"],
        name="10-km comparison ring",
        style_function=lambda _: {
            "color": "#555555",
            "weight": 1,
            "dashArray": "5, 5",
            "fillOpacity": 0.0,
        },
    ).add_to(m)

    folium.raster_layers.ImageOverlay(
        image=analysis["rgba_image"],
        bounds=analysis["map_bounds"],
        opacity=0.72,
        interactive=True,
        cross_origin=False,
        zindex=2,
        name="Surface temperature",
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Surface temperature map")
        st_folium(m, width=None, height=640, returned_objects=[])
    with right:
        st.subheader("Results")
        st.metric("City median", f"{stats['city_median_c']:.1f} °C")
        st.metric("Comparison median", f"{stats['ring_median_c']:.1f} °C")
        st.metric("Urban heat intensity", f"{stats['median_delta_c']:+.1f} °C")
        st.metric("City area hotter than ring median", f"{stats['city_hot_fraction_pct']:.0f}%")
        st.caption(
            f"Scene: {analysis['scene_date']} · Landsat {analysis['platform']} · "
            f"scene cloud cover {analysis['cloud_cover_pct']:.1f}%"
        )

    st.subheader("Interpretation")
    st.info(build_analysis_text(stats, analysis))

    with st.expander("Technical details"):
        st.write(
            "The app scales the Landsat Collection 2 surface-temperature band to Kelvin, converts to Celsius, "
            "masks cloud/shadow/snow/water pixels using QA_PIXEL, masks high-uncertainty ST pixels, "
            "then compares land pixels inside the city geometry against a surrounding ring. "
            "The app tries multiple qualifying Landsat 8/9 scenes when an individual scene does not contain enough usable pixels."
        )
        st.write(
            f"Clear land coverage inside the comparison footprint: {stats['clear_percent']:.1f}% of pixels. "
            f"City pixels analyzed: {stats['city_pixel_count']:,}; ring pixels analyzed: {stats['ring_pixel_count']:,}."
        )
else:
    st.info("Search for a city, select a result, then choose “Analyze urban heat” to run the satellite analysis.")
