from base64 import b64decode, b64encode
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

# --- 1. ตั้งค่าการเชื่อมต่อ Google Sheets API ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def connect_gsheets():
  try:
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
    st.error(f"รายละเอียดข้อผิดพลาดในการเชื่อมต่อ: {e}")
    return None


sheet = connect_gsheets()


# --- ฟังก์ชันดึงข้อมูลแปลงเป็น DataFrame ---
def get_data(worksheet_name):
  if sheet is None:
    return pd.DataFrame()
  ws = sheet.worksheet(worksheet_name)
  data = ws.get_all_records()
  return pd.DataFrame(data)


# --- ฟังก์ชันเพิ่มข้อมูลลง Google Sheets ---
def add_row(worksheet_name, row_data):
  ws = sheet.worksheet(worksheet_name)
  ws.append_row(row_data)


# --- ฟังก์ชันอัปเดตสถานะ ---
def update_row_status(worksheet_name, row_id, new_status, return_date=""):
  ws = sheet.worksheet(worksheet_name)
  cell = ws.find(str(row_id))
  if cell:
    row_num = cell.row
    if worksheet_name == "equipments":
      ws.update_cell(row_num, 4, new_status)
    elif worksheet_name == "borrowings":
      ws.update_cell(row_num, 6, return_date)
      ws.update_cell(row_num, 7, new_status)


