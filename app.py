import streamlit as st
import pandas as pd
import json
import os
import re
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
# 1. 기본 페이지 설정 및 커스텀 CSS
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
        color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 16px;
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
        box-shadow: 0 4px 15px rgba(0, 78, 162, 0.2);
    }
    .main-banner h1 { font-size: 23px; font-weight: 900; margin: 0; color: #ffffff; }
    .main-banner p { font-size: 13px; color: #e0f2fe; margin: 4px 0 0 0; }
    .tel-badge {
        background: #0f172a; color: #fde047; padding: 8px 16px; border-radius: 8px;
        font-weight: 800; font-size: 14px; border: 1px solid #334155;
    }
    .section-divider {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        color: #fde047; padding: 10px 18px; border-radius: 8px;
        font-weight: 900; font-size: 15.5px; margin: 24px 0 12px 0;
        border-left: 5px solid #f59e0b;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 9px 15px;
        font-weight: 800; color: #334155; font-size: 13.5px; border: 1px solid #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004ea2 !important; color: white !important; border-color: #004ea2 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 구글 스프레드시트 연동 설정 (3대 시트 완벽 연동)
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
    "발굴일자", "권역", "상세지번", "건물명/상호", "예상평수", "예상금액",
    "동력/호이스트", "소유자(건물주)", "연락처", "현장상태(공실/만기예정)", "접촉결과", "추후일정/메모"
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
# 3. 김소장 스타일 네이버 블로그 원고 자동 생성기 (송현동 양식 100%)
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
# 4. 데이터 로드 및 사이드바 (비밀번호 563011 보안 지원)
# ==========================================
df_props, gs_connected = load_sheet_data("properties", PROP_COLUMNS, "properties.csv")
df_custs, _ = load_sheet_data("customers", CUST_COLUMNS, "customers.csv")
df_hunts, _ = load_sheet_data("hunting", HUNT_COLUMNS, "hunting_properties.csv")

st.markdown("""
<div class="main-banner">
    <div>
        <h1>🏭 우리부동산 올인원 통합업무시스템 (10대 고도화 풀패키지)</h1>
        <p>주력 권역(석남·가좌·송림·송현·도화·원창·경서동) · 구글시트 & 홈페이지 자동연동 · 임장 복붙 파서 · 공장/아파트 경매 · 수도권 청약</p>
    </div>
    <div class="tel-badge">
        📞 매매 032-582-6200 | 임대 032-576-2600
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("🔒 관리자 보안 및 연동 상태")
    admin_pw = st.text_input("업무시스템 잠금해제", value="563011", type="password")
    if admin_pw != "563011":
        st.warning("비밀번호 `563011`을 입력해 주세요.")
        st.stop()

    if gs_connected:
        st.success("✅ 구글 스프레드시트 실시간 양방향 연동 중")
    else:
        st.info("ℹ️ 구글시트 읽기/로컬 백업 모드 작동 중")
    
    st.markdown(f"📊 **[구글 스프레드시트 원본 열기 ↗](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit)**")
    st.markdown("🟢 **[우리부동산 네이버 공식 블로그 ↗](https://blog.naver.com/woorirealestate__)**")
    st.divider()
    st.subheader("📥 3대 장부 엑셀(CSV) 원클릭 백업")
    st.download_button("💾 1. 보유매물 장부 다운로드", data=df_props.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_보유매물_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 2. 찾는손님 장부 다운로드", data=df_custs.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_손님장부_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 3. 임장(물건따기) 다운로드", data=df_hunts.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_물건따기_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)


# ==============================================================================
# 🔥 [파트 1] 상단 주업무 3대 시스템 (새매물등록 + 전체통합장부 + 공장블로그/카톡 + 손님CRM)
# ==============================================================================
st.markdown('<div class="section-divider">🔥 [상단 주업무 시스템] 1. 새 매물 등록(+사진) · 2. 전체 매물 장부 · 3. 공장 블로그 & 카톡 브리핑 · 4. 찾는 손님 CRM</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ 1. 새 매물 등록 (+사진/홈페이지 연동)",
    "📋 2. 전체 매물 통합장부 (수정/역매칭)",
    "📝 3. 공장 블로그(송현동 양식) & 카톡 브리핑",
    "👥 4. 찾는 손님 (구해요) CRM & 매물매칭"
])

# ------------------------------------------
# [1번 시스템] 새 매물 등록 (+사진 업로드 + 호이스트 선택형 + 홈페이지 자동 연동)
# ------------------------------------------
with tab1:
    st.subheader("➕ 신규 공장·창고·신축공장분양 매물 등록")
    st.caption("여기서 등록하시면 구글 스프레드시트(`properties` 탭)에 즉시 저장되며, **손님용 홈페이지(`index.html`)에 사진과 함께 자동으로 올라갑니다!**")

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
        # ★ 요청하신 호이스트 선택형 구현
        p_has_hoist = c12.selectbox("호이스트 유무", ["호이스트 있음", "호이스트 없음"])
        p_hoist_detail = c13.text_input("호이스트 상세", value="호이스트 2.8톤 완비")
        p_truck = c14.selectbox("차량 진입 / 도로 조건", [
            "40ft 츄레라 진입 가능 (광폭도로)",
            "5t~11t 윙바디 작업 수월 (8m~10m 도로)",
            "1t~2.5t 화물차 문앞 접안 (6m 도로)"
        ])
        p_movein = c15.text_input("입주 가능 시기", value="즉시 입주 / 협의")

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

            hoist_final = p_hoist_detail if "있음" in p_has_hoist else "호이스트 없음"

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
                "호이스트": hoist_final,
                "대형차량": p_truck,
                "추천업종": p_biz,
                "입주가능일": p_movein,
                "용도지역/구조": "일반공업지역 / 철골조",
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

# ------------------------------------------
# [2번 시스템] 전체 매물 통합장부 (실시간 수정 및 동기화)
# ------------------------------------------
with tab2:
    st.subheader(f"📋 전체 보유 매물 통합장부 (총 {len(df_props)}건)")
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    sel_reg = f_col1.selectbox("권역 필터", ["전체"] + REGIONS)
    sel_deal = f_col2.selectbox("거래구분 필터", ["전체"] + DEAL_TYPES)
    search_kw = f_col3.text_input("🔍 초고속 장부 검색 (실제지번, 건물주 연락처, 매물번호, 특징)")

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

# ------------------------------------------
# [3번 시스템] 공장 블로그(송현동 양식) & 손님 전송용 카카오톡 1초 브리핑
# ------------------------------------------
with tab3:
    st.subheader("📝 네이버 블로그 원고(송현동 양식) & 카카오톡 브리핑 생성기")
    st.caption("등록된 매물을 선택하면 블로그 원고와 손님 전송용 카톡 브리핑을 여러 개 골라서 확인하고 복사할 수 있습니다.")
    if len(df_props) == 0:
        st.info("먼저 [1. 새 매물 등록] 탭에서 매물을 등록해 주세요.")
    else:
        prop_options = [f"[{r['매물번호']}] {r['소재지(권역)']} {r['면적']} {r['거래구분']} ({r['가격(보/월)']}) - {r['상세주소(지번)']}" for _, r in df_props.iterrows()]
        
        # ★ 여러 매물을 선택할 수 있도록 multiselect 지원
        selected_indices = st.multiselect("원고를 생성할 매물을 선택하세요 (여러 개 선택 가능)", range(len(prop_options)), default=[0] if len(prop_options)>0 else [], format_func=lambda i: prop_options[i])

        for idx in selected_indices:
            target_row = df_props.iloc[idx].to_dict()
            st.markdown(f"---  \n### 📌 [매물번호 {target_row.get('매물번호','')}] {target_row.get('매물제목','')}")
            
            col_b1, col_b2 = st.columns([1.4, 1])
            with col_b1:
                st.markdown("#### 🟢 네이버 블로그 가독성 최적화 원고 (송현동 양식)")
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

# ------------------------------------------
# [4번 시스템] 찾는 손님 (구해요) CRM 장부 + 자동 매물 매칭
# ------------------------------------------
with tab4:
    st.subheader("👥 찾는 손님 (구해요) CRM 장부 & 보유매물 자동 매칭")
    with st.expander("➕ 새 손님(구해요 문의) 등록하기", expanded=False):
        with st.form("add_cust_form"):
            cc1, cc2, cc3, cc4 = st.columns(4)
            c_type = cc1.selectbox("구분", ["공장임대 구함", "공장매매 구함", "신축공장분양 문의", "매물 내놓기(접수)"])
            c_name = cc2.text_input("고객명 / 업체명 *")
            c_tel = cc3.text_input("연락처 *")
            c_reg = cc4.text_input("희망 지역 (예: 석남, 가좌, 송현)", value="석남동, 가좌동")

            cc5, cc6, cc7, cc8 = st.columns(4)
            c_area = cc5.text_input("희망 평수 (숫자만 입력시 자동매칭)", value="80")
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

    edited_custs = st.data_editor(df_custs, num_rows="dynamic", use_container_width=True, height=320, key="cust_editor")
    if st.button("💾 손님장부 수정사항 저장"):
        save_sheet_data(edited_custs, "customers", "customers.csv")
        st.success("✅ 손님 장부가 저장되었습니다!")

    if len(df_custs) > 0 and len(df_props) > 0:
        st.divider()
        st.markdown("##### 🎯 선택한 손님에게 딱 맞는 보유 매물 자동 추천 (역매칭)")
        cust_list = [f"{r['고객명(업체명)']} ({r['연락처']}) - 희망: {r['희망지역']} / {r['희망평수']}평 / {r['필수조건(호이스트/전력)']}" for _, r in df_custs.iterrows()]
        sel_c_idx = st.selectbox("매칭할 손님을 선택하세요", range(len(cust_list)), format_func=lambda i: cust_list[i])
        c_row = df_custs.iloc[sel_c_idx]
        c_py_digits = ''.join(filter(str.isdigit, str(c_row.get("희망평수", "0"))))
        c_py = int(c_py_digits) if c_py_digits else 0

        matched_rows = []
        for _, p_r in df_props.iterrows():
            p_py_digits = ''.join(filter(str.isdigit, str(p_r.get("면적", "0"))))
            p_py = int(p_py_digits) if p_py_digits else 0
            if c_py == 0 or (c_py * 0.65 <= p_py <= c_py * 1.45):
                matched_rows.append(p_r)

        if matched_rows:
            st.dataframe(pd.DataFrame(matched_rows)[["매물번호", "거래구분", "소재지(권역)", "상세주소(지번)", "면적", "가격(보/월)", "호이스트", "동력", "임대인연락처"]], use_container_width=True)
        else:
            st.info("희망 평수(±35%) 범위에 해당하는 매물이 없습니다.")


# ==============================================================================
# 🛠️ [파트 2] 하단 확장 업무 6대 시스템 (현장임장 복붙파서 · 공장/아파트 경매 · 수도권 청약 · 일상블로그 · 영상대본 · 툴박스)
# ==============================================================================
st.markdown('<div class="section-divider">🛠️ [하단 확장 업무 6대 시스템] 5. 현장 임장(복붙 자동추출) · 6. 공장/아파트 경매 · 7. 수도권 청약/분양 · 8. 일상 블로그 · 9. 드론 대본 · 10. 만능 툴박스</div>', unsafe_allow_html=True)

sub_tab5, sub_tab6, sub_tab7, sub_tab8, sub_tab9, sub_tab10 = st.tabs([
    "🎯 5. 현장 임장 / 물건따기 (복붙 탑재)",
    "⚖️ 6. 인천공장 & 수도권아파트 경매",
    "🏢 7. 수도권 청약 보드 & 신축분양 대출",
    "🍽️ 8. 김소장 맛집·일상·여행 블로그",
    "🎬 9. 드론(Faith2) & 짐벌 영상 대본",
    "📐 10. 공장 중개 만능 툴박스 (에폭시 등)"
])

# ------------------------------------------
# [5번 시스템] 현장 임장 / 물건따기 장부 (복붙 자동 파서 + 1번 정식 매물 1초 승격 완벽 복원!)
# ------------------------------------------
with sub_tab5:
    st.subheader("🎯 [0번 비밀장부] 현장 임장 및 잠재 매물(물건따기) 발굴 관리 (`hunting` 시트 연동)")
    
    st.markdown("##### 📋 [고도화 기능 1] 현장 메모 / 카톡 / 건축물대장 텍스트 복사·붙여넣기 자동 추출기")
    paste_col1, paste_col2 = st.columns([2, 1])
    with paste_col1:
        raw_paste = st.text_area(
            "현장에서 폰에 대충 적은 메모나 카톡, 건축물대장 텍스트를 여기에 붙여넣기(Ctrl+V) 하세요!",
            placeholder="예시: 가좌동 556-12 태형금속 약 120평 보증금 3000 / 월 300 호이스트 5톤 동력 80kW 김사장님 010-1234-5678 내년 1월 만기예정",
            height=95
        )
    with paste_col2:
        st.caption("💡 붙여넣고 아래 버튼을 누르면 권역, 지번, 평수, 전화번호, 동력을 자동으로 뽑아 아래 입력칸에 채워줍니다.")
        if st.button("🪄 붙여넣은 텍스트 자동 분석·채우기", use_container_width=True):
            parsed_reg = "가좌동"
            for r_name in REGIONS:
                if r_name[:2] in raw_paste:
                    parsed_reg = r_name
                    break
            jibun_m = re.search(r'([가-힣]+동\s*\d+(?:-\d+)?|\b\d{1,4}-\d{1,4}\b)', raw_paste)
            phone_m = re.search(r'(01[016789]-?\d{3,4}-?\d{4}|032-?\d{3,4}-?\d{4})', raw_paste)
            py_m = re.search(r'(\d+)\s*평', raw_paste)
            m2_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:㎡|m2|제곱)', raw_paste)
            kw_m = re.search(r'(\d+)\s*(?:kw|kW|키로)', raw_paste)

            st.session_state["h_p_reg"] = parsed_reg
            st.session_state["h_p_addr"] = jibun_m.group(0) if jibun_m else ""
            st.session_state["h_p_tel"] = phone_m.group(0) if phone_m else ""
            if py_m:
                st.session_state["h_p_py"] = f"{py_m.group(1)}평"
            elif m2_m:
                st.session_state["h_p_py"] = f"{round(float(m2_m.group(1))/3.3058)}평"
            else:
                st.session_state["h_p_py"] = ""
            st.session_state["h_p_spec"] = f"동력 {kw_m.group(1)}kW" if kw_m else ("호이스트 있음" if "호이스트" in raw_paste else "")
            st.session_state["h_p_memo"] = raw_paste.strip()
            st.success("✅ 텍스트에서 지번·평수·연락처를 자동으로 추출해 아래 입력칸에 채웠습니다!")

    with st.form("add_hunt_form"):
        hc1, hc2, hc3, hc4 = st.columns(4)
        def_reg = st.session_state.get("h_p_reg", "가좌동")
        reg_idx = REGIONS.index(def_reg) if def_reg in REGIONS else 0
        h_reg = hc1.selectbox("권역", REGIONS, index=reg_idx)
        h_addr = hc2.text_input("상세 지번 *", value=st.session_state.get("h_p_addr", ""), placeholder="예: 가좌동 556-12")
        h_bldg = hc3.text_input("건물명 / 현재 상호", placeholder="예: (주)태형정밀")
        h_area = hc4.text_input("예상 평수", value=st.session_state.get("h_p_py", ""), placeholder="예: 120평")

        hc5, hc6, hc7, hc8 = st.columns(4)
        h_price = hc5.text_input("예상 금액 (보/월/매매)", placeholder="예: 3,000 / 300")
        h_spec = hc6.text_input("동력 / 호이스트", value=st.session_state.get("h_p_spec", ""), placeholder="예: 80kW / 호이스트 5톤")
        h_owner = hc7.text_input("소유자(건물주) 성함")
        h_tel = hc8.text_input("소유자 연락처", value=st.session_state.get("h_p_tel", ""))

        hc9, hc10, hc11 = st.columns([1, 1, 2])
        h_state = hc9.selectbox("현장 상태", ["만기 도래 예정", "현재 공실(현수막)", "자가 사용중(매도가능성)", "신축 공사중"])
        h_res = hc10.selectbox("접촉 결과", ["1차 명함 전달", "통화 완료(긍정)", "통화 완료(보류)", "정식 매물 전환 완료"])
        h_memo = hc11.text_input("추후 일정 및 현장 메모", value=st.session_state.get("h_p_memo", ""))

        if st.form_submit_button("💾 물건따기 장부(`hunting` 시트)에 저장", use_container_width=True):
            new_h = {
                "발굴일자": datetime.now().strftime("%Y-%m-%d"),
                "권역": h_reg, "상세지번": h_addr, "건물명/상호": h_bldg, "예상평수": h_area,
                "예상금액": h_price, "동력/호이스트": h_spec, "소유자(건물주)": h_owner,
                "연락처": h_tel, "현장상태(공실/만기예정)": h_state, "접촉결과": h_res, "추후일정/메모": h_memo
            }
            df_hunts = pd.concat([pd.DataFrame([new_h]), df_hunts], ignore_index=True)
            save_sheet_data(df_hunts, "hunting", "hunting_properties.csv")
            st.success("✅ 현장 물건따기 장부에 저장되었습니다!")
            st.rerun()

    edited_hunts = st.data_editor(df_hunts, num_rows="dynamic", use_container_width=True, height=300, key="hunt_editor")
    
    h_btn_col1, h_btn_col2 = st.columns(2)
    with h_btn_col1:
        if st.button("💾 물건따기 장부 수정사항 저장", use_container_width=True):
            save_sheet_data(edited_hunts, "hunting", "hunting_properties.csv")
            st.success("✅ 물건따기 장부가 업데이트되었습니다!")

    if len(df_hunts) > 0:
        st.divider()
        st.markdown("##### 🚀 [고도화 기능 2] 임장 물건 내역 복사하기 & 1번 정식 매물(`properties`)로 1초 승격")
        hunt_opts = [f"[{r['권역']} {r['상세지번']}] {r['건물명/상호']} ({r['예상평수']} / {r['예상금액']}) - {r['현장상태(공실/만기예정)']}" for _, r in df_hunts.iterrows()]
        sel_h_idx = st.selectbox("복사하거나 정식 매물로 전환할 임장 물건을 선택하세요", range(len(hunt_opts)), format_func=lambda i: hunt_opts[i])
        h_row = df_hunts.iloc[sel_h_idx]

        hc_left, hc_right = st.columns([1.5, 1])
        with hc_left:
            hunt_copy_str = f"[현장임장 기록] 인천 {h_row['권역']} {h_row['상세지번']} ({h_row['건물명/상호']}) | 평수: {h_row['예상평수']} | 금액: {h_row['예상금액']} | 설비: {h_row['동력/호이스트']} | 소유주: {h_row['소유자(건물주)']} ({h_row['연락처']}) | 메모: {h_row['추후일정/메모']}"
            st.code(hunt_copy_str, language="text")
        with hc_right:
            if st.button("🚀 이 임장 물건을 [1번 정식 매물 장부 & 홈페이지]로 즉시 승격 등록!", type="primary", use_container_width=True):
                promoted_row = {
                    "매물번호": f"W-{101 + len(df_props)}",
                    "등록일자": datetime.now().strftime("%Y-%m-%d"),
                    "홈페이지노출": "공개",
                    "거래구분": "공장임대",
                    "소재지(권역)": h_row.get("권역", "가좌동"),
                    "상세주소(지번)": h_row.get("상세지번", ""),
                    "매물제목": f"인천 {h_row.get('권역','')} {h_row.get('예상평수','')} 단독 공장·창고 ({h_row.get('동력/호이스트','')})",
                    "가격(보/월)": h_row.get("예상금액", "협의"),
                    "면적": h_row.get("예상평수", "80평"),
                    "사무실평수": "0평",
                    "층고": "층고 8M",
                    "동력": h_row.get("동력/호이스트", "50kW"),
                    "호이스트": h_row.get("동력/호이스트", "호이스트 완비"),
                    "대형차량": "대형 화물차 진입 수월",
                    "추천업종": "일반제조·조립",
                    "입주가능일": "즉시 / 협의",
                    "용도지역/구조": "일반공업지역 / 철골조",
                    "사용승인일": "",
                    "임대인(건물주)": h_row.get("소유자(건물주)", ""),
                    "임대인연락처": h_row.get("연락처", ""),
                    "특징메모": h_row.get("추천일정/메모", ""),
                    "대표사진": ""
                }
                df_props = pd.concat([pd.DataFrame([promoted_row]), df_props], ignore_index=True)
                save_sheet_data(df_props, "properties", "properties.csv")
                st.success("🎉 정식 매물 장부(`properties`)와 손님용 홈페이지로 즉시 승격 등록되었습니다!")
                st.rerun()

# ------------------------------------------
# [6번 시스템] 인천 공장·창고 및 수도권 아파트 경매 분석 & 수익률 시뮬레이터 (완벽 복원!)
# ------------------------------------------
with sub_tab6:
    st.subheader("⚖️ 인천 핵심 공장·창고 & 수도권 아파트 주요 경매 물건 보드 + 수익률 시뮬레이터")
    
    AUCTION_PRESETS = [
        {"구분": "🏭 인천공장", "사건번호": "2025타경 51204", "소재지": "인천 서구 가좌동 482-X (일반공업지역 단독공장)", "감정가(만)": 245000, "최저가(만)": 171500, "평수(평)": 210, "특징": "1회 유찰(70%) / 호이스트 5톤 2기 및 수전설비 150kW 포함 일괄매각 / 유치권 신고 없으며 경락잔금 80% 가능"},
        {"구분": "🏭 인천공장", "사건번호": "2025타경 33891", "소재지": "인천 서구 석남동 223-X (기계가공 공장)", "감정가(만)": 160000, "최저가(만)": 112000, "평수(평)": 125, "특징": "1회 유찰(70%) / 가좌IC 인접 10m 도로 접 / 선순위 임차인 없음(명도 수월)"},
        {"구분": "🏭 인천공장", "사건번호": "2026타경 10422", "소재지": "인천 동구 송림동 11-X (대형 자가공장)", "감정가(만)": 320000, "최저가(만)": 224000, "평수(평)": 350, "특징": "1회 유찰(70%) / 송림동 산업유통센터 인근 대지 350평 알짜 공장 / 윙바디 진입 최상"},
        {"구분": "🏭 인천창고", "사건번호": "2026타경 10890", "소재지": "인천 서구 원창동 381-X (북항배후단지 물류창고)", "감정가(만)": 410000, "최저가(만)": 287000, "평수(평)": 380, "특징": "1회 유찰(70%) / 층고 10.5m 대형 물류창고 / 40ft 츄레라 독(Dock) 접안 완비"},
        {"구분": "🏢 수도권아파트", "사건번호": "2025타경 60912", "소재지": "인천 서구 청라동 청라국제도시 전용 84㎡", "감정가(만)": 82000, "최저가(만)": 57400, "평수(평)": 34, "특징": "1회 유찰(70%) / 초역세권 로열동 / 대항력 없는 후순위 임차인 거주"},
        {"구분": "🏢 수도권아파트", "사건번호": "2026타경 2145", "소재지": "경기 부천시 옥길동·역곡 권역 브랜드 전용 84㎡", "감정가(만)": 76000, "최저가(만)": 53200, "평수(평)": 34, "특징": "1회 유찰(70%) / 소유자 점유로 명도 깔끔 / 실거주 및 투자 겸용 추천"}
    ]

    st.markdown("##### 📌 실시간 관심 경매 물건 리스트 (선택 시 아래 시뮬레이터에 자동 입력됩니다)")
    st.dataframe(pd.DataFrame(AUCTION_PRESETS), use_container_width=True, hide_index=True)

    preset_names = [f"[{a['구분']}] {a['사건번호']} - {a['소재지']} (감정가 {a['감정가(만)']/10000:.1f}억 ➔ 최저가 {a['최저가(만)']/10000:.2f}억)" for a in AUCTION_PRESETS]
    sel_auc_idx = st.selectbox("🔍 시뮬레이션할 경매 물건을 선택하세요", range(len(preset_names)), format_func=lambda i: preset_names[i])
    sel_auc = AUCTION_PRESETS[sel_auc_idx]

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown("##### 1) 경매 물건 기본 제원")
        auc_case = st.text_input("사건번호 / 물건명", value=f"{sel_auc['사건번호']} ({sel_auc['소재지']})")
        auc_appraise = st.number_input("감정가 (만 원)", value=int(sel_auc["감정가(만)"]), step=1000)
        auc_bid = st.number_input("예상 입찰가 (만 원)", value=int(sel_auc["최저가(만)"]) + 3000, step=1000)
        auc_land_py = st.number_input("기준 면적 (평)", value=float(sel_auc["평수(평)"]), step=5.0)
    with ac2:
        st.markdown("##### 2) 취득세 · 명도비 · 수리비 · 대출")
        default_tax = 4.6 if "공장" in sel_auc["구분"] or "창고" in sel_auc["구분"] else 1.1
        auc_tax_rate = st.number_input("취득세율 (공장 4.6% / 주택 1.1~3.3%)", value=default_tax, step=0.1)
        auc_evict_cost = st.number_input("예상 명도비 / 미납공과금 (만 원)", value=1200, step=100)
        auc_repair_cost = st.number_input("호이스트·에폭시/인테리어 수리비 (만 원)", value=1500, step=500)
        auc_loan_ratio = st.slider("경락잔금대출 비율 (%)", 40, 85, 75 if "공장" in sel_auc["구분"] else 70)
    with ac3:
        st.markdown("##### 3) 임대 수익 및 금리 설정")
        auc_interest_rate = st.number_input("경락대출 금리 (연 %)", value=4.4, step=0.1)
        auc_exp_dep = st.number_input("예상 임대 보증금 (만 원)", value=5000, step=500)
        auc_exp_rent = st.number_input("예상 월 임대료 (만 원)", value=round(auc_bid * 0.0045), step=20)

    bid_ratio = (auc_bid / auc_appraise * 100) if auc_appraise > 0 else 0
    acq_tax = round(auc_bid * (auc_tax_rate / 100))
    total_cost = auc_bid + acq_tax + auc_evict_cost + auc_repair_cost
    loan_amt = round(auc_bid * (auc_loan_ratio / 100))
    real_invest = total_cost - loan_amt - auc_exp_dep
    monthly_interest = round((loan_amt * (auc_interest_rate / 100)) / 12)
    net_monthly_cash = auc_exp_rent - monthly_interest
    annual_roi = ((net_monthly_cash * 12) / real_invest * 100) if real_invest > 0 else 0

    auc_report = f"""[⚖️ 우리부동산 경매 권리 & 수익률 정밀 분석 리포트]
• 사건번호/소재지 : {auc_case}
• 핵심권리특징 : {sel_auc['특징']}
• 감정가 : {auc_appraise:,}만 원 ➔ 예상 입찰가 : {auc_bid:,}만 원 (낙찰가율 {bid_ratio:.1f}% / 평당 {round(auc_bid/auc_land_py if auc_land_py else 0):,}만 원)
• 총 취득원가 : {total_cost:,}만 원 (취득세 {acq_tax:,}만 + 명도/수리비 {auc_evict_cost+auc_repair_cost:,}만 포함)
• 경락잔금대출({auc_loan_ratio}%) : {loan_amt:,}만 원 (월 이자 약 {monthly_interest:,}만 원)
• 실투자금(보증금 {auc_exp_dep:,}만 공제 후) : 【 {real_invest:,}만 원 】
• 월 순수익 : 매월 {net_monthly_cash:,}만 원 (예상월세 {auc_exp_rent:,}만 - 월이자 {monthly_interest:,}만) ➔ 연 수익률(ROE) : 【 {annual_roi:.2f}% 】"""
    st.code(auc_report, language="text")

# ------------------------------------------
# [7번 시스템] 수도권 핵심 공공분양·특별공급 청약 보드 & 신축공장분양 대출 비교기 (완벽 복원!)
# ------------------------------------------
with sub_tab7:
    st.subheader("🏢 수도권 주요 공공분양·특별공급 청약 정보 보드 & 신축공장분양 대출 시뮬레이터")

    SUBSCRIPTION_DATA = [
        {"단지명": "부천대장 A5블록 (신혼희망타운/공공분양)", "위치": "경기 부천시 대장신도시", "전용면적": "55㎡ / 59㎡", "예상분양가(만)": 46500, "공급유형": "일반공급 / 신혼부부 / 생애최초 특별공급", "핵심체크": "대장홍대선 역세권 수혜 / 청라·계양·부천 인접 직주근접 최상 / 전용 모기지 최대 70% 저리 지원"},
        {"단지명": "인천계양 A6블록 (3기신도시 공공분양)", "위치": "인천 계양구 동양·박촌동 일원", "전용면적": "59㎡ / 74㎡ / 84㎡", "예상분양가(만)": 49000, "공급유형": "일반공급 / 청년·신혼·생애최초 특공", "핵심체크": "인천1호선 박촌역 및 수도권제1순환고속도로 인접 / 분양가상한제 적용 알짜 단지"},
        {"단지명": "검암역세권 공공주택지구", "위치": "인천 서구 검암동·경서동 일원", "전용면적": "59㎡ / 84㎡", "예상분양가(만)": 51000, "공급유형": "일반공급 / 특별공급(신혼·생애최초)", "핵심체크": "공항철도·인천2호선 검암역 더블역세권 / 청라국제도시 및 서구 산업단지 출퇴근 10분컷"},
        {"단지명": "고덕강일 3단지 (토지임대부 나눔형 주택)", "위치": "서울 강동구 강일동", "전용면적": "59㎡ / 84㎡", "예상분양가(만)": 38500, "공급유형": "청년 / 신혼부부 / 생애최초 특별공급", "핵심체크": "건물만 분양받아 초기 자금 부담 최소화 / 청년·신혼 전용 장기 저리 나눔형 모기지 최대 80% 지원"}
    ]

    st.markdown("##### 📋 수도권 핵심 공공주택 & 특별공급 주요 단지 브리핑 보드")
    st.dataframe(pd.DataFrame(SUBSCRIPTION_DATA), use_container_width=True, hide_index=True)

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("#### 🏠 수도권 청약 단지별 자금 & 대출 플래너 (2025.6.27 주담대 규제 & 청년버팀목 1.5억 반영)")
        sub_names = [s["단지명"] for s in SUBSCRIPTION_DATA]
        sel_sub_idx = st.selectbox("자금 계획을 세울 청약 단지를 선택하세요", range(len(sub_names)), format_func=lambda i: sub_names[i])
        sel_sub = SUBSCRIPTION_DATA[sel_sub_idx]

        apt_price = st.number_input("예상 분양가 (만 원)", value=int(sel_sub["예상분양가(만)"]), step=1000)
        apt_cash = st.number_input("현재 보유 가용 자금 (만 원)", value=16000, step=1000)
        apt_ltv = st.slider("예상 정책모기지/주담대 비율 (%)", 40, 80, 70)

        apt_loan = round(apt_price * (apt_ltv / 100))
        apt_need = apt_price - apt_loan
        apt_surplus = apt_cash - apt_need

        st.warning(f"""
        📌 **[ {sel_sub['단지명']} ] 청약 자금 스케줄**
        * **핵심 포인트**: {sel_sub['핵심체크']}
        * **계약금(10%)**: `{round(apt_price*0.1):,}만 원` ➔ **중도금(60%)**: `{round(apt_price*0.6):,}만 원` ➔ **잔금(30%)**: `{round(apt_price*0.3):,}만 원`
        * **예상 대출한도({apt_ltv}%)**: `{apt_loan:,}만 원` / **필요 자기자본**: **`{apt_need:,}만 원`**
        * **현재 가용자금 대비**: **`{apt_surplus:+,}만 원`** (※ 입주 전 전세 거주 시 **청년 버팀목 전세자금대출 최대 1.5억 한도** 활용 가능)
        """)

    with sc2:
        st.markdown("#### 🏗️ 신축공장분양 vs 월세 임차 비교 시뮬레이터 (손님 브리핑용)")
        b_price = st.number_input("신축공장분양 총 분양가 (만 원)", value=191400, step=5000)
        b_loan_pct = st.slider("1금융권 시설자금 대출 한도 (%)", 60, 85, 80)
        b_rate = st.number_input("기업 시설자금 금리 (연 %)", value=4.2, step=0.1)
        curr_rent = st.number_input("손님이 현재 내고 계신 공장 월세 (만 원)", value=550, step=50)

        b_loan = round(b_price * (b_loan_pct / 100))
        b_self = b_price - b_loan
        b_month_int = round((b_loan * (b_rate / 100)) / 12)
        diff_rent = curr_rent - b_month_int

        st.success(f"""
        💡 **[신축공장분양 손님 설득 브리핑 요약]**
        * **총 분양가**: `{b_price:,}만 원` / **대출 가능액({b_loan_pct}%)**: `{b_loan:,}만 원`
        * **필요 실입주금(자부담 20%)**: **`{b_self:,}만 원`** (취득세 감면 혜택 별도 체크)
        * **월 예상 대출이자**: **`{b_month_int:,}만 원`**
        * **결론**: 현재 월세(`{curr_rent:,}만 원`)와 비교하면 매달 **`{abs(diff_rent):,}만 원`** 차이로 남의 공장이 아닌 **대표님 소유의 신축 자가 공장**을 마련하실 수 있습니다!
        """)

# ------------------------------------------
# [8번 시스템] 김소장 맛집·일상·여행 블로그 원고 생성기
# ------------------------------------------
with sub_tab8:
    st.subheader("🍽️ 김소장 맛집 · 카페 · 일상 · 여행 블로그 포스팅 1초 생성기")
    lc1, lc2, lc3 = st.columns(3)
    l_cat = lc1.selectbox("포스팅 주제", ["인천/부천 로컬 맛집 리뷰", "분위기 좋은 카페/디저트", "주말 여행/나들이 기록", "현장 중개 일상 & 농구/운동 기록"])
    l_place = lc2.text_input("방문 장소 / 상호명", placeholder="예: 청라 OO식당 / 부천 역곡 OO카페")
    l_menu = lc3.text_input("대표 메뉴 / 핵심 포인트", placeholder="예: 직화 제육볶음, 넓은 주차장, 가성비 최고")
    l_impression = st.text_area("솔직 후기 및 한줄평", placeholder="예: 현장 임장 마치고 들렀는데 불향이 제대로 살아있고 반찬이 깔끔해서 든든하게 한 끼 해결했습니다.")

    if st.button("✨ 김소장 스타일 일상/맛집 블로그 원고 생성", use_container_width=True):
        life_post = f"""안녕하세요! 인천 산업용 부동산 현장을 발로 뛰는 우리부동산 김소장입니다. 😊
오늘 포스팅은 바쁜 현장 일정 중에 다녀온 【 {l_place} 】 ({l_cat}) 솔직 방문 후기를 남겨보려고 합니다.

📍 [ {l_place} 방문 핵심 요약 ]
• 위치 및 주차 : 접근성이 편리하고 주차 공간이 여유로워 방문하기 수월했습니다.
• 오늘의 픽(Pick) : {l_menu}

---------------------------------------------------------
[ 📸 외관 및 매장 입구 사진 넣는 곳 ]
깔끔하고 정돈된 외관이 눈에 띄는 {l_place}입니다. 평소 이 근처 지날 때마다 눈여겨보던 곳인데 드디어 방문하게 되었네요.

[ 📸 메인 메뉴 / 현장 상세 사진 3~4장 넣는 곳 ]
드디어 기다리던 【 {l_menu} 】!
비주얼부터 기대 이상이었는데, 직접 경험해 보니 더욱 만족스러웠습니다.
{l_impression}

[ 📸 마무리 사진 넣는 곳 ]
---------------------------------------------------------

가끔 이렇게 좋은 시간과 함께 에너지를 충전해야 또 현장에서 대표님들께 더 좋은 공장·창고 매물을 찾아드릴 수 있는 것 같습니다.
인근에서 {l_menu} 생각나실 때 【 {l_place} 】 한 번쯤 들러보시길 추천해 드립니다!

오늘도 활기차고 행복한 하루 보내세요! 감사합니다. 🙏

#{l_place.replace(' ','')} #인천맛집 #청라맛집 #부천맛집 #김소장일상 #우리부동산 #내돈내산후기
"""
        st.code(life_post, language="markdown")

# ------------------------------------------
# [9번 시스템] 드론(Faith 2 Pro) & 짐벌(Osmo 7P) 유튜브·릴스 대본 생성기
# ------------------------------------------
with sub_tab9:
    st.subheader("🎬 드론(Faith 2 Pro) & 짐벌(Osmo Mobile 7P) 촬영 콘티 · CapCut 릴스/쇼츠 대본 생성기")
    vc1, vc2, vc3 = st.columns(3)
    v_loc = vc1.selectbox("촬영 매물 지역", REGIONS)
    v_py = vc2.text_input("촬영 매물 평수 및 거래구분", value="송현동 75평 호이스트 단독공장 임대")
    v_key = vc3.text_input("최대 셀링 포인트", value="보증금 3000 / 월 230만 + 호이스트 2.8톤 + 2층 사무실")

    if st.button("🎥 현장 촬영 컷 리스트 & CapCut 쇼츠 대본 뽑기", use_container_width=True):
        video_script = f"""🎬 [ {v_py} ] 드론(Faith 2 Pro) & 짐벌(Osmo 7P) 5단계 촬영 콘티
1. [드론 오프닝 - 5초] 상공 40m에서 인천 {v_loc} 공업단지 전경과 진입 도로 폭이 한눈에 보이도록 하강 샷
2. [짐벌 진입로 - 8초] 도로에서 출입문으로 걸어 들어가며 화물차 접안 동선을 보여주는 광각(0.5x) 워킹 샷
3. [짐벌 내부전경 - 10초] 슬라이딩 도어 오픈 ➔ 1층 바닥 에폭시 상태와 천장 처마 층고, 호이스트 레일 패닝 샷
4. [짐벌 부대시설 - 8초] 수전반(동력 kW) 클로즈업 ➔ 2층 독립 사무실 계단 및 내부 뷰
5. [아웃트로 - 5초] 공장 정면 풀샷 배경으로 [매매 032-582-6200 | 임대 032-576-2600] 자막 삽입

---------------------------------------------------------
🎙️ [ CapCut 유튜브 쇼츠 / 인스타 릴스 더빙 대본 (40초 컷) ]
(0~5초 / 강렬한 후킹)
"인천 {v_loc}에서 【 {v_key} 】 갖춘 {v_py}, 이 조건에 나오는 거 정말 귀합니다!"

(5~20초 / 진입로 및 입지 브리핑)
"보시는 것처럼 진입 도로가 반듯하게 열려 있어서 화물차 문 앞 상하차 작업이 정말 수월하고요, 공구상가와 산업유통센터가 바로 인접해 있습니다."

(20~35초 / 내부 설비 브리핑)
"내부로 들어오시면 넉넉한 층고에 호이스트와 동력, 그리고 독립 사무실까지 이미 완비되어 있어서 초기 시설비 수천만 원 그대로 아끼고 바로 조업하실 수 있습니다."

(35~45초 / 클로징 CTA)
"실제 현장 확인을 원하시면 지금 바로 화면 상단 우리부동산으로 연락 주세요!"
"""
        st.code(video_script, language="markdown")

# ------------------------------------------
# [10번 시스템] 공장 중개 만능 툴박스 (평↔㎡, 중개보수, 동력 증설비, 에폭시 시공 견적)
# ------------------------------------------
with sub_tab10:
    st.subheader("📐 공장 전문 중개사 만능 툴박스 4종")
    tc1, tc2, tc3, tc4 = st.columns(4)

    with tc1:
        st.markdown("##### 1) 면적 변환 (㎡ ↔ 평)")
        in_m2 = st.number_input("건축물대장 면적 (㎡)", value=247.93, step=10.0)
        st.metric("평수 환산 결과", f"{in_m2 / 3.3058:.1f} 평")
        in_py = st.number_input("전용 평수 (평)", value=75.0, step=5.0)
        st.metric("제곱미터(㎡) 결과", f"{in_py * 3.3058:.2f} ㎡")

    with tc2:
        st.markdown("##### 2) 산업용 중개보수 계산 (0.9%)")
        f_deal_type = st.radio("거래유형", ["임대(월세)", "매매/분양"], horizontal=True)
        if f_deal_type == "임대(월세)":
            dep_m = st.number_input("보증금 (만 원)", value=3000, step=500)
            rent_m = st.number_input("월세 (만 원)", value=230, step=10)
            trans_amt = dep_m + (rent_m * 100)
        else:
            sale_m = st.number_input("매매/분양가 (만 원)", value=191400, step=5000)
            trans_amt = sale_m
        fee_rate = st.number_input("적용 요율 (%)", value=0.9, step=0.1)
        fee_res = round(trans_amt * (fee_rate / 100))
        st.metric("최대 중개보수 (부가세별도)", f"{fee_res:,} 만 원", f"환산금액: {trans_amt:,}만 원")

    with tc3:
        st.markdown("##### 3) 한전 동력(kW) 증설비 추산")
        curr_kw = st.number_input("현재 계약전력 (kW)", value=30, step=10)
        target_kw = st.number_input("필요 계약전력 (kW)", value=100, step=10)
        add_kw = max(0, target_kw - curr_kw)
        kepco_fee = round(add_kw * 9.8)
        elec_work = round(add_kw * 12.0)
        st.metric(f"증설 필요량 (+{add_kw}kW)", f"약 {kepco_fee + elec_work:,} 만 원", f"한전불입금 약 {kepco_fee:,}만 + 내선공사")

    with tc4:
        st.markdown("##### 4) 공장 바닥 에폭시 시공 견적")
        ep_py = st.number_input("시공 바닥 면적 (평)", value=75, step=5)
        ep_type = st.selectbox("에폭시 시공 종류", [
            "일반 코팅 에폭시 (박막형 / 평당 약 3.5만)",
            "고강도 라이닝 에폭시 (후막 3mm / 평당 약 8.5만)"
        ])
        unit_ep = 3.5 if "코팅" in ep_type else 8.5
        st.metric("예상 에폭시 시공비", f"약 {round(ep_py * unit_ep):,} 만 원", "바닥 연삭·면처리 상태에 따라 변동")
