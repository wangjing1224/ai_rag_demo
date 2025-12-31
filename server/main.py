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
from db import get_db, ChatHistory , Feedback , SessionLocal

# ➕ 新增 UploadFile 和 File，用来处理文件上传
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File

# ➕ 引入 StreamingResponse
from fastapi.responses import StreamingResponse

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

# # 🔻🔻🔻 修改核心接口：加上数据库保存逻辑 🔻🔻🔻
# @app.post("/chat")
# async def chat(req: ChatRequest, db: Session = Depends(get_db)): # 注入数据库会话
#     user_q = req.question
    
#     # 1. 【记账】先把用户的提问存进去
#     user_msg = ChatHistory(role="user", content=user_q)
#     db.add(user_msg)
#     db.commit() # 提交保存
    
#     # 2. 调用 AI 回答
#     result = rag.chat(user_q)
#     ai_text = result["answer"]
    
#     # 3. 【记账】把 AI 的回答存进去
#     ai_msg = ChatHistory(role="ai", content=ai_text)
#     db.add(ai_msg)
#     db.commit() # 提交保存
    
#     return result

#  🔴 修改 /chat 接口
# 注意：把原来的 return result 改成返回 StreamingResponse
@app.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    user_q = req.question
    
    # 1. 先存用户的问题 (记账)
    user_msg = ChatHistory(role="user", content=user_q)
    db.add(user_msg)
    db.commit()

    # 2. 定义一个生成器函数，负责一边挤牙膏，一边拼凑完整的答案（为了最后存数据库）
    def generate_response():
        full_response = ""
        try:
            # 调用刚才写的 rag.chat_stream
            for chunk in rag.chat_stream(user_q):
                full_response += chunk
                yield chunk # 把这个字推给前端
        
        # 等全都流完了，把完整的答案存进数据库 (记账)
        # 注意：这里需要新建一个 Session，因为原来的 db 可能已经过期或被占用了
        # 为了简单，我们这里先省略存 AI 回答的步骤，或者用一种特殊技巧存
        # (下一轮我教你如何优雅地在流式结束时存数据库，先跑通流式再说)
        
        finally:
            print(f"✅ AI 回答完毕: {full_response}")

            # # 存 AI 的回答 (关键!)
            # # 这里我们要手动开一个新的数据库会话，因为外面的 db 可能已经断开了
            with SessionLocal() as db_save:
                ai_msg = ChatHistory(role="ai", content=full_response)
                db_save.add(ai_msg)
                db_save.commit()
                print("💾 [数据库] AI 回答已保存")

            # ai_mesg = ChatHistory(role="ai", content=full_response)
            # db.add(ai_mesg)
            # db.commit()
            # print("💾 [数据库] AI 回答已保存")
        

    # 3. 返回流式响应
    return StreamingResponse(generate_response(), media_type="text/plain")

# ➕ 新增：获取历史记录接口
@app.get("/history")
async def get_history(db: Session = Depends(get_db)):
    # 1. 查询数据库
    # order_by(desc): 按时间倒序查（最新的在前面）
    # limit(20): 只拿最近 20 条
    messages = db.query(ChatHistory)\
        .order_by(ChatHistory.create_time.desc())\
        .limit(20)\
        .all()
    
    # 2. 因为查出来是倒序（新->旧），为了前端显示正常（旧->新），我们要反转一下
    # [::-1] 是 Python 列表反转的黑魔法
    history = [{"role": msg.role, "content": msg.content} for msg in messages][::-1]
    
    return history

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