"""第3周周末项目: 本地文档搜索 Demo
输入一个问题，返回最相关的 3 段原文（带来源和页码），不接大模型。

用法：
  python search_docs.py                      # 交互模式，回车退出
  python search_docs.py "综合测评怎么加分"     # 单次查询

前置：先跑过 build_knowledge_base.py 把知识库建好
"""
import sys

import chromadb

from chinese_embedding import MODEL_DIR, ChineseEmbedding

DB_PATH = "chroma_db"
COLLECTION = "kb_zh"
#返回最相似的3段。
N_RESULTS = 3
#每段最多显示400字，避免打字过多。
SHOW_CHARS = 400        # 每段最多显示多少字
MAX_DISTANCE = 1.1      # 拒答阈值：最近距离超过它，就认为"库里没有相关内容"
                        # 本值按你这份语料实测校准（有效问题最高 1.050，跑题问题最低 1.199）
                        # 注意：0.838 那种"沾边但没答案"的问题它拦不住 —— 单靠阈值做不到完美，
                        # 第 4 周接上大模型后由模型兜底（见 W4 Day3）


#查询向量库
def search(collection, question, n=N_RESULTS):
    #collection.query将question转化成向量
    r = collection.query(query_texts=[question], n_results=n)
    #返回结果为一个向量
    return list(zip(r["documents"][0], r["distances"][0], r["metadatas"][0]))


def show(question, hits):
    print("=" * 60)
    print(f"问题：{question}")
    #hits[0]是最接近的一条，hits[0][1]是它的距离，如果距离超过，就会发生警告。
    if hits[0][1] > MAX_DISTANCE:
        print(f"⚠️  最接近的距离 {hits[0][1]:.3f} > 阈值 {MAX_DISTANCE}"
              f" → 知识库里很可能没有相关内容")
    for i, (doc, dist, meta) in enumerate(hits, 1):
        where = f"{meta['source']}"
        if meta.get("page"):
            where += f" 第{meta['page']}页"
        where += f" 第{meta['chunk']}块"
        body = doc[:SHOW_CHARS] + ("…" if len(doc) > SHOW_CHARS else "")
        print(f"\n[{i}] 距离 {dist:.3f} | {where}")
        print("    " + body.replace("\n", "\n    "))


def main():
    #打开持久化数据库。
    client = chromadb.PersistentClient(path=DB_PATH)
    # 关键：每次打开都要传 embedding_function，否则回落内置英文模型（维度会报错）
    collection = client.get_collection(COLLECTION, embedding_function=ChineseEmbedding(MODEL_DIR))
    print(f"已加载知识库 {COLLECTION}，共 {collection.count()} 段。输入问题后回车搜索，直接回车退出。\n")

    if len(sys.argv) > 1:                     # 命令行带问题 → 查一次就退
        #sys.argv[1:]是问题分词后的列表，" ".join拼成字符串，search查询，show打印。
        show(" ".join(sys.argv[1:]), search(collection, " ".join(sys.argv[1:])))
        return

    while True:                               # 交互模式
        try:
            question = input("问题> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break
        show(question, search(collection, question))
        print()


if __name__ == "__main__":
    main()
