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

# ⑥ 让 Python 的输出不缓冲，日志能实时打出来
ENV PYTHONUNBUFFERED=1

# ⑦ 声明端口（给人看，真正映射靠 compose 的 ports）
EXPOSE 8000

# ⑧ 启动命令：uvicorn 跑 api_rag 里的 app
CMD ["python", "-m", "uvicorn", "api_rag:app", "--host", "0.0.0.0", "--port", "8000"]