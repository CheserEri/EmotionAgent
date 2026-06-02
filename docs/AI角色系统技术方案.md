# AI 角色系统技术方案（Embodied AI Avatar）

> 一个以大语言模型为大脑、以 ESP32 为执行终端的完整 AI 角色系统。
> 核心思想：**让大模型输出行为指令，设备端并行执行角色表现。**

---

## 一、项目定位

这不是一个普通的语音助手，也不是电子徽章。它是：

**AI 角色终端（Embodied AI）**——云端负责智能，设备端负责表演。

类比：简化版 VTuber / 桌面数字人，但运行在嵌入式硬件上。

---

## 二、核心架构原则

### 关键认知

- 设备端（ESP32）**不运行大模型**，它只是执行引擎
- 大模型运行在云端，输出的不是普通文本，而是**结构化行为指令（JSON）**
- 云端负责智能决策，设备端负责忠实还原

### 整体数据流

```
用户说话
  → 设备录音 → 上传
  → 云端 STT（语音转文字）
  → 云端 LLM（多 Agent 协作处理）
  → 返回结构化 JSON 包
  → 设备解析 → 并行执行：语音 + 表情 + 动作
```

---

## 三、JSON 输出协议（核心设计）

LLM 不输出普通文本，而是输出"行为包"：

```json
{
  "text": "你好呀，我很开心见到你！",
  "emotion": "happy",
  "expression": "smile",
  "action": "wave_hand",
  "voice_style": "cheerful",
  "duration": 2000
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 说的内容，用于 TTS 合成 |
| `emotion` | string | 情绪状态：`happy / sad / angry / surprised / calm` |
| `expression` | string | 表情指令：`smile / cry / angry_face / blink` |
| `action` | string | 动作指令：`wave_hand / nod / shake / blink` |
| `voice_style` | string | 音色风格：`cheerful / soft / serious` |
| `duration` | int | 动作持续时间（ms） |

### Prompt 工程模板

```
你是一个 AI 角色，名字叫 [角色名]。
请严格以 JSON 格式回复，包含以下字段：
- text：你说的话
- emotion：你的情绪（happy/sad/angry/surprised/calm）
- expression：表情（smile/cry/blink/surprised）
- action：动作（wave_hand/nod/shake/idle）
- voice_style：音色（cheerful/soft/serious）
- duration：动作持续毫秒数

