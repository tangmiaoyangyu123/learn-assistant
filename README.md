# AI 学习助手 · 本地知识库问答服务

大二自学 AI 应用开发的练习仓库（12 周计划，进行到第 7 周）。
主线：**对话 → Prompt → 检索（RAG）→ Web 界面 → 服务化部署**，每两周产出一个能跑起来的东西。

当前主项目：上传自己的 PDF，切分入库，提问时**只依据文档作答并标注来源**。
对外提供 FastAPI 服务，支持流式输出、多轮对话、知识库管理，可用 Docker 一键部署。

---

## 项目一览

| # | 项目 | 周次 | 关键技术 | 状态 |
|---|---|---|---|---|
| 1 | 命令行 AI 学习助手 | 1-2 | openai SDK / 流式输出 / 多轮记忆 / 角色模板化 | ✅ |
| 2 | 本地文档搜索 Demo | 3 | chromadb / 中文 embedding / 文档切分 | ✅ |
| 3 | PDF 问答助手 V1 | 4 | RAG 全链路 + Gradio 界面 | ✅ 归档 |
| 4 | **本地知识库问答服务** | 5-7 | FastAPI / SSE 流式 / 原生前端 / Docker | ✅ 当前 |

---

## 项目 4：本地知识库问答服务（第 5-7 周）

把第 4 周那个 Gradio 单文件应用拆成模块，套上真正的 HTTP 服务层和前端，
做成一个有明确接口、能部署、能被别人调用的东西。

### 它解决了什么

第 4 周的 Gradio 版本能在浏览器里用，但它是个**单体脚本**：

- 界面和业务逻辑长在一个文件里，换界面就得动业务
- 只能用 Gradio 自己的组件，想调样式得和框架打架
- 没有对外接口，别人没法把检索能力接到自己的程序里
- 换台机器跑不起来，模型路径写死了

这一版把它拆成 **服务层（FastAPI）+ 业务模块 + 独立前端**，三块各自可替换。

### 架构

```
① 建库
   PDF ──pypdf 逐页提取──▶ 切分(300 字 / 重叠 60) ──▶ bge-small-zh 向量化 ──▶ chromadb
                              build_knowledge_base.py        chinese_embedding.py    kb_manager.py

② 问答
   问题 ──▶ Top-3 向量检索 ──▶ 拼 Prompt ──▶ DeepSeek ──▶ 带引用的回答
                 │                              │
                 └─ 距离 > 1.1 → 直接拒答        └─ SSE 流式逐字返回
                              rag_qa.py

③ 服务
   FastAPI ──▶ 9 个业务接口 ──▶ static/ 托管前端 ──▶ Docker + 四个 bind mount
                                    api_rag.py
```

### 接口

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/ask` | 单轮问答，一次性返回 |
| POST | `/ask/stream` | 流式问答（SSE），可选带 `session_id` 走多轮 |
| POST | `/chat` | 多轮问答，写入历史 |
| GET | `/documents` | 列出知识库文件与块数 |
| POST | `/documents` | 上传 PDF，解析切分入库 |
| DELETE | `/documents/{name}` | 删除文件及其全部块 |
| GET | `/history/{session_id}` | 读某会话历史 |
| DELETE | `/history/{session_id}` | 清某会话历史 |
| GET | `/` | 前端页面 |

接口文档：启动后访问 `http://127.0.0.1:8000/docs`。

### 快速开始

**① 准备中文向量模型**（约 24MB，不进 git）

放到 `models/bge-small-zh-onnx/`，需要三个文件：

```
models/bge-small-zh-onnx/
├── model_quantized.onnx
├── tokenizer.json
└── config.json
```

来源：HuggingFace `Xenova/bge-small-zh-v1.5` 的 ONNX 量化版。
也可用环境变量 `BGE_MODEL_DIR` 指向别处的模型目录。

**② 配置 API Key**

项目根目录新建 `.env`（已在 `.gitignore` 里，不会上传）：

```
DEEPSEEK_API_KEY=sk-你的key
```

**③ 启动 · 方式 A（本地）**

```bash
pip install -r requirements.txt
python -m uvicorn api_rag:app --reload
```

**③ 启动 · 方式 B（Docker）**

```bash
docker compose up -d --build
```

两种方式都访问 **`http://127.0.0.1:8000`**。

> 注意是 `127.0.0.1`，不是 `0.0.0.0`。`0.0.0.0` 是服务端的**监听地址**（表示所有网卡），
> 不是浏览器能打开的地址。

Docker 方式的数据持久化靠三个 bind mount，删容器不丢数据：

| 宿主机 | 容器内 | 存什么 |
|---|---|---|
| `./chroma_db` | `/app/chroma_db` | 向量库 |
| `./uploads` | `/app/uploads` | 原始 PDF |
| `./chat.db` | `/app/chat.db` | 对话历史 |
| `./static` | `/app/static` | 前端页面（改完刷新即可，不用 rebuild） |

### 关键设计（都是踩过坑定下来的）

