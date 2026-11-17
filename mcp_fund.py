# -*- coding: utf-8 -*-
"""基金数据 API 的 MCP Server —— 让 AI Agent 直接查询基金数据。

配置（Claude Desktop / Cursor / Dify / 任意 MCP 客户端）：

```json
{
  "mcpServers": {
    "fundapi": {
      "command": "python",
      "args": ["/path/to/mcp_fund.py"],
      "env": {
        "FUND_API": "https://api.fundapi.cn",
        "FUND_KEY": "cf-xxxxxxxx"
      }
    }
  }
}
```

配置后可以直接说：
  "易方达消费行业这只基金怎么样"
  "它上季新进了哪些股票"
  "这只基金换过几次基金经理"
  "我这两只基金有没有重复买"
  "帮我找几只晨星五星的消费主题基金
→ AI Agent 自动调用下面的工具拿真实数据（不是编造）。

自测：python mcp_fund.py --selftest
"""
import asyncio
import json
import os
import sys

import requests

API = os.environ.get("FUND_API", "https://api.fundapi.cn").rstrip("/")
KEY = os.environ.get("FUND_KEY", "").strip()
_PRICING_URL = "https://fundapi.cn/pricing"

# 档位价格（工具描述专用）—— **本文件唯一出处**。
# 🔴 MCP 是发给客户端的独立脚本（客户机器上没有 `fundkeys.py`）⇒ 物理上无法共享
#    `TIERS[...]` 这个真源。所以这里收敛成**一个**常量，⛔ 描述里不许再写字面量。
# ⚠️ **改价必改此处**（与 `fundkeys.TIERS` 同步）。
# ⚠️ 基金线**没有 trial / standard 档**，跟股票线不是一套价格，⛔ 不要照抄。
# ⚠️ 机构版（institutional）= ¥299/月 · ¥2,999/年（2026-11-13 起标价，不再面议）
_PRICE = {"free": "免费", "trial": "体验版 ¥9.9/7天", "pro": "¥59/月", "institutional": "¥299/月"}

# 服务版本：格式 `YYYY.M.D`（不补零，否则不是合法 SemVer），取值 = REST 的 VERSION 日期
SERVER_VERSION = "2026.11.17"


# ── 工具定义（表驱动：name → (路径, 说明, 参数 schema)）─────────
def _p(name, typ, desc, required=False):
    d = {"type": typ, "description": desc}
    return name, d, required


