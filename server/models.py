# server/models.py
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.sql import func
# 记得保留这个 MySQL 专用的类型
from sqlalchemy.dialects.mysql import DATETIME 
from datetime import datetime

# 👈 从 database.py 引入基类
from database import Base 

# --- 聊天记录表 ---
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20)) # user / ai
    content = Column(Text)
    # 保留微秒精度
    create_time = Column(DATETIME(fsp=6), default=datetime.now)

# --- 点赞反馈表 ---
class Feedback(Base):
    __tablename__ = "feedback_log"

    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(50))
    score = Column(Integer)
    create_time = Column(DATETIME(fsp=6), default=datetime.now)