import json

from cli_avatar.config import DEFAULT_SYSTEM_PROMPT, ConfigError, load_config
from cli_avatar.expression import (
    DEFAULT_EXPRESSION,
    build_expression_messages,
    format_expression,
    parse_expression_json,
)
from cli_avatar.memory import (
    MemoryStore,
    build_memory_update_messages,
    build_reply_messages,
)
from cli_avatar.openai_compatible_client import OpenAICompatibleClient


MAX_TURNS = 6


def print_help() -> None:
    print("Commands:")
    print("  /exit   退出")
    print("  /clear  清空上下文")
    print("  /memory 查看摘要和长期记忆")
    print("  /forget 清空摘要和长期记忆")
    print("  /history 查看最近对话和表情 JSON")
    print("  /debug  切换调试模式，显示 LLM B 原始输出")
    print("  /help   查看命令")


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(__import__("sys"), stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    configure_console_encoding()

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"配置错误: {exc}")
        print("PowerShell 示例:")
        print('  $env:OPENAI_API_KEY="你的 API Key"')
        print('  $env:OPENAI_BASE_URL="https://api.openai.com/v1"')
        print('  $env:OPENAI_MODEL="gpt-4o-mini"')
        print("MiMo 示例:")
        print('  $env:MIMO_API_KEY="你的 MiMo API Key"')
        print('  $env:OPENAI_BASE_URL="https://api.xiaomimimo.com/v1"')
        print('  $env:OPENAI_MODEL="mimo-v2.5-pro"')
        print('  $env:OPENAI_API_KEY_HEADER="api-key"')
        print('  $env:OPENAI_TOKEN_PARAM="max_completion_tokens"')
        return

    client = OpenAICompatibleClient(
        api_key=str(config["api_key"]),
        base_url=str(config["base_url"]),
        model=str(config["model"]),
        api_key_header=str(config["api_key_header"]),
        token_param=str(config["token_param"]),
    )
    memory_store = MemoryStore()
    turns: list[dict[str, object]] = []
    debug = False

    print("Emotion Agent CLI - LLM A + Expression JSON B")
    print(f"Model: {config['model']}")
    print("Type /help for commands.")

    while True:
        try:
            user_input = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break

        if not user_input:
            continue

        if user_input == "/exit":
            print("退出。")
            break
        if user_input == "/help":
            print_help()
            continue
        if user_input == "/clear":
            turns = []
            print("本轮上下文已清空，长期记忆保留。")
            continue
        if user_input == "/forget":
            memory_store.clear()
            turns = []
            print("摘要和长期记忆已清空。")
            continue
        if user_input == "/debug":
            debug = not debug
            print(f"调试模式: {'开启' if debug else '关闭'}")
            continue
        if user_input == "/history":
            print(json.dumps(turns, ensure_ascii=False, indent=2))
            continue
        if user_input == "/memory":
            print(
                json.dumps(
                    {
                        "summary": memory_store.summary,
                        "memories": memory_store.memories,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            continue

        reply_messages, relevant_memories = build_reply_messages(
            DEFAULT_SYSTEM_PROMPT,
            user_input,
            turns,
            memory_store,
        )

        try:
            reply = client.chat(
                reply_messages,
                temperature=float(config["temperature"]),
                max_tokens=int(config["max_tokens"]),
            )
        except RuntimeError as exc:
            print(f"\nAPI 错误: {exc}")
            continue

        expression_messages = build_expression_messages(user_input, reply, turns)
        expression_error = ""
        raw_expression = ""
        try:
            raw_expression = client.chat(
                expression_messages,
                temperature=0.2,
                max_tokens=int(config["max_tokens"]),
            )
            expression = parse_expression_json(raw_expression)
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            expression_error = str(exc)
            expression = DEFAULT_EXPRESSION.copy()

        turns.append(
            {
                "user": user_input,
                "assistant": reply,
                "expression": expression,
            }
        )
        turns = turns[-MAX_TURNS:]

        memory_error = ""
        memories_added = 0
        raw_memory = ""
        try:
            raw_memory = client.chat(
                build_memory_update_messages(
                    memory_store.summary,
                    turns,
                    user_input,
                    reply,
                ),
                temperature=0.2,
                max_tokens=max(int(config["max_tokens"]), 2048),
            )
            memories_added = memory_store.update_from_model_json(raw_memory)
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            memory_error = str(exc)

        print(f"\nAI> {reply}")
        print("\nExpression JSON>")
        print(format_expression(expression))
        if debug:
            print("\nRelevant Memories>")
            print(json.dumps(relevant_memories, ensure_ascii=False, indent=2))
        if debug and raw_expression:
            print("\nRaw Expression Output>")
            print(raw_expression)
        if debug and raw_memory:
            print("\nRaw Memory Output>")
            print(raw_memory)
        if expression_error:
            print(f"\nExpression fallback: {expression_error}")
        if memory_error:
            print(f"\nMemory update failed: {memory_error}")
        elif debug:
            print(f"\nMemory updated: added {memories_added} item(s)")


if __name__ == "__main__":
    main()
