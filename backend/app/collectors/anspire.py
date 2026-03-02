# -*- coding: utf-8 -*-
"""Anspire API 采集器"""
import httpx
import logging
from datetime import datetime
from typing import List, Optional

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)


class AnspireCollector:
    """Anspire API 采集器 - 用于深度爬取"""

    source_type = "anspire"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anspire.io/v1/browser-agent"

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """深度爬取指定页面"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "task": f"访问 {request.keyword} 相关页面并提取完整内容",
            "max_steps": 10
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Anspire API error: status={response.status_code}, body={response.text[:500]}")
                    return []

                data = response.json()
                return self._parse_response(data)
        except httpx.TimeoutException:
            logger.error(f"Anspire API timeout: keyword={request.keyword}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Anspire API request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Anspire collect error: {e}")
            return []

    def _parse_response(self, response: dict) -> List[CollectResult]:
        """解析 Anspire API 响应"""
        results = []
        content = response.get("content", {})

        if content:
            results.append(CollectResult(
                keyword="",
                title=content.get("title", ""),
                content=content.get("text", ""),
                url=content.get("url", ""),
                source=content.get("source", ""),
                source_type=self.source_type,
            ))

        return results
