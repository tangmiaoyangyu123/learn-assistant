r"""学习助手 V2 主程序

功能：多轮式对话 + 4 角色转换 + 历史存档 + 三层异常保护
    1.网络错误：APIConnectionEorror 等分类捕捉，失败自动回滚用户消息
    2.优雅退出：KeyboardInterrupt 全局补获， 退出前save_history
    3.文件损坏：load_history 捕获 JSONDecodeError ，坏文件为.bak

角色 system 统一由 prompts.py build_system 模板拼接（v3）
修改对话逻辑前先跑三连破坏测试：断网/Ctrl+C/改坏 chat_history.json

"""
import json                             #JSON 序列化/反序列化 Python的对象（list，dict）与JSON相互转化，用于存档，读档
import os                               #标准库，下列有具体用法
from json import JSONDecodeError        #判断不合法异常
from dotenv import load_dotenv          #读取.env文件，将里面的键值加载至环境变量中
from openai import (
    OpenAI,                             #客户端类，Deepseek兼容OpenAI，所以可以直接使用这个SDk
    APIConnectionError,                 #网络错误，超时等连接层错误
    RateLimitError,                     #请求太频繁，被限流（HTTP 429）
    AuthenticationError                 #API Key无效或过期（HTTP 401）
)
from prompts import PROMPTS

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#存档文件名
HISTORY_FILE = "chat_history.json"


#启动读档
def load_history(system_prompt: str) -> list:
    """启动时读档：文件存在就读，不存在就新建"""
    try:
        if os.path.exists(HISTORY_FILE):                          #判断文档是否存在
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:  #打开文档，“r”：只读，utf-8保证中文不乱码。with在代码块结束会会自动关闭文件
                return json.load(f)                               #将文件内容解析为list
        return [{"role": "system", "content": system_prompt}]
    except JSONDecodeError:
        os.replace(HISTORY_FILE, HISTORY_FILE + ".bak")
        print(f"历史文件已损坏，已备份为{HISTORY_FILE}.bak")
        return [{"role": "system", "content": system_prompt}]


def save_history(messages: list):
    """每轮对话后存档"""
    #“w” ：清空原文件再写，全量覆盖，每次都是把messages写进去
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        #messages与f 对象序列化直接写入文件对象
        #ensure_ascii=False中文原样写入，方便人类阅读
        #indent=2 每层缩进两个空格，方便阅读
        json.dump(messages, f, ensure_ascii=False, indent=2)


def ask(question: str, messages: list):
    """带记忆的流式对话"""
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
        )
    except APIConnectionError:
        messages.pop()
        print("网络连接失败，请检查网络后再试")
        return "（网络出错了，请重试）"
    except RateLimitError:
        messages.pop()
        print("请求太频繁了，等几秒再试")
        return "（请求太快，稍等几秒再试）"
    except AuthenticationError:
        messages.pop()
        print("API Key 不对，检查.env里的 DEEPSEEK_API_KEY")
        return "（Key 配置有误，无法继续）"
    except Exception as e:
        messages.pop()
        print(f"其他错误：{e}")
        return "未知错误，请重试"

    print("AI: ", end="", flush=True)                          #flush强制刷新缓冲区，保证立即显示
    full_answer = ""                                           #累积完整的回复，最后要存进历史
    try:
        for chunk in response:
            piece = chunk.choices[0].delta.content             #OpenAI 格式的流式响应结构
            if piece:                                          #有些chunk的content为None，要跳过
                print(piece, end="", flush=True)               #逐字打印
                full_answer += piece
    except APIConnectionError:
        messages.pop()
        print("\n（传输中断，网络不稳定）")
        return "（回复中断，请重试）"
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

    try:
        while True:
            try:
                user_input = input("你: ")
            except EOFError:
                break
            if user_input.lower() == "quit":
                break

            if user_input in PROMPTS:
                current_key = user_input
                messages = [{"role": "system", "content":PROMPTS[user_input]["system"]}]
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
                print(f"（已切换为{PROMPTS[current_key]['name']}， 新对话开始）\n")
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
    except KeyboardInterrupt:
        save_history(messages)
        print("\n (已保存对话历史） 再见！")
