# fundapi.cn — Official MCP Server for China Mutual Fund Data

An MCP server that exposes the 19 fund-data endpoints of [fundapi.cn](https://fundapi.cn) as tools, so agents in Claude Desktop / Claude Code / Cursor / VS Code / Codex can query fund data directly.

## What it is

- **19 tools**, one per HTTP endpoint (NAV, quarterly holdings, managers, ratings, dividends, intraday estimate, portfolio look-through / diagnostics / comparison / screening)
- **Free tools** (search / profile / screener options) need no API key
- Data comes from public disclosures; NAV updates each trading day, holdings by reporting period

## Why use it

- No scraping, no reconciling data conventions yourself
- Structured JSON with fixed fields and documented units
- One API key works for both HTTP and MCP, sharing the same quota

## Quick start

### Option A: remote (recommended, nothing to install)

```json
{
  "mcpServers": {
    "fundapi": {
      "type": "http",
      "url": "https://api.fundapi.cn/mcp",
      "headers": { "Authorization": "Bearer cf-YOUR_KEY" }
    }
  }
}
```

Free tools work without a key.

### Option B: local stdio

```bash
pip install -r requirements.txt
export FUND_API="https://api.fundapi.cn"
export FUND_KEY="cf-YOUR_KEY"
python mcp_fund.py
```

## Supported clients

| Client | Config file |
|---|---|
| Claude Desktop | `claude_desktop_config.json` |
| Claude Code | `.mcp.json` |
| Cursor | `.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |
| Codex | `~/.codex/config.toml` (TOML) |
| Gemini CLI | `~/.gemini/settings.json` |
| Cline | `~/.cline/mcp.json` |
| Windsurf | `mcp_config.json` |
| CodeBuddy | `~/.codebuddy/.mcp.json` |
| WorkBuddy | `~/.workbuddy/mcp.json` |
| OpenCode | `opencode.json` |
| Kimi Code | `~/.kimi/mcp.json` |

## The 19 tools

| Tool | Endpoint | Purpose | Tier |
|---|---|---|---|
| `fund_search` | `/v1/fund-search` | Search funds by code, name or pinyin initials | Free |
| `fund_profile` | `/v1/fund-profile` | Fees, 10-period returns, size, holder structure | Free |
| `fund_screener_options` | `/v1/fund-screener-options` | Allowed values for the screener | Free |
| `fund_nav` | `/v1/fund-nav` | NAV history with daily growth and subscription status | Trial |
| `fund_rank` | `/v1/fund-rank` | Market-wide period return ranking | Trial |
| `fund_notices` | `/v1/fund-notices` | Notice index: dividends, reports, manager changes | Trial |
| `fund_holdings` | `/v1/fund-holdings` | Top-10 holdings and weights from quarterly reports | Pro |
| `fund_managers` | `/v1/fund-managers` | Manager tenure, AUM, capability profile, returns | Pro |
| `fund_estimate` | `/v1/fund-estimate` | Intraday estimate: realtime and holdings-model views | Pro |
| `fund_dividends` | `/v1/fund-dividends` | Dividend events and share conversion | Pro |
| `fund_trade_rule` | `/v1/fund-trade-rule` | Trading status, T+N settlement, fee tiers | Pro |
| `fund_rating` | `/v1/fund-rating` | Ratings by reporting period | Pro |
| `fund_overlap` | `/v1/fund-overlap` | Overlap of holdings across funds | Institutional |
| `fund_portfolio_xray` | `/v1/fund-portfolio-xray` | Look through a portfolio to individual stocks | Institutional |
| `fund_portfolio_diagnose` | `/v1/fund-portfolio-diagnose` | Industry exposure, position trend, total fees | Institutional |
| `fund_holding_changes` | `/v1/fund-holding-changes` | New, dropped, increased and reduced positions | Institutional |
| `fund_manager_history` | `/v1/fund-manager-history` | Manager change history and returns per tenure | Institutional |
| `fund_compare` | `/v1/fund-compare` | Side-by-side comparison of 2–5 funds | Institutional |
| `fund_screener` | `/v1/fund-screener` | Screen by type, company, theme and return range | Institutional |

## Example questions

- "What are the fees on this fund, and how does its 1-year return rank among peers?"
- "How much do 110022 and 009265 overlap in their top holdings?"
- "Look through these three funds weighted 4:3:3 — which stocks do I actually own?"
- "Screen stock funds with the best 1-year returns"

## Get an API key

See https://fundapi.cn/pricing . Trial ¥9.9 / 7 days, Pro ¥59 / month, Institutional ¥299 / month. No auto-renewal.

## Docs

- API reference: https://fundapi.cn/docs
- MCP setup: https://fundapi.cn/mcp
- Agent install workflow: https://fundapi.cn/install-mcp-workflow.md

## License

MIT
