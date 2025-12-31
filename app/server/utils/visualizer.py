import yaml


def dify_yaml_to_mermaid(yaml_str: str) -> str:
    """
    将 Dify YAML 转换为 Mermaid 流程图语法
    """
    try:
        data = yaml.safe_load(yaml_str)
        if not data or "workflow" not in data:
            return "graph TD\n  error[无法解析工作流结构]"

        nodes = data["workflow"]["graph"]["nodes"]
        edges = data["workflow"]["graph"]["edges"]

        mermaid = ["graph TD"]

        # 1. 定义节点样式
        for node in nodes:
            node_id = str(node["id"])
            title = str(node["data"].get("title", node_id))
            node_type = str(node["data"].get("type", ""))

            # 清理标题中的特殊字符
            safe_title = title.replace("[", "(").replace("]", ")").replace('"', "'")

            # 使用基础字符串拼接，避免 f-string 语法解析歧义
            if node_type == "start" or node_type == "end":
                mermaid.append("  " + node_id + "((" + safe_title + "))")
            elif node_type == "if-else":
                mermaid.append("  " + node_id + "{" + safe_title + "}")
            elif node_type == "code":
                mermaid.append("  " + node_id + "[/" + safe_title + "/]")
            else:
                mermaid.append("  " + node_id + "[" + safe_title + "]")

        # 2. 定义连线
        for edge in edges:
            source = str(edge["source"])
            target = str(edge["target"])
            label = str(edge.get("sourceHandle", ""))

            if label == "true":
                mermaid.append("  " + source + " -- 是 --> " + target)
            elif label == "false":
                mermaid.append("  " + source + " -- 否 --> " + target)
            else:
                mermaid.append("  " + source + " --> " + target)

        return "\n".join(mermaid)
    except Exception as e:
        return "graph TD\n  error[解析失败: " + str(e) + "]"
