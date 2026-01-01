# 文件位置: server/rag_core.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter  # ➕ 新增：递归切分器
from langchain_openai import OpenAIEmbeddings   # 👈 嵌入模型
from langchain_openai import ChatOpenAI         # 👈 聊天模型

# ➕ 新增：引入 PDF,word,excel 加载器
from langchain_community.document_loaders import PyPDFLoader,Docx2txtLoader,UnstructuredExcelLoader

load_dotenv()

# 这里的逻辑和你之前的一模一样，只是封装成了类
class RAGService:
    def __init__(self):
        # # 1. 初始化模型
        # self.llm = ChatOpenAI(
        #     api_key=api_key,
        #     base_url=base_url,
        #     model="deepseek-chat",
        #     temperature=0.1
        # )
        
        # 1. 定义一个配置字典，把所有模型的“身份证”都登记在这里
        # 这样以后想加新模型，只需要改这里，不用动业务逻辑
        self.model_config = {
            # === DeepSeek 系列 ===
            "deepseek-chat": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("DEEPSEEK_BASE_URL"),
                "temperature": 0.3
            },
            "deepseek-reasoner": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("DEEPSEEK_BASE_URL"),
                "temperature": 0.1 # 推理模型通常低温
            },
            
            # === 阿里云通义千文系列 ===
            "qwen-plus": {
                "api_key": os.getenv("QWEN_API_KEY"),
                "base_url": os.getenv("QWEN_BASE_URL"),
                "temperature": 0.5
            },
            "qwen-max": { # 通义千文最强版
                "api_key": os.getenv("QWEN_API_KEY"),
                "base_url": os.getenv("QWEN_BASE_URL"),
                "temperature": 0.5
            },

            # === OpenAI 系列 ===
            "gpt-4o": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL"),
                "temperature": 0.7
            }
        }
        
        # 默认初始化一个模型 (防止启动报错)
        self.current_llm = self._create_llm("deepseek-chat")   
        
        print("正在加载本地嵌入模型 (首次运行可能需要下载)...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") 
        # ✅ 使用这个！它会下载一个小模型到你电脑上，不用联网也能跑
        self.vector_store_path = "faiss_index" # 💾 索引保存路径
        self.vector_store = self._load_vector_store() # 🔄 启动时尝试加载
    
    # 🛠️ 工厂方法：专门负责生产 LLM 对象
    def _create_llm(self, model_name):
        config = self.model_config.get(model_name)
        if not config:
            raise ValueError(f"⚠️ 模型 {model_name} 的 API Key 未配置，请检查 .env 文件")
        
        print(f"🔄 正在初始化模型: {model_name} (URL: {config['base_url']})")
        
        return ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=model_name,
            temperature=config.get("temperature", 0.3)
        )
        
    # 🔄 内部方法：尝试从硬盘加载索引
    def _load_vector_store(self):
        if os.path.exists(self.vector_store_path):
            try:
                # allow_dangerous_deserialization=True 是为了加载本地 pickle 文件
                vs = FAISS.load_local(self.vector_store_path, self.embeddings, allow_dangerous_deserialization=True)
                print("✅ [RAG] 成功加载本地索引！")
                return vs
            except Exception as e:
                print(f"⚠️ [RAG] 加载索引失败，将重建: {e}")
                return None
        return None

    # 💾 内部方法：保存索引到硬盘
    def _save_vector_store(self):
        if self.vector_store:
            self.vector_store.save_local(self.vector_store_path)
            print("💾 [RAG] 索引已保存到本地")
    
    # 1. 保留原来的字符串初始化方法 (为了兼容)
    def init_from_text(self, text_content):
        text_splitter = CharacterTextSplitter(separator="\n", chunk_size=100, chunk_overlap=10)
        docs = [Document(page_content=x) for x in text_splitter.split_text(text_content)]
        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        print("✅ 文本知识库初始化完成")

    # 🔄 [重构] 这是一个内部通用方法，不管什么文件，读出来后都走这套流程
    def _proccess_and_save(self, docs,file_path):
        print(f"✅ 成功加载 {len(docs)} 页 文档")
        
        # 统一使用配置好的切分器
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = splitter.split_documents(docs)
        print(f"✅ 切分成 {len(split_docs)} 知识片段")
        
        if self.vector_store:
            self.vector_store.add_documents(split_docs)
            print("✅ 已经追加到现有知识库")
        else:
            self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
            print("✅ 初始化了新的知识库")  
            
        self._save_vector_store()
        print(f"✅ 文件 '{os.path.basename(file_path)}' 已成功添加到知识库！") 
        
    # 2. 新增：添加 PDF 文件到知识库,调用上面的通用方法    
    def add_pdf(self, file_path):
        # try:
        #     #加载 PDF 文件
        #     loader = PyPDFLoader(file_path)
        #     docs = loader.load()
        #     print(f"✅ 成功加载 {len(docs)} 页 PDF")
            
        #     #切分文档
        #     # 💡 知识点：chunk_size 越小，检索越精准，但丢失上下文；越大，上下文完整，但噪音多。
        #     splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        #     split_docs = splitter.split_documents(docs)
        #     print(f"✅ 切分成 {len(split_docs)} 知识片段")
            
        #     #加入到向量库(内存中)
        #     if self.vector_store:
        #         self.vector_store.add_documents(split_docs)
        #         print("✅ 已经追加到现有知识库")
        #     else:
        #         self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
        #         print("✅ 初始化了新的知识库")
                
        #     #保存到本地
        #     self._save_vector_store()
        #     print(f"✅ 文件 '{os.path.basename(file_path)}' 已成功添加到知识库！")
        # except Exception as e:
        #     print(f"❌ 添加文件失败: {e}")
        #     raise e # 抛出异常以便上层处理    
        print(f"正在处理 PDF 文件: {file_path}")
        try:
            # 加载 PDF 文件
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            self._proccess_and_save(docs,file_path)
        except Exception as e:
            print(f"❌ 添加文件失败: {e}")
            raise e  # 抛出异常以便上层处理
         
    # ➕ 新增：添加 Word 文件到知识库,调用上面的通用方法
    def add_word(self, file_path):
        print(f"正在处理 Word 文件: {file_path}")
        try:
            # 加载 Word 文件
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            self._proccess_and_save(docs,file_path)
        except Exception as e:
            print(f"❌ 添加文件失败: {e}")
            raise e  # 抛出异常以便上层处理
    
    # ➕ 新增：添加 Excel 文件到知识库,调用上面的通用方法
    def add_excel(self, file_path):
        print(f"正在处理 Excel 文件: {file_path}")
        try:
            # 加载 Excel 文件
            #mode="elements" 按行加载，更适合表格
            loader = UnstructuredExcelLoader(file_path,mode="elements")
            docs = loader.load()
            self._proccess_and_save(docs,file_path)
        except Exception as e:
            print(f"❌ 添加文件失败: {e}")
            raise e  # 抛出异常以便上层处理
              
    #🆕 新增：删除文件（通过重建索引的方式，这是最简单稳妥的方法）
    def delete_file(self, filename):
        # if not self.vector_store:
        #     print("⚠️ 知识库为空，无需删除")
        #     return
        
        # # 1. 获取所有文档
        # all_docs = self.vector_store.documents
        
        # # 2. 过滤掉要删除的文件对应的文档
        # remaining_docs = [doc for doc in all_docs if not doc.metadata.get("source", "").endswith(filename)]
        
        # # 3. 重建索引
        # self.vector_store = FAISS.from_documents(remaining_docs, self.embeddings)
        # print(f"✅ 文件 '{filename}' 已从知识库中删除！")
        
        # # 4. 保存更新后的索引
        # self._save_vector_store()
        
        # 1. 简单粗暴方案：清空内存里的索引
        self.vector_store = None
        
        # 2. 重新扫描 uploads 文件夹里的所有 PDF 重建
        # (真实生产环境会用 delete by ID，但 FAISS 简单版不支持，重建最稳)
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            files = [f for f in os.listdir(uploads_dir) if f.endswith(".pdf") and f != filename]
            
            # 如果还有其他文件，就重新把它们加进去
            for f in files:
                self.add_pdf(os.path.join(uploads_dir, f))
                
        # 如果删光了，记得把本地的索引文件也删了
        if not self.vector_store and os.path.exists(self.vector_store_path):
            import shutil
            shutil.rmtree(self.vector_store_path)
    
    # 🔴 也就是把原来的 chat 方法改造成下面这样
    def chat_stream(self, question: str , model_name: str="deepseek-chat"):
        if not self.vector_store:
            yield "知识库为空，请先上传文件！"
            return
            
        # 1. 检索 (和以前一样)
        docs = self.vector_store.similarity_search(question, k=2)
        context = "\n".join([d.page_content for d in docs])
        prompt = f"已知信息：\n{context}\n\n用户问题：{question}\n请根据已知信息回答。"
        
        # # 2. 调用 LLM (开启流式模式!)
        # # 注意：这里我们直接循环 llm.stream，而不是 invoke
        # for chunk in self.llm.stream(prompt):
        #     content = chunk.content
        #     if content:
        #         # yield 就像是“挤牙膏”，挤一点出来给外面
        #         yield content
        
        # 动态切换逻辑
        # 如果前端传来的模型名，不在我们的配置表里，就用默认的 deepseek-chat
        if model_name not in self.model_config:
            yield f"⚠️ 模型 {model_name} 未配置，使用默认模型 deepseek-chat。"
            model_name = "deepseek-chat"
            
        # 2. 动态创建模型
        print(f"🔄 当前请求使用模型: {model_name}")
        try:
            target_llm = self._create_llm(model_name)

            for chunk in target_llm.stream(prompt):
                content = chunk.content
                if content:
                    yield content
        except Exception as e:
            yield f"❌ 调用模型失败: {e}"

# # 实例化一个全局对象供大家调用
# rag_service = RAGService(
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url=os.getenv("DEEPSEEK_BASE_URL")
# )

# 🆕 重构：实例化
rag_service = RAGService()