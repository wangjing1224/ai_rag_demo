# 文件位置: server/main.py
import os
import sys
# 把上级目录加入路径，方便读取 .env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from rag_core import RAGService  # 引用刚才写的逻辑

# ➕ 新增：引入数据库相关
from sqlalchemy.orm import Session
from db import get_db, ChatHistory , Feedback

# ➕ 新增 UploadFile 和 File，用来处理文件上传
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
import shutil # 用来保存文件到硬盘

# 1. 加载配置
load_dotenv() # 读取 demo1/.env
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

# 2. 初始化服务
app = FastAPI()
rag = RAGService(API_KEY, BASE_URL)

# 3. 允许跨域 (让 React 能访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 4. 启动时自动加载知识库
# @app.on_event("startup")
# async def startup_event():
#     # 这里模拟读取文件，以后可以改成读取真正的文件
#     content = """
#     【公司作息时间】
#     1. 上班时间：上午 9:30 - 下午 6:30。
#     2. 午休时间：中午 12:00 - 14:00。
#     3. 迟到政策：每月允许迟到 3 次，超过 3 次每次扣 50 元。
#     【福利政策】
#     1. 零食柜：无限供应。
#     2. 生日福利：200 元卡。
#     """
#     rag.init_knowledge_base(content)

# ➕ 新增：文件上传接口
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 1. 确保有个文件夹专门存上传的文件
    os.makedirs("uploads", exist_ok=True)
    
    # 2. 文件的保存路径
    file_path = f"uploads/{file.filename}"
    
    # 3. 把用户发过来的文件，写入到硬盘里
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 4. 让 RAG 厨师去读这个文件
    try:
        rag.add_pdf(file_path)
        return {"message": f"文件 {file.filename} 上传并处理成功！知识库已更新。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. 定义接口
class ChatRequest(BaseModel):
    question: str


# @app.post("/chat")
# async def chat(req: ChatRequest):
#     return rag.chat(req.question)

# 🔻🔻🔻 修改核心接口：加上数据库保存逻辑 🔻🔻🔻
@app.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)): # 注入数据库会话
    user_q = req.question
    
    # 1. 【记账】先把用户的提问存进去
    user_msg = ChatHistory(role="user", content=user_q)
    db.add(user_msg)
    db.commit() # 提交保存
    
    # 2. 调用 AI 回答
    result = rag.chat(user_q)
    ai_text = result["answer"]
    
    # 3. 【记账】把 AI 的回答存进去
    ai_msg = ChatHistory(role="ai", content=ai_text)
    db.add(ai_msg)
    db.commit() # 提交保存
    
    return result


# 1. 定义接收的数据格式 (DTO)
class FeedbackRequest(BaseModel):
    msg_id: str
    score: int

# 2. 新增接口
@app.post("/feedback")
async def save_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    # 🔍 【追踪点 1】: 打印看看有没有收到前端的数据
    print(f"📡 [后端收到数据] msg_id={req.msg_id}, score={req.score}")
    
    # 3. 写入数据库
    new_feedback = Feedback(msg_id=req.msg_id, score=req.score)
    db.add(new_feedback)
    db.commit()
    
    # 🔍 【追踪点 2】: 确认已存入
    print("✅ [数据库] 写入成功！")
    
    return {"status": "ok", "message": "感谢您的反馈"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务，端口 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)