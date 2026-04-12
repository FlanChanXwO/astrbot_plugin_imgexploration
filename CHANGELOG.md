# Changelog

## [1.0.3] - 2026-04-03

### Changed

- 增加图片转发降级，避免因为其中一个策略导致整个搜索结果发送失败

## [1.0.0] - 2026-04-03

### Added

- **多引擎支持**
  - SauceNAO 搜索引擎（动漫图片专精）
  - Google Lens 搜索引擎（通过 SerpAPI）
  - Ascii2d 搜索引擎（日本搜图网站）

- **命令搜图**
  - 支持 `搜图` 命令触发搜索
  - 支持指定引擎：`搜图 saucenao`、`搜图 google`、`搜图 ascii2d`
  - 支持引擎别名：`sauce`、`2d`

- **LLM 工具调用**
  - `get_session_images` - 查询会话中的图片列表
  - `search_image` - 执行图片搜索
  - 搜索结果自动发送给用户，AI 只需总结

- **图片上下文管理器**
  - 自动捕获会话中的图片
  - 支持会话级隔离（每个群/私聊独立）
  - 支持全局隔离（所有会话共享）
  - 可配置每会话最大图片数

- **网络配置**
  - 支持自定义 User-Agent
  - 支持代理设置
  - 使用 curl_cffi 绕过 Cloudflare（模拟 Chrome 120 TLS 指纹）

- **多平台适配**
  - aiocqhttp 平台：合并转发消息
  - 其他平台：消息链发送

### Changed

- LLM 工具参数从 `image_url` 改为 `image_index`，更易使用
- AI 必须展示搜索结果的 URL 和来源名称
- 使用 `curl_cffi` 替代 `aiohttp` 请求 Ascii2d（绕过 Cloudflare）
- 图片上下文使用 `OrderedDict` 存储，支持 LRU 淘汰
- 全局共享 `aiohttp.ClientSession` 提升性能


