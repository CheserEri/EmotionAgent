import json
import re
from typing import Any


EMOTIONS = {
    "happy",
    "sad",
    "angry",
    "surprised",
    "calm",
    "thinking",
    "concerned",
}
EXPRESSIONS = {
    "smile",
    "soft_smile",
    "blink",
    "surprised",
    "sad_eyes",
    "angry_face",
    "thinking_face",
    "neutral",
}
ACTIONS = {
    "idle",
    "nod",
    "shake_head",
    "wave_hand",
    "tilt_head",
    "look_down",
}
VOICE_STYLES = {
    "cheerful",
    "soft",
    "serious",
    "calm",
    "curious",
}

DEFAULT_EXPRESSION = {
    "emotion": "calm",
    "expression": "neutral",
    "action": "idle",
    "voice_style": "calm",
    "duration": 1200,
}

EXPRESSION_SYSTEM_PROMPT = """
你是一个 AI 角色系统里的表情行为编译器。

你不会直接和用户聊天。
你的任务是根据用户输入、助手回复和最近上下文，判断当前最合适的情绪、表情、动作和语音风格。

最高优先级规则：
你必须只输出一个 JSON 对象。
不要输出解释。
不要输出 Markdown。
不要输出代码块。
不要输出问候语。
不要复述用户输入。
第一个字符必须是 {，最后一个字符必须是 }。

JSON 字段：
- emotion: happy/sad/angry/surprised/calm/thinking/concerned
- expression: smile/soft_smile/blink/surprised/sad_eyes/angry_face/thinking_face/neutral
- action: idle/nod/shake_head/wave_hand/tilt_head/look_down
- voice_style: cheerful/soft/serious/calm/curious
- duration: 800 到 4000 之间的整数，单位毫秒

决策原则：
- 用户表达疲惫、难过、压力时，优先 concerned/calm + soft_smile/sad_eyes
- 用户表达开心、成功、感谢时，优先 happy + smile
- 用户提出问题或不确定内容时，优先 thinking + thinking_face
- 表情和动作要克制，不要每轮都夸张
- 如果没有明显情绪，使用 calm + neutral 或 soft_smile

正确输出示例：
{"emotion":"calm","expression":"soft_smile","action":"nod","voice_style":"soft","duration":1800}
""".strip()


def build_expression_messages(
    user_input: str,
    assistant_reply: str,
    recent_turns: list[dict[str, Any]],
) -> list[dict[str, str]]:
    payload = {
        "user_input": user_input,
        "assistant_reply": assistant_reply,
        "recent_context": recent_turns[-6:],
    }
    return [
        {"role": "system", "content": EXPRESSION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请把下面输入编译成一个表情 JSON。只输出 JSON 对象。\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
            ),
        },
    ]


def parse_expression_json(raw_text: str) -> dict[str, Any]:
    data = json.loads(extract_json_object(raw_text))
    return validate_expression(data)


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


def validate_expression(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象")

    expression = {
        "emotion": require_enum(data, "emotion", EMOTIONS),
        "expression": require_enum(data, "expression", EXPRESSIONS),
        "action": require_enum(data, "action", ACTIONS),
        "voice_style": require_enum(data, "voice_style", VOICE_STYLES),
        "duration": require_duration(data),
    }
    return expression


def require_enum(data: dict[str, Any], field: str, allowed: set[str]) -> str:
    value = data.get(field)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field} 必须是允许枚举之一")
    return value


def require_duration(data: dict[str, Any]) -> int:
    value = data.get("duration")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("duration 必须是整数")
    if value < 800 or value > 4000:
        raise ValueError("duration 必须在 800 到 4000 之间")
    return value


def format_expression(expression: dict[str, Any]) -> str:
    return json.dumps(expression, ensure_ascii=False, indent=2)
