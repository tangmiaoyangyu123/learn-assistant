# AI 学习助手 · PDF 问答助手

大二自学 AI 应用开发的练习仓库（12 周计划，已完成第 1-4 周）。
主线：**对话 → Prompt → 检索（RAG）→ Web 界面**，每两周产出一个能跑起来的东西。

## 项目一览

| # | 项目 | 周次 | 关键技术 | 状态 |
|---|---|---|---|---|
| 1 | 命令行 AI 学习助手 | 1-2 | openai SDK / 流式输出 / 多轮记忆 / 角色模板化 | ✅ |
| 2 | 本地文档搜索 Demo | 3 | chromadb / 中文 embedding / 文档切分 | ✅ |
| 3 | **PDF 问答助手 V1** | 4 | RAG 全链路 + Gradio Web 界面 | ✅ |

---

## 项目 3：PDF 问答助手 V1（当前主项目）

上传自己的 PDF → 自动切分入库 → 提问 → **只依据文档作答，并标注引用来源**。

### 它解决了什么

普通聊天机器人回答问题时靠的是"训练时记住的东西"，对你不公开的资料一无所知，而且**会一本正经地编**。
这个助手把回答限制在你给的文档里：资料里没有的，它会直接说"资料里没有相关内容"，而不是猜。

### 架构

```
① 上传（建库）
   PDF ──pypdf逐页提取──▶ 切分(300字/重叠60) ──▶ 中文向量化 ──▶ chromadb
        kb_manager.py                          bge-small-zh     upload_kb

② 提问（问答）
   问题 ──▶ 向量检索 Top-3 ──▶ 拼 Prompt ──▶ DeepSeek ──▶ 带引用的回答
                                    ↑                      + 来源清单
                          资料不足 → 直接拒答
```

### 关键设计（都是踩过坑定下来的）

| 设计 | 为什么 |
|---|---|
| 向量模型必须用**中文**的 | chromadb 内置 `all-MiniLM-L6-v2` 是纯英文模型，中文逐字被打成 `[UNK]`，**不报错但完全失效** |
| 知识库**只加载一次**（模块级单例） | 放进请求处理里，每点一次按钮就要重载模型，实测慢约 9 倍 |
| 检索负责"召回"，模型负责"判断" | 真问题的向量距离（0.441-1.050）与"沾边但没答案"的距离（0.838-0.913）**区间重叠**，单靠距离分不开 |
| 重传同名文件先删旧块 | 否则块数翻倍，且 id 重复会直接报错 |
| 扫描件防御 | 每页字符数低于阈值就报警，**不把空内容塞进知识库** |
| 上传区独立 collection | 一个 collection 只能装同一模型产生的向量，混用会互相污染 |

### 快速开始

```bash
git clone https://github.com/tangmiaoyangyu123/learn-assistant.git
cd learn-assistant
pip install -r requirements.txt
```

**① 准备中文向量模型**（约 24MB，不进 git）

放到项目的 `models/bge-small-zh-onnx/` 目录下，需要这三个文件：

```
models/bge-small-zh-onnx/
├── model_quantized.onnx
├── tokenizer.json
└── config.json
```

来源：HuggingFace `Xenova/bge-small-zh-v1.5` 的 ONNX 量化版。
（也可以用环境变量 `BGE_MODEL_DIR` 指向别处的模型目录。）

**② 配置 API Key**：在项目根目录新建 `.env`（已在 `.gitignore` 里，不会上传）：

```
DEEPSEEK_API_KEY=sk-你的key
```

**③ 启动**

```bash
python pdf_qa_app.py
```

浏览器打开 `http://127.0.0.1:7860` → 上传 PDF → 点「加入知识库」→ 在「② 提问」标签页提问。

### 文件说明（项目 3）

| 文件 | 说明 |
|---|---|
| `pdf_qa_app.py` | **主程序**：Gradio 界面 + 把各模块串起来 |
| `kb_manager.py` | 知识库管理：上传入库 / 列清单 / 删除 / 清空 |
| `rag_qa.py` | 检索 + 生成 + 拒答（第 4 周 Day1-3） |
| `search_docs.py` | 纯向量检索（第 3 周周末） |
| `build_knowledge_base.py` | 文档切分流水线，含按页提取 + 提取质量自检 |
| `chinese_embedding.py` | 中文 embedding（ONNX，不依赖 torch） |
| `chunk_lab.py` / `doc_loader.py` | 切分实验台 / 文档加载 |

### 已知边界（V2 要解决的）

- **模型路径写死**：`chinese_embedding.py` 里的 `MODEL_DIR` 是绝对路径，换台机器要改
- 没有对话历史：问"那体育课呢"它接不上上文
- 没有流式输出：要等模型全部生成完才显示
- 只支持文字版 PDF：扫描件（图片型）提不出文字，需要 OCR
- 本地服务：`127.0.0.1:7860` 只有自己能访问

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

- 4 种角色随时切换：Python老师 / 英语外教 / 职业规划师 / Debug专家
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

- 第 1 周：环境搭建，从一问一答到流式输出、多轮记忆、历史存档
- 第 2 周：角色切换 + 三层异常保护 + Prompt 模板化
- 第 3 周：文档加载 / 切分 / 中文向量化 / 入库，做出本地文档搜索 Demo
- 第 4 周：打通检索 + 生成全链路，套上 Gradio Web 界面，做出 PDF 问答助手 V1
