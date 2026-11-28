import os, json, random
from datetime import datetime
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

import kb_manager
from search_docs import search, MAX_DISTANCE      # 别再自己写 300 / 1.1

load_dotenv()
MAX_TURNS = 5
MAX_CHARS = 400

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
            "name": "kb_search",
            "description": "检索学院综合测评实施细则。当问题涉及综测、德育、智育、身心、能力素质、加分、扣分、评奖评优、奖学金等校内规定时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，用空格分隔，不要用疑问句"},
                },
                "required": ["query"],
            },
        },
    },
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
    }
]

SYSTEM = ("你可以调用工具。涉及学院综合测评的规定必须先用 kb_search 检索，"
          "资料里没有就说没有，不要用常识补齐。涉及时间、算术、随机数时也必须调用对应工具。")

def execute(name, args_json):
    try:
        args = json.loads(args_json)
        if name == "kb_search":
            hits = search(kb_manager.get_collection(), args["query"], n=5)
            if not hits or hits[0][1] > MAX_DISTANCE:
                return json.dumps({"found": False, "message": "知识库中没有相关内容"},
                                  ensure_ascii=False)
            return json.dumps({
                "found": True,
                "hits": [{"page": m.get("page"), "distance": round(di, 3),
                          "text": doc[:MAX_CHARS]} for doc, di, m in hits],
            }, ensure_ascii=False)

        if name == "get_current_time":
            now = datetime.now()
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return json.dumps({
                "now": now.strftime("%Y-%m-%d %H:%M:%S"),
                "weekday": weekdays[now.weekday()],
            }, ensure_ascii=False)
        if name == "multiply":
            return json.dumps({"result": args["a"] * args["b"]})
        if name == "random_number":
            return json.dumps({"value": random.randint(1, 100)})
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

# State / call_model / tools_node / should_continue：从 lg_agent.py 整段拷，一行不改
llm_with_tools = llm.bind_tools(TOOLS)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int

def call_model(state: AgentState):
    msgs = [SystemMessage(SYSTEM)] + list(state["messages"])
    r = llm_with_tools.invoke(msgs)
    return {"messages": [r], "turns": state["turns"] + 1}

def tools_node(state: AgentState):
    last = state["messages"][-1]
    out = []
    for call in last.tool_calls:
        print(f"  [tools] {call['name']}({call['args']})")
        out.append(ToolMessage(content=execute(call["name"], json.dumps(call["args"])), tool_call_id=call["id"]))
    return {"messages": out}

def should_continue(state: AgentState):
    if state["turns"] >= MAX_TURNS:
        return "end"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "end"


graph = StateGraph(AgentState)
graph.add_node("llm", call_model)
graph.add_node("tools", tools_node)
graph.add_edge(START, "llm")
graph.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "llm")

app = graph.compile(checkpointer=MemorySaver())


def ask(question, thread_id="u-1"):
    cfg = {"configurable": {"thread_id": thread_id}}
    out = app.invoke({"messages": [HumanMessage(question)], "turns": 0}, cfg)
    return out["messages"][-1].content

if __name__ == "__main__":
    QS = [
        "综合测评成绩由哪几个模块组成，各占多少比例？",
        "食堂几点开门？",
        "综测里德育分怎么算？另外帮我算下 12 加 30。",
        "我校的奖学金由哪个银行代发",
    ]

    for q in QS:
        print("=" * 60)
        print("问：", q)
        print("答：", ask(q))