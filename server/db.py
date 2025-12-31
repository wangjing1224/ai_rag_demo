# 文件位置: server/db.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv
# 🔴 修改引入：不再用通用的 DateTime，而是用 MySQL 专用的
from sqlalchemy.dialects.mysql import DATETIME

# 1. 加载环境变量 (最好把数据库密码放在 .env 里，这里为了教学方便先写死或读取)
load_dotenv()
#读取配置 (如果没有读到，第二个参数是默认值)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ai_chat_db")

#拼接数据库连接 URL
# f-string: Python 的字符串格式化神器
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 打印一下看看对不对 (调试完记得注释掉，防止密码泄露在控制台)
print(f"正在连接数据库: {DB_URL}")
# 2. 创建连接引擎
engine = create_engine(DB_URL)

# 3. 创建会话工厂 (以后我们要操作数据库，就找 SessionLocal 要人)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 定义模型基类
Base = declarative_base()

# 5. 定义表结构 (对应 Navicat 里的那张表)
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), default="default") # 暂时默认 default
    role = Column(String(10))  # user 或 ai
    content = Column(Text)     # 聊天内容
    # create_time = Column(DateTime, default=datetime.now)
    # fsp=6 代表保留 6 位小数 (微秒)
    create_time = Column(DATETIME(fsp=6), default=datetime.now)

# ➕ 新增：反馈表
class Feedback(Base):
    __tablename__ = "feedback_log"

    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(50)) # 关联哪条消息
    score = Column(Integer)     # 1代表赞，-1代表踩
    create_time = Column(DateTime, default=datetime.now)

# 6. 自动建表 (如果表不存在，这行代码会帮你在数据库建表，双重保险)
Base.metadata.create_all(bind=engine)

# 工具函数：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()