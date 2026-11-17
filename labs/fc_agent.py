import os
import json
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

import random

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


def run_agent(question, tools, max_turns=5):
    messages = [{"role": "user", "content": question}]
    requests_made = 0

    for turn in range(1, max_turns + 1):
        requests_made += 1
        print(f"[第 {turn} 轮] 请求（messages {len(messages)} 条）")

        r = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=tools, temperature=0
        )
        m = r.choices[0].message

        # ★ 唯一真正的出口：这一轮模型没要工具
        if not m.tool_calls:
            print(f"[结束] 共 {requests_made} 次请求")
            return m.content

        # 模型刚才那条"申请单"必须回填，否则下一轮 400
        messages.append({
            "role": "assistant",
            "content": m.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in m.tool_calls
            ],
        })

        # 逐个执行，结果按 id 回填
        for tc in m.tool_calls:
            print(f"  [调用] {tc.function.name}({tc.function.arguments})")
            result = execute(tc.function.name, tc.function.arguments)
            print(f"  [结果] {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return f"超过最大轮数 {max_turns}，已中止"


print("=" * 60)
print(run_agent("今天几号？", TOOLS))
print("=" * 60)
print(run_agent("123*456 等于多少？", TOOLS))
print("=" * 60)
print(run_agent("你好，你是谁？", TOOLS))
print("=" * 60)
print(run_agent("先调random number取一个数，再把这个数乘以37，告诉我结果。", TOOLS))
print("=" * 60)
