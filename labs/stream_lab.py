import asyncio
import json

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from docs_helper import attach_docs

app = FastAPI(title="流式实验", docs_url=None, redoc_url=None)
attach_docs(app)

async def fake_llm(text: str):
    for ch in text:
        await asyncio.sleep(0.2)
        yield ch

@app.get("/stream")
async def stream(q: str = "你好世界"):
    async def event_gen():
        async for ch in fake_llm(q):
            #ensure_ascii=False：中文原样保留。
            payload = json.dumps({"delta": ch}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")