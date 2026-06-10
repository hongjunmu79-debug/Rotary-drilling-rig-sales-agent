# Project Brief — Zoomlion Rotary Drilling Rig AI Sales Assistant

## 一句话定位

面向中东市场旋挖钻机销售人员的 AI 询盘助手：参数查得准、型号推得对、英文/阿语回复直接可发、每个数字都有出处、没有的数据绝不编。

## 目标用户与场景

**用户**：中联重科旋挖钻机海外（中东）销售人员。

**典型场景**：
1. 客户问"ZR255R 最大钻深多少"——销售需要 30 秒内给出带来源的准确参数
2. 客户说"我有个 60m 深、2000mm 桩径的项目"——销售需要立刻知道推荐哪 1-3 个型号、为什么
3. 客户要英文/阿语的正式回复——销售需要可直接复制发送的专业话术
4. 客户问价格/油耗/质保——资料里没有，系统必须明确说没有，不能编

## 功能范围（v0，本周）

**做**：参数查询、型号对比、需求选型推荐、英/阿销售回复生成、来源追溯、缺数据拒答。
**不做**：价格报价、工程最终适配结论（仅销售参考，需工程师确认）、CRM 集成、多品类扩展。

## 数据策略

- 第一事实源：`data/processed/rotary_rig_master.csv`（自 Zoomlion_Brochure_Data.xlsx 清洗，15 个型号，v0_2026-06-11）
- 单位由 `rotary_rig_field_dictionary.csv` 唯一定义，禁止生成时擅自换算
- 组合值（如钻深 56/70 = 机锁杆/摩阻杆配置）原样展示并解释，不拆解
- Demo 重点 7 个型号：ZR140R, ZR185R, ZR255R, ZR300D, ZR320R, ZR380D, ZR420GW

## Day 1 测试问题（首批 5 条）

| # | 问题 | 期望行为 |
|---|------|----------|
| 1 | What is the max drilling depth of ZR255R? | 答 56/70 m，解释 Interlock/Friction Kelly 双配置，标来源 |
| 2 | Compare ZR185R and ZR255R for a 50m pile foundation project. | 并列参数表 + 差异解释 + 来源 |
| 3 | Recommend a rig for 60m depth and 2000mm diameter in Dubai. | 推荐型号（钻深钻径达标），附理由与风险提示 |
| 4 | What is the price of ZR255R? | 拒答：数据中无价格，建议联系销售经理 |
| 5 | What is the swing radius of ZR380D? | 如实说明原表为 N/A，不编数值 |
