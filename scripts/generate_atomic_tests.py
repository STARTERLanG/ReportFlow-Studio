import os

import yaml


def save_yaml(name, data):
    path = f"output/debug/{name}.yml"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Generated: {path}")


# 公共头部
BASE_APP = {
    "kind": "app",
    "version": "0.1.5",  # 尝试降低版本号以提高兼容性，或者使用你提供的 sample 的版本
    "app": {"name": "Debug_Workflow", "mode": "workflow", "icon": "🐞", "icon_background": "#FFEAD5"},
}


# Level 1: Start -> End
def gen_level_1():
    data = BASE_APP.copy()
    data["app"]["name"] = "Debug_L1_Start_End"
    data["workflow"] = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "custom",
                    "data": {
                        "type": "start",
                        "title": "开始",
                        "variables": [{"variable": "input_text", "label": "输入", "type": "string"}],
                    },
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "end",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "title": "结束",
                        "outputs": [{"variable": "result", "value_selector": ["start", "input_text"]}],
                    },
                    "position": {"x": 300, "y": 0},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "start",
                    "sourceHandle": "source",
                    "target": "end",
                    "targetHandle": "target",
                    "type": "custom",
                }
            ],
        }
    }
    save_yaml("level_1_base", data)


# Level 2: Start -> LLM -> End
def gen_level_2():
    data = BASE_APP.copy()
    data["app"]["name"] = "Debug_L2_LLM"
    data["workflow"] = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "custom",
                    "data": {
                        "type": "start",
                        "title": "开始",
                        "variables": [{"variable": "input_text", "label": "输入", "type": "string"}],
                    },
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "llm_node",
                    "type": "custom",
                    "data": {
                        "type": "llm",
                        "title": "LLM生成",
                        "model": {"provider": "openai", "name": "gpt-4o", "mode": "chat"},
                        "prompt_template": [
                            {"role": "system", "text": "你是一个助手。"},
                            {"role": "user", "text": "{{#start.input_text#}}"},
                        ],
                        # 关键：检查这些默认字段是否导致崩溃
                        "memory": {"window": {"enabled": False, "size": 10}, "query_prompt_template": ""},
                        "context": {"enabled": False, "variable_selector": []},
                        "vision": {"enabled": False},
                    },
                    "position": {"x": 300, "y": 0},
                },
                {
                    "id": "end",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "title": "结束",
                        "outputs": [{"variable": "result", "value_selector": ["llm_node", "text"]}],
                    },
                    "position": {"x": 600, "y": 0},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "start",
                    "sourceHandle": "source",
                    "target": "llm_node",
                    "targetHandle": "target",
                    "type": "custom",
                },
                {
                    "id": "e2",
                    "source": "llm_node",
                    "sourceHandle": "source",
                    "target": "end",
                    "targetHandle": "target",
                    "type": "custom",
                },
            ],
        }
    }
    save_yaml("level_2_llm", data)


# Level 3: Start -> If-Else -> End
# 这是最容易崩的地方
def gen_level_3():
    data = BASE_APP.copy()
    data["app"]["name"] = "Debug_L3_IfElse"
    data["workflow"] = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "custom",
                    "data": {
                        "type": "start",
                        "title": "开始",
                        "variables": [{"variable": "input_text", "label": "输入", "type": "string"}],
                    },
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "router",
                    "type": "custom",
                    "data": {
                        "type": "if-else",
                        "title": "路由",
                        "conditions": [
                            {
                                "id": "true",  # Dify 标准 if-else 只有 true/false
                                "operator": "contains",
                                "variable_selector": ["start", "input_text"],
                                "value": "a",
                            }
                        ],
                        "logical_operator": "and",
                    },
                    "position": {"x": 300, "y": 0},
                },
                {
                    "id": "end_true",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "title": "结束A",
                        "outputs": [{"variable": "res", "value_selector": ["start", "input_text"]}],
                    },
                    "position": {"x": 600, "y": -100},
                },
                {
                    "id": "end_false",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "title": "结束B",
                        "outputs": [{"variable": "res", "value_selector": ["start", "input_text"]}],
                    },
                    "position": {"x": 600, "y": 100},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "start",
                    "sourceHandle": "source",
                    "target": "router",
                    "targetHandle": "target",
                    "type": "custom",
                },
                # 关键：检查 sourceHandle 是否对应 conditions 的 id
                {
                    "id": "e2",
                    "source": "router",
                    "sourceHandle": "true",
                    "target": "end_true",
                    "targetHandle": "target",
                    "type": "custom",
                },
                {
                    "id": "e3",
                    "source": "router",
                    "sourceHandle": "false",
                    "target": "end_false",
                    "targetHandle": "target",
                    "type": "custom",
                },
            ],
        }
    }
    save_yaml("level_3_ifelse", data)


if __name__ == "__main__":
    gen_level_1()
    gen_level_2()
    gen_level_3()
