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

# 3. システムプロンプトの設定（中学生・言い淀み対応向け）
SYSTEM_PROMPT = """
あなたは日本の中学生に優しく寄り添う、フレンドリーで褒め上手なAI英語教師です。

【役割と姿勢】
- 生徒が「Uhh...」「Um...」「Well...」と言い淀んだり単語に詰まったりしても絶対に否定せず、「Take your time!」「Good try!」などの温かい言葉で優しく励ましてください。
- 生徒が単語だけで答えたり途切れたりした場合は、生徒の意図を優しく推測し、「Did you mean ...?」と補完したり、「For example, apple or banana?」のように答えやすい選択肢やヒントを出して会話を繋げてくだい。

【返答のルール】
- 返答はすべて英語で、2〜3文（30語以内）の短い文に収めてください。
- 生徒の表現に文法や単語のミスがあっても、会話のテンポを優先し、直すのは多くて1箇所だけに留めてください。
- 会話を続けるため、返答の最後には必ず中学生レベルの簡単な質問（Yes/Noで答えられるもの、または2択の質問）を1つ投げかけてください。
- 使用する単語と文法は、英検3級〜4級レベル（中学校で習う基本表現）を中心にしてください。
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

# 5. 生徒向け使い方ガイド（折りたたみ表示）
with st.expander("📖 使い方ガイド（はじめに読んでね！）", expanded=False):
    st.markdown("""
    ### 🎤 上手な話し方のコツ
    1. **マイクの距離**: マイク（または端末）は**口元からこぶし1個分（約10cm）**離して使おう。
    2. **大きな声で発表**: 授業で発表するときと同じくらいのハキハキした声で話そう！
    3. **「Uhh...」「Um...」と言ってOK**: 言葉につまったら黙らずに「Uhh...」「Um...」と声に出しながら考えよう。声を出し続けていればAI先生は待ってくれます。
    4. **耳で何度も聴こう**: 聞き取れなかったときは「🔊 もう一度聴く」ボタンをタップして何度でも聴き直そう！
    """)

# 6. セッション状態の初期化
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "messages" not in st.session_state:
    st.session_state.messages = []

# 音声再生ボタンを出力するヘルパー関数
def render_audio_button(text):
    safe_text = text.replace('\n', ' ').replace("'", "\\'").replace('"', '\\"')
    html_code = f"""
    <div style="margin-bottom: 5px;">
        <button onclick="
            const utterance = new SpeechSynthesisUtterance('{safe_text}');
            utterance.lang = 'en-US';
            utterance.rate = 0.9;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        " style="
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
            background-color: #0288D1;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            🔊 もう一度聴く
        </button>
    </div>
    """
    components.html(html_code, height=45)

# 7. これまでの会話履歴を表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # 「もう一度聴く」ボタンを表示
            render_audio_button(msg["content"])
            # テキストは折りたたんで非表示
            with st.expander("👁️ テキストを表示して確認する", expanded=False):
                st.markdown(msg["content"])

# 8. 音声認識（STT）＋ マイク音量（VAD）ハイブリッドコンポーネント
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

    let sendTimer = null;
    let recognition = null;
    let isListening = false;
    let audioCtx = null;
    let analyser = null;
    let micStream = null;
    let animFrameId = null;
    let hasSaidSomething = false;

    function resetButtonUI(msg) {
        if (sendTimer) { clearTimeout(sendTimer); sendTimer = null; }
        if (animFrameId) { cancelAnimationFrame(animFrameId); animFrameId = null; }
        if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
        if (audioCtx) { audioCtx.close(); audioCtx = null; }
        
        isListening = false;
        hasSaidSomething = false;
        btn.disabled = false;
        btn.innerText = "🎤 タップして英語で話す";
        btn.style.backgroundColor = "#FF4B4B";
        if (msg) status.innerText = msg;
    }

    if (SpeechRecognition) {
        btn.onclick = async () => {
            if (isListening) {
                stopAndSendNow();
                return;
            }

            try {
                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioCtx.createAnalyser();
                const source = audioCtx.createMediaStreamSource(micStream);
                source.connect(analyser);
                analyser.fftSize = 256;
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);

                if (recognition) { try { recognition.abort(); } catch(e) {} }
                recognition = new SpeechRecognition();
                recognition.lang = 'en-US';
                recognition.interimResults = true;
                recognition.continuous = true;

                recognition.onstart = () => {
                    isListening = true;
                    btn.innerText = "🔴 聞き取り中... (声を出している間は待ちます)";
                    btn.style.backgroundColor = "#2E7D32";
                    status.innerText = "「Uhh...」「Um...」と考えながら話して大丈夫です";
                    monitorVolume(dataArray, bufferLength);
                };

                recognition.onresult = (event) => {
                    let currentText = '';
                    for (let i = 0; i < event.results.length; i++) {
                        currentText += event.results[i][0].transcript + ' ';
                    }
                    
                    const doc = window.parent.document;
                    const chatInput = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
                    if (chatInput && currentText.trim() !== '') {
                        hasSaidSomething = true;
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                        nativeInputValueSetter.call(chatInput, currentText.trim());
                        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                        status.innerText = '認識中: "' + currentText.trim() + '"';
                    }
                };

                recognition.onerror = (event) => {
                    resetButtonUI("⚠️ マイクエラー (" + event.error + ")。もう一度試してください。");
                };

                recognition.start();

            } catch(e) {
                resetButtonUI("⚠️ マイクアクセスの許可が必要です。");
            }
        };

        function monitorVolume(dataArray, bufferLength) {
            if (!isListening) return;

            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            let avgVolume = sum / bufferLength;

            if (avgVolume > 12) {
                if (sendTimer) {
                    clearTimeout(sendTimer);
                    sendTimer = null;
                }
                btn.innerText = "🔴 声（音）を検知中... (話している間は待ちます)";
                btn.style.backgroundColor = "#2E7D32";
            } else {
                if (hasSaidSomething && !sendTimer) {
                    btn.innerText = "⏸️ 無音を検知: 2秒後に自動送信";
                    btn.style.backgroundColor = "#FFA000";
                    sendTimer = setTimeout(() => {
                        stopAndSendNow();
                    }, 2000);
                }
            }

            animFrameId = requestAnimationFrame(() => monitorVolume(dataArray, bufferLength));
        }

        function stopAndSendNow() {
            if (recognition) { try { recognition.stop(); } catch(e) {} }

            const doc = window.parent.document;
            const chatInput = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            
            if (chatInput && chatInput.value.trim() !== "") {
                const enterEvent = new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13
                });
                chatInput.dispatchEvent(enterEvent);
                resetButtonUI("送信完了！AIの返答を待っています...");
            } else {
                resetButtonUI("音声が検出されませんでした。もう一度試してください。");
            }
        }

    } else {
        btn.disabled = true;
        btn.innerText = "⚠️ お使いのブラウザは音声入力非対応です";
        status.innerText = "Google Chromeをご利用ください";
    }
</script>
"""
components.html(stt_html, height=110)

# 9. ユーザー入力エリア
user_input = st.chat_input("英語でメッセージを入力（または上のボタンで音声入力）...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(user_input)
            
            # 「もう一度聴く」ボタンを表示
            render_audio_button(response.text)

            # テキストは折りたたんで隠す
            with st.expander("👁️ テキストを表示して確認する", expanded=False):
                st.markdown(response.text)

            st.session_state.messages.append({"role": "assistant", "content": response.text})

            # 返答直後の自動音声発話
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
