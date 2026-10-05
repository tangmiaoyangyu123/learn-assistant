"""第3周Day3: 文档加载实验台 — TXT / Markdown / PDF 统一变成字符串
RAG 第一步：把真实世界的文档读进 Python
"""

#1.把资料读进来。
#2.清洗，切块。
#3.变成向量存起来，
#4.用户提问时先检索相关资料。
#5。然后把资料和问题一起交给大模型生成答案。

#Path 为路径操作，更加简洁，不用手动关闭文件。
#pypdf 是为了读取pdf。
from pathlib import Path
from pypdf import PdfReader


def load_txt(path):
    """读 TXT：必须指定 utf-8（Windows 默认 GBK 是经典大坑）"""
    #read.text()一次性读取整个文件内容，指定utf-8。
    return Path(path).read_text(encoding="utf-8")


def load_md(path):
    #.md文件会有一级标题，二级标题等结构符号，这里忽略保留原样。
    """读 Markdown：本质是文本文件，结构符号先原样保留"""
    return Path(path).read_text(encoding="utf-8")


def load_pdf(path):
    """读 PDF：pypdf 按页提取，每页加个来源标记"""
    #PdfReader()打开整个pdf文件。
    reader = PdfReader(path)
    #pages 装每页文本，提取的每一页文字都装填进去。
    pages = []
    #enumerate 会同时给出
    # i：索引，从零开始。   page：当前页面对象。
    for i, page in enumerate(reader.pages):
        #page.extract_text 提取当前页文字，若提取失败，返回None
        text = page.extract_text() or ""  # 防御：有的页可能提取出 None
        pages.append(f"【第{i+1}页】\n{text}")
    #将所有页拼成字符串，用“\n”拼接起来。
    return "\n".join(pages)


if __name__ == "__main__":
    # 1) TXT：先自己造一个测试文件
    Path("test_doc.txt").write_text(
        "RAG 是检索增强生成：先查资料，再回答问题。\n"
        "两阶段：检索（Retrieval）+ 生成（Generation）。\n",
        encoding="utf-8",
    )
    print("=== TXT ===")
    print(load_txt("test_doc.txt"))

    # 2) Markdown：就用你 GitHub 项目的 README
    print("=== Markdown ===")
    md = load_md("README.md")
    print(f"共 {len(md)} 字符，前 200 字：\n{md[:200]}")

    # 3) PDF：随便找一个 PDF 重命名为 test.pdf 放进项目文件夹
    try:
        pdf = load_pdf("test.pdf")
        print("=== PDF ===")
        print(f"共提取 {len(pdf)} 字符，前 300 字：\n{pdf[:300]}")
    except FileNotFoundError:
        print("=== PDF === 未找到 test.pdf，先跳过（找个 PDF 重命名后再跑）")
