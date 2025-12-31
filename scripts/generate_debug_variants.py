import os

import yaml

# 1. 读取当前的失败文件作为基底
SOURCE_FILE = "output/workflows/信贷预警分析.yml"


def load_yaml():
    if not os.path.exists(SOURCE_FILE):
        print(f"File not found: {SOURCE_FILE}")
        return None
    with open(SOURCE_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_variant(name, data):
    path = f"output/debug/{name}.yml"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
    print(f"Generated: {path}")


def gen_v1_linear():
    """变体1：去掉 Router，线性连接。测试 Code 节点本身是否会导致崩溃。"""
    data = load_yaml()
    if not data:
        return

    nodes = data["workflow"]["graph"]["nodes"]
    edges = data["workflow"]["graph"]["edges"]

    # 找到 start, preprocess, analyze_urgent (改名为 analyze), end
    # 移除 router 和其他分支
    keep_ids = {"start", "preprocess", "handle_refund", "end"}  # 假设节点ID是这些，根据之前的日志
    # 修正：根据日志，节点ID可能是 start, preprocess, router, handle_refund...
    # 让我们动态查看一下 source file 的内容比较保险，但这里我先盲猜ID结构，
    # 或者更简单的，完全重写 graph 结构，复用 data。

    # 简单粗暴：只保留前两个节点 + End
    new_nodes = []
    for n in nodes:
        if n["id"] in ["start", "preprocess"]:
            new_nodes.append(n)
        if n["data"]["type"] == "end":
            n["id"] = "end"  # 确保ID一致
            new_nodes.append(n)
            break

    # 连线
    new_edges = [
        {
            "id": "e1",
            "source": "start",
            "target": "preprocess",
            "sourceHandle": "source",
            "targetHandle": "target",
            "type": "custom",
        },
        {
            "id": "e2",
            "source": "preprocess",
            "target": "end",
            "sourceHandle": "source",
            "targetHandle": "target",
            "type": "custom",
        },
    ]

    data["workflow"]["graph"]["nodes"] = new_nodes
    data["workflow"]["graph"]["edges"] = new_edges
    data["app"]["name"] = "Debug_V1_Linear"

    save_variant("debug_v1_linear", data)


def gen_v2_simple_router():
    """变体2：Router 引用 Start 变量。测试 If-Else 结构本身。"""
    data = load_yaml()
    if not data:
        return

    # 构造一个最小化的 Router 测试
    nodes = []
    # Start
    nodes.append(
        {
            "id": "start",
            "type": "custom",
            "position": {"x": 0, "y": 0},
            "data": {"type": "start", "title": "Start", "variables": [{"name": "q", "type": "string"}]},
        }
    )
    # Router (引用 Start)
    nodes.append(
        {
            "id": "router",
            "type": "custom",
            "position": {"x": 200, "y": 0},
            "data": {
                "type": "if-else",
                "title": "Router",
                "cases": [
                    {
                        "case_id": "true",
                        "logical_operator": "and",
                        "conditions": [
                            {
                                "id": "c1",
                                "variable_selector": ["start", "q"],
                                "comparison_operator": "contains",
                                "value": "a",
                                "varType": "string",
                            }
                        ],
                    }
                ],
            },
        }
    )
    # End True
    nodes.append(
        {
            "id": "end_true",
            "type": "custom",
            "position": {"x": 400, "y": -100},
            "data": {"type": "end", "title": "End A", "outputs": []},
        }
    )
    # End False
    nodes.append(
        {
            "id": "end_false",
            "type": "custom",
            "position": {"x": 400, "y": 100},
            "data": {"type": "end", "title": "End B", "outputs": []},
        }
    )

    edges = [
        {
            "id": "e1",
            "source": "start",
            "target": "router",
            "sourceHandle": "source",
            "targetHandle": "target",
            "type": "custom",
        },
        {
            "id": "e2",
            "source": "router",
            "target": "end_true",
            "sourceHandle": "true",
            "targetHandle": "target",
            "type": "custom",
        },
        {
            "id": "e3",
            "source": "router",
            "target": "end_false",
            "sourceHandle": "false",
            "targetHandle": "target",
            "type": "custom",
        },
    ]

    data["workflow"]["graph"]["nodes"] = nodes
    data["workflow"]["graph"]["edges"] = edges
    data["app"]["name"] = "Debug_V2_SimpleRouter"

    save_variant("debug_v2_simple_router", data)


def gen_v3_code_outputs():
    """变体3：完整流程，但手动给 Code 节点注入 outputs 定义。"""
    data = load_yaml()
    if not data:
        return

    nodes = data["workflow"]["graph"]["nodes"]

    for n in nodes:
        if n["data"]["type"] == "code":
            # 注入 outputs
            n["data"]["outputs"] = [
                {"variable": "cleaned_input", "type": "string"},
                {"variable": "detected_keywords", "type": "array"},  # 假设这是代码输出的变量名
            ]
            # 同时检查一下 title，防止缺失
            if "title" not in n["data"]:
                n["data"]["title"] = "Code Node"

    data["app"]["name"] = "Debug_V3_CodeOutputs"
    save_variant("debug_v3_code_outputs", data)


if __name__ == "__main__":
    gen_v1_linear()
    gen_v2_simple_router()
    gen_v3_code_outputs()
