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

# 4. 利用可能なFlashモデルを自動探索して読み込む関数
@st.cache_resource
def load_model():
    # 利用可能なモデルの中から、Flash系のモデルを優先的に探す
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    # 優先したいモデル名のキーワード順
    priority_keywords = ["2.5-flash-lite", "2.5-flash", "2.0-flash", "flash"]
    
    target_model_name = None
    for kw in priority_keywords:
        for m_name in available_models:
            if kw in m_name:
                target_model_name = m_name
                break
        if target_model_name:
            break
            
    # もし該当が見つからない場合は一覧の最初のモデルを使用
    if not target_model_name and available_models:
        target_model_name = available_models[0]
        
    if not target_model_name:
        raise Exception("利用可能なGeminiモデルが見つかりませんでした。APIキーを確認してください。")

    return genai.GenerativeModel(
        model_name=target_model_name,
        system_instruction=SYSTEM_PROMPT
    ), target_model_name

try:
    model, used_model_name = load_model()
    # 接続に成功したモデル名を画面上に小さく表示
    st.caption(f"🤖 接続モデル: `{used_model_name}`")
except Exception as e:
    st.error(f"モデルの自動接続に失敗しました: {e}")
    st.stop()

# 5. セッション状態（会話履歴）の初期化
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "messages" not in st.session_state:
    st.session_state.messages = []

# 6. これまでの会話履歴を表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 7. ユーザー入力エリア
st.info("💡 ヒント：キーボードのマイクボタン（OS標準の音声入力）を使うと、声で英語を入力できます！")
user_input = st.chat_input("英語でメッセージを入力...")

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

            # 8. Web Speech APIによる自動音声読み上げ (TTS)
            safe_text = response.text.replace('\n', ' ').replace("'", "\\'").replace('"', '\\"')
            tts_html = f"""
            <script>
                const utterance = new SpeechSynthesisUtterance('{safe_text}');
                utterance.lang = 'en-US';
                utterance.rate = 0.9; // 中学生向けにややゆっくり再生
                window.speechSynthesis.cancel(); // 前の読み上げをキャンセル
                window.speechSynthesis.speak(utterance);
            </script>
            """
            components.html(tts_html, height=0)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
