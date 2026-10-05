"""第3周Day4: 文档切分实验台 — 同一篇文档的三种切法
复用 Day3 的 doc_loader：文档 → 文本 → 小块
"""
from doc_loader import load_md, load_pdf

CHUNK_SIZE = 300   # 每块目标字数（中文工程起点 200-500）
OVERLAP = 60       # 相邻块重叠字数（约 20%）

#优点：块的大小整齐，完整。
#缺点：会把一个句子从中间断开。
def split_fixed(text, size=CHUNK_SIZE):
    """切法A：定长硬切，不管句子死活"""
    return [text[i:i + size] for i in range(0, len(text), size)]

#优点：可以使上一段的断开句子在下一块完整的展现出来。
#缺点：会有赘余，块数和总字数都会增加。
def split_overlap(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """切法B：定长 + 重叠，给边界买保险"""
    chunks = []
    step = size - overlap
    for i in range(0, len(text), step):
        chunks.append(text[i:i + size])
        if i + size >= len(text):
            break
    return chunks


#优点：信息完整，语段完整。
#缺点：块的大小不一。
def split_by_structure(text):
    """切法C：按 Markdown 二级标题切（人写文档时的天然边界）"""
    chunks, current = [], []
    for line in text.splitlines():
        #判断是否为二级标题，line.startswith("## ")判断是否是 ##  开头。
        #and current: 如果文件一开始就是## 那么current还是空的，如果直接切，会生成一个空块所以只有已经收集的内容才切。
        if line.startswith("## ") and current:
            #将所有用换行符拼成一个字符串。
            #strip去掉首尾空白。
            chunks.append("\n".join(current).strip())
            #清空current，准备收集下一块。
            current = []
        current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks]



def report(name, chunks, show_index=1):
    """统一打印：块数 / 长度分布 / 第2块开头"""
    lens = [len(c) for c in chunks]
    print(f"--- {name} ---")
    print(f"块数 {len(lens)} | 总字数 {sum(lens)} | 平均 {sum(lens) // len(lens)} "
          f"| 最长 {max(lens)} | 最短 {min(lens)}")
    if show_index < len(chunks):
        print(f"第{show_index + 1}块开头 60 字: {chunks[show_index][:60]!r}")
    print()


if __name__ == "__main__":
    md = load_md("README.md")
    print("=========== README.md ===========")
    report("A 定长硬切", split_fixed(md))
    report("B 定长+重叠", split_overlap(md))
    report("C 按 ## 结构切", split_by_structure(md))

    pdf = load_pdf("test.pdf")
    print("=========== test.pdf ===========")
    report("A 定长硬切", split_fixed(pdf))
    report("B 定长+重叠", split_overlap(pdf))




