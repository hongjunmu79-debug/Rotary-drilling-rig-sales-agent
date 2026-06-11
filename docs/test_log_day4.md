# Day 4 测试日志 — 选型推荐 + 英/阿销售回复（2026-06-11）

## 新增能力

1. **src/recommender.py** — 纯结构化选型：解析组合钻深（机锁杆/摩阻杆），判定达标与所需配置；排序 = 重点型号 > 机锁杆可达标 > 钻深余量小（够用优先）；返回 1-3 个推荐
2. **src/reply_generator.py** — 英/阿客户回复：有 DEEPSEEK_API_KEY（环境变量或 .env）时走 deepseek-chat（temperature=0，系统提示词禁止使用 facts 之外的任何数字，强制免责声明）；无 Key 或调用失败自动降级确定性模板，并通过 note 字段披露降级原因
3. **app.py** — Model Recommendation 区：深度/钻径/项目类型/语言输入 → 推荐卡片（参数表+所需配置+余量+来源+免责）→ 一键生成客户回复（标注 LLM/Template 模式）

## 实测记录

| 场景 | 结果 |
|------|------|
| recommend(60, 2000) | ✅ ZR300D(机锁杆,余量34) > ZR320R > ZR380D，全为重点型号 |
| recommend(40, 1300) | ✅ ZR185R 第一，required_config=Interlock Kelly |
| recommend(200, 5000) | ✅ 空结果，无编造 |
| 浏览器端到端（60/2000 + 生成回复） | ✅ 推荐卡片完整；模板回复双语数字全部来自 CSV |
| DeepSeek 实调 | ⚠️ HTTP 402 Insufficient Balance（账户余额不足），自动降级模板并在 UI 披露原因——降级管线按设计工作 |

单元测试：test_lookup.py + test_recommender.py 全部通过。

## 审核发现并修复

- 初版 LLM 失败静默降级（`except: pass`），排障困难 → 已让 Codex 加 note 字段披露降级原因（绝不含 Key），UI 用 caption 展示。本次 402 正是靠它定位的。

## 待办

- DeepSeek 账户充值后 LLM 模式即自动启用（无需改代码）；届时补测 LLM 回复的"数字不越界"验收
