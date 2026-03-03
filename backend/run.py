"""启动脚本"""
import sys
import asyncio
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Windows 上必须在使用 Playwright 之前设置事件循环策略
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
