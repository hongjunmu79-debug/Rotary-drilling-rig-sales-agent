# 面试材料包 — 旋挖钻机 AI 销售助手

> Day 7 产出。所有内容基于本项目 6 天真实经历，数字均可在 `docs/eval_report_day5.md` 与各日志中复核。

---

## 1. 三分钟 Demo 脚本（边演边讲）

**[0:00–0:20｜开场·定位]**
"我做的是面向中东市场旋挖钻机销售的 AI 销售助手。背景是我自己就是这个行业的海外销售——客户在询盘时要快速查参数、对比型号、判断选型，还要英语阿语回复。资料散在 Excel、PDF、宣传册里，查得慢、还容易答错。"

**[0:20–0:50｜先亮核心论点]**
"但工程机械销售有个特殊点：一个参数答错，可能导致错误选型和真金白银的损失。所以我整个产品的核心设计就一句话——**参数必须来自结构化数据，绝不能让大模型生成**。我先给你看为什么。"
> 演示：在 Dify 原型版里关掉正确检索，问 ZR255R 钻深，展示它如何自信地编出"78/100m"（真实值 56/70）。

**[0:50–1:40｜结构化版·参数查询]**
> 演示 Streamlit 版三连：
> 1. 英文问 ZR255R 钻深 → 56/70m + 机锁杆/摩阻杆配置解释 + 来源 + High 置信度
> 2. 中文问"ZR600GW 的最大输出扭矩" → 600 kN·m（展示中英文都行）
> 3. 问 ZR380D 回转半径 → "源数据为 N/A"，不编

"注意这三个回答里的数字，全部来自 CSV 精确查询，整条参数路径没有大模型参与。所以幻觉不是被'缓解'，是被架构'消除'了。"

**[1:40–2:20｜选型推荐 + 双语回复]**
> 演示：输入 60m/2000mm → 推荐 ZR300D 优先（重点型号、机锁杆可达标、余量最小）→ 一键生成英文/阿语客户回复。
"推荐是结构化筛选+确定性排序。大模型只在最后'措辞'这一步参与，而且回复里的每个数字都是从结构化结果注入的，提示词禁止它用任何 facts 之外的数。调用失败会自动降级模板，并在界面上告诉你为什么失败。"

**[2:20–3:00｜评测·收尾]**
> 演示：终端跑 `python src/run_eval.py` → 30 题、6 项指标全 100%、退出码 0。
"最后这步是我觉得最像产品经理的部分：我建了一套 30 题的可重复评测，覆盖查询、对比、推荐、回复、拒答陷阱。而且评分基准是运行时从源数据读的，不是写死在评分器里——防止自己给自己放水。这套东西能在每次改动后回归，保证系统不退化。"

---

## 2. 中文面试讲法（口语版，约 90 秒）

我做的是一个面向中东市场工程机械销售的 AI Sales Assistant。背景是销售面对客户询盘时，需要快速查询旋挖钻机参数、判断适配工况、生成英文或阿语回复，但传统资料分散、查询慢、参数容易混乱。

我设计的核心原则是：参数类问题必须以 Excel/CSV 结构化表为第一事实源，大模型只负责措辞、不碰数字。因为我在做 RAG 原型时亲眼看到——检索一失效，模型就会自信地编出错误参数，比如把钻深 56/70 编成 78/100。对工程机械销售这是致命的。

所以我做了两版：先用 Dify 快速验证产品形态，再用 Python+Streamlit 把参数路径做成纯结构化查询，幻觉从架构上消除。功能上覆盖参数查询、型号对比、选型推荐、英阿双语回复，每个回答都带数据来源，没有的数据直接拒答。

最后我建了一套 30 题的自动评测，参数准确率、单位、来源、拒答全部 100%，而且评分基准运行时从源数据读取防止放水。这个项目让我理解到，AI 产品经理不只是写提示词，而是要设计数据结构、检索策略、置信规则、评测体系和业务闭环。

---

## 3. 英文面试讲法（English pitch, ~90s）

I built an AI sales assistant for rotary drilling rig sales in the Middle East market. The context: a salesperson facing a customer inquiry needs to look up rig specs, judge model fit, and reply in English or Arabic — but the data is scattered across Excel and brochures, slow to search, and easy to get wrong.

