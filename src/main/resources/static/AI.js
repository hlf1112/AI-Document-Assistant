// 【新增】全局变量：存储对话历史
// 格式：{ role: 'user' | 'model', content: '...' }
let chatHistory = [];

// --- 接口1: 流式问答 (带记忆 + Markdown) ---
async function ask() {
    const qInput = document.getElementById('question');
    const q = qInput.value.trim();
    const chatBox = document.getElementById('chatBox');
    const btn = document.getElementById('btnSend');
    const useRag = document.getElementById('ragSwitch').checked;

    if(!q) return;

    // 渲染用户消息
    chatBox.innerHTML += `
        <div class="msg-row">
            <div class="user-label">我</div>
            <div class="user-msg">${q}</div>
        </div>
    `;
    qInput.value = '';
    btn.disabled = true;

    // 创建 AI 消息容器
    const aiContainer = document.createElement('div');
    aiContainer.className = 'msg-row';
    aiContainer.innerHTML = `
        <div class="ai-label">Gemini AI</div>
        <div class="ai-msg">Thinking...</div>
    `;
    chatBox.appendChild(aiContainer);
    const aiMsgDiv = aiContainer.querySelector('.ai-msg');
    let isFirstChunk = true;

    // 初始化 Markdown
    try { if (typeof marked !== 'undefined') marked.setOptions({ breaks: true }); } catch (e) {}

    let fullRawText = "";

    try {
        // 【关键修改】发送请求时携带历史记录
        // slice(-20) 表示只带最近 20 条记录 (即 10 轮对话)，防止 token 溢出
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: q,
                enable_rag: useRag,
                history: chatHistory.slice(-20) // ⬅️ 携带滑动窗口历史
            })
        });

        if (!response.ok) throw new Error("网络响应异常");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.trim().startsWith('data:')) {
                    if (isFirstChunk) { aiMsgDiv.innerHTML = ''; isFirstChunk = false; }

                    let content = line.substring(5).replace(/\\n/g, '\n');
                    fullRawText += content;

                    // Markdown 渲染
                    if (typeof marked !== 'undefined') {
                        aiMsgDiv.innerHTML = marked.parse(fullRawText);
                    } else {
                        aiMsgDiv.innerText = fullRawText;
                    }
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            }
        }

        // 【关键步骤】对话结束后，将本次问答存入历史记录
        chatHistory.push({ role: 'user', content: q });
        chatHistory.push({ role: 'model', content: fullRawText });

    } catch (error) {
        aiMsgDiv.innerHTML += `\n<span style="color:red;">[连接断开: ${error.message}]</span>`;
    } finally {
        btn.disabled = false;
        qInput.focus();
    }
}

// --- 接口2: 上传文件并学习 ---
async function uploadAndTrain() {
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('status');
    const btn = document.getElementById('btnTrain');

    if(fileInput.files.length === 0) {
        alert("请先选择一个文件！");
        return;
    }

    const file = fileInput.files[0];
    btn.disabled = true;
    status.innerHTML = "⏳ 正在上传并解析文档，请稍候...";
    status.style.color = "#e67e22";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.message) {
            status.innerHTML = "✅ " + result.message;
            status.style.color = "#27ae60";
        } else {
            status.innerHTML = "❌ " + (result.error || "未知错误");
            status.style.color = "#c0392b";
        }
    } catch (error) {
        status.innerHTML = "❌ 上传失败: " + error.message;
        status.style.color = "#c0392b";
        console.error(error);
    } finally {
        btn.disabled = false;
    }
}

// --- 接口3: 清空知识库 ---
async function resetKb() {
    const status = document.getElementById('status');
    const btnReset = document.getElementById('btnReset');

    if (!confirm("⚠️ 确定要清空所有已学习的文档吗？\n清空后 AI 将遗忘所有已上传的知识。")) {
        return;
    }

    btnReset.disabled = true;
    status.innerHTML = "⏳ 正在清空知识库...";

    try {
        const response = await fetch('/api/reset', { method: 'POST' });
        const result = await response.json();

        if (result.message) {
            status.innerHTML = "🗑️ " + result.message;
            status.style.color = "#e74c3c";

            // 【新增】清空前端对话记忆，防止 AI 记得已删除的知识
            chatHistory = [];
            // 可选：如果你想连聊天框里的字也清空，取消下面这行的注释
            document.getElementById('chatBox').innerHTML = '';
        } else {
            status.innerHTML = "❌ 清空失败";
        }
    } catch (error) {
        status.innerHTML = "❌ 连接失败: " + error.message;
        console.error(error);
    } finally {
        btnReset.disabled = false;
    }
}