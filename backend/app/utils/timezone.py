# -*- coding: utf-8 -*-
"""时区工具模块 - 统一使用东八区时间"""
from datetime import datetime, timezone, timedelta

# 东八区时区
CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    """获取当前东八区时间（无时区信息）"""
    return datetime.now(CST).replace(tzinfo=None)


def to_cst(dt: datetime) -> datetime:
    """转换时间到东八区"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 假设是 UTC 时间，转换为东八区
        return dt + timedelta(hours=8)
    return dt.astimezone(CST).replace(tzinfo=None)
