import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components

# 1. ページ設定
st.set_page_config(page_title="AI English Teacher", page_icon="🗣️")
st.title("🗣️ AI英会話先生")

# 2. SecretsからAPIキーを取得して設定
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Secretsに GEMINI_API_KEY が設定されていません。Streamlit Cloudの設定画面で追加してください。")
    st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# 3. システムプロンプトの設定（中学生向け）
SYSTEM_PROMPT = """
あなたは日本の中学生に英語を教える、優しくフレンドリーなAI教師です。
- 生徒の英語表現にミスがあれば、優しく1つだけ訂正してください。
- 常に英語で、2〜3文（30語以内）で短く返答してください。
- 会話を続けるために、最後に必ず簡単な質問を1つ投げかけてください。
- 中学生が習う基本的な単語と文法を中心に使ってください。
"""

# 4. 利用可能な最新モデルを自動探索して読み込む関数
@st.cache_resource
def load_model():
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception as e:
        pass

    priority_keywords = ["3.5-flash-lite", "3.5-flash", "3.0-flash", "2.5-flash-lite", "flash"]
    target_model_name = None
    for kw in priority_keywords:
        for m_name in available_models:
            if kw in m_name:
                target_model_name = m_name
                break
        if target_model_name:
            break
            
    if not target_model_name:
        target_model_name = "models/gemini-3.5-flash-lite"

    return genai.GenerativeModel(
        model_name=target_model_name,
        system_instruction=SYSTEM_PROMPT
    ), target_model_name

try:
    model, used_model_name = load_model()
    st.caption(f"🤖 接続モデル: `{used_model_name}`")
except Exception as e:
    st.error(f"モデルの自動接続に失敗しました: {e}")
    st.stop()

# 5. セッション状態の初期化
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "messages" not in st.session_state:
    st.session_state.messages = []

# 6. これまでの会話履歴を表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 7. 音声認識（STT）コンポーネント：ボタンを押して英語を声で入力
st.write("---")
st.markdown("### 🎤 音声で話しかける")

stt_html = """
<div style="text-align: center; margin-bottom: 10px;">
    <button id="mic-btn" style="
        padding: 12px 24px;
        font-size: 18px;
        font-weight: bold;
        background-color: #FF4B4B;
        color: white;
        border: none;
        border-radius: 25px;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: 0.2s;
    ">
        🎤 タップして英語で話す
    </button>
    <p id="stt-status" style="margin-top: 8px; font-size: 14px; color: #555;">ボタンを押してマイクに向かって英語を話してください</p>
</div>

<script>
    const btn = document.getElementById('mic-btn');
    const status = document.getElementById('stt-status');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US'; // 英語固定
        recognition.interimResults = false;

        btn.onclick = () => {
            try {
                recognition.start();
                btn.innerText = "🔴 聞き取り中... 英語で話してね";
                btn.style.backgroundColor = "#2E7D32";
                status.innerText = "話し終わると自動でメッセージ欄に入力されます";
            } catch(e) {
                recognition.stop();
            }
        };

        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            
            // Streamlitのchat_inputを取得してテキストを自動セット
            const doc = window.parent.document;
            const chatInput = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            
            if (chatInput) {
                chatInput.value = text;
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                status.innerText = '✅ 入力完了！「送信(Enter)」ボタンを押してください';
            } else {
                status.innerText = '音声認識結果: "' + text + '" (コピーして入力欄に貼り付けてください)';
            }

            btn.innerText = "🎤 タップして英語で話す";
            btn.style.backgroundColor = "#FF4B4B";
        };

        recognition.onerror = (event) => {
            btn.innerText = "🎤 タップして英語で話す";
            btn.style.backgroundColor = "#FF4B4B";
            status.innerText = "⚠️ 音声を認識できませんでした。マイク許可を確認してもう一度試してください。";
        };

        recognition.onend = () => {
            btn.innerText = "🎤 タップして英語で話す";
            btn.style.backgroundColor = "#FF4B4B";
        };
    } else {
        btn.disabled = true;
        btn.innerText = "⚠️ お使いのブラウザは音声入力非対応です";
        status.innerText = "Google ChromeやSafariをご利用ください";
    }
</script>
"""
components.html(stt_html, height=110)

# 8. ユーザー入力エリア（キーボード／音声認識からの自動入力兼用）
user_input = st.chat_input("英語でメッセージを入力（または上のボタンで音声入力）...")

if user_input:
    # ユーザーのメッセージを表示・記録
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Gemini APIからの回答取得
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(user_input)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

            # 9. Web Speech APIによる自動音声読み上げ (TTS)
            safe_text = response.text.replace('\n', ' ').replace("'", "\\'").replace('"', '\\"')
            tts_html = f"""
            <script>
                const utterance = new SpeechSynthesisUtterance('{safe_text}');
                utterance.lang = 'en-US';
                utterance.rate = 0.9;
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utterance);
            </script>
            """
            components.html(tts_html, height=0)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
