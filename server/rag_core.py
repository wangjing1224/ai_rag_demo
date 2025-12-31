# 文件位置: server/rag_core.py
import os
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

# ➕ 新增：引入 PDF 加载器
from langchain_community.document_loaders import PyPDFLoader

# 这里的逻辑和你之前的一模一样，只是封装成了类
class RAGService:
    def __init__(self, api_key, base_url):
        # 1. 初始化模型
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model="deepseek-chat",
            temperature=0.1
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = None
    
    # 1. 保留原来的字符串初始化方法 (为了兼容)
    def init_from_text(self, text_content):
        text_splitter = CharacterTextSplitter(separator="\n", chunk_size=100, chunk_overlap=10)
        docs = [Document(page_content=x) for x in text_splitter.split_text(text_content)]
        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        print("✅ 文本知识库初始化完成")

    # 2. ➕ 新增：从 PDF 文件初始化
    def add_pdf(self, file_path):
        print(f"正在读取文件: {file_path}")
        # A. 加载 PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load() # 这里会把 PDF 每一页读出来
        
        # B. 切分 (把每一页再切碎点，方便检索)
        text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        split_docs = text_splitter.split_documents(docs)

        # C. 存入向量库
        if self.vector_store is None:
            # 如果是第一次，就新建库
            self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
        else:
            # 如果库里已经有东西了，就把新书“加”进去
            self.vector_store.add_documents(split_docs)
        
        print(f"✅ PDF '{file_path}' 已成功加入知识库！")

    def chat(self, question: str):
        if not self.vector_store:
            return {"answer": "知识库为空，请先上传文件！", "context": ""}
            
        docs = self.vector_store.similarity_search(question, k=2)
        context = "\n".join([d.page_content for d in docs])
        
        prompt = f"已知信息：\n{context}\n\n用户问题：{question}\n请根据已知信息回答。"
        response = self.llm.invoke(prompt).content
        
        return {"answer": response, "context": context}