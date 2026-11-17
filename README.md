<div align="center">

<a href="https://fundapi.cn"><img src="https://fundapi.cn/icon-512.png" width="88" height="88" alt="fundapi"></a>

# fundapi — 基金数据 API 官方 MCP 服务器

让 Claude Code / Codex / Cursor / 任意 **AI Agent（MCP）** 直接调用基金数据：净值 / 季报持仓 / 基金经理 / 评级 / 分红 / 盘中估值 / 持仓重叠 / 组合穿透 / 组合诊断 / 基金对比 / 全市场筛选 —— **19 个工具，免费工具无需 Key**。

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![MCP SDK](https://img.shields.io/badge/mcp%20SDK-1.x%20%7C%202.x-6E56CF)
[![CI](https://github.com/fundapi-cn/fundapi-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/fundapi-cn/fundapi-mcp/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-green)

**中文** · [English](README.en.md)

**支持主流 AI Agent 客户端** —— 开箱即用：

![Claude Code](https://img.shields.io/badge/Claude%20Code-supported-D97757?logo=claude&logoColor=white)
![Cursor](https://img.shields.io/badge/Cursor-supported-000000?logo=cursor&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-supported-007ACC)
![Codex](https://img.shields.io/badge/Codex-supported-000000)
![OpenCode](https://img.shields.io/badge/OpenCode-supported-000000?logo=opencode&logoColor=white)
![Gemini CLI](https://img.shields.io/badge/Gemini%20CLI-supported-8E75B2?logo=googlegemini&logoColor=white)
![Cline](https://img.shields.io/badge/Cline-supported-18181B?logo=cline&logoColor=white)
![Windsurf](https://img.shields.io/badge/Windsurf-supported-0B100F?logo=windsurf&logoColor=white)

[官网](https://fundapi.cn) · [文档](https://fundapi.cn/docs) · [MCP 接入](https://fundapi.cn/mcp) · [定价](https://fundapi.cn/pricing)

[GitHub 源码](https://github.com/fundapi-cn/fundapi-mcp) · [问题反馈 Issues](https://github.com/fundapi-cn/fundapi-mcp/issues)

</div>

---

## 这是什么

一个 **基金数据 MCP**：提供 19 个基金数据工具，AI Agent 配一次就能直接调用。之后你问「易方达消费行业这只基金费率多少、近一年在同类里排第几」，Agent 自己会拿**真实数据** —— 不用你写代码，也不用每次把用法贴给它。

---

## 为什么用它

- **19 个工具，一次配好**：净值 / 季报持仓 / 基金经理 / 评级 / 分红 / 交易规则 / 盘中估值 / 持仓重叠 / 组合穿透 / 组合诊断 / 持仓变动 / 经理变更史 / 基金对比 / 全市场筛选
- **免费工具真的免 Key**：`fund_search` / `fund_profile` / `fund_screener_options` 装上就能调，不用先买 Key
- **托管端点零安装**：填一个 URL 就能用；也可以本地 stdio 自托管（内网 / 想读源码）
- **一个 Key 两种用法**：MCP 与 HTTP 是**同一套端点、同一份额度**，不用为 MCP 另外买权限
- **工具描述写给 AI Agent 看**：每个工具都写清「什么时候用 / 参数怎么填 / 返回什么」，Agent 不会调错
- **口径固定，不用二次处理**：单位净值与累计净值分列；季报持仓按报告期披露并带 `report_period`；盘中估值明确标注是估算值
- **组合类指标可追溯**：穿透 / 重叠 / 诊断的响应带 `method` 与 `report_period`，能回到披露口径
- **不用你维护**：缓存、限流、数据刷新都在服务端，客户端只负责调用

---

## 两种用法

| 方式 | 适合 | 说明 |
|---|---|---|
| **① 托管端点**（推荐） | 大多数用户 | 服务器地址 **`https://api.fundapi.cn/mcp`**，**不用装任何东西** |
| **② 本地运行**（本仓） | 想自己托管 / 内网部署 / 想读源码 | 跑本仓的 `mcp_fund.py`，走 stdio |

---

## 托管端点（推荐）

> ⚠️ 填 **`https://api.fundapi.cn/mcp`** —— 站点上的 `fundapi.cn/mcp` 是**配置说明页**，不是接口地址。

**最快的接法** —— Claude Code 一行命令（其他客户端见下节）：

```bash
# 免费工具（无需 Key）
claude mcp add --transport http fundapi https://api.fundapi.cn/mcp

# 要用付费工具（持仓 / 经理 / 组合…）再加请求头
claude mcp add --transport http fundapi https://api.fundapi.cn/mcp \
  --header "Authorization: Bearer cf-你的KEY"

claude mcp list   # 验证：应显示 √ Connected
```

**或者交给你的 AI Agent** —— 复制这句话发给它：

> 帮我把这个 fundapi MCP 服务器加上：名字 `fundapi`，类型 HTTP，URL `https://api.fundapi.cn/mcp`。免费工具不用 Key；要用付费工具再加请求头 `Authorization: Bearer cf-你的KEY`。加完确认能连上、能看到 19 个工具。

**加完重启客户端**（或重开会话）配置才生效 —— 重启后直接在对话里问，例如「易方达消费行业这只基金费率多少，最近一年同类排第几」。

---

## 支持的客户端

配置文件位置（键名与文件名逐家核对过官方文档）：

| 客户端 | 配置文件 |
|---|---|
| Claude Desktop | `claude_desktop_config.json` |
| Claude Code | `.mcp.json` |
| Cursor | `.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |
| Codex | `~/.codex/config.toml`（TOML） |
| OpenCode | `opencode.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| Cline | `~/.cline/mcp.json` |
| Windsurf | `mcp_config.json` |
| CodeBuddy | `~/.codebuddy/.mcp.json` |
| WorkBuddy | `~/.workbuddy/mcp.json` |
| Trae | 设置 → MCP → 手动配置 |
| Kimi Code | `~/.kimi/mcp.json` |
| ZCode | `~/.zcode/cli/config.json` |
| MiMo Code | `mimocode.json` |
| Kilo Code | `kilo.jsonc` |
| Manus | 设置 → 集成 → 自定义 MCP |
| Devin | `~/.config/devin/mcp_config.json` |
| OpenClaw | `~/.openclaw/openclaw.json` |
| Hermes | `~/.hermes/config.yaml` |

**国内平台**（同样填 URL + 请求头，无需安装任何东西）：阿里云百炼 · 扣子 Coze · 腾讯元器 · 腾讯云智能体开发平台 · 火山方舟

> 各家完整配置写法（键名不一样，别照抄）：<https://fundapi.cn/mcp>

---

## 本地运行

### 环境要求

- **Python ≥ 3.10**
- 依赖：[`mcp`](https://pypi.org/project/mcp/)（**1.x 与 2.x 都支持**）+ [`requests`](https://pypi.org/project/requests/)（≥ 2.28）

```bash
pip install -r requirements.txt
```

### 配置（以 Claude Desktop 为例）

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

配置好之后可以直接说：

```
易方达消费行业这只基金费率多少、规模多大
110022 和 009265 的重仓股重叠多少
把这三只基金按 4:3:3 穿透，实际买了哪些股票
筛一下近一年收益前 20 的股票型基金
```

→ AI 会自动调用下面的工具拿**真实数据**（不是编造）。

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `FUND_API` | `https://api.fundapi.cn` | 服务端地址（一般不用改） |
| `FUND_KEY` | 空 | API Key。**留空也能用** 3 个免费工具；付费工具必填（[获取](https://fundapi.cn/pricing)，¥9.9 起） |

### 自测

```bash
python mcp_fund.py --selftest     # 直连 REST 验证工具可用性（不启 MCP）
python tests/check_stdio.py       # 本地 stdio 握手 + 工具数（应为 19）
```

---

## 19 个工具

| 工具 | 说明 | 免 Key |
|---|---|---|
| `fund_search` | 按代码 / 名称 / 拼音搜索基金（只给名字时先用它） | ✅ |
| `fund_profile` | 基金档案：费率、10 档涨幅与同类排名、规模、持仓结构、持有人结构 | ✅ |
| `fund_screener_options` | 筛选器可选值：类型树、基金公司、主题、收益区间、评级机构 | ✅ |
| `fund_nav` | 历史净值：单位净值 / 累计净值 / 日增长率 / 申赎状态 | 体验版 |
| `fund_rank` | 全市场阶段涨幅排行 | 体验版 |
| `fund_notices` | 公告索引：分红、定期报告、人事变更 | 体验版 |
| `fund_holdings` | 季报前十大重仓股、占净值比、持股数 | 专业版 |
| `fund_managers` | 基金经理：任职年限、在管规模、能力雷达、任期收益对比 | 专业版 |
| `fund_estimate` | ⭐ **盘中估值**：实时估算 + 持仓模型双口径，带逐股贡献 | 专业版 |
| `fund_dividends` | 分红送配：次数、金额、份额折算明细 | 专业版 |
| `fund_trade_rule` | 申赎状态、T+N 确认到账、分档费率、渠道折扣 | 专业版 |
| `fund_rating` | 逐报告期机构评级，看是在升还是在降 | 专业版 |
| `fund_overlap` | 多只基金前十大重仓股的重叠度与加权合计占比 | 机构版 |
| `fund_portfolio_xray` | ⭐ **组合穿透**：把一篮子基金穿透到个股及综合权重 | 机构版 |
| `fund_portfolio_diagnose` | ⭐ **组合诊断**：行业暴露、重仓穿透、仓位趋势、费率合计 | 机构版 |
| `fund_holding_changes` | 持仓变动：新进 / 跌出前十 / 加仓减仓 | 机构版 |
| `fund_manager_history` | 基金经理变更史与历任任期回报 | 机构版 |
| `fund_compare` | ⭐ **基金对比**：2–5 只并列收益 / 费率 / 经理 / 持仓 | 机构版 |
| `fund_screener` | ⭐ **全市场筛选**：按类型 / 公司 / 主题 / 收益区间横着筛 | 机构版 |

---

## 常见问题

**免费工具真的不用 Key？**
是。`fund_search` / `fund_profile` / `fund_screener_options` 不填 `FUND_KEY` 也能调，匿名按 IP 限流（每分钟 10 次 / 每天 500 次）。

**覆盖哪些基金？以后会加 ETF / QDII 吗？**
当前覆盖场外公募基金（含货币基金）。ETF / LOF 等场内品种、QDII 等在规划中；新增品种会以新端点提供，现有工具名与调用方式不变。

**MCP 和 HTTP 是两个产品吗？**
不是。同一套端点、同一个 Key、同一份额度；MCP 只是给 AI Agent 的调用方式。

**到期会自动续费吗？**
不会。到期即失效，需要手动再次购买；接口返回 `403` 并说明已过期。

**数据多久更新？**
净值在每个交易日当晚更新；季报持仓按报告期披露（最多滞后一个季度）；盘中估值是估算值，不是实际净值。

**调用频率限制？**
体验版 30 次/分、专业版 60 次/分、机构版 300 次/分；单 IP 并发上限 8 条。超限返回 `429` 与 `Retry-After`。

**接口一般多快？**
大多数端点 0.3–1.1 秒；组合诊断、多基金对比、盘中估值首次约 2–3 秒，之后走缓存基本在 1 秒内。

---

## 变更

见 [CHANGELOG.md](CHANGELOG.md)。

---

## License

MIT
