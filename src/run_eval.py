"""Run the repeatable Day 5 evaluation against structured project data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from .data_loader import load_data
    from .param_lookup import find_fields, find_model, lookup
    from .recommender import KEY_MODELS, recommend
    from . import reply_generator
except ImportError:
    from data_loader import load_data
    from param_lookup import find_fields, find_model, lookup
    from recommender import KEY_MODELS, recommend
    import reply_generator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_CSV = (
    PROJECT_ROOT / "data" / "processed" / "rotary_rig_test_questions.csv"
)
REPORT_PATH = PROJECT_ROOT / "docs" / "eval_report_day5.md"
SOURCE_KEYS = ("source_file", "source_sheet", "data_version")
TARGETS = {
    "参数准确率": 0.90,
    "单位准确率": 1.00,
    "拒答正确率": 0.80,
    "来源展示率": 1.00,
    "推荐正确率": 0.80,
    "回复合格率": 1.00,
}


def _rows_by_key(frame: Any, key: str) -> dict[str, dict[str, str]]:
    return {
        str(row[key]): {str(column): str(row[column]) for column in frame.columns}
        for _, row in frame.iterrows()
    }


def _load_questions() -> list[dict[str, str]]:
    with QUESTIONS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "id",
        "category",
        "question",
        "expected_type",
        "expected_model",
        "expected_field_key",
        "expected_params",
    }
    if not rows:
        raise ValueError("Evaluation question CSV is empty.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(
            "Evaluation question CSV is missing columns: "
            + ", ".join(sorted(missing))
        )
    if len(rows) != 30:
        raise ValueError(f"Expected 30 evaluation questions; found {len(rows)}.")
    return rows


def _params(question: dict[str, str]) -> dict[str, Any]:
    raw = question["expected_params"].strip()
    return json.loads(raw) if raw else {}


def _depth_parts(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split("/")]


def _friction_depth(value: str) -> float:
    return _depth_parts(value)[-1]


def _source_matches(
    result: dict[str, Any],
    master_row: dict[str, str],
) -> bool:
    return all(
        bool(str(result.get(key, "")).strip())
        and str(result.get(key, "")) == master_row[key]
        for key in SOURCE_KEYS
    )


def _find_all_models(query: str) -> list[str]:
    remaining = query
    models = []
    while True:
        model = find_model(remaining)
        if model is None:
            return models
        models.append(model)
        remaining = re.sub(
            re.escape(model),
            " ",
            remaining,
            count=1,
            flags=re.IGNORECASE,
        )


def _result(
    question: dict[str, str],
    passed: bool,
    reasons: list[str],
    **metric_values: bool | None,
) -> dict[str, Any]:
    return {
        "id": question["id"],
        "category": question["category"],
        "passed": passed,
        "reason": "；".join(reasons) if reasons else "全部检查通过",
        "metrics": metric_values,
    }


def _evaluate_a(
    question: dict[str, str],
    master: dict[str, dict[str, str]],
    fields: dict[str, dict[str, str]],
) -> dict[str, Any]:
    expected_model = question["expected_model"]
    expected_field = question["expected_field_key"]
    detected_model = find_model(question["question"])
    detected_fields = find_fields(question["question"])
    reasons: list[str] = []

    model_ok = detected_model == expected_model
    field_ok = detected_fields == [expected_field]
    if not model_ok:
        reasons.append(
            f"型号识别期望 {expected_model}，实际 {detected_model or 'None'}"
        )
    if not field_ok:
        reasons.append(
            f"字段识别期望 [{expected_field}]，实际 {detected_fields}"
        )

    parameter_ok = False
    unit_ok = False
    source_ok = False
    if model_ok and field_ok:
        actual = lookup(detected_model, detected_fields[0])
        raw_value = master[expected_model][expected_field]
        expected_confidence = (
            "not_available"
            if raw_value.strip().upper() == "N/A"
            else "exact_match"
        )
        value_ok = actual["value"] == raw_value
        confidence_ok = actual["confidence"] == expected_confidence
        unit_ok = actual["unit"] == fields[expected_field]["unit"]
        source_ok = _source_matches(actual, master[expected_model])
        parameter_ok = model_ok and field_ok and value_ok and confidence_ok
        if not value_ok:
            reasons.append(
                f"值期望逐字为 {raw_value!r}，实际 {actual['value']!r}"
            )
        if not confidence_ok:
            reasons.append(
                f"confidence 期望 {expected_confidence}，"
                f"实际 {actual['confidence']}"
            )
        if not unit_ok:
            reasons.append(
                f"单位期望 {fields[expected_field]['unit']!r}，"
                f"实际 {actual['unit']!r}"
            )
        if not source_ok:
            reasons.append("来源三件套缺失或与主表不一致")

    passed = parameter_ok and unit_ok and source_ok
    return _result(
        question,
        passed,
        reasons,
        parameter=parameter_ok,
        unit=unit_ok,
        source=source_ok,
        refusal=None,
        recommendation=None,
        reply=None,
    )


def _evaluate_b(
    question: dict[str, str],
    master: dict[str, dict[str, str]],
    fields: dict[str, dict[str, str]],
) -> dict[str, Any]:
    expected_field = question["expected_field_key"]
    models = _params(question).get("models", [])
    reasons: list[str] = []
    recognized_models = _find_all_models(question["question"])
    model_ok = (
        len(models) == 2
        and len(recognized_models) == 2
        and set(recognized_models) == set(models)
    )
    detected_fields = find_fields(question["question"])
    field_ok = detected_fields == [expected_field]
    if not model_ok:
        reasons.append(
            f"两型号识别期望 {models}，实际 {recognized_models}"
        )
    if not field_ok:
        reasons.append(
            f"字段识别期望 [{expected_field}]，实际 {detected_fields}"
        )

    values_ok = model_ok and field_ok
    unit_ok = model_ok and field_ok
    source_ok = model_ok and field_ok
    if model_ok and field_ok:
        for model in models:
            actual = lookup(model, expected_field)
            raw_value = master[model][expected_field]
            expected_confidence = (
                "not_available"
                if raw_value.strip().upper() == "N/A"
                else "exact_match"
            )
            if (
                actual["value"] != raw_value
                or actual["confidence"] != expected_confidence
            ):
                values_ok = False
                reasons.append(
                    f"{model} 值或 confidence 与运行时主表不一致"
                )
            if actual["unit"] != fields[expected_field]["unit"]:
                unit_ok = False
                reasons.append(f"{model} 单位与字段字典不一致")
            if not _source_matches(actual, master[model]):
                source_ok = False
                reasons.append(f"{model} 来源三件套缺失或不一致")

    parameter_ok = model_ok and field_ok and values_ok
    passed = parameter_ok and unit_ok and source_ok
    return _result(
        question,
        passed,
        reasons,
        parameter=parameter_ok,
        unit=unit_ok,
        source=source_ok,
        refusal=None,
        recommendation=None,
        reply=None,
    )


def _eligible_models(
    master: dict[str, dict[str, str]],
    required_depth: float,
    required_diameter: float,
) -> list[str]:
    eligible = []
    for model, row in master.items():
        try:
            depth = _friction_depth(row["max_drilling_depth_m"])
            diameter = float(row["max_drilling_diameter_mm"])
        except (TypeError, ValueError):
            continue
        if depth >= required_depth and diameter >= required_diameter:
            eligible.append(model)
    return eligible


def _evaluate_c(
    question: dict[str, str],
    master: dict[str, dict[str, str]],
) -> dict[str, Any]:
    params = _params(question)
    depth = float(params["required_depth_m"])
    diameter = float(params["required_diameter_mm"])
    max_results = int(params.get("max_results", 3))
    expect_empty = bool(params.get("expect_empty", False))
    recommendations = recommend(depth, diameter, max_results=max_results)
    eligible = _eligible_models(master, depth, diameter)
    reasons: list[str] = []

    if expect_empty:
        recommendation_ok = not recommendations and not eligible
        if recommendations:
            reasons.append(
                "无解题应返回空，实际返回 "
                + ", ".join(item["model"] for item in recommendations)
            )
        if eligible:
            reasons.append(f"题目标为无解，但主表存在达标型号 {eligible}")
    else:
        nonempty_ok = bool(recommendations)
        if not nonempty_ok:
            reasons.append("有解题返回了空结果")
        all_qualified = nonempty_ok
        values_match = nonempty_ok
        for item in recommendations:
            model = item["model"]
            if model not in eligible:
                all_qualified = False
                reasons.append(f"{model} 未同时满足摩阻杆钻深和钻径要求")
                continue
            row = master[model]
            if (
                item["depth_value"] != row["max_drilling_depth_m"]
                or item["diameter_value"] != row["max_drilling_diameter_mm"]
            ):
                values_match = False
                reasons.append(f"{model} 推荐参数未逐字保持主表值")
        eligible_key_models = [
            model for model in eligible if model in KEY_MODELS
        ]
        key_first_ok = (
            not eligible_key_models
            or (
                bool(recommendations)
                and recommendations[0]["model"] in KEY_MODELS
            )
        )
        if not key_first_ok:
            reasons.append(
                "存在达标重点型号，但推荐第一名不是重点型号"
            )
        expected_first = question["expected_model"]
        expected_first_ok = (
            not expected_first
            or (
                bool(recommendations)
                and recommendations[0]["model"] == expected_first
            )
        )
        if not expected_first_ok:
            actual_first = (
                recommendations[0]["model"] if recommendations else "None"
            )
            reasons.append(
                f"第一名期望 {expected_first}，实际 {actual_first}"
            )
        recommendation_ok = (
            nonempty_ok
            and all_qualified
            and values_match
            and key_first_ok
            and expected_first_ok
        )

    return _result(
        question,
        recommendation_ok,
        reasons,
        parameter=None,
        unit=None,
        source=None,
        refusal=None,
        recommendation=recommendation_ok,
        reply=None,
    )


def _template_reply(facts: dict[str, Any], customer_context: str) -> dict:
    original_get_api_key = reply_generator._get_api_key
    reply_generator._get_api_key = lambda: ""
    try:
        return reply_generator.generate_reply(
            facts,
            language="en",
            customer_context=customer_context,
        )
    finally:
        reply_generator._get_api_key = original_get_api_key


def _evaluate_d(
    question: dict[str, str],
    master: dict[str, dict[str, str]],
) -> dict[str, Any]:
    params = _params(question)
    depth = float(params["required_depth_m"])
    diameter = float(params["required_diameter_mm"])
    recommendations = recommend(depth, diameter, max_results=3)
    expected_model = question["expected_model"]
    reasons: list[str] = []
    if not recommendations:
        return _result(
            question,
            False,
            ["无法生成回复：推荐结果为空"],
            parameter=None,
            unit=None,
            source=None,
            refusal=None,
            recommendation=None,
            reply=False,
        )

    selected = recommendations[0]
    facts = {
        **selected,
        "required_depth_m": params["required_depth_m"],
        "required_diameter_mm": params["required_diameter_mm"],
        "project_type": params.get("project_type", ""),
        "market": params.get("market", ""),
    }
    generated = _template_reply(facts, params.get("customer_context", ""))
    text = generated.get("reply_text", "")
    expected_depth = master[expected_model]["max_drilling_depth_m"]
    checks = {
        "推荐型号": selected["model"] == expected_model,
        "模板模式": generated.get("mode") == "template",
        "回复含型号": expected_model in text,
        "回复含主表钻深原值": expected_depth in text,
        "回复含免责声明": "for sales reference only" in text.casefold(),
    }
    for label, ok in checks.items():
        if not ok:
            reasons.append(label + "未通过")
    reply_ok = all(checks.values())
    return _result(
        question,
        reply_ok,
        reasons,
        parameter=None,
        unit=None,
        source=None,
        refusal=None,
        recommendation=None,
        reply=reply_ok,
    )


def _evaluate_e(
    question: dict[str, str],
    master: dict[str, dict[str, str]],
) -> dict[str, Any]:
    params = _params(question)
    trap_kind = params["trap_kind"]
    reasons: list[str] = []

    if trap_kind == "unsupported_field":
        detected_fields = find_fields(question["question"])
        model_ok = find_model(question["question"]) == question["expected_model"]
        refusal_ok = model_ok and detected_fields == []
        if not model_ok:
            reasons.append("陷阱题型号识别错误")
        if detected_fields:
            reasons.append(f"无此业务字段，但识别出了 {detected_fields}")
    elif trap_kind == "unknown_model":
        detected_model = find_model(question["question"])
        refusal_ok = detected_model is None
        if not refusal_ok:
            reasons.append(f"不存在型号被识别为 {detected_model}")
    elif trap_kind == "depth_capability":
        model = question["expected_model"]
        field_key = question["expected_field_key"]
        actual = lookup(model, field_key)
        raw_value = master[model][field_key]
        required_depth = float(params["required_depth_m"])
        try:
            cannot_reach = max(_depth_parts(raw_value)) < required_depth
        except ValueError:
            cannot_reach = False
        refusal_ok = (
            find_model(question["question"]) == model
            and actual["value"] == raw_value
            and cannot_reach
        )
        if actual["value"] != raw_value:
            reasons.append("lookup 值与运行时主表不一致")
        if not cannot_reach:
            reasons.append(
                f"主表钻深 {raw_value!r} 未能程序化证明小于 {required_depth:g}"
            )
    else:
        refusal_ok = False
        reasons.append(f"未知 trap_kind: {trap_kind}")

    return _result(
        question,
        refusal_ok,
        reasons,
        parameter=None,
        unit=None,
        source=None,
        refusal=refusal_ok,
        recommendation=None,
        reply=None,
    )


def _evaluate_all(
    questions: list[dict[str, str]],
    master: dict[str, dict[str, str]],
    fields: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    evaluators = {
        "A": lambda question: _evaluate_a(question, master, fields),
        "B": lambda question: _evaluate_b(question, master, fields),
        "C": lambda question: _evaluate_c(question, master),
        "D": lambda question: _evaluate_d(question, master),
        "E": lambda question: _evaluate_e(question, master),
    }
    results = []
    for question in questions:
        category = question["category"]
        if category not in evaluators:
            results.append(
                _result(
                    question,
                    False,
                    [f"未知类别 {category}"],
                    parameter=None,
                    unit=None,
                    source=None,
                    refusal=None,
                    recommendation=None,
                    reply=None,
                )
            )
            continue
        try:
            results.append(evaluators[category](question))
        except Exception as error:
            results.append(
                _result(
                    question,
                    False,
                    [f"{type(error).__name__}: {error}"],
                    parameter=False if category in {"A", "B"} else None,
                    unit=False if category in {"A", "B"} else None,
                    source=False if category in {"A", "B"} else None,
                    refusal=False if category == "E" else None,
                    recommendation=False if category == "C" else None,
                    reply=False if category == "D" else None,
                )
            )
    return results


def _metric(
    results: list[dict[str, Any]],
    metric_key: str,
) -> tuple[int, int, float]:
    values = [
        result["metrics"][metric_key]
        for result in results
        if result["metrics"].get(metric_key) is not None
    ]
    passed = sum(value is True for value in values)
    total = len(values)
    rate = passed / total if total else 0.0
    return passed, total, rate


def _metrics(results: list[dict[str, Any]]) -> dict[str, tuple[int, int, float]]:
    return {
        "参数准确率": _metric(results, "parameter"),
        "单位准确率": _metric(results, "unit"),
        "拒答正确率": _metric(results, "refusal"),
        "来源展示率": _metric(results, "source"),
        "推荐正确率": _metric(results, "recommendation"),
        "回复合格率": _metric(results, "reply"),
    }


def _print_results(
    results: list[dict[str, Any]],
    metrics: dict[str, tuple[int, int, float]],
) -> None:
    headers = ("ID", "类别", "结果", "原因")
    rows = [
        (
            result["id"],
            result["category"],
            "PASS" if result["passed"] else "FAIL",
            result["reason"],
        )
        for result in results
    ]
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    print(
        " | ".join(
            str(headers[index]).ljust(widths[index])
            for index in range(len(headers))
        )
    )
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(
            " | ".join(
                str(row[index]).ljust(widths[index])
                for index in range(len(headers))
            )
        )

    print("\n汇总指标")
    for name, (passed, total, rate) in metrics.items():
        target = TARGETS[name]
        status = "达标" if rate >= target else "未达标"
        print(
            f"- {name}: {passed}/{total} = {rate:.1%} "
            f"(目标 {target:.0%}, {status})"
        )


def _write_report(
    results: list[dict[str, Any]],
    metrics: dict[str, tuple[int, int, float]],
) -> None:
    failed = [result for result in results if not result["passed"]]
    target_ok = all(
        metrics[name][2] >= target for name, target in TARGETS.items()
    )
    lines = [
        "# Day 5 自动评测报告",
        "",
        "评测范围：30 题，覆盖参数查询、双型号对比、选型推荐、"
        "英文模板回复和拒答陷阱。",
        "",
        "## 指标与目标",
        "",
        "| 指标 | 结果 | 目标 | 判定 |",
        "|---|---:|---:|---|",
    ]
    for name, (passed, total, rate) in metrics.items():
        target = TARGETS[name]
        status = "达标" if rate >= target else "未达标"
        lines.append(
            f"| {name} | {passed}/{total}（{rate:.1%}） | "
            f"≥{target:.0%} | {status} |"
        )

    lines.extend(["", "## 失败题清单", ""])
    if failed:
        lines.extend(
            f"- {result['id']}（{result['category']}）：{result['reason']}"
            for result in failed
        )
    else:
        lines.append("- 无。30 题全部通过。")

    lines.extend(
        [
            "",
            "## 结论",
            "",
            (
                "全部指标达到目标，评测管线退出码为 0。"
                if target_ok
                else "存在未达标指标，评测管线退出码为 1。"
            ),
            "",
            "评分时的产品参数、单位和来源均在运行时读取 "
            "`rotary_rig_master.csv` 与 "
            "`rotary_rig_field_dictionary.csv`；回复评测强制使用模板模式，"
            "不调用 LLM。",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    questions = _load_questions()
    master_frame, field_frame = load_data()
    master = _rows_by_key(master_frame, "model")
    fields = _rows_by_key(field_frame, "field_key")
    results = _evaluate_all(questions, master, fields)
    metrics = _metrics(results)
    _print_results(results, metrics)
    _write_report(results, metrics)
    return (
        0
        if all(metrics[name][2] >= target for name, target in TARGETS.items())
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
