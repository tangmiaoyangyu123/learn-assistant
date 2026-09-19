import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com/"
)

#messages 是一个数组，储存的是字典
#将代码放在外面才能将对话记忆起来，在内部会刷新，
messages = [
            {"role" : "system", "content" : "你是原神派蒙。"}
        ]
def chat_with_memony(question: str) -> str:
    messages.append({"role" : "user", "content" : question})
    response = client.chat.completions.create(
        model = "deepseek-chat",
        messages = messages
    )
    answer = response.choices[0].message.content

    messages.append({"role" : "assistant", "content" : answer})

    return answer

if __name__ == "__main__":
    print("=== AI助手已启动 ===")
    print("输入 quit 退出\n")
    while True:
        user_input = input("你: ")
        if user_input.lower() == "quit":
            print("再见！")
            break
        #将字符串格式化，去掉字符串外的双引号
        answer = chat_with_memony(user_input)
        print(f"AI: {answer}\n")