TOOLS = {
    # ══════════ 免费工具（无需 Key）══════════
    "fund_search": (
        "/v1/fund-search",
        ("按代码 / 名称 / 拼音搜索基金，返回代码 + 名称。"
         "**用户只说了基金名字、没给代码时先用这个**（如「易方达消费行业」→ 110022）。"
         "⚠️ 单次最多 10 条 —— 这是数据源搜索接口的边界，不是我们截断。"
         "· 免费工具（无需 Key）"),
        [_p("q", "string", "关键词：基金代码 / 名称 / 拼音首字母", True),
         _p("limit", "integer", "返回条数，1-50，默认 20")],
    ),
    "fund_profile": (
        "/v1/fund-profile",
        ("单只基金档案，一次拿齐：申购费率（原价/现价/起购金额）、10 档阶段涨幅"
         "（每档含同类均值 / 沪深300 / 同类排名 / 同类总数）、现任经理（星级/从业年限/"
         "在管规模/能力评分）、规模变动 5 期、股票·债券·现金仓位、持有人结构"
         "（机构/个人占比）、前 10 重仓股票代码。"
         "**用户问「这只基金怎么样 / 费率多少 / 规模多大 / 最近涨得如何 / 谁在管」用这个。**"
         "⚠️ 档案里没有的深度内容：这季调了什么 → fund_holding_changes；"
         "换过几次人 → fund_manager_history；和别的基金比 → fund_compare。"
         "· 免费工具（无需 Key）"),
        [_p("code", "string", "6 位基金代码，如 110022", True)],
    ),
    "fund_screener_options": (
        "/v1/fund-screener-options",
        ("筛选项字典：6 大类 30 个细分类型 / 188 家基金公司 / 25 个主题 / "
         "收益区间档位 / 6 家机构评级 / 13 个排序字段。"
         "⭐ **调 fund_screener 之前先调这个** —— 否则不知道 `type` 该传 `x2002` 还是 `x3008`，"
         "也不知道收益区间 1-5 各代表什么档。"
         "· 免费工具（无需 Key）"),
        [],
    ),

    # ══════════ 专业版 ¥59/月 ══════════
    "fund_nav": (
        "/v1/fund-nav",
        ("历史净值：单位净值、累计净值、日增长率、申购赎回状态，按日期倒序分页。"
         "**用户问「净值走势 / 某天的净值是多少 / 最近跌了多少」用这个。**"
         "⚠️ 要画图就把 size 开到 200 再翻页；一次最多 200 条。"
         "⚠️ 日线是**实时**的（当日已更新），不是 T-1。"
         f"⚠️ **付费工具**：体验版（{_PRICE['trial']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True),
         _p("page", "integer", "页码，从 1 开始"),
         _p("size", "integer", "每页条数，1-200，默认 20"),
         _p("start", "string", "起始日 YYYY-MM-DD，留空不限"),
         _p("end", "string", "结束日 YYYY-MM-DD，留空不限")],
    ),
    "fund_holdings": (
        "/v1/fund-holdings",
        ("季报持仓明细：前 10 大重仓股的名称、代码、占净值比例、持股数（万股）、"
         "持仓市值（万元），全部为报告期末数据（⛔ 不含实时股价）。"
         "**用户问「这只基金买了什么股票 / 重仓哪些」用这个。**"
         "⚠️ 季报法定只披露**前十大**，半年报/年报才披露全部 —— 所以这份名单不等于全部持仓。"
         "⚠️ 想知道「这季动了什么」（新进/跌出/加减仓）请用 fund_holding_changes，"
         "它做了两期对比和披露方式处理。"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True),
         _p("year", "string", "报告年份 YYYY，留空=最新一期"),
         _p("quarter", "string", "季度 1/2/3/4，留空=最新一期")],
    ),
    "fund_managers": (
        "/v1/fund-managers",
        ("**回答：这只基金现在谁在管、管了多久、能力怎么样。**\n"
         "返回在任经理：姓名、星级、任职年限（如「14年又48天」）、在管规模（如「175.06亿(4只基金)」）。\n"
         "① `power` 综合能力分 + 5 个分项（经验值 / 收益率 / 抗风险 / 稳定性 / 择时能力）\n"
         "② `profit` 任期收益 vs 同类平均 vs 沪深300（含 as_of 日期）\n"
         "⚠️ `fund_size` 括号里是**在管只数**，⛔ 不是本基金规模（本基金规模看 `fund_profile`）。\n"
         "⚠️ 要「换过几次经理、历任任期回报」用 `fund_manager_history`（机构版）。\n"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位场外基金代码，如 110022", True)],
    ),
    "fund_rank": (
        "/v1/fund-rank",
        ("全市场基金排行：按类型（全部/股票/混合/债券/指数/QDII/FOF）+ "
         "单个区间（近1周/近1月/近3月/近6月/近1年/近2年/近3年/今年来/成立来）排序，分页返回。"
         "每行含代码、名称、净值、当日涨跌幅、**9 个区间收益**、成立日、申购费（原价/现价）。"
         "**用户问「最近一年哪些基金涨得最好 / 股票型排行 / 近 3 年翻倍的基金有哪些」用这个。**\n"
         "⚠️ 跟 fund_screener 的分工：本工具只能按「类型 + 单个区间」排；"
         "要按机构评级 / 基金公司 / 主题 / 多个收益区间组合筛选，用 fund_screener（机构版）。\n"
         "⚠️ 排行是「同类内的绝对收益排序」，**不含风险调整**（不看回撤/波动），"
         "⛔ 不要把它当成推荐 —— 排在前面只说明这段时间涨得多。\n"
         f"⚠️ **付费工具**：体验版（{_PRICE['trial']}）及以上。"),
        [_p("ft", "string", "类型：all（默认）/ stock / hybrid / bond / index / qdii / fof"),
         _p("sort", "string", "排序区间：1w / 1m / 3m / 6m / 1y（默认）/ 2y / 3y / ytd / since / day"),
         _p("order", "string", "desc（默认，涨得多的在前）/ asc"),
         _p("page", "integer", "页码，1 起"),
         _p("size", "integer", "每页条数，1-200，默认 50")],
    ),
    "fund_notices": (
        "/v1/fund-notices",
        ("基金公告：分红、定期报告（季报/半年报/年报）、人事变更、估值调整、"
         "系统维护通知等，按发布日期倒序分页。"
         "**用户问「这只基金最近有什么公告 / 什么时候分红 / 换经理发公告了吗」用这个。**"
         "⭐ 这是本产品线**唯一**含公告的工具 —— 档案、持仓、调仓、经理四个工具都不含公告内容。\n"
         "⚠️ `category` 是数据源的**数字码**（3=定期报告、6=公司公告），"
         "⛔ **不要直接报给客户**，要讲标题本身或翻译成人话。\n"
         "⚠️ `publish_time` 的时分秒是补齐的（数据源只给到日期），只能当日期用。"
         f"⚠️ **付费工具**：体验版（{_PRICE['trial']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True),
         _p("page", "integer", "页码，1 起"),
         _p("size", "integer", "每页条数，1-50，默认 20")],
    ),
    "fund_overlap": (
        "/v1/fund-overlap",
        ("多基金持仓重叠：2-10 只基金**共同持有**哪些股票、各自**独有**哪些、各占净值多少。"
         "**用户问「我这几只是不是买了同一批股票 / 重叠多少 / 会不会重复买」用这个。**\n"
         "返回 `common_count`（共同持有几只）+ `common[]`（共同持有明细，含各基金自己的占比）+ "
         "`only_in`（按基金分组的独有持仓）+ `coverage: top10` + `report_period`。\n"
         "⚠️ 只覆盖季报披露的**前 10 大**，不等于全部持仓 —— 两只基金可能在第 11-20 名上也有重叠，"
         "本工具看不到。\n"
         "⚠️ 跟 fund_portfolio_diagnose 的分工：本工具**只算重叠**，轻量；"
         "要行业暴露 / 重仓股穿透 / 仓位逐季变化 / 费率合计，用 diagnose（机构版）。"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("codes", "string", "2-10 只基金代码，逗号分隔，如 110022,009265", True)],
    ),

    # ══════════ 机构版 ¥299/月 ══════════
    "fund_portfolio_xray": (
        "/v1/fund-portfolio-xray",
        ("**回答：我这一篮子基金合起来，实际买的是哪些股票、各占多少。**\n"
         "输入基金代码 + 权重，穿透到个股层面：\n"
         "① `xray_weight_pct` 该股在你**整个组合**里的综合权重（已含基金权重，⛔ 不用再乘）\n"
         "② `via` 来源拆解：哪几只基金持有、各贡献多少（contrib_pct）\n"
         "③ `covered_weight_pct` 穿透覆盖了多少净值\n"
         "⚠️ 只穿透季报前十大，`covered_weight_pct` 不到 100% 是正常的，⛔ 不要按 100% 凑满。\n"
         "⚠️ 权重传 `0.6,0.4` 或 `60,40` 都行。\n"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("codes", "string", "基金代码，逗号分隔，如 110022,009265", True),
         _p("weights", "string", "对应权重，逗号分隔，如 0.6,0.4（或 60,40）", True)],
    ),
    "fund_holding_changes": (
        "/v1/fund-holding-changes",
        ("**回答：这只基金上季新进了哪些股票、跌出前十的是哪些、加仓减仓幅度多大。**\n"
         "⭐ 核心规则：**只在两期都完整披露的前 N 名范围内对比**。"
         "季报法定只披露前十大、半年报披露全部（实测同一只基金 Q3 披露 13 只、Q2 披露 48 只），"
         "直接做集合差会把「披露方式不同」误读成「清仓 35 只」。"
         "所以：`new_in` 是**新进前十**（不是新买入，可能只是从第 11 名升上来）；"
         "`out` 是**跌出前十**（不是清仓，季报根本没披露到它）；"
         "只有 `increase` / `decrease`（按股数算）是真实的加减仓。\n"
         "⭐ **权重涨但股数没动 ≠ 加仓** —— 那是净值波动。实测茅台权重 9.77→9.96 而股数 80→80 不动。\n"
         "返回：summary（新进/掉出/加仓/减仓/没动 + 前 N 权重变化 + 两期披露数）、"
         "changes[]（逐只动作含股数变化百分比）、history[]（多期趋势）、method、note。"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("code", "string", "6 位基金代码，如 110022", True),
         _p("periods", "integer", "回溯几个报告期做趋势，2-8，默认 4"),
         _p("top_n", "integer", "对比范围取前几名，5-20，默认 10")],
    ),
    "fund_manager_history": (
        "/v1/fund-manager-history",
        ("**回答：这只基金换过几次人、现在这个是不是新来的、有没有一拖多。**\n"
         "返回：`current[]`（现任经理的星级 / 从业年限 / 在管规模与只数 / 5 维能力评分 / "
         "本基金任期收益 vs 同类均值 vs 沪深300）、`stability`（任期段数 / 人数 / "
         "平均任期 / 最短任期 / 上次变更距今多少天 / 是否一年内换过人）、"
         "`history[]`（历任任期区间 + 每段回报）、`flags[]`（一拖多 / 评分偏低 / 近期换人）。\n"
         "⚠️ **两个数字含义不同，别混**：「在管 175 亿」是这个人管的**所有基金合计**，"
         "不是他管这一只的规模（实测同一位经理在两只基金上，在管规模与能力评分完全一样，"
         "但任期收益一个是 264.68%、一个是 -26.02%）。\n"
         "⚠️ 能力评分的维度**随类型变**：股票型是抗风险/择时，指数型是跟踪误差/超额收益，"
         "货基是影响力/管理规模 —— 跨基金不能直接比。\n"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("code", "string", "6 位基金代码，如 110022", True)],
    ),
    "fund_portfolio_diagnose": (
        "/v1/fund-portfolio-diagnose",
        ("**回答：我这个组合到底押在哪儿、有没有重复买。**\n"
         "输入 1-6 只基金 + 权重，返回五块：\n"
         "① `industry_exposure` 行业暴露（加权，含前 3 / 前 5 集中度）\n"
         "② `top_holdings` 重仓股穿透（合起来实际买了哪些股票，每只标明来自哪几只基金、各贡献多少）\n"
         "③ `overlap` 两两持仓重叠（共同持有几只）\n"
         "④ `position_trend` 权益仓位逐季变化（最多 8 季）\n"
         "⑤ `fee` 费率合计（管理费 + 托管费加权）\n"
         "⚠️ 行业名称按数据源分类给出：A 股走证监会门类（制造业/采矿业），"
         "港股走港股行业分类（非必需消费品/电信服务），**同名才可相加**，不是统一分类体系。\n"
         "⚠️ 权重传 `0.6,0.4` 或 `60,40` 都行，服务端会按比例换算（0.6,0.4 与 60,40 等价）。\n"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("codes", "string", "1-6 只基金代码，逗号分隔，如 110022,009265", True),
         _p("weights", "string", "对应权重，逗号分隔，如 0.6,0.4（或 60,40）", True)],
    ),
    "fund_screener": (
        "/v1/fund-screener",
        ("**回答：按条件横着筛全市场 3.2 万只基金。**\n"
         "可按 6 大类/30 个细分类型、188 家基金公司、25 个主题、"
         "6 个收益区间（近1月/近3月/近6月/近1年/近2年/近3年/近5年/今年来）、"
         "6 家机构评级（晨星·海通·济安金信·招商·银河3年·银河5年）筛选，"
         "按 13 个字段排序，分页返回。每行含代码/名称/类型/公司/规模/9 档收益/6 家评级。\n"
         "⭐ **先调 fund_screener_options 拿 id 字典** —— `x2002`、`S20`、`80000229` 这类参数不要猜。\n"
         "⚠️ 多个条件是「与」关系，条件越多越容易筛空；筛空了返回的 `hint` 会说怎么放宽。\n"
         "⚠️ 一次最多 200 条，要全市场请分页（约 162 次）。\n"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("type", "string", "大类 id，如 x2002（股票型），取值见 fund_screener_options"),
         _p("sub_type", "string", "细分 id，如 x3008（指数型）"),
         _p("company", "string", "基金公司 id 或中文名，如 80000229 / 易方达基金"),
         _p("subject", "string", "主题 code，如 S20（医药主题）"),
         _p("w4", "integer", "近1月收益区间 1-5，0=不筛"),
         _p("w13", "integer", "近3月收益区间 1-5，0=不筛"),
         _p("w26", "integer", "近6月收益区间 1-5，0=不筛"),
         _p("w52", "integer", "近1年收益区间 1-5，0=不筛"),
         _p("y2", "integer", "近2年收益区间 1-5，0=不筛"),
         _p("y3", "integer", "近3年收益区间 1-5，0=不筛"),
         _p("y5", "integer", "近5年收益区间 1-5，0=不筛"),
         _p("yn", "integer", "今年来收益区间 1-5，0=不筛"),
         _p("morningstar", "integer", "晨星评级 1-5 星，0=不筛"),
         _p("haitong", "integer", "海通评级 1-5 星，0=不筛"),
         _p("jianxin", "integer", "济安金信评级 1-5 星，0=不筛"),
         _p("zhaoshang", "integer", "招商评级 1-5 星，0=不筛"),
         _p("yinhe3", "integer", "银河3年评级 1-5 星，0=不筛"),
         _p("yinhe5", "integer", "银河5年评级 1-5 星，0=不筛"),
         _p("sort", "string", "排序：1w/1m/3m/6m/1y/2y/3y/5y/ytd/since/scale/nav/inception/morningstar，默认 scale（规模降序）"),
         _p("order", "string", "desc / asc，默认 desc"),
         _p("page", "integer", "页码，1 起"),
         _p("size", "integer", "每页条数，1-200，默认 50")],
    ),
    "fund_compare": (
        "/v1/fund-compare",
        ("**回答：这几只基金到底差在哪。**\n"
         "2-5 只并列：10 档收益（每档含同类均值/沪深300/排名/同类总数/超额）、"
         "申购费、管理费+托管费、现任经理、前 10 重仓、行业 top5、规模、股票仓位、"
         "机构持有比例，加两两持仓重叠。\n"
         "⭐ **只并列、不排序、不给结论** —— 哪只更好取决于风险偏好、持有期和仓位，"
         "不是数据能替客户回答的问题。所以本工具**没有**综合评分、没有推荐字段。\n"
         "⭐ 会自动提示三类陷阱：\n"
         "① `same_share_class` 同一只基金的 A/C 份额（去掉份额后缀后同名）—— 不是两只基金，"
         "收益差主要来自费率结构；\n"
         "② `cross_category` 跨类别（用「近1年」那一档的同类总数判断）—— 排名不可直接比，"
         "「300/1034」和「300/4557」不是同一个含金量；\n"
         "③ `money_fund_mixed` 混了货币基金 —— 货基不披露股票持仓、不做行业配置，各项不可比。\n"
         f"⚠️ **付费工具**：机构版（{_PRICE['institutional']}）。"),
        [_p("codes", "string", "2-5 只基金代码，逗号分隔，如 110022,009265", True)],
    ),

    # ══════════ 2026-11-08 新增四个 ══════════
    "fund_estimate": (
        "/v1/fund-estimate",
        ("**回答：这只基金今天大概涨跌多少**（净值要等到晚上才公布）。\n"
         "两种估算方式并列：`realtime` 实时估算（约 3 分钟一档：估算净值 / 估算涨跌幅 / 估值时间），"
         "`model` 持仓模型估算（用季报前十大 × 个股当日涨跌，带逐股明细，"
         "能看出「今天涨是因为哪只票」）；另给 `is_trading_day` 是否交易日。\n"
         "🔴 **这是估算值，不是实际净值** —— 实际净值以基金公司公布为准，两者可能差几个点。"
         "回答时**必须**说清是「估算」，⛔ 不能直接说成「净值」。\n"
         "⚠️ `estimate_pct` / `estimated_pct` 单位是 %（0.05 表示涨 0.05%）。\n"
         "⚠️ 债基 / 货基 / 纯债没有股票仓位，`has_estimate` 会是 false 并给 `reason` —— "
         "这是正常结果，不是故障。\n"
         "⚠️ 休市时 `realtime.is_prev_day_value` 为 true，表示那是上一交易日的定格值。\n"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True)],
    ),
    "fund_dividends": (
        "/v1/fund-dividends",
        ("**回答：这只基金分过红吗 / 每次分多少 / 什么时候到账 / 拆分过几次。**\n"
         "`dividends` 历史分红（每 10 份派现金额、权益登记日、除息日、发放日）+ "
         "`splits` 份额折算（比例，如 1:1.4982）+ `notices` 分红公告标题。\n"
         "⚠️ `per_10` 是原文「每10份派现金0.1000元」，⛔ 不是每份金额；"
         "`splits` 是份额折算，与现金分红是两回事，⛔ 别混在一起算收益。\n"
         "⚠️ 公告只给 `id` 不给外链，要原文按 `id` 检索。\n"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 000001", True)],
    ),
    "fund_trade_rule": (
        "/v1/fund-trade-rule",
        ("**回答：今天买什么时候确认 / 卖出几天到账 / 在哪个平台买手续费便宜。**\n"
         "申赎状态、起购金额、单日上限、管理费 / 托管费 / 销售服务费、"
         "申购费分档表（标准价 + 代销平台折扣价）、赎回费按持有天数分档、"
         "买入与卖出的确认到账节奏（T+N）、交易规则说明。\n"
         "⭐ 这是本产品线**独有**的一项：别家只给标准费率，不给渠道折扣价，"
         "而「在哪个平台买便宜」正是客户真金白银关心的问题。\n"
         "⚠️ `fees.buy_discount` / `buy_rates[].discount_rate` 是**某代销平台**的报价，"
         "⛔ 不代表所有渠道，回答时要说明「以你实际下单的平台为准」。\n"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True)],
    ),
    "fund_rating": (
        "/v1/fund-rating",
        ("**回答：这只基金评级怎么样 / 这几年评级是在升还是在降。**\n"
         "逐报告期一行（按季度），每行给 6 家机构星级：招商证券 / 上海证券（三年·五年）/ "
         "济安金信 / 晨星（三年）/ 海通证券。\n"
         "⭐ 逐期并列能看出评级**趋势** —— 只看最新一期看不出「正在被降级」。\n"
         "⚠️ `rating` 为 null 表示**该机构当期未评级**，⛔ 不是 0 星，也不是取数失败；"
         "实测不少基金只有招商和晨星有值，回答时⛔ 别把 null 说成「评级很低」。\n"
         "⚠️ 招商证券与晨星为 5 星制，越高越好。\n"
         f"⚠️ **付费工具**：专业版（{_PRICE['pro']}）及以上。"),
        [_p("code", "string", "6 位基金代码，如 110022", True),
         _p("page", "integer", "页码，从 1 开始，默认 1"),
         _p("size", "integer", "每页条数，1-50，默认 20")],
    ),
}


