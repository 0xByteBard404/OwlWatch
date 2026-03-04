# -*- coding: utf-8 -*-
"""百度搜索采集器（使用多进程避免 Windows asyncio 问题）"""
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from .base import CollectResult, CollectRequest, extract_domain_from_url

logger = logging.getLogger(__name__)


def _resolve_redirect_url(page, baidu_url: str) -> str:
    """解析百度重定向URL获取真实地址"""
    if not baidu_url or 'baidu.com/link' not in baidu_url:
        return baidu_url

    try:
        # 创建新页面解析重定向
        redirect_page = page.context.new_page()
        redirect_page.goto(baidu_url, timeout=10000, wait_until='domcontentloaded')
        redirect_page.wait_for_timeout(1500)  # 等待重定向完成
        real_url = redirect_page.url
        redirect_page.close()

        # 如果还是百度链接，说明重定向失败
        if 'baidu.com' in real_url:
            return baidu_url
        return real_url
    except Exception as e:
        logger.debug(f"Failed to resolve redirect URL: {e}")
        return baidu_url


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

                    # 解析百度重定向URL获取真实地址
                    real_url = _resolve_redirect_url(page, baidu_url)

                    desc_el = item.query_selector('.c-abstract') or item.query_selector('.c-span9.c-color-text')
                    snippet = desc_el.inner_text() if desc_el else ""

                    source_el = item.query_selector('.c-showurl') or item.query_selector('.source_1Vdff')
                    source = source_el.inner_text() if source_el else ""
                    # 如果来源为空，从真实URL提取域名
                    if not source:
                        source = extract_domain_from_url(real_url)

                    results.append({
                        'keyword': keyword,
                        'title': title.strip(),
                        'content': snippet.strip(),
                        'url': real_url,  # 使用真实URL
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


def _extract_publish_time_from_page(page) -> Optional[str]:
    """从页面中提取发布时间"""
    import re

    try:
        # 1. 尝试从 meta 标签获取发布时间
        meta_selectors = [
            'meta[property="article:published_time"]',
            'meta[property="og:published_time"]',
            'meta[property="article:published"]',
            'meta[name="publishdate"]',
            'meta[name="pubdate"]',
            'meta[name="PublishDate"]',
            'meta[name=" PubDate"]',
            'meta[name="date"]',
            'meta[itemprop="datePublished"]',
        ]

        for selector in meta_selectors:
            try:
                meta = page.query_selector(selector)
                if meta:
                    content = meta.get_attribute('content')
                    if content:
                        return content
            except Exception:
                continue

        # 2. 尝试从 time 标签获取
        time_el = page.query_selector('time[datetime]')
        if time_el:
            datetime_attr = time_el.get_attribute('datetime')
            if datetime_attr:
                return datetime_attr

        # 3. 尝试从 JSON-LD 结构化数据获取
        try:
            json_ld_scripts = page.query_selector_all('script[type="application/ld+json"]')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.inner_text())
                    # 处理可能的列表格式
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    if isinstance(data, dict):
                        date_published = data.get('datePublished') or data.get('dateCreated')
                        if date_published:
                            return date_published
                except Exception:
                    continue
        except Exception:
            pass

        # 4. 尝试从常见的时间 class 或 id 中获取
        time_selectors = [
            '.publish-time', '.pub-time', '.article-time',
            '.post-date', '.article-date', '.news-date',
            '#publish-time', '#pub-time', '#article-time',
            '.date', '.time', '#date', '#time',
            'span[class*="date"]', 'div[class*="date"]',
        ]

        for selector in time_selectors:
            try:
                el = page.query_selector(selector)
                if el:
                    text = el.inner_text().strip()
                    # 验证是否是日期格式
                    if _is_valid_date_text(text):
                        return text
            except Exception:
                continue

    except Exception as e:
        logger.debug(f"[Extract publish time] Error: {e}")

    return None


def _is_valid_date_text(text: str) -> bool:
    """检查文本是否可能是有效的日期"""
    import re
    if not text or len(text) > 100:
        return False

    # 常见日期格式正则
    date_patterns = [
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}',  # 2024-01-01, 2024/01/01, 2024年1月1日
        r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',      # 01-01-2024, 01/01/2024
        r'\d{4}年\d{1,2}月\d{1,2}日',         # 中文格式
    ]

    for pattern in date_patterns:
        if re.search(pattern, text):
            return True
    return False


def _baidu_page_content_worker(url: str) -> dict:
    """在独立进程中获取页面内容和发布时间"""
    from playwright.sync_api import sync_playwright

    result = {'content': '', 'publish_time': None}

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

            # 提取发布时间
            publish_time_str = _extract_publish_time_from_page(page)
            if publish_time_str:
                result['publish_time'] = _parse_publish_time(publish_time_str)

            # 提取正文内容（优先获取article标签或主要内容区域）
            try:
                # 尝试获取主要内容区域
                main_content = page.query_selector('article') or \
                               page.query_selector('main') or \
                               page.query_selector('.content') or \
                               page.query_selector('#content') or \
                               page.query_selector('body')

                if main_content:
                    # 获取文本内容，去除HTML标签
                    result['content'] = main_content.inner_text()
                else:
                    result['content'] = page.content()
            except Exception:
                result['content'] = page.content()

            page.close()
            context.close()
            browser.close()
    except Exception as e:
        logger.error(f"[Baidu] Get page content error: {e}")

    return result


def _parse_publish_time(time_str: str) -> Optional[str]:
    """解析发布时间字符串，返回 ISO 格式"""
    if not time_str:
        return None

    try:
        # 尝试 ISO 格式
        if 'T' in time_str:
            clean_str = time_str.replace('Z', '').split('+')[0].split('.')[0]
            return clean_str

        # 处理中文日期格式：2024年1月1日
        import re
        cn_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_str)
        if cn_match:
            year, month, day = cn_match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # 处理斜杠格式：2024/01/01
        if '/' in time_str:
            parts = time_str.replace(' ', '-').split('/')
            if len(parts) >= 3:
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2][:2].zfill(2)}"

        # 处理横杠格式：2024-01-01
        if '-' in time_str and len(time_str) >= 10:
            return time_str[:10]

    except Exception:
        pass

    return None


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

    async def collect_page_content(self, url: str) -> dict:
        """在独立进程中获取页面内容和发布时间

        Returns:
            dict: {'content': str, 'publish_time': Optional[str]}
        """
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
