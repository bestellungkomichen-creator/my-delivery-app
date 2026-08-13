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
        # 更新：使用最新的 use_container_width 參數
        st.image(image, caption="你上傳的包裹照片", use_container_width=True)

        # 點擊按鈕開始辨識
        if st.button("🚀 開始自動提取資料"):
            with st.spinner("AI 正在努力辨識圖片中，請稍候..."):
                try:
                    # 使用 Gemini 1.5 Flash 模型 (速度快、支援圖片)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 給 AI 的指令 (因為啟用了 JSON 模式，指令可以更簡潔)
                    prompt = """
                    請從這張物流標籤圖片中提取以下資訊，並回傳指定的 JSON 格式：
                    {
                        "郵寄公司": "例如 DHL, Hermes",
                        "追蹤碼": "物流單號",
                        "寄貨人": "寄件人的姓名 (Von)",
                        "寄貨地址": "寄件人的完整地址 (包含街道、郵遞區號、城市與國家)"
                    }
                    如果圖片中找不到某項資訊，請填寫 "未找到"。
                    """
                    
                    # 更新：呼叫 AI 進行辨識，並透過設定強制要求回傳標準 JSON 格式
                    response = model.generate_content(
                        [prompt, image],
                        generation_config={"response_mime_type": "application/json"}
                    )
                    
                    # AI 現在保證會回傳純 JSON 格式，可直接解析
                    data = json.loads(response.text)
                    
                    st.success("✅ 辨識完成！")
                    
                    # 顯示成表格，方便使用者直接複製
                    df = pd.DataFrame([data])
                    
                    # 重新排列欄位，符合你的 Google Sheets 順序習慣
                    df = df[['郵寄公司', '追蹤碼', '寄貨人', '寄貨地址']]
                    
                    st.dataframe(df, use_container_width=True)
                    
                    st.info("💡 提示：你可以直接選取上方的表格內容，按 Ctrl+C 複製，然後直接到 Google Sheets 貼上 (Ctrl+V) 即可！")
                    
                except json.JSONDecodeError:
                    st.error("❌ 解析失敗：AI 回傳的格式不正確，請再試一次。")
                except Exception as e:
                    st.error(f"❌ 發生錯誤，請確認圖片是否清晰，或檢查 API 狀態。錯誤訊息: {e}")
else:
    st.warning("請先在上方輸入你的 Gemini API Key 才能開始使用喔！")
