---
name: kpexec
url: https://github.com/ssup2/kpexec
language: Unknown
category: DevOps
tags: [node, k8s, ai, cli]
stars: ""
status: archived
rating: 0
date: 2024-05-09
via: eryajf-weekly
source: #158 (2024-05-09)
---

# kpexec

> kpexec 是一个 K8s cli，它可以在没有 SSH 的情况下以高权限(root)在容器中运行命令。它在与目标容器相同的节点上运行高特权容器，并加入目标容器的命名空间（IPC、UTS、PID、net、mount）。这对于经常需要以高权限执行命令的调试很有用。此外， kpexec 有一个工具模式，它将有用的调试工具添加到被调试的容器中。当目标容器中缺少必要的调试工具时，工具模式非常有用。它的实现原理如下图： 上图展示了 kpexec 的运行流程。首先，kpexec 从 K 8 s API Server 获取目标 pod 的信息，并找出目标 pod 存在于哪个 Node。然后，kpexec 在目标 pod 所在的节点创建一个 cnsenter pod 并执行 cnsetner。 cnsenter 通过 CRI（Container Runtime Interface）从容器运行时获取目标容器的 pid 和根目录信息。然后 cnsetner 根据获取到的信息在目标容器中执行命令。

## 来源
- 学习周刊 [#158](https://wiki.eryajf.net/pages/89722e/)（2024-05-09）
- GitHub：https://github.com/ssup2/kpexec
