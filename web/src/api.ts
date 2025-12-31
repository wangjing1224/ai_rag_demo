import axios from 'axios';

// 1. 读取环境变量 (注意写法是 import.meta.env)
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 2. 创建一个专用的 axios 实例
const apiClient = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 3. 定义接口并导出
export const chatApi = {
    // 聊天接口
    sendMessage: async (question: string) => {
        const response = await apiClient.post('/chat', { question });
        return response.data; // 直接返回 data，调用者不用再 .data 了
    },

    // ➕ 新增：流式对话
    // onMessage 是一个回调函数，每收到一个字，就调用它一次
    chatStream: async (question: string, onMessage: (text: string) => void) => {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question }),
        });

        if (!response.body) return;

        // 1. 获取读取器
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // 2. 循环读取管道里的数据
        while (true) {
            const { done, value } = await reader.read();
            if (done) break; // 读完了

            // 3. 解码并通知 UI
            const chunk = decoder.decode(value, { stream: true });
            onMessage(chunk);
        }
    },

    // 上传文件 (需要特殊处理 Header)
    uploadFile: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await apiClient.post('/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    // 点赞反馈
    sendFeedback: async (msgId: string, score: number) => {
        const response = await apiClient.post('/feedback', {
            msg_id: msgId,
            score: score
        });
        return response.data;
    }
};