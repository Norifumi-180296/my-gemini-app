import os
import time
from datetime import datetime
import google.generativeai as genai
import requests
import streamlit as st

# ページ設定
st.set_page_config(page_title="Gemini 動作タイムライン解析", layout="centered")
st.title("📹 Gemini リアルタイム動画動作解析")

# APIキーの読み込み
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error(
        "Gemini APIキーが設定されていません。StreamlitのSecretsを設定してください。"
    )
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

GAS_URL = "https://script.google.com/macros/s/AKfycbx7C4RBJp0wqQDVYTZ5VJ8PC4O-DFg47juiajov8aUz95kGZulEQq4dBohbatP1akLWFA/exec"

st.write("### 1. 下のカメラで「録画開始」を押して動作を撮影してください")

# HTML5 WebRTC カメラ録画コンポーネント（ブラウザ直接録画）
html_code = """
<div style="text-align: center; font-family: sans-serif;">
    <video id="preview" width="100%" height="auto" autoplay playsinline muted style="max-width: 500px; background: #000; border-radius: 8px;"></video><br><br>
    <button id="startBtn" onclick="startRecording()" style="padding: 10px 20px; font-size: 16px; background-color: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;">🔴 録画開始</button>
    <button id="stopBtn" onclick="stopRecording()" disabled style="padding: 10px 20px; font-size: 16px; background-color: #555; color: white; border: none; border-radius: 5px; cursor: pointer;">⬛ 録画停止</button>
    <br><br>
    <video id="recorded" width="100%" height="auto" controls style="max-width: 500px; display: none; border-radius: 8px;"></video>
    <br>
    <a id="downloadLink" style="display:none; margin-top: 10px; font-weight: bold; color: #1f77b4; font-size: 16px;">💾 録画された動画をダウンロードして下の枠に移動</a>
</div>

<script>
let mediaRecorder;
let recordedChunks = [];
const preview = document.getElementById('preview');
const recorded = document.getElementById('recorded');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const downloadLink = document.getElementById('downloadLink');

navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
        preview.srcObject = stream;
        window.stream = stream;
    })
    .catch(err => {
        alert("カメラの起動に失敗しました。ブラウザのカメラ使用許可を確認してください: " + err);
    });

function startRecording() {
    recordedChunks = [];
    const options = { mimeType: 'video/webm' };
    try {
        mediaRecorder = new MediaRecorder(window.stream, options);
    } catch (e) {
        mediaRecorder = new MediaRecorder(window.stream);
    }
    mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) recordedChunks.push(event.data);
    };
    mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        recorded.src = url;
        recorded.style.display = 'block';
        
        downloadLink.href = url;
        downloadLink.download = 'recorded_video.webm';
        downloadLink.style.display = 'inline-block';
        downloadLink.innerText = "💾 録画動画を保存（クリックしてダウンロード）";
    };
    mediaRecorder.start();
    startBtn.disabled = true;
    startBtn.style.backgroundColor = '#ccc';
    stopBtn.disabled = false;
    stopBtn.style.backgroundColor = '#333';
}

function stopRecording() {
    mediaRecorder.stop();
    startBtn.disabled = false;
    startBtn.style.backgroundColor = '#ff4b4b';
    stopBtn.disabled = true;
    stopBtn.style.backgroundColor = '#555';
}
</script>
"""

st.components.v1.html(html_code, height=520)

st.write("---")
st.write("### 2. 撮影後に「録画動画を保存」をクリックし、ダウンロードした動画をここにセットしてください")

uploaded_file = st.file_uploader(
    "録画した動画を選択", type=["webm", "mp4", "mov", "avi"]
)

if uploaded_file is not None:
    st.video(uploaded_file)

    if st.button("この動画の『動作と時間』をGeminiで解析する", type="primary"):
        with st.spinner("Geminiが動画を読み込み・解析中..."):
            temp_filename = "captured_video.webm"
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                uploaded_gemini = genai.upload_file(path=temp_filename)

                while uploaded_gemini.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_gemini = genai.get_file(uploaded_gemini.name)

                prompt = """
                この動画を詳細に分析し、以下の形式でレポートしてください：

                1. 【全体の要約】
                   動画全体でどのような動作・作業が行われたか簡潔にまとめてください。

                2. 【時系列の動作解析】
                   動画の開始から終了までの動きを、何秒時点でどういう動作を行っているか秒数ごとにタイムラインで詳しく解説してください。
                   (例: 0秒〜2秒: 手を挙げて挨拶、2秒〜5秒: 画面に向かって歩く、など)

                3. 【動作の特徴・補足】
                   動作のスピード、スムーズさ、特徴的な点があれば教えてください。
                """

                response = model.generate_content([prompt, uploaded_gemini])

                analysis_text = response.text
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                st.success("解析が完了しました！")
                st.subheader("【分析結果（動作・時間）】")
                st.write(analysis_text)

                # GAS (スプレッドシート) へ送信
                payload = {"date": current_time, "text": analysis_text}
                res = requests.post(GAS_URL, json=payload)

                if res.status_code == 200:
                    st.toast("スプレッドシートへ記録しました！", icon="✅")
                else:
                    st.error(f"スプレッドシート送信失敗 (Status: {res.status_code})")

                genai.delete_file(uploaded_gemini.name)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
