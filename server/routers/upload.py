# server/routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
from rag_core import rag_service
import traceback

# 1. 创建路由器
router = APIRouter(prefix="/upload", tags=["文件上传"])

# --- 上传接口 ---
@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    # 1. 确保目录存在
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    
    # 2. 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. 让 RAG 学习
    try:
        # print(f"📂 开始处理文件: {file.filename} ...")
        # rag_service.add_pdf(file_path)
        # print("✅ 处理完成")
        # return {"message": f"文件 {file.filename} 上传并处理成功！"}
        
        #根据文件名后缀决定如何处理
        filename_lower = file.filename.lower()
        
        if filename_lower.endswith(".pdf"):
            rag_service.add_pdf(file_path)
        elif filename_lower.endswith(".docx"):
            rag_service.add_word(file_path)
        elif filename_lower.endswith(".xlsx"):
            rag_service.add_excel(file_path)
        else:
            return{"status": "error", "message": "不支持的文件类型，仅支持 PDF、Word 和 Excel 文件"}
        return {"status": "success", "message": f"文件 {file.filename} 上传并处理成功！"}
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 删除接口 ---
@router.delete("/{filename}")
async def delete_file(filename: str):
    file_path = f"uploads/{filename}"
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        return {"status": "error", "message": "文件不存在"}
    
    try:
        rag_service.delete_file(filename)
        return {"status": "success", "message": f"{filename} 已删除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 🚨 重点修复：获取列表接口 ---
@router.get("/list")
async def list_files():
    if not os.path.exists("uploads"):
        return [] # ✅ 返回空数组，而不是 None 或 报错
    
    file_list = []
    
    #定义所有支持的文件类型后缀
    supported_suffixes = [".pdf", ".docx", ".xlsx"]
    
    # 遍历文件夹，组装详细信息
    for filename in os.listdir("uploads"):
        if filename.lower().endswith(tuple(supported_suffixes)):
        # if filename.endswith(".pdf"):
            file_path = f"uploads/{filename}"
            
            # 1. 算大小
            size_str = "0 KB"
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                size_str = f"{size_bytes / 1024:.1f} KB"
            
            # 2. 算分类 (简单逻辑：提取中括号里的字)
            category = "默认"
            if filename.startswith("[") and "]" in filename:
                category = filename.split("]")[0].strip("[")
            
            # 3. 塞进列表
            file_list.append({
                "name": filename,
                "size": size_str,
                "category": category
            })
            
    return file_list # ✅ 直接返回数组 [{}, {}]，不要包在 {"files": ...} 里！