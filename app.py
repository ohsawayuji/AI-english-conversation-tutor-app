import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components

# ページ設定
st.set_page_config(page_title="AI English Teacher", page_icon="🗣️")
st.title("🗣️ AI英会話先生")

# APIキーの読み込み（ローカルでは secrets.toml から、クラウドでは設定画面から）
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Geminiモデルの準備（システムプロンプトを設定）
SYSTEM_PROMPT = """
あなたは日本の中学生に英語を教える、フレンドリーなAI教師です。
- 生徒の英語にミスがあれば、優しく1つだけ訂正してください。
- 常に英語で、2〜3文（30語以内）で短く返答してください。
- 会話を続けるために、最後に必ず簡単な質問を1つ投げかけてください。
"""

@st.cache_resource
def load_model():
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=SYSTEM_PROMPT
    )

model = load_model()

# 会話履歴の保存用（セッションステート）
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "messages" not in st.session_state:
    st.session_state.messages = []

# これまでの会話を表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 生徒（ユーザー）からの入力
st.info("💡 ヒント：端末の「音声入力ボタン（マイクのマーク）」を使って英語で話しかけてみよう！")
user_input = st.chat_input("英語でメッセージを入力...")

if user_input:
    # ユーザーの入力を画面に追加
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Gemini APIを呼び出して返答を取得
    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(user_input)
        st.markdown(response.text)
    
    st.session_state.messages.append({"role": "assistant", "content": response.text})

    # Web Speech APIでAIの返答を音声で読み上げる（JavaScriptを非表示で実行）
    safe_text = response.text.replace('\n', ' ').replace("'", "\\'")
    tts_html = f"""
    <script>
        const utterance = new SpeechSynthesisUtterance('{safe_text}');
        utterance.lang = 'en-US';
        utterance.rate = 0.9; // 少しゆっくり
        window.speechSynthesis.speak(utterance);
    </script>
    """
    components.html(tts_html, height=0)
