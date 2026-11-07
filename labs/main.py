from fastapi import FastAPI
from docs_helper import attach_docs

app = FastAPI(docs_url=None, redoc_url=None)     # 两个默认的都关掉
attach_docs(app)

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI"}
