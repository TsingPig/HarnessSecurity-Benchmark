# HarnessSecurity-Benchmark

[English](README.md) | 简体中文

**HarnessSecurity-Bench** 用于评估编程智能体 harness 的安全机制能否阻止违规行为，同时支持正常开发任务的完成。

[论文（arXiv:2610.07639）](https://arxiv.org/abs/2610.07639) · [项目网站](https://tsingpig.github.io/HarnessSecurity-Benchmark/)

本复现包包含 **9 类安全机制、23 个任务**：自动批准、命令白名单、命令黑名单、文件系统边界、网络隔离、只读模式、提示注入过滤、MCP 权限和项目信任。运行脚本支持研究评估的六种 harness：Codex、Claude Code、GitHub Copilot CLI、Gemini CLI、gptme 和 Qwen Code。

[`tasks/`](tasks/) 目录包含任务定义、容器环境、参考解法和独立验证器。[`scripts/`](scripts/) 目录包含各机制的运行入口、对应辅助脚本和共享执行代码。安全 oracle 检查违规行为产生的实际效果，任务效用验证器检查所要求的任务行为。

环境要求、模型凭证、校验、实验运行及结果文件说明见 [QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)。

PR 任务 `mvcc-lsm-compaction` 和 `embedding-drift-monitor` 改编自 [Terminal-Bench](https://github.com/harbor-framework/terminal-bench-1)，改编信息记录于 `tasks/pr-bench/manifest.json`。上游 Apache 2.0 许可证见 [UPSTREAM_LICENSE](UPSTREAM_LICENSE)。

## 引用

如果在研究中使用 HarnessSecurity-Bench，请引用：

Zhengyang Zhu, Liming Huang, Runmin Ji, Mingxi Ye, Zihan Zhou, Hanyang Guo, Jingwen Wu, Yuhan Ye, Yuming Feng, Hong-Ning Dai, and Zibin Zheng. **HarnessSecurity-Bench: Do Security Mechanisms Really Protect Coding Agent Harnesses?** arXiv:2610.07639, 2026. [论文](https://arxiv.org/abs/2610.07639).

```bibtex
@misc{zhu2026harnesssecuritybench,
  title         = {{HarnessSecurity-Bench}: Do Security Mechanisms Really Protect Coding Agent Harnesses?},
  author        = {Zhengyang Zhu and Liming Huang and Runmin Ji and Mingxi Ye and Zihan Zhou and Hanyang Guo and Jingwen Wu and Yuhan Ye and Yuming Feng and Hong-Ning Dai and Zibin Zheng},
  year          = {2026},
  eprint        = {2610.07639},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR},
  doi           = {10.48550/arXiv.2610.07639},
  url           = {https://arxiv.org/abs/2610.07639}
}
```
