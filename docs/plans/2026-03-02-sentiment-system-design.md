# OwlWatch 舆情监控系统设计方案

> 创建日期: 2026-03-02
> 状态: 已确认

---

## 一、需求总结

| 维度 | 选择 |
|------|------|
| 监控目标 | 综合需求（品牌 + 竞品 + 行业） |
| 数据渠道 | 全渠道均衡（国内 + 新闻 + 海外) |
| 实时性要求 | 准实时 + 定期报告 |
| 监控规模 | 中等规模（50-200 关键词） |
| 交付形式 | 一体化平台（Web + API + 多租户） |
| 界面风格 | 管理后台风格（Ant Design Pro） |
| 技术方案 | Python FastAPI + Vue3 + PostgreSQL |
| 预算范围 | 月成本 ≈¥1,500 |

---

## 二、技术栈
| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端框架 | FastAPI | 异步支持好，适合并发调用多个搜索 API |
| 前端框架 | Vue3 + Ant Design Vue | 管理后台首选，组件丰富 |
| 数据库 | PostgreSQL | 结构化数据存储，支持全文检索 |
| 缓存 | Redis | 任务队列、结果缓存、会话管理 |
| 定时任务 | APScheduler | Python 原生，与 FastAPI 集成简单 |
| 部署 | Docker Compose | 一键部署，环境一致 |
| AI 模型 | 百炼 qwen3-max | 情感分析、摘要生成、趋势预测 |

---

## 三、系统架构
```
┌─────────────────────────────────────────────────────────────────────┐
│                         OwlWatch 舆情监控系统                          │
├─────────────────────────────────────────────────────────────────────┤
│  前端层 (Vue3 + Ant Design Vue)                                      │
│  ├── 仪表盘 Dashboard    ├── 关键词管理    ├── 舆情列表              │
│  ├── 预警中心            ├── 报告中心      ├── 系统设置              │
├─────────────────────────────────────────────────────────────────────┤
│  API 网关                                       │
├─────────────────────────────────────────────────────────────────────┤
│  业务服务层                                            │
│  ├── KeywordService  ├── MonitorService   ├── AlertService           │
│  ├── ReportService    ├── AnalyzeService  ├── TenantService          │
├─────────────────────────────────────────────────────────────────────┤
│  数据采集层                                             │
│  ├── BochaCollector   ├── TavilyCollector  ├── AnspireCollector      │
├─────────────────────────────────────────────────────────────────────┤
│  AI 分析层 (百炼 qwen3-max)                                          │
│  ├── 情感分析          ├── 摘要生成        ├── 趋势预测               │
├─────────────────────────────────────────────────────────────────────┤
│  基础设施层                                                          │
│  ├── PostgreSQL       ├── Redis           ├── APScheduler            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 四、数据采集层设计
### 4.1 统一数据格式
```python
class CollectResult:
    """统一采集结果格式"""
    keyword: str           # 搜索关键词
    title: str             # 标题
    content: str           # 内容摘要
    url: str                # 原文链接
    source: str            # 来源平台 (微博/抖音/头条/网页)
    source_type: str       # API来源 (bocha/tavily/anspire)
    publish_time: datetime # 发布时间
    collect_time: datetime # 采集时间
    sentiment: float       # 情感分数 (-1 到 1，由 AI 填充)
    extra: dict            # 扩展字段(点赞数/评论数等)
```

### 4.2 三个 API 分工策略
| API | 调用场景 | 调用频率 | 返回数据 |
|-----|----------|----------|----------|
| **Bocha** | 国内社交媒体、新闻网站、实时热点 | 每 10 分钟 | 微博/抖音/头条/知乎等内容 |
| **Tavily** | 海外媒体、行业报告、国际新闻 | 每 30 分钟 | Twitter/新闻网站/博客等 |
| **Anspire** | 需深度爬取的页面（电商评论、论坛帖子) | 按需触发 | 完整页面内容、评论区 |

### 4.3 采集调度策略
- 高优先级关键词: Bocha 5分钟/次, Tavily 15分钟/次
- 中优先级关键词: Bocha 15分钟/次, Tavily 30分钟/次
- 低优先级关键词: Bocha 30分钟/次, Tavily 1小时/次
- Anspire 仅在发现重要舆情需深度分析时触发

```

---

