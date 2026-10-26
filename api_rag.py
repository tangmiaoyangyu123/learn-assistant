import asyncio
import json
import os
import time

import kb_manager
import rag_qa
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from search_docs import search

from docs_helper import attach_docs

import db

load_dotenv()

db.init_db()

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


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    session_id: str | None = Field(default=None, description="不传就新建一个会话")


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    elapsed: float
    session_id: str            # 一定要回传，客户端下次带着它来


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]


class DeleteResponse(BaseModel):
    session_id: str
    deleted: int


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    col = kb_manager.get_collection()

    # ① 会话 id：传了就沿用，没传才新建
    sid = req.session_id or db.new_session_id()

    # ② 读历史（只含 role/content，喂给模型）
    history = db.get_history(sid)

    # ③ 先存用户问题
    db.save_message(sid, "user", req.question)

    # ④ 计时 + 调模型
    t0 = time.perf_counter()
    answer, hits = rag_qa.ask(col, req.question, history=history)
    elapsed = time.perf_counter() - t0

    # ⑤ 存答案
    db.save_message(sid, "assistant", answer)

    # ⑥ hits → sources
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

    # ⑦ 返回
    return ChatResponse(
        answer=answer,
        sources=sources,
        elapsed=round(elapsed, 2),
        session_id=sid,
    )


@app.get("/history/{session_id}", response_model=HistoryResponse)
def get_history_api(session_id: str):
    rows = db.get_messages(session_id)
    return HistoryResponse(session_id=session_id, messages=rows)


@app.delete("/history/{session_id}", response_model=DeleteResponse)
def delete_history_api(session_id: str):
    n = db.clear_session(session_id)
    return DeleteResponse(session_id=session_id, deleted=n)


#=====================带文件传输=========================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class DocOut(BaseModel):
    name: str = Field(description="文件名")
    chunks: int = Field(description="这个文件在库里有几块")


class DocListResponse(BaseModel):
    documents: list[DocOut]
    total_chunks: int = Field(description="全部文档合计多少块")


class UploadResult(BaseModel):
    name: str
    level: str = Field(description="ok 正常 / suspect 可疑但仍入库 / fail 没入库")
    chunks: int
    pages: int
    chars: int
    msg: str = Field(description="给人看的说明")


class DeleteDocResponse(BaseModel):
    name: str
    deleted_chunks: int = Field(description="删掉了多少块（删之前有几块）")


@app.post("/documents", response_model=UploadResult)
async def upload_doc(file: UploadFile = File(...)):
    name = Path(file.filename).name

    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, f"只收 PDF，你传的是 {name}")

    target = UPLOAD_DIR / name
    target.write_bytes(await file.read())

    try:
        report = kb_manager.add_pdf(target)
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"这个文件解析失败：{e}")

    if report["level"] == "fail":
        target.unlink(missing_ok=True)
        raise HTTPException(400, report["msg"])

    return UploadResult(**report)


@app.get("/documents", response_model=DocListResponse)
def list_docs():
    items = kb_manager.list_sources()

    docs = [DocOut(name=n, chunks=c) for n, c in items]

    return DocListResponse(
        documents=docs,
        total_chunks=sum(d.chunks for d in docs),
    )


@app.delete("/documents/{name}", response_model=DeleteDocResponse)
def delete_doc(name: str):
    items = dict(kb_manager.list_sources())
    if name not in items:
        raise HTTPException(404, detail=f"知识库里没有 {name}")
    n = items[name]

    kb_manager.remove_source(name)

    target = UPLOAD_DIR / name
    if target.exists():
        target.unlink()

    return DeleteDocResponse(name=name, deleted_chunks=n)
