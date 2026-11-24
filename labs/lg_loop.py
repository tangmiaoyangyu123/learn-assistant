from typing import TypedDict, Annotated

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

SCRIPT = [
    AIMessage(content="", tool_calls=[
        {"name": "multiply", "args": {"a": 123, "b": 456}, "id": "c1"}
    ]),
    AIMessage(content="", tool_calls=[
        {"name": "multiply", "args": {"a": 56088, "b": 2}, "id": "c2"}
    ]),
    AIMessage(content="112176"),
]

MAX_TURNS = 5

class FakeLLM:
    """按顺序吐预设消息，用来单独测图结构，不发请求。"""

    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        m = SCRIPT[min(self.calls, len(SCRIPT) - 1)]
        self.calls += 1
        print(f"  [fake-llm] 第 {self.calls} 次调用，收到 {len(messages)} 条")
        return m


class LoopState(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int

fake = FakeLLM()

#调用模型，把结果送回状态
def call_model(state:LoopState):
    msgs = list(state["messages"])
    m = fake.invoke(msgs)
    return {"messages": [m], "turns": state["turns"] + 1}

#取出要调用工具的消息，遍历其中的调用、执行工具把结果转成字符串且使用正确的id，把结果作为列表返回。
def tools_node(state: LoopState):
    last = state["messages"][-1]
    out = []
    for call in last.tool_calls:
        print(f"  [tools] 执行 {call['name']}({call['args']})")
        result = call["args"]["a"] * call["args"]["b"]
        out.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return {"messages": out}

#循环的「刹车 + 分流器」—— 判断"该停还是该继续"，返回下一个节点名。
def should_continue(state: LoopState):
    #护栏，避免无限循环烧钱。
    if state["turns"] >= MAX_TURNS:
        return "end"
    #取最后一条消息
    last = state["messages"][-1]
    #判断是否有工具调用
    if getattr(last, "tool_calls", None):
        return "tools"
    return "end"

graph = StateGraph(LoopState)
graph.add_node("llm", call_model)
graph.add_node("tools", tools_node)
graph.add_edge(START, "llm")
graph.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "llm")

app = graph.compile()

if __name__ == "__main__":
    out = app.invoke({"messages": [HumanMessage("123*456 等于多少")], "turns": 0})
    print("最终消息数 =", len(out["messages"]), " turns =", out["turns"])
    for m in out["messages"]:
        print(" ", type(m).__name__, "|", repr(m.content))