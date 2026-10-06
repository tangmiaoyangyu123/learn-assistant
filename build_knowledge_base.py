r"""第3周Day5: 知识库构建流水线 — 文档 → 切分 → 中文向量化 → 入库（带元数据）

用法：python build_knowledge_base.py
前置：本文件与 chinese_embedding.py / chunk_lab.py / doc_loader.py 在同一目录，
      且项目里有 test.pdf、README.md

链路：PdfReader / load_md  →  split_overlap  →  ChineseEmbedding  →  chromadb
"""
from pathlib import Path

import chromadb
from pypdf import PdfReader

from chinese_embedding import MODEL_DIR, ChineseEmbedding
from chunk_lab import split_overlap
from doc_loader import load_md

#将所有的数据写道当前目录chroma_db/文件夹。
DB_PATH = "chroma_db"
#集合名client的collection。
COLLECTION = "kb_zh"      # 新集合：只放中文模型的向量，不与 Day2 的 study_notes 混
#要入库的文件列表，顺序就是处理顺序。
SOURCE_FILES = ["test.pdf", "README.md"]

MIN_CHARS_PER_PAGE = 50   # 工程防御阈值：每页低于这个字符数就怀疑是扫描件
                          # 文字版中文 PDF 通常每页 400-1500 字，扫描件是 0

#这是一个生成器函数。
#stats：是外部传入的字典，用来收集统计信息。
def chunks_from_pdf(path, stats=None):
    """按页读 PDF，逐页切块 —— 这样才能把真实页码写进 metadata

    stats: 传入一个 dict 时，函数会把 {'pages': 页数, 'chars': 提取到的字符数}
           写进去，供调用方判断这份 PDF 是不是扫描件（图片型，提不出文字）。
    """
    #打开PDf。
    reader = PdfReader(path)
    if stats is not None:
        stats["pages"] = len(reader.pages)
    chars = 0
    #记录页数，从一开始。
    for page_no, page in enumerate(reader.pages, 1):
        #提取当前页文字，累加字符数。
        text = page.extract_text() or ""
        chars += len(text)
        #将文本进行切块
        #i：是当前页数所对应的序号。
        for i, chunk in enumerate(split_overlap(text)):
            #过滤纯空白块。
            if chunk.strip():                      # 页码残渣之类的空块丢掉
                #yield返回两样：文本块和元数据字典
                yield chunk, {"source": Path(path).name, "page": page_no, "chunk": i}
    #生成器结束后统计，跑完才有chars。
    if stats is not None:                          # 生成器跑完才执行到这里
        stats["chars"] = chars


def chunks_from_md(path, stats=None):
    """Markdown 没有页的概念，page 记 0"""
    text = load_md(path)
    if stats is not None:
        stats.update(pages=0, chars=len(text))
    for i, chunk in enumerate(split_overlap(text)):
        if chunk.strip():
            yield chunk, {"source": Path(path).name, "page": 0, "chunk": i}


#主流程
def main():
    #创建embedding实例，加载tokenizer和ONNX模型。
    zh = ChineseEmbedding(MODEL_DIR)
    #链接Chromadb，用客户端持久化，把数据写道chroma_db。
    client = chromadb.PersistentClient(path=DB_PATH)

    #删除旧集合，知识库是派生数据，重建更安全。
    #有except是因为第一次运行集合不存在。
    try:                                            # 重建而不是增量补：知识库是派生数据
        client.delete_collection(COLLECTION)
        print(f"[重建] 已删除旧集合 {COLLECTION}")
    except Exception:
        print(f"[新建] 集合 {COLLECTION} 尚不存在")

    # 关键：必须显式传 embedding_function，否则会用回内置英文模型（Day2 的坑）
    #创建或获取集合。
    collection = client.get_or_create_collection(COLLECTION, embedding_function=zh)

    #准备收集容器
    docs, metas, ids = [], [], []                   # 文本块 / 元数据 / 唯一id
    failed, suspect = [], []                        # 提取失败 / 可疑的来源
    #遍历源文件
    for name in SOURCE_FILES:
        path = Path(name)
        if not path.exists():
            print(f"[跳过] {name} 不存在")
            continue

        stats = {}
        gen = (chunks_from_pdf(path, stats) if path.suffix.lower() == ".pdf"
               else chunks_from_md(path, stats))
        n = 0
        for chunk, meta in gen:
            docs.append(chunk)
            metas.append(meta)
            ids.append(f"{meta['source']}-p{meta['page']}-c{meta['chunk']}")
            n += 1

        # ---------- 工程防御：提取质量自检 ----------
        pages, chars = stats.get("pages", 0), stats.get("chars", 0)
        per_page = chars // pages if pages else chars
        if n == 0:
            print(f"[失败] {name}: 0 块 —— 一个字都没提取到")
            print("       很可能是扫描件（图片型 PDF），需要 OCR 转文字后才能入库")
            failed.append(name)
        elif pages and per_page < MIN_CHARS_PER_PAGE:
            print(f"[可疑] {name}: {n} 块，但平均每页仅 {per_page} 字符")
            print("       文字版 PDF 通常每页 400+ 字，建议人工打开翻一页核对")
            suspect.append(name)
        else:
            where = f"{pages} 页, " if pages else ""
            print(f"[加载] {name}: {n} 块（{where}共 {chars} 字符）")

    if not docs:
        print("\n没有任何文档可入库 —— 检查 SOURCE_FILES 里的文件名和位置是否正确")
        if failed:
            print(f"提取失败的来源：{failed}（如果是扫描件，需先做 OCR）")
        return

    collection.add(documents=docs, ids=ids, metadatas=metas)

    lens = [len(d) for d in docs]
    print("\n" + "=" * 56)
    print(f"入库完成，集合 {COLLECTION} 现有 {collection.count()} 条")
    print(f"块长：平均 {sum(lens) // len(lens)} | 最长 {max(lens)} | 最短 {min(lens)}")
    print(f"来源：{sorted({m['source'] for m in metas})}")
    print("=" * 56)

    # 只要还有来源没进来，就在最后再喊一次 —— 别让失败被成功的日志淹没
    if failed:
        print(f"\n⚠️  有 {len(failed)} 个来源没有进入知识库：{failed}")
        print("   处理方式：用扫描类 App 的「导出文字版 PDF」重导，或接 OCR 后再加入 SOURCE_FILES")
    if suspect:
        print(f"\n⚠️  有 {len(suspect)} 个来源提取质量可疑：{suspect}")


if __name__ == "__main__":
    main()