## 五、AI 分析层设计
### 5.1 AI 分析能力矩阵
| 分析类型 | 功能说明 | 调用时机 | 输出 |
|----------|----------|----------|------|
| **情感分析** | 判断内容情感倾向 | 每条采集数据入库时 | 情感分数 (-1~1) + 情感标签 |
| **摘要生成** | 提取核心观点 | 批量处理/报告生成 | 50-100 字摘要 |
| **趋势分析** | 识别话题走向 | 生成报告时 | 趋势描述 + 关键事件 |
| **主题聚类** | 内容分类归档 | 每日定时任务 | 主题标签 + 相关话题 |
### 5.2 情感分析提示词模板
```
你是一个舆情分析专家。请分析以下内容的情感倾向。

【内容】
{content}

返回 JSON 格式:
{
    "score": 情感分数(-1到1),
    "label": "positive/neutral/negative",
    "reason": "判断理由(简短)
}
```
### 5.3 成本控制策略
- 批量合并: 多条内容合并为一次 API 调用
- 智能跳过: 已有相似内容不重复分析
- 缓存结果: 相同内容 24 小时内使用缓存
```

---

## 六、数据库设计
### 6.1 核心表结构
```sql
-- 租户/关键词表
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(100) not null,
    plan_type VARCHAR(20),          -- starter/pro/basic/pro
    max_keywords INT DEFAULT 100,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 关键词表
CREATE TABLE keywords (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    keyword VARCHAR(100) not null,
    priority VARCHAR(10) default 'medium',  -- high/medium/low
    platforms TEXT[],                 -- ['bocha', 'tavily', 'anspire']
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP
);

-- 舆情文章表
CREATE TABLE articles (
    id UUID PRIMARY KEY,
    keyword_id UUID REFERENCES keywords(id),
    title VARCHAR(500) not null,
    content TEXT,
    url VARCHAR(500) not null,
    source VARCHAR(100),              -- 微博/抖音/今日头条等
    source_api VARCHAR(20),          -- bocha/tavily/anspire
    sentiment_score FLOAT,                 -- -1 到 1
    sentiment_label VARCHAR(20),           -- positive/negative/neutral
    publish_time TIMESTAMP,
    collect_time TIMESTAMP,
    extra JSONB                             -- 扩展字段
);

-- 预警表
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    keyword_id UUID REFERENCES keywords(id),
    article_id UUID REFERENCES articles(id),
    alert_level VARCHAR(20),          -- info/warning/critical
    status VARCHAR(20) DEFAULT 'pending',    -- pending/handled/ignored
    created_at TIMESTAMP,
    handled_at TIMESTAMP
);

-- 报告表
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    title VARCHAR(200),
    content TEXT,
    report_type VARCHAR(20),          -- daily/weekly/monthly
    generated_at TIMESTAMP
);
```
### 6.2 索引设计
- `articles` 表: `(tenant_id, keyword_id, publish_time, sentiment_score)` 索引
- `keywords` 表: `(tenant_id)` 索引
- `alerts` 表: `(tenant_id, status, created_at)` 索引
```

---

## 七、模块目录结构
```
owlwatch/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py              # 配置管理
│   │   ├── database.py           # 数据库连接
│   │   └── dependencies.py     # 依赖注入
│   ├── models/                    # 数据模型
│   │   ├── tenant.py
│   │   ├── keyword.py
│   │   ├── article.py
│   │   ├── alert.py
│   │   └── report.py
│   ├── collectors/              # 数据采集
│   │   ├── base.py              # 采集器基类
│   │   ├── bocha.py
│   │   ├── tavily.py
│   │   └── anspire.py
│   ├── analyzers/              # AI 分析
│   │   ├── sentiment.py
│   │   ├── summary.py
│   │   └── trend.py
│   ├── services/              # 业务服务
│   │   ├── keyword_service.py
│   │   ├── monitor_service.py
│   │   ├── alert_service.py
│   │   └── report_service.py
│   ├── schedulers/              # 定时任务
│   │   └── monitor_scheduler.py
│   └── api/                    # API 路由
│       ├── v1/
│       │   ├── auth.py
│       │   ├── keywords/
│       │   ├── articles/
│       │   ├── alerts/
│       │   └── reports/
│       └── internal/             # 内部 API
│           └── collect/
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── dashboard/
│   │   │   ├── keywords/
│   │   │   ├── articles/
│   │   │   ├── alerts/
│   │   │   └── reports/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── charts/
│   │   │   └── common/
│   │   ├── stores/
│   │   ├── api/
│   │   └── utils/
│   └── package.json
├── docker-compose.yml
└── docs/
    └── plans/
        └── 2026-03-02-sentiment-system-design.md
```

