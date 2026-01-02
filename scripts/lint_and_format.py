import subprocess
from pathlib import Path


def run_command(command: list[str], description: str):
    print(f"--- {description} ---")
    try:
        result = subprocess.run(command, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 成功\n")
        else:
            print(f"⚠️ {description} 结束 (返回码: {result.returncode})\n")
    except Exception as e:
        print(f"❌ 执行 {description} 时出错: {e}\n")


def main():
    # 切换到项目根目录执行
    root_dir = Path(__file__).parent.parent

    print("=" * 40)
    print("🧹 ReportFlow Studio 代码清理工具")
    print("=" * 40 + "\n")

    # 1. 执行 Lint 检查并自动修复
    run_command(["uv", "run", "ruff", "check", ".", "--fix"], "正在执行 Ruff Check & Fix (修复 Lint 和 Import 排序)")

    # 2. 执行格式化
    run_command(["uv", "run", "ruff", "format", "."], "正在执行 Ruff Format (代码格式化)")

    print("✨ 代码清理完成！")


if __name__ == "__main__":
    main()
