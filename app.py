import streamlit as st
import time
import json
import os
import sys

# Ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.agent_api import CloudAgentOrchestrator

# Configure page for a sleek chat experience
st.set_page_config(
    page_title="Enterprise AI Agent - SOC",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a professional dark look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0f172a;
    }
    /* Chat bubbles */
    .stChatMessage {
        background-color: transparent;
        border-radius: 10px;
    }
    [data-testid="chatAvatarIcon-user"] {
        background-color: #3b82f6;
    }
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #10b981;
    }
    /* Input box styling */
    .stChatInputContainer {
        border: 1px solid #334155;
        border-radius: 12px;
        background-color: #1e293b;
    }
    h1 {
        color: #f8fafc;
        text-align: center;
        font-family: 'Segoe UI', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Enterprise SOC Agent")
st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 2rem;'>أنا وكيلك الأمني المستقل. أحلل الأكواد، أكتشف الثغرات، وأكتب الترقيعات.</p>", unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "مرحباً! أنا الوكيل الأمني الخاص بك. يمكنك أن تطلب مني فحص رابط (DAST)، أو مراجعة كود (SAST)، أو استخراج حلول أمنية. كيف أساعدك اليوم؟"}
    ]
if "agent" not in st.session_state:
    st.session_state.agent = CloudAgentOrchestrator()

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle User Input
if prompt := st.chat_input("اكتب أمرك هنا... (مثال: افحص الرابط كذا)"):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process via Agent
    with st.chat_message("assistant"):
        with st.spinner("🧠 الوكيل المستقل يحلل طلبك ويستدعي الأدوات اللازمة..."):
            try:
                # Call the Agent Orchestrator
                response = st.session_state.agent.process_intent(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                err_msg = f"حدث خطأ أثناء الاتصال بالنماذج: {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
