from collections.abc import Awaitable, Callable
from contextvars import ContextVar

# 定义全局上下文变量用于存储回调函数
# 回调签名: async def callback(message: str) -> None
status_callback_var: ContextVar[Callable[[str], Awaitable[None]] | None] = ContextVar("status_callback", default=None)