My core design principle was that parameter questions must be answered from a structured CSV as the single source of truth — the LLM handles wording only, never the numbers. I learned this the hard way: while building a RAG prototype, I watched the model confidently invent a wrong spec — it turned a max drilling depth of 56/70 m into "78/100" the moment retrieval failed. For industrial equipment sales, that's a deal-breaker.

So I built two versions: a fast Dify prototype to validate the product shape, then a Python/Streamlit version where the parameter path is pure structured lookup — hallucination eliminated by architecture, not mitigated by prompting. It covers lookup, comparison, recommendation, and English/Arabic replies, every answer carries its source, and missing data is refused rather than invented.

Finally I built a 30-question evaluation harness — parameter accuracy, units, source attribution, and refusal all at 100%, with ground truth read from source data at runtime to prevent gaming the score. This project taught me that an AI PM isn't just writing prompts — it's designing the data schema, retrieval strategy, confidence rules, evaluation, and the full business loop.

---

## 4. 简历项目经历

### 中文
**中联重科旋挖钻机 AI 销售助手｜AI 产品经理作品集项目**
- 面向中东市场销售场景，独立设计并实现旋挖钻机 AI Sales Assistant，支持参数查询、型号推荐、英文/阿语客户回复生成，每个回答附数据来源、缺失数据自动拒答。
- 确立"参数必须来自结构化数据、大模型只负责措辞"的核心架构，将 Excel 清洗为 15 型号结构化事实源，设计字段字典与单位单点定义、组合值/缺失值保真规则，从架构上消除参数幻觉（先以 Dify 原型暴露幻觉风险，再用 Python+Streamlit 根治）。
- 构建 30 题自动评测管线，评分基准运行时取自源数据以防作弊，实现参数准确率/单位/来源/拒答 6 项指标 100%、可在每次迭代后回归。
- 全程以"规划+审核"主导、将编码任务委托给 AI 编程助手并对产出做代码审核与端到端实测，在审核中发现并修复了中文字段过匹配、LLM 静默降级等真实缺陷。
- 输出 PRD、技术架构、Demo 脚本、GitHub README，完整呈现 AI 产品从业务洞察到原型、评测、交付的闭环。

### English
**Zoomlion Rotary Drilling Rig AI Sales Assistant | AI Product Portfolio Project**
- Independently designed and built an AI sales assistant for Middle East rotary drilling rig sales: parameter lookup, model recommendation, and English/Arabic customer replies, with source attribution on every answer and automatic refusal on missing data.
- Established the core architecture "parameters come from structured data; the LLM only handles wording," cleaning the Excel brochure into a 15-model structured source of truth with a field dictionary, single-point unit definitions, and combined-/missing-value fidelity rules — eliminating parameter hallucination by design (first exposing the risk in a Dify prototype, then fixing it in a Python/Streamlit build).
- Built a 30-question evaluation harness with runtime ground truth to prevent score gaming, achieving 100% on all six metrics (parameter accuracy, units, source attribution, refusal, recommendation, reply quality) with re-runnable regression.
- Led the project as planner/reviewer, delegating implementation to an AI coding assistant and performing code review plus end-to-end testing — catching and fixing real defects including Chinese field over-matching and silent LLM fallback.
- Delivered PRD, technical architecture, demo script, and GitHub README, demonstrating the full AI-product loop from business insight to prototype, evaluation, and delivery.

---

## 5. 面试问答预案

**Q：你怎么保证大模型不胡说参数？**
A：根本上不让它碰参数。参数查询、对比、推荐都是 CSV 结构化计算，大模型只在客户回复的措辞环节出现，而且数字是从结构化结果注入的，系统提示词明确禁止使用 facts 之外的数字，temperature 设 0。这是架构隔离，不是靠提示词祈祷。

**Q：那大模型在这个产品里到底有什么用？**
A：措辞和多语言表达。把"ZR300D，钻深 62/94m，余量 34m"这种结构化事实，转成客户能直接收的专业英语/阿语邮件——这是大模型擅长且低风险的部分。它失败了还能降级到确定性模板，业务不中断。

