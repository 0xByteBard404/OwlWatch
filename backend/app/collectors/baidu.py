# -*- coding: utf-8 -*-
"""百度搜索采集器（使用多进程避免 Windows asyncio 问题）"""
import logging
from datetime import datetime
from typing import List
from urllib.parse import quote

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)


def _baidu_collect_worker(keyword: str, max_results: int) -> List[dict]:
    """在独立进程中执行采集"""
    from playwright.sync_api import sync_playwright

    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--no-first-run',
                    '--no-default-browser-check',
                ]
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
            )
            # 添加更多反检测配置
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
            """)

            page = context.new_page()

            url = f'https://www.baidu.com/s?wd={quote(keyword)}'
            page.goto(url, timeout=60000, wait_until='networkidle')
            page.wait_for_timeout(2000)

            # 检查是否被重定向到验证页面
            if 'verify' in page.url or '安全验证' in page.title():
                logger.warning(f"[Baidu] Blocked by security verification for: {keyword}")
                page.close()
                context.close()
                browser.close()
                return results

            items = page.query_selector_all('#content_left .result')

            for item in items[:max_results]:
                try:
                    title_el = item.query_selector('h3')
                    if not title_el:
                        continue
                    title = title_el.inner_text()

                    link_el = item.query_selector('h3 a')
                    baidu_url = link_el.get_attribute('href') if link_el else ""

                    desc_el = item.query_selector('.c-abstract') or item.query_selector('.c-span9.c-color-text')
                    snippet = desc_el.inner_text() if desc_el else ""

                    source_el = item.query_selector('.c-showurl') or item.query_selector('.source_1Vdff')
                    source = source_el.inner_text() if source_el else ""

                    results.append({
                        'keyword': keyword,
                        'title': title.strip(),
                        'content': snippet.strip(),
                        'url': baidu_url,
                        'source': source.strip(),
                        'source_type': 'baidu',
                        'publish_time': datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    continue

            page.close()
            context.close()
            browser.close()

        logger.info(f"[Baidu] Collected {len(results)} items for: {keyword}")

    except Exception as e:
        logger.error(f"[Baidu] Collect error: {e}")

    return results


def _baidu_page_content_worker(url: str) -> str:
    """在独立进程中获取页面内容"""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(1000)
            content = page.content()
            page.close()
            context.close()
            browser.close()
            return content
    except Exception as e:
        logger.error(f"[Baidu] Get page content error: {e}")
        return ""


class BaiduCollector:
    """百度搜索采集器 - 每次采集在独立进程中运行"""

    source_type = "baidu"

    def __init__(self):
        pass  # 不再维护浏览器实例

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """在独立进程中执行采集"""
        import asyncio

        loop = asyncio.get_event_loop()

        # 在线程池中运行同步采集函数
        results_dict = await loop.run_in_executor(
            None,
            _baidu_collect_worker,
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
            _baidu_page_content_worker,
            url
        )

    async def close(self):
        """关闭（无需操作）"""
        pass
