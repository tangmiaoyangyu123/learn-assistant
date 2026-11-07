"""学习助手 V2：跨程序记忆（对话历史存文件）"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

HISTORY_FILE = "chat_history.json"
DEFAULT_SYSTEM = "你是一个耐心的编程老师，回答简洁清晰，多举例子。"


def load_history() -> list:
    """启动时读档：文件存在就读，不存在就新建"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"role": "system", "content": DEFAULT_SYSTEM}]


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
    messages = load_history()

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
        if user_input.lower() == "new":
            messages = [{"role": "system", "content": DEFAULT_SYSTEM}]
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            print("（已开启全新对话）\n")
            continue
        if not user_input.strip():
            continue
        ask(user_input, messages)