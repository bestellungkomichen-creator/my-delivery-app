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
    
    # 圖片壓縮，加速傳輸與辨識
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
                # 優先選擇輕量版模型 (Lite / 8b)，因為它們的免費額度比標準版高非常多！
                preferred_models = [
                    'models/gemini-1.5-flash-8b',
                    'models/gemini-3.5-flash-lite',
                    'models/gemini-flash-lite-latest',
                    'models/gemini-3.5-flash',
                    'models/gemini-1.5-flash'
                ]
                
                for pm in preferred_models:
                    if pm in available_models:
                        target_model = pm.replace("models/", "")
                        break
                        
                if target_model is None:
                    # 硬抓清單裡第一個名字有 flash 且不是 preview 的
                    for m in available_models:
                        if 'flash' in m and 'preview' not in m and 'tts' not in m:
                            target_model = m.replace("models/", "")
                            break
                            
                if target_model is None:
                     st.error("❌ 找不到合適的圖片辨識模型，請確認 API 狀態。")
                else:
                    model = genai.GenerativeModel(target_model)
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
                    
                    # 清理 AI 回傳的字串格式
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    elif text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                        
                    data = json.loads(text.strip())
                    
                    tracking_val = str(data.get("追蹤碼", "")).strip()
                    company_val = str(data.get("郵寄公司", "")).strip()
                    
                    # 檢查無效資料的函數
                    def is_invalid(val):
                        return val == "" or "未找到" in val or val.lower() in ["none", "null", "not found"]

                    # 【終極防呆機制】包裹不可能沒有追蹤碼和郵寄公司！
                    if is_invalid(tracking_val) and is_invalid(company_val):
                        st.warning("⚠️ 這張圖片找不到有效的「追蹤碼」與「郵寄公司」，系統判定這不是一張包裹標籤！(已自動攔截，不會寫入表格)")
                    else:
                        new_row = pd.DataFrame([data])
                        new_row = new_row[['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址']]
                        st.session_state.scanned_data = pd.concat([st.session_state.scanned_data, new_row], ignore_index=True)
                        
                        if webhook_url:
                            res = requests.post(webhook_url, json=data, allow_redirects=True)
                            if res.status_code in [200, 201, 302]:
                                st.success(f"✅ 辨識成功！(使用模型: {target_model}) 資料已同步寫入你的 Google 表格！")
                            else:
                                st.warning(f"✅ 辨識成功，但寫入 Google 表格失敗 (代碼 {res.status_code})。")
                        else:
                            st.success(f"✅ 辨識成功！(使用模型: {target_model}，尚未設定 Google Sheets 同步)")
                            
            except Exception as e:
                error_msg = str(e)
                # 攔截 Quota 錯誤並給予中文提示
                if "429" in error_msg or "quota" in error_msg.lower():
                    st.error("❌ 錯誤：你剛剛操作太快，或是今天的免費額度已經用盡了！請等待 1 分鐘後再試一次。")
                else:
                    st.error(f"❌ 發生未知的錯誤：{e}")

# ==========================================
# 下方區塊：顯示累積的資料庫
# ==========================================
st.divider() 
st.subheader("📂 網頁暫存紀錄 (可作為備份)")

if not st.session_state.scanned_data.empty:
    st.dataframe(st.session_state.scanned_data, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        csv_data = st.session_state.scanned_data.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下載成 CSV 檔案 (備份用)",
            data=csv_data,
            file_name="包裹資料備份.csv",
            mime="text/csv"
        )
    with col2:
        if st.button("🗑️ 清空網頁畫面紀錄"):
            st.session_state.scanned_data = pd.DataFrame(columns=['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址'])
            st.rerun()
else:
    st.info("目前還沒有資料，請在上方上傳照片並開始辨識！")
