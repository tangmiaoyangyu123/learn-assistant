r"""第4周周末项目: 知识库管理 —— 用户上传的 PDF 怎么进库

职责单一：只管"知识库里有什么"。不碰界面，不碰大模型。
  - 界面（pdf_qa_app.py）用它入库、列清单
  - 问答（rag_qa.ask）用它的 collection 去检索

和第 3 周 build_knowledge_base.py 的关系：
  那个是"一次性脚本"——SOURCE_FILES 写死，跑一次全量重建；
  这个是"运行时服务"——文件由用户在网页上给，来一个加一个。
  **切分逻辑一行都没重写，直接复用 chunks_from_pdf（这就是模块化的价值）。**
"""

from collections import Counter
from pathlib import Path

import chromadb

from build_knowledge_base import MIN_CHARS_PER_PAGE, chunks_from_pdf
from chinese_embedding import MODEL_DIR, ChineseEmbedding

DB_PATH = "chroma_db"
COLLECTION = "upload_kb"

#惰性单列模式
_embedding = None     #模块级变量，初始是None
_collection = None

#ChineseEmbedding 要加载 24MB 的 ONNX 模型，get_collection 要打开数据库——都很慢。
#模型和集合，整个程序生命周期里只加载一次，之后一直复用同一个对象。提高效率
def _get_embedding():
    #因为embedding在函数内做了赋值，告诉Python不需要新建局部变量。
    global _embedding
    if _embedding is None:
        _embedding = ChineseEmbedding(MODEL_DIR)
    return _embedding


def get_collection():
    """第一次调用才加载模型 + 打开库，之后复用同一个句柄"""
    global _collection
    if _collection is None:
        _collection = chromadb.PersistentClient(path=DB_PATH).get_or_create_collection(
            COLLECTION, embedding_function=_get_embedding()
        )
    return _collection

#list_sources()：用 Counter 统计"每个文件几块"
def list_sources(collection=None):
    """返回[(文件名，块数)， ...]，按文件名排序。"""
    col = collection or get_collection()
    if col.count() == 0:
        col.count()
        #返回集合里总共有多少块。如果是0（上传区还空着），直接返回空列表，省得后面白忙活。
        return []
    #col.get 是读取窗口，include=["metadatas"]元数据，不要正文，正文太长了，占内存。
    metas = col.get(include=["metadatas"])["metadatas"]
    #Counter 可以快速读出每个块属于哪个文件的块数
    #e.g:可能的返回值[('a.pdf', 5), ('b.pdf', 3)]。
    return sorted(Counter(m["source"] for m in metas).items())

def remove_source(name, collection=None):
    """删除某个文件的所有块"""
    col = collection or get_collection()
    #所以删一个文件 = 删掉所有 source == 这个文件名 的块。
    col.delete(where={"source":name})

#把整个集合删了，建立一个新的。
def clear_all():
    global _collection
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    _collection = client.get_or_create_collection(
        COLLECTION, embedding_function=_get_embedding()
    )
    return _collection

def add_pdf(path, collection=None):
    """把一份 PDF ，加进知识库，返回一份报告 dict

    level： ok 正常 / suspect 可疑但仍入库 / fail 没入库
    """
    col = collection or get_collection()
    path = Path(path)
    name = path.name

    # ① 先抽块。这一步是只读的 —— 抽不到东西也不会动库里已有的数据。
    stats = {}
    docs, metas, ids = [], [], []
    for chunk, meta in chunks_from_pdf(path, stats):
        docs.append(chunk)
        metas.append(meta)     #元数据：含 source / page / chunk
        ids.append(f"{meta['source']}-p{meta['page']}-c{meta['chunk']}")

    pages = stats.get("pages", 0)     #取出"这份 PDF 有多少页"。
    chars = stats.get("chars", 0)     #同样取出"总共提取到多少字符"。

    # ② 一个字都没抽到 —— 扫描件。直接报错，不污染知识库。
    if not docs:
        return {"name": name, "level": "fail", "chunks": 0, "pages": pages, "chars": chars,
                "msg": f"0 块 | 提不出文字（{pages} 页）—— 多半是扫描件/图片型 PDF，需要先 OCR"}

    # ③ 重传同名文件：先删旧块，否则块会翻倍，而且 id 重复会直接报错。
    remove_source(name, col)     #删除旧块。
    col.add(documents=docs, ids=ids, metadatas=metas)     #存进向量库。

    per_page = chars // pages if pages else chars   #算平均每页多少字。
    if pages and per_page < MIN_CHARS_PER_PAGE:
        return {"name": name, "level": "suspect", "chunks": len(docs), "pages": pages,
                "chars": chars,
                "msg": f"{len(docs)} 块 | 已入库，但平均每页只有 {per_page} 字，提取质量可疑"}
    return {"name": name, "level": "ok", "chunks": len(docs), "pages": pages, "chars": chars,
            "msg": f"{len(docs)} 块 | {pages} 页 / {chars} 字"}

if __name__ == "__main__":
    items = list_sources()
    total = sum(n for _, n in items)
    print(f"集合 {COLLECTION}：" + (f"{total} 段" if items else "空"))
    for name, n in items:
        print(f"  - {name}  {n} 段")

