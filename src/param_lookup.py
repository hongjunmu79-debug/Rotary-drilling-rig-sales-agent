"""Structured model and parameter lookup with no LLM or inferred values."""

from __future__ import annotations

from functools import lru_cache
import re

import pandas as pd

try:
    from .data_loader import load_data
except ImportError:  # Allows direct execution of files inside src/.
    from data_loader import load_data


@lru_cache(maxsize=1)
def _tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_data()


def get_models() -> list[str]:
    """Return all model codes in their master-table order."""

    master, _ = _tables()
    return master["model"].tolist()


def get_field_dictionary() -> pd.DataFrame:
    """Return a copy so UI code cannot mutate the cached dictionary."""

    _, field_dictionary = _tables()
    return field_dictionary.copy()


def find_model(query: str) -> str | None:
    """Find a model code in free text, case-insensitively."""

    normalized_query = query.upper()
    # Longest first prevents a shorter code from winning inside a longer code.
    for model in sorted(get_models(), key=len, reverse=True):
        pattern = rf"(?<![A-Z0-9]){re.escape(model.upper())}(?![A-Z0-9])"
        if re.search(pattern, normalized_query):
            return model
    return None


def _normalize_latin(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match complete normalized words instead of arbitrary substrings."""

    return f" {phrase} " in f" {text} "


def _matches_english_name(query_latin: str, en_name: str) -> bool:
    """Match a full English name or a meaningful trailing sub-phrase."""

    normalized_name = _normalize_latin(en_name)
    if not normalized_name:
        return False
    if _contains_phrase(query_latin, normalized_name):
        return True

    words = normalized_name.split()
    if len(words) == 1:
        return _contains_phrase(query_latin, words[0])

    # Trailing phrases support "drilling depth" and "output torque" while
    # avoiding broad prefixes such as "max drilling".
    for start in range(1, len(words) - 1):
        phrase = " ".join(words[start:])
        if _contains_phrase(query_latin, phrase):
            return True
    return False


def _contains_ordered_chars(short_text: str, full_text: str) -> bool:
    """Return True when all characters occur in order in the full text."""

    position = 0
    for char in short_text:
        position = full_text.find(char, position)
        if position == -1:
            return False
        position += 1
    return True


def _matches_chinese_name(query: str, zh_name: str) -> bool:
    """Support compact phrases such as '钻深' for '最大钻孔深度'."""

    distinctive_chars = set(zh_name.replace("最大", ""))
    for chinese_run in re.findall(r"[\u4e00-\u9fff]+", query):
        # Check short pieces from the sentence instead of treating the whole
        # sentence as an abbreviation.
        for length in range(2, min(len(chinese_run), len(zh_name)) + 1):
            for start in range(len(chinese_run) - length + 1):
                piece = chinese_run[start : start + length]
                if (
                    any(char in distinctive_chars for char in piece)
                    and _contains_ordered_chars(piece, zh_name)
                ):
                    return True
    return False


def _field_matches(query: str, field: pd.Series) -> bool:
    query_latin = _normalize_latin(query)
    zh_name = field["zh_name"].strip()

    latin_match = _matches_english_name(
        query_latin,
        field["en_name"],
    )
    return latin_match or (zh_name != "" and _matches_chinese_name(query, zh_name))


def find_fields(query: str) -> list[str]:
    """Find all dictionary fields mentioned in the user query."""

    _, field_dictionary = _tables()
    query_latin = _normalize_latin(query)

    # An explicit field_key is unambiguous and must not trigger nearby names.
    explicit_rows = [
        row
        for _, row in field_dictionary.iterrows()
        if (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(row['field_key'])}(?![a-z0-9_])",
                query,
                flags=re.IGNORECASE,
            )
            or _contains_phrase(
                query_latin,
                _normalize_latin(row["field_key"]),
            )
        )
    ]
    if explicit_rows:
        explicit_keys = []
        normalized_keys = [
            _normalize_latin(row["field_key"]) for row in explicit_rows
        ]
        for row, normalized_key in zip(explicit_rows, normalized_keys):
            is_part_of_more_specific_key = any(
                other_key != normalized_key
                and _contains_phrase(other_key, normalized_key)
                for other_key in normalized_keys
            )
            if not is_part_of_more_specific_key:
                explicit_keys.append(row["field_key"])
        return explicit_keys

    exact_chinese_rows = [
        row
        for _, row in field_dictionary.iterrows()
        if row["zh_name"].strip() != "" and row["zh_name"].strip() in query
    ]
    if exact_chinese_rows:
        exact_keys = []
        exact_names = [row["zh_name"].strip() for row in exact_chinese_rows]
        for row, zh_name in zip(exact_chinese_rows, exact_names):
            is_part_of_more_specific_name = any(
                len(other_name) > len(zh_name) and zh_name in other_name
                for other_name in exact_names
            )
            if not is_part_of_more_specific_name:
                exact_keys.append(row["field_key"])
        return exact_keys

    matched_rows = [
        row
        for _, row in field_dictionary.iterrows()
        if _field_matches(query, row)
    ]

    # Prefer "Engine Model" over the generic one-word field "Model".
    multiword_names = [
        set(_normalize_latin(row["en_name"]).split())
        for row in matched_rows
        if len(_normalize_latin(row["en_name"]).split()) > 1
    ]
    results = []
    for row in matched_rows:
        name_words = _normalize_latin(row["en_name"]).split()
        if len(name_words) == 1 and any(
            name_words[0] in words for words in multiword_names
        ):
            continue
        results.append(row["field_key"])
    return results


def lookup(model: str, field_key: str) -> dict[str, str]:
    """Return one exact value and its metadata from the two CSV tables."""

    master, field_dictionary = _tables()

    model_rows = master.loc[master["model"].str.casefold() == model.casefold()]
    if model_rows.empty:
        raise ValueError(f"Unknown model: {model}")

    field_rows = field_dictionary.loc[
        field_dictionary["field_key"].str.casefold() == field_key.casefold()
    ]
    if field_rows.empty:
        raise ValueError(f"Unknown field_key: {field_key}")

    canonical_field_key = field_rows.iloc[0]["field_key"]
    if canonical_field_key not in master.columns:
        raise ValueError(
            f"Field {canonical_field_key} is not available in the master CSV."
        )

    model_row = model_rows.iloc[0]
    field_row = field_rows.iloc[0]
    value = model_row[canonical_field_key]
    confidence = (
        "not_available" if value.strip().upper() == "N/A" else "exact_match"
    )

    return {
        "model": model_row["model"],
        "field_key": canonical_field_key,
        "zh_name": field_row["zh_name"],
        "en_name": field_row["en_name"],
        "value": value,
        "unit": field_row["unit"],
        "data_type": field_row["data_type"],
        "description": field_row["description"],
        "source_file": model_row["source_file"],
        "source_sheet": model_row["source_sheet"],
        "data_version": model_row["data_version"],
        "confidence": confidence,
    }
