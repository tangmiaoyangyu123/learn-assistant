
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

messages = [
    {"role": "system", "content": "你是一个耐心的编程老师，回答简洁清晰，多举例子。"}
]


def ask(question: str):
    """带记忆的流式对话"""
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True
    )

    print("AI: ", end="", flush=True)
    full_answer = ""                       # 攒完整回答
    for chunk in response:
        piece = chunk.choices[0].delta.content
        if piece:
            print(piece, end="", flush=True)
            full_answer += piece           # 边打字边攒
    print("\n")

    messages.append({"role": "assistant", "content": full_answer})


if __name__ == "__main__":
    print("=" * 40)
    print("  命令行学习助手 V1")
    print("  (多轮对话 + 流式输出)")
    print("=" * 40)
    print("输入 quit 退出\n")

    while True:
        try:
            user_input = input("你: ")
        except EOFError:
            break
        if user_input.lower() == "quit":
            print("再见！")
            break
        if not user_input.strip():
            continue
        ask(user_input)