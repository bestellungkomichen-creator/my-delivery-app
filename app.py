import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd

# 網頁標題與設定
st.set_page_config(page_title="📦 寄貨單自動辨識工具", layout="centered")
st.title("📦 寄貨單自動辨識工具")
st.write("只要把包裹標籤的照片拖曳到下方，AI 就會自動提取資料並【累積成大表格】！")

# 初始化暫存資料庫
if 'scanned_data' not in st.session_state:
    st.session_state.scanned_data = pd.DataFrame(columns=['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址'])

# ==========================================
# 【關鍵更新】自動尋找 API Key
# ==========================================
api_key = ""
# 1. 先偷偷去 Streamlit 保險箱找鑰匙
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

# 2. 如果保險箱沒鑰匙，才顯示輸入框給使用者填
if not api_key:
    api_key = st.text_input("請輸入你的 Gemini API Key:", type="password")
    if not api_key:
        st.warning("請先設定或輸入 Gemini API Key 才能開始使用喔！")
        st.stop() # 暫停執行，等有鑰匙再繼續

# 3. 拿到鑰匙了，啟動 AI！
genai.configure(api_key=api_key)

# 照片上傳區塊
uploaded_file = st.file_uploader("拖曳或點擊上傳包裹照片 (上傳新照片前，可按右上角 X 移除舊照片)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # 顯示上傳的照片
    image = Image.open(uploaded_file)
    st.image(image, caption="準備辨識的包裹照片", use_container_width=True)

    # 點擊按鈕開始辨識
    if st.button("🚀 開始自動提取資料"):
        with st.spinner("系統正在辨識圖片中，請稍候..."):
            try:
                # 抓取可用模型
                available_models = [m.name for m in genai.list_models()]
                target_model = None
                preferred_models = ['models/gemini-3.5-flash', 'models/gemini-flash-latest']
                
                for pm in preferred_models:
                    if pm in available_models:
                        target_model = pm.replace("models/", "")
                        break
                if target_model is None:
                    for m in available_models:
                        if 'flash' in m and 'preview' not in m and 'tts' not in m and '2.5' not in m:
                            target_model = m.replace("models/", "")
                            break
                            
                if target_model is None:
                     st.error(f"❌ 找不到合適的圖片辨識模型，請確認 API 狀態。")
                else:
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
                    
                    response = model.generate_content([prompt, image])
                    
                    # 處理 JSON 格式
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    elif text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                        
                    data = json.loads(text.strip())
                    
                    # 將新辨識出的資料加入我們的 DataFrame
                    new_row = pd.DataFrame([data])
                    new_row = new_row[['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址']]
                    
                    # 將新資料接在舊資料的下面
                    st.session_state.scanned_data = pd.concat([st.session_state.scanned_data, new_row], ignore_index=True)
                    
                    st.success(f"✅ 辨識成功！已自動加入下方表格。")
                    
            except Exception as e:
                st.error(f"❌ 發生未知的錯誤：{e}")

# ==========================================
# 下方區塊：顯示累積的資料庫
# ==========================================
st.divider()  # 畫一條分隔線
st.subheader("📂 目前累積的包裹資料")

# 檢查有沒有資料
if not st.session_state.scanned_data.empty:
    st.dataframe(st.session_state.scanned_data, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        csv_data = st.session_state.scanned_data.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下載成 CSV 檔案 (可直接用 Excel 開啟)",
            data=csv_data,
            file_name="包裹資料累積.csv",
            mime="text/csv",
        )
    with col2:
        if st.button("🗑️ 清空表格 (準備處理下一批)"):
            st.session_state.scanned_data = pd.DataFrame(columns=['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址'])
            st.rerun()
            
    st.info("💡 【提示】直接點擊上方照片右上角的『X』移除舊照片，丟下一張新照片進來辨識，資料就會自動累積！")
else:
    st.info("目前還沒有資料，請在上方上傳照片並開始辨識！")
