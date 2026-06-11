"""Load and validate the structured rotary drilling rig CSV data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_CSV = PROJECT_ROOT / "data" / "processed" / "rotary_rig_master.csv"
FIELD_DICTIONARY_CSV = (
    PROJECT_ROOT / "data" / "processed" / "rotary_rig_field_dictionary.csv"
)

EXPECTED_MODEL_COUNT = 15
MASTER_REQUIRED_COLUMNS = {
    "model",
    "source_file",
    "source_sheet",
    "data_version",
}
DICTIONARY_REQUIRED_COLUMNS = {
    "field_key",
    "zh_name",
    "en_name",
    "unit",
    "data_type",
    "description",
}


def _read_csv(path: Path) -> pd.DataFrame:
    """Read every cell as text and preserve literal values such as N/A."""

    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")

    try:
        return pd.read_csv(
            path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )
    except Exception as exc:
        raise ValueError(f"Failed to read CSV file {path}: {exc}") from exc


def _validate_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    file_label: str,
) -> None:
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(
            f"{file_label} is missing required columns: {', '.join(missing)}"
        )


def load_master_data() -> pd.DataFrame:
    """Load the 15-model master table after validating its basic contract."""

    frame = _read_csv(MASTER_CSV)
    _validate_columns(frame, MASTER_REQUIRED_COLUMNS, "Master CSV")

    if len(frame) != EXPECTED_MODEL_COUNT:
        raise ValueError(
            "Master CSV must contain exactly "
            f"{EXPECTED_MODEL_COUNT} model rows; found {len(frame)}."
        )
    if frame["model"].eq("").any():
        raise ValueError("Master CSV contains an empty model code.")
    if frame["model"].duplicated().any():
        duplicates = sorted(frame.loc[frame["model"].duplicated(), "model"].unique())
        raise ValueError(
            f"Master CSV contains duplicate model codes: {', '.join(duplicates)}"
        )

    return frame


def load_field_dictionary() -> pd.DataFrame:
    """Load the field dictionary and verify that every field exists in master."""

    frame = _read_csv(FIELD_DICTIONARY_CSV)
    _validate_columns(frame, DICTIONARY_REQUIRED_COLUMNS, "Field dictionary CSV")

    if frame["field_key"].eq("").any():
        raise ValueError("Field dictionary CSV contains an empty field_key.")
    if frame["field_key"].duplicated().any():
        duplicates = sorted(
            frame.loc[frame["field_key"].duplicated(), "field_key"].unique()
        )
        raise ValueError(
            "Field dictionary CSV contains duplicate field keys: "
            f"{', '.join(duplicates)}"
        )

    master_columns = set(load_master_data().columns)
    unknown_fields = sorted(set(frame["field_key"]) - master_columns)
    if unknown_fields:
        raise ValueError(
            "Field dictionary contains fields not present in master CSV: "
            f"{', '.join(unknown_fields)}"
        )

    return frame


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the validated master table and field dictionary."""

    master = load_master_data()
    field_dictionary = load_field_dictionary()
    return master, field_dictionary
