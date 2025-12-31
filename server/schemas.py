# server/schemas.py
from pydantic import BaseModel

# 接收前端聊天参数
class ChatRequest(BaseModel):
    question: str

# 接收前端反馈参数
class FeedbackRequest(BaseModel):
    msg_id: str
    score: int