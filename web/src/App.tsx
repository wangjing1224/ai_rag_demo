import { useState,useRef } from 'react'; // 引入“记忆”功能
import axios from 'axios';        // 引入“打电话”功能
import './App.less';              // 引入“装修图纸”

// 【语法点：Interface】
// 定义一条聊天记录必须长什么样。
// 这样防止我们不小心把数字当成文字存进去。
interface Message {
  role: 'user' | 'ai';
  content: string;
}

function App() {
  // 【语法点：useState】
  // input: 存用户正在输入框里敲的字
  const [input, setInput] = useState(""); 
  
  // messages: 存所有的聊天记录，是一个 Message 类型的数组
  const [messages, setMessages] = useState<Message[]>([]);
  
  // loading: 标记是否正在等待 AI 回复（用来显示“思考中...”）
  const [loading, setLoading] = useState(false);

  // 2. 定义一个引用，用来模拟点击隐藏的 input 标签
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 3. 处理文件选择
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // A. 准备 FormData (就像把文件装进信封)
    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      // B. 发送到后端
      await axios.post('http://127.0.0.1:8000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data', // 告诉后端这是文件
        },
      });
      // C. 提示成功 (这里简单用 alert，实际可以用 Toast)
      alert('📚 知识库学习完成！你可以问我关于这个文档的问题了。');
      // 这里的逻辑可以优化，比如发一条系统消息到聊天框
      setMessages(prev => [...prev, { role: 'ai', content: `我已经学会了《${file.name}》的内容，快来问我吧！` }]);
    } catch (error) {
      console.error(error);
      alert('上传失败');
    } finally {
      setLoading(false);
      // 清空 input，防止同一个文件不能传两次
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- 发送消息的核心函数 ---
  const sendMessage = async () => {
    // 1. 如果没输入内容，就不发送 (trim 去掉前后空格)
    if (!input.trim()) return;

    // 2. 把用户说的话先“上屏”
    // ...messages 表示把旧记录展开，后面加上新的一条
    const newMessages = [...messages, { role: 'user', content: input } as Message];
    setMessages(newMessages);
    
    // 3. 清空输入框，并开启“加载中”状态
    setInput('');
    setLoading(true);

    try {
      // 【原理：HTTP 请求】
      // 用 axios 给咱们的 Python 后端 (8000端口) 打个电话
      // await 表示“在这里等一下”，直到后端回复了再往下走
      const res = await axios.post('http://127.0.0.1:8000/chat', {
        question: input  // 对应 Python 里的 ChatRequest
      });

      // 4. 收到回复后，把 AI 的话也“上屏”
      // res.data.answer 就是 Python 返回的那个 answer 字段
      setMessages([...newMessages, { role: 'ai', content: res.data.answer }]);
      
    } catch (error) {
      console.error(error);
      alert('连接后端失败！请检查 Python 黑窗口是不是关了？');
    } finally {
      // 无论成功失败，最后都要把“思考中”关掉
      setLoading(false);
    }
  };

  // --- 下面是界面画图 (TSX) ---
  return (
    <div className="chat-container">
      <header className="header">
        <h1>🤖 企业知识库助手</h1>
      </header>
      
      {/* 聊天记录列表区域 */}
      <div className="message-list">
        {/* 【语法点：map】 把数据数组变成一堆 HTML 标签 */}
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="avatar">{msg.role === 'user' ? '🧑‍💻' : '🤖'}</div>
            <div className="bubble">{msg.content}</div>
          </div>
        ))}
        
        {/* 【语法点：条件渲染】 只有 loading 为 true 时才显示 */}
        {loading && <div className="loading">AI 正在思考中...</div>}
      </div>

      {/* 底部输入区域 */}
      <div className="input-area">
        {/* ➕ 新增：隐藏的文件输入框 */}
        <input 
          type="file" 
          ref={fileInputRef}
          style={{ display: 'none' }} // 把它藏起来
          accept=".pdf" // 只允许传 PDF
          onChange={handleFileUpload}
        />
        
        {/* ➕ 新增：上传按钮 (点击它触发上面的 input) */}
        <button 
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          style={{ backgroundColor: '#28a745' }} // 弄个绿色区分一下
        >
          📎
        </button>

        <input 
          type="text"
          value={input}
          // 当用户打字时，实时更新 input 状态
          onChange={(e) => setInput(e.target.value)}
          // 监听回车键
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="请输入您的问题..."
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? '...' : '发送'}
        </button>
      </div>
    </div>
  );
}

export default App;