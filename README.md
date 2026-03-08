# OwlWatch 舆情监控系统

基于 **Bocha**、**Tavily**、**Anspire**、**百度**、**Bing** 多源数据采集和 **HanLP + Cemotion** 本地情感分析的智能舆情监控平台。

## ✨ 功能特性

- 🔍 **多源数据采集** - 整合 Bocha(国内)、Tavily(海外)、Anspire(深度爬取)、百度、Bing 多个数据源
- 📡 **RSS 订阅监控** - 支持 RSS/Atom Feed 自动解析，实时监控目标站点
- 🤖 **AI 智能分析** - 基于 HanLP + Cemotion 本地情感分析，支持自定义情感关键词
- ⚡ **异步任务队列** - Redis 队列驱动的异步情感分析，采集与分析解耦
- 🚨 **智能预警** - 支持负面情感爆发、敏感词命中、讨论量激增等多维度预警
- 📊 **可视化大屏** - Vue3 + Ant Design Vue 管理后台（赛博朋克风格）
- 🏢 **多租户支持** - 支持多租户隔离的企业级架构
- 🐳 **Docker 一键部署** - 完整的 Docker Compose 编排

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + APScheduler |
| 前端 | Vue3 + Ant Design Vue + ECharts |
| 数据库 | PostgreSQL + Redis |
| AI | HanLP + Cemotion (本地情感分析) |
| 部署 | Docker Compose |

## 📁 项目结构

```
OwlWatch/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── collectors/      # 数据采集器 (Bocha, Tavily, Anspire, Baidu, Bing)
│   │   ├── analyzers/       # AI 分析器 (情感分析)
│   │   ├── services/        # 业务服务 (Redis 队列、预警)
│   │   ├── schedulers/      # 定时任务 (RSS 采集、情感分析 Worker)
│   │   ├── models/          # 数据模型
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   └── main.py          # 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/                 # 前端应用 (Vue3 + Ant Design)
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── docs/
    └── plans/               # 设计文档
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 复制环境变量配置
cp backend/.env.example backend/.env

# 编辑 .env 文件，填入你的 API 密钥
```

### 2. 获取 API 密钥

| API | 用途 | 获取地址 |
|-----|------|----------|
| Bocha | 国内搜索 | https://open.bochaai.com |
| Tavily | 海外搜索 | https://tavily.com |
| Anspire | 深度爬取 | https://anspire.io |
| 百炼 | 摘要/趋势分析 (可选) | https://bailian.console.aliyun.com |

### 3. 启动服务

**Docker 部署（推荐）**

```bash
# 一键启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f
```

**本地开发模式**

```bash
# 后端
cd backend
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3080 |
| API 文档 | http://localhost:3080/api/v1/docs |
| 健康检查 | http://localhost:3080/api/v1/health |

**默认登录账号**
- 用户名: `admin`
- 密码: `admin123`

## 📡 API 接口

### 认证
```
POST   /api/v1/auth/login       # 登录
POST   /api/v1/auth/register    # 注册
```

### 关键词管理
```
POST   /api/v1/keywords          # 创建关键词
GET    /api/v1/keywords          # 获取关键词列表
PUT    /api/v1/keywords/{id}     # 更新关键词
DELETE /api/v1/keywords/{id}     # 删除关键词
```

### 舆情数据
```
GET    /api/v1/articles          # 获取舆情列表
GET    /api/v1/articles/{id}     # 获取舆情详情
```

### 采集任务
```
POST   /api/v1/collect/trigger   # 触发采集任务
GET    /api/v1/collect/status/{task_id}  # 查询任务状态
GET    /api/v1/collect/running   # 获取运行中的任务
```

### 预警管理
```
GET    /api/v1/alerts            # 获取预警列表
PUT    /api/v1/alerts/{id}/handle # 处理预警
```

### RSS 订阅
```
GET    /api/v1/rss               # 获取 RSS 订阅列表
POST   /api/v1/rss               # 添加 RSS 订阅
PUT    /api/v1/rss/{id}          # 更新 RSS 订阅
DELETE /api/v1/rss/{id}          # 删除 RSS 订阅
POST   /api/v1/rss/{id}/fetch    # 手动抓取单个订阅
```

### 情感关键词
```
GET    /api/v1/sentiment-keywords       # 获取情感关键词列表
POST   /api/v1/sentiment-keywords       # 添加情感关键词
DELETE /api/v1/sentiment-keywords/{id}  # 删除情感关键词
GET    /api/v1/sentiment-keywords/categories  # 获取关键词分类
```

### 报告生成
```
POST   /api/v1/reports/generate  # 生成报告
GET    /api/v1/reports           # 获取报告列表
```

## 🐳 Docker 配置说明

服务编排包含以下容器：

| 容器 | 端口 | 说明 |
|------|------|------|
| frontend | 3080:80 | Nginx 静态文件服务 |
| backend | 8000 | FastAPI 应用 (2 workers) |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis (任务队列 + 状态存储) |

**环境变量配置** (backend/.env)

```bash
# 数据库
DATABASE_URL=postgresql://owlwatch:password@postgres:5432/owlwatch
REDIS_URL=redis://redis:6379/0

# API 密钥
BOCHA_API_KEY=your_bocha_key
TAVILY_API_KEY=your_tavily_key
ANSPIRE_API_KEY=your_anspire_key
BAILIAN_API_KEY=your_bailian_key

# JWT
JWT_SECRET=your_jwt_secret_at_least_32_chars
```

## 💰 成本估算

基于中等规模 (100 个关键词) 的月度成本估算:

| 项目 | 月成本 | 说明 |
|------|--------|------|
| Bocha API | ¥540 | 国内搜索 |
| Tavily API | ¥300 | 海外搜索 |
| Anspire API | ¥250 | 深度爬取 |
| 百炼 AI | ¥100 | 摘要/趋势分析 (可选) |
| 服务器 | ¥200 | 云服务器 |
| **合计** | **≈ ¥1,390** | |

> 本地情感分析 (HanLP + Cemotion) 无需 API 费用，对比传统舆情系统 (年费 3-10 万)，成本降低 **85%+**

## 📈 开发路线

### Week 1: 基础框架 ✅
- [x] 项目初始化 + 目录结构
- [x] 数据库设计 + ORM 模型
- [x] 基础 API 框架
- [x] 配置系统

### Week 2: 核心功能 ✅
- [x] 五个 Collector 实现 (Bocha, Tavily, Anspire, Baidu, Bing)
- [x] AI Analyzer 集成
- [x] 采集调度器
- [x] 预警服务

### Week 3: 前端 + 集成 ✅
- [x] Vue3 前端框架
- [x] 仪表盘 + 管理界面（赛博朋克风格）
- [x] 预警通知集成
- [x] 报告生成功能

### Week 4: 优化 + 部署 ✅
- [x] 性能优化
- [x] Docker 部署配置
- [x] Redis 任务状态存储
- [x] 文档完善

### Week 5: RSS + 情感分析增强 ✅
- [x] RSS/Atom Feed 订阅功能
- [x] HanLP + Cemotion 本地情感分析
- [x] 情感关键词管理（正面/负面）
- [x] Redis 异步情感分析队列
- [x] 采集与情感分析解耦架构

## 📄 License

MIT License
