from flask import request, jsonify

from core.tool_provider import ToolProvider, registry
import local_tools2
import local_tools
import flask

app = flask.Flask(__name__)

# 2. 创建 ToolProvider，可附加 MCP 客户端
provider = ToolProvider(local_registry=registry)
# 如果有远程 MCP 服务
# mcp = HttpMcpClient("http://localhost:5000")
# provider.add_mcp_client(mcp)

# 3. 测试
print("Tools list:", provider.list_tools())
print("Execute add:", provider.execute("add", {"a": 3, "b": 4}))
print("Execute plus:", provider.execute("plus", {"a": 3, "b": 5}))


@app.route("/tools/list")
def list_tools():
    return flask.jsonify({"tools": provider.list_tools()})


@app.route('/tools/call', methods=['POST'])
def call_tool():
    data = request.get_json(force=True)
    name = data.get("name")
    arguments = data.get("arguments", {})

    if not name:
        return jsonify({"error": "Missing 'name' field"}), 400

    try:
        result = provider.execute(name, arguments)
        return jsonify({"result": result})
    except KeyError:
        return jsonify({"error": f"Tool '{name}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Execution error: {str(e)}"}), 500


# @app.route("/")
# def index():
#     return "OK"
#

if __name__ == '__main__':
    app.run()
