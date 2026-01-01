# server/schemas.py
from pydantic import BaseModel
from typing import Optional

# 接收前端聊天参数
class ChatRequest(BaseModel):
    question: str
    # 👇 2. 新增这个字段：允许前端传模型名字，默认是用 deepseek-chat
    model: Optional[str] = "deepseek-chat"

# 接收前端反馈参数
class FeedbackRequest(BaseModel):
    msg_id: str
    score: int