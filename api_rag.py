import asyncio
import json
import os
import time

import kb_manager
import rag_qa
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from search_docs import search

from docs_helper import attach_docs

load_dotenv()

app = FastAPI(title="RAG 问答", docs_url=None, redoc_url=None)
attach_docs(app)

aclient = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class Source(BaseModel):
    """一条检索来源。"""

    source: str = Field(description="文件名")
    page: int | None = Field(default=None, description="页码，md/txt 文件没有页码")
    chunk: int | None = Field(default=None, description="在该文件里的片段序号")
    distance: float = Field(description="检索距离，越小越相关")
    content: str = Field(description="命中的原文片段")


class AskResponse(BaseModel):
    """问答响应。"""

    answer: str = Field(description="模型生成的答案")
    sources: list[Source] = Field(description="这次回答参考了哪些片段")
    elapsed: float = Field(description="本次问答耗时（秒）")


@app.post("/ask", response_model=AskResponse)
def ask_api(rep: AskRequest):
    """你昨天写好的同步版本，一行不用改。"""
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



async def ask_stream(collection, question):
    """异步流式问答：检索 → 发来源 → 流式生成 → 发结束。

    yield (事件类型, 数据字典)
    """
    t0 = time.perf_counter()

    # ① 检索（同步调用，实测 18 毫秒，可接受）
    hits = search(collection, question, n=rag_qa.N_RESULTS)

    # ② hits → list[Source]，和 /ask 里一模一样
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

    # ③ 立刻把来源发出去（第 4 步）
    yield ("meta", {"sources": [s.model_dump() for s in sources]})

    # ④ 拼 prompt，复用 rag_qa 里的模板
    messages = [
        {"role": "system", "content": rag_qa.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": rag_qa.USER_TEMPLATE.format(
                context=rag_qa.build_context(hits),
                question=question,
            ),
        },
    ]

    # ⑤ 流式调模型
    stream = await aclient.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:                                  # None 和 '' 都过滤
            yield ("delta", {"delta": delta})

    # ⑥ 结束
    yield ("done", {"elapsed": round(time.perf_counter() - t0, 2)})


@app.post("/ask/stream")
async def ask_stream_api(req: AskRequest):
    """流式问答。响应是 text/event-stream，不是 JSON。"""
    col = kb_manager.get_collection()

    async def event_gen():
        try:
            async for kind, data in ask_stream(col, req.question):
                if kind == "meta":
                    yield f"event: meta\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif kind == "delta":
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    yield "data: [DONE]\n\n"
                    yield f"event: done\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            raise                                  # 必须重新抛

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
