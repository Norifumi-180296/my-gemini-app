import os
import time
from datetime import datetime
import google.generativeai as genai
import requests
import streamlit as st

# ページ設定
st.set_page_config(page_title="Gemini 動作解析アプリ", layout="centered")
st.title("📹 Gemini リアルタイム動作解析アプリ")

# APIキーの読み込み
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error(
        "Gemini APIキーが設定されていません。StreamlitのSecretsを設定してください。"
    )
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

GAS_URL = "https://script.google.com/macros/s/AKfycbx7C4RBJp0wqQDVYTZ5VJ8PC4O-DFg47juiajov8aUz95kGZulEQq4dBohbatP1akLWFA/exec"

st.write("【使い方】下の「Take Photo / 録画」で映像を撮影してください。")

# 画面上でカメラを起動するコンポーネント
camera_image = st.camera_input("カメラ映像")

if camera_image is not None:
    if st.button("この画像をGeminiで解析する", type="primary"):
        with st.spinner("Geminiが解析中... お待ちください"):
            # 一時ファイルとして保存
            temp_filename = "captured_image.jpg"
            with open(temp_filename, "wb") as f:
                f.write(camera_image.getbuffer())

            try:
                # Geminiへ画像をアップロードして分析
                uploaded_file = genai.upload_file(path=temp_filename)

                response = model.generate_content([
                    "この画像に映っている出来事や状態を詳しく分析して教えてください。",
                    uploaded_file,
                ])

                analysis_text = response.text
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

                # 一時ファイル削除
                genai.delete_file(uploaded_file.name)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