禁止输出 JSON 以外的任何内容。
```

---

## 四、云端多 Agent 协作架构

### 架构总览

<svg width="100%" viewBox="0 0 680 740" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="a1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#888780" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="a2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#7F77DD" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="a3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#1D9E75" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="a4" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#993C1D" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- 用户输入 -->
  <rect x="260" y="30" width="160" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="340" y="52" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">用户输入</text>
  <line x1="340" y1="74" x2="340" y2="118" stroke="#888780" stroke-width="1" marker-end="url(#a1)"/>
  <!-- 自我核心 Agent -->
  <rect x="190" y="120" width="300" height="68" rx="10" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.8"/>
  <text x="340" y="145" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#3C3489">自我核心 Agent</text>
  <text x="340" y="166" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#534AB7">Orchestrator · 人格主体 · 决策调度</text>
  <!-- 核心到子Agent连线 -->
  <line x1="230" y1="188" x2="92" y2="258" stroke="#7F77DD" stroke-width="1" marker-end="url(#a2)"/>
  <line x1="280" y1="188" x2="220" y2="258" stroke="#7F77DD" stroke-width="1" marker-end="url(#a2)"/>
  <line x1="340" y1="188" x2="340" y2="258" stroke="#7F77DD" stroke-width="1" marker-end="url(#a2)"/>
  <line x1="400" y1="188" x2="460" y2="258" stroke="#7F77DD" stroke-width="1" marker-end="url(#a2)"/>
  <line x1="450" y1="188" x2="590" y2="258" stroke="#7F77DD" stroke-width="1" marker-end="url(#a2)"/>
  <!-- 子Agent行：5个，宽110px，间距14px，x从37 -->
  <rect x="37" y="260" width="110" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="92" y="281" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">对话 Agent</text>
  <text x="92" y="299" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">生成回复文本</text>
  <rect x="161" y="260" width="110" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="216" y="281" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">情绪 Agent</text>
  <text x="216" y="299" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">情绪状态建模</text>
  <rect x="285" y="260" width="110" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="340" y="281" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">记忆 Agent</text>
  <text x="340" y="299" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">读写长短期记忆</text>
  <rect x="409" y="260" width="110" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="464" y="281" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">表情 Agent</text>
  <text x="464" y="299" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">映射表情指令</text>
  <rect x="533" y="260" width="110" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="588" y="281" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">动作 Agent</text>
  <text x="588" y="299" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">选择肢体动作</text>
  <!-- 子Agent到聚合层 -->
  <line x1="92" y1="316" x2="200" y2="380" stroke="#1D9E75" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#a3)"/>
  <line x1="216" y1="316" x2="258" y2="380" stroke="#1D9E75" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#a3)"/>
  <line x1="340" y1="316" x2="340" y2="380" stroke="#1D9E75" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#a3)"/>
  <line x1="464" y1="316" x2="420" y2="380" stroke="#1D9E75" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#a3)"/>
  <line x1="588" y1="316" x2="480" y2="380" stroke="#1D9E75" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#a3)"/>
  <!-- 响应编译器 -->
  <rect x="170" y="382" width="340" height="56" rx="10" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="340" y="403" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#712B13">响应编译器</text>
  <text x="340" y="421" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#993C1D">合并输出 · 冲突仲裁 · 生成最终JSON包</text>
  <line x1="340" y1="438" x2="340" y2="482" stroke="#993C1D" stroke-width="1" marker-end="url(#a4)"/>
  <!-- JSON包展示 -->
  <rect x="170" y="484" width="340" height="108" rx="8" fill="none" stroke="#888780" stroke-width="0.5"/>
  <text x="186" y="504" dominant-baseline="central" font-size="12" fill="#888780">最终输出包</text>
  <text x="186" y="524" dominant-baseline="central" font-size="12" fill="#444441" font-family="monospace">"text":  "你好呀！"</text>
  <text x="186" y="542" dominant-baseline="central" font-size="12" fill="#444441" font-family="monospace">"emotion": "happy"</text>
  <text x="186" y="560" dominant-baseline="central" font-size="12" fill="#444441" font-family="monospace">"expression": "smile"</text>
  <text x="186" y="578" dominant-baseline="central" font-size="12" fill="#444441" font-family="monospace">"action": "wave_hand"</text>
  <!-- 输出到设备 -->
  <line x1="340" y1="592" x2="340" y2="636" stroke="#888780" stroke-width="1" marker-end="url(#a1)"/>
  <rect x="200" y="638" width="280" height="56" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="340" y="659" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">设备执行引擎 (ESP32)</text>
  <text x="340" y="677" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">并行执行 · 语音 + 表情 + 动作</text>
  <!-- 记忆回写回路 -->
  <path d="M 340 694 L 50 694 L 50 154" fill="none" stroke="#888780" stroke-width="0.8" stroke-dasharray="5 4" marker-end="url(#a1)"/>
  <text x="38" y="430" dominant-baseline="central" font-size="12" fill="#888780" transform="rotate(-90,38,430)">记忆回写</text>
</svg>

### Agent 分工

```
用户输入
  ↓
自我核心 Agent（Orchestrator）
  ├─→ 对话 Agent：生成回复文本
  ├─→ 情绪 Agent：推断当前情绪状态
  ├─→ 记忆 Agent：读写长短期记忆
  ├─→ 表情 Agent：将情绪映射为表情指令
  └─→ 动作 Agent：根据语义选择肢体动作
           ↓
     响应编译器（合并 + 冲突仲裁）
           ↓
     最终 JSON 包
