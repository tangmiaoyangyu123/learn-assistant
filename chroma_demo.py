# 第 3 周 Day 2 实验台：chromadb 向量库入门
# 运行前提：pip install chromadb（已装 1.5.9）
# 首次运行会自动下载内置 Embedding 模型（约 80MB，只需一次）
# 用法：python chroma_demo.py

import chromadb

DB_PATH = "chroma_db"            # 数据库文件夹（自动创建，勿提交 git）
COLLECTION = "study_notes"          #数据库里的表名，一个client可以有很多collection，这里名字叫“study_notes”。

# ---------- 1. 建库：数据持久化在这个文件夹里 ----------
client = chromadb.PersistentClient(path=DB_PATH)          #创建一个持久化的客户端，PersistentClient代表将数据写到磁盘，而不是只储存在内存里，当程序退出时，数据chroma_db依然存在。
collection = client.get_or_create_collection(COLLECTION)          #创建名为“study_notes"的集合。

# ---------- 2. 存入文档：只给原文，向量自动生成 ----------
DOCS = [                                                           #向量库原始文档列表
    "Python 的 for 循环可以遍历列表、字符串等可迭代对象。",               #Chroma会自动把每一条文档转成向量，不需要手动算embedding。
    "列表推导式是一行代码生成列表的简洁写法。",
    "try except 用于捕获异常，防止程序崩溃。",
    "f-string 用花括号嵌入变量，是格式化字符串的首选方式。",
    "余弦相似度衡量两个向量方向的接近程度，常用于语义搜索。",
    "Embedding 把文字变成向量，意思相近的文字向量方向也相近。",
    "向量数据库用近似最近邻算法快速找出与查询最相似的向量。",
    "Git 的 commit 是一次快照，push 把快照同步到远程仓库。",
]
IDS = [f"doc_{i}" for i in range(len(DOCS))]           #给每一条文档生成唯一ID。

if collection.count() == 0:      # 防止重复运行时重复添加同一批文档
    collection.add(documents=DOCS, ids=IDS)          #document自动转成向量，将原文，ID，向量一起存进去。不需要自己写（embedding = encode(text)）
    print(f"已存入 {collection.count()} 条文档")
else:
    print(f"库中已有 {collection.count()} 条文档，跳过添加")

# ---------- 3. 语义检索：问题变向量，找最相似的 3 条 ----------
QUESTIONS = [
    "怎么防止程序报错崩掉",       # 正确答案：try except（和它没有一个词重叠！）
    "字符串格式化用什么写法",     # 正确答案：f-string
    "向量检索的原理是什么",       # 正确答案：embedding / 向量数据库
]

for q in QUESTIONS:          #遍历每一个问题，依次查询。
    result = collection.query(query_texts=[q], n_results=3)          #query_texts=[q]表示查询文本是一个列表，里面有一个问题q。用列表可以查询多个问题。n_results=3表示返回3个最相似的。
    print("=" * 50)
    print(f"问题：{q}")
    for doc_id, dist, doc in zip(                                           #解析查询结果
        result["ids"][0], result["distances"][0], result["documents"][0]
    ):
        print(f"  [{doc_id}] 距离 {dist:.3f} | {doc}")

# ========== 观察任务（答案写在下面注释里再提交） ==========
# 1. 查询 1 和正确答案文档没有一个词重叠，为什么还能排第一？
#    （提示：昨天实验 3 —— 问题变成向量后比的是方向）
# 2. 持久化验证：把 add 的 if 条件改成 if False（跳过添加）再跑一次，
#    count() 和查询结果还在吗？看看项目目录里多了哪个文件夹——数据存在哪？
# 3. 中文效果检验：在 QUESTIONS 里加一个口语化问题（如"代码老是出错咋整"），
#    看排序靠不靠谱——这是明天选模型的伏笔（内置模型是英文为主的）

