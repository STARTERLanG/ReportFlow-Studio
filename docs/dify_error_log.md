# Dify 工作流 YAML 开发错题本 (Error Log)

本文件记录在生成 Dify 0.5.0+ DSL (YAML) 过程中遇到的结构化校验错误、前端渲染崩溃问题及其对应的深度分析与解决方案。

---

## 1. 字符串类型错误 (!!str 标签冲突)

- **问题描述**：导入时 Dify 提示字符串类型错误或解析异常。
- **分析过程**：PyYAML 默认在处理包含换行符的长文本时，可能会自动添加 `!!str` 显式类型标签，或者对短标题使用了不必要的块样式 `|`。Dify 的后端校验器对带有显式 YAML 标签的 DSL 兼容性较差。
- **解决办法**：
    - 改进 `str_presenter` 呈现器，仅对包含 `\n` 的文本使用块样式 `|`。
    - 强制使用 `tag:yaml.org,2002:str` 确保输出纯净字符串，不带自定义标签。

## 2. 根节点字典校验失败 ('str' object has no attribute 'get')

- **问题描述**：导入失败，错误信息为 `'str' object has no attribute 'get'`。
- **分析过程**：Dify 0.5.0 要求根节点的 `app` 字段必须是一个字典（包含 `name`, `mode` 等），而 AI 生成时常将其简化为字符串。
- **解决办法**：
    - 在 `assembler` 逻辑中强制将 `app` 定义为包含 `name`, `mode`, `icon` 等字段的固定字典结构。

## 3. 节点类型命名不合法 ('variable_assigner' is not a valid NodeType)

- **问题描述**：提示 `'variable_assigner' is not a valid NodeType`。
- **分析过程**：Dify 的节点类型标识符（`NodeType`）严格遵循“连字符”命名法（Kebab-case），而非“下划线”命名法（Snake-case）。例如：`variable-assigner` 而非 `variable_assigner`。
- **解决办法**：
    - 在 `YAML_ARCHITECT_PROMPT` 中明确列出合法节点类型白名单。
    - 在代码层增加 `replacements` 字典，自动将下划线关键词转换为连字符。

## 4. 前端渲染崩溃 (Sentry / Client-side Exception)

- **问题描述**：导入成功但打开白屏，报错 `a client-side exception has occurred`。
- **分析过程**：这是最高频的错误。前端渲染引擎（ReactFlow）对图的完整性有极高要求。
    - **Edge ID 缺失**：每条连线必须有唯一 ID。
    - **Handle 缺失**：连线必须指定 `sourceHandle` 和 `targetHandle`（通常为 `source` 和 `target`）。
    - **变量引用错误**：在 `template-transform` 或 `end` 节点中，必须使用 `value_selector: ["node_id", "var"]` 列表，而非 `{{#node_id.var#}}` 字符串。
    - **防御性配置缺失**：LLM 节点缺少 `vision`, `memory` 等默认配置块会导致前端解析对象时读取到 `undefined`。
- **解决办法**：
    - **模版化重构**：不再允许 AI 自由生成图骨架，改为在代码中使用“黄金模版”生成 `nodes` 和 `edges`，确保所有坐标、Handle 和 Selector 100% 合规。

## 6. LLM 节点上游数据引用缺失

- **问题描述**：LLM 节点虽然连线正确，但 Prompt 中无法直接使用上游数据，或者导入后提示变量未定义。
- **分析过程**：Dify 的 LLM 节点需要在 `data.variables` 中显式定义变量映射（`variable` -> `value_selector`），才能在 `prompt_template` 中通过 `{{#variable#}}` 引用。仅有连线是不够的。
- **解决办法**：
    - 在 `assembler` 中，为每个 LLM 节点按需添加 `variables` 数组（遵循最小必要原则），将上游节点（如 `start`）的输出映射为本地变量名。
    - **分层提示词习惯**：将核心指令置于 `system` 角色，将数据引用置于 `user` 角色，符合专业开发习惯。

