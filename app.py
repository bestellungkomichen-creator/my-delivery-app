import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd

# 網頁標題與設定
st.set_page_config(page_title="📦 寄貨單自動辨識工具", layout="centered")
st.title("📦 寄貨單自動辨識工具")
st.write("只要把包裹標籤的照片拖曳到下方，AI 就會自動幫你把資料整理成表格！")

# 讓使用者輸入 API Key
api_key = st.text_input("請輸入你的 Gemini API Key (只需輸入一次):", type="password")

if api_key:
    # 設定 Gemini API
    genai.configure(api_key=api_key)
    
    # 照片上傳區塊
    uploaded_file = st.file_uploader("拖曳或點擊上傳包裹照片 (支援 JPG, PNG)", type=['jpg', 'jpeg', 'png'])

    if uploaded_file is not None:
        # 顯示上傳的照片
        image = Image.open(uploaded_file)
        st.image(image, caption="你上傳的包裹照片", use_container_width=True)

        # 點擊按鈕開始辨識
        if st.button("🚀 開始自動提取資料"):
            with st.spinner("系統正在自動尋找可用的 AI 模型並辨識圖片中，請稍候..."):
                try:
                    # 1. 自動偵測你的 API Key 到底有權限使用哪些模型
                    available_models = [m.name for m in genai.list_models()]
                    
                    target_model = None
                    # 依序往下找，只要有其中一個就抓來用
                    if 'models/gemini-1.5-flash' in available_models:
                        target_model = 'gemini-1.5-flash'
                    elif 'models/gemini-1.5-pro' in available_models:
                        target_model = 'gemini-1.5-pro'
                    elif 'models/gemini-pro-vision' in available_models:
                        target_model = 'gemini-pro-vision'
                    
                    # 如果連舊版模型都沒有權限
                    if target_model is None:
                        st.error(f"❌ 你的 API Key 完全沒有圖片辨識的權限。你的鑰匙目前只能存取: {available_models}")
                    else:
                        # 2. 啟動偵測到的可用模型
                        model = genai.GenerativeModel(target_model)
                        
                        # 給 AI 的指令
                        prompt = """
                        請幫我從這張物流標籤圖片中提取以下資訊，並嚴格以 JSON 格式回傳，不要包含任何 markdown 標記（如 ```json 等）：
                        {
                            "郵寄公司": "例如 DHL, Hermes",
                            "追蹤碼": "物流單號",
                            "寄貨人": "寄件人的姓名 (Von)",
                            "寄貨地址": "寄件人的完整地址 (包含街道、郵遞區號、城市與國家)"
                        }
                        如果圖片中找不到某項資訊，請填寫 "未找到"。
                        """
                        
                        # 呼叫 AI
                        response = model.generate_content([prompt, image])
                        
                        # 3. 手動清理文字格式 (為了相容舊版模型)
                        text = response.text.strip()
                        if text.startswith("```json"):
                            text = text[7:]
                        elif text.startswith("```"):
                            text = text[3:]
                        if text.endswith("```"):
                            text = text[:-3]
                            
                        data = json.loads(text.strip())
                        
                        st.success(f"✅ 辨識完成！(系統自動為你挑選了 {target_model} 模型)")
                        
                        # 顯示成表格
                        df = pd.DataFrame([data])
                        if all(col in df.columns for col in ['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址']):
                            df = df[['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址']]
                        
                        st.dataframe(df, use_container_width=True)
                        st.info("💡 提示：你可以直接選取上方的表格內容，按 Ctrl+C 複製，然後直接到 Google Sheets 貼上 (Ctrl+V) 即可！")
                        
                except Exception as e:
                    st.error(f"❌ 發生未知的錯誤，請截圖這段文字：{e}")
else:
    st.warning("請先在上方輸入你的 Gemini API Key 才能開始使用喔！")
