"""
Web 前端启动入口。
同时提供静态文件服务（含 PMX 模型）和 API 代理（转发到 Agent Server）。
用法: python run_web.py
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# 配置
WEB_DIR = Path(__file__).parent / "web"
AGENT_HOST = "127.0.0.1"
AGENT_PORT = 8765
WEB_HOST = "127.0.0.1"
WEB_PORT = 8080

# MIME 类型
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tga": "application/octet-stream",
    ".pmx": "application/octet-stream",
    ".vmd": "application/octet-stream",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
}


class WebHandler(SimpleHTTPRequestHandler):
    """处理静态文件和 API 代理。"""

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
        else:
            self._serve_static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _serve_static(self):
        path = urllib.parse.unquote(self.path.split("?")[0])
        if path == "/":
            path = "/index.html"

        file_path = WEB_DIR / path.lstrip("/")

        # 安全检查：防止目录遍历
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(WEB_DIR.resolve())):
                self.send_error(403)
                return
        except (ValueError, OSError):
            self.send_error(400)
            return

        if not file_path.is_file():
            self.send_error(404, f"File not found: {path}")
            return

        ext = file_path.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        try:
            data = file_path.read_bytes()
        except OSError:
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self, method):
        """代理请求到 Agent Server。"""
        api_path = self.path[4:]  # 去掉 /api 前缀
        url = f"http://{AGENT_HOST}:{AGENT_PORT}{api_path}"

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(resp_body)))
                self._cors()
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(error_body)))
            self._cors()
            self.end_headers()
            self.wfile.write(error_body)
        except urllib.error.URLError as e:
            error = json.dumps({"error": f"Agent Server 未响应: {e.reason}"}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(error)))
            self._cors()
            self.end_headers()
            self.wfile.write(error)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        # 简化日志
        print(f"  {format % args}")


def main():
    global WEB_HOST, WEB_PORT, AGENT_HOST, AGENT_PORT

    # 命令行参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            WEB_HOST = args[i + 1]; i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            WEB_PORT = int(args[i + 1]); i += 2
        elif args[i] == "--agent-port" and i + 1 < len(args):
            AGENT_PORT = int(args[i + 1]); i += 2
        else:
            i += 1

    # 检查 web 目录
    if not WEB_DIR.is_dir():
        print(f"错误: web 目录不存在 ({WEB_DIR})")
        return

    # 检查模型文件
    models_dir = WEB_DIR / "models"
    if not models_dir.is_dir():
        print(f"警告: 模型目录不存在 ({models_dir})")
        print("  请将 PMX 模型和纹理文件放入 web/models/ 目录")

    server = HTTPServer((WEB_HOST, WEB_PORT), WebHandler)

    print("=" * 50)
    print("Emotion Agent Web")
    print("=" * 50)
    print(f"  前端地址:     http://{WEB_HOST}:{WEB_PORT}")
    print(f"  Agent Server: http://{AGENT_HOST}:{AGENT_PORT}")
    print(f"  模型目录:     {models_dir}")
    print()
    print("确保 Agent Server 已启动: python run_agent_server.py")
    print("Ctrl+C 退出")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb Server 已停止。")
        server.server_close()


if __name__ == "__main__":
    main()
