import os
import json
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from datetime import datetime



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

SYSTEM = "你可以调用工具。涉及时间、算术、随机数时必须调用对应工具，不要自己心算或猜。"

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
            return json.dumps({"result": args["a"] * args["b"]})
        if name == "random_number":
            return json.dumps({"value": random.randint(1, 100)})
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    except Exception as e:
        # 工具内部崩了也不让整个 Agent 挂掉：把异常转成字符串交给模型决策
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

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

app = graph.compile()

def ask(question):
    out = app.invoke({"messages": [HumanMessage(question)], "turns": 0})
    return out["messages"][-1].content


if __name__ == "__main__":
    for q in ["今天几号？",
              "123*456 等于多少？",
              "你好，你是谁？",
              "先调 random_number 取一个数，再把这个数乘以 37，告诉我结果。"]:
        print("=" * 60)
        print("问:", q)
        print("答:", ask(q))