#==AI学习助手==
import os
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError , RateLimitError, AuthenticationError

#添加环境变量，会在当前目录寻找.env文件，找到AIP_Key并会作为环境变量（后续os.geienv会进行环境变量读取），若不存在.env文件
#不会报错，将会忽略此步骤
load_dotenv()

#创建客户端
#api_key读取deepseek的API_Key，若为None，后面会报401错误。
#base——url覆盖OpenAI默认的请求地址，改为指向Deepseek的服务器，这是Deepseek兼容OpenAI SDK的关键。
#创建后，client就成为了具有Deepseek的OpenAI风格客户端。
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#定义对话函数
#user_input: str 类型注解，说明穿入的是字符串。 -> str 表示的是返回值为字符串。
def chat(user_input: str) -> str:
    #调用API
    #response = client.chat.completions.create是OpenAI SDK的标准聊天窗口，向服务器发HTTP POST请求
    try:
        response = client.chat.completions.create(
            #model表示的是模型，目前Deepseek有“deepseek-chat”通用对话和“deepseek-reasoner”推理模型。
            model="deepseek-chat",
            #messages是消息列表每一条消息就是一条字典。
            messages=[
                #role 表示的是角色
                #system 是系统提示，代表AI的性格或是行为规范
                #user 用户说的话
                {"role": "system", "content": "你是一个耐心的编程老师，回答简洁清晰。"},
                {"role": "user", "content": user_input}
            ]
        )
    except APIConnectionError:
        print("网络连接失败，请检查网络后再试")
        return "（网络出错了，请重试）"
    except RateLimitError:
        print("请求太频繁了，等几秒再试")
        return "（请求太快，稍等几秒再试）"
    except AuthenticationError:
        print("API Key 不对，检查.env里的 DEEPSEEK_API_KEY")
        return "（Key 配置有误，无法继续）"
    except Exception as e:
        print(f"其他错误：{e}")
        return "未知错误，请重试"

    return response.choices[0].message.content

if __name__ == "__main__":
    print("=== AI助手已启动 ===")
    print("输入 quit 退出\n")
    while True:
        user_input = input("你: ")
        if user_input.lower() == "quit":
            print("再见！")
            break
        answer = chat(user_input)
        print(f"AI: {answer}\n")