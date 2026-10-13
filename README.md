# HarnessSecurity-Benchmark

English | [简体中文](README.zh-CN.md)

**HarnessSecurity-Bench** evaluates whether security mechanisms in coding agent harnesses prevent prohibited actions while allowing legitimate development tasks to succeed.

[Paper (arXiv:2610.07639)](https://arxiv.org/abs/2610.07639) · [Project website](https://tsingpig.github.io/HarnessSecurity-Benchmark/)

This replication package contains **23 tasks across nine security mechanisms**: automatic approval, command allowlists, command denylists, filesystem boundaries, network isolation, read-only mode, prompt injection filtering, MCP permissions, and project trust. The runners support the six evaluated harnesses: Codex, Claude Code, GitHub Copilot CLI, Gemini CLI, gptme, and Qwen Code.

The [`tasks/`](tasks/) directory contains the task specifications, container environments, reference solutions, and independent verifiers. The [`scripts/`](scripts/) directory contains one runner per mechanism, its required helpers, and shared execution code. Security oracles assess prohibited effects; utility verifiers assess the required task behavior.

See [QUICKSTART.md](QUICKSTART.md) for prerequisites, model credentials, validation, execution, and result files.

The PR tasks `mvcc-lsm-compaction` and `embedding-drift-monitor` are derived from [Terminal-Bench](https://github.com/harbor-framework/terminal-bench-1), with the task adaptations recorded in `tasks/pr-bench/manifest.json`. Their upstream Apache 2.0 license is provided in [UPSTREAM_LICENSE](UPSTREAM_LICENSE).

## Citation

If you use HarnessSecurity-Bench in your research, please cite:

Zhengyang Zhu, Liming Huang, Runmin Ji, Mingxi Ye, Zihan Zhou, Hanyang Guo, Jingwen Wu, Yuhan Ye, Yuming Feng, Hong-Ning Dai, and Zibin Zheng. **HarnessSecurity-Bench: Do Security Mechanisms Really Protect Coding Agent Harnesses?** arXiv:2610.07639, 2026. [Paper](https://arxiv.org/abs/2610.07639).

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
