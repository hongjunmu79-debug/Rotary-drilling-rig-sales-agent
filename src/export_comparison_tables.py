# -*- coding: utf-8 -*-
"""Build product comparison tables (对比表) for Zoomlion rotary drilling rigs.

Source of truth: rotary_rig_master.csv (15 models) + rotary_rig_field_dictionary.csv
No fabrication: combined values (56/70, height slash) preserved as-is, N/A stays N/A.
"""
import csv, os, json
from collections import OrderedDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_csv(name):
    with open(PROJECT_ROOT / 'data' / 'processed' / name, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

rows = load_csv('rotary_rig_master.csv')
fields = load_csv('rotary_rig_field_dictionary.csv')

# field_key -> (zh_name, en_name, unit, can_be_compared)
fd = {f['field_key']: f for f in fields}

# ---- parameter groups (logical sections) ----
GROUPS = OrderedDict([
    ('drilling',  ('钻孔能力 Drilling Capability', [
        'max_drilling_diameter_mm', 'max_drilling_depth_m',
        'interlock_kelly', 'friction_kelly'])),
    ('rotary',    ('动力头 Rotary Head', [
        'rated_output_torque_knm', 'rotation_speed_rpm'])),
    ('crowd',     ('加压系统 Crowd System', [
        'crowd_force_kn', 'line_pull_kn', 'stroke_mm'])),
    ('winch',     ('卷扬系统 Winch System', [
        'main_winch_pull_kn', 'main_winch_rope_diameter_mm', 'main_winch_speed_m_min',
        'aux_winch_pull_kn', 'aux_rope_diameter_mm', 'aux_speed_m_min'])),
    ('engine',    ('发动机 Engine', [
        'engine_model', 'power_kw', 'capacity_l', 'emission'])),
    ('crawler',   ('底盘行走 Undercarriage', [
        'track_ext_width_mm', 'track_shoe_width_mm', 'crawler_length_mm', 'swing_radius_mm'])),
    ('dims',      ('整机尺寸与重量 Dimensions & Weight', [
        'weight_t', 'height_mm', 'transport_width_mm', 'transport_height_mm', 'transport_length_mm'])),
])

KEY_MODELS = ['ZR140R', 'ZR185R', 'ZR255R', 'ZR300D', 'ZR320R', 'ZR380D', 'ZR420GW']

# top sales-critical parameters for the transposed quick-compare sheet
QUICK_PARAMS = [
    'max_drilling_diameter_mm', 'max_drilling_depth_m',
    'rated_output_torque_knm', 'crowd_force_kn', 'line_pull_kn',
    'main_winch_pull_kn', 'power_kw', 'engine_model', 'emission',
    'weight_t', 'swing_radius_mm', 'height_mm',
    'interlock_kelly', 'friction_kelly',
]

def zh_en(key):
    f = fd[key]
    return f['zh_name'], f['en_name'], f['unit']

def cell_val(r, key):
    v = (r.get(key) or '').strip()
    if v == '' or v.upper() == 'N/A':
        return 'N/A'
    return v

# sort models by (max drilling diameter, rated torque) for a capability-ordered view
def dia_num(r):
    try: return int(r['max_drilling_diameter_mm'])
    except: return 0
def depth_max(r):
    s = r['max_drilling_depth_m']
    try:
        parts = s.split('/')
        return int(parts[-1])  # friction (deeper) config
    except:
        return 0
def torque_num(r):
    try: return int(r['rated_output_torque_knm'])
    except: return 0

models_sorted = sorted(rows, key=lambda r: (dia_num(r), torque_num(r)))

# =====================================================================
# MARKDOWN: full wide comparison table (all 15 models, capability-ordered)
# =====================================================================
md = []
md.append('# 中联重科旋挖钻机产品对比表 (Zoomlion Rotary Drilling Rig Comparison Table)\n')
md.append('> 数据来源：`data/processed/rotary_rig_master.csv`（自 Zoomlion_Brochure_Data.xlsx 清洗，15 个型号，v0_2026-06-11）。')
md.append('> 单位以 `rotary_rig_field_dictionary.csv` 为准；斜杠组合值（如钻深 56/70 = 机锁杆/摩阻杆）原样保留，不拆解。N/A 表示原资料未提供。')
md.append('> 标注 ★ 的 7 个型号为 Demo 重点型号。\n')

md.append('## 一、核心 7 型号速查对比（Quick Compare）\n')
md.append('| 参数 Parameter | ' + ' | '.join(f'**{m}**{"★" if m in KEY_MODELS else ""}' for m in KEY_MODELS) + ' |')
md.append('|' + '---|' * (len(KEY_MODELS) + 1))
for key in QUICK_PARAMS:
    zh, en, unit = zh_en(key)
    label = f'{zh} {en}'
    if unit:
        label += f' ({unit})'
    vals = [cell_val(next(r for r in rows if r['model'] == m), key) for m in KEY_MODELS]
    md.append(f'| {label} | ' + ' | '.join(vals) + ' |')

md.append('\n## 二、全 15 型号参数总表（Full Spec Matrix）\n')
# capability order + group sections as separate sub-tables for readability
md.append('*按最大钻孔直径/扭矩升序排列。*\n')
all_cols = ['model'] + [k for _, cols in GROUPS.values() for k in cols]
# header row
hdr = ['型号 Model']
for _, cols in GROUPS.values():
    for k in cols:
        zh, en, unit = zh_en(k)
        label = f'{zh} {en}'
        if unit:
            label += f'\n({unit})'
        hdr.append(label)
md.append('| ' + ' | '.join(hdr) + ' |')
md.append('|' + '---|' * len(hdr))

for r in models_sorted:
    star = '★' if r['model'] in KEY_MODELS else ''
    line = [f'**{r["model"]}**{star}']
    for _, cols in GROUPS.values():
        for k in cols:
            line.append(cell_val(r, k))
    md.append('| ' + ' | '.join(line) + ' |')

md.append('\n## 三、选型速查（按桩径 / 桩深能力）\n')
md.append('| 型号 | 最大钻孔直径 (mm) | 最大钻深 (m) | 最大输出扭矩 (kN·m) | 工作质量 (t) |')
md.append('|---|---|---|---|---|')
for r in sorted(rows, key=lambda r: (dia_num(r), depth_max(r))):
    star = '★' if r['model'] in KEY_MODELS else ''
    md.append(f'| {r["model"]}{star} | {cell_val(r,"max_drilling_diameter_mm")} | {cell_val(r,"max_drilling_depth_m")} | {cell_val(r,"rated_output_torque_knm")} | {cell_val(r,"weight_t")} |')

md.append('\n### 选型规则（项目驱动）\n')
md.append('1. 客户给 **桩径 (diameter)** → 筛 `最大钻孔直径 ≥ 桩径` 的型号；')
md.append('2. 客户给 **桩深 (depth)** → 筛 `最大钻深（摩阻杆上限）≥ 桩深`；')
md.append('3. 在达标型号中，优先推荐 **最小余量**（smallest adequate margin）型号，兼顾运输尺寸与扭矩；')
md.append('4. 机锁杆 (Interlock) 能提供更高加压力，适合硬地层；摩阻杆 (Friction) 钻深更大。')

md.append('\n## 四、数据说明（Data Notes）\n')
md.append('**数据质量发现，销售使用前必读：**\n')
md.append('- **同参数后缀变体**：以下型号对在原始资料中参数完全一致，仅型号后缀不同——`ZR140 / ZR140R`、`ZR185H / ZR185R`、`ZR255H / ZR255R`、`ZR300L / ZR300D`。后缀（H/R/L/D）的官方含义**待确认**（可能为底盘/出口版本差异），对外介绍时勿当作不同性能档位。')
md.append('- **N/A 字段**：`ZR380D`、`ZR420GW` 的回转半径 (Swing Radius) 原始资料未提供，表中保留 N/A，不得编造。')
md.append('- **斜杠组合值**：最大钻深（如 `56/70`）、整机高度（如 `19324/20819`）、运输高（如 `3500/3790`）均对应 机锁杆/摩阻杆 或 不同配置，须原样展示并解释，禁止拆解或取单值。')
md.append('- **单位权威**：所有单位以 `rotary_rig_field_dictionary.csv` 为准，生成回复时不得擅自换算（例如不把 kN·m 写成 N·m）。')

md_text = '\n'.join(md) + '\n'
with open(PROJECT_ROOT / 'docs' / 'product_comparison.md', 'w', encoding='utf-8') as f:
    f.write(md_text)

print('markdown written:', len(md_text), 'chars')

# =====================================================================
# EXCEL workbook
# =====================================================================
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()

HDR_FILL = PatternFill('solid', fgColor='1F4E78')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
KEY_FILL = PatternFill('solid', fgColor='FFF2CC')
SECTION_FILL = PatternFill('solid', fgColor='D6E4F0')
SECTION_FONT = Font(bold=True, color='1F4E78', size=11)
NA_FONT = Font(color='9E9E9E', italic=True)
thin = Side(style='thin', color='BFBFBF')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(vertical='center', wrap_text=True)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)