**Q：为什么先做 Dify 又重做 Python？不是浪费？**
A：不浪费，是两个目的。Dify 两小时就能让我看到产品形态、验证交互、拿到可演示的东西；但我在它身上恰恰发现了幻觉风险——这反而成了 Python 版核心设计的依据。先快后稳，而且 Dify 版本身也是作品集的一部分。

**Q：你的评测凭什么可信？满分会不会是自己给自己放水？**
A：我专门做了防作弊设计。评分基准不是写死在评分器里的，而是运行时从源数据 CSV 读的；字段识别要求精确唯一命中；推荐题独立重算一遍达标集合交叉验证；陷阱题要求程序化证明（比如"能钻100m吗"要程序验证 44/56<100）；任何异常一律计 FAIL。满分是经得起"裁判被收买"质疑的。

**Q：这个项目你自己写了多少代码？**
A：我主导规划、设计和审核，具体编码委托给 AI 编程助手，但我对每一份产出做代码审核和端到端实测。价值恰恰体现在审核上——比如它写的单测全绿，我实测时却发现中文查"最大输出扭矩"会把"最大钻孔直径/深度"一起匹配出来，这种"测试过了但真实场景翻车"的缺陷只有人工审核+实测能抓到。这正是 AI 时代产品经理/技术负责人的核心能力。

**Q：局限性？**
A：三个。一是 LLM 措辞模式我还没做输出数字的逐位回查后校验，目前靠 temperature0+facts 注入；二是字段识别是词典匹配不是语义理解，超出词典的问法会落到友好失败，这是准确性优先的有意取舍；三是评测 30 题规模有限、没覆盖多轮对话。这些都在 roadmap 里。

**Q：怎么扩展到其他产品线？**
A：数据清洗管线和评测框架是可复用的。原始 Excel 里其实还有液压抓斗、双轮铣等品类，加新品类就是跑一遍清洗脚本生成新的结构化源+扩充评测集，架构不用动。

---

## 6. JD 对齐表

| 岗位能力项 | 本项目对应证据 |
|---|---|
| ToB / 行业 AI 产品 | 真实工程机械销售场景，业务痛点来自亲身经历 |
| RAG / Agent 理解 | 两版架构对照，深刻理解检索失效→幻觉的因果 |
| 数据策略 | 第一事实源、字段字典、组合值/缺失值保真规则 |
| 评测 / 数据驱动 | 30 题自动评测、6 指标、防作弊设计、可回归 |
| 风控意识 | 拒答、来源追溯、过度承诺防护、可观测降级 |
| 技术沟通 | PRD、架构图、Demo 脚本、README 完整交付 |
| AI 协作能力 | 规划+审核主导，委托编码并把控质量 |

---

## 7. 七天复盘

| Day | 目标 | 实际产出 | 关键收获 |
|---|---|---|---|
| 1 | 数据清洗 v0 | 15 型号主表+字段字典+事实卡+清洗报告 | 第一事实源、单位独立、组合值保真 |
| 2 | Dify RAG 原型 | 可演示应用，10 题 9.5/10 | 亲眼见到幻觉，确立核心设计原则 |
| 3 | Python 结构化版 | Streamlit 零 LLM 参数查询 | 幻觉从架构消除；审核抓出中文过匹配 bug |
| 4 | 推荐+双语回复 | 结构化筛选+LLM 措辞+模板降级 | 可观测降级；LLM 只碰措辞 |
| 5 | 评测体系 | 30 题管线，6 指标 100% | 防作弊评测设计，从"能跑"到"可信" |
| 6 | 作品集包装 | PRD+README+架构文档 | 把工程事实翻译成产品叙事 |
| 7 | 面试表达 | Demo 脚本+面试讲法+简历+问答 | 把 6 天经历提炼成可讲的故事线 |

**最重要的一条认知**：这一周真正的产品决策不是"用什么模型"，而是"哪些环节根本不该用模型"。把幻觉风险最高的参数路径彻底排除大模型，反而做出了一个可信的 AI 产品。这就是 AI 产品经理的判断力。
