# 导入 gradio
#
# def fn(参数们):                    ← 4 个参数，顺序和 inputs 一致
#     拼字符串 → 返回它
#
# with gr.Blocks() as demo:
#     标题（Markdown）
#
#     dropdown = ______              ← 选一个：文字单选是哪个组件？
#     slider   = ______              ← 数字、范围 0~10、初始 3
#     text     = ______              ← 2 行
#     checks   = ______              ← 多选，选项 ["红","绿","蓝"]
#
#     btn = ______                   ← 按钮，文字"提交"
#     out = ______                   ← 输出，显示那行结果
#
#     # 绑事件
#     ___.click(___, inputs=[___], outputs=___)
#
# demo.launch()

import gradio as gr

def fn(dropdown, slider, text, checks):
    return f"下拉={dropdown} | 滑块={slider} | 文本={text} | 多选={checks}"

with gr.Blocks() as demo:
    gr.Markdown("组件练习台")

    dropdown = gr.Dropdown(choices = ["A", "B", "C"], label="选一个：")
    slider = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="平滑滑块")
    text = gr.Textbox(label="填写文字：",lines=2)
    checks = gr.CheckboxGroup(choices=["红", "绿", "蓝"], label="可多选")

    btn = gr.Button("提交", variant="primary")
    out = gr.Textbox(label="结果", lines=3)

    btn.click(fn, inputs=[dropdown, slider, text, checks], outputs=[out])

demo.launch()