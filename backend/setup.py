"""
本地开发环境设置脚本
使用方法:
    python setup.py          # 安装依赖并创建 .env
    python run.py             # 启动开发服务器
"""
import os
import subprocess
import sys
from pathlib import Path


def create_env_file():
    """创建 .env 配置文件"""
    env_example = Path(__file__).parent / ".env.example"
    env_file = Path(__file__).parent / ".env"

    if not env_file.exists():
        print("📝 创建 .env 文件...")
        with open(env_example, "r", encoding="utf-8") as f:
            content = f.read()

        # 提示用户填写 API 密钥
        print("\n" + "=" * 50)
        print("⚠️  请编辑 .env 文件，填写你的 API 密钥:")
        print("   - BOCHA_API_KEY: 博查 API 密钥")
        print("   - TAVILY_API_KEY: Tavily API 密钥")
        print("   - ANSPIRE_API_KEY: Anspire API 密钥 (可选)")
        print("   - BAILIAN_API_KEY: 百炼 API 密钥")
        print("   - DATABASE_URL: 数据库连接 (默认: SQLite)")
        print("   - REDIS_URL: Redis 连接 (默认: localhost:6379)")
        print("\n" + "=" * 50 + "\n")

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        print("✅ .env 文件已存在")


def check_virtual_env():
    """检查是否在虚拟环境中"""
    return (
        hasattr(sys, 'real_prefix') and sys.real_prefix is not None
    ) or (
        hasattr(sys, 'base_prefix') and sys.base_prefix is not None
    ) or (
        os.environ.get('VIRTUAL_ENV') == 'true'
    )


def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖...")
    requirements = Path(__file__).parent / "requirements.txt"

    if not requirements.exists():
        print("❌ requirements.txt 不存在")
        sys.exit(1)

    # 检查是否需要创建虚拟环境
    if not check_virtual_env():
        print("⚠️  未检测到虚拟环境，正在创建...")
        venv_path = Path(__file__).parent / "venv"

        subprocess.run(
            [sys.executable, "-m", "venv", "create", str(venv_path)],
            check=True
        )
        print(f"✅ 虚拟环境已创建: {venv_path}")

        # 激活虚拟环境
        if sys.platform == "win32":
            venv_python = str(venv_path / "Scripts/python.exe")
            venv_pip = str(venv_path / "Scripts/pip.exe")
        else:
            venv_python = str(venv_path / "bin/python")
            venv_pip = str(venv_path / "bin/pip")

        # 使用虚拟环境的 pip 安装依赖
        subprocess.run(
            [venv_pip, "install", "-r", str(requirements)],
            check=True
        )
        print("✅ 依赖安装完成")
    else:
        print("✅ 检测到虚拟环境，正在安装依赖...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            check=True
        )
        print("✅ 依赖安装完成")


def create_sqlite_db():
    """为本地开发创建 SQLite 数据库"""
    db_url = "sqlite:///./owlwatch.db"
    env_file = Path(__file__).parent / ".env"

    # 读取现有 .env
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
            # 替换数据库 URL 为 SQLite
            content = content.replace(
                "postgresql://user:password@localhost:5432/owlwatch",
                db_url
            )
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        print(f"✅ 数据库已设置为 SQLite: {db_url}")
    else:
        print("❌ .env 文件不存在")
        sys.exit(1)


def main():
    print("\n" + "=" * 60)
    print("  OwlWatch 本地开发环境设置")
    print("=" * 60 + "\n")

    create_env_file()
    install_dependencies()
    create_sqlite_db()

    print("\n" + "=" * 60)
    print("✅ 环境设置完成!")
    print("=" * 60)
    print("\n📖 下一步:")
    print("   1. 编辑 .env 文件，填写你的 API 密钥")
    print("   2. 运行 python run.py 启动服务器")
    print("   3. 访问 http://localhost:8000 查看 API 文档")
    print("\n")


if __name__ == "__main__":
    main()
