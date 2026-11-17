# fundapi.cn 场外公募基金数据 API · 官方 MCP 服务器

把 [fundapi.cn](https://fundapi.cn) 的 19 个基金数据端点封装成 MCP 工具，让 Claude Desktop / Claude Code / Cursor / VS Code / Codex 等 AI 客户端里的 Agent 直接查基金数据。

## 这是什么

- **19 个工具**，与 HTTP 端点一一对应（净值、季报持仓、基金经理、评级、分红、盘中估值、组合穿透 / 诊断 / 对比 / 筛选）
- **免费工具**（搜索 / 档案 / 筛选项字典）不需要 API Key
- 数据来自公开披露；净值按交易日更新，季报按报告期披露

## 为什么用它

- 不用自己爬季报、自己对齐口径
- 返回结构化 JSON，字段固定、有单位说明
- 一个 API Key 同时用于 HTTP 与 MCP，额度共用

## 最快的用法

### 方式 A：远程接入（推荐，不用安装）

```json
{
  "mcpServers": {
    "fundapi": {
      "type": "http",
      "url": "https://api.fundapi.cn/mcp",
      "headers": { "Authorization": "Bearer cf-你的Key" }
    }
  }
}
```

免费工具不填 Key 也能用。

### 方式 B：本地 stdio

```bash
pip install -r requirements.txt
export FUND_API="https://api.fundapi.cn"
export FUND_KEY="cf-你的Key"
python mcp_fund.py
```

客户端配置：

```json
{
  "mcpServers": {
    "fundapi": {
      "command": "python",
      "args": ["/path/to/mcp_fund.py"],
      "env": { "FUND_API": "https://api.fundapi.cn", "FUND_KEY": "cf-你的Key" }
    }
  }
}
```

## 支持的客户端

| 客户端 | 配置文件 |
|---|---|
| Claude Desktop | `claude_desktop_config.json` |
| Claude Code | `.mcp.json` |
| Cursor | `.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |
| Codex | `~/.codex/config.toml`（TOML） |
| Gemini CLI | `~/.gemini/settings.json` |
| Cline | `~/.cline/mcp.json` |
| Windsurf | `mcp_config.json` |
| CodeBuddy | `~/.codebuddy/.mcp.json` |
| WorkBuddy | `~/.workbuddy/mcp.json` |
| OpenCode | `opencode.json` |
| Kimi Code | `~/.kimi/mcp.json` |

## 19 个工具

| 工具 | 端点 | 说明 | 版本 |
|---|---|---|---|
| `fund_search` | `/v1/fund-search` | 按代码 / 名称 / 拼音搜索基金 | 免费 |
| `fund_profile` | `/v1/fund-profile` | 基金档案：费率、10 档涨幅、规模、持仓结构 | 免费 |
| `fund_screener_options` | `/v1/fund-screener-options` | 筛选器可选值：类型树、公司、主题、区间 | 免费 |
| `fund_nav` | `/v1/fund-nav` | 历史净值：单位 / 累计 / 日增长率 / 申赎状态 | 体验版 |
| `fund_rank` | `/v1/fund-rank` | 全市场阶段涨幅排行 | 体验版 |
| `fund_notices` | `/v1/fund-notices` | 公告索引：分红、定期报告、人事变更 | 体验版 |
| `fund_holdings` | `/v1/fund-holdings` | 季报前十大重仓股与占比 | 专业版 |
| `fund_managers` | `/v1/fund-managers` | 基金经理：任职、规模、能力雷达、任期收益 | 专业版 |
| `fund_estimate` | `/v1/fund-estimate` | 盘中估值：实时估算 + 持仓模型双口径 | 专业版 |
| `fund_dividends` | `/v1/fund-dividends` | 分红送配明细与份额折算 | 专业版 |
| `fund_trade_rule` | `/v1/fund-trade-rule` | 申赎状态、T+N、分档费率、渠道折扣 | 专业版 |
| `fund_rating` | `/v1/fund-rating` | 逐报告期机构评级 | 专业版 |
| `fund_overlap` | `/v1/fund-overlap` | 多只基金重仓股重叠度 | 机构版 |
| `fund_portfolio_xray` | `/v1/fund-portfolio-xray` | 组合穿透到个股及综合权重 | 机构版 |
| `fund_portfolio_diagnose` | `/v1/fund-portfolio-diagnose` | 组合诊断：行业暴露、仓位趋势、费率合计 | 机构版 |
| `fund_holding_changes` | `/v1/fund-holding-changes` | 持仓变动：新进 / 跌出 / 加减仓 | 机构版 |
| `fund_manager_history` | `/v1/fund-manager-history` | 基金经理变更史与历任回报 | 机构版 |
| `fund_compare` | `/v1/fund-compare` | 2–5 只基金并列对比 | 机构版 |
| `fund_screener` | `/v1/fund-screener` | 按类型 / 公司 / 主题 / 收益区间筛选 | 机构版 |

## 示例提问

- 「易方达消费行业这只基金费率多少、最近一年在同类里排第几？」
- 「110022 和 009265 重仓股重叠多少？」
- 「把这三只基金按 4:3:3 穿透，实际买了哪些股票？」
- 「筛选近一年收益前 20 的股票型基金」

## 获取 API Key

访问 https://fundapi.cn/pricing 。体验版 ¥9.9 / 7 天，专业版 ¥59 / 月，机构版 ¥299 / 月。到期不自动扣费。

## 文档

- 接口文档：https://fundapi.cn/docs
- MCP 接入说明：https://fundapi.cn/mcp
- 客户端安装工作流（给 Agent 读）：https://fundapi.cn/install-mcp-workflow.md

## License

MIT
