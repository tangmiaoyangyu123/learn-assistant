"""Prompt 四大技巧 · 对照实验台

用法：
    1) 把本文件复制到 D:\\PythonProject\\ 目录下
    2) 在 PyCharm 终端执行：  python prompt_lab.py
    3) 屏幕会依次打印 4 组 A/B 对照，跑完后生成 prompt_lab_results.md

设计说明：
    - 每组实验只改一个变量，其余全部固定（这就是"对照实验"）
    - temperature 固定为 0.3，压低随机性，让对比更公平
    - 异常处理沿用 assistant_v3.py 的写法：网络问题不会让程序崩掉
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, RateLimitError, AuthenticationError

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"
RESULT_FILE = "prompt_lab_results.md"

# 全局 token 计数器：成本意识要从第一天抓起
TOTAL_TOKENS = 0


def ask(system: str, user: str) -> tuple:
    """发一次请求，返回 (回答文本, 本次 token 用量)。"""
    global TOTAL_TOKENS

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,          # 压低随机性，对照才公平
        )
    except APIConnectionError:
        return "（网络出错了，请检查网络后重试）", 0
    except RateLimitError:
        return "（请求太快，稍等几秒再试）", 0
    except AuthenticationError:
        return "（API Key 配置有误，无法继续）", 0
    except Exception as e:
        return f"（其他错误：{e}）", 0

    tokens = response.usage.total_tokens if response.usage else 0
    TOTAL_TOKENS += tokens
    return response.choices[0].message.content, tokens


# ============================================================
# 实验 3 用到的长文本（放在这里，避免嵌在字典里看不清）
# ============================================================

FEWSHOT_TASK = """你的任务：把用户随口说的学习流水记录，整理成固定格式的卡片。

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
下一步：重看第 1 集并做笔记"""

FEWSHOT_INPUT = "今天下午看了异常处理，try except 基本懂了，但是 finally 还是不熟"


# ============================================================
# 四组对照实验
# ============================================================

EXPERIMENTS = [
    {
        "no": 1,
        "title": "角色设定（Role Prompting）",
        "question": "我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？",
        "a": {
            "label": "A · 无角色",
            "system": "你是一个助手。",
            "user": "我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？",
        },
        "b": {
            "label": "B · 有角色",
            "system": (
                "你是一位资深 DevOps 工程师，处理过大量密钥泄露事故。"
                "说话直接，先给结论再给步骤，不写安慰话和背景介绍。"
            ),
            "user": "我不小心把 .env 文件提交到 GitHub 了，里面是 API Key，现在该怎么办？",
        },
        "watch": "专业度、结构、语气：哪一版更像「内行」？哪一版在说废话？两版的信息密度差多少？",
    },
    {
        "no": 2,
        "title": "明确指令（Explicit Instruction）",
        "question": "解释 Python 的列表推导式。",
        "a": {
            "label": "A · 随口一问",
            "system": "你是一个助手。",
            "user": "解释一下 Python 的列表推导式",
        },
        "b": {
            "label": "B · 明确指令",
            "system": "你是一个助手。",
            "user": (
                "解释 Python 的列表推导式，严格按以下三段格式输出，不要多写任何其他内容：\n"
                "1) 一句话定义（不超过 30 字）\n"
                "2) 传统 for 循环写法 与 列表推导式写法 的代码对比\n"
                "3) 初学者最常踩的一个坑\n"
                "全篇不超过 200 字。不要出现与列表推导式无关的内容。"
            ),
        },
        "watch": "B 版是否老老实实按 1/2/3 输出？两版的字数差多少？token 用量差多少（越啰嗦越贵）？",
    },
    {
        "no": 3,
        "title": "Few-shot（给示例）",
        "question": "把一条学习流水记录整理成四段式卡片。",
        "a": {
            "label": "A · 无示例",
            "system": "你是一个助手。",
            "user": (
                "把用户的学习流水记录整理成「日期 | 主题 | 掌握程度 | 下一步」四段式卡片。\n\n"
                "记录：" + FEWSHOT_INPUT
            ),
        },
        "b": {
            "label": "B · 两个示例",
            "system": "你是一个助手。",
            "user": FEWSHOT_TASK + "\n\n现在整理这条：" + FEWSHOT_INPUT,
        },
        "watch": "两版的格式完全一致吗？字段名、标点、换行位置是否严格对齐？谁更「一模一样」？",
    },
    {
        "no": 4,
        "title": "思维链（Chain of Thought）",
        "question": "两道陷阱题（答案都是「反直觉」的那一个）",
        "a": {
            "label": "A · 直接问",
            "system": "你是一个助手。",
            "user": (
                "请回答下面两个问题：\n"
                "1. 如果 3 台机器 3 分钟能生产 3 个零件，那么 100 台机器生产 100 个零件需要多少分钟？\n"
                "2. 一根蜡烛烧掉一半需要 30 分钟，如果同时点燃 4 根一模一样的蜡烛并全部烧完，需要多久？"
            ),
        },
        "b": {
            "label": "B · 要求分步推理",
            "system": "你是一个助手。",
            "user": (
                "请一步一步分析下面每个问题：先写出题目给出的已知条件，再逐步推导，"
                "最后用「答案：」开头给出结论。不要跳步。\n\n"
                "1. 如果 3 台机器 3 分钟能生产 3 个零件，那么 100 台机器生产 100 个零件需要多少分钟？\n"
                "2. 一根蜡烛烧掉一半需要 30 分钟，如果同时点燃 4 根一模一样的蜡烛并全部烧完，需要多久？"
            ),
        },
        "watch": "正确答案：3 分钟 / 60 分钟。哪一版掉进了直觉陷阱？B 版的推理过程有几步？值得多花那些 token 吗？",
    },
]


def run_experiment(exp: dict) -> dict:
    """跑一组 A/B 对照，返回结果字典。"""
    bar = "=" * 66
    print(f"\n{bar}")
    print(f"实验 {exp['no']} · {exp['title']}")
    print(bar)
    print(f"问题：{exp['question']}\n")

    print(f"--- {exp['a']['label']} " + "-" * (60 - len(exp["a"]["label"])))
    text_a, tok_a = ask(exp["a"]["system"], exp["a"]["user"])
    print(text_a)

    print(f"\n--- {exp['b']['label']} " + "-" * (60 - len(exp["b"]["label"])))
    text_b, tok_b = ask(exp["b"]["system"], exp["b"]["user"])
    print(text_b)

    print(f"\n[观察] {exp['watch']}")
    print(f"[用量] A: {tok_a} tokens   |   B: {tok_b} tokens   |   差 {tok_b - tok_a:+d}")

    return {
        "no": exp["no"],
        "title": exp["title"],
        "question": exp["question"],
        "label_a": exp["a"]["label"],
        "prompt_a": exp["a"]["user"],
        "text_a": text_a,
        "tok_a": tok_a,
        "label_b": exp["b"]["label"],
        "prompt_b": exp["b"]["user"],
        "text_b": text_b,
        "tok_b": tok_b,
        "watch": exp["watch"],
    }


def write_markdown(results: list):
    """把全部结果写成一份可对比的 Markdown 报告。"""
    lines = [
        "# Prompt 四大技巧 · 对照实验结果",
        "",
        f"> 模型：{MODEL}　temperature：0.3　总用量：{TOTAL_TOKENS} tokens",
        "> 由 prompt_lab.py 自动生成，可反复运行对比。",
        "",
        "## 用量速览",
        "",
        "| 实验 | A 版 tokens | B 版 tokens | 差值 |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['no']} · {r['title']} | {r['tok_a']} | {r['tok_b']} | {r['tok_b'] - r['tok_a']:+d} |"
        )

    lines += ["", "> 注意：B 版 tokens 更多≠更差。多出来的部分是「买」到了更稳定的格式、更准的推理。", ""]

    for r in results:
        lines += [
            "---",
            "",
            f"## 实验 {r['no']} · {r['title']}",
            "",
            f"**问题**：{r['question']}",
            "",
            f"### {r['label_a']}（{r['tok_a']} tokens）",
            "",
            "**发给模型的 Prompt：**",
            "",
            "```text",
            r["prompt_a"],
            "```",
            "",
            "**输出：**",
            "",
            r["text_a"],
            "",
            f"### {r['label_b']}（{r['tok_b']} tokens）",
            "",
            "**发给模型的 Prompt：**",
            "",
            "```text",
            r["prompt_b"],
            "```",
            "",
            "**输出：**",
            "",
            r["text_b"],
            "",
            f"**观察提示**：{r['watch']}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 我的结论（自己填，这才是今天的产出）",
        "",
        "1. 角色设定：",
        "2. 明确指令：",
        "3. Few-shot：",
        "4. 思维链：",
        "",
    ]

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[完成] 全部结果已保存到 {RESULT_FILE}")
    print(f"[用量] 本次共消耗 {TOTAL_TOKENS} tokens")


if __name__ == "__main__":
    print("=" * 66)
    print("  Prompt 四大技巧 · 对照实验台")
    print("=" * 66)
    print(f"  模型：{MODEL}　实验数：{len(EXPERIMENTS)} 组（共 {len(EXPERIMENTS) * 2} 次请求）")
    print("  预计耗时 1-2 分钟，请稍等……")

    all_results = []
    for exp in EXPERIMENTS:
        all_results.append(run_experiment(exp))

    write_markdown(all_results)
