"""Day 3 Streamlit app: structured CSV lookup only, with no LLM."""

from __future__ import annotations

import streamlit as st

from src.answer_generator import (
    format_fields_not_found,
    format_lookup_result,
    format_model_not_found,
)
from src.param_lookup import (
    find_fields,
    find_model,
    get_field_dictionary,
    get_models,
    lookup,
)
from src.recommender import recommend
from src.reply_generator import generate_reply


KEY_MODELS = {
    "ZR140R",
    "ZR185R",
    "ZR255R",
    "ZR300D",
    "ZR320R",
    "ZR380D",
    "ZR420GW",
}


def answer_free_text(query: str) -> list[str]:
    """Resolve free text to one or more exact structured lookup answers."""

    model = find_model(query)
    if model is None:
        return [format_model_not_found()]

    field_keys = find_fields(query)
    if not field_keys:
        return [format_fields_not_found(model)]

    return [format_lookup_result(lookup(model, key)) for key in field_keys]


def field_option_label(field_key: str, labels: dict[str, str]) -> str:
    return labels[field_key]


def render_sidebar(models: list[str], data_version: str) -> None:
    st.sidebar.header("Data")
    st.sidebar.write(f"Version: `{data_version}`")
    st.sidebar.write("Available models (★ = key model):")
    for model in models:
        marker = "★" if model in KEY_MODELS else "•"
        st.sidebar.write(f"{marker} {model}")


def _recommendation_table(item: dict) -> list[dict[str, str]]:
    """Build a compact parameter table for one recommendation card."""

    return [
        {"Parameter": "Max drilling depth (m)", "Value": item["depth_value"]},
        {
            "Parameter": "Max drilling diameter (mm)",
            "Value": item["diameter_value"],
        },
        {"Parameter": "Rated output torque (kN.m)", "Value": item["torque"]},
        {"Parameter": "Engine model", "Value": item["engine_model"]},
        {"Parameter": "Power (kW)", "Value": item["power_kw"]},
        {"Parameter": "Weight (t)", "Value": item["weight_t"]},
        {"Parameter": "Emission", "Value": item["emission"]},
        {
            "Parameter": "Transport L/W/H (mm)",
            "Value": (
                f"{item['transport_length_mm']} / "
                f"{item['transport_width_mm']} / "
                f"{item['transport_height_mm']}"
            ),
        },
    ]


def _full_friction_depth_range() -> tuple[float, float]:
    """Return the full product-line Friction Kelly depth range."""

    all_models = recommend(0, 0, max_results=100)
    friction_depths = [
        float(item["depth_value"].split("/")[-1]) for item in all_models
    ]
    return min(friction_depths), max(friction_depths)


def render_recommendation_section() -> None:
    """Render Day 4 model recommendation and customer reply controls."""

    st.divider()
    st.header("Model Recommendation")
    st.caption(
        "Recommendations use structured CSV specifications only. "
        "Customer replies use DeepSeek when configured and a safe template "
        "otherwise."
    )

    depth_col, diameter_col = st.columns(2)
    with depth_col:
        required_depth = st.number_input(
            "Required depth (m)",
            min_value=0.0,
            value=40.0,
            step=1.0,
        )
    with diameter_col:
        required_diameter = st.number_input(
            "Required diameter (mm)",
            min_value=0.0,
            value=1300.0,
            step=100.0,
        )

    project_type = st.text_input("Project type (optional)")
    language_label = st.selectbox(
        "Reply language",
        ["English", "Arabic", "Both"],
    )
    language_codes = {"English": "en", "Arabic": "ar", "Both": "both"}

    if st.button("Recommend", type="primary"):
        st.session_state["recommendation_results"] = recommend(
            required_depth,
            required_diameter,
        )
        st.session_state["recommendation_request"] = {
            "required_depth_m": required_depth,
            "required_diameter_mm": required_diameter,
            "project_type": project_type.strip(),
            "market": "",
            "language": language_codes[language_label],
        }
        st.session_state["generated_replies"] = {}

    if "recommendation_results" not in st.session_state:
        return

    results = st.session_state["recommendation_results"]
    request_facts = st.session_state["recommendation_request"]
    if not results:
        minimum, maximum = _full_friction_depth_range()
        st.warning(
            "No model meets both requirements. "
            f"The full product-line Friction Kelly depth range is "
            f"{minimum:g}-{maximum:g} m."
        )
        return

    for index, item in enumerate(results):
        with st.container(border=True):
            key_marker = "Key model" if item["is_key_model"] else "Standard model"
            st.subheader(f"{index + 1}. {item['model']} ({key_marker})")
            st.table(_recommendation_table(item))
            st.write(f"**Required configuration:** {item['required_config']}")
            st.write(f"**Friction-depth margin:** {item['depth_margin']:g} m")
            source = item["source"]
            st.write(
                "**Source:** "
                f"{source['file']} / {source['sheet']} / {source['version']}"
            )
            st.warning("Sales reference only, confirm with engineers")

            if st.button(
                "Generate customer reply",
                key=f"generate_reply_{index}_{item['model']}",
            ):
                facts = {**item, **request_facts}
                customer_context = request_facts["project_type"]
                st.session_state["generated_replies"][item["model"]] = (
                    generate_reply(
                        facts,
                        request_facts["language"],
                        customer_context,
                    )
                )

            reply = st.session_state["generated_replies"].get(item["model"])
            if reply:
                mode_label = "LLM" if reply["mode"] == "llm" else "Template"
                st.caption(f"Generation mode: {mode_label}")
                st.text(reply["reply_text"])
                if reply["note"]:
                    st.caption(reply["note"])


def main() -> None:
    st.set_page_config(page_title="Zoomlion Rotary Rig Lookup", layout="wide")
    st.title(
        "Zoomlion Rotary Drilling Rig AI Sales Assistant "
        "(v0 — Structured Lookup)"
    )
    st.caption(
        "All answers come directly from the structured CSV tables. "
        "This version does not use an LLM."
    )

    models = get_models()
    field_dictionary = get_field_dictionary()
    data_version = lookup(models[0], "model")["data_version"]
    render_sidebar(models, data_version)

    query = st.text_input(
        "Ask by model and parameter",
        placeholder="What is the max drilling depth of ZR255R?",
    )
    if st.button("Search text", type="primary"):
        if query.strip():
            for answer in answer_free_text(query):
                st.markdown(answer)
                st.divider()
        else:
            st.warning("Enter a model and parameter, or use the dropdowns below.")

    st.subheader("Dropdown lookup")
    labels = {
        row["field_key"]: (
            f"{row['zh_name']} / {row['en_name']}"
            + (f" ({row['unit']})" if row["unit"] else "")
        )
        for _, row in field_dictionary.iterrows()
    }
    selected_model = st.selectbox("Model", models)
    selected_field = st.selectbox(
        "Field",
        field_dictionary["field_key"].tolist(),
        format_func=lambda key: field_option_label(key, labels),
    )

    if st.button("Lookup selected field"):
        st.markdown(format_lookup_result(lookup(selected_model, selected_field)))

    render_recommendation_section()


if __name__ == "__main__":
    main()
