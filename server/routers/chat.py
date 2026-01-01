# server/routers/chat.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

# 引入我们拆分出去的模块
# from db import get_db, ChatHistory, Feedback ,SessionLocal # 假设没改名
from database import SessionLocal, get_db
from models import ChatHistory, Feedback
from schemas import ChatRequest, FeedbackRequest
from rag_core import rag_service

router = APIRouter( tags=["聊天相关"])

#1.聊天接口（流式响应版）
@router.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    user_q = req.question
    user_model = req.model#获取前端传过来的模型名字
    
    # 1. 先存用户的问题 (记账)
    user_msg = ChatHistory(role="user", content=user_q)
    db.add(user_msg)
    db.commit()

    # 2. 定义一个生成器函数，负责一边挤牙膏，一边拼凑完整的答案（为了最后存数据库）
    def generate_response():
        full_response = ""
        try:
            # 调用刚才写的 rag.chat_stream
            for chunk in rag_service.chat_stream(user_q, model_name=user_model):
                full_response += chunk
                yield chunk # 把这个字推给前端
        
        finally:
            if full_response:
                print(f"✅ AI 回答完毕: {full_response}")
                # # 存 AI 的回答 (关键!)
                # # 这里我们要手动开一个新的数据库会话，因为外面的 db 可能已经断开了
                with SessionLocal() as db_save:
                    ai_msg = ChatHistory(role="ai", content=full_response)
                    db_save.add(ai_msg)
                    db_save.commit()

    return StreamingResponse(generate_response(), media_type="text/plain")


# 2. 反馈接口
@router.post("/feedback")  
async def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    msg_id = req.msg_id
    score = req.score

    feedback_entry = Feedback(msg_id=msg_id, score=score)
    db.add(feedback_entry)
    db.commit()

    return {"message": "反馈已记录，感谢您的参与！"}

# 3. 获取聊天记录接口
@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    # order_by(desc): 按时间倒序查（最新的在前面）
    # limit(20): 只拿最近 20 条
    messages = db.query(ChatHistory)\
        .order_by(ChatHistory.create_time.desc())\
        .limit(20)\
        .all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages][::-1]
    return {"history": history}    
    