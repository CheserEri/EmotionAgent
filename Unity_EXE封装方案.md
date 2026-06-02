# Unity EXE 封装方案

> 当前目标：把 Emotion-Agent 从命令行原型升级为一个可运行的 Windows `.exe` 软件。
> Unity 负责角色模型、房间、动画和界面；LLM 系统负责对话、记忆和表情 JSON。

---

## 1. 总体目标

最终软件形态：

```text
Windows EXE
  -> 打开后显示一个房间
  -> 房间中有一个角色模型
  -> 用户输入文字
  -> 角色回复
  -> 角色根据 JSON 做表情、动作、视线或姿态变化
```

当前阶段不追求完整语音、不追求高精度动画、不追求复杂 AI 行为树。

先实现：

```text
用户打字
  -> LLM A 回复
  -> LLM B 输出行为 JSON
  -> Unity 显示回复气泡
  -> Unity 根据 JSON 切换表情 / 播放动作
```

---

## 2. 推荐架构

为了方便快速实现，建议使用 **Unity 前端 + 本地 Python Agent 服务**。

```text
┌────────────────────────┐
│        Unity EXE        │
│  房间 / 模型 / UI / 动画 │
└───────────┬────────────┘
            │ HTTP localhost
            ▼
┌────────────────────────┐
│   Python Agent Server   │
│ LLM A / LLM B / 记忆系统 │
└───────────┬────────────┘
            │ OpenAI-compatible API
            ▼
┌────────────────────────┐
│       MiMo / LLM API    │
└────────────────────────┘
```

### 为什么推荐这个架构

- 当前 Python 代码已经实现 A/B 双 LLM、JSON 校验和记忆系统
- Unity 只负责视觉表现，逻辑简单
- Python Agent 可以独立调试
- Unity 不需要直接处理复杂 Prompt、记忆、JSON 修复
- 后续可以把 Python 服务一起打包进 exe 目录

---

## 3. 不推荐一开始做的方案

### 不建议一开始让 Unity 直接调用大模型

虽然 Unity C# 可以直接请求 API，但会遇到：

```text
1. Prompt、记忆、JSON 修复逻辑都要重写成 C#
2. API Key 更容易暴露在客户端
3. 调试体验比 Python 差
4. 后续加记忆、日志、工具调用更麻烦
```

后期产品化时可以重构，但 MVP 阶段不建议。

### 不建议一开始做复杂动作系统

第一版只做状态映射：

```text
expression -> 表情
action     -> 动画片段
emotion    -> 氛围参数
voice_style -> 暂时只显示，不播放语音
```

---

## 4. Unity 与 Python 通信协议

Unity 向 Python 发送：

```http
POST http://127.0.0.1:8765/chat
Content-Type: application/json
```

请求：

```json
{
  "message": "今天有点累"
}
```

Python 返回：

```json
{
  "text": "辛苦啦，今天一定不轻松。先慢一点，我陪你安静待会儿。",
  "emotion": "concerned",
  "expression": "soft_smile",
  "action": "nod",
  "voice_style": "soft",
  "duration": 1200
}
```

Unity 只需要解析这个 JSON，然后执行表现层逻辑。

---

## 5. 行为 JSON 字段

第一版保持简单：

```json
{
  "text": "角色说的话",
  "emotion": "calm",
  "expression": "soft_smile",
  "action": "idle",
  "voice_style": "soft",
  "duration": 1200
}
```

### emotion

```text
happy
sad
angry
surprised
calm
thinking
concerned
```

### expression

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

### action

```text
idle
nod
shake_head
wave_hand
tilt_head
look_down
```

---

## 6. Unity 端模块

建议 Unity 工程中先做这些脚本：

```text
Assets/
  Scripts/
    AgentApiClient.cs       # 调 Python /chat 接口
    ChatUIController.cs     # 输入框、发送按钮、回复气泡
    AvatarController.cs     # 接收 JSON，驱动角色表现
    ExpressionMapper.cs     # expression -> blendshape / morph
    ActionMapper.cs         # action -> animation trigger
    AgentResponse.cs        # JSON 数据结构
```

### AgentApiClient.cs

职责：

```text
1. 接收用户输入
2. POST 到 http://127.0.0.1:8765/chat
3. 解析返回 JSON
4. 把结果交给 ChatUIController 和 AvatarController
```

### AvatarController.cs

职责：

```text
1. 显示或更新角色表情
2. 播放动作动画
3. 根据 emotion 调整简单状态
4. 控制动作持续时间
```

第一版可以不用真实 blendshape，先用日志或 UI 标签确认状态：

```text
Expression: soft_smile
Action: nod
Emotion: concerned
```

