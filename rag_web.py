r"""第4周Day5: RAG + Gradio 整合 —— 给命令行助手套上网页界面

链路：
  网页输入问题 → search_docs.search 检索 Top-3 → rag_qa.ask 拼 Prompt 调模型
  → 网页同时显示「答案」和「检索来源」

和 Day1-3 的关系（这就是模块化的价值）：
  业务逻辑（检索 / 拼装 / 调用 / 拒答）**一行都没改**，全部复用
  今天新增的只有"界面层" —— 一个函数 + 一段布局声明

运行：
  python rag_web.py
然后浏览器打开 http://127.0.0.1:7860

前置：与 rag_qa.py / search_docs.py / chinese_embedding.py 放在同一目录，
      且 .env 里有 DEEPSEEK_API_KEY，chroma_db 已建好。
"""

import chromadb
import gradio as gr

from chinese_embedding import MODEL_DIR, ChineseEmbedding
from rag_qa import ask
from search_docs import COLLECTION, DB_PATH

# 启动时加载一次知识库。
# 关键：绝对不要写在 answer() 里面 —— 那样每点一次按钮都要重新加载
# embedding 模型 + 打开数据库，慢几十倍。这是 Web 应用最常见的性能坑。
#下划线前缀 _client、_collection,这是 Python 约定：变量名前的 _ 表示"这是模块内部使用的，别人别来动它"。它和 _dist、_doc 里"忽略这个值"的用法不同，这里是"模块级私有变量"的意思——它俩是整个文件共享的"全局知识库句柄"，但不希望被外部直接访问。

_client = chromadb.PersistentClient(path=DB_PATH)
_collection = _client.get_collection(
    COLLECTION, embedding_function=ChineseEmbedding(MODEL_DIR)
)

N_SHOW = 3


def format_sources(hits):
    """把检索结果格式化成"来源清单"文本"""
    lines = []
    for i, (_doc, dist, meta) in enumerate(hits, 1):
        where = meta["source"]
        if meta.get("page"):
            where += f" 第{meta['page']}页"
        lines.append(f"[{i}] {where}    距离 {dist:.3f}")
    return "\n".join(lines)


def answer(question):
    """界面调用的函数：问题 → (答案, 来源清单)"""
    if not question or not question.strip():
        return "请先输入问题。", ""
    text, hits = ask(_collection, question)
    return text, format_sources(hits)


#返回三个空字符串，对应三个框（问题框、回答框、来源框），点击"清空"时把它们全部置空。逻辑极其简单，但体现了界面的完整交互设计。
def clear():
    """清空三个输入框"""
    return "", "", ""


with gr.Blocks(title="本地文档问答助手") as demo:
    gr.Markdown(
        "## 本地文档问答助手\n"      #标题
        f"知识库 `{COLLECTION}`，共 {_collection.count()} 段，"     #问题入框。
        "由 `test.pdf` 与 `README.md` 构建。"
    )

    inp = gr.Textbox(label="你的问题", placeholder="例如：志愿者活动加分吗", lines=2)
    #with gr.Row():布局容器：把两个按钮并排放在同一行。没有它，按钮会竖着叠。
    with gr.Row():            #一行放两个按钮
        btn = gr.Button("提问", variant="primary")
        clr = gr.Button("清空")

    ans = gr.Textbox(label="回答", lines=10, buttons=["copy"])
    src = gr.Textbox(label="检索来源（Top-3）", lines=4)

    gr.Examples(
        examples=[
            "志愿者活动加分吗",
            "综合测评的分数怎么算的",
            "怎么用 Python 读取 Excel",
            "红烧肉怎么做",
        ],
        inputs=inp,
        label="试试这些问题",
    )

    # 事件绑定：点按钮 或 在输入框里按回车 → 调 answer()
    btn.click(answer, inputs=inp, outputs=[ans, src])
    inp.submit(answer, inputs=inp, outputs=[ans, src])
    clr.click(clear, outputs=[inp, ans, src])

    gr.Markdown(
        "> 回答只依据检索到的资料；资料不足时它会直接说「资料里没有相关内容」。"
    )


if __name__ == "__main__":
    demo.launch(inbrowser=True)
