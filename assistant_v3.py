import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from prompts import PROMPTS

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

HISTORY_FILE = "chat_history.json"


def load_history(system_prompt: str) -> list:
    """启动时读档：文件存在就读，不存在就新建"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"role": "system", "content": system_prompt}]


def save_history(messages: list):
    """每轮对话后存档"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def ask(question: str, messages: list):
    """带记忆的流式对话"""
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True
    )

    print("AI: ", end="", flush=True)
    full_answer = ""
    for chunk in response:
        piece = chunk.choices[0].delta.content
        if piece:
            print(piece, end="", flush=True)
            full_answer += piece
    print("\n")

    messages.append({"role": "assistant", "content": full_answer})
    save_history(messages)


if __name__ == "__main__":
    current_key = "python"
    messages = load_history(PROMPTS[current_key]["system"])

    print("=" * 40)
    print("  学习助手 V2（跨程序记忆版）")
    print("=" * 40)
    print("输入 quit 退出 | new 重新开始\n")

    while True:
        try:
            user_input = input("你: ")
        except EOFError:
            break
        if user_input.lower() == "quit":
            break

        if user_input in PROMPTS:
            current_key = user_input
            messanges = [{"role": "system", "content":PROMPTS[user_input]["system"]}]
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            print(f"（以切换为{PROMPTS[current_key]['name']}， 新对话开始）\n")
            continue

        if user_input.lower() == "new":
            messages = [{"role": "system", "content": PROMPTS[current_key]["system"]}]
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            print("（已开启全新对话）\n")
            continue
        if not user_input.strip():
            continue
        ask(user_input, messages)