然后再接模型表情。

---

## 7. 模型接入策略

当前 zip 是 PMX/MMD 模型。

Unity 对 PMX 支持不是原生的，建议路线：

```text
PMX 模型
  -> 使用转换工具转 FBX 或 VRM
  -> 导入 Unity
  -> 配置材质、骨骼、表情、动画
```

### Vibe Coding 友好的建议

第一版不要直接卡在 PMX 转换上。

建议先用 Unity 免费示例模型或临时 humanoid 模型跑通：

```text
1. Unity 场景里放一个临时角色
2. 跑通输入框 + API 调用 + JSON 返回
3. 用 Animator 播放 idle / nod / wave 等占位动画
4. 最后再替换成目标 PMX 转换后的模型
```

这样不会因为模型格式、材质、骨骼问题阻塞主系统。

---

## 8. Python 端改造

当前已有：

```text
LLM A 对话
LLM B 表情 JSON
记忆系统
命令行输入
```

需要新增：

```text
Python HTTP Server
  POST /chat
  输入: {"message": "..."}
  输出: 完整行为 JSON
```

建议新增文件：

```text
cli_avatar/server.py
```

保持命令行版本不删除：

```text
python run_mimo.py          # 命令行测试
python run_agent_server.py  # Unity 调用的本地服务
```

---

## 9. EXE 打包策略

第一阶段打包方式：

```text
Unity.exe
Python Agent Server
配置文件
```

运行方式：

```text
1. 用户双击启动器
2. 启动器先启动 Python Agent Server
3. 再启动 Unity EXE
4. Unity 通过 localhost 调用 Agent Server
```

### 后续可选优化

```text
方案 A：Unity 启动时自动拉起 Python server
方案 B：用 PyInstaller 把 Python server 打成 agent_server.exe
方案 C：做一个总启动器，一键启动两个进程
方案 D：后期把 Agent 逻辑迁移到远程服务器
```

MVP 最推荐：

```text
PyInstaller 打包 Python server
Unity Build Windows x86_64
写一个 start.bat 或小启动器同时启动
```

---

## 10. 分阶段实施

### 阶段 1：Python 本地服务

```text
新增 /chat HTTP 接口
复用现有 LLM A / LLM B / memory
返回完整行为 JSON
```

验收：

```text
curl http://127.0.0.1:8765/chat
能返回 text + expression JSON
```

### 阶段 2：Unity UI 原型

```text
创建 Unity 场景
添加输入框
添加发送按钮
添加回复文本框
调用 Python /chat
显示返回 JSON
```

验收：

```text
Unity 内输入文字
能看到角色回复和 JSON 状态
```

### 阶段 3：Unity 角色占位表现

```text
添加临时角色或 Capsule
根据 emotion 改变颜色
根据 action 播放简单动画或移动
根据 expression 显示表情文本
```

验收：

```text
happy -> 明亮状态
concerned -> 柔和状态
nod -> 播放点头动画或占位动作
```

### 阶段 4：接入真实模型

```text
PMX 转 FBX / VRM
导入 Unity
配置材质
配置 Animator
配置表情 BlendShape / Morph
把 JSON 映射到模型表现
```

验收：

```text
模型能显示
能 idle
能至少执行 smile / blink / nod / wave_hand
```

### 阶段 5：封装 EXE

```text
Python server -> PyInstaller
Unity -> Windows Build
启动器 -> 一键启动
```

验收：

```text
双击启动
出现房间和角色
可以输入对话
角色回复并做表情动作
```

---

## 11. Vibe Coding 任务拆分

适合逐条让 Vibe Coding 实现：

```text
任务 1：把现有 Python CLI 改造成可复用 AgentEngine 类
任务 2：新增 FastAPI 或标准库 HTTP server，提供 POST /chat
任务 3：写 curl 测试 /chat 接口
任务 4：创建 Unity 工程和基础房间场景
任务 5：Unity 添加输入框、发送按钮、回复文本
任务 6：Unity C# 调用 localhost /chat
任务 7：Unity 解析 AgentResponse JSON
任务 8：创建 AvatarController，把 expression/action 映射到占位表现
任务 9：PMX 模型转换为 Unity 可用格式
任务 10：替换占位角色为真实模型
任务 11：PyInstaller 打包 Python server
任务 12：Unity Build Windows EXE
任务 13：启动器一键启动 Agent + Unity
```

---

## 12. 当前建议的下一步

下一步先做：

```text
新增 Python Agent Server
```

也就是把现在命令行里的核心流程封装成：

```text
POST /chat
输入 message
返回完整行为 JSON
```

这一步完成后，Unity 端就可以很干净地接入。

