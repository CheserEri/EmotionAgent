# 单 LLM 命令行对话测试

这是第一阶段测试：接入 OpenAI 格式 API，在本机命令行里完成多轮文本对话，并让第二次模型调用输出表情 JSON。

## 一键运行

项目已经提供本机 MiMo 启动脚本：

```powershell
cd E:\Code\Projects\Emotion-Agent
python run_mimo.py
```

## 运行方式

PowerShell:

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"

python -m cli_avatar.main
```

如果使用 OpenAI-compatible 服务，只需要替换：

```powershell
$env:OPENAI_BASE_URL="你的兼容接口地址，例如 https://example.com/v1"
$env:OPENAI_MODEL="你的模型名"
```

## 小米 MiMo 接口示例

MiMo 的调用格式使用 `api-key` 请求头，并且 token 参数名是 `max_completion_tokens`。

PowerShell:

```powershell
$env:MIMO_API_KEY="你的 MiMo API Key"
$env:OPENAI_BASE_URL="https://api.xiaomimimo.com/v1"
$env:OPENAI_MODEL="mimo-v2.5-pro"
$env:OPENAI_API_KEY_HEADER="api-key"
$env:OPENAI_TOKEN_PARAM="max_completion_tokens"
$env:OPENAI_TEMPERATURE="1.0"
$env:OPENAI_MAX_TOKENS="1024"

python -m cli_avatar.main
```

## 命令

```text
/exit   退出
/clear  清空上下文
/history 查看最近对话和表情 JSON
/memory  查看摘要和长期记忆
/forget  清空摘要和长期记忆
/help    查看命令
```

## 当前数据流

```text
命令行输入
  -> 检索相关长期记忆 + 最近上下文
  -> LLM A: OpenAI 格式 /chat/completions 生成文本回复
  -> LLM B: 根据用户输入、A 的回复、最近上下文生成表情 JSON
  -> JSON 校验
  -> 更新摘要和长期记忆
  -> 命令行输出文本回复和表情 JSON
```

当前已经拆出 LLM A 和 LLM B：

```text
用户输入
  -> LLM A 生成回复
  -> LLM B 根据用户输入和 A 的回复生成表情 JSON
  -> JSON Schema 校验
  -> 命令行展示回复和表情 JSON
```