# --- 2. ตั้งค่า CSS และฟอนต์ Saraban ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        * { font-family: 'Sarabun', sans-serif !important; }
        .card-box { padding: 20px; border-radius: 8px; color: white; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .card-wheelchair { background: linear-gradient(135deg, #1e7e34, #28a745); }
        .card-crutches { background: linear-gradient(135deg, #d39e00, #ffc107); color: #333 !important; }
        .card-bed { background: linear-gradient(135deg, #117a8b, #17a2b8); }
        .card-other { background: linear-gradient(135deg, #5a6268, #6c757d); }
        .card-title { font-size: 18px; font-weight: 600; margin-bottom: 5px; }
        .card-value { font-size: 24px; font-weight: 700; }
        .card-sub { font-size: 14px; opacity: 0.95; }
        /* แก้ไขปัญหาปุ่มอัปโหลดตัวหนังสือซ้อนกัน */
        [data-testid='stFileUploader'] section { padding: 10px; }
        [data-testid='stFileUploader'] button { width: auto; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- เมนูด้านข้าง (Sidebar) ---
st.sidebar.title("📌 เมนูระบบ")
choice = st.sidebar.radio(
    "เลือกการทำงาน",
    [
        "📊 แดชบอร์ดภาพรวม",
        "📋 รายการอุปกรณ์ทั้งหมด",
        "➕ เพิ่มอุปกรณ์ใหม่",
        "📝 ทำรายการยืม",
        "🔄 คืนอุปกรณ์",
    ],
)

# โหลดข้อมูลปัจจุบันจาก Google Sheets
df_equipments = get_data("equipments")
df_borrowings = get_data("borrowings")

# --- เมนูที่ 1: แดชบอร์ดภาพรวม ---
if choice == "📊 แดชบอร์ดภาพรวม":
  st.title("📊 แดชบอร์ดสรุปสถานะคลังกายอุปกรณ์ตามชนิด")
  st.write("")

  categories = [
      ("รถเข็น (Wheelchair)", "card-wheelchair", "🦽"),
      ("ไม้เท้า/ไม้ค้ำ", "card-crutches", "🦯"),
      ("เตียงผู้ป่วย", "card-bed", "🛏️"),
      ("อื่นๆ", "card-other", "📦"),
  ]

  st.subheader("📦 สรุปยอดแยกตามชนิดอุปกรณ์")
  cols = st.columns(4)

  for i, (cat_name, css_class, icon_emoji) in enumerate(categories):
    with cols[i]:
      if not df_equipments.empty and "category" in df_equipments.columns:
        total_cat = len(
            df_equipments[df_equipments["category"] == cat_name]
        )
        avail_cat = len(
            df_equipments[
                (df_equipments["category"] == cat_name)
                & (df_equipments["status"] == "พร้อมใช้งาน")
            ]
        )
        borrow_cat = len(
            df_equipments[
                (df_equipments["category"] == cat_name)
                & (df_equipments["status"] == "กำลังถูกยืม")
            ]
        )
      else:
        total_cat, avail_cat, borrow_cat = 0, 0, 0

      st.markdown(
          f"""
            <div class="card-box {css_class}">
                <div class="card-title">{icon_emoji} {cat_name}</div>
                <div class="card-value">ทั้งหมด {total_cat} ชิ้น</div>
                <div class="card-sub">✅ พร้อมใช้: {avail_cat} | 🔄 กำลังยืม: {borrow_cat}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

  st.divider()

  st.subheader("📋 รายการอุปกรณ์ทั้งหมดในคลัง พร้อมรูปภาพ")
  if df_equipments.empty:
    st.info("💡 ยังไม่มีข้อมูลอุปกรณ์ในระบบ กรุณาเพิ่มอุปกรณ์ใหม่")
  else:
    for index, row in df_equipments.iterrows():
      with st.container():
        col_img, col_info = st.columns([1, 4])
        with col_img:
          img_data = (
              row.get("image_url", "")
              if "image_url" in df_equipments.columns
              else ""
          )
          if img_data:
            try:
              if str(img_data).startswith("data:image"):
                st.image(img_data, width=120)
              elif str(img_data).startswith("http"):
                st.image(img_data, width=120)
              else:
                image_bytes = b64decode(img_data)
                st.image(image_bytes, width=120)
            except Exception:
              st.markdown("🖼️ *แสดงรูปไม่ได้*")
          else:
            st.markdown("🖼️ *ไม่มีรูปภาพ*")
        with col_info:
          st.markdown(f"### ID: {row['id']} - {row['name']}")
          st.write(
              f"**หมวดหมู่:** {row['category']} | **สถานะ:** {row['status']}"
          )
        st.divider()

  st.subheader("📌 รายการอุปกรณ์ที่กำลังถูกยืมขณะนี้")
  if not df_borrowings.empty and "status" in df_borrowings.columns:
    current_borrowed = df_borrowings[df_borrowings["status"] == "กำลังยืม"]
    if current_borrowed.empty:
      st.info("🎉 ไม่มีอุปกรณ์ค้างยืมในขณะนี้")
    else:
      st.dataframe(current_borrowed, use_container_width=True)
  else:
    st.info("🎉 ไม่มีอุปกรณ์ค้างยืมในขณะนี้")

# --- เมนูที่ 2: รายการอุปกรณ์ทั้งหมด ---
elif choice == "📋 รายการอุปกรณ์ทั้งหมด":
  st.subheader("📋 รายการกายอุปกรณ์ทั้งหมดในระบบ")
  if not df_equipments.empty:
    st.dataframe(df_equipments, use_container_width=True)
  else:
    st.info("ยังไม่มีข้อมูลอุปกรณ์")

# --- เมนูที่ 3: เพิ่มอุปกรณ์ใหม่ ---
elif choice == "➕ เพิ่มอุปกรณ์ใหม่":
  st.subheader("➕ เพิ่มกายอุปกรณ์เข้าคลัง")
  with st.form("add_eq_form"):
    eq_name = st.text_input("ชื่ออุปกรณ์ (เช่น รถเข็นอลูมิเนียมพับได้)")
    category = st.selectbox(
        "หมวดหมู่", ["รถเข็น (Wheelchair)", "ไม้เท้า/ไม้ค้ำ", "เตียงผู้ป่วย", "อื่นๆ"]
    )
    uploaded_file = st.file_uploader(
        "อัปโหลดรูปภาพอุปกรณ์ (จากมือถือหรือคอมพิวเตอร์)",
        type=["png", "jpg", "jpeg"],
    )
    submit = st.form_submit_button("💾 บันทึกข้อมูล")

    if submit and eq_name:
      image_string = ""
      if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_string = b64encode(bytes_data).decode("utf-8")

      new_id = (
          1
          if df_equipments.empty
          else int(df_equipments["id"].max()) + 1
      )
      add_row(
          "equipments", [new_id, eq_name, category, "พร้อมใช้งาน", image_string]
      )
      st.success(f"เพิ่มอุปกรณ์ '{eq_name}' เรียบร้อยแล้ว!")
      st.rerun()

# --- เมนูที่ 4: ทำรายการยืม ---
elif choice == "📝 ทำรายการยืม":
  st.subheader("📝 บันทึกการยืมอุปกรณ์")

  if df_equipments.empty:
    st.warning("⚠️ ไม่มีข้อมูลอุปกรณ์ในระบบ")
  else:
    available_eq = df_equipments[df_equipments["status"] == "พร้อมใช้งาน"]
    if available_eq.empty:
      st.warning("⚠️ ไม่มีอุปกรณ์ที่พร้อมให้ยืมในขณะนี้")
    else:
      with st.form("borrow_form"):
        available_eq["display_name"] = (
            available_eq["id"].astype(str)
            + " - "
            + available_eq["name"].astype(str)
            + " ("
            + available_eq["category"].astype(str)
            + ")"
        )
        eq_dict = dict(
            zip(available_eq["display_name"], available_eq["id"])
        )

        selected_eq_name = st.selectbox(
            "เลือกอุปกรณ์ที่ต้องการยืม", list(eq_dict.keys())
        )
        borrower_name = st.text_input("ชื่อ-นามสกุล ผู้ยืม")
        phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
        borrow_date = st.date_input("วันที่ยืม", date.today())

        submit_borrow = st.form_submit_button("✅ ยืนยันการยืม")

        if submit_borrow and borrower_name and phone:
          eq_id = int(eq_dict[selected_eq_name])
          borrow_id = (
              1
              if df_borrowings.empty
              else int(df_borrowings["id"].max()) + 1
          )

          add_row(
              "borrowings",
              [
                  borrow_id,
                  eq_id,
                  borrower_name,
                  phone,
                  str(borrow_date),
                  "",
                  "กำลังยืม",
              ],
          )
          update_row_status("equipments", eq_id, "กำลังถูกยืม")

          st.success(f"บันทึกการยืมอุปกรณ์สำเร็จสำหรับคุณ {borrower_name}")
          st.rerun()

# --- เมนูที่ 5: คืนอุปกรณ์ ---
elif choice == "🔄 คืนอุปกรณ์":
  st.subheader("🔄 บันทึกรับคืนอุปกรณ์")

  if df_borrowings.empty or "status" not in df_borrowings.columns:
    st.info("🎉 ไม่มีอุปกรณ์ค้างยืมในขณะนี้")
  else:
    borrowed_df = df_borrowings[df_borrowings["status"] == "กำลังยืม"]

    if borrowed_df.empty:
      st.info("🎉 ไม่มีอุปกรณ์ค้างยืมในขณะนี้ ทุกชิ้นอยู่ครบในคลัง")
    else:
      st.dataframe(borrowed_df, use_container_width=True)

      borrow_id_to_return = st.selectbox(
          "เลือก ID รายการยืมที่ต้องการบันทึกรับคืน",
          borrowed_df["id"].tolist(),
      )

      if st.button("✅ ยืนยันการรับคืนอุปกรณ์"):
        row = borrowed_df[borrowed_df["id"] == borrow_id_to_return].iloc[0]
        eq_id = int(row["eq_id"])

        update_row_status(
            "borrowings", borrow_id_to_return, "คืนแล้ว", str(date.today())
        )
        update_row_status("equipments", eq_id, "พร้อมใช้งาน")

        st.success("✅ บันทึกรับคืนอุปกรณ์เรียบร้อยแล้ว!")
        st.rerun()
