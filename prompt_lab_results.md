# Prompt 四大技巧 · 对照实验结果

> 模型：deepseek-chat　temperature：0.3　总用量：3510 tokens
> 由 prompt_lab.py 自动生成，可反复运行对比。

## 用量速览

| 实验 | A 版 tokens | B 版 tokens | 差值 |
|---|---|---|---|
| 1 · 角色设定（Role Prompting） | 650 | 459 | -191 |
| 2 · 明确指令（Explicit Instruction） | 1041 | 191 | -850 |
| 3 · Few-shot（给示例） | 110 | 193 | +83 |
| 4 · 思维链（Chain of Thought） | 378 | 488 | +110 |

> 注意：B 版 tokens 更多≠更差。多出来的部分是「买」到了更稳定的格式、更准的推理。

---

## 实验 1 · 角色设定（Role Prompting）

**问题**：我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？

### A · 无角色（650 tokens）

**发给模型的 Prompt：**

```text
我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？
```

**输出：**

# 紧急处理步骤

## 1. 立即撤销/轮换 API Key（最重要！）

**这是第一优先级**，比清理 Git 历史更紧急。因为：
- 即使你删除了提交，GitHub 的缓存、fork、爬虫、第三方镜像可能已经抓取了
- 有专门的机器人 24 小时扫描 GitHub 上的密钥

所以**立刻去对应平台作废旧 Key 并生成新的**：
- OpenAI / Anthropic / AWS / Stripe 等平台后台
- 检查账单，看有没有异常调用

## 2. 从 Git 历史中彻底删除

仅仅 `git rm .env` 再提交是**没用的**，历史里还在。

### 方法 A：git-filter-repo（推荐）

```bash
# 安装
pip install git-filter-repo

# 从所有历史中删除该文件
git filter-repo --path .env --invert-paths

# 强制推送
git push origin --force --all
git push origin --force --tags
```

### 方法 B：BFG Repo-Cleaner（更简单）

```bash
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

### 方法 C：如果仓库是私有的且刚提交

如果只是最近一次提交，且没别人 clone：

```bash
git rm --cached .env
git commit --amend
git push --force
```

## 3. 联系 GitHub 支持（可选）

如果仓库是公开的，可以联系 GitHub Support 请求清理缓存，但**不要依赖这个**，轮换 Key 才是根本。

## 4. 防止再次发生

**添加到 .gitignore：**
```
.env
.env.*
*.env
```

**使用模板文件：**
- 提交 `.env.example`（只有 key 名，没有值）
- 真实值放本地 `.env`

**安装 pre-commit 钩子：**
```bash
pip install pre-commit detect-secrets
```
`.pre-commit-config.yaml`：
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

**其他工具：**
- `git-secrets`（AWS 出品）
- `gitleaks`
- GitHub 的 **Secret Scanning**（公开仓库免费开启）

## 关键提醒

⚠️ **顺序很重要**：先轮换 Key，再清理历史。因为清理历史需要时间，而密钥泄露的每一分钟都可能被利用。

⚠️ **force push 会影响协作者**，如果团队协作，提前通知大家重新 clone。

需要我针对某个具体平台（比如 OpenAI、AWS）说明怎么轮换 Key 吗？

### B · 有角色（459 tokens）

**发给模型的 Prompt：**

```text
我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？
```

**输出：**

**立刻撤销密钥，别管 Git 历史。**

## 立即执行（按顺序）

1. **去服务商后台吊销/轮换这个 API Key**——这是唯一真正止血的动作。GitHub 上的东西可能已经被爬虫抓走了，改历史没用。
2. **生成新 Key**，更新到本地 `.env` 和所有部署环境（CI/CD、服务器、Vercel 等）。
3. **确认旧 Key 已失效**，调一次 API 验证返回 401。

## 然后清理 Git

4. 如果只是最近一次 commit：
   ```bash
   git rm --cached .env
   echo ".env" >> .gitignore
   git commit -m "remove .env"
   git push
   ```
   注意：**历史里还在**，只是当前分支不再追踪。

5. 如果要彻底从历史抹掉（仓库是公开的、或敏感度高）：
   ```bash
   # 用 git-filter-repo（推荐，bfg 也行）
   pip install git-filter-repo
   git filter-repo --path .env --invert-paths
   git push --force
   ```
   强制推送后通知所有协作者重新 clone，否则他们会把旧历史推回来。

6. **联系 GitHub Support** 请求清除缓存的 commit（fork、PR 引用、API 缓存不会因为 force push 消失）。公开仓库尤其要做。

## 事后

7. 加 pre-commit hook 防再犯：
   ```bash
   pip install pre-commit detect-secrets
   ```
   或用 `gitleaks` 扫全仓库。
8. 检查这个 Key 有没有被滥用——看服务商的用量/账单/日志，有异常就报警。

**核心原则：密钥一旦进了公开仓库，就当它已经泄露。改历史是给未来看的，不是给现在止血的。**

**观察提示**：专业度、结构、语气：哪一版更像「内行」？哪一版在说废话？两版的信息密度差多少？

---

## 实验 2 · 明确指令（Explicit Instruction）

**问题**：解释 Python 的列表推导式。

### A · 随口一问（1041 tokens）

**发给模型的 Prompt：**

```text
解释一下 Python 的列表推导式
```

**输出：**

# Python 列表推导式（List Comprehension）

列表推导式是 Python 中一种**简洁、优雅**地创建列表的语法，它可以用一行代码替代传统的 `for` 循环 + `append` 的写法。

## 基本语法

```python
[表达式 for 变量 in 可迭代对象 if 条件]
```

## 一、基础用法

### 1. 传统写法 vs 列表推导式

```python
# 传统写法
squares = []
for x in range(5):
    squares.append(x ** 2)
