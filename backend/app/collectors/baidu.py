# -*- coding: utf-8 -*-
"""百度搜索采集器（使用 Playwright 同步 API）"""
import logging
import asyncio
from datetime import datetime
from typing import List
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import threading

from .base import CollectResult, CollectRequest

logger = logging.getLogger(__name__)

# 共享线程池（所有采集器共用）
_shared_executor = None
_executor_lock = threading.Lock()


def get_shared_executor():
    """获取共享线程池"""
    global _shared_executor
    if _shared_executor is None:
        with _executor_lock:
            if _shared_executor is None:
                _shared_executor = ThreadPoolExecutor(max_workers=3)
    return _shared_executor


# 线程本地存储
_thread_local = threading.local()


def _get_or_create_browser():
    """获取或创建浏览器实例"""
    if not hasattr(_thread_local, 'context') or _thread_local.context is None:
        try:
            from playwright.sync_api import sync_playwright
            _thread_local.playwright = sync_playwright().start()
            _thread_local.browser = _thread_local.playwright.chromium.launch(headless=True)
            _thread_local.context = _thread_local.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            logger.debug("Created new browser context")
        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            raise
    return _thread_local.context


def _check_browser_alive():
    """检查浏览器是否存活"""
    try:
        if hasattr(_thread_local, 'context') and _thread_local.context is not None:
            test_page = _thread_local.context.new_page()
            test_page.close()
            return True
    except Exception:
        pass

    _cleanup_browser()
    return False


def _cleanup_browser():
    """清理浏览器资源"""
    try:
        if hasattr(_thread_local, 'context') and _thread_local.context:
            _thread_local.context.close()
    except Exception:
        pass
    try:
        if hasattr(_thread_local, 'browser') and _thread_local.browser:
            _thread_local.browser.close()
    except Exception:
        pass
    try:
        if hasattr(_thread_local, 'playwright') and _thread_local.playwright:
            _thread_local.playwright.stop()
    except Exception:
        pass

    _thread_local.context = None
    _thread_local.browser = None
    _thread_local.playwright = None
    logger.debug("Cleaned up browser")


def _collect_baidu_sync(keyword: str, max_results: int) -> List[CollectResult]:
    """执行百度采集（同步版本，在线程中运行）"""
    if not _check_browser_alive():
        _get_or_create_browser()

    context = _thread_local.context
    results = []
    page = None

    try:
        page = context.new_page()
        url = f'https://www.baidu.com/s?wd={quote(keyword)}'

        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)

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

                real_url = baidu_url
                content = snippet

                # 不在这里做深度跳转，太慢了
                results.append(CollectResult(
                    keyword=keyword,
                    title=title.strip(),
                    content=content.strip(),
                    url=real_url,
                    source=source.strip(),
                    source_type="baidu",
                    publish_time=datetime.utcnow(),
                ))
            except Exception as e:
                logger.debug(f"Parse item error: {e}")
                continue

        logger.info(f"Baidu collected {len(results)} items for: {keyword}")

    except Exception as e:
        logger.error(f"Baidu collect error: {e}")
        _cleanup_browser()
    finally:
        if page:
            try:
                page.close()
            except:
                pass

    return results


def _collect_page_content_sync(url: str) -> str:
    """获取页面实际内容（同步版本）"""
    if not _check_browser_alive():
        _get_or_create_browser()

    context = _thread_local.context
    page = None
    try:
        page = context.new_page()
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(1000)
        content = page.content()
        return content
    except Exception as e:
        logger.error(f"Get page content error: {e}")
        return ""
    finally:
        if page:
            try:
                page.close()
            except:
                pass


class BaiduCollector:
    """百度搜索采集器"""

    source_type = "baidu"

    async def collect(self, request: CollectRequest) -> List[CollectResult]:
        """执行采集"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            get_shared_executor(),
            _collect_baidu_sync,
            request.keyword,
            request.max_results
        )

    async def collect_page_content(self, url: str) -> str:
        """获取页面实际内容"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(get_shared_executor(), _collect_page_content_sync, url)

    def close(self):
        """关闭浏览器（不需要手动关闭，由线程池管理）"""
        pass
