import gradio as gr

def fn(q):
    return f"（假答案）你问的是：{q}", "（假来源）test.pdf 第1页"

with gr.Blocks() as demo:
    with gr.Tab("问题"):
        inp = gr.Textbox(label="你的问题", lines=2)
        btn = gr.Button(value="提问", variant="primary")
        ans = gr.Textbox(label="回答", lines=12, buttons=["copy"])  #buttons=["copy"]就是加一键复制的按钮。
        src = gr.Textbox(label="检索来源（top4）", lines=4)

    btn.click(fn, inputs=[inp], outputs=[ans, src])
    inp.submit(fn, inputs=[inp], outputs=[ans, src])

demo.launch()