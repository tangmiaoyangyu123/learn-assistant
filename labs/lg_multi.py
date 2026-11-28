import os
import json
import random
from datetime import datetime
from typing import TypedDict, Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import kb_manager
from search_docs import search, MAX_DISTANCE

load_dotenv()

MAX_TURNS = 5

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询当前的日期和时间。当用户问今天几号、现在几点、今天星期几时必须调用。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "计算两个数字的乘积。当用户问 123*456 这类算术题时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个乘数"},
                    "b": {"type": "number", "description": "第二个乘数"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "random_number",
            "description": "取一个 1 到 100 之间的随机整数。用户要求随机数时调用。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

llm_with_tools = llm.bind_tools(TOOLS)

SYSTEM_KB = (
    "你是学院综合测评问答助手。只根据给定的知识库资料回答，"
    "资料里没有的内容直接说没有，不要用常识补齐。"
)
SYSTEM_CHAT = "你是学院综合测评问答助手。正常回答用户的问题。"
SYSTEM_TOOLS = "涉及时间、算术、随机数时必须调用对应工具，不要自己心算或猜。"

POLICY_WORDS = ["综合测评", "综测", "德育", "智育", "身心", "能力素质",
                "加分", "扣分", "评奖", "评优", "奖学金", "素质测评"]


def execute(name, args_json):
    try:
        args = json.loads(args_json)
        if name == "get_current_time":
            now = datetime.now()
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return json.dumps({
                "now": now.strftime("%Y-%m-%d %H:%M:%S"),
                "weekday": weekdays[now.weekday()],
            }, ensure_ascii=False)
        if name == "multiply":
            return json.dumps({"result": int(args["a"]) * int(args["b"])}, ensure_ascii=False)
        if name == "random_number":
            return json.dumps({"result": random.randint(1, 100)}, ensure_ascii=False)
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int
    route: str
    context: str
    sources: list


def router(state: AgentState):
    question = state["messages"][-1].content
    hit = any(w in question for w in POLICY_WORDS)
    print(f"  [router] {question[:16]}... → {'kb' if hit else 'chat'}")
    return {"route": "kb" if hit else "chat", "turns": 0, "context": "", "sources": []}


def pick(state: AgentState) -> Literal["kb", "chat"]:
    return state["route"]


def kb(state: AgentState):
    question = state["messages"][-1].content
    hits = search(kb_manager.get_collection(), question, n=5)
    if not hits or hits[0][1] > MAX_DISTANCE:
        print(f"  [kb] 未命中（最近距离 {hits[0][1] if hits else 'N/A'}）")
        return {"context": "（知识库中没有检索到相关内容）", "sources": []}

    text = "\n\n".join(f"[第 {m.get('page')} 页] {d[:400]}" for d, _, m in hits)
    print(f"  [kb] 检索到 {len(hits)} 段，最近距离 {hits[0][1]:.3f}")
    return {
        "context": text,
        "sources": [{"page": m.get("page"), "distance": round(di, 3)} for _, di, m in hits],
    }


def llm_node(state: AgentState):
    sys = SYSTEM_KB if state["route"] == "kb" else SYSTEM_CHAT
    sys += "\n" + SYSTEM_TOOLS
    if state["context"]:
        sys += "\n\n以下是知识库资料，只根据它回答：\n" + state["context"]

    msgs = [SystemMessage(sys)] + list(state["messages"])
    print(f"  [llm] 第 {state.get('turns', 0) + 1} 次，system {len(sys)} 字，messages {len(msgs)} 条")
    r = llm_with_tools.invoke(msgs)
    return {"messages": [r], "turns": state.get("turns", 0) + 1}


def tools_node(state: AgentState):
    last = state["messages"][-1]
    out = []
    for call in last.tool_calls:
        print(f"  [tools] {call['name']}({call['args']})")
        out.append(ToolMessage(
            content=execute(call["name"], json.dumps(call["args"])),
            tool_call_id=call["id"],
        ))
    return {"messages": out}


def should_continue(state: AgentState):
    if state["turns"] >= MAX_TURNS:
        return "end"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "end"


graph = StateGraph(AgentState)
graph.add_node("router", router)
graph.add_node("kb", kb)
graph.add_node("llm", llm_node)
graph.add_node("tools", tools_node)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", pick, {"kb": "kb", "chat": "llm"})
graph.add_edge("kb", "llm")
graph.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "llm")

app = graph.compile(checkpointer=MemorySaver())


def ask(question, thread_id="u-1"):
    cfg = {"configurable": {"thread_id": thread_id}}
    out = app.invoke({"messages": [HumanMessage(question)],}, cfg)
    return out["messages"][-1].content, out["sources"]

if __name__ == "__main__":
    for q in ["综合测评成绩由哪几个模块组成，各占多少比例？",
              "123*456 等于多少？",
              "你好，你是谁？",
              "综测里的德育分怎么算？顺便帮我算一下 12 加 30 是多少。"]:
        print("=" * 60)
        print("问:", q)
        text, src = ask(q)
        print("答:", text[:300])
        if src:
            print("来源:", src)
