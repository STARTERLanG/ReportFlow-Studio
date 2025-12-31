import os

from app.server.logger import logger


def configure_network_settings():
    """
    完全禁用当前进程的代理设置，确保所有请求直连。
    """
    proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]

    removed = []
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
            removed.append(var)

    # 同时设置 NO_PROXY 为通配符作为双重保险
    os.environ["NO_PROXY"] = "*"

    if removed:
        logger.info(f"[Network] 已清理代理环境变量: {', '.join(removed)}，并设置 NO_PROXY='*'")
    else:
        logger.info("[Network] 未检测到代理环境变量，已设置 NO_PROXY='*' 确保直连")
