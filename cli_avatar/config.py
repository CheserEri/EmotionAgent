import os


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_KEY_HEADER = "Authorization"
DEFAULT_TOKEN_PARAM = "max_tokens"
DEFAULT_SYSTEM_PROMPT = (
    "你是一个运行在本机命令行里的 AI 角色。"
    "请用自然、简短、有温度的中文回复用户。"
)


class ConfigError(RuntimeError):
    pass


def load_config() -> dict[str, str | float | int]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("MIMO_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("缺少环境变量 OPENAI_API_KEY 或 MIMO_API_KEY。")

    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
    api_key_header = os.getenv("OPENAI_API_KEY_HEADER", DEFAULT_API_KEY_HEADER).strip()
    token_param = os.getenv("OPENAI_TOKEN_PARAM", DEFAULT_TOKEN_PARAM).strip()
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "500"))

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "api_key_header": api_key_header,
        "token_param": token_param,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
