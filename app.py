from datetime import date
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(
    page_title="ระบบยืม-คืน กายอุปกรณ์ (Google Sheets)",
    page_icon="🏥",
    layout="wide",
)

# --- 1. ตั้งค่าการเชื่อมต่อ Google Sheets API (รองรับทั้งแบบออนไลน์และในเครื่อง) ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def connect_gsheets():
  try:
    # เช็คว่ารันบน Streamlit Cloud (อ่านจาก Secrets) หรือรันในเครื่อง (อ่านจากไฟล์)
    if "gcp_service_account" in st.secrets:
      creds_dict = dict(st.secrets["gcp_service_account"])
      creds = ServiceAccountCredentials.from_json_keyfile_dict(
          creds_dict, scope
      )
    else:
      creds = ServiceAccountCredentials.from_json_keyfile_name(
          "credentials.json", scope
      )

    client = gspread.authorize(creds)
    sheet = client.open("equipment_db")
    return sheet
  except Exception as e:
    st.error(
        f"ไม่สามารถเชื่อมต่อ Google Sheets ได้ กรุณาตรวจสอบการตั้งค่า Secrets"
        f" หรือไฟล์ credentials.json: {e}"
    )
    return None


sheet = connect_gsheets()