```

### 关键设计

- **自我核心 Agent** 不直接输出内容，只负责决策和调度
- 五路子 Agent **并行处理**，由响应编译器做最终合并
- 冲突仲裁规则：情绪优先于动作，人格一致性优先于单次输出

---

## 五、记忆与认知系统

### 分层记忆与读写机制总览

<svg width="100%" viewBox="0 0 680 720" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="b1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#888780" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="b2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#185FA5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="b3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#0F6E56" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="b4" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#534AB7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="b5" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#BA7517" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- 左列标签 -->
  <text x="42" y="58" dominant-baseline="central" font-size="12" fill="#888780">层级</text>
  <!-- L1 感知缓冲 -->
  <rect x="106" y="36" width="148" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="180" y="58" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">感知缓冲</text>
  <text x="180" y="96" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">当前对话上下文窗口</text>
  <text x="180" y="114" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">≈ 感觉记忆 (秒级)</text>
  <!-- L2 工作记忆 -->
  <rect x="90" y="140" width="180" height="44" rx="8" fill="#E6F1FB" stroke="#185FA5" stroke-width="0.5"/>
  <text x="180" y="162" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#0C447C">工作记忆</text>
  <text x="180" y="200" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#185FA5">最近N轮对话摘要</text>
  <text x="180" y="218" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">≈ 短期记忆 (分钟~小时)</text>
  <!-- L3 情景记忆 -->
  <rect x="74" y="250" width="212" height="44" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="180" y="272" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">情景记忆</text>
  <text x="180" y="310" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">发生过的事件 · 用户历史</text>
  <text x="180" y="328" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">≈ 长期情景记忆 (天~年)</text>
  <!-- L4 语义记忆 -->
  <rect x="74" y="360" width="212" height="44" rx="8" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
  <text x="180" y="382" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#3C3489">语义记忆</text>
  <text x="180" y="420" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#534AB7">世界知识 · 用户偏好归纳</text>
  <text x="180" y="438" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">≈ 长期语义记忆 (永久)</text>
  <!-- L5 核心人格 -->
  <rect x="74" y="470" width="212" height="44" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="180" y="492" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#712B13">核心人格</text>
  <text x="180" y="530" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#993C1D">性格 · 价值观 · 说话风格</text>
  <text x="180" y="548" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">≈ 自我概念 (极慢演化)</text>
  <!-- 左侧层级连线 -->
  <line x1="180" y1="80" x2="180" y2="140" stroke="#888780" stroke-width="1" marker-end="url(#b1)"/>
  <line x1="180" y1="184" x2="180" y2="250" stroke="#185FA5" stroke-width="1" marker-end="url(#b2)"/>
  <line x1="180" y1="294" x2="180" y2="360" stroke="#0F6E56" stroke-width="1" marker-end="url(#b3)"/>
  <line x1="180" y1="404" x2="180" y2="470" stroke="#534AB7" stroke-width="1" marker-end="url(#b4)"/>
  <text x="180" y="590" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#888780">↑ 越往下越稳定，遗忘发生在L1-L3</text>
  <!-- 分隔线 -->
  <line x1="320" y1="20" x2="320" y2="680" stroke="#888780" stroke-width="0.5" opacity="0.2"/>
  <!-- 右侧读写机制标题 -->
  <text x="500" y="38" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">记忆读写机制</text>
  <!-- 触发检索 -->
  <rect x="358" y="60" width="280" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="498" y="81" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">触发式检索</text>
  <text x="498" y="99" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">输入语义 → 向量相似度召回</text>
  <line x1="498" y1="116" x2="498" y2="160" stroke="#BA7517" stroke-width="1" marker-end="url(#b5)"/>
  <!-- 记忆融合 -->
  <rect x="358" y="162" width="280" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="498" y="183" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">记忆融合注入</text>
  <text x="498" y="201" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">多层召回 → 压缩 → 注入Prompt</text>
  <line x1="498" y1="218" x2="498" y2="262" stroke="#BA7517" stroke-width="1" marker-end="url(#b5)"/>
  <!-- 情绪着色 -->
  <rect x="358" y="264" width="280" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="498" y="285" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">情绪着色</text>
  <text x="498" y="303" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">当前情绪影响记忆检索权重</text>
  <line x1="498" y1="320" x2="498" y2="364" stroke="#BA7517" stroke-width="1" marker-end="url(#b5)"/>
  <!-- 归纳写入 -->
  <rect x="358" y="366" width="280" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="498" y="387" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">归纳写入</text>
  <text x="498" y="405" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">对话后摘要 → 更新情景/语义层</text>
  <line x1="498" y1="422" x2="498" y2="466" stroke="#BA7517" stroke-width="1" marker-end="url(#b5)"/>
  <!-- 主动遗忘 -->
  <rect x="358" y="468" width="280" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="498" y="489" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">主动遗忘</text>
  <text x="498" y="507" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">时间衰减 + 重要性评分过滤</text>
  <!-- 横向虚线连接左右 -->
  <line x1="286" y1="58" x2="356" y2="88" stroke="#888780" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#b1)"/>
  <line x1="270" y1="162" x2="356" y2="190" stroke="#185FA5" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#b1)"/>
  <line x1="286" y1="272" x2="356" y2="292" stroke="#0F6E56" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#b1)"/>
  <line x1="286" y1="382" x2="356" y2="394" stroke="#534AB7" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#b1)"/>
  <line x1="286" y1="492" x2="356" y2="496" stroke="#993C1D" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#b1)"/>
  <!-- 技术栈 -->
  <rect x="358" y="548" width="280" height="100" rx="8" fill="none" stroke="#888780" stroke-width="0.5"/>
  <text x="374" y="568" dominant-baseline="central" font-size="12" fill="#5F5E5A">推荐技术栈</text>
  <text x="374" y="590" dominant-baseline="central" font-size="12" fill="#444441">向量库: Qdrant / Pinecone / pgvector</text>
  <text x="374" y="610" dominant-baseline="central" font-size="12" fill="#444441">图数据库: Neo4j（关系推理）</text>
  <text x="374" y="630" dominant-baseline="central" font-size="12" fill="#444441">KV存储: Redis（工作记忆）</text>
  <text x="374" y="650" dominant-baseline="central" font-size="12" fill="#444441">摘要模型: Claude / GPT-4o mini</text>
</svg>

### 分层记忆结构（模拟真人认知）

| 层级 | 名称 | 对应真人 | 存储方式 | 生命周期 |
|------|------|---------|---------|---------|
| L1 | 感知缓冲 | 感觉记忆 | 对话上下文窗口 | 秒级 |
| L2 | 工作记忆 | 短期记忆 | Redis 滑动窗口 | 分钟~小时 |
| L3 | 情景记忆 | 长期情景 | 向量数据库（Qdrant）| 天~年 |
| L4 | 语义记忆 | 长期语义 | 结构化 JSON + 向量库 | 永久 |
| L5 | 核心人格 | 自我概念 | YAML 文件（慢速更新）| 极慢演化 |

### 记忆读写机制

1. **触发式检索**：输入语义 → 向量相似度召回多层记忆
2. **记忆融合注入**：多层召回结果压缩后注入 Prompt
3. **情绪着色**：当前情绪状态影响记忆检索权重
4. **归纳写入**：对话结束后异步摘要，更新情景/语义层
5. **主动遗忘**：时间衰减 + 重要性评分，模拟艾宾浩斯遗忘曲线

### 推荐技术栈

- 向量库：Qdrant / Pinecone / pgvector
- 图数据库：Neo4j（关系推理）
- KV 存储：Redis（工作记忆）
- 摘要模型：Claude / GPT-4o mini

---

## 六、情绪状态机

### 情绪状态机设计图

<svg width="100%" viewBox="0 0 680 580" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="c1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#888780" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="c2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#534AB7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="c3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#0F6E56" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- 刺激评估器 -->
  <rect x="240" y="30" width="200" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="340" y="52" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">刺激评估器</text>
  <text x="340" y="90" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">输入内容 × 历史关系 × 当前情绪基线</text>
  <!-- 评估器到各情绪的箭头 -->
  <line x1="290" y1="74" x2="120" y2="120" stroke="#888780" stroke-width="0.8" marker-end="url(#c1)"/>
  <line x1="315" y1="74" x2="230" y2="120" stroke="#3B6D11" stroke-width="0.8" marker-end="url(#c1)"/>
  <line x1="340" y1="74" x2="340" y2="120" stroke="#185FA5" stroke-width="0.8" marker-end="url(#c1)"/>
  <line x1="365" y1="74" x2="450" y2="120" stroke="#BA7517" stroke-width="0.8" marker-end="url(#c1)"/>
  <line x1="390" y1="74" x2="560" y2="120" stroke="#A32D2D" stroke-width="0.8" marker-end="url(#c1)"/>
  <!-- 五个情绪节点 -->
  <rect x="70" y="120" width="100" height="56" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="120" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">平静</text>
  <text x="120" y="159" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">基准状态</text>
  <rect x="180" y="120" width="100" height="56" rx="8" fill="#EAF3DE" stroke="#3B6D11" stroke-width="0.5"/>
  <text x="230" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#27500A">开心</text>
  <text x="230" y="159" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#3B6D11">高效 · 活跃</text>
  <rect x="290" y="120" width="100" height="56" rx="8" fill="#E6F1FB" stroke="#185FA5" stroke-width="0.5"/>
  <text x="340" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#0C447C">难过</text>
  <text x="340" y="159" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#185FA5">低沉 · 内敛</text>
  <rect x="400" y="120" width="100" height="56" rx="8" fill="#FAEEDA" stroke="#BA7517" stroke-width="0.5"/>
  <text x="450" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#633806">惊讶</text>
  <text x="450" y="159" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#854F0B">短暂 · 快速</text>
  <rect x="510" y="120" width="100" height="56" rx="8" fill="#FCEBEB" stroke="#A32D2D" stroke-width="0.5"/>
  <text x="560" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#791F1F">生气</text>
  <text x="560" y="159" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#A32D2D">强烈 · 边界感</text>
  <!-- 情绪到向量空间 -->
  <line x1="340" y1="176" x2="340" y2="224" stroke="#888780" stroke-width="1" marker-end="url(#c1)"/>
  <!-- 情绪向量空间 -->
  <rect x="170" y="226" width="340" height="56" rx="8" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
  <text x="340" y="247" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#3C3489">情绪向量空间</text>
  <text x="340" y="265" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#534AB7">Valence(愉悦度) × Arousal(唤醒度) 连续坐标</text>
  <line x1="340" y1="282" x2="340" y2="326" stroke="#534AB7" stroke-width="1" marker-end="url(#c2)"/>
  <!-- 情绪调制输出 -->
  <rect x="130" y="328" width="420" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="340" y="349" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">情绪调制输出</text>
  <text x="340" y="367" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">语速 · 用词选择 · 动作强度 · 表情深度</text>
  <!-- 衰减回路 -->
  <path d="M 130 356 L 60 356 L 60 148 L 70 148" fill="none" stroke="#888780" stroke-width="0.8" stroke-dasharray="4 3" marker-end="url(#c1)"/>
  <text x="40" y="260" dominant-baseline="central" font-size="12" fill="#888780">自然衰减</text>
  <!-- 关键设计原则 -->
  <rect x="60" y="420" width="560" height="120" rx="10" fill="none" stroke="#888780" stroke-width="0.5"/>
  <text x="80" y="442" dominant-baseline="central" font-size="12" fill="#5F5E5A">关键设计原则</text>
  <text x="80" y="466" dominant-baseline="central" font-size="12" fill="#444441">1. 情绪有惯性：不能瞬间切换，需要过渡帧</text>
  <text x="80" y="488" dominant-baseline="central" font-size="12" fill="#444441">2. 情绪有记忆：上次伤心，下次见面仍有隐性警觉</text>
  <text x="80" y="510" dominant-baseline="central" font-size="12" fill="#444441">3. 情绪影响认知：生气时检索偏激进记忆</text>
  <text x="80" y="532" dominant-baseline="central" font-size="12" fill="#444441">4. 情绪可被调节：内部机制让角色能自我平复</text>
</svg>

### 设计原则（让情绪像真人）

1. **情绪有惯性**：不能瞬间切换，需要过渡帧（真人情绪有持续时间）
2. **情绪有记忆**：同一用户让角色伤心过，下次见面会有隐性警觉
3. **情绪影响认知**：生气时检索偏激进记忆，开心时创造力更高
4. **情绪可被调节**：内部平复机制让角色能自然恢复基准状态

### 情绪向量空间

使用 **Valence（愉悦度）× Arousal（唤醒度）** 二维连续坐标，而非离散枚举。

- 优势：情绪之间有自然的渐变过渡，避免机械切换
- 实现：情绪状态持久化在 Redis，每次对话加载上次残余值

```python
# 情绪状态示例
emotion_state = {
    "valence": 0.7,   # -1.0（极负）~ 1.0（极正）
    "arousal": 0.5,   # 0.0（平静）~ 1.0（高度激动）
    "decay_rate": 0.1 # 每轮对话自然衰减向基准靠拢
}
```

---

## 七、ESP32 设备端执行引擎

### 并行执行架构图

<svg width="100%" viewBox="0 0 680 660" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="d1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#888780" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="d2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#7F77DD" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="d3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#1D9E75" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- JSON包接收 -->
  <rect x="230" y="30" width="220" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="340" y="52" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">接收 JSON 包</text>
  <line x1="340" y1="74" x2="340" y2="118" stroke="#888780" stroke-width="1" marker-end="url(#d1)"/>
  <!-- 调度器 -->
  <rect x="190" y="120" width="300" height="56" rx="10" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.8"/>
  <text x="340" y="141" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#3C3489">调度器 Task (Core 1)</text>
  <text x="340" y="160" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#534AB7">JSON解析 · 时序对齐 · 三路分发</text>
  <!-- 三路队列箭头 -->
  <line x1="250" y1="176" x2="115" y2="240" stroke="#7F77DD" stroke-width="1" marker-end="url(#d2)"/>
  <line x1="340" y1="176" x2="340" y2="240" stroke="#7F77DD" stroke-width="1" marker-end="url(#d2)"/>
  <line x1="430" y1="176" x2="565" y2="240" stroke="#7F77DD" stroke-width="1" marker-end="url(#d2)"/>
  <!-- 队列标签 -->
  <text x="158" y="218" dominant-baseline="central" font-size="11" fill="#888780">audio_queue</text>
  <text x="290" y="218" dominant-baseline="central" font-size="11" fill="#888780">face_queue</text>
  <text x="468" y="218" dominant-baseline="central" font-size="11" fill="#888780">motion_queue</text>
  <!-- 三个Task：宽160px，间距26px，x从40 -->
  <rect x="40" y="242" width="160" height="68" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="120" y="263" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">语音 Task</text>
  <text x="120" y="281" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Priority: HIGH</text>
  <text x="120" y="297" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Core 0 · I2S驱动</text>
  <rect x="260" y="242" width="160" height="68" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="340" y="263" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">表情 Task</text>
  <text x="340" y="281" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Priority: NORMAL</text>
  <text x="340" y="297" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Core 1 · SPI/TFT</text>
  <rect x="480" y="242" width="160" height="68" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="560" y="263" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#085041">动作 Task</text>
  <text x="560" y="281" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Priority: NORMAL</text>
  <text x="560" y="297" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#0F6E56">Core 1 · PWM/GPIO</text>
  <!-- Task到硬件 -->
  <line x1="120" y1="310" x2="120" y2="360" stroke="#1D9E75" stroke-width="1" marker-end="url(#d3)"/>
  <line x1="340" y1="310" x2="340" y2="360" stroke="#1D9E75" stroke-width="1" marker-end="url(#d3)"/>
  <line x1="560" y1="310" x2="560" y2="360" stroke="#1D9E75" stroke-width="1" marker-end="url(#d3)"/>
  <!-- 硬件层 -->
  <rect x="40" y="362" width="160" height="56" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="120" y="383" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#712B13">I2S 功放</text>
  <text x="120" y="401" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#993C1D">MAX98357 / DAC</text>
  <rect x="260" y="362" width="160" height="56" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="340" y="383" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#712B13">TFT 屏幕</text>
  <text x="340" y="401" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#993C1D">ST7789 / ILI9341</text>
  <rect x="480" y="362" width="160" height="56" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="560" y="383" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#712B13">舵机 / 马达</text>
  <text x="560" y="401" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#993C1D">LEDC PWM × N</text>
  <!-- 同步事件组 -->
  <rect x="150" y="450" width="380" height="56" rx="10" fill="none" stroke="#888780" stroke-width="0.8" stroke-dasharray="5 3"/>
  <text x="340" y="471" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#444441">EventGroup 同步屏障</text>
  <text x="340" y="490" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#5F5E5A">三路 Task 就绪后同时释放 · 帧级同步</text>
  <!-- Task到同步屏障虚线 -->
  <line x1="120" y1="418" x2="200" y2="450" stroke="#888780" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#d1)"/>
  <line x1="340" y1="418" x2="340" y2="450" stroke="#888780" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#d1)"/>
  <line x1="560" y1="418" x2="480" y2="450" stroke="#888780" stroke-width="0.6" stroke-dasharray="3 3" marker-end="url(#d1)"/>
  <!-- 状态回报 -->
  <line x1="340" y1="506" x2="340" y2="550" stroke="#888780" stroke-width="1" marker-end="url(#d1)"/>
  <rect x="220" y="552" width="240" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="340" y="574" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="500" fill="#2C2C2A">执行完毕 · 状态回报</text>
</svg>

### 并行执行架构

ESP32 使用 FreeRTOS 多任务实现三路并行：

```
JSON 包接收
    ↓
