"""图片搜索插件工具函数.

包含 HTTP 请求、图片下载、图床上传等通用功能。
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
from typing import Any

import aiohttp

from astrbot.api import logger

from .constant import DEFAULT_USER_AGENT, HTTP_TIMEOUT_SECONDS, IMAGE_DOWNLOAD_TIMEOUT

# Telegraph 图床 URL
TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"

# Catbox 图床 URL (免费，无需 API key)
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"

# 全局共享的 aiohttp ClientSession
_aiohttp_session: aiohttp.ClientSession | None = None
_aiohttp_session_lock = asyncio.Lock()
# 全局代理设置
_proxy_url: str | None = None
# 全局 User-Agent 设置
_user_agent: str | None = None


def set_proxy_url(proxy_url: str | None) -> None:
    """设置全局代理 URL.

    Args:
        proxy_url: 代理 URL，如 http://127.0.0.1:7890。None 或空字符串表示不使用代理。
    """
    global _proxy_url
    if (
        proxy_url
        and proxy_url.strip()
        and proxy_url.startswith(("http://", "https://"))
    ):
        _proxy_url = proxy_url.strip()
        logger.info(f"[ImgExploration] 已设置代理: {_proxy_url}")
    else:
        _proxy_url = None
        logger.debug("[ImgExploration] 未设置有效代理，将直接连接")


def get_proxy_url() -> str | None:
    """获取当前代理 URL.

    Returns:
        代理 URL，未设置则返回 None
    """
    return _proxy_url


def set_user_agent(user_agent: str | None) -> None:
    """设置全局 User-Agent.

    Args:
        user_agent: User-Agent 字符串。None 或空字符串表示使用默认值。
    """
    global _user_agent
    if user_agent and user_agent.strip():
        _user_agent = user_agent.strip()
        logger.info(f"[ImgExploration] 已设置 User-Agent: {_user_agent[:50]}...")
    else:
        _user_agent = None
        logger.debug("[ImgExploration] 未设置自定义 User-Agent，将使用默认值")


def get_user_agent() -> str:
    """获取当前 User-Agent.

    Returns:
        User-Agent 字符串，未设置则返回默认值
    """
    if _user_agent:
        return _user_agent
    return DEFAULT_USER_AGENT


async def _get_aiohttp_session() -> aiohttp.ClientSession:
    """获取全局共享的 aiohttp ClientSession.

    Returns:
        全局共享的 ClientSession 实例
    """
    global _aiohttp_session
    # 双重检查锁，避免在高并发时重复创建 ClientSession
    if _aiohttp_session is not None and not _aiohttp_session.closed:
        return _aiohttp_session

    async with _aiohttp_session_lock:
        if _aiohttp_session is None or _aiohttp_session.closed:
            connector = None
            if _proxy_url:
                # 使用代理连接器
                connector = aiohttp.TCPConnector()
            _aiohttp_session = aiohttp.ClientSession(connector=connector)
        return _aiohttp_session


async def close_aiohttp_session() -> None:
    """关闭全局共享的 aiohttp ClientSession.

    在插件卸载时调用，避免资源泄漏和事件循环清理警告。
    """
    global _aiohttp_session
    if _aiohttp_session is not None and not _aiohttp_session.closed:
        await _aiohttp_session.close()
        logger.debug("[ImgExploration] aiohttp ClientSession 已关闭")
    _aiohttp_session = None


async def download_bytes(
    url: str,
    timeout: int = IMAGE_DOWNLOAD_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> bytes | None:
    """下载指定 URL 的内容并返回字节数据.

    Args:
        url: 要下载的 URL
        timeout: 请求超时时间 (秒)
        headers: 自定义请求头

    Returns:
        下载的字节数据，失败返回 None
    """
    if not url or not url.startswith(("http://", "https://")):
        return None

    default_headers = {"User-Agent": get_user_agent()}
    if headers:
        default_headers.update(headers)

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    proxy = get_proxy_url()

    try:
        session = await _get_aiohttp_session()
        async with session.get(
            url, timeout=client_timeout, headers=default_headers, proxy=proxy
        ) as resp:
            if resp.status == 200:
                return await resp.read()
    except Exception as e:
        logger.debug(f"[ImgExploration] 下载失败: {url}, 错误: {e}")

    return None


async def download_bytes_batch(
    urls: list[str],
    timeout: int = IMAGE_DOWNLOAD_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> list[bytes | None]:
    """批量下载多个 URL 的内容.

    Args:
        urls: URL 列表
        timeout: 每个请求的超时时间 (秒)
        headers: 自定义请求头

    Returns:
        字节数据列表，每个位置对应输入 URL 列表的位置
    """
    tasks = [download_bytes(url, timeout, headers) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def post_multipart(
    url: str,
    data: dict[str, Any],
    files: dict[str, tuple[str, bytes, str]] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
    headers: dict[str, str] | None = None,
) -> tuple[int, str | None]:
    """发送 multipart/form-data POST 请求.

    Args:
        url: 目标 URL
        data: 表单字段数据
        files: 文件数据，格式为 {字段名: (文件名, 字节内容, MIME类型)}
        timeout: 请求超时时间 (秒)
        headers: 自定义请求头

    Returns:
        (状态码, 响应内容)，失败返回 (0, None)
    """
    default_headers = {"User-Agent": get_user_agent()}
    if headers:
        default_headers.update(headers)

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    proxy = get_proxy_url()

    try:
        session = await _get_aiohttp_session()
        # 构建 multipart 数据
        multipart_data = aiohttp.MultipartWriter("form-data")

        for key, value in data.items():
            part = multipart_data.append(f"{value}")
            part.set_content_disposition("form-data", name=key)

        if files:
            for field_name, (filename, content, mime_type) in files.items():
                part = multipart_data.append(content)
                part.set_content_disposition(
                    "form-data", name=field_name, filename=filename
                )
                part.content_type = mime_type

        async with session.post(
            url,
            data=multipart_data,
            timeout=client_timeout,
            headers=default_headers,
            proxy=proxy,
        ) as resp:
            content = await resp.text() if resp.status == 200 else None
            return resp.status, content

    except Exception as e:
        logger.error(f"[ImgExploration] POST 请求失败: {url}, 错误: {e}")
        return 0, None


async def get_json(
    url: str,
    params: dict[str, str] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    """发送 GET 请求并返回 JSON 解析结果.

    Args:
        url: 目标 URL
        params: 查询参数
        timeout: 请求超时时间 (秒)
        headers: 自定义请求头

    Returns:
        (状态码, JSON字典)，失败返回 (0, None)
    """
    import json

    default_headers = {"User-Agent": get_user_agent()}
    if headers:
        default_headers.update(headers)

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    proxy = get_proxy_url()

    try:
        session = await _get_aiohttp_session()
        async with session.get(
            url,
            params=params,
            timeout=client_timeout,
            headers=default_headers,
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                return resp.status, json.loads(text)
            return resp.status, None

    except Exception as e:
        logger.error(f"[ImgExploration] GET 请求失败: {url}, 错误: {e}")
        return 0, None


async def get_html(
    url: str,
    params: dict[str, str] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
    headers: dict[str, str] | None = None,
) -> tuple[int, str | None]:
    """发送 GET 请求并返回 HTML 文本.

    Args:
        url: 目标 URL
        params: 查询参数
        timeout: 请求超时时间 (秒)
        headers: 自定义请求头

    Returns:
        (状态码, HTML文本)，失败返回 (0, None)
    """
    default_headers = {"User-Agent": get_user_agent()}
    if headers:
        default_headers.update(headers)

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    proxy = get_proxy_url()

    try:
        session = await _get_aiohttp_session()
        async with session.get(
            url,
            params=params,
            timeout=client_timeout,
            headers=default_headers,
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                return resp.status, await resp.text()
            logger.debug(f"[ImgExploration] GET HTML 非200响应: HTTP {resp.status}")
            return resp.status, None

    except Exception as e:
        logger.error(f"[ImgExploration] GET HTML 失败: {url}, 错误: {e}")
        return 0, None


def bytes_to_base64_uri(data: bytes, mime_type: str = "image/jpeg") -> str:
    """将字节数据转换为 base64 data URI.

    Args:
        data: 字节数据
        mime_type: MIME 类型

    Returns:
        base64 data URI 字符串
    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def is_aiocqhttp_platform(event: Any) -> bool:
    """检测当前平台是否为 aiocqhttp (支持合并转发).

    Args:
        event: AstrBot 消息事件

    Returns:
        True 如果是 aiocqhttp 平台
    """
    platform = getattr(event, "platform", None)
    if platform:
        return "aiocqhttp" in str(platform).lower()
    return False


