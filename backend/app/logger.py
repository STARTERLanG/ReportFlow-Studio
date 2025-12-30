import logging
import sys

# 配置日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger(
    name: str = "ReportFlow-Studio", level: int = logging.INFO
) -> logging.Logger:
    """
    配置并返回一个 Logger 实例。
    """
    logger = logging.getLogger(name)

    # 如果 logger 已经有 handler，说明已经被配置过，直接返回
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    return logger


# 全局 Logger 实例
logger = setup_logger()


def set_debug_mode(enabled: bool):
    """切换 Debug 模式"""
    level = logging.DEBUG if enabled else logging.INFO
    logger.setLevel(level)
    # 同时设置 LangChain 的日志
    if enabled:
        from langchain.globals import set_debug, set_verbose

        set_debug(True)
        set_verbose(True)
