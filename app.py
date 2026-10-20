import streamlit as st
import pandas as pd
import json
import os
import base64
from io import BytesIO
from datetime import datetime

# ==========================================
# 0. 외부 라이브러리 안전 로드 (에러 100% 방지)
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
    page_title="우리부동산 올인원 통합업무시스템",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-banner {
        background: linear-gradient(90deg, #004ea2 0%, #003775 100%);
        color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 18px;
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
    }
    .main-banner h1 { font-size: 24px; font-weight: 900; margin: 0; color: #ffffff; }
    .main-banner p { font-size: 13.5px; color: #e0f2fe; margin: 4px 0 0 0; }
    .tel-badge {
        background: #0f172a; color: #fde047; padding: 8px 16px; border-radius: 8px;
        font-weight: 800; font-size: 14px; border: 1px solid #334155;
    }
    .section-divider {
        background: #1e293b; color: #fde047; padding: 10px 18px; border-radius: 8px;
        font-weight: 900; font-size: 16px; margin: 28px 0 12px 0;
        border-left: 5px solid #f59e0b;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 9px 16px;
        font-weight: 800; color: #334155; font-size: 13.5px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004ea2 !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 구글 스프레드시트 연동 설정 (3대 시트: properties, customers, hunting)
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
    "등록일자", "구분", "고객명(업체명)", "연락처", "희망지역", "희망평수",
    "예산(보/월/매매가)", "필수조건(호이스트/전력)", "진행상태", "상세메모"
]

HUNT_COLUMNS = [
    "발굴일자", "권역", "상세지번", "건물명/상호", "예상평수", "소유자(건물주)",
    "연락처", "현장상태(공실/만기예정)", "접촉결과", "추후일정/메모"
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

    try:
        pub_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(pub_url)
        df = normalize_dataframe(df, default_cols)
        return df, False
    except Exception:
        pass

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
            st.warning(f"구글 시트 자동 쓰기 확인 필요 (로컬 백업 완료): {e}")
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
# 4. 데이터 로드 및 사이드바 구성
# ==========================================
df_props, gs_connected = load_sheet_data("properties", PROP_COLUMNS, "properties.csv")
df_custs, _ = load_sheet_data("customers", CUST_COLUMNS, "customers.csv")
df_hunts, _ = load_sheet_data("hunting", HUNT_COLUMNS, "hunting_properties.csv")

st.markdown("""
<div class="main-banner">
    <div>
        <h1>🏭 우리부동산 올인원 통합업무시스템 (10대 기능 풀패키지)</h1>
        <p>상단: 핵심 주업무(매물등록·장부·공장블로그·손님CRM) | 하단: 확장 업무(현장물건따기·경매·청약·일상블로그·유튜브·중개툴박스)</p>
    </div>
    <div class="tel-badge">
        📞 매매 032-582-6200 | 임대 032-576-2600
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("🔗 클라우드 & 홈페이지 연동")
    if gs_connected:
        st.success("✅ 구글 스프레드시트 실시간 양방향 연동 중")
    else:
        st.info("ℹ️ 구글시트 읽기/로컬 백업 모드 작동 중")
    
    st.markdown(f"📊 **[구글 스프레드시트 원본 열기 ↗](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit)**")
    st.markdown("🟢 **[우리부동산 네이버 공식 블로그 ↗](https://blog.naver.com/woorirealestate__)**")
    st.divider()
    st.subheader("📥 3대 장부 엑셀(CSV) 백업")
    st.download_button("💾 1. 보유매물 장부 다운로드", data=df_props.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_보유매물_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 2. 찾는손님 장부 다운로드", data=df_custs.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_손님장부_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 3. 임장(물건따기) 다운로드", data=df_hunts.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_물건따기_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

# ==============================================================================
# 🔥 [파트 1] 상단 주업무 4대 탭 (매물등록 / 전체장부 / 블로그·카톡생성 / 손님CRM)
# ==============================================================================
st.markdown('<div class="section-divider">🔥 [주업무 시스템] 매물 등록 · 전체 장부 · 공장 블로그/카톡 생성 · 손님 CRM (홈페이지 실시간 연동)</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ 1. 새 매물 등록 (+사진/홈페이지 연동)",
    "📋 2. 전체 매물 장부 (실시간 수정/삭제)",
    "📝 3. 공장 블로그 & 카톡 브리핑 생성기",
    "👥 4. 찾는 손님 (구해요) CRM 장부"
])

with tab1:
    st.subheader("➕ 신규 공장·창고·신축공장분양 매물 등록")
    st.caption("여기서 저장하면 구글 스프레드시트(`properties` 탭)에 기록되며, **손님용 홈페이지(`index.html`)에 사진과 함께 자동으로 올라갑니다!**")

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
                st.success(f"🎉 [{p_id}] 매물이 구글 스프레드시트와 손님용 홈페이지에 즉시 반영되었습니다!")
            else:
                st.success(f"🎉 [{p_id}] 매물이 저장되었습니다! 아래에서 자동 완성된 네이버 블로그 원고를 바로 복사하세요.")

            st.session_state["last_created_row"] = new_row

    if "last_created_row" in st.session_state:
        st.divider()
        st.subheader("📝 방금 등록한 매물 — 네이버 블로그 포스팅 원고 (우측 상단 복사 아이콘 클릭!)")
        st.code(generate_naver_blog_post(st.session_state["last_created_row"]), language="markdown")

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

    edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True, height=420, key="props_editor")
    if st.button("💾 장부 수정사항 구글시트 & 홈페이지 즉시 반영", type="primary"):
        save_sheet_data(edited_df, "properties", "properties.csv")
        st.success("✅ 수정하신 장부 내용이 구글 스프레드시트와 홈페이지에 반영되었습니다!")
        st.rerun()

with tab3:
    st.subheader("📝 네이버 블로그 원고(송현동 양식) & 카카오톡 브리핑 1초 생성기")
    if len(df_props) == 0:
        st.info("먼저 [1. 새 매물 등록] 탭에서 매물을 등록해 주세요.")
    else:
        prop_options = [f"[{r['매물번호']}] {r['소재지(권역)']} {r['면적']} {r['거래구분']} ({r['가격(보/월)']}) - {r['상세주소(지번)']}" for _, r in df_props.iterrows()]
        selected_idx = st.selectbox("블로그 원고나 카톡 브리핑을 뽑을 매물을 선택하세요", range(len(prop_options)), format_func=lambda i: prop_options[i])
        target_row = df_props.iloc[selected_idx].to_dict()

        col_b1, col_b2 = st.columns([1.4, 1])
        with col_b1:
            st.markdown("#### 🟢 네이버 블로그 가독성 최적화 원고")
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

    edited_custs = st.data_editor(df_custs, num_rows="dynamic", use_container_width=True, height=360, key="cust_editor")
    if st.button("💾 손님장부 수정사항 저장"):
        save_sheet_data(edited_custs, "customers", "customers.csv")
        st.success("✅ 손님 장부가 저장되었습니다!")


# ==============================================================================
# 🛠️ [파트 2] 하단 확장 업무 6대 탭 (기존 5~10번 업무 완벽 복원!)
# ==============================================================================
st.markdown('<div class="section-divider">🛠️ [확장 업무 & 콘텐츠 시스템] 현장 물건따기 · 경매 분석 · 청약/대출 · 일상 블로그 · 드론 영상 · 만능 계산기</div>', unsafe_allow_html=True)

sub_tab5, sub_tab6, sub_tab7, sub_tab8, sub_tab9, sub_tab10 = st.tabs([
    "🎯 5. 현장 임장 / 물건따기 장부",
    "⚖️ 6. 경매 권리·수익률 계산기",
    "🏢 7. 청약 · 신축분양 · 대출 계산",
    "🍽️ 8. 맛집·일상·여행 블로그 생성기",
    "🎬 9. 드론/짐벌 유튜브·릴스 대본",
    "📐 10. 공장 중개 만능 툴박스"
])

# ------------------------------------------
# [탭 5] 현장 임장 / 물건따기 장부 (hunting 시트 연동)
# ------------------------------------------
with sub_tab5:
    st.subheader("🎯 [0번 비밀장부] 현장 임장 및 잠재 매물(물건따기) 발굴 관리")
    st.caption("공단 임장 중 발견한 공실 예정 공장, 건축주 직통 번호, 만기 도래 물건을 기록하고 정식 매물로 전환하기 전에 관리하는 장부입니다. (`hunting` 시트 연동)")
    with st.expander("➕ 현장 발굴 물건 새로 기록하기", expanded=False):
        with st.form("add_hunt_form"):
            hc1, hc2, hc3, hc4 = st.columns(4)
            h_reg = hc1.selectbox("권역", REGIONS)
            h_addr = hc2.text_input("상세 지번 *", placeholder="예: 가좌동 556-12")
            h_bldg = hc3.text_input("건물명 / 현재 상호", placeholder="예: (주)태형금속")
            h_area = hc4.text_input("예상 평수", placeholder="예: 약 120평")

            hc5, hc6, hc7, hc8 = st.columns(4)
            h_owner = hc5.text_input("소유자(건축주) 성함")
            h_tel = hc6.text_input("소유자 연락처")
            h_state = hc7.selectbox("현장 상태", ["만기 도래 예정", "현재 공실(현수막)", "자가 사용중(매도가능성)", "신축 공사중"])
            h_res = hc8.selectbox("접촉 결과", ["1차 명함 전달", "통화 완료(긍정)", "통화 완료(보류)", "정식 매물 전환 완료"])

            h_memo = st.text_input("추후 일정 및 현장 특이사항 메모")
            if st.form_submit_button("💾 물건따기 장부에 저장", use_container_width=True):
                new_h = {
                    "발굴일자": datetime.now().strftime("%Y-%m-%d"),
                    "권역": h_reg, "상세지번": h_addr, "건물명/상호": h_bldg, "예상평수": h_area,
                    "소유자(건물주)": h_owner, "연락처": h_tel, "현장상태(공실/만기예정)": h_state,
                    "접촉결과": h_res, "추후일정/메모": h_memo
                }
                df_hunts = pd.concat([pd.DataFrame([new_h]), df_hunts], ignore_index=True)
                save_sheet_data(df_hunts, "hunting", "hunting_properties.csv")
                st.success("✅ 현장 물건따기 장부에 저장되었습니다!")
                st.rerun()

    edited_hunts = st.data_editor(df_hunts, num_rows="dynamic", use_container_width=True, height=340, key="hunt_editor")
    if st.button("💾 물건따기 장부 수정사항 저장"):
        save_sheet_data(edited_hunts, "hunting", "hunting_properties.csv")
        st.success("✅ 물건따기 장부가 업데이트되었습니다!")

# ------------------------------------------
# [탭 6] 공장·창고 경매 권리분석 & 수익률 계산기
# ------------------------------------------
with sub_tab6:
    st.subheader("⚖️ 공장·창고 경매 낙찰가 산정 및 수익률 시뮬레이터")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown("##### 1) 경매 물건 기본 정보")
        auc_case = st.text_input("사건번호 / 소재지", value="2026타경 10245 (인천 가좌동 공장)")
        auc_appraise = st.number_input("감정가 (만 원)", value=200000, step=5000)
        auc_bid = st.number_input("예상 입찰가 (만 원)", value=150000, step=1000)
        auc_land_py = st.number_input("대지면적 (평)", value=200.0, step=10.0)
    with ac2:
        st.markdown("##### 2) 부대비용 및 인수금액")
        auc_tax_rate = st.number_input("취득세율 (%)", value=4.6, step=0.1)
        auc_evict_cost = st.number_input("예상 명도비 / 체납관리비 (만 원)", value=1500, step=100)
        auc_repair_cost = st.number_input("호이스트·에폭시 수리비 (만 원)", value=2000, step=500)
        auc_loan_ratio = st.slider("경락잔금대출 비율 (%)", 50, 85, 75)
    with ac3:
        st.markdown("##### 3) 예상 임대 수익 설정")
        auc_interest_rate = st.number_input("대출 금리 (연 %)", value=4.5, step=0.1)
        auc_exp_dep = st.number_input("예상 임대 보증금 (만 원)", value=5000, step=500)
        auc_exp_rent = st.number_input("예상 월 임대료 (만 원)", value=750, step=50)

    bid_ratio = (auc_bid / auc_appraise * 100) if auc_appraise > 0 else 0
    acq_tax = round(auc_bid * (auc_tax_rate / 100))
    total_cost = auc_bid + acq_tax + auc_evict_cost + auc_repair_cost
    loan_amt = round(auc_bid * (auc_loan_ratio / 100))
    real_invest = total_cost - loan_amt - auc_exp_dep
    monthly_interest = round((loan_amt * (auc_interest_rate / 100)) / 12)
    net_monthly_cash = auc_exp_rent - monthly_interest
    annual_roi = ((net_monthly_cash * 12) / real_invest * 100) if real_invest > 0 else 0

    st.info(f"""
    📊 **[ {auc_case} ] 경매 수익 분석 리포트**
    * **낙찰가율**: `{bid_ratio:.1f}%` (평당 낙찰단가: 약 `{round(auc_bid/auc_land_py if auc_land_py else 0):,}`만 원/평)
    * **총 취득원가**: `{total_cost:,}만 원` (입찰가 {auc_bid:,}만 + 취득세 {acq_tax:,}만 + 명도/수리비 {auc_evict_cost+auc_repair_cost:,}만)
    * **경락잔금대출({auc_loan_ratio}%)**: `{loan_amt:,}만 원` (월 이자 약 `{monthly_interest:,}만 원`)
    * **실제 자기자본(실투자금)**: **`{real_invest:,}만 원`** (임대보증금 {auc_exp_dep:,}만 원 공제 후)
    * **월 순수익**: **`{net_monthly_cash:,}만 원`** ➔ **연환산 수익률(ROE): `{annual_roi:.2f}%`**
    """)

# ------------------------------------------
# [탭 7] 청약 · 신축공장분양 · 주택/시설자금 대출 분석기
# ------------------------------------------
with sub_tab7:
    st.subheader("🏢 신축공장분양 실입주금 & 공공·특별공급 청약 자금 계산기")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("#### 🏗️ 신축공장분양 vs 월세 임차 비교 시뮬레이터")
        b_price = st.number_input("총 분양가 / 매매가 (만 원)", value=185000, step=5000)
        b_loan_pct = st.slider("1금융권 시설자금 대출 한도 (%)", 60, 85, 80)
        b_rate = st.number_input("기업 시설자금 금리 (연 %)", value=4.2, step=0.1)
        curr_rent = st.number_input("현재 내고 계신 공장 월세 (만 원)", value=550, step=50)

        b_loan = round(b_price * (b_loan_pct / 100))
        b_self = b_price - b_loan
        b_month_int = round((b_loan * (b_rate / 100)) / 12)
        diff_rent = curr_rent - b_month_int

        st.success(f"""
        💡 **[손님 설득용 브리핑 요약]**
        * **총 분양가**: `{b_price:,}만 원`
        * **대출 가능액({b_loan_pct}%)**: `{b_loan:,}만 원`
        * **필요 실입주금(자부담)**: **`{b_self:,}만 원`**
        * **월 예상 이자**: **`{b_month_int:,}만 원`** (현재 월세 {curr_rent:,}만 원 대비 매월 **`{diff_rent:,}만 원`** 차이로 내 자가 공장 마련!)
        """)

    with sc2:
        st.markdown("#### 🏠 수도권 주요 공공분양·특별공급 청약 자금 플래너")
        apt_name = st.text_input("관심 단지명", value="부천대장 / 계양 / 검암 / 고덕강일 공공분양")
        apt_price = st.number_input("예상 분양가 (만 원)", value=52000, step=1000)
        apt_cash = st.number_input("현재 보유 가용 자금 (만 원)", value=18000, step=1000)
        apt_ltv = st.slider("예상 주택담보/정책대출 비율 (%)", 40, 80, 70)

        apt_loan = round(apt_price * (apt_ltv / 100))
        apt_need = apt_price - apt_loan
        apt_surplus = apt_cash - apt_need
        st.warning(f"""
        📌 **[ {apt_name} ] 자금 계획표**
        * **계약금(10%)**: `{round(apt_price*0.1):,}만 원` / **중도금(60%)**: `{round(apt_price*0.6):,}만 원` / **잔금(30%)**: `{round(apt_price*0.3):,}만 원`
        * **예상 대출액({apt_ltv}%)**: `{apt_loan:,}만 원`
        * **필요 자기자본**: `{apt_need:,}만 원` ➔ 현재 가용자금 대비 **`{apt_surplus:+,}만 원`** ({"자금 충분" if apt_surplus>=0 else "추가 자금 확보 필요"})
        """)

# ------------------------------------------
# [탭 8] 김소장 맛집 · 카페 · 일상 · 여행 블로그 원고 생성기
# ------------------------------------------
with sub_tab8:
    st.subheader("🍽️ 김소장 맛집 · 일상 · 여행 블로그 포스팅 1초 생성기")
    st.caption("부동산 매물 글 사이에 맛집·일상 글을 섞어주어야 블로그 지수(체류시간·이웃소통)가 건강하게 유지됩니다.")
    lc1, lc2, lc3 = st.columns(3)
    l_cat = lc1.selectbox("포스팅 주제", ["인천/부천 로컬 맛집 리뷰", "분위기 좋은 카페/디저트", "주말 여행/나들이 기록", "현장 중개 일상 & 운동 기록"])
    l_place = lc2.text_input("방문 장소 / 상호명", placeholder="예: 청라 OO식당 / 역곡 OO카페")
    l_menu = lc3.text_input("대표 메뉴 / 핵심 포인트", placeholder="예: 직화 제육볶음, 넓은 주차장, 가성비 최고")
    l_impression = st.text_area("솔직 후기 및 한줄평", placeholder="예: 현장 임장 마치고 들렀는데 불향이 제대로 살아있고 반찬이 깔끔해서 든든하게 한 끼 해결했습니다.")

    if st.button("✨ 김소장 스타일 일상/맛집 블로그 원고 생성", use_container_width=True):
        life_post = f"""안녕하세요! 인천 산업용 부동산 현장을 발로 뛰는 김소장입니다. 😊
오늘 포스팅은 바쁜 현장 일정 중에 다녀온 【 {l_place} 】 ({l_cat}) 솔직 방문 후기를 남겨보려고 합니다.

📍 [ {l_place} 방문 핵심 요약 ]
• 위치 및 주차 : 접근성이 편리하고 주차 공간이 여유로워 방문하기 수월했습니다.
• 오늘의 픽(Pick) : {l_menu}

---------------------------------------------------------
[ 📸 외관 및 매장 입구 사진 넣는 곳 ]
깔끔하고 정돈된 외관이 눈에 띄는 {l_place}입니다. 평소 이 근처 지날 때마다 눈여겨보던 곳인데 드디어 방문하게 되었네요.

[ 📸 메인 메뉴 / 현장 상세 사진 3~4장 넣는 곳 ]
드디어 주문한 【 {l_menu} 】이(가) 나왔습니다!
비주얼부터 군침이 돌았는데, 직접 맛보니 기대 이상으로 만족스러웠습니다.
{l_impression}

[ 📸 마무리 및 영수증/명함 사진 넣는 곳 ]
---------------------------------------------------------

가끔 이렇게 맛있는 음식과 함께 에너지를 충전해야 또 현장에서 대표님들께 더 좋은 공장·창고 매물을 찾아드릴 수 있는 것 같습니다.
인천·부천 인근에서 {l_menu} 생각나실 때 【 {l_place} 】 한 번쯤 들러보시길 추천해 드립니다!

오늘도 활기차고 행복한 하루 보내세요! 감사합니다. 🙏

#{l_place.replace(' ','')} #인천맛집 #청라맛집 #부천맛집 #김소장일상 #우리부동산 #내돈내산후기
"""
        st.code(life_post, language="markdown")

# ------------------------------------------
# [탭 9] 드론/짐벌 영상 촬영 콘티 & 유튜브/릴스 대본 생성기
# ------------------------------------------
with sub_tab9:
    st.subheader("🎬 드론(Faith 2 Pro) & 짐벌(Osmo 7P) 촬영 콘티 · 쇼츠/릴스 대본 생성기")
    vc1, vc2, vc3 = st.columns(3)
    v_loc = vc1.selectbox("촬영 매물 지역", REGIONS)
    v_py = vc2.text_input("촬영 매물 평수 및 거래", value="가좌동 120평 단독공장 임대")
    v_key = vc3.text_input("최대 셀링 포인트", value="40ft 츄레라 회전 가능 단독마당 + 호이스트 5톤")

    if st.button("🎥 현장 촬영 컷 리스트 & 45초 쇼츠 대본 뽑기", use_container_width=True):
        video_script = f"""🎬 [ {v_py} ] 드론 & 짐벌 5단계 촬영 체크리스트 (CapCut 편집용)
1. [드론 오프닝 - 5초] 상공 40m에서 공장 지붕과 진입 도로 폭이 한눈에 보이도록 천천히 하강(Tilt-down) 샷
2. [짐벌 진입로 - 8초] 도로에서 마당으로 걸어 들어가며 '{v_key}' 스케일 보여주는 광각(0.5x) 워킹 샷
3. [짐벌 내부전경 - 10초] 출입문 열리는 순간부터 1층 바닥 에폭시 상태와 천장 처마 층고, 호이스트 레일 패닝 샷
4. [짐벌 부대시설 - 8초] 수전반(동력 kW) 클로즈업 ➔ 2층 사무실 계단 및 창문 뷰
5. [아웃트로 - 5초] 공장 정면 풀샷 배경으로 우리부동산 연락처 자막 삽입

---------------------------------------------------------
🎙️ [ 릴스 / 유튜브 쇼츠 더빙 대본 (40초 컷) ]
(0~5초 / 강렬한 후킹)
"인천 {v_loc}에서 {v_key} 갖춘 {v_py}, 시세보다 저렴하게 나왔습니다!"

(5~20초 / 진입로 및 마당 브리핑)
"드론 뷰로 보시는 것처럼 진입 도로가 시원하게 뚫려 있어서 대형 화물차 상하차 걱정 전혀 없고요."

(20~35초 / 내부 제원 브리핑)
"내부로 들어오시면 높은 층고에 호이스트와 동력까지 이미 완비되어 있어서 초기 시설비 수천만 원 그대로 아끼고 바로 기계만 들여오시면 됩니다."

(35~45초 / 클로징 CTA)
"상세 임대료와 위치가 궁금하시다면 지금 바로 화면 상단 우리부동산으로 연락 주세요!"
"""
        st.code(video_script, language="markdown")

# ------------------------------------------
# [탭 10] 공장 중개 만능 툴박스 (평↔㎡, 동력kW, 중개보수, 에폭시 견적)
# ------------------------------------------
with sub_tab10:
    st.subheader("📐 공장 전문 중개사 만능 계산기 4종")
    tc1, tc2, tc3, tc4 = st.columns(4)

    with tc1:
        st.markdown("##### 1) 면적 변환 (㎡ ↔ 평)")
        in_m2 = st.number_input("건축물대장 면적 (㎡)", value=330.58, step=10.0)
        st.metric("평수 환산 결과", f"{in_m2 / 3.3058:.1f} 평")
        in_py = st.number_input("전용 평수 (평)", value=100.0, step=10.0)
        st.metric("제곱미터(㎡) 결과", f"{in_py * 3.3058:.2f} ㎡")

    with tc2:
        st.markdown("##### 2) 산업용中개보수 계산 (0.9%)")
        f_deal_type = st.radio("거래유형", ["임대(월세)", "매매/분양"], horizontal=True)
        if f_deal_type == "임대(월세)":
            dep_m = st.number_input("보증금 (만 원)", value=3000, step=500)
            rent_m = st.number_input("월세 (만 원)", value=300, step=10)
            trans_amt = dep_m + (rent_m * 100)
        else:
            sale_m = st.number_input("매매/분양가 (만 원)", value=150000, step=5000)
            trans_amt = sale_m
        fee_rate = st.number_input("요율 (%)", value=0.9, step=0.1)
        fee_res = round(trans_amt * (fee_rate / 100))
        st.metric("최대 중개보수 (부가세별도)", f"{fee_res:,} 만 원", f"환산금액: {trans_amt:,}만 원")

    with tc3:
        st.markdown("##### 3) 한전 동력(kW) 증설비 추산")
        curr_kw = st.number_input("현재 계약전력 (kW)", value=20, step=10)
        target_kw = st.number_input("필요 계약전력 (kW)", value=100, step=10)
        add_kw = max(0, target_kw - curr_kw)
        kepco_fee = round(add_kw * 9.8) # 한전 시설부담금 개략치
        elec_work = round(add_kw * 12.0) # 내선 및 수전설비 개략치
        st.metric(f"증설 필요량 (+{add_kw}kW)", f"약 {kepco_fee + elec_work:,} 만 원", f"한전불입금 약 {kepco_fee:,}만 + 전기공사비")

    with tc4:
        st.markdown("##### 4) 공장 바닥 에폭시 시공 견적")
        ep_py = st.number_input("시공 바닥 면적 (평)", value=75, step=5)
        ep_type = st.selectbox("시공 종류", ["일반 코팅 에폭시 (평당 약 3.5만)", "고강도 라이닝 에폭시 (평당 약 8만)"])
        unit_ep = 3.5 if "코팅" in ep_type else 8.0
        st.metric("예상 에폭시 시공비", f"약 {round(ep_py * unit_ep):,} 만 원", "바닥 면처리 상태에 따라 변동")
