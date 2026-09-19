# 学习助手 Learning Assistant

一个基于 DeepSeek API 的命令行 AI 助手，大二自学 AI 应用开发的第一周作品。

## 功能

- 多角色切换（Python老师 / 英语外教 / 职业规划师 / Debug专家）
- 流式输出（打字机效果）
- 多轮对话记忆
- 对话历史存档（关掉程序不失忆）

## 工作原理

【用自己的话写 5-8 句：程序启动时做什么 → 每轮对话发生什么 → "记忆"是怎么实现的】
【写不下去的地方，就是你还没真懂的地方，标记出来问我】

## 运行方法

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，写入：`DEEPSEEK_API_KEY=你的key`
3. 运行：`python assistant_v3.py`

## 文件说明

| 文件 | 说明 |
|---|---|
| chat.py | 基础版：一问一答 |
| chat_stream.py | 流式版：打字机效果 |
| chat_memory.py | 记忆版：多轮对话 |
| assistant.py | V1：流式+记忆合体 |
| assistant_v2.py | V2：对话历史存档 |
| assistant_v3.py | V3：多角色切换（最终版） |
| prompts.py | 角色提示词库 |

## 学习轨迹

从零开始逐步迭代，每个版本只增加一个知识点。