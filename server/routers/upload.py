# server/routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
# 假设你的 RAG 服务实例需要被调用，这里先简单处理，或者在 main 里初始化
from rag_core import rag_service

# 1. 创建路由器
router = APIRouter(prefix="/upload", tags=["文件上传"])

@router.post("/")
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
        rag_service.add_pdf(file_path)
        return {"message": f"文件 {file.filename} 上传并处理成功！知识库已更新。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))      