import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
import requests

# 網頁標題與設定
st.set_page_config(page_title="📦 寄貨單自動辨識工具 (雲端同步版)", layout="centered")
st.title("📦 寄貨單自動辨識工具 ⚡")
st.write("只要把包裹標籤的照片拖曳到下方，AI 就會自動提取資料並【即時同步至 Google Sheets】！")

# 初始化暫存資料庫
if 'scanned_data' not in st.session_state:
    st.session_state.scanned_data = pd.DataFrame(columns=['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址'])

# 自動尋找 API Key 與 Google Sheets 通道
api_key = st.secrets.get("GEMINI_API_KEY", "")
webhook_url = st.secrets.get("GSHEET_WEBHOOK_URL", "")

if not api_key:
    api_key = st.text_input("請輸入你的 Gemini API Key:", type="password")
    if not api_key:
        st.warning("請先設定或輸入 Gemini API Key 才能開始使用喔！")
        st.stop() 

genai.configure(api_key=api_key)

# 照片上傳區塊
uploaded_file = st.file_uploader("拖曳或點擊上傳包裹照片 (按右上角 X 移除舊照片)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    max_size = 1024
    if max(image.size) > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    st.image(image, caption="準備辨識的照片", use_container_width=True)

    if st.button("🚀 開始自動提取資料"):
        with st.spinner("⚡ 圖片已壓縮，AI 正在極速辨識並同步中..."):
            try:
                available_models = [m.name for m in genai.list_models()]
                target_model = None
                
                # 【防 Quota 限制的關鍵更新】
                # 優先選擇 "Lite" 輕量版模型，因為它們的免費額度比標準版高非常多！
                preferred_models = [
                    'models/gemini-3.5-flash-lite', 
                    'models/gemini-3.1-flash-lite',
                    'models/gemini-flash-lite-latest',
                    'models/gemini-3.5-flash' # 如果 Lite 真的不能用，才退回標準版
                ]
                
                for pm in preferred_models:
                    if pm in available_models:
                        target_model = pm.replace("models/", "")
                        break
                        
                if target_model is None:
                    # 如果清單裡都沒配對到，硬抓一個帶有 flash-lite 的
                    for m in available_models:
                        if 'flash-lite' in m and 'preview' not in m:
                            target_model = m.replace("models/", "")
                            break
                            
                if target_model is None:
                     st.error("❌ 找不到合適的輕量版圖片辨識模型，請確認 API 狀態。")
                else:
                    model = genai.GenerativeModel(target_model)
                    prompt = """
                    請幫我從這張物流標籤圖片中提取以下資訊，並嚴格以 JSON 格式回傳，不要包含任何 markdown 標記（如 
```json 等）：
                    {
                        "郵寄公司": "例如 DHL, Hermes",
                        "追蹤碼": "物流單號",
                        "寄貨人": "寄件人的姓名 (Von)",
                        "寄貨地址": "寄件人的完整地址 (包含街道、郵遞區號、城市與國家)"
                    }
                    如果圖片中找不到某項資訊，請填寫 "未找到"。
                    """
                    response = model.generate_content([prompt, image])
                    
                    text = response.text.strip()
                    if text.startswith("
http://googleusercontent.com/immersive_entry_chip/0

請將這段程式碼貼到 GitHub 並 Commit。這一次，系統會優先選用額度極高的 `gemini-3.5-flash-lite` 模型，這樣就不會再輕易跳出 `429 Quota Exceeded` 的錯誤了！如果還有遇到問題，隨時告訴我！
