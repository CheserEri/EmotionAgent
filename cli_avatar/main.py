import json

from cli_avatar.config import ConfigError, load_config
from cli_avatar.engine import AgentEngine


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

    engine = AgentEngine(config)

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
            engine.reset()
            print("本轮上下文已清空，长期记忆保留。")
            continue
        if user_input == "/forget":
            engine.reset_all()
            print("摘要和长期记忆已清空。")
            continue
        if user_input == "/debug":
            engine.debug = not engine.debug
            print(f"调试模式: {'开启' if engine.debug else '关闭'}")
            continue
        if user_input == "/history":
            print(json.dumps(engine.get_history(), ensure_ascii=False, indent=2))
            continue
        if user_input == "/memory":
            print(
                json.dumps(
                    engine.get_memory_info(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            continue

        try:
            result = engine.chat(user_input)
        except RuntimeError as exc:
            print(f"\nAPI 错误: {exc}")
            continue

        print(f"\nAI> {result['text']}")
        print("\nExpression JSON>")
        print(
            json.dumps(
                {k: v for k, v in result.items() if k != "_debug"},
                ensure_ascii=False,
                indent=2,
            )
        )

        debug_info = result.get("_debug")
        if debug_info:
            if debug_info.get("relevant_memories"):
                print("\nRelevant Memories>")
                print(json.dumps(debug_info["relevant_memories"], ensure_ascii=False, indent=2))
            if debug_info.get("raw_expression"):
                print("\nRaw Expression Output>")
                print(debug_info["raw_expression"])
            if debug_info.get("raw_memory"):
                print("\nRaw Memory Output>")
                print(debug_info["raw_memory"])
            if debug_info.get("expression_error"):
                print(f"\nExpression fallback: {debug_info['expression_error']}")
            if debug_info.get("memory_error"):
                print(f"\nMemory update failed: {debug_info['memory_error']}")
            elif debug_info.get("memories_added"):
                print(f"\nMemory updated: added {debug_info['memories_added']} item(s)")


if __name__ == "__main__":
    main()
