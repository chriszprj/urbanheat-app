from __future__ import annotations


def _severity(delta_c: float) -> str:
    if delta_c < 1.0:
        return "low"
    if delta_c < 2.0:
        return "moderate"
    if delta_c < 4.0:
        return "strong"
    return "very strong"


def build_analysis_text(stats: dict, analysis: dict) -> str:
    delta = stats["median_delta_c"]
    severity = _severity(delta)
    hot_fraction = stats["city_hot_fraction_pct"]
    above_p90 = stats["city_above_ring_p90_pct"]

    if delta >= 0:
        comparison = (
            f"The city’s median land-surface temperature was {delta:.1f} °C higher than the surrounding comparison ring. "
            f"That is a {severity} snapshot of the urban heat signal under this scene."
        )
    else:
        comparison = (
            f"The city’s median land-surface temperature was {abs(delta):.1f} °C lower than the surrounding comparison ring. "
            "That means this particular satellite snapshot does not show a positive urban heat signal."
        )

    detail = (
        f"About {hot_fraction:.0f}% of analyzed city pixels were hotter than the ring median, and {above_p90:.0f}% were hotter than the ring’s 90th-percentile temperature. "
        f"The scene was acquired on {analysis['scene_date']} with about {analysis['cloud_cover_pct']:.0f}% scene-level cloud cover."
    )

    caveat = (
        "This is a land-surface-temperature comparison, not a direct measurement of outdoor air temperature or human heat stress. "
        "Results can vary with season, time of day, recent weather, land cover, water, cloud screening, and the exact city boundary. "
        "For a stronger scientific assessment, repeat the analysis across many clear scenes in the same season and summarize the distribution of the city-minus-ring difference."
    )

    return f"{comparison} {detail} {caveat}"
