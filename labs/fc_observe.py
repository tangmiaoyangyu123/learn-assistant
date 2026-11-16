import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询当前的日期和时间。当用户问今天几号、现在几点、今天星期几时必须调用这个工具。",
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
]


def observe(question):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": question}],
        tools=TOOLS,
        temperature=0,
    )
    msg = resp.choices[0].message

    print("=" * 56)
    print("问题：", question)
    print("finish_reason：", resp.choices[0].finish_reason)
    print("content：", repr(msg.content))

    if not msg.tool_calls:
        print("→ 没有调用工具，模型直接回答了")
        return

    for tc in msg.tool_calls:
        print("工具名：", tc.function.name)
        print("参数原始值：", repr(tc.function.arguments))
        print("解析后的参数：", json.loads(tc.function.arguments))
        print("tool_call_id：", tc.id)


for q in ["今天几号？", "123*456 等于多少？", "你好，你是谁？"]:
    observe(q)


def execute(name, args_json):
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
    return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)


def run(question):
    messages = [{"role": "user", "content": question}]
    for _ in range(5):
        r = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS, temperature=0
        )
        m = r.choices[0].message
        if not m.tool_calls:
            return m.content
        messages.append(m)
        for tc in m.tool_calls:
            print(f"  [调用] {tc.function.name}({tc.function.arguments})")
            result = execute(tc.function.name, tc.function.arguments)
            print(f"  [结果] {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    return "超过最大轮数，已中止"


print("\n" + "#" * 60)
print(run("今天几号？"))
print(run("123*456 等于多少？"))
print(run("你好，你是谁？"))
