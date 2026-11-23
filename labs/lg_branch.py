import json
import os
from typing import TypedDict, Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import kb_manager
from search_docs import search, MAX_DISTANCE

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)

SYSTEM_KB = (
    "你是学院综合测评问答助手。只根据给定的知识库资料回答，"
    "资料里没有的内容直接说没有，不要用常识补齐。"
)
SYSTEM_CHAT = (
    "你是学院综合测评问答助手。正常回答用户的问题；"
    "涉及学院政策、综测、评优时，说明需要检索知识库。"
)

POLICY_WORDS = ["综合测评", "综测", "德育", "智育", "身心", "能力素质",
                "加分", "扣分", "评奖", "评优", "奖学金", "素质测评"]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    route: str          # router 写，条件边读
    sources: list       # kb 节点写，最后打印用

#作为【分流器】：判断是普通聊天还是知识库检索。
def router(state: AgentState):
    #在对话历史中取最后一句话，也就是用户的问题
    question = state["messages"][-1].content
    #判断问题中含不含政治元素，只要命中就是 True
    hit = any(w in question for w in POLICY_WORDS)
    print(f"  [router] {question[:20]}... → {'kb' if hit else 'chat'}")
    return {"route": "kb" if hit else "chat"}

#作为【检索节点】：拿用户的问题去查知识库，把查到的资料变成一条 system 消息塞进对话，同时把来源记到 state 里。
def kb(state: AgentState):
    question = state["messages"][-1].content
    hits = search(kb_manager.get_collection(), question, n=5)
    if not hits or hits[0][1] > MAX_DISTANCE:
        return {"messages": [("system", "知识库中没有检索到相关内容。")], "sources": []}

    text = "\n\n".join(f"[第 {m.get('page')} 页] {d[:400]}" for d, _, m in hits)
    print(f"  [kb] 检索到 {len(hits)} 段，最近距离 {hits[0][1]:.3f}")
    return {
        "messages": [("system", f"以下是知识库资料，只根据它回答：\n\n{text}")],
        "sources": [{"page": m.get("page"), "distance": round(di, 3)} for _, di, m in hits],
    }

#保证这一轮对话，不会带有上一句对话的残余。
def chat(state: AgentState):
    print("  [chat] 不检索，直接回答")
    return {"messages": [], "sources": []}


def answer(state: AgentState):
    sys = SYSTEM_KB if state["route"] == "kb" else SYSTEM_CHAT
    #拼消息：全局系统提示 + 历史消息（含 kb 塞进去的资料）
    msgs = [SystemMessage(sys)] + list(state["messages"])
    #llm 是 LangChain 封装的模型客户端（类似你手写的 client.chat.completions.create）
    #invoke 是同步调用
    r = llm.invoke(msgs)
    return {"messages": [r]}


#Literal["kb", "chat"] 这是给类型检查器和 IDE 看的：声明“我只会返回这两个值之一”。
def pick(state: AgentState) -> Literal["kb", "chat"]:
    return state["route"]


graph = StateGraph(AgentState)
graph.add_node("router", router)
graph.add_node("kb", kb)
graph.add_node("chat", chat)
graph.add_node("answer", answer)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", pick, {"kb": "kb", "chat": "chat"})
graph.add_edge("kb", "answer")
graph.add_edge("chat", "answer")
graph.add_edge("answer", END)

app = graph.compile()


def ask(question):
    out = app.invoke({"messages": [("user", question)], "route": "", "sources": []})
    return out["messages"][-1].content, out["sources"]


if __name__ == "__main__":
    for q in ["综合测评成绩由哪几个模块组成，各占多少比例？",
              "123*456 等于多少？"]:
        print("=" * 60)
        print("问:", q)
        text, src = ask(q)
        print("答:", text[:300])

        if src:
            print("来源:", src)