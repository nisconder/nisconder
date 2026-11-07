# Nisconder

构建本地优先的开发者工具，关注 npm 供应链安全、开发环境诊断与浏览器工具。

[个人网站](https://nisconder.pages.dev/) · [技术文章](https://nisconder.pages.dev/articles/) · [项目目录](https://nisconder.pages.dev/software/)

## 从一个具体问题开始

| 你遇到的问题 | 我的项目 |
| --- | --- |
| 安装 npm 包前，想知道有哪些供应链风险 | [npm-safe](https://github.com/nisconder/npm-safe) — 本地静态检查、归档深扫、CLI / CI / 桌面与 Agent 接口 |
| localhost 在 Windows 能访问，WSL 或容器里却不行 | [portdoc](https://github.com/nisconder/portdoc) — 对比 IPv4 / IPv6 / localhost，定位监听项目与 Docker 映射 |
| 看不出两次 npm 发布究竟改了哪些文件 | [Pack Receipt](https://github.com/nisconder/pack-receipt) — 在浏览器本地打开并比较 npm 归档 |
| 复制的文本看起来一样，匹配和代码却总出错 | [Paste X-Ray](https://github.com/nisconder/paste-xray) — 检查零宽字符、双向控制符、同形字符与隐藏 HTML |
| 想跟着指令理解标志位、内存和调用栈 | [8086 Step Lab](https://github.com/nisconder/8086-step-lab) — 可单步、回退的 16 位教学模型 · [在线实验](https://nisconder.github.io/8086-step-lab/) |

[![8086 实验室：单步观察寄存器、标志位与内存](https://raw.githubusercontent.com/nisconder/8086-step-lab/main/preview.jpg)](https://nisconder.github.io/8086-step-lab/)

## 当前关注

- 让安全检查给出可追溯的文件证据，并明确未覆盖的情况。
- 让开发环境诊断保留来源与不完整状态，帮助复现问题。
- 把 [ICS / 8086 复习笔记](https://nisconder.pages.dev/series/ics-8086/) 转化为可以动手观察的实验。

主要使用 TypeScript / JavaScript，也用 Python 和 Java 处理工具与实验。项目中的使用示例、验证边界和已知限制都保留在各自仓库里。
