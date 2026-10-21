import kb_manager
import rag_qa

from pydantic import BaseModel, Field
from fastapi import FastAPI

from docs_helper import attach_docs

import time

app = FastAPI(title="RAG 问答", docs_url=None, redoc_url=None)
attach_docs(app)

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class Source(BaseModel):
    """一条检索来源。"""
    source: str = Field(description="文件名")
    page: int | None = Field(default=None, description="页码，md/txt 文件没有页码")
    chunk: int | None = Field(default=None, description="在该文件里的片段序号")
    distance: float = Field(description="检索距离，越小越相关")
    content: str = Field(description="命中的原文片段（已截断）")


class  AskResponse(BaseModel):
    """问答响应"""

    answer: str = Field(description="模型生成的答案")
    sources: list[Source] = Field(description="这次回答参考哪些界面")
    elapsed: float = Field(description="本次问答耗时（秒）")


@app.post("/ask", response_model=AskResponse)
def ask_api(rep: AskRequest):
    col = kb_manager.get_collection()

    t0 = time.perf_counter()

    answer, hits = rag_qa.ask(col, rep.question)

    elapsed = time.perf_counter() - t0

    sources = [
        Source(
            source=meta["source"],
            page=meta.get("page"),
            chunk=meta.get("chunk"),
            distance=round(dist, 4),
            content=doc[:200],
        )
        for doc, dist, meta in hits
    ]

    return AskResponse(answer=answer, sources=sources, elapsed=round(elapsed, 2))