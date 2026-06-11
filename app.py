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


if __name__ == "__main__":
    main()
