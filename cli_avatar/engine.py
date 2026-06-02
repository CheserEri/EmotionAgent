import json
from typing import Any

from cli_avatar.config import DEFAULT_SYSTEM_PROMPT, ConfigError, load_config
from cli_avatar.expression import (
    DEFAULT_EXPRESSION,
    build_expression_messages,
    parse_expression_json,
)
from cli_avatar.memory import (
    MemoryStore,
    build_memory_update_messages,
    build_reply_messages,
)
from cli_avatar.openai_compatible_client import OpenAICompatibleClient


MAX_TURNS = 6


class AgentEngine:
    """封装 LLM A + LLM B + 记忆系统的核心引擎，供 CLI 和 HTTP Server 共用。"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_config()
        self.config = config
        self.client = OpenAICompatibleClient(
            api_key=str(config["api_key"]),
            base_url=str(config["base_url"]),
            model=str(config["model"]),
            api_key_header=str(config["api_key_header"]),
            token_param=str(config["token_param"]),
        )
        self.memory_store = MemoryStore()
        self.turns: list[dict[str, Any]] = []
        self.debug = False

    def chat(self, user_input: str) -> dict[str, Any]:
        """处理一轮对话，返回完整行为 JSON。"""
        # 1. 构建回复消息（含记忆检索）
        reply_messages, relevant_memories = build_reply_messages(
            DEFAULT_SYSTEM_PROMPT,
            user_input,
            self.turns,
            self.memory_store,
        )

        # 2. LLM A 生成回复
        reply = self.client.chat(
            reply_messages,
            temperature=float(self.config["temperature"]),
            max_tokens=int(self.config["max_tokens"]),
        )

        # 3. LLM B 生成表情 JSON
        expression_messages = build_expression_messages(user_input, reply, self.turns)
        expression_error = ""
        raw_expression = ""
        try:
            raw_expression = self.client.chat(
                expression_messages,
                temperature=0.2,
                max_tokens=int(self.config["max_tokens"]),
            )
            expression = parse_expression_json(raw_expression)
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            expression_error = str(exc)
            expression = DEFAULT_EXPRESSION.copy()

        # 4. 更新上下文
        self.turns.append(
            {
                "user": user_input,
                "assistant": reply,
                "expression": expression,
            }
        )
        self.turns = self.turns[-MAX_TURNS:]

        # 5. LLM C 更新记忆
        memory_error = ""
        memories_added = 0
        raw_memory = ""
        try:
            raw_memory = self.client.chat(
                build_memory_update_messages(
                    self.memory_store.summary,
                    self.turns,
                    user_input,
                    reply,
                ),
                temperature=0.2,
                max_tokens=max(int(self.config["max_tokens"]), 2048),
            )
            memories_added = self.memory_store.update_from_model_json(raw_memory)
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            memory_error = str(exc)

        # 6. 组装返回结果
        result: dict[str, Any] = {
            "text": reply,
            "emotion": expression["emotion"],
            "expression": expression["expression"],
            "action": expression["action"],
            "voice_style": expression["voice_style"],
            "duration": expression["duration"],
        }

        if self.debug:
            result["_debug"] = {
                "relevant_memories": relevant_memories,
                "raw_expression": raw_expression,
                "raw_memory": raw_memory,
                "expression_error": expression_error,
                "memory_error": memory_error,
                "memories_added": memories_added,
            }

        return result

    def reset(self) -> None:
        """清空对话上下文（保留长期记忆）。"""
        self.turns = []

    def reset_all(self) -> None:
        """清空对话上下文和所有记忆。"""
        self.turns = []
        self.memory_store.clear()

    def get_memory_info(self) -> dict[str, Any]:
        """获取当前记忆状态。"""
        return {
            "summary": self.memory_store.summary,
            "memories": self.memory_store.memories,
        }

    def get_history(self) -> list[dict[str, Any]]:
        """获取最近对话历史。"""
        return self.turns