调度器 Task（Core 1）
JSON 解析 + 三路消息队列分发
    ├─→ audio_queue  →  语音 Task（Core 0, 优先级 HIGH）
    ├─→ face_queue   →  表情 Task（Core 1, 优先级 NORMAL）
    └─→ motion_queue →  动作 Task（Core 1, 优先级 NORMAL）
              ↓
    EventGroup 同步屏障（三路就绪后同时释放）
              ↓
    并行执行：I2S 播音 + TFT 换图 + PWM 舵机
```

### 核心代码框架

```c
// 指令包结构体
typedef struct {
    char text[256];
    char emotion[16];
    char action[32];
    char voice_style[16];
    uint32_t duration_ms;
} AvatarCommand_t;

// 同步屏障（三路全部就绪才同时开始）
EventGroupHandle_t sync_event;
#define AUDIO_READY_BIT   (1 << 0)
#define FACE_READY_BIT    (1 << 1)
#define MOTION_READY_BIT  (1 << 2)
#define ALL_READY_BITS    (AUDIO_READY_BIT | FACE_READY_BIT | MOTION_READY_BIT)

// 语音 Task（Core 0，优先级最高）
void audio_task(void *pvParam) {
    AvatarCommand_t cmd;
    while (1) {
        xQueueReceive(audio_queue, &cmd, portMAX_DELAY);
        audio_prepare(cmd.voice_style);                         // 预缓冲
        xEventGroupSetBits(sync_event, AUDIO_READY_BIT);       // 标记就绪
        xEventGroupWaitBits(sync_event, ALL_READY_BITS,        // 等全部就绪
                            pdTRUE, pdTRUE, pdMS_TO_TICKS(200));
        i2s_play_audio(cmd.text, cmd.voice_style);             // 同步开始
    }
}

