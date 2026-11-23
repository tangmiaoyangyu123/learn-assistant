from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    steps: Annotated[list, operator.add]     # ← 追加，不是覆盖


def node_a(state: State):
    print("  [a] 收到:", dict(state))
    return {"text": state["text"] + "-a", "steps": ["a"]}


def node_b(state: State):
    print("  [b] 收到:", dict(state))
    return {"text": state["text"] + "-b", "steps": ["b"]}


graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")
graph.add_edge("a", "b")
graph.add_edge("b", END)

app = graph.compile()

print("=== invoke ===")
print(app.invoke({"text": "x", "steps": []}))

print("=== stream ===")
for chunk in app.stream({"text": "x", "steps": []}):
    print("  step:", chunk)

print("=== 图结构 ===")
print(app.get_graph().draw_mermaid())