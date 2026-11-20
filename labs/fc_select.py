"""Day4 实验：5 个工具时，模型选哪个"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def fn(name, desc, props=None, req=None):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props or {}, "required": req or []},
    }}


TOOLS = [
    fn("search_knowledge",
       "检索本地知识库，内容是《学生素质综合测评实施细则》。当用户问到综测分数构成、加分项、"
       "德育/智育/身心/能力素质的评定标准、评奖评优规则时必须调用。不要凭记忆回答这类政策问题。"
       "与学院规定无关的问题（闲聊、算术、时间）不要调用。",
       {"query": {"type": "string",
                  "description": "检索用的关键词。把用户口语化的问题改写成书面检索式。"}},
       ["query"]),
    fn("list_documents",
       "列出知识库里有哪些文档，以及每个文档被切成了多少块。用户问知识库里有什么文件时调用。"),
    fn("get_current_time",
       "查询当前的日期和时间。当用户问今天几号、现在几点、今天星期几时调用。"),
    fn("multiply",
       "计算两个数字的乘积。当用户问两个数相乘等于多少时调用。",
       {"a": {"type": "number", "description": "第一个乘数"},
        "b": {"type": "number", "description": "第二个乘数"}},
       ["a", "b"]),
    fn("count_text",
       "统计一段文字的字数（不含空格和标点）。用户问某段话有多少字时调用。",
       {"text": {"type": "string", "description": "要统计的文字"}},
       ["text"]),
]

TOOLS_PREFIXED = [
    fn("kb_search",
       "检索本地知识库，内容是《学生素质综合测评实施细则》。当用户问到综测分数构成、加分项、"
       "德育/智育/身心/能力素质的评定标准、评奖评优规则时必须调用。不要凭记忆回答这类政策问题。"
       "与学院规定无关的问题（闲聊、算术、时间）不要调用。",
       {"query": {"type": "string",
                  "description": "检索用的关键词。把用户口语化的问题改写成书面检索式。"}},
       ["query"]),
    fn("kb_list",
       "列出知识库里有哪些文档，以及每个文档被切成了多少块。用户问知识库里有什么文件时调用。"),
    fn("time_now",
       "查询当前的日期和时间。当用户问今天几号、现在几点、今天星期几时调用。"),
    fn("math_mul",
       "计算两个数字的乘积。当用户问两个数相乘等于多少时调用。",
       {"a": {"type": "number", "description": "第一个乘数"},
        "b": {"type": "number", "description": "第二个乘数"}},
       ["a", "b"]),
    fn("text_count",
       "统计一段文字的字数（不含空格和标点）。用户问某段话有多少字时调用。",
       {"text": {"type": "string", "description": "要统计的文字"}},
       ["text"]),
]

QUESTIONS = [
    "知识库里有哪些文件？",
    "综合测评德育素质怎么评？",
    "今天几号？",
    "帮我数一下「今天天气不错」这句话有多少字",
    "学校食堂几点关门？",
]


def probe(tools, label):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    for q in QUESTIONS:
        r = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": q}],
            tools=tools,
            temperature=0,
        )
        m = r.choices[0].message
        picked = [tc.function.name for tc in (m.tool_calls or [])]
        print(f"{q}\n    → {picked if picked else '(不调用，直接回答)'}")


def by_name(name):
    """按名字从 TOOLS_PREFIXED 里取工具定义"""
    return next(t for t in TOOLS_PREFIXED if t["function"]["name"] == name)


def pick_tools(question):
    """按问题返回候选工具子集；拿不准就返回全部。"""
    # 知识库域
    if any(w in question for w in ["知识库", "文件", "文档", "综合测评", "测评",
                                   "德育", "智育", "身心", "能力", "加分", "扣分",
                                   "评优", "奖学金"]):
        if any(w in question for w in ["文件", "文档", "有哪些"]):
            return [by_name("kb_list")]
        return [by_name("kb_search"), by_name("kb_list")]

    # 时间域
    if any(w in question for w in ["几号", "几点", "星期", "时间", "日期"]):
        return [by_name("time_now")]

    # 算术域
    if any(w in question for w in ["乘", "×", "*"]):
        return [by_name("math_mul")]

    # 文本域
    if any(w in question for w in ["多少字", "字数"]):
        return [by_name("text_count")]

    return TOOLS_PREFIXED          # 拿不准 → 全部给


def probe_picked():
    print(f"\n{'=' * 70}\n实验 4：裁剪后的工具集\n{'=' * 70}")
    for q in QUESTIONS:
        sub = pick_tools(q)
        names = [t["function"]["name"] for t in sub]
        print(f"{q}\n    给模型 {len(sub)} 个: {names}")
        r = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": q}],
            tools=sub,
            temperature=0,
        )
        m = r.choices[0].message
        picked = [tc.function.name for tc in (m.tool_calls or [])]
        print(f"    → {picked if picked else '(不调用，直接回答)'}")


if __name__ == "__main__":
    probe(TOOLS, "实验 1：完整 description（5 个工具）")

    # 实验 2：只削弱 search_knowledge 的描述，其余不动
    weak = json.loads(json.dumps(TOOLS))
    weak[0]["function"]["description"] = "检索知识库。"
    probe(weak, "实验 2：search_knowledge 描述削弱成「检索知识库。」")

    # 实验 3：全部加前缀
    probe(TOOLS_PREFIXED, "实验 3：全部加前缀")

    # 实验 4：工具集裁剪
    probe_picked()
