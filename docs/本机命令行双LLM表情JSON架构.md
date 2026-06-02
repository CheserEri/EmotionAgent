# 本机命令行双 LLM 表情 JSON MVP 架构

> 目标：先不接 ESP32、不接语音，只在本机命令行里完成最小闭环：
> **用户输入 → LLM A 回复文本 → LLM B 生成表情 JSON → 命令行展示结果**。

---

## 1. MVP 目标

本阶段只验证一件事：

**能否让两个大模型角色稳定协作，产出“可执行的角色反馈包”。**

其中：

- **LLM A：对话模型**
  - 负责像角色本人一样回复用户
  - 输出自然语言文本
  - 不负责 JSON，不负责表情动作判断

- **LLM B：表情编译模型**
  - 读取用户输入、历史上下文、LLM A 的回复
  - 判断角色当前情绪、表情、动作和语气
  - 严格输出 JSON

最终命令行输出两部分：

```text
AI: 你好呀，我也很开心见到你。

JSON:
{
  "emotion": "happy",
  "expression": "smile",
  "action": "idle",
  "voice_style": "cheerful",
  "duration": 1800
}
```

---

## 2. 整体架构

```text
┌────────────────────┐
│     CLI 输入循环    │
│  用户在终端输入文本  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Conversation     │
│   Context Manager  │
│  保存最近 N 轮对话  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│       LLM A         │
│    Reply Agent      │
│  生成角色自然回复    │
└─────────┬──────────┘
          │ reply_text
          ▼
┌────────────────────┐
│       LLM B         │
│ Expression Agent    │
│  生成表情行为 JSON   │
└─────────┬──────────┘
          │ expression_json
          ▼
┌────────────────────┐
│   JSON Validator    │
│ Schema 校验与降级处理 │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    CLI Renderer     │
│ 显示文本与 JSON 结果 │
└────────────────────┘
```

---

## 3. 数据流

### 单轮对话流程

```text
1. 用户在命令行输入：
   今天有点累。

2. 系统把输入和最近上下文交给 LLM A。

3. LLM A 输出角色回复：
   辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。

4. 系统把以下信息交给 LLM B：
   - 用户本轮输入
   - LLM A 本轮回复
   - 最近几轮对话摘要
   - 当前允许的 emotion/expression/action 枚举

5. LLM B 输出 JSON：
   {
     "emotion": "calm",
     "expression": "soft_smile",
     "action": "nod",
     "voice_style": "soft",
     "duration": 2200
   }

6. 系统校验 JSON。

7. 命令行同时显示：
   - AI 文本回复
   - 表情行为 JSON
```

---

## 4. 模块划分

建议先用 Python 实现，目录结构如下：

```text
Emotion-Agent/
  cli_avatar/
    __init__.py
    main.py                 # CLI 主入口
    config.py               # API Key、模型名、运行参数
    context.py              # 最近对话上下文管理
    agents/
      __init__.py
      reply_agent.py        # LLM A：回复 Agent
      expression_agent.py   # LLM B：表情 JSON Agent
    schemas/
      expression_schema.py  # JSON Schema / Pydantic 模型
    prompts/
      reply_agent.md        # A 的角色 Prompt
      expression_agent.md   # B 的 JSON Prompt
```

---

## 5. LLM A：回复 Agent

### 职责

LLM A 只负责生成角色说的话。

它不输出 JSON，不输出动作说明，不解释自己的表情。

### 输入

```json
{
  "character_profile": "角色人格设定",
  "recent_messages": [
    {"role": "user", "content": "今天有点累。"}
  ]
}
```

### 输出

```text
辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。
```

### Prompt 草案

```text
你是一个运行在桌面终端里的 AI 角色。

请根据用户输入，用自然、简短、有情绪温度的方式回复。

要求：
- 只输出你要对用户说的话
- 不要输出 JSON
- 不要描述自己的表情或动作
- 回复长度控制在 1 到 3 句话
- 语气保持真诚、轻松、有人格感
```

---

## 6. LLM B：表情 JSON Agent

### 职责

LLM B 是“表情行为编译器”。

它不和用户聊天，只把对话语义转换为结构化表情 JSON。

### 输入

```json
{
  "user_input": "今天有点累。",
  "assistant_reply": "辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。",
  "recent_context": [
    {
      "user": "今天有点累。",
      "assistant": "辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。"
    }
  ]
}
```

### 输出

必须严格输出 JSON：

```json
{
  "emotion": "calm",
  "expression": "soft_smile",
  "action": "nod",
  "voice_style": "soft",
  "duration": 2200
}
```

### 可选枚举

#### emotion

```text
happy
sad
angry
surprised
calm
thinking
concerned
```

#### expression

```text
smile
soft_smile
blink
surprised
sad_eyes
angry_face
thinking_face
neutral
```

#### action

```text
idle
nod
shake_head
wave_hand
tilt_head
look_down
```

#### voice_style

```text
cheerful
soft
serious
calm
curious
```

### Prompt 草案