def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = CENTER
        cell.border = BORDER

def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

# --- Sheet 1: 核心7型号速查对比 (transposed) ---
ws1 = wb.active
ws1.title = '核心7型号对比'
ws1.cell(row=1, column=1, value='参数 Parameter').font = HDR_FONT
ws1.cell(row=1, column=1).fill = HDR_FILL
ws1.cell(row=1, column=1).alignment = CENTER
ws1.cell(row=1, column=1).border = BORDER
for j, m in enumerate(KEY_MODELS, 2):
    c = ws1.cell(row=1, column=j, value=m)
    c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CENTER; c.border = BORDER
row = 2
for key in QUICK_PARAMS:
    zh, en, unit = zh_en(key)
    label = f'{zh} {en}'
    if unit: label += f' ({unit})'
    a = ws1.cell(row=row, column=1, value=label)
    a.font = Font(bold=True, size=10); a.alignment = WRAP; a.border = BORDER
    a.fill = PatternFill('solid', fgColor='F2F2F2')
    for j, m in enumerate(KEY_MODELS, 2):
        v = cell_val(next(r for r in rows if r['model'] == m), key)
        c = ws1.cell(row=row, column=j, value=v)
        c.alignment = CENTER; c.border = BORDER
        c.fill = KEY_FILL
        if v == 'N/A':
            c.font = NA_FONT
    row += 1