def get_bot_api(event: Any) -> Any | None:
    """从事件中获取底层 bot API 客户端.

    Args:
        event: AstrBot 消息事件

    Returns:
        bot API 客户端对象，失败返回 None
    """
    return getattr(event, "bot", None)


async def read_image_bytes(source: str) -> bytes | None:
    r"""读取图片源并返回字节数据

    支持多种格式：
    - HTTP/HTTPS URL: 下载图片
    - file:// 本地文件路径: 读取本地文件
    - Windows 本地路径 (C:\path 或 D:/path): 读取本地文件
    - base64:// 数据: 解码 base64
    - data:image/...;base64,... : 解码 base64 data URI

    Args:
        source: 图片源字符串

    Returns:
        图片字节数据，失败返回 None
    """
    if not source:
        return None

    # HTTP/HTTPS URL - 直接下载
    if source.startswith(("http://", "https://")):
        return await download_bytes(source)

    # file:// 本地文件
    if source.startswith("file://"):
        file_path = source[7:]  # 去掉 file:// 前缀
        # 处理 Windows 路径 (file:///C:/...)
        if file_path.startswith("/") and len(file_path) > 2 and file_path[2] == ":":
            file_path = file_path[1:]  # 去掉开头的 /
        try:
            if os.path.exists(file_path):
                return await asyncio.to_thread(lambda: open(file_path, "rb").read())
        except Exception as e:
            logger.debug(f"[ImgExploration] 读取本地文件失败: {file_path}, 错误: {e}")
        return None

    # Windows 本地路径 (如 D:\path 或 C:/path)
    if re.match(r"^[A-Za-z]:[/\\]", source):
        try:
            if os.path.exists(source):
                return await asyncio.to_thread(lambda: open(source, "rb").read())
        except Exception as e:
            logger.debug(f"[ImgExploration] 读取本地文件失败: {source}, 错误: {e}")
        return None

    # base64:// 格式
    if source.startswith("base64://"):
        try:
            return base64.b64decode(source[9:])
        except Exception as e:
            logger.debug(f"[ImgExploration] base64 解码失败: {e}")
        return None

    # data:image/...;base64,... 格式
    if source.startswith("data:image"):
        # 提取 base64 部分
        match = re.match(r"data:image/\w+;base64,(.+)", source)
        if match:
            try:
                return base64.b64decode(match.group(1))
            except Exception as e:
                logger.debug(f"[ImgExploration] data URI 解码失败: {e}")
        return None

    return None


