r"""第5周 Day2 · PDF 问答助手 V2 —— 上传 PDF → 多轮提问 → 带引用的回答

本文件只干两件事：**画界面** + **把已有模块串起来**。业务逻辑一行都没有新写：

    入库 → kb_manager.add_pdf          （第 4 周周末新写的"知识库管理"）
    检索 → search_docs.search          （第 3 周，包含在 ask 内部）
    生成 → rag_qa.ask                  （第 4 周 Day1-3）

Day2 改动：界面层支持多轮对话
    数据层  gr.State([])   →  存一份"干净"的历史 [{"role":…, "content":"文字"}]
    显示层  gr.Chatbot     →  只负责把历史画成气泡，不参与业务

运行：
  python pdf_qa_app.py
然后浏览器打开 http://127.0.0.1:7860

前置：与 rag_qa.py / search_docs.py / kb_manager.py / chinese_embedding.py 同目录，
      且 .env 里有 DEEPSEEK_API_KEY。
"""

# ============================================================================
# 本次修正清单（按你原代码的顺序）
#
#   P0-1  第 137 行 `clear.click(...)`：clear 是函数不是按钮 → AttributeError 启动崩
#   P0-2  answer() 返回 3 个值，outputs 要 4 个；且位置错位 → 会话直接失败
#   P0-3  早退分支 `return "请输入问题"` 只给 1 个值；空知识库检查被删掉
#   严重  `test, hits = ask(...)` 里 test 从未使用 → 模型答案没显示，
#         Chatbot 里是 chat_demo 的玩具假回复（不报错，最坑）
#   残留  ans = gr.Textbox(...)（旧回答框）没删
#   残留  msg = gr.Textbox("说点什么…")（chat_demo 的输入框）没删 → 页面有两个输入框
#   小    gr.Blocks(title="最小功能对话") 被 chat_demo 覆盖
#   小    answer() 的 docstring 还是旧的
#
# 核心心法：改了 outputs，就必须同步改 return —— 数量和顺序都要对得上。
# ============================================================================

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


def answer(question, history):
    """② 提问 → (给Chatbot显示的历史, 来源Markdown, 存回State的历史, 清空后的输入框)

    ⚠️ 四个返回值的【顺序】必须和 outputs=[chatbot, src, hist, inp] 一一对应。
    """
    col = kb_manager.get_collection()

    # ── 【你的问题 P0-3】原代码：return "请输入问题" ──────────────────────────
    # 只返回 1 个值，但 outputs 有 4 个 → 一点发送就报错，页面没反应。
    # 正确做法：返回 4 个值，而且历史【原样返回】——
    # "请先输入问题"不是一轮问答，不该写进对话历史，否则气泡里会多出一条废话。
    if not question or not question.strip():
        return history, "_请先输入问题。_", history, ""

    # ── 【你的问题 P0-3 之二】原代码把这段空库检查删掉了 ──────────────────────
    # 实测确认：chromadb 1.5.9 查空集合返回 [[]]，【不会报错】。
    # 所以删掉它不会崩，但会白调一次大模型，还给用户一句莫名其妙的
    # "资料里没有相关内容" —— 明明是他还没上传文档。所以加回来。
    if col.count() == 0:
        return history, "_知识库还是空的，请先在「① 上传文档」里加入 PDF。_", history, ""

    # ── 【需求 2 已接上】原代码：test, hits = ask(col, question) ──────────────
    # 变量名 test 是"测试"的意思，这里装的是模型答案，改叫 text。
    # 更要命的是：原来的 test 从头到尾没被用过，答案就这么丢了（静默失效）。
    # 现在把 history 一并传进去 —— 模型这才真正"记得上一轮说过什么"。
    # 注意：检索仍然只用 question，history 【不进检索】（原因见手册观察 3）。
    text, hits = ask(col, question, history=history)

    # ── 【你的问题·严重之二】原代码 assistant 的 content 是：
    #     f"你说的是「{question}」，这是第 {len(history) // 2 + 1} 轮"
    # 这是 chat_demo.py 里那个【玩具】的假回复（它不接大模型，只会复读）。
    # 抄 Demo 时把结构搬对了，却忘了把假回复换成真答案。
    # 后果：程序不报错，对话气泡也能出来，但回答永远是 "你说的是「…」，这是第 1 轮"。
    new_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": text},
    ]

    # ── 【你的问题 P0-2】原代码：return new_history, new_history, fmt_sources(hits)
    # 只给了 3 个值、顺序也对不上。你的 outputs 是 [chatbot, src, hist, inp]，
    # 所以 return 必须按这个顺序给 4 个值：
    #     ① chatbot ← new_history        刷新对话气泡
    #     ② src     ← fmt_sources(hits)  刷新来源折叠面板
    #     ③ hist    ← new_history        存回 State，下一轮才有历史可传
    #     ④ inp     ← ""                 清空输入框
    return new_history, fmt_sources(hits), new_history, ""


