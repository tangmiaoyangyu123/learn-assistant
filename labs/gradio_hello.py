r"""第4周Day4: Gradio 最小 Demo —— 理解"界面只是函数的壳"

Gradio 的三步走：
  1. 写一个普通 Python 函数（和界面完全无关）
  2. 用 gr.Interface 声明：fn 是哪个函数、inputs 有哪些控件、outputs 有哪些控件
  3. launch() 启动一个本地网页

运行：
  python gradio_hello.py
然后浏览器打开 http://127.0.0.1:7860

重点观察：greet() 里一行界面代码都没有。界面和数据逻辑是分开的。
"""
import gradio as gr

#写普通函数（和界面无关）
def greet(name, times):
    """普通函数：输入名字和次数，返回一段文字"""
    if not name:
        return "请先输入姓名。"
    return f"你好，{name}！\n" * int(times)

#声明界面怎么接这个函数。
#gr.Interface：我要做一个界面，这个界面是函数 fn 的壳
dmeo = gr.Interface(
    #壳里装了哪个函数。
    fn=greet,
    #注意 inputs 是个列表，里面有两个控件——因为 greet(name, times) 有两个参数。控件数量和顺序，必须和函数参数一一对应：
    #label：控件上方显示的标签文字
    #placeholder：灰色提示文字（用户还没输入时显示的占位符），提示"该填什么格式"
    #minimum=1, maximum=5：滑块范围是 1 到 5
    #value=1：默认值（页面一打开滑块就停在 1）
    #step=1：每拖一格跳 1（只能取 1、2、3、4、5 整数）
    #label：标签
    inputs=[
        gr.Textbox(label="你的名字", placeholder="例如：小缪"),
        gr.Slider(minimum=1, maximum=10, value=1, step=1, label="重复次数"),
    ],
    #函数的"输出"怎么显示
    outputs=gr.Textbox(label="回复", lines=5),
    #页面的标题和说明
    title="第一个 Gradio 应用",
    description="输入名字，点 Submit 试试。",
)

if __name__ == "__main__":
    dmeo.launch(inbrowser=True)

