"""采集器模块"""
from .base import CollectResult, CollectRequest
from .bocha import BochaCollector
from .tavily import TavilyCollector
from .anspire import AnspireCollector

__all__ = [
    "CollectResult",
    "CollectRequest",
    "BochaCollector",
    "TavilyCollector",
    "AnspireCollector",
]