def _call(path: str, **params):
    """调我们的 REST API。

    ⚠️ 鉴权走 `Authorization: Bearer`（服务端 query 和 header 都认，
    但 header 不会把 Key 留在 URL / 访问日志里，优先用它）。
    """
    p = {k: v for k, v in params.items() if v not in (None, "")}
    h = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        r = requests.get(API + path, params=p, headers=h, timeout=60)
        return r.status_code, r.text
    except Exception as e:
        return 0, json.dumps({"error": f"请求失败: {type(e).__name__}: {e}"},
                             ensure_ascii=False)


def _friendly(status: int, text: str) -> str:
    """把 REST 的错误换成「AI Agent 和客户都能看懂、且知道下一步做什么」的话。

    🔴 这一层唯一必须写对的事：**403 不能说成「服务出错」**。
       403 = 档位不够，是「该升级」；说成「查询失败、稍后再试」的话，
       AI Agent 会照原话告诉客户，客户就永远不知道该掏钱 —— 这是最伤转化的一种错。

    基金线的状态码语义（`app.py::_auth`）：
        401  没配 Key / Key 无效
        403  档位不够（body 带 error + hint + upgrade）或额度用完
        429  限流（body 带 retry_after_s）
        200  `ok:true` 正常；`ok:false` 是**业务错误**（如代码查不到）⇒ 直接返回
    """
    try:
        j = json.loads(text)
    except Exception:                                    # noqa: BLE001
        return text

    # 业务错误与正常结果都直接返回
    if status == 200:
        return text

    err = (j.get("error") or "").strip()
    hint = (j.get("hint") or "").strip()
    upgrade = (j.get("upgrade") or "").strip()

    if status == 401:
        if not KEY:
            return ("该工具属付费层，需要 API Key。请在 MCP 客户端配置里把 `FUND_KEY` "
                    f"设成你的 Key。免费工具（fund_search / fund_profile / "
                    f"fund_screener_options）无需 Key 即可用。"
                    f"专业版 {_PRICE['pro']}，机构版（{_PRICE['institutional']}）。"
                    f"档位与购买：{_PRICING_URL}")
        return f"{err}。{hint}" if hint else (err or "Key 无效或已停用")

    if status == 403:
        # 档位不够：必须说清「升哪个档、去哪儿升」
        if "档" in err:
            return (f"{err}（{hint}）。这个能力属**机构版**"
                    f"（{_PRICE['institutional']}，需联系开通）。"
                    f"升级说明：{upgrade or _PRICING_URL}")
        # 额度用完
        return f"{err}。{hint}" if hint else (err or "额度已用完")

    if status == 429:
        wait = j.get("retry_after_s")
        base = err or "请求过于频繁"
        if hint:
            base += f"。{hint}"
        if wait:
            base += f"（约 {wait} 秒后可重试）"
        return base + f"。需要更高频率请升级档位：{_PRICING_URL}"

    if status == 0:
        return (j.get("error") or "请求失败") + \
               f"。请检查 `FUND_API` 是否可访问（当前 {API}）"

    # 其余（500/502/503）如实说，⛔ 不猜原因
    return f"数据服务返回 HTTP {status}：{err or text[:200]}"


