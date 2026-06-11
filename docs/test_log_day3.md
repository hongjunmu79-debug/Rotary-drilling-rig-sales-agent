# Day 3 测试日志 — Python + Streamlit 结构化查询版（2026-06-11）

## 架构要点

- **零 LLM**：参数答案 100% 来自 CSV 精确查询（data_loader → param_lookup → answer_generator → app.py），数值不可能幻觉——Day 2 Dify 版的钻径幻觉问题在本版被结构性根治
- 输出契约：Model / Field(中英) / Value / Unit / Configuration(组合值 Kelly 解释) / Confidence / Source
- 双入口：自由文本（中英文均可）+ 型号/字段下拉
- 运行：`.venv\Scripts\python -m streamlit run app.py`（必须用 .venv——本机是 Windows ARM64，系统 ARM64 Python 装不了 pyarrow/streamlit，.venv 基于 x64 Python 3.12 模拟层）

## 实测记录（浏览器端到端）

| # | 查询 | 结果 |
|---|------|------|
| 1 | What is the max drilling depth of ZR255R? | ✅ 56/70 m，Kelly 配置解释，High 置信度 |
| 2 | What is the swing radius of ZR380D? | ✅ "Not available in source data (recorded as N/A)"，不给数值 |
| 3 | ZR600GW的最大输出扭矩是多少？ | ✅（修复后）精确返回 600 kN·m 唯一结果 |

单元测试：`python src/test_lookup.py` 全部通过（含修复回归用例）。

## 审核中发现并修复的 bug

**中文字段过匹配**：初版 `find_fields('最大输出扭矩')` 会同时命中 最大钻孔直径/最大钻孔深度/最大输出扭矩 三个字段（模糊有序字符匹配中"最大"二字命中所有"最大×"字段）。修复：zh_name 精确子串命中时只返回精确结果，模糊缩写匹配（如'钻深'→最大钻孔深度）仅作兜底。新增 4 条回归断言。

> 教训：单测全绿 ≠ 真实查询正确，验收必须包含端到端实测。

## 环境记录（Windows ARM64 重要）

- 本机 ARM64 Python 无 pyarrow 轮子 → `winget install Python.Python.3.12 --architecture x64 --force` 装 x64 版（用户级）→ 项目 `.venv` 用 x64 Python 创建，streamlit 1.58.0 + pandas 3.0.3 正常
