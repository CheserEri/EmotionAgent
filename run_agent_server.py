import os
import sys

from cli_avatar.engine import AgentEngine
from cli_avatar.server import run_server

try:
    from config.local_mimo_config import (
        MIMO_API_KEY,
        OPENAI_API_KEY_HEADER,
        OPENAI_BASE_URL,
        OPENAI_MAX_TOKENS,
        OPENAI_MODEL,
        OPENAI_TEMPERATURE,
        OPENAI_TOKEN_PARAM,
    )
except ModuleNotFoundError:
    MIMO_API_KEY = ""
    OPENAI_BASE_URL = "https://api.xiaomimimo.com/v1"
    OPENAI_MODEL = "mimo-v2.5-pro"
    OPENAI_API_KEY_HEADER = "api-key"
    OPENAI_TOKEN_PARAM = "max_completion_tokens"
    OPENAI_TEMPERATURE = "1.0"
    OPENAI_MAX_TOKENS = "1024"


def apply_local_config() -> None:
    if MIMO_API_KEY:
        os.environ.setdefault("MIMO_API_KEY", MIMO_API_KEY)
    os.environ.setdefault("OPENAI_BASE_URL", OPENAI_BASE_URL)
    os.environ.setdefault("OPENAI_MODEL", OPENAI_MODEL)
    os.environ.setdefault("OPENAI_API_KEY_HEADER", OPENAI_API_KEY_HEADER)
    os.environ.setdefault("OPENAI_TOKEN_PARAM", OPENAI_TOKEN_PARAM)
    os.environ.setdefault("OPENAI_TEMPERATURE", OPENAI_TEMPERATURE)
    os.environ.setdefault("OPENAI_MAX_TOKENS", OPENAI_MAX_TOKENS)


if __name__ == "__main__":
    apply_local_config()

    host = "127.0.0.1"
    port = 8765

    # 支持命令行参数: python run_agent_server.py --port 8765
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    engine = AgentEngine()
    run_server(engine, host, port)
