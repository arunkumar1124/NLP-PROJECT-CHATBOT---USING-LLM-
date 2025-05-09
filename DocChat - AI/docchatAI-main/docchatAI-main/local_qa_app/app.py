# app.py

import streamlit as st
from utils import load_text_file, chunk_text, build_faiss_index, get_most_relevant_chunks, generate_answer
import datetime

st.set_page_config(
    page_title="Document Q&A Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🌈 Custom styles with professional background and modern UI
st.markdown("""
    <style>
    body, .main {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        font-family: 'Segoe UI', sans-serif;
    }
    .chat-container {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin: 10px 0;
    }
    .chat-row {
        display: flex;
        align-items: flex-start;
        margin: 1.2rem 0;
        padding: 0 1rem;
    }
    .chat-user {
        justify-content: flex-end;
    }
    .chat-assistant {
        justify-content: flex-start;
    }
    .chat-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-avatar {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
    }
    .assistant-avatar {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
    }
    .chat-bubble {
        padding: 1rem 1.5rem;
        border-radius: 18px;
        max-width: 75%;
        font-size: 15px;
        color: #2c3e50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        line-height: 1.5;
        position: relative;
        margin: 0 1rem;
    }
    .chat-user .chat-bubble {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-bottom-right-radius: 4px;
    }
    .chat-assistant .chat-bubble {
        background: white;
        border-bottom-left-radius: 4px;
    }
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #ffd54f 0%, #ffb300 100%);
        color: #2c3e50;
        border: none;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .stFileUploader {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stFileUploader label {
        font-weight: 500;
        color: #2c3e50;
    }
    .stChatInput {
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .document-item {
        padding: 0.8rem;
        margin: 0.5rem 0;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .document-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .main-header {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "document_history" not in st.session_state:
    st.session_state.document_history = []
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None

# Sidebar for document history
with st.sidebar:
    st.markdown('<div class="sidebar-header">📚 Document History</div>', unsafe_allow_html=True)
    
    # Document upload in sidebar
    uploaded_file = st.file_uploader("📄 Upload New Document", type=["txt"])
    
    if uploaded_file:
        with st.spinner("Processing document..."):
            text = load_text_file(uploaded_file)
            chunks = chunk_text(text)
            index, chunk_list = build_faiss_index(chunks)
            
            # Store document info
            doc_info = {
                "name": uploaded_file.name,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "index": index,
                "chunk_list": chunk_list
            }
            st.session_state.document_history.append(doc_info)
            st.session_state.current_doc = doc_info
            st.success("✅ Document processed successfully!")
    
    # Display document history
    if st.session_state.document_history:
        st.markdown("### Recent Documents")
        for idx, doc in enumerate(reversed(st.session_state.document_history)):
            if st.button(f"📄 {doc['name']} ({doc['date']})", key=f"doc_{idx}"):
                st.session_state.current_doc = doc
                st.session_state.chat_history = []  # Clear chat history when switching documents
                st.rerun()

# Main content area
st.markdown('<div class="main-header">', unsafe_allow_html=True)
col1, col2 = st.columns([8, 2])
with col1:
    st.markdown("## 🤖 DocChatAI...")
    if st.session_state.current_doc:
        st.markdown(f"**Current Document:** {st.session_state.current_doc['name']}")
with col2:
    if st.button("🧹 Clear Chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Chat interface
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Display chat history
for q, a in st.session_state.chat_history:
    st.markdown(f"""
        <div class="chat-row chat-user">
            <div class="chat-bubble">{q}</div>
            <div class="chat-avatar user-avatar">👤</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
        <div class="chat-row chat-assistant">
            <div class="chat-avatar assistant-avatar">🤖</div>
            <div class="chat-bubble">{a}</div>
        </div>
    """, unsafe_allow_html=True)

# Chat input
if st.session_state.current_doc:
    user_input = st.chat_input("Ask a question about the document...")
    if user_input:
        with st.spinner("Thinking..."):
            context = "\n".join(get_most_relevant_chunks(
                user_input, 
                st.session_state.current_doc["index"], 
                st.session_state.current_doc["chunk_list"]
            ))
            answer = generate_answer(user_input, context, st.session_state.chat_history)
            st.session_state.chat_history.append((user_input, answer))
            st.rerun()
else:
    st.info("👈 Please upload a document from the sidebar to start chatting!")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        🛠️ Powered by Streamlit and TinyLlama | 
        <a href='#' style='color: #666; text-decoration: none;'>Documentation</a> | 
        <a href='#' style='color: #666; text-decoration: none;'>About</a>
    </div>
""", unsafe_allow_html=True)
