#!/bin/bash
set -e

echo "=== OwlWatch Backend Starting ==="
echo "Environment: ${APP_ENV:-development}"

# 调试：检查关键环境变量
echo "Checking environment variables..."
echo "  DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "  REDIS_URL: ${REDIS_URL}"
echo "  JWT_SECRET: ${JWT_SECRET:0:8}... (masked)"
echo "  INITIAL_ADMIN_USERNAME: ${INITIAL_ADMIN_USERNAME}"
echo "  APP_ENV: ${APP_ENV}"

# 等待数据库就绪
echo "Waiting for database..."
sleep 3

# 初始化数据库
echo "Initializing database..."
python -c "
import sys
sys.path.insert(0, '/app')
from app.scripts.init_db import init_db
init_db()
"

if [ $? -eq 0 ]; then
    echo "✓ Database initialization completed!"
else
    echo "⚠ Database initialization had issues, but continuing..."
fi

echo "Starting application..."

# 启动应用
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
