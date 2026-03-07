"""报告生成服务"""
import httpx
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.report import Report
from ..models.article import Article
from ..models.keyword import Keyword
from ..config import settings
from ..analyzers.summary import SummaryGenerator
from ..analyzers.trend import TrendAnalyzer
from ..utils.timezone import now_cst


class ReportService:
    """报告生成服务"""

    def __init__(self, db: Session):
        self.db = db
        self.summary_generator = SummaryGenerator(settings.bailian_api_key) if settings.bailian_api_key else None
        self.trend_analyzer = TrendAnalyzer(settings.bailian_api_key) if settings.bailian_api_key else None
        self.http_client = httpx.AsyncClient()

    async def generate_daily_report(self, tenant_id: str, keyword_ids: Optional[List[str]] = None) -> Dict:
        """生成日报"""
        return await self._generate_report(
            tenant_id=tenant_id,
            report_type="daily",
            time_range="24小时",
            keyword_ids=keyword_ids
        )

    async def generate_weekly_report(self, tenant_id: str, keyword_ids: Optional[List[str]] = None) -> Dict:
        """生成周报"""
        return await self._generate_report(
            tenant_id=tenant_id,
            report_type="weekly",
            time_range="7天",
            keyword_ids=keyword_ids
        )

    async def _generate_report(
        self,
        tenant_id: str,
        report_type: str,
        time_range: str,
        keyword_ids: Optional[List[str]] = None
    ) -> Dict:
        """生成报告"""
        import uuid

        # 确定时间范围
        if time_range == "24小时":
            start_time = now_cst() - timedelta(hours=24)
        elif time_range == "7天":
            start_time = now_cst() - timedelta(days=7)
        else:
            start_time = now_cst() - timedelta(hours=24)

        # 获取关键词
        query = self.db.query(Keyword).filter(Keyword.tenant_id == tenant_id)
        if keyword_ids:
            query = query.filter(Keyword.id.in_(keyword_ids))
        keywords = query.all()

        if not keywords:
            return {"error": "未找到关键词"}

        # 收集各关键词的数据
        keyword_stats = []
        all_articles = []

        for keyword in keywords:
            articles = self.db.query(Article).filter(
                Article.keyword_id == keyword.id,
                Article.collect_time >= start_time
            ).all()

            all_articles.extend(articles)

            # 计算统计数据
            total = len(articles)
            positive = sum(1 for a in articles if a.sentiment_score and a.sentiment_score > 0.3)
            negative = sum(1 for a in articles if a.sentiment_score and a.sentiment_score < -0.3)
            neutral = total - positive - negative

            avg_sentiment = (
                sum(a.sentiment_score for a in articles if a.sentiment_score) / total
                if total and any(a.sentiment_score for a in articles)
                else 0
            )

            keyword_stats.append({
                "keyword": keyword.keyword,
                "total": total,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "avg_sentiment": round(avg_sentiment, 2)
            })

        # 生成摘要
        summary = ""
        if self.summary_generator and all_articles:
            try:
                summary = await self.summary_generator.generate(
                    [a.__dict__ for a in all_articles],
                    max_length=500
                )
            except Exception as e:
                summary = f"摘要生成失败: {str(e)}"

        # 生成趋势分析
        trend_analysis = {}
        if self.trend_analyzer and all_articles:
            try:
                trend_analysis = await self.trend_analyzer.analyze(
                    [a.__dict__ for a in all_articles],
                    time_range=time_range
                )
            except Exception as e:
                trend_analysis = {"error": str(e)}

        # 构建报告内容
        report_content = {
            "generated_at": now_cst().isoformat(),
            "time_range": time_range,
            "keywords": keyword_stats,
            "summary": summary,
            "trend_analysis": trend_analysis,
            "total_articles": len(all_articles),
        }

        # 保存报告
        report = Report(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=f"舆情分析报告 - {now_cst().strftime('%Y-%m-%d')}",
            content=json.dumps(report_content, ensure_ascii=False),
            report_type=report_type
        )

        self.db.add(report)
        self.db.commit()

        return {
            "report_id": report.id,
            "title": report.title,
            "generated_at": report.generated_at.isoformat(),
            "content": report_content
        }

    async def close(self):
        """关闭服务"""
        await self.http_client.aclose()
