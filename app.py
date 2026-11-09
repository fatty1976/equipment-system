from base64 import b64decode, b64encode
from datetime import date
from io import BytesIO
import pandas as pd
from PIL import Image, ImageOps
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


# --- ฟังก์ชันปรับปรุงและหมุนรูปแนวตั้งอัตโนมัติ ---
def compress_image(image_file):
  try:
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P"):
      img = img.convert("RGB")

    max_size = 200
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=55)
    return b64encode(buffered.getvalue()).decode("utf-8")
  except Exception:
    return ""


# --- 2. ตั้งค่า CSS และฟอนต์ Saraban ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        * { font-family: 'Sarabun', sans-serif !important; }
        
        [data-testid='stFileUploader'] * {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }

        /* ดีไซน์การ์ดให้จัดวางข้อความซ้าย รูปภาพไอคอนใหญ่ขวา */
        .card-box { 
            position: relative;
            padding: 20px; 
            border-radius: 8px; 
            color: white; 
            margin-bottom: 15px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            min-height: 130px;
        }
        .card-wheelchair { background: linear-gradient(135deg, #1e7e34, #28a745); }
        .card-crutches { background: linear-gradient(135deg, #d39e00, #ffc107); color: #333 !important; }
        .card-bed { background: linear-gradient(135deg, #117a8b, #17a2b8); }
        .card-other { background: linear-gradient(135deg, #5a6268, #6c757d); }
        
        /* ขยายขนาดรูปไอคอนให้ใหญ่ชัดเจนขึ้น (85px) และเว้นพื้นที่ข้อความด้านซ้าย */
        .card-icon-img { 
            position: absolute;
            top: 15px;
            right: 15px;
            width: 85px;
            height: 85px;
            object-fit: contain;
        }
        .card-title { font-size: 17px; font-weight: 600; margin-bottom: 5px; padding-right: 90px; }
        .card-value { font-size: 22px; font-weight: 700; margin-bottom: 3px; padding-right: 90px; }
        .card-sub { font-size: 13px; opacity: 0.95; }
        
        .equipment-img img {
            border-radius: 8px;
            object-fit: contain;
            max-height: 150px;
            width: auto;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            background-color: #f8f9fa;
            padding: 3px;
        }
        
        .main-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        .main-header img {
            height: 55px;
            width: auto;
        }
        .main-header h2 {
            margin: 0;
            padding: 0;
            font-weight: 700;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# --- เมนูด้านข้าง (Sidebar) ---
st.sidebar.title("📌 เมนูระบบ")
choice = st.sidebar.radio(
    "เลือกการทำงาน",
    [
        "📊 ภาพรวมกายอุปกรณ์",
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
if choice == "📊 ภาพรวมกายอุปกรณ์":
  try:
    with open("moph-logo.gif", "rb") as f:
      gif_bytes = f.read()
      gif_base64 = b64encode(gif_bytes).decode("utf-8")
      gif_url = f"data:image/gif;base64,{gif_base64}"
  except Exception:
    gif_url = ""

  if gif_url:
    st.markdown(
        f"""
        <div class="main-header">
            <img src="{gif_url}" alt="MOPH Logo">
            <h2>ระบบยืม-คืนกายอุปกรณ์จำแนกตามชนิด</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.markdown("<h2>🏥 ระบบยืม-คืนกายอุปกรณ์จำแนกตามชนิด</h2>", unsafe_allow_html=True)

  st.write("")

  # กำหนดชื่อหมวดหมู่, คลาสสี, และไฟล์ไอคอนที่ตรงกัน
  categories = [
      ("รถเข็น (Wheelchair)", "card-wheelchair", "icon-wheelchair.png"),
      ("ไม้เท้า/ไม้ค้ำ", "card-crutches", "icon-crutches.png"),
      ("เตียงผู้ป่วย", "card-bed", "icon-bed.png"),
      ("อื่นๆ", "card-other", "icon-other.png"),
  ]

  st.subheader("📦 สรุปยอดจำแนกตามชนิดกายอุปกรณ์")
  cols = st.columns(4)

  for i, (cat_name, css_class, icon_filename) in enumerate(categories):
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

      # แปลงไฟล์ไอคอนเป็น Base64 เพื่อให้แสดงผลผ่าน HTML ได้อย่างไร้รอยต่อ
      icon_base64_str = ""
      try:
        with open(icon_filename, "rb") as img_f:
          icon_bytes = img_f.read()
          icon_b64 = b64encode(icon_bytes).decode("utf-8")
          icon_base64_str = f"data:image/png;base64,{icon_b64}"
      except Exception:
        pass

      st.markdown(
          f"""
            <div class="card-box {css_class}">
                <img src="{icon_base64_str}" class="card-icon-img" alt="icon">
                <div class="card-title">{cat_name}</div>
                <div class="card-value">ทั้งหมด {total_cat} ชิ้น</div>
                <div class="card-sub">✅ พร้อมใช้: {avail_cat} | 🔄 กำลังยืม: {borrow_cat}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

  st.divider()

  st.subheader("📋 รายการกายอุปกรณ์ทั้งหมดในคลัง พร้อมรูปภาพ")
  if df_equipments.empty:
    st.info("💡 ยังไม่มีข้อมูลอุปกรณ์ในระบบ กรุณาเพิ่มอุปกรณ์ใหม่")
  else:
    for index, row in df_equipments.iterrows():
      with st.container():
        col_img, col_info = st.columns([1, 5])
        with col_img:
          st.markdown('<div class="equipment-img">', unsafe_allow_html=True)
          img_data = (
              row.get("image_url", "")
              if "image_url" in df_equipments.columns
              else ""
          )
          if img_data:
            try:
              if str(img_data).startswith("data:image"):
                st.image(img_data, width=100)
              elif str(img_data).startswith("http"):
                st.image(img_data, width=100)
              else:
                image_bytes = b64decode(img_data)
                st.image(image_bytes, width=100)
            except Exception:
              st.markdown("🖼️ *แสดงรูปไม่ได้*")
          else:
            st.markdown("🖼️ *ไม่มีรูป*")
          st.markdown("</div>", unsafe_allow_html=True)

        with col_info:
          st.markdown(f"### ID: {row['id']} - {row['name']}")
          st.write(
              f"**หมวดหมู่:** {row['category']} | **สถานะ:** {row['status']}"
          )
        st.divider()

  st.subheader("📌 รายการกายอุปกรณ์ที่กำลังถูกยืมขณะนี้")
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

  if "save_success" not in st.session_state:
    st.session_state.save_success = False

  if st.session_state.save_success:
    st.success("🎉 บันทึกข้อมูลอุปกรณ์เรียบร้อยแล้ว! พร้อมสำหรับเพิ่มชิ้นถัดไป")
    if st.button("➕ เพิ่มอุปกรณ์ชิ้นใหม่"):
      st.session_state.save_success = False
      st.rerun()
  else:
    with st.form("add_eq_form"):
      eq_name = st.text_input("ชื่ออุปกรณ์ (เช่น รถเข็นอลูมิเนียมพับได้)")
      category = st.selectbox(
          "หมวดหมู่",
          ["รถเข็น (Wheelchair)", "ไม้เท้า/ไม้ค้ำ", "เตียงผู้ป่วย", "อื่นๆ"],
      )
      uploaded_file = st.file_uploader(
          "อัปโหลดรูปภาพอุปกรณ์ (หมุนภาพแนวตั้งอัตโนมัติ)",
          type=["png", "jpg", "jpeg"],
      )
      submit = st.form_submit_button("💾 บันทึกข้อมูล")

      if submit:
        if not eq_name.strip():
          st.warning("⚠️ กรุณากรอกชื่ออุปกรณ์ก่อนบันทึก")
        else:
          with st.spinner("กำลังบันทึกข้อมูลและปรับหมุนภาพแนวตั้ง..."):
            image_string = ""
            if uploaded_file is not None:
              image_string = compress_image(uploaded_file)

            new_id = (
                1
                if df_equipments.empty
                else int(df_equipments["id"].max()) + 1
            )
            add_row(
                "equipments",
                [new_id, eq_name, category, "พร้อมใช้งาน", image_string],
            )

          st.session_state.save_success = True
          st.rerun()

# --- เมนูที่ 4: ทำรายการยืม ---
elif choice == "📝 ทำรายการยืม":
  st.subheader("📝 บันทึกการยืมกายอุปกรณ์")

  if df_equipments.empty:
    st.warning("⚠️ ไม่มีข้อมูลกายอุปกรณ์ในระบบ")
  else:
    available_eq = df_equipments[df_equipments["status"] == "พร้อมใช้งาน"]
    if available_eq.empty:
      st.warning("⚠️ ไม่มีกายอุปกรณ์ที่พร้อมให้ยืมในขณะนี้")
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
            "เลือกกายอุปกรณ์ที่ต้องการยืม", list(eq_dict.keys())
        )
        borrower_name = st.text_input("ชื่อ-นามสกุล ผู้ยืม")
        phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
        address = st.text_area("ที่อยู่ (address)")
        borrow_date = st.date_input("วันที่ยืม", date.today())

        submit_borrow = st.form_submit_button("✅ ยืนยันการยืม")

        if submit_borrow:
          if not borrower_name.strip() or not address.strip():
            st.warning("⚠️ กรุณากรอก 'ชื่อ-นามสกุล' และ 'ที่อยู่' ให้ครบถ้วน")
          else:
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
                    address,
                ],
            )
            update_row_status("equipments", eq_id, "กำลังถูกยืม")

            st.success(f"บันทึกการยืมอุปกรณ์สำเร็จสำหรับคุณ {borrower_name}")
            st.rerun()

# --- เมนูที่ 5: คืนอุปกรณ์ ---
elif choice == "🔄 คืนกายอุปกรณ์":
  st.subheader("🔄 บันทึกรับคืนกายอุปกรณ์")

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
