# -*- coding: utf-8 -*-
"""Tavily API 采集器"""
import httpx
import logging
from datetime import datetime
from typing import List, Optional

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)


class TavilyCollector:
    """Tavily API 采集器"""

    source_type = "tavily"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """执行采集"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "query": request.keyword,
            "max_results": request.max_results,
            "search_depth": "basic",
            "include_raw_content": False
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Tavily API error: status={response.status_code}, body={response.text[:500]}")
                    return []

                data = response.json()
                return self._parse_response(data)
        except httpx.TimeoutException:
            logger.error(f"Tavily API timeout: keyword={request.keyword}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Tavily API request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Tavily collect error: {e}")
            return []

    def _parse_response(self, response: dict) -> List[CollectResult]:
        """解析 Tavily API 响应"""
        results = []
        for item in response.get("results", []):
            results.append(CollectResult(
                keyword=response.get("query", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                source_type=self.source_type,
                publish_time=self._parse_time(item.get("published_date")),
            ))
        return results

    @staticmethod
    def _parse_time(time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            # ISO 格式
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            return None
