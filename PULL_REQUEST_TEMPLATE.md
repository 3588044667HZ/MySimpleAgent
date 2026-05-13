Title: Fix MCP list_tools method, plus implementation, and ask_user parameter name

This PR contains three small but important fixes:

1. Change HttpMcpClient.list_tools to use GET /tools/list to match the MCP server implementation in MCpServer.py.
2. Fix local_tools2.plus implementation: it previously multiplied inputs; now it correctly adds them.
3. Align ask_user function parameter name to `question` in local_tools.py so the generated tool schema matches the documentation (system.md).

Validation steps:
- Start the MCP server: `python MCpServer.py`.
- Confirm GET http://127.0.0.1:5000/tools/list returns a JSON object with a `tools` array.
- Run `python main.py` and verify tool listing and invocation work as expected.
- Test plus: call with a=3, b=5 -> expect result "8".
- Test ask_user: call ask_user with `question` argument -> it should prompt and return user input.
