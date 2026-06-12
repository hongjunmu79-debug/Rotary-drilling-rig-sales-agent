# 架构与设计决策 — 旋挖钻机 AI 销售助手

## 1. 总览

```mermaid
flowchart LR
    subgraph 数据层
        A[Zoomlion_Brochure_Data.xlsx<br/>原始 Excel] -->|src/clean_data.py<br/>可重复清洗| B[(rotary_rig_master.csv<br/>15型号×34字段)]
        A --> C[(rotary_rig_field_dictionary.csv<br/>31字段·单位唯一定义)]
        B --> D[(rotary_rig_model_cards.jsonl/.md<br/>15张事实卡→Dify知识库)]
    end
    subgraph 检索与计算层（零LLM）
        B --> E[param_lookup<br/>型号/字段识别+精确查询]
        B --> F[recommender<br/>达标筛选+确定性排序]
    end
    subgraph 生成层
        F --> G[reply_generator<br/>DeepSeek措辞 or 模板<br/>数字只来自facts]
    end
    subgraph 展示层
        E --> H[Streamlit app]
        F --> H
        G --> H
    end
    subgraph 质量层
        B --> I[run_eval.py<br/>30题·运行时基准·exit code]
    end
```

## 2. 关键设计决策（面试展开点）

### 决策 1：参数路径零 LLM
**问题**：Day 2 的 Dify RAG 版在 10 题测试中出现 1 处数值幻觉（钻径 2000→2200mm），且检索失效时模型会自信地编造（56/70→78/100m）。
**决策**：参数查询/对比/推荐全部走 CSV 结构化计算，LLM 只许碰"措辞"。
**效果**：数值幻觉从"提示词缓解"变为"架构消除"——Day 5 评测参数准确率 100% 是结构保证的，不是概率结果。

### 决策 2：单位与字段定义单点化
字段字典是单位的唯一权威（`max_drilling_depth_m` 的 unit=m 只定义一次），任何环节不许运行时换算。中英文字段名、数据类型（number/range_or_pair/text）、组合值语义都集中在字典里——这也是中英文自由文本查询能工作的基础。

### 决策 3：组合值与缺失值保真
- `56/70`（机锁杆/摩阻杆）原样保留为字符串，展示时解释而不拆解；推荐逻辑解析它但输出仍引用原值
- `N/A`（ZR380D/ZR420GW 回转半径）原样保留，查询返回 `not_available` 置信度而非空字符串或猜测值
- pandas 读取用 `dtype=str, keep_default_na=False`，防止 'N/A' 被吞成 NaN

### 决策 4：推荐排序的业务语义
排序键 =（重点型号优先）>（机锁杆可达标 > 仅摩阻杆达标）>（钻深余量小者优先）。
理由：重点型号是中东市场主推（卷扬加压 R/D/GW 系）；机锁杆是标准作业配置，"仅摩阻杆达标"意味着客户要接受配置约束；余量小 = 不向客户推过度配置的机器。

### 决策 5：LLM 降级必须可观测
`generate_reply` 返回 `{reply_text, mode, note}`：LLM 失败自动降级模板，note 披露原因（如 `HTTP 402 Payment Required`），UI 直接展示。本项目实际靠它定位了 DeepSeek 余额不足的问题。**降级不可耻，静默降级才可耻。**

### 决策 6：评测器防作弊
评分基准运行时从主表读取（评分器零硬编码参数）、字段识别要求精确唯一命中、推荐题独立重算达标集合交叉验证、陷阱题要求程序化证明、任何异常计 FAIL。满分必须经得起"裁判收买"质疑。

## 3. 两版架构对照

| 维度 | Dify 原型版 | Python 结构化版 |
|---|---|---|
| 搭建时间 | ~2 小时 | ~1.5 天 |
| 参数路径 | 知识库 RAG + 提示词约束 | CSV 精确查询（零 LLM） |
| 幻觉风险 | 低但非零（实测 1/23 数值） | 参数路径为零 |
| 来源引用 | Dify 内置 citations | 每答案注入来源三件套 |
| 适用 | 快速验证产品形态、演示 | 可信交付、可评测、可扩展 |
| 教训 | 经济索引对英文失效；草稿不发布即丢失 | Windows ARM64 需 x64 venv |

## 4. 已知局限

1. LLM 措辞模式下，未对输出做"逐数字回查"后校验（roadmap 第 2 项）；当前靠 temperature=0 + 提示词约束 + facts 注入
2. 字段识别基于词典匹配而非语义向量，超出词典表述（如"能打多深"）会落到友好失败而非智能理解——这是准确性优先的有意取舍
3. 评测集 30 题规模有限，未覆盖多轮对话场景