autosize(ws1, [30] + [11] * len(KEY_MODELS))
ws1.freeze_panes = 'B2'

# --- Sheet 2: 全15型号参数总表 (wide, grouped) ---
ws2 = wb.create_sheet('参数总表')
ws2.cell(row=1, column=1, value='型号 Model').font = HDR_FONT
ws2.cell(row=1, column=1).fill = HDR_FILL
ws2.cell(row=1, column=1).alignment = CENTER
ws2.cell(row=1, column=1).border = BORDER
col = 2
col_map = {}  # key -> excel col
for gname, cols in GROUPS.values():
    for k in cols:
        zh, en, unit = zh_en(k)
        label = f'{zh} {en}'
        if unit: label += f' ({unit})'
        c = ws2.cell(row=1, column=col, value=label)
        c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CENTER; c.border = BORDER
        col_map[k] = col
        col += 1
# section band row (merged group headers)
ws2.insert_rows(2)
col = 2
for gname, cols in GROUPS.values():
    start = col; end = col + len(cols) - 1
    if start < end:
        ws2.merge_cells(start_row=2, start_column=start, end_row=2, end_column=end)
    c = ws2.cell(row=2, column=start, value=gname)
    c.fill = SECTION_FILL; c.font = SECTION_FONT; c.alignment = CENTER
    c.border = BORDER
    for cc in range(start, end + 1):
        ws2.cell(row=2, column=cc).border = BORDER
        ws2.cell(row=2, column=cc).fill = SECTION_FILL
    col = end + 1
r = 3
for mr in models_sorted:
    star = '★' if mr['model'] in KEY_MODELS else ''
    c0 = ws2.cell(row=r, column=1, value=f'{mr["model"]}{star}')
    c0.font = Font(bold=True); c0.alignment = CENTER; c0.border = BORDER
    if star: c0.fill = KEY_FILL
    for gname, cols in GROUPS.values():
        for k in cols:
            v = cell_val(mr, k)
            c = ws2.cell(row=r, column=col_map[k], value=v)
            c.alignment = CENTER; c.border = BORDER
            if star: c.fill = KEY_FILL
            if v == 'N/A': c.font = NA_FONT
    r += 1
autosize(ws2, [12] + [12] * len(col_map))
ws2.freeze_panes = 'B3'

# --- Sheet 3: 选型速查 ---
ws3 = wb.create_sheet('选型速查')
ws3.cell(row=1, column=1, value='型号').font = HDR_FONT
ws3.cell(row=1, column=1).fill = HDR_FILL
ws3.cell(row=1, column=1).alignment = CENTER; ws3.cell(row=1, column=1).border = BORDER
sel_headers = ['最大钻孔直径 (mm)', '最大钻深 (m)', '最大输出扭矩 (kN·m)', '工作质量 (t)', '机锁杆', '摩阻杆']
sel_keys = ['max_drilling_diameter_mm', 'max_drilling_depth_m', 'rated_output_torque_knm', 'weight_t', 'interlock_kelly', 'friction_kelly']
for j, h in enumerate(sel_headers, 2):
    c = ws3.cell(row=1, column=j, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CENTER; c.border = BORDER
r = 2
for mr in sorted(rows, key=lambda r: (dia_num(r), depth_max(r))):
    star = '★' if mr['model'] in KEY_MODELS else ''
    c0 = ws3.cell(row=r, column=1, value=f'{mr["model"]}{star}')
    c0.font = Font(bold=True); c0.alignment = CENTER; c0.border = BORDER
    if star: c0.fill = KEY_FILL
    for j, k in enumerate(sel_keys, 2):
        c = ws3.cell(row=r, column=j, value=cell_val(mr, k))
        c.alignment = CENTER; c.border = BORDER
        if star: c.fill = KEY_FILL
        if cell_val(mr, k) == 'N/A': c.font = NA_FONT
    r += 1
autosize(ws3, [12, 14, 12, 14, 11, 14, 14])
ws3.freeze_panes = 'A2'

xlsx_path = PROJECT_ROOT / 'data' / 'processed' / 'rotary_rig_comparison_table.xlsx'
wb.save(str(xlsx_path))
print('xlsx written:', xlsx_path)
print('KEY models:', KEY_MODELS)
print('total models:', len(rows))
