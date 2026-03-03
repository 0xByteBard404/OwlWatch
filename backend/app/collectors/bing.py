# -*- coding: utf-8 -*-
"""Bing 搜索采集器（使用多进程避免 Windows asyncio 问题）"""
import logging
from datetime import datetime
from typing import List
from urllib.parse import quote

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)


def _bing_collect_worker(keyword: str, max_results: int) -> List[dict]:
    """在独立进程中执行采集"""
    from playwright.sync_api import sync_playwright

    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            url = f'https://www.bing.com/search?q={quote(keyword)}&setlang=zh-CN'
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)

            items = page.query_selector_all('#b_results li.b_algo')

            for item in items[:max_results]:
                try:
                    title_el = item.query_selector('h2 a')
                    if not title_el:
                        continue

                    title = title_el.inner_text()
                    href = title_el.get_attribute('href')

                    desc_el = item.query_selector('.b_caption p')
                    content = desc_el.inner_text() if desc_el else ""

                    cite_el = item.query_selector('cite')
                    source = cite_el.inner_text() if cite_el else ""

                    results.append({
                        'keyword': keyword,
                        'title': title.strip(),
                        'content': content.strip(),
                        'url': href,
                        'source': source.strip(),
                        'source_type': 'bing',
                        'publish_time': datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    continue

            page.close()
            context.close()
            browser.close()

        logger.info(f"[Bing] Collected {len(results)} items for: {keyword}")

    except Exception as e:
        logger.error(f"[Bing] Collect error: {e}")

    return results


def _bing_page_content_worker(url: str) -> str:
    """在独立进程中获取页面内容"""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # 使用 networkidle 等待网络请求完成
            try:
                page.goto(url, timeout=30000, wait_until='networkidle')
            except Exception:
                # 如果 networkidle 超时，降级为 domcontentloaded
                page.goto(url, timeout=30000, wait_until='domcontentloaded')

            # 等待页面稳定
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(2000)  # 额外等待JS执行完成

            # 提取正文内容（优先获取article标签或主要内容区域）
            try:
                main_content = page.query_selector('article') or \
                               page.query_selector('main') or \
                               page.query_selector('.content') or \
                               page.query_selector('#content') or \
                               page.query_selector('body')

                if main_content:
                    content = main_content.inner_text()
                else:
                    content = page.content()
            except Exception:
                content = page.content()

            page.close()
            context.close()
            browser.close()
            return content
    except Exception as e:
        logger.error(f"[Bing] Get page content error: {e}")
        return ""


class BingCollector:
    """Bing 搜索采集器 - 每次采集在独立进程中运行"""

    source_type = "bing"

    def __init__(self):
        pass  # 不再维护浏览器实例

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """在独立进程中执行采集"""
        import asyncio

        loop = asyncio.get_event_loop()

        # 在线程池中运行同步采集函数
        results_dict = await loop.run_in_executor(
            None,
            _bing_collect_worker,
            request.keyword,
            request.max_results
        )

        # 转换为 CollectResult 对象
        results = []
        for item in results_dict:
            results.append(CollectResult(
                keyword=item['keyword'],
                title=item['title'],
                content=item['content'],
                url=item['url'],
                source=item['source'],
                source_type=item['source_type'],
                publish_time=datetime.fromisoformat(item['publish_time']),
            ))

        return results

    async def collect_page_content(self, url: str) -> str:
        """在独立进程中获取页面内容"""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            _bing_page_content_worker,
            url
        )

    async def close(self):
        """关闭（无需操作）"""
        pass
