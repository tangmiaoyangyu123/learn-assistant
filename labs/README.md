# labs · 各周练习与实验台

**这个目录不是项目的一部分**，是 12 周学习过程中每一天的练习脚本，留作记录。
项目本体见仓库根目录和 [README](../README.md)。

## 怎么运行

从**仓库根目录**：

```bash
python -m labs.chroma_demo
```

不要用 `python labs/chroma_demo.py`。原因：这些脚本会 `import` 根目录的模块（`chinese_embedding`、`kb_manager` 等），
直接按路径运行时 Python 只把 `labs/` 放进搜索路径，找不到根目录的模块。

`python -m` 会把**当前目录**（仓库根）放进搜索路径，所以能正常工作。

---

## 第 1-2 周 · 命令行 AI 学习助手

| 文件 | 说明 |
|---|---|
| `chat.py` | 第一版：一问一答，最朴素的 `while` 循环 |
| `chat_stream.py` | 加上流式输出（打字机效果） |
| `chat_memory.py` | 加上多轮记忆，把历史存进文件 |
| `assistant.py` | 整合版：流式 + 记忆 |
| `assistant_v2.py` | 跨程序记忆：退出保存、重启恢复 |
| `assistant_v3.py` | 最终版：4 角色切换 + 历史存档 + 三层异常保护 |
| `prompts.py` | 4 个角色的 system 模板，集中管理（被 v2/v3 引用） |
| `prompt_lab.py` | Prompt 四大技巧的对照实验台 |
| `role_compare.py` | 同一个问题、四个角色，输出差异对比 |

## 第 3 周 · 检索

| 文件 | 说明 |
|---|---|
| `embedding_lab.py` | Embedding 与余弦相似度，纯 Python 零依赖 |
| `chroma_demo.py` | chromadb 向量库入门：增删查改 |

## 第 4 周 · Gradio 与 RAG 界面

| 文件 | 说明 |
|---|---|
| `gradio_hello.py` | Gradio 最小 Demo：理解"界面只是函数的壳" |
| `quiz_tab.py` | Gradio 多标签页练习 |
| `comp_lab.py` | Gradio 组件实验台 |
| `rag_web.py` | 第 4 周 Day5：RAG + Gradio 整合，第一次把检索接到网页上 |

## 第 5 周 · 对话历史与容器化

| 文件 | 说明 |
|---|---|
| `chat_demo.py` | 多轮对话最小 Demo，验证 SQLite 存历史的完整链路 |
| `pdf_qa_app.py` | **项目 3 的主程序**：上传 PDF → 多轮提问 → 带引用回答（Gradio 版，已归档） |

## 第 6 周 · FastAPI 与流式

| 文件 | 说明 |
|---|---|
| `main.py` | 第 6 周第一个 FastAPI 应用，只有 hello world |
| `api_ask.py` | 加 POST 与 Pydantic 字段校验 |
| `api_lab.py` | 把 RAG 接进 API，返回答案 + 来源 |
| `stream_lab.py` | SSE 流式实验台，验证分块与 `[DONE]` |
| `upload_lab.py` | 文件上传实验台，`UploadFile` 与 `FormData` |

---

## 为什么 `chunk_lab.py` 和 `doc_loader.py` 不在这个目录

它们名字看着像实验台，但**主链路依赖它们**：

```python
# build_knowledge_base.py
from chunk_lab import split_overlap     # 切分算法
from doc_loader import load_md          # 文档加载
```

`kb_manager.py` → `build_knowledge_base.py` → `chunk_lab.py`，这条链是上传 PDF 入库时的必经路径。
挪进 `labs/` 会让 `POST /documents` 直接挂掉。

**教训：判断一个文件该不该清理，看依赖关系，不看文件名。**
