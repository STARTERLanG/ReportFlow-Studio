import os
import subprocess
import sys


def main():
    """启动 ReportFlow Studio 服务"""
    print("=" * 50)
    print("🚀 ReportFlow Studio 正在启动...")
    print("=" * 50)

    # 检查 .env 文件
    if not os.path.exists(".env"):
        print("⚠️ 警告: 未找到 .env 文件，请参考 .env.example 进行配置。")

    # 设置工作目录
    cwd = os.path.dirname(os.path.abspath(__file__))

    # 运行命令
    # 使用 uv run 确保在虚拟环境中运行
    try:
        print("\n👉 访问地址: http://localhost:8000")
        print("👉 API 文档: http://localhost:8000/docs\n")

        # 启动主服务
        subprocess.run(["uv", "run", "python", "app/server/main.py"], cwd=cwd)
    except KeyboardInterrupt:
        print("\n👋 服务已停止。")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