# [0, 1, 4, 9, 16]

# 列表推导式
squares = [x ** 2 for x in range(5)]
# [0, 1, 4, 9, 16]
```

### 2. 带条件过滤

```python
# 只保留偶数
evens = [x for x in range(10) if x % 2 == 0]
# [0, 2, 4, 6, 8]
```

### 3. 带 if-else 的表达式

注意：这里的 `if-else` 是**表达式**，位置在 `for` 前面。

```python
result = [x if x % 2 == 0 else -x for x in range(5)]
# [0, -1, 2, -3, 4]
```

## 二、进阶用法

### 1. 嵌套循环

```python
pairs = [(x, y) for x in [1, 2] for y in ['a', 'b']]
# [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]
```

等价于：

```python
pairs = []
for x in [1, 2]:
    for y in ['a', 'b']:
        pairs.append((x, y))
```

### 2. 嵌套推导式（矩阵转置）

```python
matrix = [[1, 2, 3], [4, 5, 6]]
transposed = [[row[i] for row in matrix] for i in range(3)]
# [[1, 4], [2, 5], [3, 6]]
```

### 3. 处理字符串

```python
words = ["hello", "world", "python"]
lengths = [len(w) for w in words]
# [5, 5, 6]

upper = [w.upper() for w in words]
# ['HELLO', 'WORLD', 'PYTHON']
```

## 三、相关的推导式

Python 还有类似的推导式：

```python
# 集合推导式
s = {x ** 2 for x in range(5)}       # {0, 1, 4, 9, 16}

# 字典推导式
d = {x: x ** 2 for x in range(3)}    # {0: 0, 1: 1, 2: 4}

# 生成器表达式（惰性求值，节省内存）
g = (x ** 2 for x in range(5))
```

## 四、优缺点

**优点：**
- 代码更简洁、可读性高
- 通常比普通 `for` 循环**更快**（C 层优化）

**缺点：**
- 逻辑复杂时可读性变差
- 嵌套过深时难以理解

## 五、使用建议

✅ **适合**：简单的转换、过滤操作

```python
[x.strip() for x in lines if x]
```

❌ **不适合**：逻辑复杂、有副作用（如打印、修改外部变量）

```python
# 不推荐：逻辑太复杂
result = [f(x) if cond1(x) else g(x) for x in data if cond2(x) and cond3(x)]
```

这种情况下，用普通 `for` 循环反而更清晰。

## 六、性能对比

```python
import timeit

# 列表推导式
t1 = timeit.timeit('[x**2 for x in range(1000)]', number=10000)

# 普通循环
t2 = timeit.timeit('''
result = []
for x in range(1000):
    result.append(x**2)
''', number=10000)

print(f"推导式: {t1:.4f}s, 循环: {t2:.4f}s")
# 推导式通常快 20%~40%
```

---

**一句话总结**：列表推导式是 Python 的"语法糖"，用一行代码完成"遍历 + 转换 + 过滤"的常见模式，简洁高效，但要注意别写得太复杂。

### B · 明确指令（191 tokens）

**发给模型的 Prompt：**

```text
解释 Python 的列表推导式，严格按以下三段格式输出，不要多写任何其他内容：
1) 一句话定义（不超过 30 字）
2) 传统 for 循环写法 与 列表推导式写法 的代码对比
3) 初学者最常踩的一个坑
全篇不超过 200 字。不要出现与列表推导式无关的内容。
```

**输出：**

1) 用简洁语法从可迭代对象生成新列表。

2) 传统：
r=[]
for x in range(3):
 r.append(x*x)
推导式：
r=[x*x for x in range(3)]

3) 坑：在推导式中修改外部变量，如 `[i for i in range(3) if i<2]` 后误以为 `i` 仍可用；Python 3 中 `i` 不会泄漏到外部。

**观察提示**：B 版是否老老实实按 1/2/3 输出？两版的字数差多少？token 用量差多少（越啰嗦越贵）？

---

## 实验 3 · Few-shot（给示例）

**问题**：把一条学习流水记录整理成四段式卡片。

### A · 无示例（110 tokens）

**发给模型的 Prompt：**

```text
把用户的学习流水记录整理成「日期 | 主题 | 掌握程度 | 下一步」四段式卡片。

