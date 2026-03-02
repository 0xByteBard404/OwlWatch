# -*- coding: utf-8 -*-
"""预警服务"""
import httpx
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from ..models.alert import Alert
from ..models.article import Article
from ..models.keyword import Keyword
from ..config import settings
from ..analyzers.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)


class AlertRule:
    """预警规则"""
    def __init__(self, rule_type: str, threshold: float, actions: List[str]):
        self.rule_type = rule_type
        self.threshold = threshold
        self.actions = actions


class AlertService:
    """预警服务"""

    # 敏感词列表
    SENSITIVE_WORDS = [
        "投诉", "维权", "诈骗", "欺诈", "跑路",
        "倒闭", "破产", "起诉", "违法", "违规",
        "非法", "涉案", "被查", "处罚", "罚款",
        "曝光", "黑幕", "内幕", "黑平台", "传销",
        "套现", "洗钱", "非法集资", "庞氏骗局"
    ]

    def __init__(self, db: Session):
        self.db = db
        # 从配置读取阈值
        self.negative_threshold = settings.alert_negative_threshold
        self.volume_threshold = settings.alert_volume_threshold
        self.sentiment_analyzer = SentimentAnalyzer(settings.bailian_api_key) if settings.bailian_api_key else None
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # 构建预警规则（使用配置的阈值）
        self.rules = {
            "negative_burst": AlertRule(
                rule_type="negative_burst",
                threshold=self.negative_threshold,
                actions=["email", "webhook"]
            ),
            "sensitive_keyword": AlertRule(
                rule_type="sensitive_keyword",
                threshold=1,  # 包含敏感词即触发
                actions=["sms", "wechat"]
            ),
            "volume_spike": AlertRule(
                rule_type="volume_spike",
                threshold=2.0,  # 200% 增长触发
                actions=["email"]
            ),
        }

    async def check_and_alert(self, keyword_id: str):
        """检查关键词并触发预警"""
        # 获取最近 1 小时的文章
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        articles = self.db.query(Article).filter(
            Article.keyword_id == keyword_id,
            Article.collect_time >= one_hour_ago
        ).all()

        if not articles:
            return

        keyword = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            return

        # 检查负面情感爆发
        await self._check_negative_burst(articles, keyword)

        # 检查敏感词命中
        await self._check_sensitive_keywords(articles, keyword)

        # 检查讨论量激增
        await self._check_volume_spike(articles, keyword)

    async def _check_cooldown(self, keyword_id: str, alert_type: str) -> bool:
        """检查预警冷却期（同类型预警 1 小时内不重复发送）"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        existing = self.db.query(Alert).filter(
            Alert.keyword_id == keyword_id,
            Alert.alert_type == alert_type,
            Alert.status == "pending",
            Alert.created_at >= one_hour_ago
        ).first()
        return existing is not None

    async def _check_negative_burst(self, articles: List[Article], keyword: Keyword):
        """检查负面情感爆发"""
        alert_type = "negative_burst"
        rule = self.rules[alert_type]

        # 检查冷却期
        if await self._check_cooldown(keyword.id, alert_type):
            logger.debug(f"Alert cooldown: {alert_type} for keyword {keyword.id}")
            return

        negative_count = sum(1 for a in articles if a.sentiment_score and a.sentiment_score < -0.3)
        ratio = negative_count / len(articles) if articles else 0

        if ratio >= rule.threshold:
            await self._create_alert(
                keyword=keyword,
                alert_type=alert_type,
                alert_level="warning",
                message=f"1小时内负面情感占比 {ratio:.1%}，超过阈值 {rule.threshold:.1%}",
                articles=[a.id for a in articles if a.sentiment_score and a.sentiment_score < -0.3][:5]
            )

    async def _check_sensitive_keywords(self, articles: List[Article], keyword: Keyword):
        """检查敏感词命中"""
        alert_type = "sensitive_keyword"
        rule = self.rules[alert_type]

        for article in articles:
            content = article.content or ""
            title = article.title or ""

            for word in self.SENSITIVE_WORDS:
                if word in content or word in title:
                    # 敏感词预警不检查冷却期，每次都发送
                    await self._create_alert(
                        keyword=keyword,
                        alert_type=alert_type,
                        alert_level="critical",
                        message=f"检测到敏感词「{word}」",
                        articles=[article.id]
                    )
                    break

    async def _check_volume_spike(self, articles: List[Article], keyword: Keyword):
        """检查讨论量激增"""
        alert_type = "volume_spike"
        rule = self.rules[alert_type]

        # 检查冷却期
        if await self._check_cooldown(keyword.id, alert_type):
            logger.debug(f"Alert cooldown: {alert_type} for keyword {keyword.id}")
            return

        # 获取前 1 小时的文章数作为基准
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        previous_count = self.db.query(Article).filter(
            Article.keyword_id == keyword.id,
            Article.collect_time >= two_hours_ago,
            Article.collect_time < one_hour_ago
        ).count()

        current_count = len(articles)

        if previous_count > 0:
            growth = current_count / previous_count
            if growth >= rule.threshold:
                await self._create_alert(
                    keyword=keyword,
                    alert_type=alert_type,
                    alert_level="info",
                    message=f"讨论量增长 {growth:.1f} 倍，当前 {current_count} 条",
                    articles=[a.id for a in articles[:10]]
                )

    async def _create_alert(
        self,
        keyword: Keyword,
        alert_type: str,
        alert_level: str,
        message: str,
        articles: List[str]
    ):
        """创建预警"""
        alert = Alert(
            id=str(uuid.uuid4()),
            tenant_id=keyword.tenant_id,
            keyword_id=keyword.id,
            article_id=articles[0] if articles else None,
            alert_type=alert_type,
            alert_level=alert_level,
            status="pending",
            message=message
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert created: [{alert_level}] {message}")

        # 发送通知
        rule = self.rules.get(alert_type)
        if rule:
            for action in rule.actions:
                try:
                    if action == "email":
                        await self._send_email(alert)
                    elif action == "webhook":
                        await self._send_webhook(alert)
                    elif action == "sms":
                        await self._send_sms(alert)
                    elif action == "wechat":
                        await self._send_wechat(alert)
                except Exception as e:
                    logger.error(f"Failed to send {action} notification: {e}")

    async def _send_email(self, alert: Alert):
        """发送邮件通知"""
        if not all([settings.email_smtp_host, settings.email_smtp_user]):
            logger.warning("Email SMTP not configured, skipping email notification")
            return

        try:
            import aiosmtplib
            from email.message import EmailMessage

            subject = f"【{alert.alert_level.upper()}】舆情预警 - {alert.alert_type}"
            content = f"""
