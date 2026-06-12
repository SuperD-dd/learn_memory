---
name: Eclipse Zenoh
url: https://github.com/eclipse-zenoh/zenoh
language: Rust
category: Infra
tags: [pub-sub, robotics, iot, edge, ros2, middleware, networking]
stars: 2.9k
status: learned
rating: 5
date: 2026-06-13
---

# Eclipse Zenoh

> 零开销的统一数据中间件：把 发布/订阅、存储/查询、计算 三种语义合一，面向边缘、IoT 与机器人的低时延分布式通信协议。

## 核心功能 / 亮点
- **三合一语义**：pub/sub（数据在动）+ geo-distributed storage/query（数据静止）+ compute，用一套协议统一
- **零开销 / 低时延**：极小的线路开销，适合带宽受限、实时性要求高的场景
- **多传输 + 共享内存**：支持 TCP/UDP/串口等多种传输，本机走 shared memory 提升吞吐
- **路由器 + 插件**：独立 `zenohd` 路由器，插件式架构（存储、REST、MQTT 桥接等）
- **AdvancedPublisher/Subscriber**：可配置的可靠性与历史回放等高级投递保证
- **跨语言**：Rust 核心 + C / C++ / Python / Kotlin / Java / TypeScript 绑定；`zenoh-pico` 是纯 C 实现，跑在资源受限的 MCU/嵌入式上

## 技术栈
- Rust（核心）；多语言绑定；EPL 2.0 / Apache 2.0 双协议

## 适用场景
- **机器人通信中间件**：与 ROS 2 兼容（`rmw_zenoh`），可替代 DDS，跨网段/跨广域更友好
- IoT / 边缘：海量设备低开销组网、边到云数据汇聚
- 分布式实时数据：把订阅、查询历史数据、远程计算统一编程模型

## 关键启发 / 可借鉴点
- **「数据在动 / 数据静止 / 计算」统一抽象**很有借鉴价值——一套 API 同时覆盖实时流、历史查询与远程调用
- 对**我们的机器人项目直接相关**：若用 ROS 2，`rmw_zenoh` 在多机/弱网/跨子网场景常优于默认 DDS，值得评估
- `zenoh-pico`（纯 C，无堆/可静态分配）展示了「同一协议下沉到 MCU」的分层设计思路

## 相关项目
- [[zenoh-pico]]
