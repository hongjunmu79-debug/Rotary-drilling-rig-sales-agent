"""Pure-Python assertions for the Day 3 structured lookup."""

from __future__ import annotations

from answer_generator import format_lookup_result, format_model_not_found
from param_lookup import find_fields, find_model, get_models, lookup


def run_tests() -> None:
    depth = lookup("ZR255R", "max_drilling_depth_m")
    assert depth["value"] == "56/70"
    assert depth["confidence"] == "exact_match"
    assert (
        "56 = Interlock Kelly, 70 = Friction Kelly"
        in format_lookup_result(depth)
    )

    swing_radius = lookup("ZR380D", "swing_radius_mm")
    assert swing_radius["value"] == "N/A"
    assert swing_radius["confidence"] == "not_available"
    na_answer = format_lookup_result(swing_radius)
    assert "Not available in source data (recorded as N/A)" in na_answer

    torque = lookup("ZR600GW", "rated_output_torque_knm")
    assert torque["value"] == "600"

    assert find_fields("ZR600GW的最大输出扭矩是多少？") == [
        "rated_output_torque_knm"
    ]
    assert find_fields("最大钻孔直径") == ["max_drilling_diameter_mm"]
    assert find_fields("ZR255R 钻深") == ["max_drilling_depth_m"]
    assert find_fields("ZR140 扭矩") == ["rated_output_torque_knm"]

    assert "max_drilling_depth_m" in find_fields("ZR255R 的钻深是多少？")
    assert "max_drilling_depth_m" in find_fields(
        "What is the drilling depth of ZR255R?"
    )
    assert "max_drilling_depth_m" in find_fields(
        "ZR255R max_drilling_depth_m"
    )
    assert find_fields("What is the engine model of ZR255R?") == [
        "engine_model"
    ]

    assert find_model("please show zr140r specifications") == "ZR140R"

    assert find_model("ZR999 unknown model") is None
    assert find_fields("ZR255R warranty period") == []
    friendly_answer = format_model_not_found()
    assert "Model not recognized" in friendly_answer
    assert all(model in friendly_answer for model in get_models())

    print("All structured lookup tests passed.")


if __name__ == "__main__":
    run_tests()