async def upload_image(image_bytes: bytes) -> str | None:
    """将图片上传到图床.

    使用 Catbox 图床（免费，无需 API key）。

    Args:
        image_bytes: 图片字节数据

    Returns:
        上传后的图片 URL，失败返回 None
    """
    if not image_bytes:
        return None

    # 限制文件大小 (Catbox 限制 200MB)
    if len(image_bytes) > 200 * 1024 * 1024:
        logger.warning("[ImgExploration] 图片过大，超过 200MB 限制")
        return None

    client_timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
    proxy = get_proxy_url()

    try:
        session = await _get_aiohttp_session()
        # 构建 multipart form data
        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        data.add_field(
            "fileToUpload",
            image_bytes,
            filename="image.jpg",
            content_type="image/jpeg",
        )

        headers = {"User-Agent": get_user_agent()}

        async with session.post(
            CATBOX_UPLOAD_URL,
            data=data,
            headers=headers,
            timeout=client_timeout,
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                url = await resp.text()
                # Catbox 直接返回图片 URL
                if url and url.startswith("https://"):
                    return url.strip()
                logger.warning(f"[ImgExploration] Catbox 返回异常: {url}")
            else:
                text = await resp.text()
                logger.warning(
                    f"[ImgExploration] Catbox 上传失败: HTTP {resp.status}, {text}"
                )
    except Exception as e:
        logger.error(f"[ImgExploration] Catbox 上传异常: {e}")

    return None


async def get_http_image_url(source: str) -> str | None:
    """将图片源转换为 HTTP URL.

    如果已经是 HTTP URL，直接返回。
    如果是本地文件或 base64，上传到图床后返回 URL。

    Args:
        source: 图片源字符串

    Returns:
        HTTP URL，失败返回 None
    """
    if not source:
        return None

    # 已经是 HTTP URL，直接返回
    if source.startswith(("http://", "https://")):
        return source

    # 其他格式：读取并上传
    image_bytes = await read_image_bytes(source)
    if not image_bytes:
        return None

    return await upload_image(image_bytes)
