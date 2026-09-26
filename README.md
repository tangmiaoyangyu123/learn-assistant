# learn-assistant —— 命令行 AI 学习助手

一个基于 DeepSeek API 的命令行 AI 对话助手，支持多角色切换、带记忆、能抗网络错误。
大二自学 AI 应用开发两周的迭代作品。

## 功能

- 4 种角色随时切换：Python老师 / 英语外教 / 职业规划师 / Debug专家
- 流式输出（打字机效果）
- 多轮对话记忆：退出自动保存，重启自动恢复
- 三层异常保护：网络错误兜底、Ctrl+C 优雅退出、历史文件损坏自动备份
- 角色模板化：公共约束一处管理，改一处全局生效（prompts.py）

## 工作原理

【在这里用你自己的话写 5-8 句，回答三个问题：
  1. 启动时： load_history 检查 chat_history.json 是否存在。存在就用 json.load 解析成列表；如果文件内容损坏，json.load 会抛出 JSONDecodeError 被 except 接住——坏文件改名 .bak 留证，返回只含 system 的新列表。文件不存在则直接返回新列表（此时还没有文件，等第一轮对话后才创建）。
  2. 每层对话：用户输入追加进 messages → 把整个 messages 列表发给模型（API 无状态，模型不记得任何东西，“记忆”靠每轮重发完整历史）→ stream=True 流式接收回复 → 完整回复追加进 messages → save_history 写盘。输入 new 则重置 messages 并删除历史文件。
  3. 记忆的两层：运行中记得上文，靠每轮重发完整 messages；跨重启的记忆，靠 chat_history.json 每轮写盘、启动时读回。

## 快速开始

git clone https://github.com/tangmiaoyangyu123/learn-assistant.git
cd learn-assistant
pip install openai python-dotenv

在项目目录新建 `.env` 文件，写入一行（不要提交到 git）：

DEEPSEEK_API_KEY=你的key

python assistant_v3.py

## 命令

| 输入 | 作用 |
|---|---|
| python / english / career / debug | 切换角色（开启新对话） |
| new | 当前角色重新开始 |
| quit | 退出 |

## 文件说明

| 文件 | 说明 |
|---|---|
| assistant_v3.py | 最终版主程序：多角色 + 流式 + 记忆 + 异常保护 |
| prompts.py | 角色模板库：build_system 拼接公共约束 |
| chat.py / chat_stream.py / chat_memory.py / assistant_v1.py~v2.py | 学习过程的迭代版本，保留作记录 |

## 迭代记录

- 第 1 周：环境搭建，从一问一答到流式输出、多轮记忆、历史存档（V1）
- 第 2 周：角色切换 + 三层异常保护 + Prompt 模板化（V2）