```text
你是一个 AI 角色系统里的表情行为编译器。

你不会直接和用户聊天。
你的任务是根据用户输入和助手回复，判断当前最合适的情绪、表情、动作和语音风格。

只允许输出严格 JSON，不允许输出解释、Markdown、代码块或任何额外文字。

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
```

---

## 7. JSON Schema

第一版表情包不包含 `text`，因为文本由 LLM A 单独负责。

```json
{
  "type": "object",
  "required": [
    "emotion",
    "expression",
    "action",
    "voice_style",
    "duration"
  ],
  "properties": {
    "emotion": {
      "type": "string",
      "enum": [
        "happy",
        "sad",
        "angry",
        "surprised",
        "calm",
        "thinking",
        "concerned"
      ]
    },
    "expression": {
      "type": "string",
      "enum": [
        "smile",
        "soft_smile",
        "blink",
        "surprised",
        "sad_eyes",
        "angry_face",
        "thinking_face",
        "neutral"
      ]
    },
    "action": {
      "type": "string",
      "enum": [
        "idle",
        "nod",
        "shake_head",
        "wave_hand",
        "tilt_head",
        "look_down"
      ]
    },
    "voice_style": {
      "type": "string",
      "enum": [
        "cheerful",
        "soft",
        "serious",
        "calm",
        "curious"
      ]
    },
    "duration": {
      "type": "integer",
      "minimum": 800,
      "maximum": 4000
    }
  },
  "additionalProperties": false
}
```

---

## 8. 命令行交互设计

### 启动方式

```bash
python -m cli_avatar.main
```

### 运行效果

```text
Emotion Agent CLI
Type /exit to quit.

You> 今天有点累

AI> 辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。

Expression JSON>
{
  "emotion": "calm",
  "expression": "soft_smile",
  "action": "nod",
  "voice_style": "soft",
  "duration": 2200
}
```

### 特殊命令

```text
/exit      退出
/clear     清空上下文
/history   查看最近对话
/debug     显示 LLM A/B 原始请求与响应
```

---

## 9. 上下文策略

第一版只保留最近 N 轮对话，不做长期记忆。

建议：

```text
MAX_HISTORY_TURNS = 6
```

每轮保存：

```json
{
  "user": "今天有点累。",
  "assistant": "辛苦啦，要不要先慢一点？我可以陪你安静待一会儿。",
  "expression": {
    "emotion": "calm",
    "expression": "soft_smile",
    "action": "nod",
    "voice_style": "soft",
    "duration": 2200
  }
}
```

---

## 10. 错误处理

### LLM A 失败

降级回复：

```text
我刚刚有点没反应过来，可以再说一遍吗？
```

### LLM B 输出非法 JSON

处理顺序：

```text
1. 尝试提取 JSON 对象
2. 尝试重新请求 LLM B 修复格式
3. 仍失败则使用默认表情包
```

默认表情包：

```json
{
  "emotion": "calm",
  "expression": "neutral",
  "action": "idle",
  "voice_style": "calm",
  "duration": 1200
}
```

---

## 11. 模型调用策略

### 串行调用

第一版使用串行调用：

```text
用户输入 → LLM A → LLM B → 输出
```

原因：

- LLM B 需要读取 A 的回复
- 逻辑简单
- 容易调试

### 后续可优化

未来可以让 B 先根据用户输入预测初始表情，再在 A 回复后修正：

```text
用户输入 ─┬─→ LLM A 生成回复
          └─→ LLM B 预测表情
                    ↓
              A 完成后微调 JSON
```

---

## 12. 后续扩展路径

### 阶段 1：CLI MVP

```text
用户文本输入
LLM A 回复文本
LLM B 输出表情 JSON
命令行展示
```

### 阶段 2：本机可视化

```text
根据 expression 字段在终端或桌面窗口显示 ASCII 表情 / 图片表情
```

### 阶段 3：加入 TTS

```text
LLM A 回复文本 → TTS → 本机播放语音
```

### 阶段 4：接入 ESP32

```text
把 expression JSON 通过串口 / WebSocket / MQTT 发给 ESP32
```

### 阶段 5：完整 Avatar 包

```json
{
  "text": "辛苦啦，要不要先慢一点？",
  "emotion": "calm",
  "expression": "soft_smile",
  "action": "nod",
  "voice_style": "soft",
  "duration": 2200
}
```

---

## 13. 第一版验收标准

满足以下条件即可认为 CLI MVP 成功：

- 可以在命令行连续多轮对话
- LLM A 回复自然语言
- LLM B 稳定输出合法 JSON
- JSON 字段全部来自允许枚举
- 非法 JSON 有默认降级处理
- 最近上下文能影响后续回复和表情判断

---

## 14. 建议下一步

下一步可以直接实现 Python CLI：

```text
1. 创建 cli_avatar 目录
2. 写两个 Prompt 文件
3. 写 OpenAI / 兼容 API 调用封装
4. 写 Pydantic 表情 Schema
5. 写 main.py 输入循环
```

