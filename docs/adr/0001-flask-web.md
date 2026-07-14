# ADR 0001 — Python Flask + Web 前端

**日期**: 2026-07-14

**状态**: Accepted

## 背景

AA 算账工具需要在手机上方便使用，同时用户希望用 Python 学习实践。

## 决策

用 Python (Flask) 写后端 + 轻量 HTML 前端：

- 后端 Flask：聊天记录解析、净额清算算法
- 前端单页 HTML + Vanilla JS：移动优先，粘贴聊天记录 → 展示结果
- 部署到免费 Python 托管平台（Render 等）
- 手机上浏览器访问即可使用

## 后果

- ✅ Python 核心逻辑，适合学习和维护
- ✅ 朋友手机浏览器打开即用，无需安装
- ✅ 一套代码，统一逻辑
- ⚠ 需要部署到有 Python 运行时的平台（Render/Railway/Fly.io）
- ⚠ 无法与微信原生集成，需手动粘贴聊天记录
