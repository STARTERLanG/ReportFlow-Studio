---
trigger: always_on
---


# Python 代码风格规范

## 库导入规范
- 使用绝对路径导入，严禁使用相对路径

## 代码格式化
- 使用 Ruff 工具进行代码格式化
- 遵循最新的 PEP8 规范，根据 Ruff 的官方代码风格编写代码
- 使用 `uv run ruff format .` 格式化代码

## 类型注解
- 使用现代类型注解语法：`X | Y`，而不是 `Optional[X]` 或 `Union[X]`
- 为函数参数和返回值添加类型注解

## 异常处理
在复杂逻辑或需要数据校验的代码块中，主动捕获异常：
```python
try:
    # 业务逻辑
    ...
except Exception as e:
    logger.exception("操作失败", exc_info=e)
```

## 数据校验
- 使用 Pydantic 进行数据校验
- 定义清晰的数据模型和验证规则


# Dify 规范与错题本维护
- 在与用户交互过程中，如果遇到 Dify YAML 结构、导入、渲染等相关问题，必须在 `docs/dify_error_log.md` 中记录“问题描述”、“分析过程”。
- **重要**：只有当“解决办法”经过用户实际导入并运行验证通过后，方可填入错题本的“解决办法”栏目。
- **按需注入原则**：在为 LLM 节点配置变量引用时，必须遵循“最小必要原则”，仅注入该节点任务所需的上游变量，严禁全量注入以防止污染 LLM 上下文。

# 日志工具使用规范

## 日志配置
- 日志配置在 logger.py
- 日志适配器在 log_adapter.py
- 应用启动时调用 `setup_logging()` 初始化日志系统

## 日志使用示例
```python
from app.core.log_adapter import logger

logger.info("操作描述")
```

## 日志最佳实践
- 使用结构化日志，通过关键字参数传递变量
- 提供有意义的日志描述
- 在异常处理中使用 `logger.exception()` 记录完整的异常信息
- 避免在日志中记录敏感信息（如密码、token 等）