# ── MCP 接线（同一份工具表，兼容 mcp SDK 1.x 与 2.x）────────────────────────
#  1.x：`Server(...)` + `@server.list_tools()` / `@server.call_tool()` 装饰器注册
#  2.x：`Server(..., on_list_tools=…, on_call_tool=…)` 回调注册
#  两版只差在「工具怎么挂上去」—— TOOLS 表与 _call 跟协议层解耦，
#  换 SDK 大版本不必动工具定义。
def build_server():
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from mcp import types

    def _tool_list():
        out = []
        for name, (path, desc, ps) in TOOLS.items():
            props, req = {}, []
            for pname, schema, required in ps:
                props[pname] = schema
                if required:
                    req.append(pname)
            out.append(types.Tool(
                name=name,
                description=f"{desc}（额度消耗 1 次）",
                inputSchema={"type": "object", "properties": props,
                             **({"required": req} if req else {})}))
        return out

    async def _invoke(name: str, arguments) -> str:
        if name not in TOOLS:
            return f"未知工具：{name}"
        status, text = await asyncio.to_thread(_call, TOOLS[name][0], **(arguments or {}))
        return _friendly(status, text)

    if hasattr(Server, "list_tools"):          # ── mcp SDK 1.x：装饰器式
        server = Server("fund-data-api", version=SERVER_VERSION)

        @server.list_tools()
        async def list_tools():
            return _tool_list()

        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return [types.TextContent(type="text",
                                      text=await _invoke(name, arguments))]

    else:                                      # ── mcp SDK 2.x：回调式
        async def on_list_tools(ctx, params):
            return types.ListToolsResult(tools=_tool_list())

        async def on_call_tool(ctx, params):
            text = await _invoke(params.name, params.arguments)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=text)])

        server = Server("fund-data-api",
                        version=SERVER_VERSION,
                        on_list_tools=on_list_tools,
                        on_call_tool=on_call_tool)

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream,
                             server.create_initialization_options())

    return main


