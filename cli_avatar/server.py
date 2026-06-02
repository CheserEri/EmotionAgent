import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from cli_avatar.engine import AgentEngine


class AgentHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器，将请求转发给 AgentEngine。"""

    engine: AgentEngine

    def do_POST(self) -> None:
        if self.path == "/chat":
            self._handle_chat()
        elif self.path == "/reset":
            self._handle_reset()
        else:
            self._send_error(404, "Not Found")

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok", "model": self.engine.config.get("model", "")})
        elif self.path == "/memory":
            self._send_json(self.engine.get_memory_info())
        elif self.path == "/history":
            self._send_json(self.engine.get_history())
        else:
            self._send_error(404, "Not Found")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _handle_chat(self) -> None:
        body = self._read_body()
        if body is None:
            return

        message = body.get("message")
        if not isinstance(message, str) or not message.strip():
            self._send_error(400, "缺少 message 字段")
            return

        try:
            result = self.engine.chat(message.strip())
        except RuntimeError as exc:
            self._send_error(502, f"LLM 调用失败: {exc}")
            return

        self._send_json(result)

    def _handle_reset(self) -> None:
        body = self._read_body()
        if body is None:
            body = {}

        if body.get("all"):
            self.engine.reset_all()
        else:
            self.engine.reset()

        self._send_json({"status": "reset"})

    def _read_body(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}

        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(400, "无效的 JSON")
            return None

    def _send_json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: Any) -> None:
        # 简化日志输出
        print(f"[{self.log_date_time_string()}] {format % args}")


def create_server(engine: AgentEngine, host: str = "127.0.0.1", port: int = 8765) -> HTTPServer:
    AgentHandler.engine = engine
    server = HTTPServer((host, port), AgentHandler)
    return server


def run_server(engine: AgentEngine, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(engine, host, port)
    print(f"Agent Server 启动在 http://{host}:{port}")
    print("  POST /chat    - 发送消息")
    print("  POST /reset   - 重置上下文")
    print("  GET  /health  - 健康检查")
    print("  GET  /memory  - 查看记忆")
    print("  GET  /history - 查看历史")
    print("Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer 已停止。")
        server.server_close()
