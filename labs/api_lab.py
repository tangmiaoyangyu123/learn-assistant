from fastapi import FastAPI
import kb_manager
from docs_helper import attach_docs

app = FastAPI(title="PDF 问答助手 API", docs_url=None, redoc_url=None)
attach_docs(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"你好，{name}"}


@app.get("/kb/stats")
def kb_stats():
    col = kb_manager.get_collection()
    return {"count": col.count()}
