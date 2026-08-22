import os
import time
from datetime import datetime
import google.generativeai as genai
import requests
import streamlit as st

# 1. ページ設定
st.set_page_config(page_title="動作解析アプリ", layout="centered")
st.title("📹 Gemini 動作解析アプリ")

# 2. APIキーの設定（Secretから安全に取得）
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error(
        "Gemini APIキーが設定されていません。StreamlitのSecretsに設定してください。"
    )
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

GAS_URL = "https://script.google.com/macros/s/AKfycbx7C4RBJp0wqQDVYTZ5VJ8PC4O-DFg47juiajov8aUz95kGZulEQq4dBohbatP1akLWFA/exec"

st.write("カメラで動画を録画するか、動画ファイルをアップロードしてください。")

# 3. ブラウザから動画を入力
video_file = st.file_uploader(
    "動画ファイルを選択（またはカメラで録画）",
    type=["mp4", "mov", "avi", "webm"],
)

if video_file is not None:
    # 画面に動画を表示
    st.video(video_file)

    if st.button("この動画をGeminiで解析する", type="primary"):
        with st.spinner("Geminiが動画を解析中... お待ちください"):
            # 一時ファイルとして保存
            temp_filename = "temp_video.mp4"
            with open(temp_filename, "wb") as f:
                f.write(video_file.read())

            try:
                # Geminiへアップロード＆解析
                uploaded_file = genai.upload_file(path=temp_filename)

                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)

                response = model.generate_content([
                    (
                        "この動画に映っている動きや出来事を詳しく分析して教えてください。"
                    ),
                    uploaded_file,
                ])

                analysis_text = response.text
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 結果表示
                st.success("解析が完了しました！")
                st.subheader("【分析結果】")
                st.write(analysis_text)

                # GASへ送信
                payload = {"date": current_time, "text": analysis_text}
                res = requests.post(GAS_URL, json=payload)

                if res.status_code == 200:
                    st.toast(
                        "スプレッドシートへの記録に成功しました！", icon="✅"
                    )
                else:
                    st.error(f"スプレッドシート送信失敗 (Status: {res.status_code})")

                # サーバー上の一次ファイルを削除
                genai.delete_file(uploaded_file.name)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
