"""第一个AI对话程序"""
#1.文件头和导入
import os
from dotenv import load_dotenv
from openai import OpenAI

#2.拿Key，造连接器
#打开.env文件，将内部的内容读进内存。
load_dotenv()

#client相当于一个电话，创造Ai链接对象
client = OpenAI(
    #api_key相当于身份证，os.getenvs
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    #base_url是服务器地址，告诉程序别连OpenAI官方，去连deep seek的服务器。
    base_url="https://api.deepseek.com"
)


def chat(question: str) -> str:
    #相当于打电话
    response = client.chat.completions.create(
        #表示使用的是哪个模型
        model="deepseek-chat",
        #"role":"system"是身份的系统设定，相当于“员工手册”。
        #"content"设定AI性格。
        #question是函数传过来的参量，相当于我输入的文字。
        messages=[
            {"role": "system", "content": "你是一个温柔的人。"},
            {"role": "user", "content": question}
        ]
    )
    # print(response)在下一行代码运行前，这个会出现乱码。
    #response.choices回答列表，一般只有一个。
    #message回答的这个消息体，比如我和AI对话，我发消息或者AI发消息。同时也是一个结构体。
    #content 最终所需要的文字，也就是对话内容
    return response.choices[0].message.content or ""


