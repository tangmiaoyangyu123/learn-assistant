r"""第4周周末项目: PDF 问答助手 V1 —— 上传 PDF → 提问 → 带引用的回答

本文件只干两件事：**画界面** + **把已有模块串起来**。业务逻辑一行都没有新写：

    入库 → kb_manager.add_pdf          （本周末新写的"知识库管理"）
    检索 → search_docs.search          （第 3 周，包含在 ask 内部）
    生成 → rag_qa.ask                  （第 4 周 Day1-3）

运行：
  python pdf_qa_app.py
然后浏览器打开 http://127.0.0.1:7860

前置：与 rag_qa.py / search_docs.py / kb_manager.py / chinese_embedding.py 同目录，
      且 .env 里有 DEEPSEEK_API_KEY。
"""

from pathlib import Path

import gradio as gr

import kb_manager
from rag_qa import ask


def fmt_sources(hits):
    """检索来源清单：编号 + 文件名/页码 + 距离"""
    lines = [
        "| # | 来源 | 距离 |",
        "|---|---|---|",
    ]
    for i, (_doc, dist, meta) in enumerate(hits, 1):
        where = meta["source"]
        if meta.get("page"):
            where += f" 第{meta['page']}页"
        mark = " ⚠️" if dist > 0.9 else ""
        lines.append(f"| {i} | {where} | {dist:.3f}{mark} |")
    return "\n".join(lines)


def fmt_kb():
    """知识库现状（Markdown 表格）"""
    items = kb_manager.list_sources()
    if not items:
        return "_知识库是空的。_先在上面选择 PDF，然后点「加入知识库」。"
    total = sum(n for _, n in items)
    rows = "\n".join(f"| `{name}` | {n} |" for name, n in items)
    return f"**已入库 {len(items)} 个文件，共 {total} 段**\n\n| 文件 | 段数 |\n|---|---|\n{rows}"


def upload(files):
    """① 上传 → 入库。返回 (日志, 知识库清单)"""
    if not files:
        return "⚠️ 还没有选择文件。", fmt_kb()
    logs = []
    for f in files:
        p = Path(f if isinstance(f, str) else getattr(f, "name", str(f)))
        r = kb_manager.add_pdf(p)
        icon = {"ok": "✅", "suspect": "⚠️", "fail": "❌"}[r["level"]]
        logs.append(f"{icon} **{r['name']}** — {r['msg']}")
    return "\n\n".join(logs), fmt_kb()


def clear():
    """清空知识库"""
    kb_manager.clear_all()
    return "_已清空知识库。_", fmt_kb()


def answer(question):
    """② 提问 → (答案, 来源清单)"""
    col = kb_manager.get_collection()
    if col.count() == 0:
        return "知识库还是空的，请先在「① 上传文档」里加入 PDF。", ""
    if not question or not question.strip():
        return "请先输入问题。", ""
    text, hits = ask(col, question)
    return text, fmt_sources(hits)


with gr.Blocks(title="PDF 问答助手 V1") as demo:
    gr.Markdown(
        "## PDF 问答助手 V1\n"
        "上传 PDF → 加入知识库 → 提问。回答**只依据文档内容**，并标注引用来源。"
    )

    with gr.Tab("① 上传文档"):
        files = gr.File(
            label="选择 PDF（可多选）",
            file_count="multiple",
            file_types=[".pdf"],
        )
        with gr.Row():
            up_btn = gr.Button("加入知识库", variant="primary")
            clr_btn = gr.Button("清空知识库")
        up_log = gr.Markdown("_等待上传…_")
        gr.Markdown("---")
        kb_view = gr.Markdown(fmt_kb())

    with gr.Tab("② 提问"):
        inp = gr.Textbox(
            label="你的问题",
            placeholder="例如：这份文件里关于 XX 是怎么规定的？",
            lines=2,
        )
        ask_btn = gr.Button("提问", variant="primary")
        ans = gr.Textbox(label="回答", lines=12, buttons=["copy"])
        with gr.Accordion(label="检索来源（Top-3）", open=False):
            src = gr.Markdown("_还没有提问。_")
        gr.Markdown(
            "> 回答只依据你上传的文档；资料不足时它会直接说「资料里没有相关内容」。"
        )

    with gr.Tab("③ 使用说明"):
        gr.Markdown(
            "### 怎么用\n"
            "1. 在「① 上传文档」里选择 PDF（可多选）\n"
            "2. 点「加入知识库」\n"
            "3. 切到「② 提问」，输入问题\n\n"
            "### 支持什么\n"
            "- 中文 PDF（文字版）\n"
            "- 一次可上传多个文件\n"
            "- 回答会标注引用来源和页码\n\n"
            "### 不支持什么\n"
            "- **扫描件 / 图片型 PDF**：里面没有文字层，提不出内容，会被跳过\n"
            "- 一次上传太多大文件会明显变慢\n"
        )

    up_btn.click(upload, inputs=files, outputs=[up_log, kb_view])
    clr_btn.click(clear, outputs=[up_log, kb_view])
    ask_btn.click(answer, inputs=inp, outputs=[ans, src])
    inp.submit(answer, inputs=inp, outputs=[ans, src])


if __name__ == "__main__":
    demo.launch(inbrowser=True)