## 7. 代码节点 Python 格式不合规

- **问题描述**：代码节点运行报错或导入后代码逻辑无法识别。
- **分析过程**：Dify 的代码节点（Python3）有严格的入口函数要求：必须定义 `def main(...)`，必须包含类型注解，且必须返回一个字典。
- **解决办法 (待验证)**：
    - 强制使用模板生成代码：`def main(arg1: str, arg2: str): return {"result": ...}`。
    - 确保 `data.outputs` 中定义的键值与 `main` 函数返回的字典键值严格对应。

## 8. 变量引用语法规范 (Absolute Path)

- **问题描述**：LLM 节点的 Prompt 无法正确解析变量，或者导入后引用的数据为空。
- **分析过程**：在 Dify 0.5.0+ 的 `prompt_template` 中，直接在文本中引用变量时，标准且最稳健的方式是使用绝对路径语法：`{{#node_id.variable_name#}}`，而非仅使用本地映射的别名。
- **解决办法**：
    - 在生成的 `user` 角色提示词中，强制使用 `{{#start.input_text#}}` 这种包含起始节点 ID 的完整语法，确保渲染引擎能够准确定位数据源。

## 10. YAML 解析语法冲突 (ParserError / f-string Conflict)

- **问题描述**：生成失败（LangChain 报错变量未定义）或 Assembler 组装时报 YAML 语法错误（found character '%'...）。
- **分析过程**：AI 架构师生成的 `expression` 或 `template` 经常包含 `{% %}` 或 `{{ }}`，这会与 LangChain 的 `ChatPromptTemplate` 发生变量识别冲突。且在正则还原后，由于引号嵌套问题，PyYAML 经常将 `{{#...#}}` 误认为非法的流式映射。
- **解决办法**：
    - **提示词脱敏**：在 `YAML_ARCHITECT_PROMPT` 中严禁使用花括号，强制使用 `__NODE_ID.VAR__` 占位符。
    - **解析前转换**：在 `safe_load` 之前，将占位符转换为绝对安全的中间字符串（如 `SAFE_REF_START_...`），避免触发 YAML 解析器对 `%` 或 `{` 的敏感逻辑。
    - **解析后递归还原**：在得到 Python 字典对象后，递归遍历整个树，将中间字符串还原为 Dify 标准的 `{{#...#}}` 语法。这种方式由 `yaml.dump` 自动处理所有引号转义，100% 稳健。

---

## 5. 网络授权与代理干扰 (401 Unauthorized)

- **问题描述**：生成过程中调用 LLM 或 RAG 失败，报 401 错误。
- **分析过程**：
    - **变量污染**：Shell 环境中残留的 `OPENAI_BASE_URL` 覆盖了 `.env`。
    - **代理冲突**：VPN 代理导致请求被错误转发至非预期地址（如阿里云）。
- **解决办法**：
    - 使用 `load_dotenv(override=True)` 强制覆盖。
    - 同时强制确保每个节点的顶级字段 `type` 为 `custom`。

## 11. 节点类型层级冲突 ('custom' is not a valid NodeType)

- **问题描述**：导入失败，报 `'custom' is not a valid NodeType`。
- **分析过程**：这是由于对 Dify 0.5.0 节点结构的误解。在 DSL 中，每个节点的顶级字段 `type` 必须固定为 `custom`（这是 Dify 前端渲染引擎的硬性要求）；但该节点具体的业务类型（如 `start`, `llm`, `end`）必须放在 `data.type` 字段中。如果将 `custom` 错误地填入 `data.type`，后端校验将失败。
- **解决办法**：
    - 在 `assembler` 中建立类型识别机制：
        1. 提取节点的真实功能类型（从 `data.type` 或 AI 生成的旧 `type` 字段）。
        2. 强制将顶级 `node["type"]` 设为 `custom`。
        3. 强制将提取到的真实功能类型（确保不是 `custom`）填入 `data["type"]`。