# 自测用的参数（每个工具一个最小可用调用）
_SELFTEST_ARGS = {
    "fund_search": {"q": "易方达消费行业", "limit": 3},
    "fund_profile": {"code": "110022"},
    "fund_screener_options": {},
    "fund_nav": {"code": "110022", "size": 2},
    "fund_holdings": {"code": "110022"},
    "fund_managers": {"code": "110022"},
    "fund_rank": {"ft": "stock", "sort": "1y", "size": 2},
    "fund_notices": {"code": "110022", "size": 2},
    "fund_overlap": {"codes": "110022,009265"},
    "fund_portfolio_xray": {"codes": "110022,009265", "weights": "0.6,0.4"},
    "fund_holding_changes": {"code": "110022", "periods": 2},
    "fund_manager_history": {"code": "110022"},
    "fund_portfolio_diagnose": {"codes": "110022,009265", "weights": "0.6,0.4"},
    "fund_screener": {"morningstar": 5, "size": 2},
    "fund_compare": {"codes": "110022,009265"},
    # 2026-11-08 新增四个
    "fund_estimate": {"code": "110022"},
    "fund_dividends": {"code": "000001"},
    "fund_trade_rule": {"code": "110022"},
    "fund_rating": {"code": "110022", "size": 2},
}


def selftest():
    """自测：直连 REST 验证工具可用性（不启 MCP）。"""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"API = {API}")
    print(f"KEY = {KEY[:12]}..." if KEY else "KEY = (未设，只能测免费工具)")
    print(f"工具数 = {len(TOOLS)}")
    free_n = sum(1 for _, d, _ in TOOLS.values() if "免费工具" in d)
    bad = 0
    gated = []
    for name, (path, desc, ps) in TOOLS.items():
        args = _SELFTEST_ARGS.get(name, {})
        st, body = _call(path, **args)
        text = _friendly(st, body)
        if st == 200 and '"ok":true' in body.replace(" ", ""):
            ok, note = True, ""
        elif st in (401, 403):
            # 档位门槛：没配 Key（401）或当前档位不够（403）。
            # ⚠️ 这不算失败，但**必须列出来** —— 如果 Key 已开通机构版却看到 GATED，
            #    那就是真问题（档位配置不对），不能静默放过。
            ok, note = True, "  GATED %d（%s）" % (
                st, "未配 Key" if st == 401 else "当前档位不够")
            gated.append(name)
        else:
            ok, note = False, ""
            bad += 1
        print(f"\n--- {name} {args} ---")
        print(f"  status={st}  {'OK' if ok else 'FAIL'}{note}")
        print(f"  {text[:300]}")
    print(f"\n{'=' * 60}\n{len(TOOLS) - bad}/{len(TOOLS)} 通过"
          + ("" if not bad else f" · {bad} 个失败")
          + ("" if not gated else f" · {len(gated)} 个被档位拦住"))
    if gated:
        print("  被拦：%s" % " / ".join(gated))
        print("  ⚠️ 如果你的 Key 已开通机构版，上面这些应该返回 200 —— "
              "看到 GATED 说明你的 Key 档位与该端点不匹配")
    if not KEY:
        print(f"  未配 FUND_KEY：{free_n} 个免费工具可直接用，其余需 Key")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        asyncio.run(build_server()())
