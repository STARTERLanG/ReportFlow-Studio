---
trigger: always_on
---


# Python 代码风格规范

## 库导入规范
- 使用绝对路径导入，严禁使用相对路径

## 代码质量与格式化 (Ruff)
- **命令**:
    - 检查并修复 Lint 问题: `uv run ruff check . --fix`
    - 格式化代码: `uv run ruff format .`
- **配置策略**:
    - 优先修改代码以符合规范。
    - 针对框架特性（如 FastAPI/Typer 的 `Depends`/`Option` 默认值），在 `pyproject.toml` 中配置 `extend-per-file-ignores` 忽略 `B008` 等规则，而非在代码中逐行添加 `# noqa`。
    - 脚本文件可忽略导入位置限制 (`E402`)。

## 类型注解
- 使用现代类型注解语法：`X | Y`，而不是 `Optional[X]` 或 `Union[X]`
- 为函数参数和返回值添加类型注解

## 异常处理
- **严禁裸捕获**: 禁止使用 `except:`，必须指定异常类型（如 `except Exception:` 或更具体的异常），防止捕获 `SystemExit` 等系统信号。
- **保留异常链**: 重新抛出异常时，必须使用 `raise ... from e`，保留原始错误堆栈以便调试。
```python
try:
    # 业务逻辑
    ...
except ValueError as e:
    # 记录日志并保留异常链
    logger.exception("数据校验失败")
    raise HTTPException(status_code=400, detail="无效输入") from e
```

## 数据校验
- 使用 Pydantic 进行数据校验
- 定义清晰的数据模型和验证规则


# Dify 规范与错题本维护
- 在与用户交互过程中，如果遇到 Dify YAML 结构、导入、渲染等相关问题，必须在 `docs/dify_error_log.md` 中记录“问题描述”、“分析过程”。
- **重要**：只有当“解决办法”经过用户实际导入并运行验证通过后，方可填入错题本的“解决办法”栏目。
- **按需注入原则**：在为 LLM 节点配置变量引用时，必须遵循“最小必要原则”，仅注入该节点任务所需的上游变量，严禁全量注入以防止污染 LLM 上下文。

## Dify DSL 架构规范 (v0.5.x Legacy)
为了避免 Dify 前端崩溃 (Sentry Error) 和 CSP 拦截，必须严格遵守以下 **Builder 模式** 规范：

### 1. 核心架构：Blueprint + Builder
- **Architect (LLM)**: 仅负责生成精简的 `Blueprint JSON`，不直接生成 YAML。
- **Builder (Python)**: 负责将 JSON 编译为 YAML。变量翻译、坐标计算、ID 生成、Handle 映射全部由 Python 硬编码实现。

### 2. 节点关键避坑指南
- **If-Else (二元限制)**: 仅使用 `true/false` 两个出口。`conditions` 列表中的首个条件 ID 必须设为字符串 `"true"`。不支持 `cases` 嵌套结构（旧版兼容性）。
- **Code (输出字典)**: `outputs` 字段**必须是字典 (Dict)** 而非列表 (List)。示例：`{"result": {"type": "string", "children": null}}`。
- **Template (变量显式注册)**: 凡是在模板内容中使用的变量，**必须**在 `variables` 映射列表中显式定义，否则会导致渲染异常。
- **Edge (Handle 标准化)**: 非分支节点 `sourceHandle` 统一为 `"source"`，`targetHandle` 统一为 `"target"`。If-Else 节点的 `sourceHandle` 必须严格对应 `"true"` 或 `"false"`。
- **Start (UI 完整性)**: 必须包含 `label`, `type: text-input`, `required`, `options` 等前端渲染字段。

### 3. Prompt 编写禁忌
- **大括号转义**: 在 Prompt Template 中使用 JSON 示例或 Dify 变量语法时，**必须使用双大括号 `{{ }}`**，否则会触发 Python f-string 或 LangChain 变量解析错误。

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