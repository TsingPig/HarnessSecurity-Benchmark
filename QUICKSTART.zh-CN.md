# HarnessSecurity-Bench 快速开始

[English](QUICKSTART.md)

从仓库根目录运行命令。配置环境和凭证后，可直接使用“运行实验”中的命令；验证步骤可选。

## 准备 Python 和 Docker 环境

- Python 3.11+（已测试版本为 3.13），宿主机脚本使用标准库。
- Docker 使用 Linux 容器，原生沙箱需要用户命名空间支持。Gemini/Qwen 的 NI 实验还需要嵌套 Docker。
- 网络访问和模型 API 密钥。

使用 `python --version` 和 `docker info` 检查环境。

## 配置模型凭证

在启动运行脚本的 shell 中设置变量：

```powershell
$env:AGENT_API_KEY = '<your-api-key>'
$env:AGENT_BASE_URL = 'https://<your-provider>/v1'
$env:AGENT_MODEL = '<model-id>'
```

Bash 中使用 `export NAME='value'`。各 harness 的配置如下：

| Harness ID | 凭证和 API 协议 |
|---|---|
| `codex` | `AGENT_*`；Responses API。 |
| `copilot-agent`, `gptme`, `qwen` | `AGENT_*`；OpenAI 兼容提供方。 |
| `claude-code` | `ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`、`AGENT_MODEL`；可用 `ANTHROPIC_BASE_URL` 指定 Anthropic Messages 端点。 |
| `gemini-cli` | `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`、`GEMINI_CLI_MODEL`；可用 `GOOGLE_GEMINI_BASE_URL` 指定 Gemini API 端点。 |

AA 的 OFF 模式须将 `REVIEWER_MODEL` 设为不同的审核模型。外部审核模型使用 `REVIEWER_BASE_URL`/`REVIEWER_API_KEY`（默认使用 `AGENT_BASE_URL`/`AGENT_API_KEY`），端点须支持 Chat Completions。Codex 的两个模型共用执行模型的端点和凭证。

**可选：验证任务与预览计划**

以下命令检查任务包或执行计划，不构建镜像、不调用模型。

验证任务文件：

```text
python scripts/cal/cal_run_agent.py --validate
```

预览将运行的任务和模式：

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/runs/cal-codex --dry-run
```

## 运行实验

以下命令会构建 Docker 镜像并调用模型：

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/runs/cal-codex
```

该 CAL/Codex 试跑对每个任务及适用模式尝试三次，使用三个并行作业，每次试验的截止时间为八小时。

可将 `codex` 替换为上表中的 harness ID。其他机制的入口为 `scripts/<id>/<id>_run_agent.py`：

| ID | 机制 |
|---|---|
| `aa` | 自动批准 |
| `cal` | 命令白名单 |
| `cdl` | 命令黑名单 |
| `mcp` | MCP 权限 |
| `ni` | 网络隔离 |
| `pif` | 提示注入过滤 |
| `pr` | 文件系统边界 |
| `pt` | 项目信任 |
| `ro` | 只读模式 |

每种配置使用新的输出目录。用 `--tasks <task-id> ...` 选择任务，用 `--modes <mode> ...` 选择模式；完整选项见 `--help`。

Codex/Qwen 的 PIF 实验使用 `--modes native`。Gemini/Qwen 的 NI 实验需要 Docker 宿主机可访问的 HTTPS 模型端点。

## 续跑至十次尝试

试跑正常完成后，用五个并行作业继续同一实验：

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 10 --jobs 5 --agent-timeout 28800 --out .runtime/runs/cal-codex --resume
```

十次是总目标次数。沿用输出目录和实验配置；Codex/Qwen 的 PIF 实验继续添加 `--modes native`。

## 查看结果文件

打开输出目录中的文件：

- `results.md`：结果表格。
- `report.json`：各次试验结果、指标及 token 用量。
