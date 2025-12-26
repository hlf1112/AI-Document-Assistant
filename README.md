# 🚀 AI 智能文档分析助手 (AI Document Assistant)

> 基于 **Spring Boot + FastAPI + Google Gemini** 的全栈 RAG（检索增强生成）应用。
> 支持文档上传学习、多轮对话记忆、流式打字机效果及 Markdown 渲染。

## ✨ 项目亮点

* **双后端架构**：采用 **Java (Spring Boot)** 处理业务逻辑与网关转发，**Python (FastAPI)** 负责向量计算与 LLM 交互。
* **RAG 检索增强**：集成 **LangChain + ChromaDB**，实现本地文档知识库的构建与检索，有效解决大模型幻觉问题。
* **极致交互体验**：
    * 实现 **SSE (Server-Sent Events)** 流式响应，提供 ChatGPT 般的打字机体验。
    * 支持 **Markdown 实时渲染**（代码高亮、公式解析）。
    * 具备 **多轮对话记忆** 能力，支持上下文连续追问。
* **状态管理**：前端实现滑动窗口记忆机制，后端提供知识库热重置功能。

## 🛠️ 技术栈

* **前端**：HTML5, CSS3, Vanilla JS, Marked.js (Markdown渲染)
* **Java 后端**：Spring Boot 3, Spring WebFlux (WebClient)
* **Python 后端**：FastAPI, Uvicorn, LangChain, Google Gemini API
* **向量库**：ChromaDB (本地轻量级向量数据库)

## 🚀 快速开始

### 1. 启动 Python 服务
确保配置了 `GOOGLE_API_KEY` 环境变量。
```bash
pip install -r requirements.txt
python ai_engine.py
# 服务将运行在 [http://127.0.0.1:8000](http://127.0.0.1:8000)

2. 启动 Java 服务
运行 Spring Boot 主程序。
# 服务将运行在 [http://127.0.0.1:8080](http://127.0.0.1:8080)

3. 访问应用
打开浏览器访问：http://127.0.0.1:8080/AI_Test.html
