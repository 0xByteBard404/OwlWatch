"""采集器模块"""
from .base import CollectResult, CollectRequest
from .bocha import BochaCollector
from .tavily import TavilyCollector
from .anspire import AnspireCollector
from .rss_collector import RSSCollector

__all__ = [
    "CollectResult",
    "CollectRequest",
    "BochaCollector",
    "TavilyCollector",
    "AnspireCollector",
    "RSSCollector",
]
