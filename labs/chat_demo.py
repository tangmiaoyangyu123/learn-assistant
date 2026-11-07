"""第5周 Day2 最小 Demo：多轮对话

核心设计（也是今天最重要的一课）：
    数据层  gr.State      →  存一份"干净"的历史 [{"role":…, "content": "文字"}]
    显示层  gr.Chatbot    →  只管把历史画出来，不参与业务

为什么不用 Chatbot 组件直接当历史存？
    实测（gradio 6.29.1）：Chatbot 传给函数的历史里，content 是【列表】而不是字符串，
    形如 [{"text": "你好", "type": "text"}]。取出来直接拼进 prompt 会得到一堆垃圾字符。
    自己用 State 存，格式完全可控。

运行：python chat_demo.py
"""

import gradio as gr


def chat(message, history):
    """history 是我们自己维护的干净列表：[{"role": "user", "content": "文字"}, …]"""
    print("history[0] =", history[0] if history else "(空)")
    print("content 的类型 =", type(history[0]["content"]).__name__ if history else "-")
    print(f"[服务端] history 有 {len(history)}")
    if not message or not message.strip():
        return history, "", history          # 空输入：什么都不做

    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": f"你说的是「{message}」，这是第 {len(history) // 2 + 1} 轮"},
    ]
    # 三个返回值 → 对应三个 outputs：新历史、清空输入框、给 Chatbot 显示
    return new_history, "", new_history


with gr.Blocks(title="最小多轮对话") as demo:
    gr.Markdown(
        "## 最小多轮对话\n"
        "历史存在 `gr.State` 里，`Chatbot` 只负责显示。连问两句，看它记不记得住。"
    )

    hist = gr.State([])                                # 数据层
    chatbot = gr.Chatbot(label="对话", height = 320)     # 显示层
    msg = gr.Textbox(label="输入", placeholder="说点什么…", lines=2)

    with gr.Row():
        send = gr.Button("发送", variant="primary")
        clear = gr.Button("清空对话")

    send.click(chat, inputs=[msg, hist], outputs=[hist, msg, chatbot])
    msg.submit(chat, inputs=[msg, hist], outputs=[hist, msg, chatbot])
    clear.click(lambda: ([], [], []), outputs=[hist, chatbot, msg])


if __name__ == "__main__":
    demo.launch()
