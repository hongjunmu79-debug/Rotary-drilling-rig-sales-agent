"""Format structured lookup results for display."""

from __future__ import annotations

try:
    from .param_lookup import get_field_dictionary, get_models
except ImportError:  # Allows direct execution of files inside src/.
    from param_lookup import get_field_dictionary, get_models


def format_lookup_result(result: dict[str, str]) -> str:
    """Format one lookup result without changing or inferring its value."""

    lines = [
        f"**Model:** {result['model']}",
        (
            f"**Field:** {result['zh_name']} / {result['en_name']} "
            f"(`{result['field_key']}`)"
        ),
    ]

    if result["confidence"] == "not_available":
        lines.append(
            "**Value:** Not available in source data (recorded as N/A)"
        )
        lines.append("**Confidence:** Not available")
    else:
        lines.append(f"**Value:** {result['value']}")
        lines.append(f"**Unit:** {result['unit'] or 'No unit'}")

        is_pair = "/" in result["value"] and (
            result["data_type"] == "range_or_pair"
            or "kelly" in result["description"].casefold()
        )
        if is_pair:
            first, second = result["value"].split("/", maxsplit=1)
            lines.append(
                f"**Configuration:** {first} = Interlock Kelly, "
                f"{second} = Friction Kelly"
            )
        lines.append(
            "**Confidence:** High (exact structured table match)"
        )

    lines.append(
        "**Source:** "
        f"{result['source_file']} / {result['source_sheet']} / "
        f"{result['data_version']}"
    )
    return "\n\n".join(lines)


def format_model_not_found() -> str:
    """Tell the user which exact model codes can be selected."""

    models = ", ".join(get_models())
    return (
        "Model not recognized. Please choose one of the 15 available models:\n\n"
        f"{models}"
    )


def format_fields_not_found(model: str) -> str:
    """List all structured fields available for a recognized model."""

    field_dictionary = get_field_dictionary()
    field_lines = []
    for _, row in field_dictionary.iterrows():
        unit = f" [{row['unit']}]" if row["unit"] else ""
        field_lines.append(
            f"- {row['zh_name']} / {row['en_name']}{unit} "
            f"(`{row['field_key']}`)"
        )

    return (
        f"No parameter field was recognized for {model}. "
        "Available fields are:\n\n"
        + "\n".join(field_lines)
    )
