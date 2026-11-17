"""本地 stdio 握手验证：启动 mcp_fund.py，初始化并列出工具。"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PY = sys.executable
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp_fund.py")


async def main() -> None:
    params = StdioServerParameters(
        command=PY,
        args=[os.path.abspath(SERVER)],
        env={**os.environ, "FUND_API": "https://api.fundapi.cn"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            info = getattr(init, "server_info", None) or init.serverInfo
            print("serverInfo:", info.name, info.version)
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("tools:", len(names))
            print("first 5:", ", ".join(names[:5]))
            assert len(names) == 19, names


if __name__ == "__main__":
    asyncio.run(main())
