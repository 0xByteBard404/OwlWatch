# -*- coding: utf-8 -*-
"""博查 API 采集器"""
import httpx
import logging
from datetime import datetime
from typing import List, Optional

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)


class BochaCollector:
    """博查 API 采集器"""

    source_type = "bocha"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bocha.cn/v1/web-search"

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """执行采集"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 时间范围映射到博查 API 支持的格式
        freshness_map = {
            "oneDay": "oneDay",
            "threeDays": "oneWeek",  # 博查不支持3天，映射到1周
            "oneWeek": "oneWeek",
            "oneMonth": "oneMonth",
            "threeMonths": "oneYear",  # 博查不支持3个月，映射到1年
        }

        payload = {
            "query": request.keyword,
            "count": request.max_results,
            "freshness": freshness_map.get(request.time_range, request.time_range) or "noLimit",
            "summary": True
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Bocha API error: status={response.status_code}, body={response.text[:500]}")
                    return []

                data = response.json()
                return self._parse_response(data)
        except httpx.TimeoutException:
            logger.error(f"Bocha API timeout: keyword={request.keyword}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Bocha API request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Bocha collect error: {e}")
            return []

    def _parse_response(self, response: dict) -> List[CollectResult]:
        """解析博查 API 响应"""
        results = []
        web_pages = response.get("data", {}).get("webPages", {}).get("value", [])

        for item in web_pages:
            results.append(CollectResult(
                keyword=response.get("query", ""),
                title=item.get("name", ""),
                content=item.get("summary") or item.get("snippet", ""),
                url=item.get("url", ""),
                source=item.get("siteName", ""),
                source_type=self.source_type,
                publish_time=self._parse_time(item.get("dateLastCrawled")),
            ))

        return results

    @staticmethod
    def _parse_time(time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            # 尝试 ISO 格式（最常见）
            if "T" in time_str:
                # 处理 2026-03-02T10:30:00 或 2026-03-02T10:30:00Z 格式
                clean_str = time_str.replace("Z", "").split(".")[0]
                return datetime.fromisoformat(clean_str)

            # 尝试其他格式
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return None
