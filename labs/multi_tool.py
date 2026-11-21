"""周末项目：多功能助手（知识库 / 时间 / 算术 / 字数）"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

import kb_manager
from search_docs import search, MAX_DISTANCE
from labs.fc_agent import run_agent

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MAX_CHARS = 400

SYSTEM = (
    "你是学院综合测评问答助手，服务对象是本院学生。"
    "你能查本地知识库、报当前时间、做乘法、统计字数。"
    "规则："
    "1) 学院规定、综测、加分、评优这类政策问题，必须以知识库资料为准，并标注来源页码；"
    "2) 没有调用检索工具时，不要断言知识库里有什么或没有什么；"
    "3) 资料里没有的内容直接说没有，不要用常识补齐；"
    "4) 不确定就说不确定。"
)

REFUSAL = (
    "知识库里没有找到与这个问题相关的内容。"
    "建议查阅学院发布的最新版《学生素质综合测评实施细则》原文，或直接联系辅导员确认。"
)

POLICY_WORDS = [
    "综合测评", "综测", "德育", "智育", "身心", "能力素质",
    "加分", "扣分", "评奖", "评优", "奖学金", "素质测评",
]

PUNCT = set("，。！？、；：,.!?;:()（）【】「」《》" + '"' + "'")


def fn(name, desc, props=None, req=None):
    """工具定义的唯一构造函数：parameters 这一层不能少。"""
    return {"type": "function", "function": {
        "name": name,
        "description": desc,
        "parameters": {
            "type": "object",
            "properties": props or {},
            "required": req or [],
        },
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


# ---------- 工具实现：统一「收 args 字典，返回 JSON 字符串」 ----------

def tool_kb_search(args):
    collection = kb_manager.get_collection()
    hits = search(collection, args["query"], n=5)

    if not hits:
        return json.dumps({"found": False, "reason": "知识库为空，还没有上传文档"},
                          ensure_ascii=False)

    best_dist = hits[0][1]
    if best_dist > MAX_DISTANCE:
        return json.dumps({
            "found": False,
            "reason": f"知识库中没有相关内容（最近距离 {best_dist:.3f} > 阈值 {MAX_DISTANCE}）",
        }, ensure_ascii=False)

    results = []
    for doc, dist, meta in hits:
        results.append({
            "text": doc[:MAX_CHARS],
            "source": meta["source"],
            "page": meta.get("page"),
            "distance": round(dist, 3),
        })
    return json.dumps({"found": True, "hits": results}, ensure_ascii=False)


def tool_kb_list(_args):
    items = kb_manager.list_sources()          # [("test.pdf", 66)]
    docs = [{"name": name, "chunks": chunks} for name, chunks in items]
    return json.dumps({
        "documents": docs,
        "total_chunks": sum(chunks for _, chunks in items),
    }, ensure_ascii=False)


def tool_time_now(_args):
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return json.dumps({
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": weekdays[now.weekday()],
    }, ensure_ascii=False)


def tool_math_mul(args):
    # 模型可能按字符串传参，int() 是必须的（Day2 实测过）
    return json.dumps({"result": int(args["a"]) * int(args["b"])}, ensure_ascii=False)


def tool_text_count(args):
    text = args["text"]
    n = sum(1 for c in text if not c.isspace() and c not in PUNCT)
    return json.dumps({"count": n, "original": text}, ensure_ascii=False)


TOOL_IMPL = {
    "search_knowledge": tool_kb_search,
    "list_documents": tool_kb_list,
    "get_current_time": tool_time_now,
    "multiply": tool_math_mul,
    "count_text": tool_text_count,
}

_declared = {str(t["function"]["name"]) for t in TOOLS}
assert _declared == set(TOOL_IMPL), f"定义与实现不一致：{_declared ^ set(TOOL_IMPL)}"


def execute(name, args_json):
    try:
        args = json.loads(args_json or "{}")
        impl = TOOL_IMPL.get(name)
        if impl is None:
            return json.dumps({"error": f"未知工具：{name}"}, ensure_ascii=False)
        return impl(args)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}：{e}"}, ensure_ascii=False)


# ---------- 统一入口 ----------

def is_policy_question(question):
    return any(w in question for w in POLICY_WORDS)


def ask(question):
    if not is_policy_question(question):
        print("  [路径] 普通问题 → 模型自己决定")
        return run_agent(question, TOOLS, executor=execute, system=SYSTEM)

    print("  [路径] 政策问题 → 强制先检索")
    # 用原句检索：Day4 实测距离 0.608，top-3 里仍含正确段落（page 2）
    raw = execute("search_knowledge", json.dumps({"query": question}, ensure_ascii=False))
    data = json.loads(raw)
    print(f"  [检索] found={data.get('found')}")

    if not data.get("found"):
        return REFUSAL

    context = (
        "以下是知识库检索到的资料，请只根据这些资料回答；"
        "资料里没有的内容直接说没有，不要补充你自己的知识；"
        "标注来源页码。\n\n" + raw
    )
    return run_agent(question, TOOLS, executor=execute, system=SYSTEM, context=context)


def main():
    print("=" * 46)
    print("  多功能助手：知识库 / 时间 / 算术 / 字数")
    print("  输入 exit 退出")
    print("=" * 46)
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q in ("", "exit", "quit"):
            break
        try:
            print("助手>", ask(q))
        except Exception as e:
            print("助手> 出错了：", type(e).__name__, e)


if __name__ == "__main__":
    main()
