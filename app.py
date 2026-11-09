import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบยืม-คืนอุปกรณ์", page_icon="📦", layout="centered")

# --- ฟังก์ชันเชื่อมต่อ Google Sheets ---
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
    client = gspread.authorize(creds)
    return client

# เชื่อมต่อ Google Sheets และเลือกแท็บต่างๆ
try:
    client = init_connection()
    spreadsheet = client.open("equipment_db")
    sheet_borrowings = spreadsheet.worksheet("borrowings") 
    sheet_equipments = spreadsheet.worksheet("equipments") 
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อกับ Google Sheets ได้: {e}")

# --- ส่วนติดต่อผู้ใช้งาน (UI) ---
st.title("📦 ระบบยืม-คืนอุปกรณ์")

# เมนูย่อยสำหรับเลือกการใช้งาน
menu = st.radio("เลือกการใช้งาน", ["บันทึกการยืมอุปกรณ์", "ดูประวัติและรายการยืมทั้งหมด"], horizontal=True)
st.divider()

if menu == "บันทึกการยืมอุปกรณ์":
    st.subheader("📝 บันทึกการยืมกายอุปกรณ์")
    
    # ดึงข้อมูลอุปกรณ์จากแท็บ equipments มาทำตัวเลือก
    try:
        eq_data = sheet_equipments.get_all_records()
        if eq_data:
            df_eq = pd.DataFrame(eq_data)
            # สมมติให้คอลัมน์แรกหรือคอลัมน์ชื่อ eq_id / name เป็นตัวเลือก
            eq_options = [f"{row.get('eq_id', '')} - {row.get('name', '')}" for index, row in df_eq.iterrows()]
        else:
            eq_options = ["ไม่พบรายการอุปกรณ์ในระบบ"]
    except Exception:
        eq_options = ["โหลดข้อมูลอุปกรณ์ไม่สำเร็จ"]

    with st.form("loan_form", clear_on_submit=True):
        
        selected_eq = st.selectbox("เลือกกายอุปกรณ์ที่ต้องการยืม", eq_options)
        borrower_name = st.text_input("ชื่อ-นามสกุล ผู้ยืม")
        phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
        
        # เพิ่มช่องกรอกที่อยู่ตรงนี้ครับ
        address = st.text_area("ที่อยู่สำหรับการติดต่อ (address)")
        
        borrow_date = st.date_input("วันที่ยืม", value=datetime.now())
        
        submitted = st.form_submit_button("ยืนยันการยืม")
        
        if submitted:
            if borrower_name.strip() == "" or address.strip() == "":
                st.warning("⚠️ กรุณากรอก 'ชื่อ-นามสกุล' และ 'ที่อยู่' ให้ครบถ้วนครับ")
            else:
                try:
                    # ดึงรหัสอุปกรณ์จากข้อความที่เลือก (เช่น "EQ001 - เตียงผู้ป่วย" จะดึงคำว่า EQ001 ออกมา)
                    eq_id = selected_eq.split(" - ")[0] if " - " in selected_eq else selected_eq
                    
                    new_id = int(datetime.now().timestamp())
                    formatted_borrow_date = borrow_date.strftime("%Y-%m-%d")
                    
                    # เรียงข้อมูลให้ตรงกับคอลัมน์ในชีต borrowings: 
                    # A:id, B:eq_id, C:borrower_name, D:phone, E:borrow_date, F:return_date, G:status, H:address
                    row_data = [
                        new_id,                 # A: id
                        eq_id,                  # B: eq_id
                        borrower_name,          # C: borrower_name
                        phone,                  # D: phone
                        formatted_borrow_date,  # E: borrow_date
                        "",                     # F: return_date (ว่างไว้ก่อน)
                        "กำลังยืม",              # G: status
                        address                 # H: address (ที่อยู่)
                    ]
                    
                    # บันทึกข้อมูลลง Google Sheets
                    sheet_borrowings.append_row(row_data)
                    
                    st.success("✅ บันทึกข้อมูลการยืมและที่อยู่สำเร็จเรียบร้อยครับ!")
                    
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

elif menu == "ดูประวัติและรายการยืมทั้งหมด":
    st.subheader("📋 รายการข้อมูลการยืมทั้งหมดในระบบ")
    
    if st.button("🔄 รีเฟรชข้อมูล"):
        st.rerun()
        
    try:
        data = sheet_borrowings.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการยืมในระบบ")
    except Exception as e:
        st.warning(f"ยังไม่สามารถดึงข้อมูลมาแสดงได้: {e}")
