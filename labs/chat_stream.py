import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com"
)

def chat_stream(question: str):
    """流式版：AI边生边打印"""
    response = client.chat.completions.create(
        model = "deepseek-chat",
        messages = [
            {"role" : "system" , "content":"你叫陈建宇,你是一位来自安徽大一学生，我是你的朋友，说话绅士内涵，比较谦虚，喜欢看小说。还有喜欢星穹铁道里的游戏角色丹恒"},
            {"role" : "user" , "content" : question}
        ],
        stream = True
    )
    print("AI:", end = "", flush = True)
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end = "", flush = True)
    print("\n")

if __name__ == "__main__":
    print("=== 流式AI助手已启动 ===")
    print("输入 quit 退出\n")
    while True:
        user_input = input("你：")
        if user_input.lower() == "quit":
            print("再见！")
            break
        chat_stream(user_input)
