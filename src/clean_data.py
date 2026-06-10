"""清洗中联重科旋挖钻机产品数据并生成可追溯的数据文件。

正常项目环境使用 pandas + openpyxl 读取 Excel。为了让脚本也能在没有安装
第三方依赖的受限环境中完成数据验收，文件末尾保留了一个只读 XLSX 兼容方案；
它不会修改原始工作簿。
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from posixpath import join as posix_join
from posixpath import normpath
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile

try:
    import pandas as pd
    from openpyxl import load_workbook
except ModuleNotFoundError:
    pd = None
    load_workbook = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = PROJECT_ROOT / "data" / "raw" / "Zoomlion_Brochure_Data.xlsx"
SOURCE_SHEET = "旋挖钻机 Rotary Drilling Rig"
SOURCE_FILE_NAME = SOURCE_FILE.name
DATA_VERSION = "v0_2026-06-11"

MASTER_FILE = PROJECT_ROOT / "data" / "processed" / "rotary_rig_master.csv"
DICTIONARY_FILE = (
    PROJECT_ROOT / "data" / "processed" / "rotary_rig_field_dictionary.csv"
)
MODEL_CARDS_FILE = (
    PROJECT_ROOT / "data" / "processed" / "rotary_rig_model_cards.jsonl"
)
REPORT_FILE = PROJECT_ROOT / "docs" / "data_cleaning_report.md"

FIELD_KEYS = [
    "category",
    "model",
    "crowd_mode",
    "max_drilling_diameter_mm",
    "max_drilling_depth_m",
    "rated_output_torque_knm",
    "rotation_speed_rpm",
    "crowd_force_kn",
    "line_pull_kn",
    "stroke_mm",
    "main_winch_pull_kn",
    "main_winch_rope_diameter_mm",
    "main_winch_speed_m_min",
    "aux_winch_pull_kn",
    "aux_rope_diameter_mm",
    "aux_speed_m_min",
    "engine_model",
    "power_kw",
    "capacity_l",
    "emission",
    "track_ext_width_mm",
    "track_shoe_width_mm",
    "crawler_length_mm",
    "swing_radius_mm",
    "weight_t",
    "height_mm",
    "transport_width_mm",
    "transport_height_mm",
    "transport_length_mm",
    "interlock_kelly",
    "friction_kelly",
]

EXPECTED_MODELS = [
    "ZR140",
    "ZR160L",
    "ZR185H",
    "ZR225",
    "ZR255H",
    "ZR300L",
    "ZR360L",
    "ZR140R",
    "ZR185R",
    "ZR255R",
    "ZR300D",
    "ZR320R",
    "ZR380D",
    "ZR420GW",
    "ZR600GW",
]

KEY_MODELS = {
    "ZR140R",
    "ZR185R",
    "ZR255R",
    "ZR300D",
    "ZR320R",
    "ZR380D",
    "ZR420GW",
}

RANGE_OR_PAIR_FIELDS = {
    "max_drilling_depth_m",
    "rotation_speed_rpm",
    "height_mm",
    "transport_height_mm",
}

TEXT_FIELDS = {
    "category",
    "model",
    "crowd_mode",
    "engine_model",
    "emission",
    "interlock_kelly",
    "friction_kelly",
}

DESCRIPTIONS = {
    "category": "设备加压方式分类，保留中文和英文并规范为单行文本。",
    "model": "产品型号，是每条产品记录的唯一标识。",
    "crowd_mode": "英文加压方式；与 category 语义重复，按原表保留。",
    "max_drilling_diameter_mm": "最大钻孔直径。",
    "max_drilling_depth_m": (
        "最大钻孔深度。斜杠分隔的两个值通常对应机锁杆/摩阻杆"
        "（Interlock/Friction Kelly）不同配置，不可随意拆解。"
    ),
    "rated_output_torque_knm": "动力头最大额定输出扭矩。",
    "rotation_speed_rpm": "动力头转速范围，连字符两侧为范围边界。",
    "crowd_force_kn": "加压系统可施加的最大向下压力。",
    "line_pull_kn": "加压系统可提供的最大起拔力。",
    "stroke_mm": "加压系统的最大行程。",
    "main_winch_pull_kn": "主卷扬最大拉力。",
    "main_winch_rope_diameter_mm": "主卷扬钢丝绳直径。",
    "main_winch_speed_m_min": "主卷扬钢丝绳速度。",
    "aux_winch_pull_kn": "副卷扬最大拉力。",
    "aux_rope_diameter_mm": "副卷扬钢丝绳直径。",
    "aux_speed_m_min": "副卷扬钢丝绳速度。",
    "engine_model": "发动机品牌及型号。",
    "power_kw": "发动机额定功率。",
    "capacity_l": "发动机排量。",
    "emission": "发动机排放阶段。",
    "track_ext_width_mm": "履带完全展开时的整机宽度。",
    "track_shoe_width_mm": "单侧履带板宽度。",
    "crawler_length_mm": "履带总长度。",
    "swing_radius_mm": "设备回转半径；N/A 表示原资料未提供可用数值。",
    "weight_t": (
        "整机工作质量。如出现斜杠组合值，两个值通常对应机锁杆/摩阻杆"
        "（Interlock/Friction Kelly）不同配置，不可随意拆解。"
    ),
    "height_mm": "设备工作状态整机高度；斜杠组合值按原资料整体保留。",
    "transport_width_mm": "设备运输状态宽度。",
    "transport_height_mm": "设备运输状态高度；斜杠组合值按原资料整体保留。",
    "transport_length_mm": "设备运输状态长度。",
    "interlock_kelly": (
        "机锁式钻杆规格代号，例如 J355-4×10。ZR225 的 J419-4×14m "
        "中 m 后缀表示单位米，数据保留原样。"
    ),
    "friction_kelly": (
        "摩阻式钻杆规格代号，例如 M355-5×10。ZR225 的 M419-5×14m "
        "中 m 后缀表示单位米，数据保留原样。"
    ),
}

REQUIRED_FIELDS = [
    "max_drilling_diameter_mm",
    "max_drilling_depth_m",
    "rated_output_torque_knm",
    "engine_model",
    "power_kw",
    "weight_t",
]


def normalize_category(value: Any) -> Any:
    """把分类中的换行和多余空白压缩成一个空格。"""

    if not isinstance(value, str):
        return value
    return " ".join(value.split())


def is_missing(value: Any) -> bool:
    """统一判断真正的空值；字符串 N/A 不是空单元格。"""

    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, float):
        return math.isnan(value)
    return False


def to_plain_value(value: Any) -> Any:
    """把 pandas/numpy 标量转换成 json 可以直接写出的 Python 类型。"""

    if is_missing(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def parse_header(header: str) -> tuple[str, str, str]:
    """从“中文名(单位)+换行+英文名”中拆出中英文名和单位。"""

    lines = [line.strip() for line in str(header).splitlines() if line.strip()]
    first_line = lines[0]
    unit_match = re.search(r"[\(（]([^()（）]+)[\)）]", first_line)
    unit = unit_match.group(1).strip() if unit_match else ""
    zh_name = re.sub(r"[\(（][^()（）]+[\)）]", "", first_line).strip()

    if len(lines) > 1:
        en_name = " ".join(lines[1:])
    else:
        # 前三列表头没有换行，用中文与英文之间的空格分隔。
        name_match = re.match(r"^(.*?)\s+([A-Za-z].*)$", zh_name)
        if not name_match:
            raise ValueError(f"无法解析表头: {header!r}")
        zh_name, en_name = name_match.group(1).strip(), name_match.group(2).strip()

    return zh_name, en_name, unit


def read_with_pandas_openpyxl() -> tuple[list[str], Any]:
    """使用指定的 pandas + openpyxl 读取并验证目标 sheet。"""

    assert pd is not None and load_workbook is not None

    workbook = load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    try:
        if workbook.sheetnames[0] != SOURCE_SHEET:
            raise ValueError(
                f"第一个 sheet 应为 {SOURCE_SHEET!r}，实际为 {workbook.sheetnames[0]!r}"
            )
        worksheet = workbook[SOURCE_SHEET]
        headers = [cell.value for cell in worksheet[1]]
    finally:
        workbook.close()

    frame = pd.read_excel(
        SOURCE_FILE,
        sheet_name=SOURCE_SHEET,
        header=0,
        dtype=object,
        engine="openpyxl",
    )
    return [str(header) for header in headers], frame


def column_number(cell_reference: str) -> int:
    """把 A、B、AA 这样的 Excel 列名转换为从 0 开始的列序号。"""

    letters = re.match(r"[A-Z]+", cell_reference)
    if not letters:
        raise ValueError(f"无效的 Excel 单元格坐标: {cell_reference}")
    result = 0
    for letter in letters.group(0):
        result = result * 26 + ord(letter) - ord("A") + 1
    return result - 1


def parse_number(raw_value: str) -> int | float:
    """把 XLSX XML 中的数字恢复为常用的 int 或 float。"""

    number = float(raw_value)
    return int(number) if number.is_integer() else number


def read_without_dependencies() -> tuple[list[str], list[list[Any]]]:
    """第三方库缺失时，只读解析 XLSX；正常项目环境不会进入此函数。"""

    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    office_rel_ns = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    )
    package_rel_ns = (
        "http://schemas.openxmlformats.org/package/2006/relationships"
    )
    namespaces = {"m": main_ns}

    with ZipFile(SOURCE_FILE) as archive:
        workbook_xml = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships_xml = ElementTree.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        relationship_map = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships_xml.findall(f"{{{package_rel_ns}}}Relationship")
        }

        sheets = workbook_xml.find("m:sheets", namespaces)
        if sheets is None or not list(sheets):
            raise ValueError("Excel 工作簿中没有 sheet")
        first_sheet = list(sheets)[0]
        if first_sheet.attrib["name"] != SOURCE_SHEET:
            raise ValueError(
                f"第一个 sheet 应为 {SOURCE_SHEET!r}，"
                f"实际为 {first_sheet.attrib['name']!r}"
            )

        relation_id = first_sheet.attrib[f"{{{office_rel_ns}}}id"]
        target = relationship_map[relation_id]
        sheet_path = (
            target.lstrip("/")
            if target.startswith("/")
            else normpath(posix_join("xl", target))
        )

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_xml = ElementTree.fromstring(
                archive.read("xl/sharedStrings.xml")
            )
            for item in shared_xml.findall("m:si", namespaces):
                shared_strings.append(
                    "".join(
                        text.text or ""
                        for text in item.iter(f"{{{main_ns}}}t")
                    )
                )

        sheet_xml = ElementTree.fromstring(archive.read(sheet_path))
        parsed_rows: list[list[Any]] = []
        for row in sheet_xml.findall(".//m:sheetData/m:row", namespaces):
            values: list[Any] = [None] * len(FIELD_KEYS)
            for cell in row.findall("m:c", namespaces):
                index = column_number(cell.attrib["r"])
                cell_type = cell.attrib.get("t")
                value_node = cell.find("m:v", namespaces)

                if cell_type == "inlineStr":
                    value: Any = "".join(
                        text.text or ""
                        for text in cell.iter(f"{{{main_ns}}}t")
                    )
                elif value_node is None:
                    value = None
                elif cell_type == "s":
                    value = shared_strings[int(value_node.text)]
                elif cell_type == "b":
                    value = value_node.text == "1"
                else:
                    value = parse_number(value_node.text)
                values[index] = value
            parsed_rows.append(values)

    return [str(value) for value in parsed_rows[0]], parsed_rows[1:]


def load_source_data() -> tuple[list[str], list[dict[str, Any]], str]:
    """读取数据、替换英文列名，并返回统一的字典记录。"""

    if pd is not None and load_workbook is not None:
        headers, frame = read_with_pandas_openpyxl()
        if frame.shape != (15, 31):
            raise ValueError(f"目标 sheet 应为 15×31 数据区，实际为 {frame.shape}")
        frame.columns = FIELD_KEYS
        frame["category"] = frame["category"].map(normalize_category)
        records = [
            {key: to_plain_value(value) for key, value in row.items()}
            for row in frame.to_dict(orient="records")
        ]
        reader_name = "pandas + openpyxl"
    else:
        headers, rows = read_without_dependencies()
        if len(rows) != 15 or any(len(row) != 31 for row in rows):
            raise ValueError("目标 sheet 应包含 15 行数据且每行 31 列")
        records = []
        for row in rows:
            record = dict(zip(FIELD_KEYS, row, strict=True))
            record["category"] = normalize_category(record["category"])
            records.append(record)
        reader_name = "标准库 XLSX 兼容读取（当前环境缺少 pandas/openpyxl）"

    if len(headers) != len(FIELD_KEYS):
        raise ValueError(f"表头应有 31 列，实际有 {len(headers)} 列")

    actual_models = [record["model"] for record in records]
    if actual_models != EXPECTED_MODELS:
        raise ValueError(
            "型号或顺序与已确认清单不一致：\n"
            f"预期: {EXPECTED_MODELS}\n实际: {actual_models}"
        )

    return headers, records, reader_name


def build_field_dictionary(
    headers: list[str], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """根据原表表头和清洗规则生成字段字典。"""

    dictionary_rows = []
    for field_key, header in zip(FIELD_KEYS, headers, strict=True):
        zh_name, en_name, unit = parse_header(header)
        if field_key in TEXT_FIELDS:
            data_type = "text"
        elif field_key in RANGE_OR_PAIR_FIELDS:
            data_type = "range_or_pair"
        else:
            data_type = "number"

        example = next(
            (
                record[field_key]
                for record in records
                if not is_missing(record[field_key])
            ),
            "",
        )
        dictionary_rows.append(
            {
                "field_key": field_key,
                "zh_name": zh_name,
                "en_name": en_name,
                "unit": unit,
                "data_type": data_type,
                "description": DESCRIPTIONS[field_key],
                "example": example,
                "can_be_compared": data_type == "number",
            }
        )
    return dictionary_rows


def write_csv(
    path: Path, rows: list[dict[str, Any]], fieldnames: list[str]
) -> None:
    """以 UTF-8 with BOM 覆盖写入 CSV，便于 Excel 正确显示中文。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_master(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """追加数据来源字段并写入主数据 CSV。"""

    master_rows = []
    for record in records:
        master_rows.append(
            {
                **record,
                "source_file": SOURCE_FILE_NAME,
                "source_sheet": SOURCE_SHEET,
                "data_version": DATA_VERSION,
            }
        )
    source_fields = ["source_file", "source_sheet", "data_version"]
    write_csv(MASTER_FILE, master_rows, FIELD_KEYS + source_fields)
    return master_rows


def build_model_cards(
    records: list[dict[str, Any]], units_by_field: dict[str, str]
) -> list[dict[str, Any]]:
    """把每个型号转换成一条适合检索和问答使用的 JSON 记录。"""

    spec_fields = [
        field for field in FIELD_KEYS if field not in {"model", "category"}
    ]
    cards = []
    for record in records:
        specs = {field: record[field] for field in spec_fields}
        units = {
            field: units_by_field[field]
            for field in spec_fields
            if units_by_field[field]
        }
        cards.append(
            {
                "model": record["model"],
                "category": record["category"],
                "is_key_model": record["model"] in KEY_MODELS,
                "specs": specs,
                "units": units,
                "source": {
                    "file": SOURCE_FILE_NAME,
                    "sheet": SOURCE_SHEET,
                    "data_version": DATA_VERSION,
                },
            }
        )
    return cards


def write_model_cards(cards: list[dict[str, Any]]) -> None:
    """以 UTF-8 JSONL 覆盖写入，每个型号严格占一行。"""

    MODEL_CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_CARDS_FILE.open("w", encoding="utf-8", newline="\n") as file:
        for card in cards:
            file.write(json.dumps(card, ensure_ascii=False, separators=(",", ":")))
            file.write("\n")


def run_quality_checks(
    records: list[dict[str, Any]],
    dictionary_rows: list[dict[str, Any]],
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """执行任务要求的完整性和一致性质检。"""

    actual_models = {record["model"] for record in records}
    missing_required = {
        record["model"]: [
            field for field in REQUIRED_FIELDS if is_missing(record[field])
        ]
        for record in records
    }
    missing_required = {
        model: fields for model, fields in missing_required.items() if fields
    }

    units_by_field = {
        row["field_key"]: row["unit"] for row in dictionary_rows
    }
    units_consistent = True
    for card in cards:
        expected_units = {
            field: units_by_field[field]
            for field in card["specs"]
            if units_by_field[field]
        }
        if card["units"] != expected_units:
            units_consistent = False
            break

    empty_cells = []
    slash_values = []
    na_values = []
    for record in records:
        for field in FIELD_KEYS:
            value = record[field]
            if is_missing(value):
                empty_cells.append((record["model"], field))
            elif isinstance(value, str) and value.strip().upper() == "N/A":
                na_values.append((record["model"], field, value))
            elif isinstance(value, str) and "/" in value:
                slash_values.append((record["model"], field, value))

    return {
        "model_count_ok": len(records) == 15,
        "key_models_ok": KEY_MODELS.issubset(actual_models),
        "missing_key_models": sorted(KEY_MODELS - actual_models),
        "required_fields_ok": not missing_required,
        "missing_required": missing_required,
        "units_consistent": units_consistent,
        "empty_cells": empty_cells,
        "slash_values": slash_values,
        "na_values": na_values,
    }


def status_text(passed: bool) -> str:
    """把布尔质检结果转换为报告中的中文状态。"""

    return "通过" if passed else "未通过"


def write_report(checks: dict[str, Any], reader_name: str) -> None:
    """根据实际清洗结果生成中文 Markdown 报告。"""

    slash_lines = [
        f"- `{model}` / `{field}`：`{value}`"
        for model, field, value in checks["slash_values"]
    ]
    empty_lines = (
        [
            f"- `{model}` / `{field}`"
            for model, field in checks["empty_cells"]
        ]
        if checks["empty_cells"]
        else ["- 未发现真正的空单元格。"]
    )
    na_lines = (
        [
            f"- `{model}` / `{field}`：`{value}`（原表缺失标记，按原样保留）"
            for model, field, value in checks["na_values"]
        ]
        if checks["na_values"]
        else ["- 未发现 `N/A` 等文本缺失标记。"]
    )

    report = f"""# 旋挖钻机数据清洗报告

## 清洗范围

- 原始文件：`data/raw/{SOURCE_FILE_NAME}`
- 原始 sheet：`{SOURCE_SHEET}`
- 数据版本：`{DATA_VERSION}`
- 读取方式：{reader_name}
- 清洗原则：不修改原始数值，不做单位换算；斜杠组合值和钻杆规格代号按原样保留。

## 质检结果

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 型号数是否为 15 | {status_text(checks["model_count_ok"])} | 实际 15 个型号 |
| 7 个重点型号是否齐全 | {status_text(checks["key_models_ok"])} | ZR140R、ZR185R、ZR255R、ZR300D、ZR320R、ZR380D、ZR420GW |
| 关键参数是否完整 | {status_text(checks["required_fields_ok"])} | 检查钻径、钻深、扭矩、发动机、功率、重量 |
| 单位与字段字典是否一致 | {status_text(checks["units_consistent"])} | JSONL 的单位映射与字段字典逐字段核对 |

## 发现的数据问题

### 斜杠组合值

以下值均作为不可随意拆解的字符串保留：

{chr(10).join(slash_lines)}

其中 `max_drilling_depth_m` 的两个值通常对应机锁杆/摩阻杆不同配置。
`height_mm` 和 `transport_height_mm` 的组合值也未做推断或拆分。

### ZR225 钻杆规格后缀

- `interlock_kelly`：`J419-4×14m`
- `friction_kelly`：`M419-5×14m`
- `m` 后缀表示单位米；两个原始值均完整保留。

### 空值

{chr(10).join(empty_lines)}

文本缺失标记：

{chr(10).join(na_lines)}

## 本期未清洗内容

以下 3 个 sheet 不在本期清洗范围内：

- `液压抓斗 Hydraulic Grab`
- `双轮铣+全套管+动力站`
- `产品目录 Product Catalog`
"""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")


def main() -> None:
    """执行完整清洗流程，并在任一质检失败时终止。"""

    headers, records, reader_name = load_source_data()
    dictionary_rows = build_field_dictionary(headers, records)
    units_by_field = {
        row["field_key"]: row["unit"] for row in dictionary_rows
    }

    master_rows = write_master(records)
    write_csv(
        DICTIONARY_FILE,
        dictionary_rows,
        [
            "field_key",
            "zh_name",
            "en_name",
            "unit",
            "data_type",
            "description",
            "example",
            "can_be_compared",
        ],
    )
    cards = build_model_cards(records, units_by_field)
    write_model_cards(cards)

    checks = run_quality_checks(records, dictionary_rows, cards)
    write_report(checks, reader_name)

    required_checks = [
        checks["model_count_ok"],
        checks["key_models_ok"],
        checks["required_fields_ok"],
        checks["units_consistent"],
    ]
    if not all(required_checks):
        raise ValueError(f"质检未通过: {checks}")

    print(f"读取方式: {reader_name}")
    print(f"主数据: {MASTER_FILE.relative_to(PROJECT_ROOT)} ({len(master_rows)} 行数据)")
    print(
        "字段字典: "
        f"{DICTIONARY_FILE.relative_to(PROJECT_ROOT)} ({len(dictionary_rows)} 行数据)"
    )
    print(
        "型号卡片: "
        f"{MODEL_CARDS_FILE.relative_to(PROJECT_ROOT)} ({len(cards)} 行 JSONL)"
    )
    print(f"清洗报告: {REPORT_FILE.relative_to(PROJECT_ROOT)}")
    print("全部质检通过。")


if __name__ == "__main__":
    main()