---

## 八、API 接口设计
### 8.1 核心业务流程
```
创建关键词 → 定时采集任务 → 数据采集 → AI分析 → 存储 → 预警判断 → 通知推送
```
### 8.2 RESTful API 列表
| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/keywords` | 创建监控关键词 |
| GET | `/api/v1/keywords` | 获取关键词列表 |
| PUT | `/api/v1/keywords/{id}` | 更新关键词配置 |
| DELETE | `/api/v1/keywords/{id}` | 删除关键词 |
| GET | `/api/v1/articles` | 获取舆情列表（支持筛选/分页） |
| GET | `/api/v1/articles/{id}` | 获取舆情详情 |
| GET | `/api/v1/alerts` | 获取预警列表 |
| PUT | `/api/v1/alerts/{id}/handle` | 处理预警 |
| POST | `/api/v1/reports/generate` | 生成分析报告 |
| GET | `/api/v1/reports` | 获取报告列表 |
| GET | `/api/v1/dashboard/stats` | 获取仪表盘统计数据 |
### 8.3 认证方式
- Bearer Token (JWT)
```

---

## 九、预警机制设计
### 9.1 预警规则类型
| 规则类型 | 触发条件 | 严重程度 | 通知方式 |
|----------|----------|----------|----------|
| **负面情感爆发** | 1小时内负面情感占比 > 30% | ⚠️ Warning | 邮件 + Webhook |
| **敏感词命中** | 内容包含预设敏感词（如"投诉"/"维权"） | 🔴 Critical | 短信 + 企微 |
| **高热度话题** | 1小时内讨论量增长 > 200% | ℹ️ Info | 邮件 |
| **信源异常** | 同一来源大量出现负面内容 | ⚠️ Warning | 邮件 + Webhook |
| **竞品动态** | 竞品出现重大新闻 | ℹ️ Info | 邮件 |
### 9.2 通知渠道
- **邮件**: SMTP 服务（如阿里云邮件推送)
- **Webhook**: 自定义 HTTP 回调
- **企业微信/钉钉**: 机器人 Webhook
- **短信**: 阿里云/腾讯云短信服务（仅 Critical 级别)
### 9.3 预警冷却时间
- Info: 24 小时未处理自动归档
- Warning: 72 小时未处理升级为 Critical
- 手动标记"已处理"后关闭
```

---

## 十、成本估算
### 10.1 月度成本（中等规模: 100个关键词）
| 项目 | 用量 | 单价 | 月成本 |
|------|------|------|--------|
| **Bocha API** | ~15万次/月 | ¥0.0036/次 | **¥540** |
| **Tavily API** | ~3万次/月 | ¥0.01/次 | **¥300** |
| **Anspire API** | ~0.5万次/月 | ¥0.05/次 | **¥250** |
| **百炼 qwen3-max** | ~100万 tokens | ¥0.002/千tokens | **¥200** |
| **服务器** | 2核4G 云服务器 | - | **¥200** |
| **合计** | | | **≈ ¥1,490/月** |

> 💡 对比传统舆情系统（年费 3-10 万），成本降低 **85%+**

---

## 十一、实施路线图
### Week 1: 基础框架
- [ ] 项目初始化 + 目录结构
- [ ] 数据库设计 + ORM 模型
- [ ] 基础 API 框架
- [ ] 配置系统

### Week 2: 核心功能
- [ ] 三个 Collector 实现
- [ ] AI Analyzer 集成
- [ ] 采集调度器
- [ ] 预警服务

### Week 3: 前端 + 集成
- [ ] Vue3 前端框架
- [ ] 仪表盘 + 管理界面
- [ ] 预警通知集成
- [ ] 报告生成功能

### Week 4: 优化 + 部署
- [ ] 性能优化
- [ ] Docker 部署
- [ ] 监控告警
- [ ] 文档完善

---

## 十二、后续扩展方向
- [ ] 卖网链接过滤（可扩展）
- [ ] 社交媒体评论监控（按需）
- [ ] 语音/视频舆情分析
- [ ] 知识图谱可视化
