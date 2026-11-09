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

# เชื่อมต่อ Google Sheets และเลือกแท็บ borrowings
try:
    client = init_connection()
    # ** หมายเหตุ: เปลี่ยนชื่อ 'equipment_db' ให้ตรงกับชื่อไฟล์ Google Sheets ของคุณจริง **
    spreadsheet = client.open("equipment_db")
    sheet_borrowings = spreadsheet.worksheet("borrowings") 
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อกับ Google Sheets ได้: {e}")

# --- ส่วนติดต่อผู้ใช้งาน (UI) ---
st.title("📦 ระบบยืม-คืนอุปกรณ์")

# เมนูย่อยสำหรับเลือกการใช้งาน
menu = st.radio("เลือกการใช้งาน", ["บันทึกการยืมอุปกรณ์", "ดูประวัติและรายการยืมทั้งหมด"], horizontal=True)
st.divider()

if menu == "บันทึกการยืมอุปกรณ์":
    st.subheader("📝 ฟอร์มบันทึกข้อมูลการยืม")
    
    with st.form("loan_form", clear_on_submit=True):
        st.info("กรุณากรอกข้อมูลให้ครบถ้วนเพื่อบันทึกการยืม")
        
        eq_id = st.text_input("รหัสอุปกรณ์ (eq_id)")
        borrower_name = st.text_input("ชื่อ-นามสกุล ผู้ยืม (borrower_name)")
        phone = st.text_input("เบอร์โทรศัพท์ (phone)")
        address = st.text_area("ที่อยู่ (address)")
        
        submitted = st.form_submit_button("ยืนยันการยืมอุปกรณ์")
        
        if submitted:
            if borrower_name.strip() == "" or eq_id.strip() == "":
                st.warning("⚠️ กรุณากรอก 'รหัสอุปกรณ์' และ 'ชื่อผู้ยืม' ให้ครบถ้วนครับ")
            else:
                try:
                    # สร้าง id อัตโนมัติจากตัวเลขเวลาปัจจุบัน
                    new_id = int(datetime.now().timestamp())
                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # เรียงข้อมูลให้ตรงกับคอลัมน์ในชีต borrowings: 
                    # A:id, B:eq_id, C:borrower_name, D:phone, E:borrow_date, F:return_date, G:status, H:address
                    row_data = [
                        new_id,             # A: id
                        eq_id,              # B: eq_id
                        borrower_name,      # C: borrower_name
                        phone,              # D: phone
                        current_date,       # E: borrow_date
                        "",                 # F: return_date (ยังไม่คืน ปล่อยว่างไว้)
                        "กำลังยืม",          # G: status
                        address             # H: address
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
