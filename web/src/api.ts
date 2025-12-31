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