| 设计 | 为什么 |
|---|---|
| 向量模型必须用**中文**的 | chromadb 内置 `all-MiniLM-L6-v2` 是纯英文模型，中文逐字被打成 `[UNK]`，**不报错但完全失效**，检索结果退化成按字数排序 |
| 每次打开 collection 都显式传 `embedding_function=` | 不传会静默回落到英文模型；维度相同时连报错都没有 |
| 知识库**只加载一次**（模块级单例） | 放进请求处理里，每点一次按钮就要重载模型，实测慢约 9 倍 |
| 检索负责"召回"，模型负责"判断" | 真问题的向量距离与"沾边但没答案"的距离**区间重叠**，单靠距离分不开，所以设阈值 1.1 拒答 |
| 重传同名文件先删旧块 | 否则块数翻倍，且 id 重复会直接报错 |
| 扫描件防御 | 每页字符数低于 50 就报警，**不把空内容塞进知识库** |
| 上传区用独立 collection | 一个 collection 只能装同一模型产生的向量，混用会互相污染 |
| 流式用 SSE，不用 WebSocket | 单向推送，SSE 走普通 HTTP，不需要协议升级和心跳 |
| `session_id` 做成可选，而不是单开一个接口 | 传了就带历史、不传当单轮，一个接口覆盖两种用法 |
| 前端中断用 `AbortController` | 客户端断开 → 生成器收到 `CancelledError` → 自动停，**天然省 token** |
| `static/` 也做 bind mount | 否则改前端要重新构建镜像，而镜像里的 `static` 与宿主机是两份副本 |

### 测试

边界测试的过程与结果见 [TESTING.md](TESTING.md)：路径穿越、假 PDF、空文件、
字段约束（超长 / 空 / `top_k` 越界）、删除不存在的文件、两路流式并发。

### 已知边界

诚实写，不是待办清单：

- **上传无大小限制**：`await file.read()` 把整个文件读进内存，传大文件会吃满内存
- **容器时区是 UTC**：`python:3.11-slim` 没装 `tzdata`，历史时间比北京时间晚 8 小时
- **并发只验证到 2 路**：SQLite 写锁在 10 路以上未测，可能出现 `database is locked`
- **只支持文字版 PDF**：扫描件提不出文字，需要 OCR
- **单机单进程**：没有队列、没有多副本，重启即短暂不可用
- **前端与后端同源**：服务整体挂掉时页面本身也打不开，前端无法显示"后端已离线"

### 文件说明

| 文件 | 说明 |
|---|---|
| `api_rag.py` | **主服务**：路由、SSE、静态托管 |
| `rag_qa.py` | 检索 + 生成 + 拒答，含 `MAX_TURNS` |
| `kb_manager.py` | 知识库管理：上传入库 / 列清单 / 删除 |
| `chinese_embedding.py` | 中文 embedding（ONNX，不依赖 torch） |
| `build_knowledge_base.py` | 文档切分流水线，含按页提取与质量自检 |
| `db.py` | SQLite 对话历史 |
| `docs_helper.py` | 接口文档挂载 |
| `static/index.html` | 前端（原生 HTML/CSS/JS，单文件） |
| `Dockerfile` / `docker-compose.yml` | 容器化与编排 |
| `TESTING.md` | 边界测试记录 |

---

## 项目 3：PDF 问答助手 V1（第 4 周，历史版本）

> ⚠️ **已归档，不再维护。** 下面这套 Gradio 版本的启动方式仅作为迭代记录保留，
> 当前版本请用上面的项目 4。

上传 PDF → 切分入库 → 提问 → 只依据文档作答并标注引用来源。

```bash
python pdf_qa_app.py
```

浏览器打开 `http://127.0.0.1:7860` → 上传 PDF → 点「加入知识库」→ 在「② 提问」标签页提问。

架构与项目 4 的建库 / 问答两段相同，区别在于它用 Gradio 组件搭界面、没有独立的服务层和前端。

---

## 项目 2：本地文档搜索 Demo（第 3 周）

输入问题，返回最相关的 3 段原文（带来源和页码），**不接大模型**。
用来验证"语义检索"到底有没有效——这就是发现"英文模型处理中文会静默失效"的地方。

```bash
python build_knowledge_base.py    # 建库
python search_docs.py "综合测评怎么加分"   # 检索
```

---

## 项目 1：命令行 AI 学习助手（第 1-2 周）

- 4 种角色随时切换：Python 老师 / 英语外教 / 职业规划师 / Debug 专家
- 流式输出（打字机效果）
- 多轮对话记忆：退出自动保存，重启自动恢复
- 三层异常保护：网络错误兜底、Ctrl+C 优雅退出、历史文件损坏自动备份
- 角色模板化：公共约束一处管理（`prompts.py`）

```bash
python assistant_v3.py
```

| 输入 | 作用 |
|---|---|
| python / english / career / debug | 切换角色（开启新对话） |
| new | 当前角色重新开始 |
| quit | 退出 |

---

## 迭代记录

- **第 1 周**：环境搭建，从一问一答到流式输出、多轮记忆、历史存档
- **第 2 周**：角色切换 + 三层异常保护 + Prompt 模板化
- **第 3 周**：文档加载 / 切分 / 中文向量化 / 入库，做出本地文档搜索 Demo
- **第 4 周**：打通检索 + 生成全链路，套上 Gradio 界面，做出 PDF 问答助手 V1
- **第 5 周**：对话历史独立成模块，Docker 入门，把应用容器化
- **第 6 周**：用 FastAPI 重写服务层，异步 + SSE 流式，SQLite 存对话历史
- **第 7 周**：原生前端、流式多轮与中断、Docker Compose 部署、边界测试
