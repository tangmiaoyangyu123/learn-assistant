# 第 2 周 Day 3 实验台：同一个问题，四个角色，输出差多少？
# 运行前提：本目录下有 prompts.py 和 .env（含 DEEPSEEK_API_KEY）
# 用法：python role_compare.py

import os
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, RateLimitError, AuthenticationError
from prompts import PROMPTS

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def ask(system: str, question: str) -> str:
    """用指定的 system 回答问题，返回完整回复文本"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


# ========== 实验 1：同一个问题，四个角色 ==========
# 这个问题故意"万能"——每个角色都会给出完全不同的回答角度
QUESTION = "怎么学好编程？"

print("=" * 50)
print(f"实验 1：同一个问题问四个角色 ->「{QUESTION}」")
print("=" * 50)

for key, conf in PROMPTS.items():
    print(f"\n【{conf['name']}】")
    print("-" * 30)
    try:
        answer = ask(conf["system"], QUESTION)
        print(answer)
        print(f"（长度：{len(answer)} 字符）")
    except APIConnectionError:
        print("网络连接失败，请检查网络后再试")
    except RateLimitError:
        print("请求太频繁，等几秒重跑一次")
    except AuthenticationError:
        print("API Key 不对，检查 .env 里的 DEEPSEEK_API_KEY")
        break  # Key 错误继续跑也是白跑，直接退出
    except Exception as e:
        print(f"其他错误：{e}")

# ========== 实验 2：System Prompt 拆除对照 ==========
# 把 python 角色的 system 拆成 3 个版本，观察每个零件的作用。
# 控制变量：只有 system 不同，问题完全相同。

full_system = PROMPTS["python"]["system"]
bare_system = "你是Python老师。"                       # 只有角色，没有结构/约束
structure_only = (
    "回答按这个结构输出："
    "1) 一句话结论 2) 可运行的代码示例（带简短注释）3) 一个初学者最容易踩的坑。"
     "解释文字每段不超过 2 句、代码块不超过 12 行；"
    "不要输出与问题无关的背景介绍。"
)                                                       # 只有结构/约束，没有角色

Q2 = "什么是循环？"
structure_only = (                     # 原版，4 条约束
    "回答按这个结构输出："
    "1) 一句话结论 2) 可运行的代码示例（带简短注释）3) 一个初学者最容易踩的坑。"
    "解释文字每段不超过 2 句、代码块不超过 12 行；"
    "不要输出与问题无关的背景介绍。"
)

# 变体 A：删掉长度约束
structure_only_no_len = (
    "回答按这个结构输出："
    "1) 一句话结论 2) 可运行的代码示例（带简短注释）3) 一个初学者最容易踩的坑。"
    "不要输出与问题无关的背景介绍。"
)

# 变体 B：删掉禁止项
structure_only_no_ban = (
    "回答按这个结构输出："
    "1) 一句话结论 2) 可运行的代码示例（带简短注释）3) 一个初学者最容易踩的坑。"
    "解释文字每段不超过 2 句、代码块不超过 12 行；"
)
variants = [
    ("完整版", structure_only),
    ("删掉长度约束", structure_only_no_len),
    ("删掉禁止项", structure_only_no_ban),
]

print("\n" + "=" * 50)
print(f"实验 2：System Prompt 拆除对照 ->「{Q2}」")
print("=" * 50)

for name, system in variants:
    print(f"\n【{name}】")
    print("-" * 30)
    try:
        answer = ask(system, Q2)
        print(answer)
        print(f"（长度：{len(answer)} 字符）")
    except Exception as e:
        print(f"出错：{e}")

print("\n" + "=" * 50)
print("观察任务（把答案写在下面三行注释里再提交）：")
print("  1. 实验一中四个角色的回答角度、长度、结构有什么不同？")
print("  2. 实验二中，裸奔版少了什么？（对比结构项）")
print("  3. 无人格版和完整版的输出几乎一样吗？这说明了什么？")
# 1. 四个角色角度、长度、结构都不同：Python老师用三段教学结构（结论/代码/踩坑），
#    305字符；英语外教把问题当成英语句式练习来纠正（Good/Fix/Rule），333字符；
#    职业规划师给"结论+3条依据+本周动作"，还主动声明不编造行情，345字符；
#    Debug专家识别出这不是报错问题，拒绝按排查结构输出，只反问一个最具体的问题
#    （你卡在哪一步），121字符最短。——角色重新定义了"什么问题归我管"和"怎么理解问题"，
#    不只是换口吻。
# 2. 裸奔版（1110字符）少了结构约束和长度约束：没有"三段结构"管形状，没有
#    "每段不超过2句、代码不超过12行"管体积。于是模型默认按"写教程"模式输出——
#    Markdown大标题、两章循环讲解、break/continue、死循环警告、最后还反问要不要演示。
#    结构管形状，长度管体积，两个都没了体积就失控（1110 vs 245，差4.5倍）。
# 3. 几乎一样（112 vs 245，结构完全相同、只有细节差异）。说明对纯知识问答，
#    决定输出格式的是结构约束而不是角色人设——角色管回答的角度和语气，
#    指令管输出的格式和长度。所以写system时明确指令优先级高于角色设定。