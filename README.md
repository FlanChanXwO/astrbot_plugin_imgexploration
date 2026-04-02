# 🔍 图片搜索插件（astrbot_plugin_imgexploration）

<div align="center">

**一个支持多引擎、LLM 工具调用的图片溯源搜索插件**

[![License: AGPL](https://img.shields.io/badge/License-AGPL-blue.svg)](https://opensource.org/licenses/agpl-3.0)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A54.10.4-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

</div>

本插件完全开源免费，欢迎 Issue 和 PR。

---

## ✨ 功能特性

- 🔍 **多引擎支持** - SauceNAO、Google Lens、Ascii2d 三大搜索引擎
- 🤖 **LLM 工具调用** - 支持通过大模型自动搜图，无需手动命令
- 📷 **图片上下文管理** - 自动记录会话中的图片，支持会话级/全局隔离
- 💬 **多平台适配** - aiocqhttp 支持合并转发，其他平台支持消息链
- 🌐 **网络配置** - 支持自定义 User-Agent、代理设置
- 🛡️ **Cloudflare 绕过** - 使用 curl_cffi 模拟浏览器 TLS 指纹

---

## 📦 安装

### 方式一：通过 AstrBot 插件市场安装（推荐）

在 AstrBot 管理面板中搜索 `astrbot_plugin_imgexploration` 并安装。

### 方式二：手动安装

1. 克隆本仓库到 AstrBot 的插件目录：
   ```bash
   cd AstrBot/data/plugins
   git clone https://github.com/your-repo/astrbot_plugin_imgexploration.git
   ```
2. 安装依赖：
   ```bash
   pip install curl_cffi
   ```
3. 重启 AstrBot 或重载插件

---

## 🛠️ 配置项

### API 密钥配置

| 配置项 | 类型 | 说明 | 必填 |
|--------|------|------|------|
| `saucenao_api_key` | 字符串 | SauceNAO API Key | 是（使用该引擎） |
| `serpapi_keys` | 列表 | SerpAPI Keys（Google Lens） | 是（使用该引擎） |
| `ascii2d_session_id` | 字符串 | Ascii2d Session ID | 是（使用该引擎） |
| `ascii2d_cf_clearance` | 字符串 | Ascii2d cf_clearance（绕过 CF） | 否 |

### 搜图策略配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `enable_saucenao` | 布尔值 | 启用 SauceNAO | `true` |
| `saucenao_similarity_threshold` | 整数 | SauceNAO 相似度阈值 | `40` |
| `enable_google_lens` | 布尔值 | 启用 Google Lens | `true` |
| `enable_ascii2d` | 布尔值 | 启用 Ascii2d | `true` |

### AI 行为配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `allow_ai_search_image` | 布尔值 | 允许 AI 执行搜图 | `true` |
| `image_context_isolation` | 字符串 | 图片上下文隔离模式（`session`/`global`） | `session` |
| `max_images_per_session` | 整数 | 每会话最大图片数 | `20` |
| `image_context_ttl_seconds` | 整数 | 图片上下文保留时长（秒），0 表示不过期 | `0` |
| `max_image_context_sessions` | 整数 | 最大图片上下文会话数（LRU 回收） | `200` |
| `include_image_url_in_context` | 布尔值 | 在 AI 图片上下文中包含原始 URL | `true` |
| `llm_tool_silent_mode` | 布尔值 | LLM 工具静默模式，开启后不自动发送消息 | `false` |

### 显示配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `max_results` | 整数 | 每个引擎返回的最大结果数量 | `5` |

### 网络配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `proxy_url` | 字符串 | 代理服务器 URL | 空 |
| `user_agent` | 字符串 | User-Agent | Chrome 120 |

---

## 📝 使用方法

### 命令方式

回复一张图片发送以下命令：

```
搜图
搜图 saucenao
搜图 google
搜图 ascii2d
搜图 saucenao,google
搜图 sauce,2d
```

**命令别名：**
- `sauce` = `saucenao`
- `2d` = `ascii2d`

### LLM 工具调用

确保使用支持 Function Calling 的模型（如 GPT-4、Claude、DeepSeek 等），然后：

1. 发送一张图片
2. 说"找一下这张图的来源"或"搜图"
3. AI 会自动调用搜图工具

**注意：** 需要使用支持 `tool_use` 的模型。如果日志显示 `does not support tool_use`，请切换模型。

---

## 🔧 获取 API 密钥

### SauceNAO

1. 访问 https://saucenao.com/user.php?page=search-api
2. 注册/登录账号
3. 获取 API Key

### SerpAPI（Google Lens）

1. 访问 https://serpapi.com
2. 注册账号（免费版每月 100 次）
3. 获取 API Key

### Ascii2d

1. 用 **Chrome 浏览器**访问 https://ascii2d.net
2. 通过 Cloudflare 验证
3. 打开开发者工具 (F12) → Application → Cookies
4. 复制 `_session_id` 和 `cf_clearance` 的值

**重要：** Ascii2d 需要使用代理访问，确保获取 Cookie 和服务器请求使用相同的代理 IP。

---

## 📖 引擎说明

| 引擎 | 特点 | 适用场景 |
|------|------|----------|
| **SauceNAO** | 动漫图片专精，支持 Pixiv、Danbooru 等数据库 | 动漫插画、二次元图片 |
| **Google Lens** | 通用图片搜索，覆盖面广 | 通用图片、商品、风景 |
| **Ascii2d** | 日本搜图网站，支持色合/特征搜索 | 动漫图片、Pixiv 插画 |

---

## ⚠️ 常见问题

### 1. Ascii2d 返回 403 错误

原因：被 Cloudflare 拦截

解决：
- 使用 Chrome 浏览器获取 Cookie
- 配置代理，确保 IP 一致
- 正确填写 `cf_clearance` 和 `session_id`

### 2. LLM 不调用工具

原因：模型不支持 Function Calling

解决：切换到支持 `tool_use` 的模型

### 3. 图片没有被识别

原因：图片上下文为空

解决：
- 确保图片发送后有时间被捕获
- 检查日志是否显示"捕获图片到上下文"

---

## 📄 开源协议

本项目基于 [AGPL-3.0](LICENSE) 协议开源。

---

## 🙏 致谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - 强大的 AI 助手框架
- [SauceNAO](https://saucenao.com) - 动漫图片搜索引擎
- [SerpAPI](https://serpapi.com) - Google Lens API 服务
- [Ascii2d](https://ascii2d.net) - 日本图片搜索网站