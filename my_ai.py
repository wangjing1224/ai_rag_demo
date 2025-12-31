import os
from dotenv import load_dotenv
import streamlit as st
# 1. 这里改了：
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

st.set_page_config(page_title="我的 AI 知识库", page_icon="🤖")
st.title("🤖 企业知识库问答 Demo")

# --- 修改开始 ---
# 1. 加载环境变量
load_dotenv()

# 2. 获取 Key (不再是硬编码的字符串了)
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

# 3. 安全检查
if not API_KEY:
    st.error("⚠️ 报错：未找到 API Key！请确保你创建了 .env 文件并配置了 DEEPSEEK_API_KEY。")
    st.stop()
# --- 修改结束 ---

knowledge_base_content = """
【公司作息时间】
1. 上班时间：上午 9:30 - 下午 6:30。
2. 午休时间：中午 12:00 - 14:00 (两小时)。
3. 迟到政策：每月允许迟到 3 次，超过 3 次每次扣 50 元。
【福利政策】
1. 零食柜：每层楼茶水间无限供应零食和快乐水。
2. 生日福利：员工生日当天可提前 2 小时下班，并领取 200 元卡。
3. 团建：每季度一次部门聚餐，人均预算 150 元。
"""

@st.cache_resource
def load_db():
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=100, chunk_overlap=10)
    docs = [Document(page_content=x) for x in text_splitter.split_text(knowledge_base_content)]
    
    # 2. 这里改了：使用本地模型，而不是 API
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    return FAISS.from_documents(docs, embeddings)

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    model="deepseek-chat",
    temperature=0.1
)

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("请输入问题..."):
    st.session_state.history.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    db = load_db()
    docs = db.similarity_search(prompt, k=2)
    context = "\n".join([d.page_content for d in docs])
    
    final_prompt = f"已知信息：\n{context}\n\n用户问题：{prompt}\n请根据已知信息回答，不知道就说不知道。"
    
    response = llm.invoke(final_prompt).content
    st.chat_message("assistant").write(response)
    st.session_state.history.append({"role": "assistant", "content": response})