with gr.Blocks(title="PDF 问答助手 V2") as demo:
    # ── 【你的问题·小】原代码标题是 "最小功能对话"，被 chat_demo 覆盖了，改回来 ──
    gr.Markdown(
        "## PDF 问答助手 V2\n"
        "上传 PDF → 加入知识库 → 提问。回答**只依据文档内容**，并标注引用来源。"
        "支持多轮追问。"
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
        hist = gr.State([])                              # 数据层：干净历史
        chatbot = gr.Chatbot(label="对话", height=320)    # 显示层：只管画气泡
        inp = gr.Textbox(
            label="你的问题",
            placeholder="例如：这份文件里关于 XX 是怎么规定的？",
            lines=2,
        )
        with gr.Row():
            ask_btn = gr.Button("提问", variant="primary")
            # ── 【你的问题 P0-1】新按钮 ─────────────────────────────────────
            # 原代码没有这个按钮，而是在文件末尾写 `clear.click(...)`：
            #   clear 是第 63 行的【函数对象】，没有 .click → AttributeError 启动崩。
            # 注意也不能复用上面的 clr_btn —— 那个已经被"清空知识库"占了，
            # 一个按钮只能干一件事。
            chat_clr = gr.Button("清空对话")

        # ── 【你的问题·残留】原代码这里还留着两行，都删掉了 ──────────────────
        #   ans = gr.Textbox(label="回答", lines=12, buttons=["copy"])
        #       ↑ V1 的旧回答框，已被 Chatbot 取代，没有任何 outputs 指向它，
        #         留在页面上就是个永远空着的框
        #   msg = gr.Textbox(label="输入", placeholder="说点什么…", lines=2)
        #       ↑ chat_demo.py 的输入框，抄 Demo 时没删干净
        #         → 页面「② 提问」里会出现【两个】输入框

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
            "3. 切到「② 提问」，输入问题（可以连续追问）\n\n"
            "### 支持什么\n"
            "- 中文 PDF（文字版）\n"
            "- 一次可上传多个文件\n"
            "- 回答会标注引用来源和页码\n"
            "- 多轮对话：能记住前面聊过什么\n\n"
            "### 不支持什么\n"
            "- **扫描件 / 图片型 PDF**：里面没有文字层，提不出内容，会被跳过\n"
            "- 一次上传太多大文件会明显变慢\n"
            "- 刷新页面会丢失对话历史（State 是会话级的）\n"
        )

    up_btn.click(upload, inputs=files, outputs=[up_log, kb_view])
    clr_btn.click(clear, outputs=[up_log, kb_view])

    # ── 【你的问题 P0-2】inputs 2 个、outputs 4 个，与 answer() 的返回值严格对齐 ──
    #     inputs  = [问题框, 历史State]
    #     outputs = [Chatbot, 来源, 历史State, 问题框]
    # hist 既在 inputs 又在 outputs：不写回去，State 永远是空的，第二轮就没历史。
    ask_btn.click(answer, inputs=[inp, hist], outputs=[chatbot, src, hist, inp])
    inp.submit(answer, inputs=[inp, hist], outputs=[chatbot, src, hist, inp])

    # ── 【你的问题 P0-1】原代码：clear.click(lambda: ([], [], ""), ...) ──────
    # 报错原文：AttributeError: 'function' object has no attribute 'click'
    # 改成新按钮 chat_clr；lambda 返回 3 个空值，一次清掉
    # 历史 State / 对话气泡 / 输入框 三处。
    chat_clr.click(lambda: ([], [], ""), outputs=[hist, chatbot, inp])


if __name__ == "__main__":
    demo.launch(inbrowser=True)
