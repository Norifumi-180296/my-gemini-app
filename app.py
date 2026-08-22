import os
import time
from datetime import datetime
import google.generativeai as genai
import requests
import streamlit as st

# ページ設定
st.set_page_config(
    page_title="Gemini 動画動作解析アプリ", layout="centered"
)
st.title("📹 Gemini 動画動作・時間解析アプリ")

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

st.write("【使い方】下の「Record video」で動画を撮影して送信してください。")

# 1. ブラウザのカメラで動画を録画（または録画済み動画をアップロード）
video_file = st.file_uploader(
    "カメラで録画（スマホ/PCのカメラ起動）、または動画ファイルを選択",
    type=["mp4", "mov", "avi", "webm"],
)

if video_file is not None:
    # 画面に録画した動画を表示して確認
    st.video(video_file)

    if st.button("この動画の『動作と時間』をGeminiで解析する", type="primary"):
        with st.spinner("Geminiが動画を読み込み・解析中... お待ちください"):
            # 一時ファイルとして動画を保存
            temp_filename = "captured_video.mp4"
            with open(temp_filename, "wb") as f:
                f.write(video_file.getbuffer())

            try:
                # Gemini File APIへアップロード
                uploaded_file = genai.upload_file(path=temp_filename)

                # 処理完了まで待機
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)

                # 動作と経過時間に特化したプロンプト指示
                prompt = """
                この動画を詳細に分析し、以下の形式でレポートしてください：

                1. 【全体の要約】
                   動画全体でどのような動作が行われたか簡潔にまとめてください。

                2. 【時系列の動作解析】
                   動画の開始から終了までの動きを、何秒時点でどういう動作（作業や身振りなど）を行っているか秒数ごとにタイムラインで詳しく解説してください。
                   (例: 0秒〜2秒: 手を挙げて挨拶、2秒〜5秒: 画面に向かって歩く、など)

                3. 【動作の特徴・補足】
                   動作のスピード、スムーズさ、特徴的な点があれば教えてください。
                """

                # 動画の分析を実行
                response = model.generate_content([prompt, uploaded_file])

                analysis_text = response.text
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                st.success("解析が完了しました！")
                st.subheader("【分析結果（動作・時間）】")
                st.write(analysis_text)

                # GAS (スプレッドシート) へ送信
                payload = {"date": current_time, "text": analysis_text}
                res = requests.post(GAS_URL, json=payload)

                if res.status_code == 200:
                    st.toast(
                        "スプレッドシートへの記録に成功しました！", icon="✅"
                    )
                else:
                    st.error(f"スプレッドシート送信失敗 (Status: {res.status_code})")

                # サーバー上の一時ファイルを削除
                genai.delete_file(uploaded_file.name)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