记录：今天下午看了异常处理，try except 基本懂了，但是 finally 还是不熟
```

**输出：**

日期 | 主题 | 掌握程度 | 下一步
--- | --- | --- | ---
今天下午 | 异常处理 | try except 基本懂了，finally 还不熟 | 重点练习 finally 的用法，搞清楚它在有无异常、有无 return 时的执行顺序

### B · 两个示例（193 tokens）

**发给模型的 Prompt：**

```text
你的任务：把用户随口说的学习流水记录，整理成固定格式的卡片。

参考示例：

输入：昨天装了 pandas，能读 csv 了
输出：
日期：昨天
主题：pandas 安装与 csv 读取
掌握程度：能独立完成
下一步：练习 groupby 聚合

输入：前天看的 3Blue1Brown，向量那里有点晕
输出：
日期：前天
主题：3Blue1Brown 线性代数（向量）
掌握程度：概念模糊
下一步：重看第 1 集并做笔记

现在整理这条：今天下午看了异常处理，try except 基本懂了，但是 finally 还是不熟
```

**输出：**

日期：今天下午  
主题：异常处理（try-except 与 finally）  
掌握程度：try-except 基本掌握，finally 尚不熟练  
下一步：重点练习 finally 的使用场景并做相关练习

**观察提示**：两版的格式完全一致吗？字段名、标点、换行位置是否严格对齐？谁更「一模一样」？

---

## 实验 4 · 思维链（Chain of Thought）

**问题**：两道陷阱题（答案都是「反直觉」的那一个）

### A · 直接问（378 tokens）

**发给模型的 Prompt：**

```text
请回答下面两个问题：
1. 如果 3 台机器 3 分钟能生产 3 个零件，那么 100 台机器生产 100 个零件需要多少分钟？
2. 一根蜡烛烧掉一半需要 30 分钟，如果同时点燃 4 根一模一样的蜡烛并全部烧完，需要多久？
```

**输出：**

好的，我们一步一步来推理这两个问题。  

---

**问题 1：**  
已知：3 台机器 3 分钟能生产 3 个零件。  
先看一台机器的情况：  
3 台机器 3 分钟做 3 个零件 → 意味着 3 台机器一起工作，每 3 分钟产出 3 个零件，也就是每台机器每 3 分钟做 1 个零件。  
所以一台机器的速度是：1 个零件 / 3 分钟。  

那么 100 台机器一起工作，速度是 100 台 × (1 个零件 / 3 分钟) = 100 个零件 / 3 分钟。  
也就是说，100 台机器一起工作，3 分钟就能生产 100 个零件。  

所以答案是 **3 分钟**。

---

**问题 2：**  
一根蜡烛烧掉一半需要 30 分钟，那么烧完整根蜡烛需要 60 分钟。  
现在同时点燃 4 根一模一样的蜡烛，它们是同时燃烧的，所以每根都是 60 分钟烧完。  
4 根同时烧完的时间依然是 60 分钟，不会因为数量增加而延长或缩短。  

所以答案是 **60 分钟**。

---

**最终答案：**  
1. 3 分钟  
2. 60 分钟

### B · 要求分步推理（488 tokens）

**发给模型的 Prompt：**

```text
请一步一步分析下面每个问题：先写出题目给出的已知条件，再逐步推导，最后用「答案：」开头给出结论。不要跳步。

1. 如果 3 台机器 3 分钟能生产 3 个零件，那么 100 台机器生产 100 个零件需要多少分钟？
2. 一根蜡烛烧掉一半需要 30 分钟，如果同时点燃 4 根一模一样的蜡烛并全部烧完，需要多久？
```

**输出：**

好的，我们一步一步来分析。  

---

### **第1题**
**已知条件：**
- 3 台机器 3 分钟能生产 3 个零件。

**逐步推导：**
1. 3 台机器 3 分钟生产 3 个零件 → 意味着 3 台机器一起工作，3 分钟做 3 个零件。  
2. 那么 3 台机器 1 分钟能生产 1 个零件（因为 3 个零件 ÷ 3 分钟 = 1 个/分钟）。  
3. 由此可知，1 台机器 1 分钟能生产 1/3 个零件。  
4. 现在有 100 台机器，一起工作 1 分钟能生产 100 × (1/3) = 100/3 个零件。  
5. 要生产 100 个零件，所需时间 = 100 ÷ (100/3) = 100 × (3/100) = 3 分钟。  

所以依然是 3 分钟。

**答案：** 3 分钟。

---

### **第2题**
**已知条件：**
- 一根蜡烛烧掉一半需要 30 分钟。
- 同时点燃 4 根一模一样的蜡烛，并全部烧完。

**逐步推导：**
1. 烧掉一半要 30 分钟 → 说明烧完整根蜡烛需要 60 分钟。  
2. 同时点燃 4 根蜡烛，它们是独立燃烧的，并不会因为数量多而加快或减慢燃烧速度。  
3. 每根蜡烛都需要 60 分钟烧完，它们是同时点燃的，所以全部烧完也只需要 60 分钟。  

**答案：** 60 分钟。

**观察提示**：正确答案：3 分钟 / 60 分钟。哪一版掉进了直觉陷阱？B 版的推理过程有几步？值得多花那些 token 吗？

---

## 我的结论（自己填，这才是今天的产出）

1. 角色设定：
2. 明确指令：
3. Few-shot：
4. 思维链：
