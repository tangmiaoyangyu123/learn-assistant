from fastapi import FastAPI
from pydantic import BaseModel, Field

from docs_helper import attach_docs

app = FastAPI(title="问答 API ", docs_url=None, redoc_url=None)
attach_docs(app)

#请求体模型：进来的模型。
class AskRequest(BaseModel):
    """提问请求体。"""

    question: str = Field(min_length = 1, max_length = 500, description="用户的问题")
    # default:默认值。
    top_k: int = Field(default=3, ge=1, le=10, description="检索几条文档")

@app.post("/ask")
def ask(req: AskRequest):
    return {"answer": f"（还没接 RAG）你问的是：{req.question}", "top_k": req.top_k}