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
from ..models.keyword import Keyword, DEFAULT_ALERT_CONFIG
from ..models.article_keyword import ArticleKeyword
from ..models.sentiment_keyword import SentimentKeyword
from ..config import settings
from ..analyzers.sentiment import SentimentAnalyzer
from ..utils.timezone import now_cst

logger = logging.getLogger(__name__)


class AlertRule:
    """预警规则"""
    def __init__(self, rule_type: str, threshold: float, actions: List[str]):
        self.rule_type = rule_type
        self.threshold = threshold
        self.actions = actions


class AlertService:
    """预警服务"""

    # 从数据库加载的情感关键词（缓存）
    _positive_keywords_cache: List[str] = []
    _negative_keywords_cache: List[str] = []
    _keywords_cache_time: datetime = None

    def _get_sentiment_keywords(self) -> tuple:
        """从数据库加载情感关键词（带缓存）"""
        # 缓存有效期 1 小时
        if (self._keywords_cache_time and
            (now_cst() - self._keywords_cache_time).total_seconds() < 3600):
            return self._positive_keywords_cache, self._negative_keywords_cache

        try:
            # 从数据库加载正面关键词
            positive_kws = self.db.query(SentimentKeyword).filter(
                SentimentKeyword.sentiment_type == 'positive',
                SentimentKeyword.is_active == True
            ).all()
            self._positive_keywords_cache = [kw.keyword for kw in positive_kws]

            # 从数据库加载负面关键词
            negative_kws = self.db.query(SentimentKeyword).filter(
                SentimentKeyword.sentiment_type == 'negative',
                SentimentKeyword.is_active == True
            ).all()
            self._negative_keywords_cache = [kw.keyword for kw in negative_kws]

            self._keywords_cache_time = now_cst()
            logger.info(f"已加载情感关键词: 正面 {len(self._positive_keywords_cache)} 个, 负面 {len(self._negative_keywords_cache)} 个")

            return self._positive_keywords_cache, self._negative_keywords_cache
        except Exception as e:
            logger.error(f"加载情感关键词失败: {e}")
            # 使用备用关键词
            return [], self._get_fallback_negative_keywords()

    def _get_fallback_negative_keywords(self) -> List[str]:
        """备用负面关键词（数据库加载失败时使用）"""
        return [
            "投诉", "维权", "诈骗", "欺诈", "跑路",
            "倒闭", "破产", "起诉", "违法", "违规",
            "非法", "涉案", "被查", "处罚", "罚款",
            "曝光", "黑幕", "内幕", "黑平台", "传销",
            "套现", "洗钱", "非法集资", "庞氏骗局"
        ]

    def __init__(self, db: Session):
        self.db = db
        # 从配置读取阈值（作为默认值）
        self.negative_threshold = settings.alert_negative_threshold
        self.volume_threshold = settings.alert_volume_threshold
        self.sentiment_analyzer = SentimentAnalyzer()
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # 构建预警规则（使用配置的阈值作为默认）
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

    async def check_and_alert(self, keyword_id: str, hours: int = 24):
        """检查关键词并触发预警

        Args:
            keyword_id: 关键词ID
            hours: 检查最近多少小时的文章，默认24小时
        """
        # 获取监控主体及其预警配置
        keyword = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            logger.warning(f"Keyword {keyword_id} not found")
            return

        # 使用监控主体的预警配置，如果没有则使用默认配置
        alert_config = keyword.alert_config or DEFAULT_ALERT_CONFIG
        logger.info(f"检查预警: keyword={keyword.keyword}, hours={hours}, config={alert_config}")

        # 通过 ArticleKeyword 关联表获取与该关键词关联的文章
        time_ago = now_cst() - timedelta(hours=hours)

        # 查询文章ID列表
        article_links = self.db.query(ArticleKeyword).filter(
            ArticleKeyword.keyword_id == keyword_id,
            ArticleKeyword.matched_at >= time_ago
        ).all()

        article_ids = [ak.article_id for ak in article_links]

        if not article_ids:
            logger.info(f"Keyword {keyword.keyword} 没有最近{hours}小时的文章")
            return

        # 获取文章详情
        articles = self.db.query(Article).filter(
            Article.id.in_(article_ids)
        ).all()

        logger.info(f"Keyword {keyword.keyword} 最近{hours}小时有 {len(articles)} 篇文章")

        # 统计情感分布
        negative_count = sum(1 for a in articles if a.sentiment_label == 'negative')
        positive_count = sum(1 for a in articles if a.sentiment_label == 'positive')
        neutral_count = sum(1 for a in articles if a.sentiment_label == 'neutral')
        logger.info(f"情感分布: 负面={negative_count}, 正面={positive_count}, 中性={neutral_count}")

        # 检查负面情感爆发（如果启用）
        nb_config = alert_config.get('negative_burst', {})
        if nb_config.get('enabled', True):
            await self._check_negative_burst(articles, keyword, alert_config)
        else:
            logger.debug(f"负面爆发预警已禁用")

        # 检查敏感词命中（如果启用）
        sk_config = alert_config.get('sensitive_keyword', {})
        if sk_config.get('enabled', True):
            await self._check_sensitive_keywords(articles, keyword, alert_config)
        else:
            logger.debug(f"敏感词预警已禁用")

        # 检查讨论量激增（如果启用）
        vs_config = alert_config.get('volume_spike', {})
        if vs_config.get('enabled', True):
            await self._check_volume_spike(articles, keyword, alert_config, hours=hours)
        else:
            logger.debug(f"讨论量激增预警已禁用")

    async def _check_cooldown(self, keyword_id: str, alert_type: str) -> bool:
        """检查预警冷却期（同类型预警 1 小时内不重复发送）"""
        one_hour_ago = now_cst() - timedelta(hours=1)
        existing = self.db.query(Alert).filter(
            Alert.keyword_id == keyword_id,
            Alert.alert_type == alert_type,
            Alert.status == "pending",
            Alert.created_at >= one_hour_ago
        ).first()
        return existing is not None

    def _get_active_negative_keywords(self, alert_config: dict = None) -> List[str]:
        """获取活跃的负面敏感词列表"""
        # 优先使用自定义敏感词
        custom_keywords = alert_config.get('sensitive_keyword', {}).get('custom_keywords', [])
        if custom_keywords:
            return custom_keywords

        # 如果启用了全局敏感词库
        use_global = alert_config.get('sensitive_keyword', {}).get('use_global', True)
        if use_global:
            # 使用全局敏感词库
            _, negative_keywords = self._get_sentiment_keywords()
            if negative_keywords:
                return negative_keywords

        # 使用备用关键词
        return self._get_fallback_negative_keywords()

    async def _check_negative_burst(self, articles: List[Article], keyword: Keyword, alert_config: dict):
        """检查负面情感爆发"""
        alert_type = "negative_burst"

        # 从监控主体配置获取阈值
        nb_config = alert_config.get('negative_burst', {})
        threshold = nb_config.get('threshold', self.negative_threshold)
        min_count = nb_config.get('min_count', 3)

        # 检查冷却期
        if await self._check_cooldown(keyword.id, alert_type):
            logger.debug(f"Alert cooldown: {alert_type} for keyword {keyword.id}")
            return

        negative_count = sum(1 for a in articles if a.sentiment_score and a.sentiment_score < -0.3)

        # 检查是否满足最少文章数
        if len(articles) < min_count:
            logger.debug(f"文章数 {len(articles)} 少于最小阈值 {min_count}，跳过负面爆发预警")
            return

        ratio = negative_count / len(articles) if articles else 0
        logger.info(f"负面情感统计: 负面={negative_count}, 总数={len(articles)}, 比例={ratio:.2%}, 阈值={threshold:.2%}")

        if ratio >= threshold:
            await self._create_alert(
                keyword=keyword,
                alert_type=alert_type,
                alert_level="warning",
                message=f"1小时内负面情感占比 {ratio:.1%}，超过阈值 {threshold:.1%}",
                articles=[a.id for a in articles if a.sentiment_score and a.sentiment_score < -0.3][:5]
            )
        else:
            logger.debug(f"负面比例 {ratio:.2%} 未超过阈值 {threshold:.2%}")

    async def _check_sensitive_keywords(self, articles: List[Article], keyword: Keyword, alert_config: dict):
        """检查敏感词命中"""
        alert_type = "sensitive_keyword"

        # 检查最近已创建的敏感词预警，避免重复
        one_hour_ago = now_cst() - timedelta(hours=1)
        existing_alerts = self.db.query(Alert).filter(
            Alert.keyword_id == keyword.id,
            Alert.alert_type == alert_type,
            Alert.created_at >= one_hour_ago
        ).all()

        # 构建已预警的 article_id + word 组合集合
        alerted_combinations = set()
        for alert in existing_alerts:
            if alert.article_id and alert.message:
                # 从 message 中提取敏感词，格式: "检测到敏感词「xxx」"
                import re
                match = re.search(r'「(.+?)」', alert.message)
                if match:
                    word = match.group(1)
                    alerted_combinations.add((alert.article_id, word))

        # 获取敏感词列表
        sensitive_words = self._get_active_negative_keywords(alert_config)
        logger.info(f"检查敏感词，敏感词列表: {sensitive_words[:10]}...")

        alert_count = 0
        for article in articles:
            content = article.content or ""
            title = article.title or ""

            for word in sensitive_words:
                if word in content or word in title:
                    # 检查是否已经预警过（同一文章+同一敏感词）
                    combination = (article.id, word)
                    if combination in alerted_combinations:
                        logger.debug(f"Alert already exists for article {article.id} word '{word}'")
                        continue

                    await self._create_alert(
                        keyword=keyword,
                        alert_type=alert_type,
                        alert_level="critical",
                        message=f"检测到敏感词「{word}」",
                        articles=[article.id]
                    )
                    alert_count += 1
                    # 记录已预警的组合
                    alerted_combinations.add(combination)
                    break  # 每篇文章最多触发一次敏感词预警

        logger.info(f"敏感词预警创建: {alert_count} 条")

    async def _check_volume_spike(self, articles: List[Article], keyword: Keyword, alert_config: dict, hours: int = 24):
        """检查讨论量激增"""
        alert_type = "volume_spike"

        # 从监控主体配置获取阈值
        vs_config = alert_config.get('volume_spike', {})
        threshold = vs_config.get('threshold', self.volume_threshold)

        # 检查冷却期
        if await self._check_cooldown(keyword.id, alert_type):
            logger.debug(f"Alert cooldown: {alert_type} for keyword {keyword.id}")
            return

        # 获取前一个时间段的文章数作为基准
        current_start = now_cst() - timedelta(hours=hours)
        previous_start = now_cst() - timedelta(hours=hours * 2)

        previous_links = self.db.query(ArticleKeyword).filter(
            ArticleKeyword.keyword_id == keyword.id,
            ArticleKeyword.matched_at >= previous_start,
            ArticleKeyword.matched_at < current_start
        ).all()

        previous_count = len(previous_links)
        current_count = len(articles)

        logger.info(f"讨论量统计: 当前时段={current_count}, 前一时段={previous_count}")

        if previous_count > 0:
            growth = current_count / previous_count
            if growth >= threshold:
                await self._create_alert(
                    keyword=keyword,
                    alert_type=alert_type,
                    alert_level="info",
                    message=f"讨论量增长 {growth:.1f} 倍，当前 {current_count} 条",
                    articles=[a.id for a in articles[:10]]
                )
            else:
                logger.debug(f"讨论量增长 {growth:.1f} 未超过阈值 {threshold}")
        else:
            logger.debug(f"前一时段没有文章，无法比较讨论量")

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
            related_article_ids=json.dumps(articles) if articles else None,
            alert_type=alert_type,
            alert_level=alert_level,
            status="pending",
            message=message
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert created: [{alert_level}] {message}, articles={len(articles)}")

        # 发送通知 - 使用监控主体的通知配置
        alert_config = keyword.alert_config or DEFAULT_ALERT_CONFIG
        notifications = alert_config.get('notifications', ['email', 'webhook'])

        for action in notifications:
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
            logger.debug("Webhook URL not configured, skipping webhook notification")
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
            logger.debug("WeChat webhook not configured, skipping wechat notification")
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
