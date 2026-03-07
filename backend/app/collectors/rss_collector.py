# -*- coding: utf-8 -*-
"""RSS/Atom 订阅采集器"""
import httpx
import feedparser
import logging
import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from .base import CollectResult, extract_domain_from_url

logger = logging.getLogger(__name__)

# 东八区时区
CST = timezone(timedelta(hours=8))


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
                result = await self._parse_entry(entry, feed_url, parsed.feed)
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

    async def _parse_entry(
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

            # 提取发布时间（优先详情页 > RSS > URL）
            publish_time = await self._extract_publish_time(entry, url)

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

    async def _extract_publish_time(self, entry: dict, url: str) -> Optional[datetime]:
        """提取发布时间（优先级：详情页 > RSS > URL）"""
        # 1. 先尝试从 RSS feed 中获取
        publish_time = self._parse_publish_time_from_rss(entry)
        if publish_time:
            return publish_time

        # 2. 尝试从详情页获取
        if url:
            publish_time = await self._fetch_publish_time_from_page(url)
            if publish_time:
                return publish_time

        # 3. 尝试从 URL 中提取日期
        if url:
            publish_time = self._extract_date_from_url(url)
            if publish_time:
                return publish_time

        return None

    def _parse_publish_time_from_rss(self, entry: dict) -> Optional[datetime]:
        """从 RSS feed 中解析发布时间（转换为东八区）"""
        # feedparser 会解析时间到 published_parsed 或 updated_parsed（返回的是 UTC 时间）
        time_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_tuple:
            try:
                # feedparser 返回的是 UTC 时间，需要转换为东八区
                utc_dt = datetime(*time_tuple[:6], tzinfo=timezone.utc)
                cst_dt = utc_dt.astimezone(CST).replace(tzinfo=None)
                return cst_dt
            except Exception:
                pass

        # 尝试解析字符串
        time_str = entry.get("published") or entry.get("updated") or entry.get("pubDate")
        if time_str and time_str != "Invalid Date":
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(time_str)
                # 转换为东八区
                if dt.tzinfo is None:
                    # 假设是 UTC 时间
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(CST).replace(tzinfo=None)
            except Exception:
                pass

        return None

    async def _fetch_publish_time_from_page(self, url: str) -> Optional[datetime]:
        """从详情页获取发布时间"""
        try:
            response = await self.client.get(url, timeout=10.0)
            if response.status_code != 200:
                return None

            html = response.text

            # 中国新闻网特殊处理：组合 newsdate + newstime
            newsdate_match = re.search(r'<input[^>]+id=["\']newsdate["\'][^>]+value=["\']([^"\']+)["\']', html, re.IGNORECASE)
            newstime_match = re.search(r'<input[^>]+id=["\']newstime["\'][^>]+value=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if newsdate_match and newstime_match:
                time_str = f"{newsdate_match.group(1)} {newstime_match.group(1)}"
                parsed = self._parse_time_string(time_str)
                if parsed:
                    logger.debug(f"Got publish time from chinanews: {url} -> {parsed}")
                    return parsed

            # 中国新闻网：pubtime_baidu span
            pubtime_match = re.search(r'<span[^>]+id=["\']pubtime_baidu["\'][^>]*>([^<]+)</span>', html, re.IGNORECASE)
            if pubtime_match:
                parsed = self._parse_time_string(pubtime_match.group(1).strip())
                if parsed:
                    return parsed

            # 常见的发布时间 meta 标签
            patterns = [
                r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']publishdate["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']PubDate["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
                r'<time[^>]+datetime=["\']([^"\']+)["\']',
                r'<span[^>]+class=["\'].*?date.*?["\'][^>]*>(\d{4}-\d{2}-\d{2})',
                r'<div[^>]+class=["\'].*?time.*?["\'][^>]*>([^<]+)</div>',
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    time_str = match.group(1).strip()
                    parsed = self._parse_time_string(time_str)
                    if parsed:
                        logger.debug(f"Got publish time from page: {url} -> {parsed}")
                        return parsed

            return None
        except Exception as e:
            logger.debug(f"Failed to fetch publish time from page: {url} - {e}")
            return None

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串（转换为东八区）"""
        from email.utils import parsedate_to_datetime

        # 常见时间格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                # 如果有时区信息，转换为东八区
                if dt.tzinfo is not None:
                    dt = dt.astimezone(CST).replace(tzinfo=None)
                return dt
            except Exception:
                pass

        # 尝试 email 格式
        try:
            dt = parsedate_to_datetime(time_str)
            # 转换为东八区
            if dt.tzinfo is not None:
                dt = dt.astimezone(CST).replace(tzinfo=None)
            return dt
        except Exception:
            pass

        return None

    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """从 URL 中提取日期"""
        # 匹配 /2026/03-07/ 格式
        match = re.search(r'/(\d{4})/(\d{2})-(\d{2})/', url)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except Exception:
                pass

        # 匹配 /20260307/ 格式
        match = re.search(r'/(\d{4})(\d{2})(\d{2})/', url)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except Exception:
                pass

        return None
