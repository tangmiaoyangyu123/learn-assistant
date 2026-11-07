from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from docs_helper import attach_docs

app = FastAPI(title="上传实验", docs_url=None, redoc_url=None)
attach_docs(app)

UPLOAD_DIR = Path("uploads")
#创建目录，已创建就跳过，不报错。
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # ① 只保留文件名本身 —— 为什么必须这样，见下一节
    name = Path(file.filename).name

    # ② 只收 PDF， endswith 检查后缀，
    if not name.lower().endswith(".pdf"):
        return {"error": f"只收 PDF，你传的是 {name}"}

    # ③ 写盘
    target = UPLOAD_DIR / name
    target.write_bytes(await file.read())

    return {
        "name": name,
        "size": file.size,
        "saved_to": str(target),
        "content_type": file.content_type,
    }