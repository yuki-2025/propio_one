# LangChain Agent Backend Service

一个基于 FastAPI 的 LangChain Agent 后端服务，使用现代 Lifespan 模式管理资源，集成 MLflow 进行监控。

## 🎯 功能特性

- ✅ **FastAPI 后端**: 使用最新的 Lifespan 模式管理应用生命周期
- ✅ **LangChain Agent**: 集成 LangGraph 和结构化输出
- ✅ **对话持久化**: 使用 InMemorySaver 支持多轮对话
- ✅ **流式响应**: 支持 SSE (Server-Sent Events) 流式输出
- ✅ **MLflow 监控**: 自动追踪 OpenAI API 调用和性能指标
- ✅ **CORS 支持**: 允许跨域请求
- ✅ **现代前端**: 响应式聊天界面

## 📁 项目结构

```
monitoring/
├── backend/                    # 后端代码
│   ├── app/                   # FastAPI 应用
│   │   ├── __init__.py
│   │   ├── main.py           # 主入口 (Lifespan)
│   │   ├── config.py         # 配置管理
│   │   ├── models/           # 数据模型
│   │   │   ├── __init__.py
│   │   │   └── schemas.py    # Pydantic 模型
│   │   ├── routers/          # API 路由
│   │   │   ├── __init__.py
│   │   │   └── chat.py       # 聊天端点
│   │   ├── services/         # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   └── agent.py      # LangChain Agent
│   │   └── utils/            # 工具函数
│   │       └── __init__.py
│   ├── tests/                # 后端测试
│   │   ├── __init__.py
│   │   └── test_api.py
│   └── examples/             # 示例代码
│       ├── langchain_app.py
│       └── mlflow_test.py
├── frontend/                  # 前端代码
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── styles/
│   │   │   └── main.css
│   │   └── App.js
│   └── index.html
├── scripts/                   # 启动脚本
│   └── start.ps1
├── .env                       # 环境变量
├── .gitignore
├── .vscode/                   # VS Code 设置
├── pyproject.toml            # Python 依赖配置
├── requirements.txt
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 UV (推荐)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中配置:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### 3. 启动后端服务

```bash
# 使用启动脚本
.\scripts\start.ps1

# 或直接运行
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 启动前端 (可选)

```bash
# 使用 Python HTTP 服务器
cd frontend
python -m http.server 3000

npm run dev

# 访问 http://localhost:3000
```

### 5. 启动 MLflow 服务器 (可选)

```bash
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000

# 访问 http://localhost:5000
```

## 📡 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 状态 |
| `/health` | GET | 健康检查 |
| `/chat` | POST | 发送消息 (同步) |
| `/chat/stream` | POST | 发送消息 (流式) |

### 示例请求

```bash
# 健康检查
curl http://localhost:8000/health

# 发送消息
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather outside?", "user_id": "1"}'

# 流式响应
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about the weather"}'
```

## 🧪 运行测试

```bash
uv run python backend/tests/test_api.py
```

## 📦 依赖库

| 类别 | 库 | 用途 |
|------|-----|------|
| **Web 框架** | `fastapi`, `uvicorn` | 后端 API 服务 |
| **AI 框架** | `langchain`, `langgraph` | Agent 和工作流 |
| **LLM** | `openai`, `tiktoken` | OpenAI API 调用 |
| **监控** | `mlflow` | 实验追踪和监控 |
| **数据验证** | `pydantic` | 请求/响应验证 |

## 🔧 开发命令

```bash
# 添加新依赖
uv add package-name

# 运行后端
uv run uvicorn backend.app.main:app --reload

# 运行测试
uv run pytest

# 代码格式化
uv run black backend/

# 代码检查
uv run ruff check backend/
```

## 📝 License

MIT
