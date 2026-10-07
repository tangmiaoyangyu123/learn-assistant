r"""第4周Day1-3: RAG 问答助手 —— 检索 + 生成 全链路

链路：问题 → 检索知识库（周3成果）→ 拼装 Prompt → 调 DeepSeek → 带引用的回答

三个设计要点（对应 Day1/Day2/Day3）：
  Day1  Prompt 拼装：把检索到的段落塞进模板，用「资料」和「要求」分隔
  Day2  引用来源：每段资料带编号和出处，要求模型标注用了哪一段
  Day3  拒答策略：资料不足时明确说"资料里没有"，而不是硬编（对照 search_docs 的阈值）

用法：
  python rag_qa.py                           # 交互模式，回车退出
  python rag_qa.py "志愿者活动加分吗"          # 单次提问
  python rag_qa.py --debug "xxx"             # 显示检索详情（距离/来源）
"""

import sys

import chromadb
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    OpenAI,
    RateLimitError,
    AuthenticationError
)
from chinese_embedding import MODEL_DIR, ChineseEmbedding
from search_docs import COLLECTION, DB_PATH, search

load_dotenv()

client = OpenAI(
    api_key=__import__("os").getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"
#检索三段资料。
N_RESULTS = 3
MAX_CONTEXT_CHARS = 1200

SYSTEM_PROMPT = """你是一个严谨的文档问答助手。

规则：
1. 只根据【资料】回答，不使用你的任何先验知识。
2.每条结论后用[1][2]这样的编号标注它来自哪一段资料。
3. 如果【资料】不足以回答问题，直接回答"资料里没有相关内容"，不要猜测，不要补充。
4.回答简洁，用中文。
"""

USER_TEMPLATE = """【资料】
{context}

【问题】
{question}
"""


#它把 search() 检索出来的 3 段原文，打包成一段带编号、带出处、模型能直接读的"资料"文本，方便模型在回答时引用。
def build_context(hits):
    """把检索结果拼成带编号的资料文本，供模型引用"""
    parts = []
    # enumerate(hits, 1)边循坏边计数 -> [(1, 元组1), (2, 元组2), (3, 元组3)]。
    # i 接受序号。
    # (doc, _dist, meta)元组解包(text原文, 距离, 元数据{"source": "test.pdf", "page": 3, "chunk": 2})。

    for i, (doc, _dist, meta) in enumerate(hits, 1):
        #去出“来源文件名”。
        where = meta["source"]
        #如果有页码，追加页码。
        #如果使用meta["page"]，没有了话会直接报错。而meta.get()会返回None,更加安全。
        #这一段代码主要是分开.pdf和.md文件，.md文件没有页数这一说。
        if meta.get("page"):
            #在文件后加上页数。
            where += f" 第{meta['page']}页"
        body = doc[:MAX_CONTEXT_CHARS]
        parts.append(f"[{i}] （来源：{where}）\n{body}")
    return "\n\n".join(parts)

def ask(collection, question, verbose=False):
    """核心：检索 → 拼 prompt → 调模型 → 返回答案"""
    #在知识库中寻找最相关的3段。
    hits = search(collection, question, n=N_RESULTS)
    #可选的调试输出。
    if verbose:
        print("--- 检索详情 ---")
        for i, (_doc, dist, meta) in enumerate(hits, 1):
            where = f"{meta['source']}"
            if meta.get("page"):
                where += f" 第{meta['page']}页"
            print(f"  [{i}] 距离 {dist:.3f} | {where}")
        print("--- 检索结束 ---\n")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            #相当于填空，根据上面USER_TEMPLATE
            context=build_context(hits), question=question)},
    ]

    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.1,
        )
        return resp.choices[0].message.content, hits
    except AuthenticationError:
        return "❌ API Key 无效，检查 .env 里的 DEEPSEEK_API_KEY", hits
    except RateLimitError:
        return "❌ 请求被限流，稍后再试", hits
    except APIConnectionError:
        return "❌ 网络连接失败，检查网络或代理设置", hits


def main():
    #sys.argv 是 Python 给你的命令行参数列表。
    #sys.argv[0]是脚本文件名本身，从[1]之后才是我们所需要的内容。
    #该行代码就是过滤"--debug"
    args = [a for a in sys.argv[1:] if a != "--debug"]
    verbose = "--debug" in sys.argv

    #PersistentClient：打开 chromadb 的"持久化数据库"，数据存在 chroma_db 文件夹里（DB_PATH 从 search_docs.py 导入）
    c = chromadb.PersistentClient(path=DB_PATH)
    #get_collection：从数据库里取出名为 kb_zh 的集合（知识库）
    collection = c.get_collection(COLLECTION, embedding_function=ChineseEmbedding(MODEL_DIR))

    #判断有没有带问题。
    if args:
        q = " ".join(args)
        answer, hits = ask(collection, q, verbose)
        print(f"问题：{q}\n")
        print(answer)
        return

    print(f"已加载知识库 {COLLECTION}（{collection.count()} 段）。提问后回车，直接回车退出。\n")
    while True:
        try:
            q = input("问题> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            break
        answer, _ = ask(collection, q, verbose)
        print(f"\n{answer}\n")


if __name__ == "__main__":
    main()











