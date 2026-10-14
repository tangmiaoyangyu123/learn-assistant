# ① 基础镜像：官方精简版 Python 3.11（约 50 MB）
#    为什么用 slim？完整版 python 镜像有好几百 MB，我们不需要
FROM python:3.11-slim

# ② 工作目录：容器里的 /app，后面所有路径都相对它
WORKDIR /app

# ③ 先【只】复制 requirements.txt
#    ★ 这是 Docker 最重要的性能优化：利用"层缓存"
#    只要 requirements.txt 没变，下面 pip install 那层就直接用缓存，不用重装
COPY requirements.txt .

# ④ 装依赖
#    -i 阿里云 PyPI 源（本机实测：清华源对 Python 客户端返回 403，阿里源正常）
#    --no-cache-dir 不保留 pip 缓存，镜像更小
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

# ⑤ 复制应用代码（.dockerignore 里排除的不会进来，models/ 会进来）
COPY . .

# ⑥ ★ 让 Gradio 监听 0.0.0.0 —— 否则宿主机访问不到
#    实测：gradio 6.29.1 的 launch() 会读这两个环境变量
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"

# ⑦ 声明端口（只是给人和工具看的说明，真正的映射靠 docker run -p）
ENV PYTHONUNBUFFERED=1
EXPOSE 7860

# ⑧ 启动命令
CMD ["python", "pdf_qa_app.py"]