# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 👇 变化在这里：
from database import engine
import models # 👈 必须导入这个，不然 create_all 找不到表！

# 引入路由模块
from routers import upload, chat

# 初始化数据库表
# Base.metadata.create_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="企业知识库助手 Pro")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 注册路由 (把拆分出去的模块挂载回来)
app.include_router(upload.router) # 负责 /upload
app.include_router(chat.router)   # 负责 /chat, /history, /feedback

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)