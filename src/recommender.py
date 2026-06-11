"""Recommend rotary drilling rig models from structured CSV facts."""

from __future__ import annotations

try:
    from .data_loader import load_master_data
except ImportError:  # Allows direct execution of files inside src/.
    from data_loader import load_master_data


KEY_MODELS = {
    "ZR140R",
    "ZR185R",
    "ZR255R",
    "ZR300D",
    "ZR320R",
    "ZR380D",
    "ZR420GW",
}


def _parse_number(value: str) -> float:
    """Convert one structured numeric CSV value to a float."""

    return float(value.strip())


def _parse_depths(value: str) -> tuple[float, float]:
    """Return Interlock and Friction Kelly depths from one CSV value."""

    parts = [part.strip() for part in value.split("/")]
    if len(parts) == 1:
        depth = _parse_number(parts[0])
        return depth, depth
    if len(parts) == 2:
        return _parse_number(parts[0]), _parse_number(parts[1])
    raise ValueError(f"Invalid drilling depth value: {value}")


def _build_result(
    row: object,
    required_depth_m: float,
    interlock_depth: float,
    friction_depth: float,
) -> dict:
    """Build one recommendation without changing source values."""

    model = row["model"]
    return {
        "model": model,
        "is_key_model": model in KEY_MODELS,
        "required_config": (
            "Interlock Kelly"
            if interlock_depth >= required_depth_m
            else "Friction Kelly only"
        ),
        "depth_value": row["max_drilling_depth_m"],
        "diameter_value": row["max_drilling_diameter_mm"],
        "torque": row["rated_output_torque_knm"],
        "engine_model": row["engine_model"],
        "power_kw": row["power_kw"],
        "weight_t": row["weight_t"],
        "emission": row["emission"],
        "transport_width_mm": row["transport_width_mm"],
        "transport_height_mm": row["transport_height_mm"],
        "transport_length_mm": row["transport_length_mm"],
        "depth_margin": friction_depth - required_depth_m,
        "source": {
            "file": row["source_file"],
            "sheet": row["source_sheet"],
            "version": row["data_version"],
        },
    }


def recommend(
    required_depth_m: float,
    required_diameter_mm: float,
    max_results: int = 3,
) -> list[dict]:
    """Return the best structured-data matches for the customer requirement."""

    if max_results <= 0:
        return []

    matches = []
    master = load_master_data()
    for row_index, row in master.iterrows():
        try:
            interlock_depth, friction_depth = _parse_depths(
                row["max_drilling_depth_m"]
            )
            diameter = _parse_number(row["max_drilling_diameter_mm"])
        except (TypeError, ValueError):
            # Invalid or unavailable source values cannot prove suitability.
            continue

        if (
            friction_depth < required_depth_m
            or diameter < required_diameter_mm
        ):
            continue

        result = _build_result(
            row,
            required_depth_m,
            interlock_depth,
            friction_depth,
        )
        matches.append((result, row_index))

    # The acceptance cases prefer an Interlock-capable model before a
    # Friction-only model, then choose the smallest Friction depth margin.
    matches.sort(
        key=lambda item: (
            not item[0]["is_key_model"],
            item[0]["required_config"] != "Interlock Kelly",
            item[0]["depth_margin"],
            item[1],
        )
    )
    return [result for result, _ in matches[:max_results]]
