import argparse
import sys

from backend.app.logger import logger
from backend.app.utils.dsl_validator import DifyDSLValidator


def main():
    parser = argparse.ArgumentParser(description="Dify DSL 校验工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="DSL YAML 文件路径")
    group.add_argument("-s", "--string", help="DSL YAML 字符串内容")

    args = parser.parse_args()

    validator = DifyDSLValidator()

    if args.file:
        logger.info(f"正在从文件校验: {args.file}")
        if not validator.load_from_file(args.file):
            sys.exit(1)
    else:
        logger.info("正在从字符串校验...")
        if not validator.load_from_string(args.string):
            sys.exit(1)

    success, errors = validator.validate()

    if success:
        logger.info("🎉 校验成功: DSL 符合 Dify 规范")
    else:
        logger.error("❌ 校验失败:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
