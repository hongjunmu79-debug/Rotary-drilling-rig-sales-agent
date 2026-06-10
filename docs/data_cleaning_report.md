# 旋挖钻机数据清洗报告

## 清洗范围

- 原始文件：`data/raw/Zoomlion_Brochure_Data.xlsx`
- 原始 sheet：`旋挖钻机 Rotary Drilling Rig`
- 数据版本：`v0_2026-06-11`
- 读取方式：标准库 XLSX 兼容读取（当前环境缺少 pandas/openpyxl）
- 清洗原则：不修改原始数值，不做单位换算；斜杠组合值和钻杆规格代号按原样保留。

## 质检结果

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 型号数是否为 15 | 通过 | 实际 15 个型号 |
| 7 个重点型号是否齐全 | 通过 | ZR140R、ZR185R、ZR255R、ZR300D、ZR320R、ZR380D、ZR420GW |
| 关键参数是否完整 | 通过 | 检查钻径、钻深、扭矩、发动机、功率、重量 |
| 单位与字段字典是否一致 | 通过 | JSONL 的单位映射与字段字典逐字段核对 |

## 发现的数据问题

### 斜杠组合值

以下值均作为不可随意拆解的字符串保留：

- `ZR140` / `max_drilling_depth_m`：`35/44`
- `ZR160L` / `max_drilling_depth_m`：`44/55`
- `ZR185H` / `max_drilling_depth_m`：`44/56`
- `ZR185H` / `height_mm`：`19324/20819`
- `ZR225` / `max_drilling_depth_m`：`51/64`
- `ZR255H` / `max_drilling_depth_m`：`56/70`
- `ZR300L` / `max_drilling_depth_m`：`62/94`
- `ZR300L` / `height_mm`：`24561/25861`
- `ZR360L` / `max_drilling_depth_m`：`65/100`
- `ZR140R` / `max_drilling_depth_m`：`35/44`
- `ZR185R` / `max_drilling_depth_m`：`44/56`
- `ZR185R` / `height_mm`：`19324/20819`
- `ZR255R` / `max_drilling_depth_m`：`56/70`
- `ZR300D` / `max_drilling_depth_m`：`62/94`
- `ZR300D` / `height_mm`：`24561/25861`
- `ZR320R` / `max_drilling_depth_m`：`65/100`
- `ZR320R` / `transport_height_mm`：`3500/3790`
- `ZR380D` / `max_drilling_depth_m`：`65/100`
- `ZR420GW` / `max_drilling_depth_m`：`65/100`
- `ZR600GW` / `max_drilling_depth_m`：`108/136`

其中 `max_drilling_depth_m` 的两个值通常对应机锁杆/摩阻杆不同配置。
`height_mm` 和 `transport_height_mm` 的组合值也未做推断或拆分。

### ZR225 钻杆规格后缀

- `interlock_kelly`：`J419-4×14m`
- `friction_kelly`：`M419-5×14m`
- `m` 后缀表示单位米；两个原始值均完整保留。

### 空值

- 未发现真正的空单元格。

文本缺失标记：

- `ZR380D` / `swing_radius_mm`：`N/A`（原表缺失标记，按原样保留）
- `ZR420GW` / `swing_radius_mm`：`N/A`（原表缺失标记，按原样保留）

## 本期未清洗内容

以下 3 个 sheet 不在本期清洗范围内：

- `液压抓斗 Hydraulic Grab`
- `双轮铣+全套管+动力站`
- `产品目录 Product Catalog`
