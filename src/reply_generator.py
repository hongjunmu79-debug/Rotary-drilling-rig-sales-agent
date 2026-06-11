"""Generate fact-bound English and Arabic sales replies."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
SALES_DISCLAIMER = (
    "for sales reference only, subject to engineering confirmation"
)


def _read_env_value(name: str) -> str:
    """Read one KEY=VALUE entry without adding a dotenv dependency."""

    if not ENV_FILE.exists():
        return ""

    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    return ""


def _get_api_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY", "").strip() or _read_env_value(
        "DEEPSEEK_API_KEY"
    )


def _fact(facts: dict[str, Any], name: str) -> str:
    value = facts.get(name, "")
    return str(value) if value not in (None, "") else "not provided"


def _context_lines(
    facts: dict[str, Any],
    customer_context: str,
    language: str,
) -> str:
    project_type = _fact(facts, "project_type")
    market = _fact(facts, "market")
    context = customer_context.strip() or "not provided"
    if language == "ar":
        return (
            f"نوع المشروع: {project_type}. السوق: {market}. "
            f"سياق العميل: {context}."
        )
    return (
        f"Project type: {project_type}. Market: {market}. "
        f"Customer context: {context}."
    )


def _english_template(
    facts: dict[str, Any],
    customer_context: str,
) -> str:
    source = facts.get("source", {})
    return "\n".join(
        [
            f"Recommended model: {_fact(facts, 'model')}.",
            (
                f"Customer requirement: {_fact(facts, 'required_depth_m')} m "
                f"depth and {_fact(facts, 'required_diameter_mm')} mm diameter."
            ),
            (
                f"Structured product data: max drilling depth "
                f"{_fact(facts, 'depth_value')} m, max drilling diameter "
                f"{_fact(facts, 'diameter_value')} mm, rated output torque "
                f"{_fact(facts, 'torque')} kN.m."
            ),
            (
                f"Required configuration: {_fact(facts, 'required_config')}. "
                f"Friction-depth margin: {_fact(facts, 'depth_margin')} m."
            ),
            (
                f"Engine: {_fact(facts, 'engine_model')}; power "
                f"{_fact(facts, 'power_kw')} kW; weight "
                f"{_fact(facts, 'weight_t')} t; emission "
                f"{_fact(facts, 'emission')}."
            ),
            (
                f"Transport dimensions (L/W/H): "
                f"{_fact(facts, 'transport_length_mm')}/"
                f"{_fact(facts, 'transport_width_mm')}/"
                f"{_fact(facts, 'transport_height_mm')} mm."
            ),
            _context_lines(facts, customer_context, "en"),
            (
                f"Source: {source.get('file', 'not provided')} / "
                f"{source.get('sheet', 'not provided')} / "
                f"{source.get('version', 'not provided')}."
            ),
            SALES_DISCLAIMER,
        ]
    )


def _arabic_template(
    facts: dict[str, Any],
    customer_context: str,
) -> str:
    source = facts.get("source", {})
    return "\n".join(
        [
            f"الموديل الموصى به: {_fact(facts, 'model')}.",
            (
                f"متطلبات العميل: عمق {_fact(facts, 'required_depth_m')} متر "
                f"وقطر {_fact(facts, 'required_diameter_mm')} مم."
            ),
            (
                f"بيانات المنتج المنظمة: أقصى عمق حفر "
                f"{_fact(facts, 'depth_value')} متر، وأقصى قطر حفر "
                f"{_fact(facts, 'diameter_value')} مم، وعزم الخرج المقنن "
                f"{_fact(facts, 'torque')} كيلو نيوتن.متر."
            ),
            (
                f"التجهيز المطلوب: {_fact(facts, 'required_config')}. "
                f"هامش عمق قضيب الاحتكاك: "
                f"{_fact(facts, 'depth_margin')} متر."
            ),
            (
                f"المحرك: {_fact(facts, 'engine_model')}؛ القدرة "
                f"{_fact(facts, 'power_kw')} كيلوواط؛ الوزن "
                f"{_fact(facts, 'weight_t')} طن؛ الانبعاثات "
                f"{_fact(facts, 'emission')}."
            ),
            (
                f"أبعاد النقل (الطول/العرض/الارتفاع): "
                f"{_fact(facts, 'transport_length_mm')}/"
                f"{_fact(facts, 'transport_width_mm')}/"
                f"{_fact(facts, 'transport_height_mm')} مم."
            ),
            _context_lines(facts, customer_context, "ar"),
            (
                f"المصدر: {source.get('file', 'not provided')} / "
                f"{source.get('sheet', 'not provided')} / "
                f"{source.get('version', 'not provided')}."
            ),
            SALES_DISCLAIMER,
        ]
    )


def _template_reply(
    facts: dict[str, Any],
    language: str,
    customer_context: str,
) -> str:
    if language == "en":
        return _english_template(facts, customer_context)
    if language == "ar":
        return _arabic_template(facts, customer_context)
    return (
        "English\n"
        + _english_template(facts, customer_context)
        + "\n\nالعربية\n"
        + _arabic_template(facts, customer_context)
    )


def _llm_reply(
    facts: dict[str, Any],
    language: str,
    customer_context: str,
    api_key: str,
) -> str:
    system_prompt = (
        "You write concise rotary drilling rig sales replies. Use only the "
        "provided facts. Use no numeric value unless it appears in the facts. "
        "Never invent or estimate specifications, prices, discounts, delivery "
        "times, availability, or guarantees. Write in English for 'en', Arabic "
        "for 'ar', and both languages for 'both'. End the complete reply with "
        f"this exact text: {SALES_DISCLAIMER}"
    )
    user_payload = {
        "language": language,
        "customer_context": customer_context,
        "facts": facts,
    }
    request_body = json.dumps(
        {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "temperature": 0,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        DEEPSEEK_URL,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    reply = payload["choices"][0]["message"]["content"].strip()
    if not reply.endswith(SALES_DISCLAIMER):
        reply = f"{reply}\n{SALES_DISCLAIMER}"
    return reply


def _llm_unavailable_note(error: Exception, api_key: str) -> str:
    """Build a short diagnostic without exposing the configured API key."""

    error_type = type(error).__name__
    message = " ".join(str(error).split())
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    if isinstance(error, urllib.error.HTTPError):
        status_code = getattr(error, "code", None)
        status_text = f"HTTP status {status_code}"
        message = f"{status_text}: {message}" if message else status_text
    message = message[:200] or "no details"
    return (
        f"LLM unavailable ({error_type}: {message}), "
        "used template instead"
    )


def generate_reply(
    recommendation_facts: dict,
    language: str,
    customer_context: str,
) -> dict:
    """Generate an LLM reply when configured, otherwise use a safe template."""

    normalized_language = language.casefold()
    if normalized_language not in {"en", "ar", "both"}:
        raise ValueError("language must be 'en', 'ar', or 'both'")

    try:
        api_key = _get_api_key()
    except Exception:
        api_key = ""
    if api_key:
        try:
            return {
                "reply_text": _llm_reply(
                    recommendation_facts,
                    normalized_language,
                    customer_context,
                    api_key,
                ),
                "mode": "llm",
                "note": "",
            }
        except Exception as error:
            note = _llm_unavailable_note(error, api_key)
            return {
                "reply_text": _template_reply(
                    recommendation_facts,
                    normalized_language,
                    customer_context,
                ),
                "mode": "template",
                "note": note,
            }

    return {
        "reply_text": _template_reply(
            recommendation_facts,
            normalized_language,
            customer_context,
        ),
        "mode": "template",
        "note": "No API key configured",
    }
