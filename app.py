import streamlit as st
import pandas as pd
import json
import os
import base64
from io import BytesIO
from datetime import datetime

# ==========================================
# 0. 외부 라이브러리 안전 로드 (없어도 앱이 절대 죽지 않음)
# ==========================================
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ==========================================
# 1. 기본 페이지 설정 및 스타일
# ==========================================
st.set_page_config(
    page_title="우리부동산 통합업무시스템",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-banner {
        background: linear-gradient(90deg, #004ea2 0%, #003775 100%);
        color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
    }
    .main-banner h1 { font-size: 24px; font-weight: 900; margin: 0; color: #ffffff; }
    .main-banner p { font-size: 13.5px; color: #e0f2fe; margin: 4px 0 0 0; }
    .tel-badge {
        background: #0f172a; color: #fde047; padding: 8px 16px; border-radius: 8px;
        font-weight: 800; font-size: 14px; border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px;
        font-weight: 800; color: #334155;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004ea2 !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 구글 스프레드시트 연동 설정
# ==========================================
SPREADSHEET_ID = "1oTTZ1ok-quer9_NR5v5hEFYpRiOrR8tAwwo7UPnwRco"
REGIONS = ["석남동", "가좌동", "송림동", "송현동", "도화동", "원창동", "경서동"]
DEAL_TYPES = ["공장임대", "공장매매", "신축공장분양"]
BIZ_TAGS = ["금속·기계가공", "물류·유통창고", "일반제조·조립", "화학·환경인허가", "신축·사옥형"]

PROP_COLUMNS = [
    "매물번호", "등록일자", "홈페이지노출", "거래구분", "소재지(권역)", "상세주소(지번)",
    "매물제목", "가격(보/월)", "면적", "사무실평수", "층고", "동력", "호이스트",
    "대형차량", "추천업종", "입주가능일", "용도지역/구조", "사용승인일",
    "임대인(건물주)", "임대인연락처", "특징메모", "대표사진"
]

CUST_COLUMNS = [
    "등록일자", "구분", "고객명(업체명)", "연락처", "희망지역", "희망평수", "예산(보/월/매매가)", "필수조건(호이스트/전력)", "진행상태", "상세메모"
]

def get_gspread_client():
    if not GSPREAD_AVAILABLE:
        return None
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
        elif "GOOGLE_CREDENTIALS" in st.secrets:
            creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
        elif os.path.exists("service_account.json"):
            creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
            return gspread.authorize(creds)
    except Exception:
        pass
    return None

def normalize_dataframe(df, default_cols):
    # 중복 컬럼이나 빈 컬럼 이름이 있어도 절대 에러가 나지 않게 보정
    df = df.loc[:, ~df.columns.duplicated()]
    for c in default_cols:
        if c not in df.columns:
            df[c] = ""
    return df[default_cols].fillna("")

def load_sheet_data(sheet_name, default_cols, local_csv):
    client = get_gspread_client()
    if client:
        try:
            sh = client.open_by_key(SPREADSHEET_ID)
            try:
                ws = sh.worksheet(sheet_name)
            except Exception:
                ws = sh.add_worksheet(title=sheet_name, rows="500", cols="25")
                ws.append_row(default_cols)
            records = ws.get_all_values()
            if len(records) > 1:
                raw_headers = records[0]
                headers = [h if h.strip() != "" else f"빈열_{i}" for i, h in enumerate(raw_headers)]
                df = pd.DataFrame(records[1:], columns=headers)
                df = normalize_dataframe(df, default_cols)
                df.to_csv(local_csv, index=False, encoding="utf-8-sig")
                return df, True
            else:
                return pd.DataFrame(columns=default_cols), True
        except Exception:
            pass

    # 공개 시트 URL로 읽기 시도
    try:
        pub_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(pub_url)
        df = normalize_dataframe(df, default_cols)
        return df, False
    except Exception:
        pass

    # 로컬 백업 파일 읽기
    if os.path.exists(local_csv):
        try:
            df = pd.read_csv(local_csv)
            df = normalize_dataframe(df, default_cols)
            return df, False
        except Exception:
            pass

    return pd.DataFrame(columns=default_cols), False

def save_sheet_data(df, sheet_name, local_csv):
    df = normalize_dataframe(df, df.columns.tolist())
    try:
        df.to_csv(local_csv, index=False, encoding="utf-8-sig")
    except Exception:
        pass
    client = get_gspread_client()
    if client:
        try:
            sh = client.open_by_key(SPREADSHEET_ID)
            try:
                ws = sh.worksheet(sheet_name)
            except Exception:
                ws = sh.add_worksheet(title=sheet_name, rows="500", cols="25")
            ws.clear()
            data_to_write = [df.columns.values.tolist()] + df.astype(str).values.tolist()
            ws.update(data_to_write)
            return True
        except Exception as e:
            st.warning(f"구글 시트 자동 쓰기 확인 필요 (로컬 저장은 완료됨): {e}")
    return False

def compress_uploaded_image(uploaded_file):
    if not uploaded_file:
        return ""
    try:
        if PIL_AVAILABLE:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((600, 420))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=65)
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_str}"
        else:
            b64_str = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_str}"
    except Exception:
        return ""

# ==========================================
# 3. 김소장 스타일 네이버 블로그 원고 자동 생성기
# ==========================================
def generate_naver_blog_post(row):
    region = str(row.get("소재지(권역)", "송현동") or "송현동")
    deal = str(row.get("거래구분", "공장임대") or "공장임대")
    price = str(row.get("가격(보/월)", "보증금 3,000만 / 월세 230만") or "보증금 3,000만 / 월세 230만")
    
    area_digits = ''.join(filter(str.isdigit, str(row.get("면적", "75"))))
    area_num = int(area_digits) if area_digits else 75
    
    off_digits = ''.join(filter(str.isdigit, str(row.get("사무실평수", "15"))))
    office_num = int(off_digits) if off_digits else 0
    
    total_py = area_num + office_num
    total_m2 = round(total_py * 3.3058)

    height = str(row.get("층고", "호이스트 주행 넉넉한 하이 층고") or "호이스트 주행 넉넉한 하이 층고")
    power = str(row.get("동력", "30kW") or "30kW")
    hoist = str(row.get("호이스트", "호이스트 2.8톤 완비") or "호이스트 2.8톤 완비")
    road = str(row.get("대형차량", "8m 도로 화물차 및 윙바디 접안 수월") or "8m 도로 화물차 접안 수월")
    move_in = str(row.get("입주가능일", "즉시 입주 / 협의 가능") or "즉시 입주 / 협의 가능")
    zoning = str(row.get("용도지역/구조", "일반공업지역 / 철골조") or "일반공업지역 / 철골조")
    approval_date = str(row.get("사용승인일", "건축물대장 확인 완료") or "건축물대장 확인 완료")
    biz_tag = str(row.get("추천업종", "금속·기계가공") or "금속·기계가공")
    memo = str(row.get("특징메모", "공구상가 및 주요 간선도로 인접, 가성비 최상 매물") or "가성비 최상 매물")

    office_line = f" + 2층 {office_num}평 전용 사무실" if office_num > 0 else " (단독 작업장 구조)"

    blog_text = f"""안녕하세요. 인천 공장·창고 전문 우리부동산입니다.
인천 {region} {deal} 매물 중 탄탄한 제조 인프라 배후에서 {hoist} 설비와 실속 있는 작업 공간을 갖추고 이 가격에 나오는 곳은 정말 귀합니다.

요즘 {region}이나 인근 공업지역에서 {area_num}평대 1층 공장을 찾아보시면 금액대가 만만치 않은 데다, 호이스트가 없거나 동력·사무실이 마땅치 않아 초기 시설 설치비로 수천만 원이 깨지는 경우가 허다합니다.
오늘 소개해 드리는 매물은 인천 {region} 1층 {area_num}평 공장{office_line} 조건으로, 【 {price} 】이라는 주변 시세 대비 아주 합리적인 조건으로 나와 강력 추천해 드립니다.

---------------------------------------------------------
[ 📸 대표사진 넣는 곳 - 공장 외관 및 진입도로 전경 ]
주요 산업단지 및 공구상가·외주 가공 단지가 인접해 있어 원자재 수급 및 물류 연계성이 인천에서 손꼽히는 입지입니다. 공장 정면으로 진입 도로({road})가 반듯하게 열려 있어 화물차가 문 앞까지 수월하게 접안해 상하차 작업을 진행하기에 최적화된 동선을 자랑합니다.
---------------------------------------------------------

📊 [ 인천 {region} {deal} 핵심 제원 요약표 ] (블로그 표에 복사해 넣으세요)
• 소재지 : 인천광역시 {region} (상세 지번은 보안상 유선 안내)
• 거래조건 : {price}
• 매물구분 / 주용도 : {deal} / 공장·창고
• 입주날짜 : {move_in}
• 용도지역 / 건축구조 : {zoning}
• 사용승인일 : {approval_date}
• 실사용 면적 : 1층 {area_num}평{office_line} (합계 약 {total_m2}㎡)

✨ [ 본 매물 핵심 체크포인트 ]
• 층고 : {height}
• 동력 : {power} (제조 및 가공 설비 구동 충분)
• 도로 및 주차 : {road} (문 앞 차량 작업 및 접안 편리)
• 승강기 / 호이스트 : {hoist}
• 사무실 / 화장실 : {"2층 " + str(office_num) + "평 독립 사무실 및 화장실 구비" if office_num > 0 else "내부 사무 공간 및 전용 화장실 구비"}
• 관리비 : 실비 정산

✅ 인천 {region} {deal} 매물 중 【 {price} 】의 특급 시세 가성비!
✅ {hoist} 설비로 H빔 보강 및 크레인 신규 설치비 수천만 원 굳히고 입주!
✅ 동력 {power} 기본 인입으로 추가 승압 공사비 부담 없이 기계 설비 즉시 연결!
✅ {"2층 " + str(office_num) + "평 독립 사무실 완비로 1층 바닥 공간 " + str(area_num) + "평을 온전히 작업장으로 통활용!" if office_num > 0 else "기둥 간섭 없는 반듯한 1층 작업장 구조로 공간 활용도 극대화!"}
✅ {memo}
✅ 추천 업종 : {biz_tag}, 정밀 금형·기계 가공, 선반·밀링 임가공, 철구조물 제작, 물류 보관 등 강력 추천!

---------------------------------------------------------
[ 📸 1층 내부 사진 1~3장 넣는 곳 ]
공장 메인 진입로 및 화물차 문 앞 접안 전경입니다. 출입구 폭과 높이가 널찍해 무거운 원자재와 파레트를 내부로 직결 반입하기 수월합니다.

1층 메인 작업장 전체 전경입니다. 기계 하중을 단단하게 버텨주는 튼튼한 에폭시/콘크리트 바닥 기초 위에 설비를 안정적으로 안착시킬 수 있습니다. 주변 민원 눈치 볼 필요 없이 편하게 일하실 '진짜 제조업·물류업' 대표님들께 최고의 사업장입니다.

[ 📸 상부 호이스트 및 층고 사진 넣는 곳 ]
상단 {hoist} 및 천장 트러스 골조 상세 뷰입니다. 빈 공장에 H빔 보강하고 호이스트 레일 새로 까시려면 최소 수천만 원 깨지는 거 대표님들이 더 잘 아실 텐데요. 무거운 중량 자재와 완제품을 힘들이지 않고 안전하게 인양할 수 있습니다.

[ 📸 2층 사무실 및 화장실 사진 넣는 곳 ]
{"약 " + str(office_num) + "평 규모의 전용 사무실 내부 공간입니다. 컴퓨터 데스크, 도면 검토대, 상담용 소파를 여유롭게 두고 현장 소음 간섭 없이 바이어 미팅과 수주 관리를 보기에 안성맞춤입니다." if office_num > 0 else "깔끔하게 관리된 부대 공간 및 전용 화장실 전경입니다."}
---------------------------------------------------------

인천 {region} 공업지역에서 1층 {area_num}평 작업장에 {hoist}, 동력 {power}{office_line}까지 알차게 갖춘 공장을 【 {price} 】에 선점할 수 있는 기회는 흔치 않습니다.
고정비를 획기적으로 줄이면서 즉시 기계를 안착시켜 조업에 들어갈 알짜배기 공장을 찾으시는 대표님들께서는 서둘러 현장을 확인해 보시길 권해드립니다.

[ 📸 우리부동산 대표 명함 사진 넣는 곳 ]
명함을 누르시면 전화 연결이 됩니다. 언제든 편하게 연락 주시기 바랍니다.

매물 상담 문의, 공장·창고 접수 의뢰 언제든 환영합니다.
🏭 우리부동산 공인중개사 사무소 대표 김태형
📞 매매문의 : 032-582-6200 | 📞 임대문의 : 032-576-2600
📱 대표 직통 : 010-2660-8276
🌐 공식 블로그 : https://blog.naver.com/woorirealestate__

정직하고 최선을 다하여 책임 중개하겠습니다.

#{region}공장임대 #{region}공장매매 #{region}공장 #인천{region}공장 #인천공장임대 #인천공장매매 #인천창고임대 #인천호이스트공장 #신축공장분양 #석남동공장임대 #가좌동공장임대 #송림동공장임대 #송현동공장임대 #도화동공장임대 #원창동공장임대 #경서동공장임대 #인천공장전문 #우리부동산
"""
    return blog_text

# ==========================================
# 4. 상단 헤더 및 데이터 로드
# ==========================================
df_props, gs_connected = load_sheet_data("properties", PROP_COLUMNS, "properties.csv")
df_custs, _ = load_sheet_data("customers", CUST_COLUMNS, "customers.csv")

st.markdown("""
<div class="main-banner">
    <div>
        <h1>🏭 우리부동산 통합업무시스템 (스트림릿 전용 ERP)</h1>
        <p>주력 권역(석남·가좌·송림·송현·도화·원창·경서동) 매물 관리 · 구글 시트 & 홈페이지 실시간 연동 · 네이버 블로그 원고 1초 생성</p>
    </div>
    <div class="tel-badge">
        📞 매매 032-582-6200 | 임대 032-576-2600
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("🔗 시스템 연동 상태")
    if gs_connected:
        st.success("✅ 구글 스프레드시트 실시간 양방향 연동 중")
    elif not GSPREAD_AVAILABLE:
        st.warning("⚠️ requirements.txt에 gspread 패키지를 추가하면 구글시트 자동 저장이 활성화됩니다.")
    else:
        st.info("ℹ️ 구글시트 읽기 연동 중 (자동 저장은 Secrets 키 확인)")
    
    st.markdown(f"📊 **[구글 스프레드시트 원본 열기 ↗](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit)**")
    st.markdown("🟢 **[우리부동산 네이버 공식 블로그 ↗](https://blog.naver.com/woorirealestate__)**")
    st.divider()
    st.subheader("📥 비상용 엑셀(CSV) 다운로드")
    csv_props = df_props.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("💾 전체 매물장부 엑셀 다운로드", data=csv_props, file_name=f"우리부동산_매물장부_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    csv_custs = df_custs.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("💾 손님장부 엑셀 다운로드", data=csv_custs, file_name=f"우리부동산_손님장부_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

# ==========================================
# 5. 메인 4대 업무 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ 1. 새 매물 등록 (+사진/블로그 자동생성)",
    "📋 2. 전체 매물 장부 (실시간 수정/삭제)",
    "📝 3. 네이버 블로그 & 카톡 브리핑 생성기",
    "👥 4. 찾는 손님 (구해요) CRM 장부"
])

with tab1:
    st.subheader("➕ 신규 공장·창고·신축공장분양 매물 등록")
    st.caption("여기서 등록하시면 구글 스프레드시트(`properties` 탭)에 저장되며, **손님용 홈페이지(`index.html`)에 자동으로 매물이 뜹니다!**")

    with st.form("add_property_form", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        next_num = f"W-{101 + len(df_props)}"
        p_id = c1.text_input("매물번호 *", value=next_num)
        p_deal = c2.selectbox("거래구분 *", DEAL_TYPES)
        p_region = c3.selectbox("소재지(주력 7대 권역) *", REGIONS)
        p_show = c4.selectbox("홈페이지 자동 노출 여부 *", ["공개 (홈페이지 즉시 노출)", "비공개 (내부 장부만 보관)"])

        c5, c6, c7 = st.columns([2, 1.2, 1])
        p_title = c5.text_input("홈페이지/블로그용 매물 제목 *", placeholder="예: 송현동 공구상가 인근 호이스트 2.8톤+2층 사무실 완비 단독 공장")
        p_price = c6.text_input("가격 조건 (보증금/월세 또는 매매·분양가) *", placeholder="예: 보증금 3,000만 / 월세 230만")
        p_biz = c7.selectbox("추천 업종 태그", BIZ_TAGS)

        c8, c9, c10, c11 = st.columns(4)
        p_area = c8.text_input("1층 공장/창고 전용평수 (숫자) *", value="75")
        p_office = c9.text_input("2층/부속 사무실 평수 (없으면 0)", value="15")
        p_height = c10.text_input("처마 층고", value="층고 8.5M (호이스트 주행 넉넉)")
        p_power = c11.text_input("계약 전력(동력)", value="30kW")

        c12, c13, c14, c15 = st.columns(4)
        p_hoist = c12.text_input("호이스트 설비", value="호이스트 2.8톤 완비")
        p_truck = c13.selectbox("차량 진입 / 도로 조건", [
            "40ft 츄레라 진입 가능 (광폭도로)",
            "5t~11t 윙바디 작업 수월 (8m~10m 도로)",
            "1t~2.5t 화물차 문앞 접안 (6m 도로)"
        ])
        p_movein = c14.text_input("입주 가능 시기", value="즉시 입주 / 협의")
        p_zoning = c15.text_input("용도지역 / 건축구조", value="일반공업지역 / 철골조")

        st.markdown("##### 🔒 중개사 전용 비밀장부 (손님용 홈페이지에는 절대 노출되지 않습니다)")
        s1, s2, s3, s4 = st.columns([1.5, 1, 1.2, 1])
        p_secret_addr = s1.text_input("📍 실제 상세 지번 (비공개)", placeholder="예: 송현동 123-45")
        p_owner_name = s2.text_input("👤 건물주/임대인 성함", placeholder="예: 김회장님")
        p_owner_tel = s3.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")
        p_approval = s4.text_input("📅 사용승인일", placeholder="예: 1997.01.17")

        p_memo = st.text_area("💡 핵심 특징 메모 (블로그 원고 및 브리핑에 자동 반영됩니다)", 
                              value="인천산업유통센터 및 공구상가 초인접, 호이스트 및 독립 사무실 완비로 초기 시설비 수천만 원 절감 가능한 특급 가성비 매물")

        st.markdown("##### 📸 대표 현장 사진 등록 (선택사항 - 등록 시 홈페이지 매물 카드에 즉시 반영!)")
        img_col1, img_col2 = st.columns(2)
        uploaded_photo = img_col1.file_uploader("방법 1) 내 PC/폰에서 대표 사진 1장 선택 (자동 초경량 압축)", type=["jpg", "jpeg", "png", "webp"])
        photo_url_input = img_col2.text_input("방법 2) 또는 이미지 웹 주소(URL) 붙여넣기 (비워두면 기본 공장 사진 적용)")

        submitted = st.form_submit_button("💾 매물 저장 + 구글시트/홈페이지 동기화 + 블로그 원고 생성", use_container_width=True)

        if submitted:
            final_photo = ""
            if uploaded_photo is not None:
                final_photo = compress_uploaded_image(uploaded_photo)
            elif photo_url_input.strip():
                final_photo = photo_url_input.strip()

            new_row = {
                "매물번호": p_id,
                "등록일자": datetime.now().strftime("%Y-%m-%d"),
                "홈페이지노출": "공개" if "공개" in p_show else "비공개",
                "거래구분": p_deal,
                "소재지(권역)": p_region,
                "상세주소(지번)": p_secret_addr,
                "매물제목": p_title if p_title.strip() else f"인천 {p_region} {p_area}평 {p_deal} 추천 매물",
                "가격(보/월)": p_price,
                "면적": f"{p_area}평",
                "사무실평수": f"{p_office}평",
                "층고": p_height,
                "동력": p_power,
                "호이스트": p_hoist,
                "대형차량": p_truck,
                "추천업종": p_biz,
                "입주가능일": p_movein,
                "용도지역/구조": p_zoning,
                "사용승인일": p_approval,
                "임대인(건물주)": p_owner_name,
                "임대인연락처": p_owner_tel,
                "특징메모": p_memo,
                "대표사진": final_photo
            }

            df_props = pd.concat([pd.DataFrame([new_row]), df_props], ignore_index=True)
            ok = save_sheet_data(df_props, "properties", "properties.csv")
            if ok:
                st.success(f"🎉 [{p_id}] 매물이 구글 스프레드시트에 완벽히 저장되었으며, 손님용 홈페이지에도 즉시 반영되었습니다!")
            else:
                st.success(f"🎉 [{p_id}] 매물이 저장되었습니다! 아래에서 자동 완성된 네이버 블로그 원고를 바로 복사하세요.")

            st.session_state["last_created_row"] = new_row

    if "last_created_row" in st.session_state:
        st.divider()
        st.subheader("📝 방금 등록한 매물 — 네이버 블로그 포스팅 원고 (우측 상단 복사 아이콘 클릭!)")
        blog_draft = generate_naver_blog_post(st.session_state["last_created_row"])
        st.code(blog_draft, language="markdown")

with tab2:
    st.subheader(f"📋 전체 보유 매물 통합장부 (총 {len(df_props)}건)")
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    sel_reg = f_col1.selectbox("권역 필터", ["전체"] + REGIONS)
    sel_deal = f_col2.selectbox("거래구분 필터", ["전체"] + DEAL_TYPES)
    search_kw = f_col3.text_input("🔍 초고속 장부 검색 (지번, 건물주 연락처, 매물번호, 특징)")

    filtered_df = df_props.copy()
    if sel_reg != "전체":
        filtered_df = filtered_df[filtered_df["소재지(권역)"].astype(str).str.contains(sel_reg)]
    if sel_deal != "전체":
        filtered_df = filtered_df[filtered_df["거래구분"].astype(str).str.contains(sel_deal)]
    if search_kw.strip():
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_kw.strip(), case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        use_container_width=True,
        height=460,
        key="props_editor"
    )

    if st.button("💾 장부 수정사항 구글시트 & 홈페이지 즉시 반영", type="primary"):
        save_sheet_data(edited_df, "properties", "properties.csv")
        st.success("✅ 수정하신 장부 내용이 저장되었습니다!")
        st.rerun()

with tab3:
    st.subheader("📝 네이버 블로그 원고 & 카카오톡 브리핑 1초 생성기")
    if len(df_props) == 0:
        st.info("먼저 [1. 새 매물 등록] 탭에서 매물을 등록해 주세요.")
    else:
        prop_options = [f"[{r['매물번호']}] {r['소재지(권역)']} {r['면적']} {r['거래구분']} ({r['가격(보/월)']}) - {r['상세주소(지번)']}" for _, r in df_props.iterrows()]
        selected_idx = st.selectbox("블로그 원고나 카톡 브리핑을 뽑을 매물을 선택하세요", range(len(prop_options)), format_func=lambda i: prop_options[i])
        target_row = df_props.iloc[selected_idx].to_dict()

        col_b1, col_b2 = st.columns([1.4, 1])
        with col_b1:
            st.markdown("#### 🟢 네이버 블로그 가독성 최적화 원고 (김소장 양식)")
            st.caption("코드 박스 우측 상단의 **[복사(📄)]** 아이콘을 누르면 전체 원고가 1초 만에 복사됩니다.")
            st.code(generate_naver_blog_post(target_row), language="markdown")
        with col_b2:
            st.markdown("#### 💬 손님 전송용 카카오톡 1초 브리핑")
            kakao_txt = f"""[🏭 우리공장부동산 추천 매물 브리핑]
• 매물번호 : {target_row.get('매물번호','')} ({target_row.get('거래구분','')})
• 소재지 : 인천 {target_row.get('소재지(권역)','')} (지번 안심보호)
• 실사용면적 : 1층 {target_row.get('면적','')} (사무실 {target_row.get('사무실평수','0평')})
• 금액조건 : {target_row.get('가격(보/월)','')}
• 설비제원 : {target_row.get('층고','')} / 동력 {target_row.get('동력','')} / {target_row.get('호이스트','')}
• 차량진입 : {target_row.get('대형차량','')}
• 핵심특징 : {target_row.get('특징메모','')}

☎ 매매문의 : 032-582-6200 | 임대문의 : 032-576-2600
👤 우리부동산 대표 김태형 : 010-2660-8276"""
            st.code(kakao_txt, language="text")

with tab4:
    st.subheader("👥 찾는 손님 (구해요) 및 콜백 관리 장부")
    with st.expander("➕ 새 손님(구해요 문의) 등록하기", expanded=False):
        with st.form("add_cust_form"):
            cc1, cc2, cc3, cc4 = st.columns(4)
            c_type = cc1.selectbox("구분", ["임대 구함", "매매 구함", "신축공장분양 문의", "매물 내놓기(접수)"])
            c_name = cc2.text_input("고객명 / 업체명 *")
            c_tel = cc3.text_input("연락처 *")
            c_reg = cc4.text_input("희망 지역", value="석남·가좌·송현·송림동")

            cc5, cc6, cc7, cc8 = st.columns(4)
            c_area = cc5.text_input("희망 평수", placeholder="예: 70~100평")
            c_budget = cc6.text_input("예산 조건", placeholder="예: 월 250만 이하")
            c_req = cc7.text_input("필수 설비 (호이스트/전력)", placeholder="예: 호이스트 2.8톤 필수")
            c_status = cc8.selectbox("진행 상태", ["🔥 진행중(A급)", "진행중(일반)", "계약완료", "보류"])

            c_memo = st.text_input("상세 상담 메모")
            if st.form_submit_button("💾 손님 장부에 저장", use_container_width=True):
                new_c = {
                    "등록일자": datetime.now().strftime("%Y-%m-%d"),
                    "구분": c_type, "고객명(업체명)": c_name, "연락처": c_tel,
                    "희망지역": c_reg, "희망평수": c_area, "예산(보/월/매매가)": c_budget,
                    "필수조건(호이스트/전력)": c_req, "진행상태": c_status, "상세메모": c_memo
                }
                df_custs = pd.concat([pd.DataFrame([new_c]), df_custs], ignore_index=True)
                save_sheet_data(df_custs, "customers", "customers.csv")
                st.success("✅ 손님 장부에 등록되었습니다!")
                st.rerun()

    edited_custs = st.data_editor(df_custs, num_rows="dynamic", use_container_width=True, height=400, key="cust_editor")
    if st.button("💾 손님장부 수정사항 저장"):
        save_sheet_data(edited_custs, "customers", "customers.csv")
        st.success("✅ 손님 장부가 저장되었습니다!")
