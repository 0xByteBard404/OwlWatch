# -*- coding: utf-8 -*-
"""RSS/Atom 订阅采集器"""
import httpx
import feedparser
import logging
import hashlib
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from .base import CollectResult, extract_domain_from_url

logger = logging.getLogger(__name__)


class RSSCollector:
    """RSS/Atom 订阅采集器"""

    source_type = "rss"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    async def fetch_feed(
        self,
        feed_url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        last_entry_id: Optional[str] = None,
    ) -> Tuple[List[CollectResult], Optional[str], Optional[str], Optional[str]]:
        """
        获取 RSS Feed 的新内容
        
        Args:
            feed_url: RSS 订阅地址
            etag: HTTP ETag（用于缓存）
            last_modified: HTTP Last-Modified（用于缓存）
            last_entry_id: 已知的最后一条条目 ID（用于增量获取）
        
        Returns:
            Tuple[List[CollectResult], etag, last_modified, new_last_entry_id]
        """
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        try:
            response = await self.client.get(feed_url, headers=headers)

            # 304 Not Modified - 无更新
            if response.status_code == 304:
                logger.debug(f"RSS feed not modified: {feed_url}")
                return [], etag, last_modified, last_entry_id

            if response.status_code != 200:
                logger.error(f"RSS fetch error: status={response.status_code}, url={feed_url}")
                return [], None, None, last_entry_id

            # 解析 RSS/Atom
            parsed = feedparser.parse(response.content)

            if parsed.bozo and not parsed.entries:
                logger.error(f"RSS parse error: {parsed.bozo_exception}, url={feed_url}")
                return [], None, None, last_entry_id

            # 提取新的 ETag 和 Last-Modified
            new_etag = response.headers.get("ETag")
            new_last_modified = response.headers.get("Last-Modified")

            # 过滤新条目
            new_entries = self._filter_new_entries(parsed.entries, last_entry_id)

            # 转换为 CollectResult
            results = []
            new_last_entry_id_out = last_entry_id

            for entry in new_entries:
                result = self._parse_entry(entry, feed_url, parsed.feed)
                if result:
                    results.append(result)
                    # 更新最后一条条目 ID（取第一条，因为 RSS 通常是按时间倒序）
                    if new_last_entry_id_out == last_entry_id:
                        new_last_entry_id_out = self._get_entry_id(entry)

            logger.info(f"RSS fetch success: {feed_url}, new_entries={len(results)}")
            return results, new_etag, new_last_modified, new_last_entry_id_out

        except httpx.TimeoutException:
            logger.error(f"RSS fetch timeout: {feed_url}")
            raise
        except httpx.RequestError as e:
            logger.error(f"RSS fetch request error: {e}")
            raise
        except Exception as e:
            logger.error(f"RSS fetch error: {e}")
            raise

    def _filter_new_entries(
        self, entries: List[dict], last_entry_id: Optional[str]
    ) -> List[dict]:
        """过滤出新条目（增量获取）"""
        if not last_entry_id:
            # 没有记录过，返回所有条目
            return entries[:50]  # 限制首次获取数量

        new_entries = []
        for entry in entries:
            entry_id = self._get_entry_id(entry)
            if entry_id == last_entry_id:
                # 已到达已知的最后一条，停止
                break
            new_entries.append(entry)

        return new_entries

    def _get_entry_id(self, entry: dict) -> str:
        """获取条目的唯一标识"""
        # 优先使用 id，其次使用 link 的 hash
        if entry.get("id"):
            return entry.get("id")
        if entry.get("link"):
            return hashlib.md5(entry.get("link").encode()).hexdigest()
        if entry.get("title"):
            return hashlib.md5(entry.get("title").encode()).hexdigest()
        return ""

    def _parse_entry(
        self, entry: dict, feed_url: str, feed_info: dict
    ) -> Optional[CollectResult]:
        """解析 RSS 条目为 CollectResult"""
        try:
            # 提取标题
            title = entry.get("title", "")
            if not title:
                return None

            # 提取内容
            content = (
                entry.get("summary")
                or entry.get("description")
                or entry.get("content", [{}])[0].get("value", "")
            )

            # 清理乱码字符 (Unicode 私有使用区字符)
            import re
            content = re.sub(r'[\ue000-\uf8ff\udb80-\udbff]', '', content)
            title = re.sub(r'[\ue000-\uf8ff\udb80-\udbff]', '', title)

            # 提取链接
            url = entry.get("link", "")
            if not url:
                # 尝试从 links 中获取
                links = entry.get("links", [])
                if links:
                    url = links[0].get("href", "")

            # 提取来源
            source = self._extract_source(entry, feed_info, feed_url)

            # 提取发布时间
            publish_time = self._parse_publish_time(entry)

            return CollectResult(
                keyword="",  # 由调用方填充
                title=title,
                content=content,
                url=url,
                source=source,
                source_type=self.source_type,
                publish_time=publish_time,
                extra={
                    "entry_id": self._get_entry_id(entry),
                    "author": entry.get("author", ""),
                    "feed_title": feed_info.get("title", ""),
                },
            )
        except Exception as e:
            logger.error(f"RSS entry parse error: {e}")
            return None

    def _extract_source(self, entry: dict, feed_info: dict, feed_url: str) -> str:
        """提取来源名称"""
        # 优先使用 feed 的 title
        if feed_info.get("title"):
            return feed_info.get("title")

        # 尝试从条目中获取
        if entry.get("source"):
            return entry.get("source").get("title", "") or entry.get("source")

        # 从 URL 提取域名
        return extract_domain_from_url(feed_url)

    def _parse_publish_time(self, entry: dict) -> Optional[datetime]:
        """解析发布时间"""
        # feedparser 会解析时间到 published_parsed 或 updated_parsed
        time_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_tuple:
            try:
                return datetime(*time_tuple[:6])
            except Exception:
                pass

        # 尝试解析字符串
        time_str = entry.get("published") or entry.get("updated") or entry.get("pubDate")
        if time_str:
            try:
                # feedparser 已经标准化了时间格式
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(time_str)
            except Exception:
                pass

        return None
