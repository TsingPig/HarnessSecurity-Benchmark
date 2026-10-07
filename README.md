# HarnessSecurity-Benchmark

Task packages for **HarnessSecurity-Bench**, a benchmark for security mechanisms in coding agent harnesses.

[Paper (arXiv:2610.07639)](https://arxiv.org/abs/2610.07639) · [Project website](https://tsingpig.github.io/HarnessSecurity-Benchmark/)

The [`tasks/`](tasks/) directory contains ten mechanism suites: automatic approval, audit logging, command allowlists, command denylists, filesystem boundaries, network isolation, read-only mode, prompt injection filtering, MCP permissions, and project trust.

Each suite provides a manifest and task packages with instructions, container environments, reference solutions, and utility checks. See the individual task files for setup and verification details. The full evaluation runner is maintained separately.

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
