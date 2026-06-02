import json
import math
import re
import time
from pathlib import Path
from typing import Any


MEMORY_FILE = Path(__file__).parent.parent / "data" / "memory_store.json"
MAX_SUMMARY_CHARS = 1200
MAX_MEMORY_TEXT_CHARS = 180

MEMORY_SYSTEM_PROMPT = """
你是一个本地 AI 角色系统的记忆整理器。

你的任务：
1. 更新一段简短的对话摘要，用来维持长期上下文。
2. 从最新一轮对话中抽取值得长期记住的信息。

只输出严格 JSON，不要输出解释、Markdown 或代码块。

JSON 格式：
{
  "summary": "压缩后的对话摘要，不超过 300 字",
  "memories": [
    {
      "kind": "profile/preference/project/relationship/fact/task",
      "text": "一条可以长期使用的记忆",
      "importance": 1到5之间的整数
    }
  ]
}

记忆抽取规则：
- 只记录以后可能影响回复的信息。
- 优先记录用户偏好、身份信息、项目目标、长期任务、重要约定。
- 不要记录普通寒暄。
- 不要记录一次性的无意义情绪。
- 每轮最多输出 3 条 memories，可以为空数组。
""".strip()


class MemoryStore:
    def __init__(self, path: Path | str = MEMORY_FILE) -> None:
        self.path = Path(path)
        self.summary = ""
        self.memories: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self.summary = str(data.get("summary", ""))[:MAX_SUMMARY_CHARS]
        memories = data.get("memories", [])
        if isinstance(memories, list):
            self.memories = [item for item in memories if isinstance(item, dict)]

    def save(self) -> None:
        data = {
            "summary": self.summary,
            "memories": self.memories,
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.summary = ""
        self.memories = []
        self.save()

    def retrieve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        now = time.time()
        for memory in self.memories:
            text = str(memory.get("text", ""))
            kind = str(memory.get("kind", ""))
            memory_tokens = tokenize(f"{kind} {text}")
            if not memory_tokens:
                continue

            overlap = len(query_tokens & memory_tokens)
            if overlap == 0:
                continue

            importance = int(memory.get("importance", 3))
            use_count = int(memory.get("use_count", 0))
            updated_at = float(memory.get("updated_at", memory.get("created_at", now)))
            age_days = max((now - updated_at) / 86400, 0)
            recency = 1 / (1 + math.log1p(age_days))
            score = overlap * 3 + importance + recency + min(use_count, 5) * 0.2
            scored.append((score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)
        result = [memory for _, memory in scored[:limit]]
        for memory in result:
            memory["last_used"] = now
            memory["use_count"] = int(memory.get("use_count", 0)) + 1
        if result:
            self.save()
        return result

    def add_memories(self, memories: list[dict[str, Any]]) -> int:
        added = 0
        now = time.time()
        for item in memories:
            text = normalize_memory_text(str(item.get("text", "")))
            if not text or self._has_similar_memory(text):
                continue

            kind = str(item.get("kind", "fact"))
            importance = clamp_int(item.get("importance", 3), 1, 5)
            self.memories.append(
                {
                    "id": f"mem_{int(now * 1000)}_{len(self.memories) + 1}",
                    "kind": kind,
                    "text": text,
                    "importance": importance,
                    "created_at": now,
                    "updated_at": now,
                    "last_used": 0,
                    "use_count": 0,
                }
            )
            added += 1

        if added:
            self.save()
        return added

    def update_from_model_json(self, raw_text: str) -> int:
        data = json.loads(extract_json_object(raw_text))
        summary = data.get("summary")
        if isinstance(summary, str) and summary.strip():
            self.summary = summary.strip()[:MAX_SUMMARY_CHARS]

        memories = data.get("memories", [])
        added = 0
        if isinstance(memories, list):
            added = self.add_memories([item for item in memories if isinstance(item, dict)])
        else:
            self.save()
        return added

    def _has_similar_memory(self, text: str) -> bool:
        new_tokens = tokenize(text)
        for memory in self.memories:
            old_text = str(memory.get("text", ""))
            if text == old_text:
                return True
            old_tokens = tokenize(old_text)
            if new_tokens and old_tokens:
                ratio = len(new_tokens & old_tokens) / max(len(new_tokens | old_tokens), 1)
                if ratio >= 0.75:
                    return True
        return False


def build_reply_messages(
    base_system_prompt: str,
    user_input: str,
    recent_turns: list[dict[str, Any]],
    memory_store: MemoryStore,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    relevant = memory_store.retrieve(user_input, limit=5)
    memory_context = format_memory_context(memory_store.summary, relevant)
    messages = [
        {"role": "system", "content": base_system_prompt},
        {"role": "system", "content": memory_context},
    ]

    for turn in recent_turns[-4:]:
        user = str(turn.get("user", "")).strip()
        assistant = str(turn.get("assistant", "")).strip()
        if user:
            messages.append({"role": "user", "content": user})
        if assistant:
            messages.append({"role": "assistant", "content": assistant})

    messages.append({"role": "user", "content": user_input})
    return messages, relevant


def build_memory_update_messages(
    summary: str,
    recent_turns: list[dict[str, Any]],
    user_input: str,
    assistant_reply: str,
) -> list[dict[str, str]]:
    payload = {
        "current_summary": summary,
        "recent_context": recent_turns[-4:],
        "latest_turn": {
            "user": user_input,
            "assistant": assistant_reply,
        },
    }
    return [
        {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        },
    ]


def format_memory_context(summary: str, memories: list[dict[str, Any]]) -> str:
    lines = [
        "以下是可用记忆。只在和当前问题相关时使用，不要生硬提及。",
    ]
    if summary:
        lines.append(f"对话摘要: {summary}")
    if memories:
        lines.append("相关长期记忆:")
        for memory in memories:
            kind = memory.get("kind", "fact")
            text = memory.get("text", "")
            lines.append(f"- [{kind}] {text}")
    else:
        lines.append("相关长期记忆: 无")
    return "\n".join(lines)


def tokenize(text: str) -> set[str]:
    lowered = text.lower()
    ascii_words = re.findall(r"[a-z0-9_]{2,}", lowered)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    return set(ascii_words + chinese_chars)


def normalize_memory_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())[:MAX_MEMORY_TEXT_CHARS]


def clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 3
    return max(minimum, min(maximum, number))


def extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未找到 JSON 对象")
    return text[start : end + 1]
