# OwlWatch 舆情监控系统

基于 **Tavily**、**Anspire**、**Bocha** 三个搜索 API 和 **百炼 qwen3-max** 大模型的智能舆情监控平台。

## ✨ 功能特性

- 🔍 **多源数据采集** - 整合 Bocha(国内)、Tavily(海外)、Anspire(深度爬取) 三个 API
- 🤖 **AI 智能分析** - 基于百炼 qwen3-max 实现情感分析、摘要生成、趋势预测
- 🚨 **智能预警** - 支持负面情感爆发、敏感词命中、讨论量激增等多维度预警
- 📊 **可视化大屏** - Vue3 + Ant Design Vue 管理后台
- 🏢 **多租户支持** - 支持多租户隔离的企业级架构

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + APScheduler |
| 前端 | Vue3 + Ant Design Vue + ECharts |
| 数据库 | PostgreSQL + Redis |
| AI | 百炼 qwen3-max |
| 部署 | Docker Compose |

## 📁 项目结构

```
OwlWatch/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── collectors/      # 数据采集器
│   │   ├── analyzers/       # AI 分析器
│   │   ├── services/        # 业务服务
│   │   ├── schedulers/       # 定时任务
│   │   ├── models/          # 数据模型
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   └── main.py          # 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/                 # 前端应用 (待开发)
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
| 百炼 | AI 分析 | https://bailian.console.aliyun.com |

### 3. 启动服务

```bash
# 使用 Docker Compose 启动
docker-compose up -d

# 或本地开发模式
cd backend
pip install -r requirements.txt
python run.py
```

### 4. 访问服务

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📡 API 接口

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

### 预警管理
```
GET    /api/v1/alerts             # 获取预警列表
PUT    /api/v1/alerts/{id}/handle # 处理预警
```

### 报告生成
```
POST   /api/v1/reports/generate  # 生成报告
GET    /api/v1/reports            # 获取报告列表
```

## 💰 成本估算

基于中等规模 (100 个关键词) 的月度成本估算:

| 项目 | 月成本 |
|------|--------|
| Bocha API | ¥540 |
| Tavily API | ¥300 |
| Anspire API | ¥250 |
| 百炼 AI | ¥200 |
| 服务器 | ¥200 |
| **合计** | **≈ ¥1,490** |

> 对比传统舆情系统 (年费 3-10 万)，成本降低 **85%+**

## 📈 开发路线

### Week 1: 基础框架 ✅
- [x] 项目初始化 + 目录结构
- [x] 数据库设计 + ORM 模型
- [x] 基础 API 框架
- [x] 配置系统

### Week 2: 核心功能 ✅
- [x] 三个 Collector 实现
- [x] AI Analyzer 集成
- [x] 采集调度器
- [x] 预警服务

### Week 3: 前端 + 集成 (待开发)
- [ ] Vue3 前端框架
- [ ] 仪表盘 + 管理界面
- [ ] 预警通知集成
- [ ] 报告生成功能

### Week 4: 优化 + 部署 (待开发)
- [ ] 性能优化
- [ ] Docker 部署
- [ ] 监控告警
- [ ] 文档完善

## 📄 License

MIT License
