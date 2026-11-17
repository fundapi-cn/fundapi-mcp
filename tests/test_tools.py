"""最小自检：模块可导入、工具数正确、必需参数存在。不需要网络。"""
import mcp_fund


def test_tool_count():
    assert len(mcp_fund.TOOLS) == 19, f"expected 19 tools, got {len(mcp_fund.TOOLS)}"


def test_tool_shape():
    for name, spec in mcp_fund.TOOLS.items():
        assert isinstance(spec, tuple) and len(spec) == 3, name
        path, desc, params = spec
        assert path.startswith("/v1/"), name
        assert isinstance(desc, str) and desc.strip(), name
        assert isinstance(params, list), name


def test_free_tools_need_no_key():
    # 三个免费工具的端点必须存在
    for name in ("fund_search", "fund_profile", "fund_screener_options"):
        assert name in mcp_fund.TOOLS
