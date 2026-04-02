"""Google Lens 搜图策略实现.

通过 SerpAPI 调用 Google Lens 进行图片搜索。
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse

import aiohttp

from astrbot.api import logger

from .constant import HTTP_TIMEOUT_SECONDS, SERPAPI_BASE_URL
from .models import SearchResultItem
from .strategy import ImageSearchStrategy
from .utils import _get_aiohttp_session, download_bytes, get_proxy_url


class GoogleLensStrategy(ImageSearchStrategy):
    """Google Lens 搜图策略.

    使用 SerpAPI 的 google_lens 引擎进行图片搜索。
    支持多 API Key 负载均衡和余额检查。
    """

    def __init__(self, api_keys: list[str] | None = None) -> None:
        """初始化 Google Lens 策略.

        Args:
            api_keys: SerpAPI API Key 列表，支持多 Key 负载均衡
        """
        self.api_keys = api_keys or []
        self._current_key_index = 0
        self._key_lock = asyncio.Lock()

    def get_service_name(self) -> str:
        return "Google Lens"

    async def search(self, image_url: str) -> list[SearchResultItem]:
        """执行 Google Lens 搜索.

        Args:
            image_url: 图片 URL 地址

        Returns:
            搜索结果列表
        """
        if not self.api_keys:
            logger.warning("[GoogleLens] 未配置 SerpAPI Key，跳过搜索")
            return []

        if not image_url.startswith(("http://", "https://")):
            logger.warning("[GoogleLens] SerpAPI 不支持本地文件")
            return []

        try:
            # 选择可用的 API Key
            api_key = await self._select_viable_key()
            if not api_key:
                logger.error("[GoogleLens] 所有 API Key 已耗尽")
                return []

            logger.info(f"[GoogleLens] 使用 Key ...{api_key[-4:]} 开始搜索")

            # 构建 SerpAPI 请求
            params = {
                "api_key": api_key,
                "engine": "google_lens",
                "url": image_url,
                "hl": "zh-cn",
            }

            url = f"{SERPAPI_BASE_URL}/search?{urllib.parse.urlencode(params)}"

            session = await _get_aiohttp_session()
            timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
            proxy = get_proxy_url()

            async with session.get(url, timeout=timeout, proxy=proxy) as resp:
                if resp.status != 200:
                    logger.error(f"[GoogleLens] API 返回错误: HTTP {resp.status}")
                    return []

                text = await resp.text()
                data = json.loads(text)

            # 解析结果
            results = []
            if "visual_matches" in data:
                matches = data["visual_matches"]
                limit = min(len(matches), 8)  # 最多 8 条结果

                for i in range(limit):
                    try:
                        match = matches[i]
                        title = match.get("title", "")
                        link = match.get("link", "")
                        source = match.get("source", "")
                        thumbnail = match.get("thumbnail", "")

                        if not title or not link:
                            continue

                        # 下载缩略图
                        thumbnail_bytes = await download_bytes(thumbnail)

                        results.append(
                            SearchResultItem(
                                title=title,
                                url=link,
                                thumbnail=thumbnail,
                                thumbnail_bytes=thumbnail_bytes,
                                source="Google Lens",
                                similarity=None,
                                description=source,
                                domain=None,
                            )
                        )
                    except Exception as e:
                        logger.warning(f"[GoogleLens] 解析结果项失败: {e}")

            elif "error" in data:
                logger.error(f"[GoogleLens] SerpAPI 错误: {data['error']}")

            logger.info(f"[GoogleLens] 搜索完成，获取 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"[GoogleLens] 搜索异常: {e}")
            return []

    async def _select_viable_key(self) -> str | None:
        """选择有余额的 API Key.

        实现负载均衡和余额检查。

        Returns:
            可用的 API Key，如果没有则返回 None
        """
        if not self.api_keys:
            return None

        async with self._key_lock:
            start_idx = self._current_key_index % len(self.api_keys)

            for i in range(len(self.api_keys)):
                idx = (start_idx + i) % len(self.api_keys)
                key = self.api_keys[idx]

                # 检查余额
                searches_left = await self._check_quota(key)

                if searches_left > 0:
                    # 明确知道还有余额的 Key，优先使用
                    self._current_key_index = idx
                    return key
                elif searches_left == 0:
                    # 余额为 0，跳过该 Key
                    logger.info(f"[GoogleLens] Key ...{key[-4:]} 余额为 0，跳过此 Key")
                    continue
                else:
                    # 查询失败（返回 -1），视为余额未知，作为降级策略仍允许使用
                    logger.debug(
                        f"[GoogleLens] 无法确定 Key ...{key[-4:]} 余额，作为降级策略仍尝试使用该 Key"
                    )
                    self._current_key_index = idx
                    return key

            return None

    @staticmethod
    async def _check_quota(api_key: str) -> int:
        """检查 SerpAPI Key 的剩余搜索次数.

        Args:
            api_key: API Key

        Returns:
            剩余搜索次数，查询失败返回 -1
        """
        url = f"{SERPAPI_BASE_URL}/account?api_key={api_key}"

        try:
            session = await _get_aiohttp_session()
            timeout = aiohttp.ClientTimeout(total=10)
            proxy = get_proxy_url()

            async with session.get(url, timeout=timeout, proxy=proxy) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    data = json.loads(text)
                    return data.get("total_searches_left", 0)

        except Exception as e:
            logger.debug(f"[GoogleLens] 检查 Key ...{api_key[-4:]} 余额失败: {e}")

        return -1