// 启动时绑定核心
xTaskCreatePinnedToCore(audio_task,      "audio",  4096, NULL, 10, NULL, 0);
xTaskCreatePinnedToCore(face_task,       "face",   4096, NULL,  5, NULL, 1);
xTaskCreatePinnedToCore(motion_task,     "motion", 4096, NULL,  5, NULL, 1);
xTaskCreatePinnedToCore(dispatcher_task, "disp",   8192, NULL,  8, NULL, 1);
```

### 硬件驱动方案

| 功能 | 推荐芯片/模块 | 接口 | 备注 |
|------|-------------|------|------|
| 语音播放 | MAX98357A | I2S | DMA 传输，不占 CPU |
| 表情显示 | ST7789 / ILI9341 | SPI | 240×240，表情图存 PSRAM |
| 动作控制 | 舵机 × N | LEDC PWM | 帧动画序列播放 |
| 录音 | INMP441 | I2S | 麦克风模块 |
| 存储 | SPIFFS / SD | SPI | 存表情图、动作帧数据 |

### 关键技术细节

- 语音 Task 优先级最高（10），I2S DMA buffer 不能断，否则有噪音
- 表情图（240×240 RGB565 ≈ 112KB/张）预加载到 PSRAM，切换在单帧内完成
- `EventGroupWaitBits` 是三路同步的关键——确保语音第一帧、表情切换、动作起始帧同时触发
- 等待超时设 200ms，超时也继续执行，避免某路故障导致全部卡死

---

## 八、延迟优化策略

端到端延迟估算：语音录制 → STT → LLM → TTS → 设备执行，约 2~5 秒。

### 优化手段

1. **流式 TTS**：LLM 开始输出时就并行生成语音，不等完整文本
2. **预加载表情资源**：常用表情常驻内存，切换零加载时间
3. **过渡动画**：等待期间播放"思考中"表情动画，避免设备呆滞
4. **本地 VAD**：设备端语音活动检测，减少无效上传
5. **指令预测**：根据上下文预测下一个可能动作，提前准备资源

---

## 九、进阶功能规划

### 情绪驱动 UI
- 开心 → 屏幕亮度提升，动画节奏加快
- 难过 → 冷色调，动画减缓
- 生气 → 红色边框，动作幅度加大

### 多角色切换
- 同一设备支持多套人格（YAML 配置切换）
- 每套人格有独立的记忆空间和情绪基线

### 记忆可视化
- 设备长按可展示"我记得你说过……"的历史摘要

### 关系进化
- 角色对用户的熟悉度影响称呼、语气、话题深度
- 互动次数、情绪共鸣度影响"亲密度"参数

---

## 十、已识别的关键难点

| 难点 | 描述 | 应对策略 |
|------|------|---------|
| LLM 输出稳定性 | 偶尔不按 JSON 格式输出 | Schema 校验 + 自动重试 + 降级处理 |
| 端到端延迟 | 2~5 秒用户感知明显 | 流式处理 + 过渡动画掩盖 |
| 情绪自然性 | 机械切换让人出戏 | Valence-Arousal 连续空间 + 惯性衰减 |
| 记忆一致性 | 跨会话记忆冲突 | 归纳摘要 + 版本控制 |
| 资源限制 | ESP32 RAM/Flash 有限 | PSRAM 扩展 + SPIFFS 分区管理 |

---

## 十一、推荐实施顺序

```
阶段 1：最小闭环
  → 定好 JSON 协议（所有字段）
  → 写 Prompt 模板，验证 LLM 稳定输出 JSON
  → ESP32 接收 JSON，屏幕显示对应表情
  （不带语音，不带动作，先跑通链路）

阶段 2：加入语音
  → 接入 TTS，I2S 播放音频
  → 三路同步执行（EventGroup）

阶段 3：加入动作
  → 舵机 PWM 驱动，帧动画序列

阶段 4：记忆系统
  → 工作记忆（Redis）
  → 情景记忆（向量库）
  → 对话后归纳写入

阶段 5：情绪状态机
  → Valence-Arousal 坐标系
  → 情绪惯性与自然衰减
  → 情绪影响输出风格

阶段 6：人格进化
  → 用户关系建模
  → 多角色切换
  → 长期记忆可视化
```

---

*文档版本：v1.1 · 含架构图三张（SVG内嵌）*
