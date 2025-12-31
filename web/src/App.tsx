import { useState, useRef, useEffect } from 'react';
import './App.less'; // 确保你的 CSS 文件里有我上一轮发的样式
import { chatApi } from './api';

// 定义消息类型
interface Message {
  role: 'user' | 'ai';
  content: string;
}

function App() {
  // --- 1. 状态定义 ---
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 🆕 新增：文件列表状态 (之前缺这个)
  const [files, setFiles] = useState<any[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- 2. 初始化加载 (历史记录 + 文件列表) ---
  useEffect(() => {
    const initData = async () => {
      // A. 加载历史记录
      try {
        const history = await chatApi.getHistory();
        // 兼容两种后端返回格式 (直接数组 或 {history: []})
        if (Array.isArray(history)) {
          setMessages(history);
        } else if (history && Array.isArray(history.history)) {
          setMessages(history.history);
        }
      } catch (e) {
        console.error("加载历史记录失败:", e);
      }

      // B. 加载文件列表
      try {
        const fileList = await chatApi.getFiles();
        if (Array.isArray(fileList)) {
            setFiles(fileList);
        }
      } catch (e) {
        console.error("加载文件列表失败:", e);
      }
    };

    initData();
  }, []);

  // --- 3. 核心功能函数 ---

  // 发送消息 (流式)
  const sendMessage = async () => {
    if (!input.trim()) return;

    // 1. 用户消息上屏
    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // 2. AI 占位
    setMessages(prev => [...prev, { role: 'ai', content: '' }]);

    try {
      // 3. 流式请求
      let fullText = "";
      await chatApi.chatStream(input, (chunk) => {
        fullText += chunk;
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];
          lastMsg.content = fullText;
          return newMessages;
        });
      });
    } catch (error) {
      console.error(error);
      alert("生成失败");
    } finally {
      setLoading(false);
    }
  };

  // 上传文件
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    try {
      await chatApi.uploadFile(file);
      alert('📚 上传并学习完成！');
      
      // 刷新文件列表
      const updatedList = await chatApi.getFiles();
      
      // 🛡️【加个保险】只有当它是数组时才更新，防止白屏
      if (Array.isArray(updatedList)) {
          setFiles(updatedList);
      } else {
          console.error("后端返回格式不对:", updatedList);
          // 可以在这里做一个兼容，防止老代码导致白屏
          if (updatedList.files && Array.isArray(updatedList.files)) {
             setFiles(updatedList.files);
          }
      }
    } catch (error) {
      console.error(error);
      alert('上传失败');
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // 删除文件
  const handleDeleteFile = async (filename: string) => {
    if (!confirm(`确定要删除文件 "${filename}" 吗？`)) return;
    try {
      await chatApi.deleteFile(filename);
      // 刷新列表
      const updatedList = await chatApi.getFiles();
      setFiles(updatedList);
    } catch (error) {
      console.error(error);
      alert("删除失败");
    }
  };

  // --- 4. 界面渲染 (左右布局) ---
  return (
    <div className="app-container">
      
      {/* 🟢 左侧边栏：知识库管理 */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>企业知识库</h2>
          <button className="new-chat-btn" onClick={() => setMessages([])}>
            + 新对话
          </button>
        </div>

        <hr style={{ margin: '20px 0', borderColor: 'rgba(255,255,255,0.1)' }} />
        
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', color: '#ccc' }}>
            <span>📚 文件列表</span>
            <span style={{ fontSize: '12px' }}>{files.length}</span>
        </div>

        <div className="file-list" style={{ flex: 1, overflowY: 'auto' }}>
          {files.map((file, index) => (
            <div key={index} className="file-item" style={{ 
              padding: '10px', background: 'rgba(255,255,255,0.05)', marginBottom: '8px', borderRadius: '6px', position: 'relative' 
            }}>
              <div style={{ fontWeight: 'bold', paddingRight: '20px', color: 'white' }}>{file.name}</div>
              <div style={{ fontSize: '12px', color: '#999', marginTop: '5px' }}>
                {file.size || '未知大小'}
              </div>
              
              {/* 删除按钮 */}
              <button 
                onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.name); }}
                style={{ position: 'absolute', top: '5px', right: '5px', background: 'none', border: 'none', color: '#ff5555', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          ))}
          {files.length === 0 && <div style={{color: '#666', textAlign:'center'}}>暂无文件</div>}
        </div>
      </div>

      {/* 🔵 右侧主区域：聊天窗口 */}
      <div className="chat-main">
        <div className="message-list">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="avatar">{msg.role === 'user' ? '🧑‍💻' : '🤖'}</div>
              <div className="content">{msg.content}</div>
            </div>
          ))}
          {loading && <div className="message ai"><div className="avatar">🤖</div><div className="content">正在思考...</div></div>}
        </div>

        {/* 底部输入框 */}
        <div className="input-area">
            {/* 文件上传 (隐形 Input) */}
            <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".pdf" onChange={handleFileUpload} />
            
            {/* 上传按钮 */}
            <button className="upload-btn" onClick={() => fileInputRef.current?.click()} disabled={loading} style={{ background: 'transparent', color: '#666', fontSize: '20px', padding: '0 10px' }}>
             📎
            </button>

            <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="请输入您的问题..."
            />
            <button onClick={sendMessage} disabled={loading}>发送</button>
        </div>
      </div>
    </div>
  );
}

export default App;