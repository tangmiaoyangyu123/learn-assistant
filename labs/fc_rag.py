import json
import kb_manager
from search_docs import search, MAX_DISTANCE

from labs.fc_agent import run_agent

MAX_CHARS = 200      #每段能给模型看的字数，可以改，但要说明理由

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "检索本地知识库，内容是《学生素质综合测评实施细则》。"
                "当用户问到综测分数构成、加分项、德育/智育/身心/能力素质的评定标准、"
                "评奖评优规则时必须调用。不要凭记忆回答这类政策问题。"
                "与学院规定无关的问题（闲聊、算术、时间）不要调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索用的关键词。把用户口语化的问题改写成书面检索式。",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

def search_knowledge(query):
    """把本地知识库包装成工具。返回JSON字符串。"""
    collection = kb_manager.get_collection()
    hits = search(collection, query)

    if not hits:
        return json.dumps({"found": False, "reason": "知识库为空"}, ensure_ascii=False)

    best_dist = hits[0][1]

    if best_dist > MAX_DISTANCE:
        return json.dumps({
            "found": False,
            "reason": f"知识库中没有相关内容（最近距离 {best_dist:.3f} > 阈值 {MAX_DISTANCE}）"},
        ensure_ascii=False)

    results = []
    for doc, dist, meta in hits:
        results.append({
            "text": doc[:MAX_CHARS],
            "source": meta["source"],
            "page": meta.get("page"),
            "distance": round(dist, 3),
        })

    return json.dumps({"found": True, "hits": results}, ensure_ascii=False)

def execute(name, args_json):
    try:
        args = json.loads(args_json)
        if name == "search_knowledge":
            return search_knowledge(args["query"])
        return json.dumps({"error": f"未知工具：{name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}：{e}"}, ensure_ascii=False)

if __name__ == "__main__":
    print(run_agent("综合测评成绩由哪几个模块组成，各占多少比例？", TOOLS, executor=execute))
    print(run_agent("学校食堂几点关门？", TOOLS, executor=execute))
    print(run_agent("你好，你是谁？", TOOLS, executor=execute))
