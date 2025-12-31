from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.workflows.yaml_generator import YamlAgentService

# 定义 API 路由
router = APIRouter(prefix="/yaml", tags=["YAML Generation"])

# 实例化服务
yaml_service = YamlAgentService()


# 定义请求体模型
class YamlGenerateRequest(BaseModel):
    user_request: str
    context: str


@router.post("/generate", response_model=dict)
async def generate_yaml_endpoint(request: YamlGenerateRequest):
    """
    接收用户请求和上下文，触发 deepagents 工作流以生成 YAML。
    """
    try:
        # 调用服务并获取生成的 YAML
        generated_yaml = await yaml_service.generate_yaml(user_request=request.user_request, context=request.context)
        # 以 JSON 格式返回 YAML 字符串
        return {"yaml": generated_yaml}
    except Exception as e:
        # 记录异常可以放在服务层，这里只向上抛出 HTTP 异常
        raise HTTPException(status_code=500, detail=str(e)) from e
