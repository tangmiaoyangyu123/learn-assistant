# 第 3 周 Day 1 实验台：Embedding 与余弦相似度（纯 Python，零依赖）
# 运行：python embedding_lab.py

import math


# ---------- 数学工具：全部手写，不用任何库 ----------

def dot(a, b):
    """点积：对应位置相乘再求和"""
    return sum(x * y for x, y in zip(a, b))          #zip的作用是一一对应，比如x坐标对应x坐标。


def norm(a):
    """向量的长度（模）"""
    return math.sqrt(dot(a, a))          #求模的长度，先平方再取根号。


def cosine(a, b):
    """余弦相似度：两个方向有多接近，与向量长短无关"""
    return dot(a, b) / (norm(a) * norm(b))          #就是求两个向量之间夹角的余弦值。余弦值为 1（方向完全相同）


def euclidean(a, b):
    """欧氏距离：两点的直线距离，受长短影响"""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))          #就是两点之间的距离。


# ---------- 手工造的词向量（3 维：可爱度 / 速度 / 机械感） ----------
# 真实模型是 384~4096 维、从海量语料学出来的；这里手工造 3 维是为了算得动、看得见。
# 数学完全一样，只是维度更少。

# WORDS = {
#     "小猫": [0.9, 0.2],
#     "小狗": [0.8, 0.35],
#     "猎豹": [0.3, 1.0],
#     "锤子": [0.1, 0.2],
#     "高铁": [0.05, 0.8],
#     "汽车": [0.1, 0.7],
# }

WORDS = {
    "小猫": [0.9, 0.2, 0.0],

    "小狗": [0.8, 0.35, 0.05],
    "猎豹": [0.3, 1.0, 0.1],
    "锤子": [0.1, 0.2, 0.95],
    "高铁": [0.05, 0.8, 0.9],
    "汽车": [0.1, 0.7, 0.85],
}

# 检索用的打分函数。观察任务 3 会让你把它换成 euclidean
SCORE_FN = cosine          #选择打分函数cosine 或者是 euclidean.
# SCORE_FN = euclidean


def bar(score: float) -> str:
    """把相似度画成简易条形图"""
    return "█" * int(max(score, 0) * 20)   #负分记为0，放大20倍，最后取整输出。


def rank(target: list, exclude: str = "") -> list:
    """按 SCORE_FN 对所有词打分，从高到低排序"""
    scored = [(w, SCORE_FN(target, v)) for w, v in WORDS.items() if w != exclude]          #target为小猫，排除，然后依次小猫计算其他物体的余弦相似值，cos越接近1，相似值越高。.item()输出键值。
    return sorted(scored, key=lambda x: x[1], reverse=True)           #reverse=True为从高到低排。key=lambda x是匿名函数，x[1]代表根据第二个大小进行排序。
#匿名函数：e.g: x + y：一般是构建add(),但也可以写成lambda x, y: x + y。

# def rank(target: list, exclude: str = "") -> list:
#     """按 SCORE_FN 对所有词打分，从高到低排序"""
#     scored = [(w, SCORE_FN(target, v)) for w, v in WORDS.items() if w != exclude]
#     return sorted(scored, key=lambda x: x[1], reverse=False)


# ========== 实验 1：谁和「小猫」最像？ ==========

print("=" * 50)
print("实验 1：谁和「小猫」最像？（余弦相似度）")
print("=" * 50)
for name, score in rank(WORDS["小猫"], exclude="小猫"):
    print(f"  {name}   {score:+.3f}  {bar(score)}")

# ========== 实验 2：方向 vs 距离 ==========

v_short = WORDS["小猫"]
v_long = [x * 10 for x in v_short]      # 每个数都乘 10，方向不变、长度变 10 倍

print()
print("=" * 50)
print("实验 2：同方向、长短不同的两个向量")
print("=" * 50)
print(f"  v_short = {v_short}")
print(f"  v_long  = {v_long}（每个数 ×10）")
print(f"  余弦相似度 = {cosine(v_short, v_long):+.3f}   <- 方向完全相同，给满分")
print(f"  欧氏距离   = {euclidean(v_short, v_long):.3f}    <- 距离却非常大")
print("  手算验证：dot(v_short, v_long) 和 norm(v_short)*norm(v_long)")
print("  是不是都同时放大了 10 倍？除法把它们约掉了 -> 余弦不受长度影响")

# ========== 实验 3：一次最小的「搜索」 ==========

QUERY = [0.15, 0.95, 0.2]               # 「跑得快的东西？」的手工向量

print()
print("=" * 50)
print(f"实验 3：检索「跑得快的东西？」-> 向量 {QUERY}")
print("=" * 50)
for name, score in rank(QUERY):
    print(f"  {name}   {score:+.3f}  {bar(score)}")
print()
print("  问题变成向量 -> 找最相关的 -> 返回内容")
print("  这就是 RAG 里 R（Retrieval 检索）的全部逻辑")

# ========== 观察任务（把答案写在下面注释里再提交） ==========
# 1. 实验 1：小狗和猎豹的分差主要来自第一、二维（可爱度和速度），
#    机械感这一维两者都很低，基本不参与分差。
#    删掉第三维后锤子从垫底反超猎豹（0.631 > 0.488）：因为锤子和小猫
#    最大的区别就是机械感 0.95，这个区别信息恰恰住在第三维里——删掉它
#    等于烧掉了"锤子不是猫"的证据，剩下的二维里锤子的方向反而和小猫
#    夹角更近。结论：Embedding 的质量取决于维度里装的是什么（能否区分
#    事物），而不是装了多少维。
# 2. 手算验证：dot(v_short, v_long) = 0.9×9.0 + 0.2×2.0 + 0×0 = 8.5；
#    norm(v_short) = √(0.81+0.04) ≈ 0.922；norm(v_long) = √(81+4) ≈ 9.220；
#    0.922 × 9.220 ≈ 8.5。分子是原来的 10 倍，分母也是原来的 10 倍，
#    8.5 ÷ 8.5 = 1.000 —— 长度在除法里被约掉了，所以余弦只看方向。
# 3. 改成 euclidean + reverse=False 后，检索结果不是完全相反：
#    猎豹仍排第一（距离 0.187），只有汽车和高铁互换了。
#    说明两个指标对差距大的候选判断一致，对接近的候选会抖。
#    踩坑记录：第一次跑出"完全相反"，是忘了把 reverse=True 改成 False，
#    程序按"距离越大越相关"排了序——反常结果先怀疑自己的改动，
#    再怀疑结论。
