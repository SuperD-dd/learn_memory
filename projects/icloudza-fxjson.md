---
name: fxjson
url: https://github.com/icloudza/fxjson
language: Unknown
category: Security
tags: [go, node, ai, 安全]
stars: ""
status: archived
rating: 0
date: 2025-10-31
via: eryajf-weekly
source: #235 (2025-10-31)
---

# fxjson

> 一个专注性能的Go JSON解析库，提供高效的JSON遍历和访问能力。相比标准库有显著的性能提升，同时保持内存安全和易用性。 示例：go get github.com/icloudza/fxjson package main import ( "fmt" "github.com/icloudza/fxjson" ) func main() { jsonData := []byte(`{"name": "Alice", "age": 30}`) node := fxjson.FromBytes(jsonData) name, _ := node.Get("name").String() age, _ := node.Get("age").Int() fmt.Printf("Name: %s, Age: %d\n", name, age) } 123456789101112131415161718

## 来源
- 学习周刊 [#235](https://wiki.eryajf.net/pages/14c483/)（2025-10-31）
- GitHub：https://github.com/icloudza/fxjson