预警级别: {alert.alert_level}
预警类型: {alert.alert_type}
预警内容: {alert.message}
关键词ID: {alert.keyword_id}
创建时间: {alert.created_at}

请及时处理。
            """.strip()

            message = EmailMessage()
            message["From"] = settings.email_smtp_user
            message["To"] = settings.email_smtp_user  # 发送给自己，可配置
            message["Subject"] = subject
            message.set_content(content)

            await aiosmtplib.send(
                message,
                hostname=settings.email_smtp_host,
                username=settings.email_smtp_user,
                password=settings.email_smtp_password or "",
                port=587,
                start_tls=True,
            )
            logger.info(f"Email sent for alert {alert.id}")
        except ImportError:
            logger.warning("aiosmtplib not installed, skipping email notification")
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")

    async def _send_webhook(self, alert: Alert):
        """发送 Webhook 通知"""
        webhook_url = settings.alert_webhook_url
        if not webhook_url:
            return

        try:
            response = await self.http_client.post(
                webhook_url,
                json={
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "level": alert.alert_level,
                    "message": alert.message,
                    "keyword_id": alert.keyword_id,
                    "created_at": alert.created_at.isoformat()
                }
            )
            logger.info(f"Webhook sent for alert {alert.id}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook send failed: {str(e)}")

    async def _send_sms(self, alert: Alert):
        """发送短信通知"""
        if not settings.sms_access_key:
            logger.warning("SMS not configured, skipping SMS notification")
            return

        # TODO: 实现短信发送（根据具体短信服务商 API）
        logger.info(f"[短信] 预警通知: {alert.message}")

    async def _send_wechat(self, alert: Alert):
        """发送企业微信通知"""
        wechat_webhook = settings.wechat_webhook_url
        if not wechat_webhook:
            return

        try:
            response = await self.http_client.post(
                wechat_webhook,
                json={
                    "msgtype": "text",
                    "text": {
                        "content": f"【{alert.alert_level.upper()}】{alert.message}\n类型: {alert.alert_type}\n时间: {alert.created_at}"
                    }
                }
            )
            logger.info(f"WeChat webhook sent for alert {alert.id}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"WeChat webhook send failed: {str(e)}")

    async def send_notification(self, alert: Alert):
        """手动发送预警通知（用于测试）"""
        rule = self.rules.get(alert.alert_type)
        if rule:
            for action in rule.actions:
                try:
                    if action == "email":
                        await self._send_email(alert)
                    elif action == "webhook":
                        await self._send_webhook(alert)
                    elif action == "sms":
                        await self._send_sms(alert)
                    elif action == "wechat":
                        await self._send_wechat(alert)
                except Exception as e:
                    logger.error(f"Failed to send {action} notification: {e}")

    async def close(self):
        """关闭服务"""
        await self.http_client.aclose()
