# EmotionAgent

本项目是一个本机 AI 角色原型：命令行输入文本，LLM A 负责自然语言回复，LLM B 负责输出表情行为 JSON，并带有本地摘要和长期记忆系统。

## 当前能力

- OpenAI-compatible `/chat/completions` API 调用
- MiMo 接口适配
- LLM A 对话回复
- LLM B 表情 JSON 输出
- JSON 校验与默认降级
- 本地滚动摘要和长期记忆
- Unity EXE 封装方案文档

## 快速运行

复制配置模板：

```powershell
Copy-Item local_mimo_config.example.py local_mimo_config.py
```

编辑 `local_mimo_config.py`，填入自己的 API Key，然后运行：

```powershell
python run_mimo.py
```

也可以不创建本地配置文件，直接使用环境变量：

```powershell
$env:MIMO_API_KEY="你的 MiMo API Key"
$env:OPENAI_BASE_URL="https://api.xiaomimimo.com/v1"
$env:OPENAI_MODEL="mimo-v2.5-pro"
$env:OPENAI_API_KEY_HEADER="api-key"
$env:OPENAI_TOKEN_PARAM="max_completion_tokens"
$env:OPENAI_TEMPERATURE="1.0"
$env:OPENAI_MAX_TOKENS="1024"

python run_mimo.py
```

## 命令

```text
/exit    退出
/clear   清空当前短上下文，长期记忆保留
/memory  查看摘要和长期记忆
/forget  清空摘要和长期记忆
/history 查看最近对话和表情 JSON
/debug   切换调试模式
/help    查看命令
```

## 重要说明

`local_mimo_config.py`、`memory_store.json`、模型 zip 等本地文件不会提交到 GitHub。

