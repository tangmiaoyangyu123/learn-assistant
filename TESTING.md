# 边界测试记录

**日期**：2026-11-07
**环境**：Windows 11 · Docker 29.8.2 · 镜像 `rag-app:v1`（`python:3.11-slim`，Python 3.11.18）· 容器 `rag-app`，端口 `8000:8000`
**方式**：所有请求打在容器内的 uvicorn 上（`http://127.0.0.1:8000`），不是在宿主机直接跑 Python。

## 通过

| # | 测试项 | 输入 | 期望 | 实际结果 |
|---|---|---|---|---|
| T1 | 文件名路径穿越 | `filename=../../evil.pdf` | 只保留 `evil.pdf`，项目外无文件 | `name` 返回 `evil.pdf`；`uploads/` 内落地；`..\evil.pdf` 与 `D:\evil.pdf` 都不存在 |
| T2 | 假 PDF（文本改名） | 一行文本存为 `fake.pdf` | 400 + 文件不残留 | 400，`detail` 为解析失败；`uploads/fake.pdf` 不存在 |
| T3 | 空文件 | 0 字节 `empty.pdf` | 400，不是 500 | 400，`detail` 说明无法解析 |
| T4a | 超长问题 | `question` 600 字 | 422 `string_too_long` | 422，`ctx.max_length = 500` |
| T4b | 空问题 | `question` 为空串 | 422 `string_too_short` | 422，`min_length = 1` |
| T4c | `top_k` 超范围 | `top_k=100` | 422 `less_than_equal` | 422，`ctx.le = 10` |
| T5 | 删除不存在的文件 | `DELETE /documents/nothing.pdf` | 404 + 明确说明 | 404，`detail` 为「知识库里没有 nothing.pdf」 |
| T6 | 两路流式并发 | 同时两个 `/ask/stream` | 两路都完整，不串行 | A 1.68s / 111 块、B 1.59s / 122 块，均收到 `event: done`；总耗时 1.68s，串行之和 3.27s |

前 7 项由代码里已有的三层防护提供，本轮验证全部生效：

| 层 | 位置 | 防的是 |
|---|---|---|
| 路径截断 | `api_rag.py` `name = Path(file.filename).name` | 目录穿越 |
| 字段约束 | `AskRequest` 的 `Field(min_length=1, max_length=500)`、`top_k` 的 `ge=1, le=10` | 空输入、超长输入、过量检索 |
| 异常与清理 | 上传端点 `try/except` + `target.unlink(missing_ok=True)` | 解析失败后残留垃圾文件 |

## 未通过 / 已知缺口

### 1. 上传大小无限制（未修）

`api_rag.py`：

```python
target.write_bytes(await file.read())
```

`await file.read()` 把整个文件读进内存，再一次性写盘。传一个 2 GB 的 PDF，进程内存就涨 2 GB。

- **影响**：单个大文件即可拖慢甚至拖垮服务；也给了别人把服务当网盘用的空间。
- **为什么暂不修**：修法是分块读写（`while chunk := await file.read(1 << 20)`），属于新 API，需要单独讲；当前服务只在本机，风险为零。
- **什么时候必须修**：第 10 周部署到公网之前。

### 2. 容器时区是 UTC（未修）

`db.py` 用 `datetime('now','localtime')` 记时间，但容器内 `localtime` 就是 UTC，所以 `GET /history` 返回的时间比北京时间晚 8 小时。

- **影响**：只影响显示，不影响问答与检索。
- **为什么暂不修**：`python:3.11-slim` 没有 `tzdata`，只设 `TZ=Asia/Shanghai` 环境变量无效，需要在镜像里装时区数据，会让镜像变大。

### 3. 并发只测了两路（未覆盖）

T6 验证了两路并发可用，但没有验证 10 路以上时 SQLite 写锁的表现。`db.save_message` 是同步写，理论上高并发下会出现 `database is locked`。

- **影响**：个人使用无影响；多人同时用会暴露。
- **什么时候必须处理**：如果第 10 周做的是公开访问的服务。

## 复现方式（PowerShell）

```powershell
cd D:\PythonProject

# T1 路径穿越
curl.exe --noproxy "*" -s -m 120 -F "file=@test.pdf;filename=../../evil.pdf" http://127.0.0.1:8000/documents
Test-Path ..\evil.pdf; Test-Path D:\evil.pdf          # 都应为 False
curl.exe --noproxy "*" -X DELETE http://127.0.0.1:8000/documents/evil.pdf

# T2 假 PDF
Set-Content -Path fake.pdf -Value "not a pdf" -Encoding ascii
curl.exe --noproxy "*" -s -m 30 -w "`n[HTTP %{http_code}]`n" -F "file=@fake.pdf" http://127.0.0.1:8000/documents
Test-Path uploads\fake.pdf                             # False

# T3 空文件
New-Item -Path empty.pdf -ItemType File -Force | Out-Null
curl.exe --noproxy "*" -s -m 30 -w "`n[HTTP %{http_code}]`n" -F "file=@empty.pdf" http://127.0.0.1:8000/documents

# T4 字段约束（三条都应 422）
& "D:\python_download\python.exe" -c "import httpx; q=chr(21834)*600; r=httpx.post('http://127.0.0.1:8000/ask', json={'question':q}, timeout=30); print(r.status_code)"
& "D:\python_download\python.exe" -c "import httpx; r=httpx.post('http://127.0.0.1:8000/ask', json={'question':''}, timeout=30); print(r.status_code)"
& "D:\python_download\python.exe" -c "import httpx; r=httpx.post('http://127.0.0.1:8000/ask', json={'question':'test','top_k':100}, timeout=30); print(r.status_code)"

# T5 删除不存在的文件
curl.exe --noproxy "*" -s -m 10 -w "`n[HTTP %{http_code}]`n" -X DELETE http://127.0.0.1:8000/documents/nothing.pdf

# T6 两路流式并发
& "D:\python_download\python.exe" "D:\workbuddy_data\tools\test_concurrent.py"
```

测试结束后清理临时文件：

```powershell
Remove-Item fake.pdf, empty.pdf -ErrorAction SilentlyContinue
```
