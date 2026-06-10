import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "rotary_rig_model_cards.jsonl"
DICTIONARY_PATH = (
    PROJECT_ROOT / "data" / "processed" / "rotary_rig_field_dictionary.csv"
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "rotary_rig_model_cards.md"
SOURCE_LINE = (
    "Source: Zoomlion_Brochure_Data.xlsx / 旋挖钻机 Rotary Drilling Rig / "
    "v0_2026-06-11"
)


def load_field_names() -> dict[str, str]:
    with DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as csv_file:
        return {
            row["field_key"]: row["en_name"]
            for row in csv.DictReader(csv_file)
        }


def format_value(field_key: str, value: object, unit: str | None) -> str:
    formatted = str(value)
    if unit:
        formatted += f" {unit}"
    if "/" in str(value):
        formatted += " (Interlock Kelly / Friction Kelly configurations)"
    if field_key == "swing_radius_mm" and str(value).upper() == "N/A":
        formatted += " (not available in source data)"
    return formatted


def format_card(card: dict[str, object], field_names: dict[str, str]) -> str:
    model = card["model"]
    category = card["category"]
    key_model = "yes" if card["is_key_model"] else "no"
    specs = card["specs"]
    units = card["units"]

    lines = [
        f"# Zoomlion {model} Rotary Drilling Rig",
        f"Category: {category}",
        f"Key model: {key_model}",
    ]
    for field_key, value in specs.items():
        en_name = field_names[field_key]
        lines.append(
            f"- {en_name} ({field_key}): "
            f"{format_value(field_key, value, units.get(field_key))}"
        )
    lines.append(SOURCE_LINE)
    return "\n".join(lines)


def main() -> None:
    field_names = load_field_names()
    with INPUT_PATH.open(encoding="utf-8") as jsonl_file:
        cards = [json.loads(line) for line in jsonl_file if line.strip()]

    output = "\n---\n".join(format_card(card, field_names) for card in cards) + "\n"
    OUTPUT_PATH.write_text(output, encoding="utf-8", newline="\n")
    print(f"Exported {len(cards)} model cards to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
