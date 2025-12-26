import uvicorn
import os
import json
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 导入 Google Gemini 相关组件
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

app = FastAPI()

# --- 配置区 ---
# 1. 你的 API Key
GOOGLE_API_KEY = "你的API"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# 2. 代理配置 (确保端口与你的软件一致)
os.environ["http_proxy"] = "http://127.0.0.1:7897"
os.environ["https_proxy"] = "http://127.0.0.1:7897"

# 全局变量：存储当前文档的向量索引
vector_store = None


# 【修改点 1】：更新请求模型，增加 history 字段
class ChatRequest(BaseModel):
    question: str
    enable_rag: bool = True
    # 新增：接收前端传来的历史记录，默认为空列表
    # 格式示例：[{"role": "user", "content": "你好"}, {"role": "model", "content": "你好！"}]
    history: list = []


@app.get("/")
async def health_check():
    return {"message": "Gemini 2.5 Engine is running", "vector_store_active": vector_store is not None}


# 1. 文档学习接口 (追加模式)
@app.post("/ai/upload")
async def upload_file(file_path: str = Form(...)):
    global vector_store
    try:
        if not os.path.exists(file_path):
            return {"error": f"路径不存在: {file_path}"}

        # 文档解析逻辑
        if file_path.lower().endswith(".pdf"):
            loader = PyMuPDFLoader(file_path)
        elif file_path.lower().endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        else:
            return {"error": "仅支持 PDF 和 DOCX"}

        data = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(data)

        # 使用最新的 Embedding 模型 (text-embedding-004)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="text-embedding-004",
            google_api_key=GOOGLE_API_KEY
        )

        # 如果 vector_store 已经存在，就往里面加数据 (append)
        if vector_store:
            vector_store.add_documents(documents=docs)
            return {"message": f"Gemini 已追加学习新文档！当前知识库已包含: {os.path.basename(file_path)}"}
        else:
            # 如果是第一次上传，就新建一个
            vector_store = Chroma.from_documents(documents=docs, embedding=embeddings)
            return {"message": f"Gemini 知识库初始化完成！文件: {os.path.basename(file_path)}"}
    except Exception as e:
        print(f"上传失败: {e}")
        return {"error": str(e)}


@app.post("/ai/reset")
async def reset_knowledge():
    global vector_store
    vector_store = None
    return {"message": "知识库已清空，AI 大脑已重置。"}


# 2. 智能问答接口 (支持 历史记忆 + RAG 开关)
@app.post("/ai/chat")
async def chat_endpoint(request: ChatRequest):
    global vector_store

    # 1. 获取参数
    query = request.question
    use_rag = request.enable_rag
    history = request.history  # 获取前端传来的历史记录列表

    # --- 构建上下文 (RAG Context) ---
    context = ""
    # 只有当 (向量库存在) 且 (开关开启) 时，才去检索
    if vector_store and use_rag:
        try:
            # 检索最相关的 5 段内容
            related_docs = vector_store.similarity_search(query, k=5)
            context = "\n".join([doc.page_content for doc in related_docs])
        except Exception as e:
            print(f"检索失败: {e}")

    # --- 构建历史记录字符串 (History Context) ---
    history_text = ""
    if history:
        for msg in history:
            role = "用户" if msg.get('role') == 'user' else "AI助手"
            content = str(msg.get('content', '')).replace('\n', ' ')  # 去掉换行防止格式混乱
            history_text += f"{role}: {content}\n"

    # 初始化最新的 Gemini 2.5 模型
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        streaming=True,
        google_api_key=GOOGLE_API_KEY
    )

    async def generate_stream():
        # --- Prompt 组装策略 ---
        # 基础设定
        base_prompt = "你是一个专业的 AI 助手。"

        # 1. 注入历史记录 (如果有)
        if history_text:
            base_prompt += f"\n\n【之前的对话历史】(仅供参考，帮助理解上下文)：\n{history_text}"

        # 2. 注入 RAG 背景知识 (如果有)
        if context:
            prompt = (
                f"{base_prompt}\n\n"
                "请参考以下【背景知识】回答用户的【最新问题】。\n"
                "⚠️ 重要提示：如果【背景知识】与问题完全无关，请忽略背景知识，直接用你的通用知识回答。\n\n"
                f"【背景知识】：\n{context}\n\n"
                f"【最新问题】：{query}"
            )
        else:
            # 3. 纯聊天模式 (无文档 或 开关关闭)
            prompt = (
                f"{base_prompt}\n\n"
                f"【最新问题】：{query}"
            )

        try:
            async for chunk in llm.astream(prompt):
                if chunk.content:
                    # 标准 SSE 格式：data: 内容\n\n
                    safe_content = chunk.content.replace('\n', '\\n')
                    yield f"data: {safe_content}\n\n"
        except Exception as e:
            print(f"Gemini 生成异常: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)