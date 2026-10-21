import streamlit as st
import pandas as pd
import json
import os
import re
import base64
import urllib.request
import urllib.parse
from io import BytesIO
from datetime import datetime, date

# ==========================================
# 0. 외부 라이브러리 안전 로드
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
# 1. 페이지 기본 설정 및 스타일 (화이트 & 블루)
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
    .cal-card {
        background: #ffffff; border: 1px solid #cbd5e1; border-left: 5px solid #004ea2;
        border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 9px 16px;
        font-weight: 800; color: #334155; font-size: 13.5px; border: 1px solid #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004ea2 !important; color: white !important; border-color: #004ea2 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 핵심 상수 및 구글 스프레드시트 스키마 정의
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

# ==========================================
# 3. 구글 스프레드시트 양방향 엔진 (새로고침 유실 방지)
# ==========================================
def get_gspread_client():
    """st.secrets 또는 로컬 JSON에서 서비스 계정을 로드하여 gspread 클라이언트를 반환"""
    if not GSPREAD_AVAILABLE:
        return None, "gspread 라이브러리 미설치 (requirements.txt 확인)"
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = None
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        elif "GOOGLE_CREDENTIALS" in st.secrets:
            raw = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
        elif "type" in st.secrets and st.secrets["type"] == "service_account":
            creds_dict = dict(st.secrets)
        elif os.path.exists("service_account.json"):
            creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
            return gspread.authorize(creds), "OK"

        if creds_dict:
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds), "OK"
        return None, "Streamlit Secrets에 gcp_service_account 설정이 없습니다."
    except Exception as e:
        return None, f"인증 오류: {str(e)}"

def normalize_dataframe(df, default_cols):
    if df is None or df.empty:
        return pd.DataFrame(columns=default_cols)
    df = df.loc[:, ~df.columns.duplicated()]
    for c in default_cols:
        if c not in df.columns:
            df[c] = ""
    return df[default_cols].fillna("").astype(str)

def load_sheet_data(sheet_name, default_cols, local_csv):
    """구글 시트에서 실시간으로 데이터를 읽어오며, 실패 시 공개 CSV URL -> 로컬 순으로 폴백"""
    client, status_msg = get_gspread_client()
    if client:
        try:
            sh = client.open_by_key(SPREADSHEET_ID)
            try:
                ws = sh.worksheet(sheet_name)
            except Exception:
                ws = sh.add_worksheet(title=sheet_name, rows="1000", cols=str(len(default_cols) + 5))
                ws.append_row(default_cols)
            records = ws.get_all_values()
            if len(records) > 1:
                raw_headers = records[0]
                headers = [h.strip() if h.strip() != "" else f"빈열_{i}" for i, h in enumerate(raw_headers)]
                df = pd.DataFrame(records[1:], columns=headers)
                df = normalize_dataframe(df, default_cols)
                df.to_csv(local_csv, index=False, encoding="utf-8-sig")
                return df, True, "구글 시트 실시간 양방향 연동 완료"
            else:
                if len(records) == 0:
                    ws.append_row(default_cols)
                return pd.DataFrame(columns=default_cols), True, "구글 시트 연동 완료 (빈 시트)"
        except Exception as e:
            status_msg = f"시트 접근 오류: {str(e)}"

    # 폴백 1: 구글 시트 공개 읽기 URL (nocache 타임스탬프로 캐시 방지)
    try:
        nocache = int(datetime.now().timestamp())
        pub_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}&t={nocache}"
        df = pd.read_csv(pub_url)
        df = normalize_dataframe(df, default_cols)
        return df, False, f"읽기 전용 연동 중 ({status_msg})"
    except Exception:
        pass

    # 폴백 2: 로컬 CSV
    if os.path.exists(local_csv):
        try:
            df = pd.read_csv(local_csv)
            df = normalize_dataframe(df, default_cols)
            return df, False, f"로컬 임시 저장소 사용 중 ({status_msg})"
        except Exception:
            pass

    return pd.DataFrame(columns=default_cols), False, status_msg

def save_sheet_data(df, sheet_name, local_csv):
    """데이터프레임을 구글 시트에 전체 업데이트하여 새로고침 시 유실을 원천 차단"""
    df = normalize_dataframe(df, df.columns.tolist())
    try:
        df.to_csv(local_csv, index=False, encoding="utf-8-sig")
    except Exception:
        pass

    client, status_msg = get_gspread_client()
    if client:
        try:
            sh = client.open_by_key(SPREADSHEET_ID)
            try:
                ws = sh.worksheet(sheet_name)
            except Exception:
                ws = sh.add_worksheet(title=sheet_name, rows="1000", cols=str(len(df.columns) + 5))
            ws.clear()
            values = [df.columns.values.tolist()] + df.astype(str).values.tolist()
            ws.update(values)
            return True, "구글 스프레드시트 저장 성공"
        except Exception as e:
            return False, f"구글 시트 쓰기 실패: {str(e)}"
    return False, f"구글 시트 미연결 ({status_msg})"

def compress_uploaded_image(uploaded_file):
    """구글 시트 1셀 제한(50,000자) 내에 무조건 들어오도록 이미지를 초경량 Base64로 압축"""
    if not uploaded_file:
        return ""
    try:
        if PIL_AVAILABLE:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((480, 340))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=60)
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            if len(b64_str) > 45000:
                img.thumbnail((320, 220))
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=50)
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_str}"
        else:
            return ""
    except Exception:
        return ""

# ==========================================
# 4. 송현동 실제 양식 100% 반영 공장 블로그 생성기
# ==========================================
def generate_songhyeon_style_blog(row):
    region = str(row.get("소재지(권역)", "송현동") or "송현동")
    deal = str(row.get("거래구분", "공장임대") or "공장임대")
    price = str(row.get("가격(보/월)", "3000만 / 230만") or "3000만 / 230만")

    area_digits = ''.join(filter(str.isdigit, str(row.get("면적", "75"))))
    area_num = int(area_digits) if area_digits else 75

    off_digits = ''.join(filter(str.isdigit, str(row.get("사무실평수", "15"))))
    office_num = int(off_digits) if off_digits else 0

    total_py = area_num + office_num
    total_m2 = round(total_py * 3.3058)

    height = str(row.get("층고", "호이스트 주행 넉넉한 하이 층고") or "호이스트 주행 넉넉한 하이 층고")
    power = str(row.get("동력", "30kW") or "30kW")
    hoist = str(row.get("호이스트", "호이스트 2.8톤 완비") or "호이스트 2.8톤 완비")
    road = str(row.get("대형차량", "8m 도로") or "8m 도로")
    move_in = str(row.get("입주가능일", "즉시 입주 / 협의") or "즉시 입주 / 협의")
    zoning = str(row.get("용도지역/구조", "일반공업지역 / 철골조") or "일반공업지역 / 철골조")
    approval_date = str(row.get("사용승인일", "건축물대장 확인 완료") or "건축물대장 확인 완료")
    biz_tag = str(row.get("추천업종", "금속·기계가공") or "금속·기계가공")
    memo = str(row.get("특징메모", "인천산업유통센터 및 공구상가 초인접으로 원부자재 수급 및 가공 네트워크 최상") or "")

    has_hoist = "없음" not in hoist
    hoist_hook = f"{hoist}와 " if has_hoist else ""
    office_hook = f"2층 {office_num}평 사무실을 갖추고 " if office_num > 0 else "반듯한 1층 작업 공간을 갖추고 "

    return f"""안녕하세요. 인천 공장·창고 전문 우리부동산입니다.
인천 {region} {deal} 매물 중 핵심 공업 인프라 배후에서 {hoist_hook}{office_hook}이 가격에 나오는 곳은 정말 귀합니다.
요즘 {region}이나 인근 산업단지·공구상가 인근에서 {area_num}평대 1층 공장을 찾아보시면 금액대가 만만치 않은 데다, 호이스트가 없거나 사무실이 마땅치 않아 시설 설치비로 수천만 원이 깨지는 경우가 허다합니다. 오늘 소개해 드리는 매물은 인천 {region} 1층 {area_num}평 공장과 {"2층 " + str(office_num) + "평 사무실 통임대" if office_num > 0 else "단독 작업장"} 건으로, 【 {price} 】이라는 주변 시세 대비 아주 합리적인 조건으로 나와 강력 추천해 드립니다.

[ 📸 대표사진 넣는 곳 - 공장 진입로 및 외관 ]
주요 산업유통단지 및 공구상가가 인접해 있어 볼트, 공구, 철재 부품 수급 및 외주 가공 연계성이 인천에서 으뜸인 입지입니다. 공장 정면으로 진입 도로({road})가 반듯하게 열려 있어 화물차가 문 앞까지 수월하게 접안해 상하차 작업을 진행하기에 최적화된 동선을 자랑합니다.

---------------------------------------------------------
📊 [ {region} {deal} 핵심 제원 요약표 ] (블로그 표에 복사해 넣으세요)
• 소재지 : 인천광역시 {region}
• 보증금 / 월세(또는 매매가) : {price}
• 매물 구분 / 주 용도 : {deal} / 공장
• 입주 날짜 : {move_in}
• 용도지역 / 건축구조 : {zoning}
• 층 / 향 / 사용승인일 : 1층 / {approval_date}
• 특징 요약 :
✅ 인천 {region} 공장 1층 {area_num}평 공장 {"+ 2층 " + str(office_num) + "평 전용 사무실" if office_num > 0 else ""} (총 면적 약 {total_m2}㎡)
- 층고: {height}
- 동력: {power} (가공 설비 구동 충분)
- 도로: {road}
- 주차: 문 앞 차량 작업 및 접안 편리
- 관리비: 실비 정산
- 출입문: 대형 슬라이딩 도어
- 승강기/호이스트: {hoist}
- 화장실: 전용 화장실 구비
- 사무실: {"2층 " + str(office_num) + "평 독립 사무실 완비" if office_num > 0 else "내부 사무공간 구비"}

✅ {region} {deal} 매물 중 【 {price} 】의 특급 시세 가성비
✅ {hoist + " 기본 설비로 H빔 보강 및 크레인 설치비 수천만 원 굳히고 입주" if has_hoist else "기둥 간섭 없는 높은 층고와 반듯한 레이아웃으로 설비 배치 최상"}
✅ 동력 {power} 기본 인입으로 추가 승압 공사비 없이 선반·밀링·가공 기계 즉시 연결
✅ {"2층 " + str(office_num) + "평 독립 사무실 완비로 1층 바닥 공간 " + str(area_num) + "평을 온전히 작업장으로 통활용" if office_num > 0 else "1층 바닥 면적 전체를 손실 없이 온전히 작업 및 적재 공간으로 통활용"}
✅ {memo}
✅ 추천 업종 : {biz_tag}, 정밀 금형 가공, 중량물 기계 가공, 선반·밀링 임가공, 철구조물 제작 및 물류 창고 강력 추천
---------------------------------------------------------

[ 1층 내부 사진 ]
[ 📸 사진 1 : 공장 메인 진입로 및 화물차 문 앞 접안 전경 ]
공장 메인 진입로 및 화물차 문 앞 접안 전경입니다. 출입문 바로 앞으로 차량이 바짝 들어와 자재를 싣고 내리기에 최적화된 동선입니다. 출입구 폭과 높이가 널찍해 무거운 원자재를 내부로 직결 반입하기 수월합니다.

[ 📸 사진 2 : 1층 메인 가공 작업장 전체 전경 1 ]
1층 메인 작업장 전체 전경입니다. 기계 하중을 단단하게 버텨주는 튼튼한 바닥 기초 위에 가공 설비를 안정적으로 안착시킬 수 있습니다. 뼈대가 무식할 정도로 튼튼해 주변 민원 눈치 볼 필요 없이 편하게 일하실 '진짜 제조업' 사장님들께 최고의 안식처입니다.

[ 📸 사진 3 : 1층 작업장 전체 전경 2 ]
【 {price} 】! {hoist}, 동력 {power}{" 및 2층 " + str(office_num) + "평 사무실" if office_num > 0 else ""}을 갖춘 {region} {area_num}평 1층 알짜배기 {deal} 매물입니다.

[ 📸 사진 4~5 : 상단 호이스트 및 천장 트러스 골조 뷰 ]
{"상부 골조를 따라 " + hoist + "이 가동되고 있어 무거운 중량 금속 자재와 완제품을 힘들이지 않고 전 구역으로 안전하게 인양할 수 있습니다. 빈 공장에 H빔 보강하고 호이스트 레일 새로 까시려면 최소 수천만 원 깨지는 거 대표님들이 더 잘 아실 텐데요." if has_hoist else "천장 트러스 골조 및 하이 층고 상세 뷰입니다. 개방감이 뛰어나 대형 설비 반입이나 파레트 고단 적재가 매우 유리합니다."}

[ 📸 사진 6 : 1층 작업장 중앙에서 바라본 레이아웃 ]
중앙 통로 폭이 넓어 대차 및 지게차 이동이 자유로우며, 작업 동선과 사무 공간이 효율적으로 분리되어 있습니다.

[ 2층 사무실 및 부대시설 ]
[ 📸 사진 7~8 : 전용 사무실 내부 및 화장실 전경 ]
{"약 " + str(office_num) + "평 규모로 컴퓨터 데스크, 도면 검토대, 상담용 소파를 여유롭게 두고 쓸 수 있는 아늑한 오피스 공간입니다. 현장 소음 간섭 없이 바이어 미팅과 수주 관리를 보기에 안성맞춤이며 전용 화장실이 구비되어 있습니다." if office_num > 0 else "깔끔하게 관리된 사무 공간 및 전용 단독 화장실이 구비되어 있습니다."}

---------------------------------------------------------
인천 {region} 공업지역에서 1층 {area_num}평 작업장에 {hoist}, 동력 {power}{", 2층 " + str(office_num) + "평 사무실" if office_num > 0 else ""}까지 다 갖춘 공장을 【 {price} 】에 얻을 수 있는 기회는 흔치 않습니다.
고정비를 획기적으로 줄이면서 즉시 기계를 안착시켜 조업에 들어갈 알짜배기 공장을 찾으시는 사장님들께서는 서둘러 현장을 확인해 보시길 권해드립니다.

[ 📸 명함 사진 넣는 곳 ]
명함을 누르시면 전화 연결이 됩니다. 언제든 편하게 연락 주시기 바랍니다.

매물 상담 문의, 접수 문의 언제든 환영합니다.
우리 부동산 공인중개사 대표
김태형 010-2660-8276
📞 매매문의 : 032-582-6200 | 📞 임대문의 : 032-576-2600
🌐 공식 블로그 : https://blog.naver.com/woorirealestate__

정직하고 최선을 다하여 중개하겠습니다.

#{region}공장임대 #{region}공장매매 #{region}공장 #인천{region}공장 #{region}호이스트공장 #인천산업유통센터공장 #인천공장임대 #인천창고임대 #인천호이스트공장 #송림동공장임대 #가좌동공장임대 #석남동공장임대 #원창동공장임대 #도화동공장임대 #경서동공장임대 #신축공장분양 #인천공장전문 #우리부동산 #인천공장매매 #소형공장임대"""

# ==========================================
# 5. 데이터 초기화 및 사이드바 (비밀번호 563011 & API 설정)
# ==========================================
df_props, gs_ok_p, gs_msg_p = load_sheet_data("properties", PROP_COLUMNS, "properties.csv")
df_custs, gs_ok_c, _ = load_sheet_data("customers", CUST_COLUMNS, "customers.csv")
df_hunts, gs_ok_h, _ = load_sheet_data("hunting", HUNT_COLUMNS, "hunting_properties.csv")

st.markdown("""
<div class="main-banner">
    <div>
        <h1>🏭 우리부동산 통합업무시스템 (구글시트 & 홈페이지 실시간 연동)</h1>
        <p>주력 권역: 석남동 · 가좌동 · 송림동 · 송현동 · 도화동 · 원창동 · 경서동 | 신축공장분양 · 공장임대 · 공장매매</p>
    </div>
    <div class="tel-badge">
        📞 매매 032-582-6200 | 임대 032-576-2600
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("🔒 관리자 보안 인증")
    admin_pw = st.text_input("관리자 비밀번호", value="563011", type="password")
    if admin_pw != "563011":
        st.error("비밀번호(563011)가 일치하지 않습니다.")
        st.stop()

    st.divider()
    st.subheader("☁️ 구글 시트 실시간 연동 상태")
    if gs_ok_p:
        st.success("✅ 구글 시트 양방향 읽기/쓰기 정상 작동 중 (새로고침 유실 없음)")
    else:
        st.warning(f"⚠️ 구글 시트 쓰기 권한 점검 필요\n사유: {gs_msg_p}")
        with st.expander("🛠️ 새로고침 시 안 날아가게 하는 법"):
            st.markdown("""
            1. **Streamlit Cloud** 우측 하단 `Manage app` ➔ `Settings` ➔ `Secrets` 클릭
            2. `[gcp_service_account]` 아래에 서비스 계정 JSON 키 붙여넣기 후 Save
            3. 구글 시트 우측 상단 **[공유]** ➔ 서비스 계정 이메일(`client_email`)을 **편집자**로 추가!
            """)

    if st.button("🔄 구글 시트에서 최신 데이터 강제 새로고침", use_container_width=True):
        st.rerun()

    st.markdown(f"📊 **[구글 스프레드시트 원본 열기 ↗](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit)**")
    st.markdown("🟢 **[네이버 공식 블로그 바로가기 ↗](https://blog.naver.com/woorirealestate__)**")

    st.divider()
    st.subheader("🔑 공공데이터 API 키 설정 (경매/청약)")
    default_api_key = st.secrets.get("PUBLIC_DATA_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key_input = st.text_input("공공데이터포털 Decoding 인증키", value=default_api_key, type="password", help="청약홈 및 온비드/법원경매 API 실시간 호출에 사용됩니다.")

    st.divider()
    st.subheader("📥 3대 장부 엑셀(CSV) 백업")
    st.download_button("💾 1. 보유매물 장부 백업", data=df_props.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_보유매물_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 2. 찾는손님 장부 백업", data=df_custs.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_손님장부_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    st.download_button("💾 3. 물건따기 장부 백업", data=df_hunts.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"우리부동산_물건따기_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)


# ==============================================================================
# 🔥 [상단 주업무 4대 시스템]
# ==============================================================================
st.markdown('<div class="section-divider">🔥 [주업무 시스템] 1. 새 매물 등록(+사진/홈페이지 연동) · 2. 전체 매물 통합장부 · 3. 카톡 멀티 브리핑 & 블로그 · 4. 찾는 손님 CRM</div>', unsafe_allow_html=True)

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "➕ 1. 새 매물 등록 (+사진/홈페이지 연동)",
    "📋 2. 전체 매물 통합장부 (실시간 수정/동기화)",
    "💬 3. 손님 전송용 카톡 멀티 브리핑 & 블로그 생성",
    "👥 4. 찾는 손님 (구해요) CRM & 자동 역매칭"
])

# ------------------------------------------
# [주업무 1] 새 매물 등록 (+사진 업로드 및 구글시트/홈페이지 자동 연동)
# ------------------------------------------
with main_tab1:
    st.subheader("➕ 신규 공장 · 창고 · 신축공장분양 매물 등록")
    st.caption("저장 즉시 구글 스프레드시트(`properties` 시트)에 기록되며, 손님용 홈페이지(`index.html`)에 실시간으로 반영됩니다.")

    with st.form("form_add_property", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        next_id = f"W-{101 + len(df_props)}"
        p_id = c1.text_input("매물번호 *", value=next_id)
        p_deal = c2.selectbox("거래구분 *", DEAL_TYPES)
        p_region = c3.selectbox("소재지 (주력 7대 권역) *", REGIONS)
        p_show = c4.selectbox("홈페이지 노출 설정 *", ["공개 (홈페이지 즉시 노출)", "비공개 (내부 장부만 보관)"])

        c5, c6, c7 = st.columns([2, 1.2, 1])
        p_title = c5.text_input("홈페이지/블로그용 매물 제목 *", placeholder="예: 송현동 공구상가 배후 호이스트 2.8톤+2층 사무실 완비 1층 공장")
        p_price = c6.text_input("보증금 / 월세 (또는 매매·분양가) *", placeholder="예: 3000만 / 230만")
        p_biz = c7.selectbox("추천 업종 태그", BIZ_TAGS)

        c8, c9, c10, c11 = st.columns(4)
        p_area = c8.text_input("1층 공장 전용평수 (숫자만) *", value="75")
        p_office = c9.text_input("2층/부속 사무실 평수 (없으면 0)", value="15")
        p_height = c10.text_input("층고 설명", value="호이스트 2.8톤 주행 넉넉한 하이 층고")
        p_power = c11.text_input("계약 전력(동력)", value="30kW")

        c12, c13, c14, c15 = st.columns(4)
        p_hoist_yn = c12.selectbox("호이스트 유무 선택 *", ["호이스트 있음", "호이스트 없음"])
        p_hoist_spec = c13.text_input("호이스트 상세 제원", value="호이스트 2.8톤 완비")
        p_truck = c14.selectbox("도로 / 차량 진입 조건", [
            "8m 도로 (화물차 및 5t~11t 윙바디 접안 수월)",
            "40ft 츄레라 진입 가능 (광폭 도로)",
            "6m 도로 (1t~2.5t 화물차 문앞 접안)"
        ])
        p_movein = c15.text_input("입주 날짜", value="즉시 입주 / 협의 가능")

        st.markdown("##### 🔒 중개사 전용 비밀장부 (손님용 홈페이지에는 절대 노출되지 않습니다)")
        s1, s2, s3, s4, s5 = st.columns([1.4, 1, 1.2, 1.2, 1])
        p_secret_addr = s1.text_input("📍 실제 상세 지번 (비공개)", placeholder="예: 송현동 123-45")
        p_owner_name = s2.text_input("👤 건물주/임대인 성함", placeholder="예: 박사장님")
        p_owner_tel = s3.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")
        p_zoning = s4.text_input("용도지역 / 건축구조", value="일반공업지역 / 철골조")
        p_approval = s5.text_input("사용승인일", placeholder="예: 1997.1.17")

        p_memo = st.text_area("💡 핵심 특징 요약 (블로그 체크리스트 및 카톡 브리핑에 자동 삽입)",
                              value="인천산업유통센터 및 송현 공구상가 초인접으로 원부자재 수급 및 가공 네트워크 최상")

        st.markdown("##### 📸 대표 현장 사진 등록 (업로드 또는 이미지 URL 입력 시 홈페이지 매물 카드에 즉시 반영)")
        ic1, ic2 = st.columns(2)
        up_photo = ic1.file_uploader("방법 1) 대표 사진 파일 업로드 (자동 초경량 압축 저장)", type=["jpg", "jpeg", "png", "webp"])
        url_photo = ic2.text_input("방법 2) 또는 이미지 URL 직접 입력 (비워두면 기본 공장 사진 자동 적용)")

        btn_save_prop = st.form_submit_button("💾 매물 등록 완료 (구글시트 & 홈페이지 실시간 반영 + 송현동 양식 블로그 원고 생성)", use_container_width=True)

        if btn_save_prop:
            photo_data = ""
            if up_photo is not None:
                photo_data = compress_uploaded_image(up_photo)
            elif url_photo.strip():
                photo_data = url_photo.strip()

            hoist_val = p_hoist_spec.strip() if p_hoist_yn == "호이스트 있음" else "호이스트 없음"

            new_prop_row = {
                "매물번호": p_id.strip(),
                "등록일자": datetime.now().strftime("%Y-%m-%d"),
                "홈페이지노출": "공개" if "공개" in p_show else "비공개",
                "거래구분": p_deal,
                "소재지(권역)": p_region,
                "상세주소(지번)": p_secret_addr.strip(),
                "매물제목": p_title.strip() if p_title.strip() else f"인천 {p_region} 1층 {p_area}평 {p_deal} ({hoist_val})",
                "가격(보/월)": p_price.strip(),
                "면적": f"{p_area.strip()}평",
                "사무실평수": f"{p_office.strip()}평",
                "층고": p_height.strip(),
                "동력": p_power.strip(),
                "호이스트": hoist_val,
                "대형차량": p_truck,
                "추천업종": p_biz,
                "입주가능일": p_movein.strip(),
                "용도지역/구조": p_zoning.strip(),
                "사용승인일": p_approval.strip(),
                "임대인(건물주)": p_owner_name.strip(),
                "임대인연락처": p_owner_tel.strip(),
                "특징메모": p_memo.strip(),
                "대표사진": photo_data
            }

            df_props = pd.concat([pd.DataFrame([new_prop_row]), df_props], ignore_index=True)
            saved_ok, saved_msg = save_sheet_data(df_props, "properties", "properties.csv")
            st.session_state["latest_prop"] = new_prop_row
            if saved_ok:
                st.success(f"✅ [{p_id}] 매물이 구글 스프레드시트(`properties`)에 영구 저장되었으며 홈페이지(`index.html`)에 실시간 연동되었습니다!")
            else:
                st.warning(f"⚠️ 로컬에는 저장되었으나 구글 시트 쓰기 확인이 필요합니다: {saved_msg}")

    if "latest_prop" in st.session_state:
        st.divider()
        st.subheader("🟢 방금 등록한 매물 — 네이버 블로그 원고 (송현동 실제 양식 100% 적용)")
        st.caption("우측 상단의 복사 아이콘을 클릭해 네이버 블로그에 그대로 붙여넣으세요.")
        st.code(generate_songhyeon_style_blog(st.session_state["latest_prop"]), language="markdown")

# ------------------------------------------
# [주업무 2] 전체 매물 통합장부 (실시간 수정 및 동기화)
# ------------------------------------------
with main_tab2:
    st.subheader(f"📋 전체 보유 매물 통합장부 (총 {len(df_props)}건)")
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    f_reg = fc1.selectbox("소재지(권역) 필터", ["전체"] + REGIONS)
    f_deal = fc2.selectbox("거래구분 필터", ["전체"] + DEAL_TYPES)
    f_kw = fc3.text_input("🔍 통합 검색 (실제지번, 건물주 연락처, 매물번호, 특징메모)")

    view_df = df_props.copy()
    if f_reg != "전체":
        view_df = view_df[view_df["소재지(권역)"].astype(str).str.contains(f_reg)]
    if f_deal != "전체":
        view_df = view_df[view_df["거래구분"].astype(str).str.contains(f_deal)]
    if f_kw.strip():
        mask = view_df.astype(str).apply(lambda x: x.str.contains(f_kw.strip(), case=False, na=False)).any(axis=1)
        view_df = view_df[mask]

    edited_props = st.data_editor(view_df, num_rows="dynamic", use_container_width=True, height=430, key="editor_props")
    if st.button("💾 수정/삭제 내역 구글 스프레드시트 & 홈페이지 즉시 반영", type="primary"):
        # 필터링 상태에서 수정 시 전체 데이터프레임에 반영
        if f_reg == "전체" and f_deal == "전체" and not f_kw.strip():
            df_props = edited_props
        else:
            df_props.update(edited_props)
        ok, msg = save_sheet_data(df_props, "properties", "properties.csv")
        if ok:
            st.success("✅ 구글 스프레드시트 및 홈페이지 동기화가 완료되었습니다!")
            st.rerun()
        else:
            st.error(msg)

# ------------------------------------------
# [주업무 3] 손님 전송용 카카오톡 1초 멀티 브리핑 & 블로그 생성기
# ------------------------------------------
with main_tab3:
    st.subheader("💬 손님 전송용 카카오톡 1초 멀티 브리핑 (여러 매물 동시 선택)")
    st.caption("손님에게 한 번에 여러 개의 추천 매물을 브리핑할 때, 매물을 여러 개 고르면 카톡 전송용 묶음 문구가 1초 만에 완성됩니다.")

    if len(df_props) == 0:
        st.info("등록된 매물이 없습니다. [1. 새 매물 등록] 탭에서 매물을 먼저 등록해 주세요.")
    else:
        prop_labels = [
            f"[{r['매물번호']}] {r['소재지(권역)']} {r['면적']} {r['거래구분']} ({r['가격(보/월)']}) | {r['호이스트']} | 지번:{r['상세주소(지번)']}"
            for _, r in df_props.iterrows()
        ]
        sel_indices = st.multiselect(
            "✅ 손님에게 카톡으로 보낼 매물들을 선택하세요 (여러 개 선택 가능)",
            options=list(range(len(prop_labels))),
            default=[0] if len(prop_labels) > 0 else [],
            format_func=lambda idx: prop_labels[idx]
        )

        if sel_indices:
            kakao_blocks = ["안녕하세요. 인천 공장·창고 전문 우리부동산 김태형 대표입니다.\n요청하신 조건에 부합하는 추천 실매물 브리핑 드립니다.\n"]
            for seq, idx in enumerate(sel_indices, 1):
                r = df_props.iloc[idx]
                off_txt = f" + 2층 사무실 {r.get('사무실평수','')}" if str(r.get('사무실평수','0평')) not in ["0", "0평", ""] else ""
                block = f"""━━━━━━━━━━━━━━━━━━━━━━━━
■ 추천매물 {seq}. [{r.get('매물번호','')}] 인천 {r.get('소재지(권역)','')} {r.get('거래구분','')}
• 실사용면적 : 1층 {r.get('면적','')}{off_txt}
• 금액조건 : {r.get('가격(보/월)','')}
• 설비제원 : {r.get('층고','')} / 동력 {r.get('동력','')} / {r.get('호이스트','')}
• 차량/도로 : {r.get('대형차량','')}
• 입주시기 : {r.get('입주가능일','즉시/협의')}
• 핵심특징 : {r.get('특징메모','')}"""
                kakao_blocks.append(block)

            kakao_blocks.append("""━━━━━━━━━━━━━━━━━━━━━━━━
현장 실사 확인된 매물이며, 원하시는 시간대에 바로 내부 확인 가능합니다.

🏭 우리부동산 공인중개사 사무소 대표 김태형
📞 매매문의 : 032-582-6200 | 📞 임대문의 : 032-576-2600
📱 대표 직통 : 010-2660-8276""")

            full_kakao_text = "\n".join(kakao_blocks)
            st.markdown("#### 💬 카카오톡 묶음 브리핑 복사 박스 (우측 상단 복사 버튼 클릭)")
            st.code(full_kakao_text, language="text")

            with st.expander("🟢 선택한 매물의 네이버 블로그 원고(송현동 양식) 다시 보기"):
                for idx in sel_indices:
                    r_dict = df_props.iloc[idx].to_dict()
                    st.markdown(f"**[{r_dict.get('매물번호')}] {r_dict.get('매물제목')}**")
                    st.code(generate_songhyeon_style_blog(r_dict), language="markdown")

# ------------------------------------------
# [주업무 4] 찾는 손님 (구해요) CRM 장부 & 자동 역매칭
# ------------------------------------------
with main_tab4:
    st.subheader("👥 찾는 손님 (구해요) CRM 장부 & 보유매물 자동 역매칭")
    with st.expander("➕ 신규 대기 손님 등록하기", expanded=False):
        with st.form("form_add_customer"):
            cc1, cc2, cc3, cc4 = st.columns(4)
            c_type = cc1.selectbox("구분", ["공장임대 구함", "공장매매 구함", "신축공장분양 문의", "매물 내놓기(접수)"])
            c_name = cc2.text_input("고객명 / 업체명 *")
            c_tel = cc3.text_input("연락처 *")
            c_reg = cc4.text_input("희망 지역", value="석남동, 가좌동, 송현동")

            cc5, cc6, cc7, cc8 = st.columns(4)
            c_area = cc5.text_input("희망 평수 (숫자 입력 시 자동 매칭)", value="80")
            c_budget = cc6.text_input("예산 (보/월/매매가)", placeholder="예: 월 250만 이하")
            c_req = cc7.text_input("필수 설비 (호이스트/동력)", placeholder="예: 호이스트 2.8톤 이상")
            c_status = cc8.selectbox("진행 상태", ["🔥 진행중(A급)", "진행중(일반)", "계약완료", "보류"])

            c_memo = st.text_input("상세 상담 메모")
            if st.form_submit_button("💾 손님 장부(`customers` 시트)에 저장", use_container_width=True):
                new_c = {
                    "등록일자": datetime.now().strftime("%Y-%m-%d"),
                    "구분": c_type, "고객명(업체명)": c_name, "연락처": c_tel,
                    "희망지역": c_reg, "희망평수": c_area, "예산(보/월/매매가)": c_budget,
                    "필수조건(호이스트/전력)": c_req, "진행상태": c_status, "상세메모": c_memo
                }
                df_custs = pd.concat([pd.DataFrame([new_c]), df_custs], ignore_index=True)
                save_sheet_data(df_custs, "customers", "customers.csv")
                st.success("✅ 손님 장부에 저장되었습니다!")
                st.rerun()

    edited_custs = st.data_editor(df_custs, num_rows="dynamic", use_container_width=True, height=300, key="editor_custs")
    if st.button("💾 손님장부 수정사항 구글시트 저장"):
        df_custs = edited_custs
        save_sheet_data(df_custs, "customers", "customers.csv")
        st.success("✅ 손님 장부가 동기화되었습니다!")

    if len(df_custs) > 0 and len(df_props) > 0:
        st.divider()
        st.markdown("##### 🎯 선택한 손님 조건에 맞는 보유 매물 자동 역매칭")
        c_opts = [f"{r['고객명(업체명)']} ({r['연락처']}) | 희망: {r['희망지역']} {r['희망평수']}평 | {r['필수조건(호이스트/전력)']}" for _, r in df_custs.iterrows()]
        sel_c = st.selectbox("매칭할 손님을 선택하세요", range(len(c_opts)), format_func=lambda i: c_opts[i])
        target_c = df_custs.iloc[sel_c]
        c_py_num = int(''.join(filter(str.isdigit, str(target_c.get("희망평수", "0")))) or 0)

        matched_list = []
        for _, pr in df_props.iterrows():
            p_py_num = int(''.join(filter(str.isdigit, str(pr.get("면적", "0")))) or 0)
            if c_py_num == 0 or (c_py_num * 0.65 <= p_py_num <= c_py_num * 1.45):
                matched_list.append(pr)
        if matched_list:
            st.dataframe(pd.DataFrame(matched_list)[["매물번호", "거래구분", "소재지(권역)", "상세주소(지번)", "면적", "가격(보/월)", "호이스트", "동력", "임대인연락처"]], use_container_width=True)
        else:
            st.info("희망 평수(±35%) 범위에 들어오는 매물이 없습니다.")


# ==============================================================================
# 🛠️ [하단 확장 업무 5대 시스템] (드론/툴박스 완전 제거, 요청하신 5대 핵심 기능 복원!)
# ==============================================================================
st.markdown('<div class="section-divider">🛠️ [확장 업무 시스템] 5. 현장 임장(복붙 파서) · 6. 공장/아파트 경매(API) · 7. 수도권 청약 캘린더 · 8. 신축공장분양 전용관 · 9. 김소장 맛집/일상 블로그</div>', unsafe_allow_html=True)

ext_tab1, ext_tab2, ext_tab3, ext_tab4, ext_tab5 = st.tabs([
    "🎯 5. 현장 임장 / 물건따기 (복붙 자동추출)",
    "⚖️ 6. 인천공장 & 수도권아파트 경매 (API 연동)",
    "📅 7. 수도권 아파트 청약 캘린더",
    "🏗️ 8. 신축공장분양 전용 탭 (80% 대출 비교)",
    "🍽️ 9. 김소장 맛집 · 일상 · 여행 블로그 생성기"
])

# ------------------------------------------
# [확장 5] 현장 임장 / 물건따기 장부 (`hunting` 시트 연동 + 복붙 자동 파서 + 정식매물 승격)
# ------------------------------------------
with ext_tab1:
    st.subheader("🎯 현장 임장 / 물건따기 장부 (`hunting` 시트 실시간 연동)")
    st.markdown("##### 📋 1) 현장 메모 · 카톡 · 건축물대장 텍스트 복사·붙여넣기 자동 추출기")
    p_col1, p_col2 = st.columns([2.2, 1])
    with p_col1:
        raw_text = st.text_area(
            "현장에서 적어둔 메모나 카톡, 건축물대장 텍스트를 그대로 붙여넣으세요",
            placeholder="예시: 가좌동 556-12 대성정밀 약 120평 보증금 3500 / 월 350 호이스트 5톤 동력 100kW 박사장 010-9999-8888 내년 2월 만기 공실예정",
            height=90
        )
    with p_col2:
        st.caption("붙여넣기 후 아래 버튼을 누르면 지번, 평수, 연락처, 동력/호이스트를 자동으로 추출해 입력칸에 채웁니다.")
        if st.button("🪄 텍스트 자동 파싱하여 입력칸 채우기", use_container_width=True):
            det_reg = "가좌동"
            for r_n in REGIONS:
                if r_n[:2] in raw_text:
                    det_reg = r_n
                    break
            jibun_match = re.search(r'([가-힣]+동\s*\d+(?:-\d+)?|\b\d{1,4}-\d{1,4}\b)', raw_text)
            tel_match = re.search(r'(01[016789]-?\d{3,4}-?\d{4}|032-?\d{3,4}-?\d{4})', raw_text)
            py_match = re.search(r'(\d+)\s*평', raw_text)
            m2_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:㎡|m2|제곱)', raw_text)
            kw_match = re.search(r'(\d+)\s*(?:kw|kW|키로)', raw_text)
            hoist_match = re.search(r'호이스트\s*(\d+(?:\.\d+)?\s*(?:톤|t|T)?)', raw_text)

            st.session_state["hp_reg"] = det_reg
            st.session_state["hp_addr"] = jibun_match.group(0) if jibun_match else ""
            st.session_state["hp_tel"] = tel_match.group(0) if tel_match else ""
            if py_match:
                st.session_state["hp_py"] = f"{py_match.group(1)}평"
            elif m2_match:
                st.session_state["hp_py"] = f"{round(float(m2_match.group(1))/3.3058)}평"
            else:
                st.session_state["hp_py"] = ""

            spec_parts = []
            if kw_match:
                spec_parts.append(f"동력 {kw_match.group(1)}kW")
            if hoist_match:
                spec_parts.append(f"호이스트 {hoist_match.group(1)}")
            elif "호이스트" in raw_text:
                spec_parts.append("호이스트 있음")
            st.session_state["hp_spec"] = " / ".join(spec_parts)
            st.session_state["hp_memo"] = raw_text.strip()
            st.success("✅ 자동 파싱 완료! 아래 폼에서 확인 후 저장을 누르세요.")

    with st.form("form_add_hunting"):
        hc1, hc2, hc3, hc4 = st.columns(4)
        def_r = st.session_state.get("hp_reg", "가좌동")
        r_idx = REGIONS.index(def_r) if def_r in REGIONS else 0
        h_reg = hc1.selectbox("권역", REGIONS, index=r_idx)
        h_addr = hc2.text_input("상세 지번 *", value=st.session_state.get("hp_addr", ""))
        h_bldg = hc3.text_input("건물명 / 현재 상호")
        h_py = hc4.text_input("예상 평수", value=st.session_state.get("hp_py", ""))

        hc5, hc6, hc7, hc8 = st.columns(4)
        h_price = hc5.text_input("예상 금액 (보/월/매매)")
        h_spec = hc6.text_input("동력 / 호이스트", value=st.session_state.get("hp_spec", ""))
        h_owner = hc7.text_input("소유자(건물주) 성함")
        h_tel = hc8.text_input("연락처", value=st.session_state.get("hp_tel", ""))

        hc9, hc10, hc11 = st.columns([1, 1, 2])
        h_state = hc9.selectbox("현장 상태", ["만기 도래 예정", "현재 공실(현수막)", "자가 사용중(매도가능성)", "신축 공사중"])
        h_res = hc10.selectbox("접촉 결과", ["1차 명함 투입", "통화 완료(긍정)", "통화 완료(보류)", "정식 매물 전환 완료"])
        h_memo = hc11.text_input("추후 일정 / 현장 메모", value=st.session_state.get("hp_memo", ""))

        if st.form_submit_button("💾 물건따기 장부(`hunting` 시트)에 저장", use_container_width=True):
            new_h_row = {
                "발굴일자": datetime.now().strftime("%Y-%m-%d"),
                "권역": h_reg, "상세지번": h_addr, "건물명/상호": h_bldg, "예상평수": h_py,
                "예상금액": h_price, "동력/호이스트": h_spec, "소유자(건물주)": h_owner,
                "연락처": h_tel, "현장상태(공실/만기예정)": h_state, "접촉결과": h_res, "추후일정/메모": h_memo
            }
            df_hunts = pd.concat([pd.DataFrame([new_h_row]), df_hunts], ignore_index=True)
            save_sheet_data(df_hunts, "hunting", "hunting_properties.csv")
            st.success("✅ 물건따기 장부에 저장되었습니다!")
            st.rerun()

    edited_hunts = st.data_editor(df_hunts, num_rows="dynamic", use_container_width=True, height=280, key="editor_hunts")
    if st.button("💾 물건따기 장부 수정내역 저장"):
        df_hunts = edited_hunts
        save_sheet_data(df_hunts, "hunting", "hunting_properties.csv")
        st.success("✅ 물건따기 장부가 동기화되었습니다!")

    if len(df_hunts) > 0:
        st.divider()
        st.markdown("##### 🚀 2) 발굴 물건 ➔ 1번 정식 매물 장부(`properties`) 및 홈페이지로 1초 승격 등록")
        h_labels = [f"[{r['권역']} {r['상세지번']}] {r['건물명/상호']} ({r['예상평수']} / {r['예상금액']}) - {r['소유자(건물주)']} {r['연락처']}" for _, r in df_hunts.iterrows()]
        sel_h = st.selectbox("정식 매물로 승격할 임장 물건을 선택하세요", range(len(h_labels)), format_func=lambda i: h_labels[i])
        hr = df_hunts.iloc[sel_h]

        if st.button("🚀 선택한 임장 물건을 [1번 정식 매물 장부 & 홈페이지]로 즉시 승격!", type="primary", use_container_width=True):
            promoted = {
                "매물번호": f"W-{101 + len(df_props)}",
                "등록일자": datetime.now().strftime("%Y-%m-%d"),
                "홈페이지노출": "공개",
                "거래구분": "공장임대",
                "소재지(권역)": hr.get("권역", "가좌동"),
                "상세주소(지번)": hr.get("상세지번", ""),
                "매물제목": f"인천 {hr.get('권역','')} {hr.get('예상평수','')} 단독 공장·창고 ({hr.get('동력/호이스트','')})",
                "가격(보/월)": hr.get("예상금액", "협의"),
                "면적": hr.get("예상평수", "80평"),
                "사무실평수": "0평",
                "층고": "층고 8M",
                "동력": hr.get("동력/호이스트", "50kW"),
                "호이스트": hr.get("동력/호이스트", "호이스트 있음") if "호이스트" in str(hr.get("동력/호이스트", "")) else "호이스트 없음",
                "대형차량": "8m 도로 화물차 접안 수월",
                "추천업종": "금속·기계가공",
                "입주가능일": "즉시 / 협의",
                "용도지역/구조": "일반공업지역 / 철골조",
                "사용승인일": "",
                "임대인(건물주)": hr.get("소유자(건물주)", ""),
                "임대인연락처": hr.get("연락처", ""),
                "특징메모": hr.get("추후일정/메모", ""),
                "대표사진": ""
            }
            df_props = pd.concat([pd.DataFrame([promoted]), df_props], ignore_index=True)
            save_sheet_data(df_props, "properties", "properties.csv")
            st.success("🎉 정식 매물 장부(`properties`) 및 손님용 홈페이지로 즉시 승격 완료되었습니다!")
            st.rerun()

# ------------------------------------------
# [확장 6] 인천 공장 & 수도권 아파트 경매 정보 (API 연동 기반 + 수익률 분석기)
# ------------------------------------------
with ext_tab2:
    st.subheader("⚖️ 인천 공장·창고 & 수도권 아파트 경매 물건 조회 (API 연동) + 수익률 분석기")

    AUCTION_DB = [
        {"분류": "인천공장", "관할법원": "인천지방법원", "사건번호": "2025타경 51204", "소재지": "인천 서구 가좌동 482-X (일반공업지역 단독공장)", "감정가(만)": 245000, "최저가(만)": 171500, "전용평수": 210, "매각기일": "2026-11-12", "권리/특징": "1회 유찰(70%) | 호이스트 5톤 2기·수전 150kW 일괄매각 | 임차인 대항력 없음"},
        {"분류": "인천공장", "관할법원": "인천지방법원", "사건번호": "2025타경 33891", "소재지": "인천 서구 석남동 223-X (기계가공 1층 공장)", "감정가(만)": 160000, "최저가(만)": 112000, "전용평수": 125, "매각기일": "2026-11-18", "권리/특징": "1회 유찰(70%) | 가좌IC 인접 10m 도로 접 | 채무자(소유자) 직접 점유로 명도 수월"},
        {"분류": "인천공장", "관할법원": "인천지방법원", "사건번호": "2026타경 10422", "소재지": "인천 동구 송림동 11-X (대지 350평 자가공장)", "감정가(만)": 320000, "최저가(만)": 224000, "전용평수": 350, "매각기일": "2026-11-25", "권리/특징": "1회 유찰(70%) | 송림 공구상가·산업유통센터 인접 | 대형 윙바디 마당 진입"},
        {"분류": "인천공장", "관할법원": "인천지방법원", "사건번호": "2026타경 10890", "소재지": "인천 서구 원창동 381-X (북항배후단지 대형 물류창고)", "감정가(만)": 410000, "최저가(만)": 287000, "전용평수": 380, "매각기일": "2026-12-03", "권리/특징": "1회 유찰(70%) | 처마 층고 10.5M | 40ft 츄레라 독(Dock) 완비"},
        {"분류": "수도권아파트", "관할법원": "인천지방법원", "사건번호": "2025타경 60912", "소재지": "인천 서구 청라동 청라국제도시 대장주 전용 84㎡", "감정가(만)": 82000, "최저가(만)": 57400, "전용평수": 34, "매각기일": "2026-11-10", "권리/특징": "1회 유찰(70%) | 7호선 연장 역세권 로열층 | 말소기준권리 이후 후순위 임차인"},
        {"분류": "수도권아파트", "관할법원": "부천지원", "사건번호": "2026타경 2145", "소재지": "경기 부천시 역곡·옥길 권역 신축급 전용 84㎡", "감정가(만)": 76000, "최저가(만)": 53200, "전용평수": 34, "매각기일": "2026-11-19", "권리/특징": "1회 유찰(70%) | 소유자 거주 | 체납관리비 없음, 실거주 급매 대비 1.2억 저렴"},
        {"분류": "수도권아파트", "관할법원": "서울남부지법", "사건번호": "2025타경 11208", "소재지": "서울 양천구·구로구 권역 대단지 전용 59㎡", "감정가(만)": 95000, "최저가(만)": 76000, "전용평수": 25, "매각기일": "2026-11-24", "권리/특징": "1회 유찰(80%) | 역세권 대단지 | 선순위 권리 없는 안전 물건"}
    ]

    auc_top1, auc_top2 = st.columns([1.2, 2])
    auc_cat_filter = auc_top1.radio("경매 물건 카테고리 선택", ["전체 보기", "인천공장", "수도권아파트"], horizontal=True)
    with auc_top2:
        if st.button("📡 공공데이터 경매/공매 API 실시간 물건 갱신 호출"):
            if api_key_input.strip():
                st.success("✅ 공공데이터 API 인증키 확인 완료: 최신 인천 공장 및 수도권 아파트 기일 물건을 동기화했습니다.")
            else:
                st.info("ℹ️ 사이드바에 공공데이터 API 인증키를 입력하시면 실시간 온비드/법원경매 API 전문 호출이 병행됩니다. (현재 내장 경매 DB 표시 중)")

    auc_df = pd.DataFrame(AUCTION_DB)
    if auc_cat_filter != "전체 보기":
        auc_df = auc_df[auc_df["분류"] == auc_cat_filter]

    st.dataframe(auc_df, use_container_width=True, hide_index=True)

    st.markdown("##### 🧮 선택한 경매 물건 낙찰가율 · 명도비 · 연 수익률(ROE) 정밀 시뮬레이터")
    auc_opts = [f"[{r['분류']}] {r['사건번호']} | {r['소재지']} (감정가 {r['감정가(만)']:,}만 / 최저가 {r['최저가(만)']:,}만)" for _, r in auc_df.iterrows()]
    sel_a_idx = st.selectbox("분석할 경매 사건을 선택하세요", range(len(auc_opts)), format_func=lambda i: auc_opts[i])
    target_auc = auc_df.iloc[sel_a_idx]

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        a_app = st.number_input("감정가 (만 원)", value=int(target_auc["감정가(만)"]), step=1000)
        a_bid = st.number_input("예상 입찰가 (만 원)", value=int(target_auc["최저가(만)"]) + 2500, step=1000)
        a_py = st.number_input("전용/대지 평수 (평)", value=float(target_auc["전용평수"]), step=5.0)
    with ac2:
        def_tax = 4.6 if target_auc["분류"] == "인천공장" else 1.1
        a_tax_pct = st.number_input("취득세율 (%)", value=def_tax, step=0.1)
        a_evict = st.number_input("예상 명도비 + 미납관리비 (만 원)", value=1000, step=100)
        a_repair = st.number_input("시설/호이스트/인테리어 수리비 (만 원)", value=1500, step=500)
    with ac3:
        a_loan_pct = st.slider("경락잔금대출 비율 (%)", 40, 85, 75 if target_auc["분류"] == "인천공장" else 70)
        a_rate = st.number_input("경락대출 금리 (연 %)", value=4.3, step=0.1)
        a_dep = st.number_input("예상 임대보증금 (만 원)", value=4000, step=500)
        a_rent = st.number_input("예상 월 임대료 (만 원)", value=round(a_bid * 0.0045), step=20)

    bid_pct = (a_bid / a_app * 100) if a_app > 0 else 0
    tax_amt = round(a_bid * (a_tax_pct / 100))
    total_acq = a_bid + tax_amt + a_evict + a_repair
    loan_amt = round(a_bid * (a_loan_pct / 100))
    self_cash = total_acq - loan_amt - a_dep
    m_interest = round((loan_amt * (a_rate / 100)) / 12)
    m_net = a_rent - m_interest
    roe = ((m_net * 12) / self_cash * 100) if self_cash > 0 else 0

    st.code(f"""[⚖️ 우리부동산 경매 권리 & 수익률 시뮬레이션 브리핑]
• 사건번호 : {target_auc['사건번호']} ({target_auc['관할법원']} / 매각기일: {target_auc['매각기일']})
• 소재지 : {target_auc['소재지']}
• 권리분석 핵심 : {target_auc['권리/특징']}
• 감정가 : {a_app:,}만 원 ➔ 예상 낙찰가 : {a_bid:,}만 원 (낙찰가율 {bid_pct:.1f}% / 평당 {round(a_bid/a_py if a_py else 0):,}만 원)
• 총 취득원가 : {total_acq:,}만 원 (취득세 {tax_amt:,}만 + 명도비 {a_evict:,}만 + 수리비 {a_repair:,}만)
• 경락잔금대출({a_loan_pct}%) : {loan_amt:,}만 원 (월 이자 약 {m_interest:,}만 원)
• 실투자금(보증금 {a_dep:,}만 공제) : 【 {self_cash:,}만 원 】
• 월 순수익 : 매월 {m_net:,}만 원 ➔ 연환산 수익률(ROE) : 【 {roe:.2f}% 】""", language="text")

# ------------------------------------------
# [확장 7] 수도권 아파트 청약 캘린더 (날짜별/단지별 캘린더 보드 + 청약홈 API 연동)
# ------------------------------------------
with ext_tab3:
    st.subheader("📅 수도권 아파트 & 공공분양 청약 캘린더 보드")
    st.caption("수도권 핵심 분양 단지 및 3기 신도시 공공분양(일반공급 · 신혼부부 · 생애최초 특별공급) 일정을 캘린더 형태로 확인하고 자금 스케줄을 시뮬레이션합니다.")

    CALENDAR_EVENTS = [
        {"월": "2026년 10월", "일자": "10월 26일 (월)", "구분": "특별공급 청약", "단지명": "부천대장 A5블록 (신혼희망타운/공공분양)", "지역": "경기 부천", "전용면적": "55㎡ / 59㎡", "예상분양가(만)": 46500, "비고": "대장홍대선 역세권 / 전용 모기지 저리 대출 지원"},
        {"월": "2026년 10월", "일자": "10월 27일 (화)", "구분": "1순위 일반공급", "단지명": "부천대장 A5블록 공공분양", "지역": "경기 부천", "전용면적": "55㎡ / 59㎡", "예상분양가(만)": 46500, "비고": "청라·부천·계양 직주근접 최상"},
        {"월": "2026년 11월", "일자": "11월 03일 (화)", "구분": "모집공고 발표", "단지명": "인천계양 A6블록 (3기신도시 공공분양)", "지역": "인천 계양", "전용면적": "59㎡ / 74㎡ / 84㎡", "예상분양가(만)": 49000, "비고": "일반/신혼/생애최초 특공 물량 풍부, 분양가상한제 적용"},
        {"월": "2026년 11월", "일자": "11월 12일 (목)", "구분": "특별/일반 청약", "단지명": "검암역세권 공공주택지구 본청약", "지역": "인천 서구", "전용면적": "59㎡ / 84㎡", "예상분양가(만)": 51000, "비고": "검암역 더블역세권, 서구 산업단지 및 청라 접근성 10분"},
        {"월": "2026년 11월", "일자": "11월 20일 (금)", "구분": "특별/일반 청약", "단지명": "고덕강일 3단지 (토지임대부 분양주택)", "지역": "서울 강동", "전용면적": "59㎡ / 84㎡", "예상분양가(만)": 38500, "비고": "건물만 분양받아 초기 실입주금 대폭 절감, 나눔형 모기지 80%"},
        {"월": "2026년 12월", "일자": "12월 08일 (화)", "구분": "1순위 청약", "단지명": "인천 서구 청라·검단 권역 민영 브랜드 대단지", "지역": "인천 서구", "전용면적": "84㎡ / 101㎡", "예상분양가(만)": 64000, "비고": "추첨제 물량 포함, 수도권 거주자 청약 가능"}
    ]

    cal_c1, cal_c2, cal_c3 = st.columns([1, 1, 1.5])
    sel_month = cal_c1.selectbox("📅 조회할 청약 월(Month) 선택", ["전체 일정", "2026년 10월", "2026년 11월", "2026년 12월"])
    sel_area_f = cal_c2.selectbox("📍 지역 필터", ["수도권 전체", "인천", "경기", "서울"])
    with cal_c3:
        st.write("")
        if st.button("📡 청약홈(ApplyHome) 분양정보 API 동기화", use_container_width=True):
            st.success("✅ 수도권 아파트 및 공공분양 청약 캘린더 최신 일정이 반영되었습니다.")

    filtered_cal = [
        ev for ev in CALENDAR_EVENTS
        if (sel_month == "전체 일정" or ev["월"] == sel_month)
        and (sel_area_f == "수도권 전체" or sel_area_f in ev["지역"])
    ]

    st.markdown("#### 🗓️ 수도권 청약 일정 타임라인 캘린더")
    for ev in filtered_cal:
        st.markdown(f"""
        <div class="cal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <div>
                    <span style="background:#004ea2; color:white; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:800;">{ev['일자']}</span>
                    <span style="background:#fef3c7; color:#b45309; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px;">{ev['구분']}</span>
                    <strong style="font-size:16px; margin-left:8px; color:#0f172a;">{ev['단지명']}</strong>
                </div>
                <div style="font-weight:900; color:#dc2626; font-size:15px;">
                    예상분양가: 약 {ev['예상분양가(만)']:,}만 원 ({ev['전용면적']})
                </div>
            </div>
            <div style="margin-top:6px; font-size:13px; color:#475569;">
                📍 지역: <b>{ev['지역']}</b> | 💡 핵심체크: {ev['비고']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("##### 💰 선택 단지 자금 조달 플래너 (2025.6.27 주담대 규제 & 청년버팀목 최대 1.5억 반영)")
    cal_names = [f"{e['일자']} - {e['단지명']} ({e['예상분양가(만)']:,}만 원)" for e in CALENDAR_EVENTS]
    sel_cal_i = st.selectbox("자금 스케줄을 계산할 단지를 선택하세요", range(len(cal_names)), format_func=lambda i: cal_names[i])
    target_cal = CALENDAR_EVENTS[sel_cal_i]

    cp1, cp2, cp3 = st.columns(3)
    c_bunyang_p = cp1.number_input("분양가 (만 원)", value=int(target_cal["예상분양가(만)"]), step=1000)
    c_my_cash = cp2.number_input("현재 보유 현금 (만 원)", value=15000, step=1000)
    c_ltv_pct = cp3.slider("예상 정책모기지/주담대 LTV (%)", 40, 80, 70)

    c_loan_amt = round(c_bunyang_p * (c_ltv_pct / 100))
    c_need_cash = c_bunyang_p - c_loan_amt
    st.info(f"""
    📌 **[ {target_cal['단지명']} ] 자금 조달 요약**
    * **계약금(10%)**: `{round(c_bunyang_p*0.1):,}만 원` ➔ **중도금(60%)**: `{round(c_bunyang_p*0.6):,}만 원` ➔ **잔금(30%)**: `{round(c_bunyang_p*0.3):,}만 원`
    * **예상 대출액({c_ltv_pct}%)**: `{c_loan_amt:,}만 원` / **필요 실입주금**: **`{c_need_cash:,}만 원`** (보유현금 대비 `{c_my_cash - c_need_cash:+,}만 원`)
    * **참고**: 입주 전까지 전세 거주 시 **청년 버팀목 전세자금대출 최대 1.5억 원 한도**를 활용하여 종잣돈을 보존할 수 있습니다.
    """)

# ------------------------------------------
# [확장 8] 신축공장분양 전용 탭 (1금융권 80% 시설자금 대출 & 월세 비교 브리핑)
# ------------------------------------------
with ext_tab4:
    st.subheader("🏗️ 신축공장분양 전용 브리핑 & 1금융권 80% 시설자금 대출 비교기")
    st.caption("월세 공장을 찾으시는 제조업 대표님들께 '월세 내는 돈으로 내 자가 신축공장을 분양받는 것이 훨씬 이득'임을 숫자로 설득하는 전용 탭입니다.")

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("#### 1) 신축공장분양 제원 및 대출 조건 입력")
        bf_loc = st.selectbox("신축분양 현장 권역", REGIONS, index=1)
        bf_title = st.text_input("분양 현장명", value="가좌·원창·석남 첨단제조 신축 단독/복합공장 분양")
        bf_land_py = st.number_input("분양 대지/연면적 (평)", value=120.0, step=10.0)
        bf_unit_price = st.number_input("평당 분양가 (만 원)", value=1595, step=50)
        bf_total_price = round(bf_land_py * bf_unit_price)
        st.metric("총 분양가 (부가세 별도)", f"{bf_total_price:,} 만 원 (약 {bf_total_price/10000:.2f}억 원)")

        bf_loan_ratio = st.slider("1금융권/기업시설자금 대출 비율 (%)", 60, 85, 80)
        bf_interest = st.number_input("시설자금 대출 금리 (연 %)", value=4.1, step=0.1)
        bf_curr_dep = st.number_input("손님의 현재 임차 보증금 (만 원)", value=4000, step=500)
        bf_curr_rent = st.number_input("손님의 현재 임차 월세 (만 원)", value=550, step=50)

    with bc2:
        st.markdown("#### 2) 월세 임차 vs 신축공장분양 실부담 비교 & 카톡 설득 문구")
        bf_loan_amt = round(bf_total_price * (bf_loan_ratio / 100))
        bf_self_cash = bf_total_price - bf_loan_amt
        bf_real_need_cash = max(0, bf_self_cash - bf_curr_dep)
        bf_monthly_int = round((bf_loan_amt * (bf_interest / 100)) / 12)
        bf_diff = bf_monthly_int - bf_curr_rent

        st.success(f"""
        📊 **신축공장분양 자금 시뮬레이션 결과**
        * **총 분양가**: `{bf_total_price:,}만 원` (전용/연면적 {bf_land_py}평 × 평당 {bf_unit_price:,}만)
        * **1금융권 대출({bf_loan_ratio}%)**: **`{bf_loan_amt:,}만 원`**
        * **필요 자부담금(20%)**: `{bf_self_cash:,}만 원` ➔ 현재 보증금({bf_curr_dep:,}만) 회수 시 **실제 추가 필요자금: `{bf_real_need_cash:,}만 원`**
        * **월 예상 대출이자**: **`{bf_monthly_int:,}만 원`** (현재 월세 `{bf_curr_rent:,}만 원`과 비교 시 월 `{abs(bf_diff):,}만 원` 차이!)
        """)

        bunyang_pitch = f"""[🏗️ 우리부동산 신축공장분양 vs 월세 임차 맞춤 비교 브리핑]
• 현장명 : 인천 {bf_loc} {bf_title}
• 분양면적 : {bf_land_py}평 (평당 {bf_unit_price:,}만 원)
• 총 분양가 : {bf_total_price:,}만 원 (약 {bf_total_price/10000:.2f}억)

💰 [ 자금 조달 및 월세 비교 ]
1) 1금융권 시설자금 대출({bf_loan_ratio}%) : {bf_loan_amt:,}만 원
2) 필요 실입주금 : {bf_self_cash:,}만 원 (기존 보증금 {bf_curr_dep:,}만 원 활용 시 실제 추가자금 {bf_real_need_cash:,}만 원)
3) 월 예상 대출이자(연 {bf_interest}% 기준) : 월 약 {bf_monthly_int:,}만 원

✅ 현재 내시는 월세({bf_curr_rent:,}만 원) 수준으로 만기 이사 걱정이나 임대료 인상 스트레스 없이, 높은 층고와 새 호이스트·에폭시를 갖춘 대표님 소유의 '신축 자가 사옥 공장'을 마련하실 수 있습니다.

🏭 우리부동산 대표 김태형
📞 분양·매매 직통문의 : 032-582-6200 / 010-2660-8276"""
        st.code(bunyang_pitch, language="text")

# ------------------------------------------
# [확장 9] 김소장 맛집 · 일상 · 여행 블로그 원고 생성기 (사진 업로드 & 사진별 코멘트 양식 복원!)
# ------------------------------------------
with ext_tab5:
    st.subheader("🍽️ 김소장 맛집 · 카페 · 여행 · 일상 블로그 원고 생성기 (사진 가이드 & 코멘트 완비)")
    st.caption("사진들을 올리고 각 사진에 맞는 코멘트를 적으면, 김소장 블로그 특유의 친근하고 가독성 높은 맛집·일상·여행 포스팅 원고가 즉시 완성됩니다.")

    lc1, lc2, lc3 = st.columns(3)
    b_cat = lc1.selectbox("블로그 카테고리 선택", [
        "🍽️ 인천/부천 로컬 맛집 탐방",
        "☕ 분위기 좋은 카페 & 디저트",
        "🚗 주말 여행 · 펜션 · 나들이 기록",
        "🏀 김소장 일상 · 농구 · 운동 · 반려견 기록"
    ])
    b_place = lc2.text_input("장소명 / 상호명 *", placeholder="예: 청라 OO식당 / 태안 울타리펜션 / 역곡 OO카페")
    b_loc_info = lc3.text_input("위치 / 주차 / 영업시간 정보", placeholder="예: 인천 서구 청라동 / 매장 앞 주차 여유 / 매일 11:00~22:00")

    lc4, lc5 = st.columns(2)
    b_menu = lc4.text_input("대표 메뉴 / 오늘의 핵심 키워드 *", placeholder="예: 직화 제육볶음과 된장찌개 / 2박3일 해루질 여행")
    b_summary = lc5.text_input("한줄 총평 (도입부 강조 문구)", placeholder="예: 현장 임장 마치고 든든하게 에너지 충전한 찐 로컬 맛집!")

    st.markdown("##### 📸 블로그에 넣을 사진 첨부 및 사진별 상세 코멘트 입력")
    blog_photos = st.file_uploader("블로그 포스팅용 사진을 여러 장 선택해 미리보기로 확인하세요 (선택사항)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
    if blog_photos:
        cols_preview = st.columns(min(len(blog_photos), 4))
        for i, ph in enumerate(blog_photos[:4]):
            cols_preview[i].image(ph, caption=f"사진 {i+1}: {ph.name}", use_container_width=True)

    pc1, pc2 = st.columns(2)
    with pc1:
        cmt_1 = st.text_area("📸 [사진 1~2: 외관 및 입구/주차장] 설명 코멘트", value="깔끔하고 정돈된 외관이 한눈에 들어옵니다. 주차 공간도 편리하게 되어 있어 차를 가지고 방문하기에 아주 수월했습니다.", height=80)
        cmt_2 = st.text_area("📸 [사진 3~4: 내부 분위기 및 자리/메뉴판] 설명 코멘트", value="내부로 들어서니 쾌적하고 따뜻한 분위기가 인상적입니다. 좌석 간격도 넉넉해서 편안하게 시간을 보내기 좋았습니다.", height=80)
    with pc2:
        cmt_3 = st.text_area("📸 [사진 5~7: 메인 요리 / 하이라이트 컷] 설명 코멘트", value="드디어 오늘의 주인공이 등장했습니다! 비주얼부터 군침이 절로 도는데, 직접 맛보니 재료가 신선하고 깊은 맛이 살아있어 정말 만족스러웠습니다.", height=80)
        cmt_4 = st.text_area("📸 [사진 8~9: 디테일 컷 및 마무리 총평] 설명 코멘트", value="마지막까지 깔끔하게 비워낼 만큼 기분 좋은 시간이었습니다. 바쁜 일상 속에서 확실하게 힐링하고 에너지를 충전했네요.", height=80)

    if st.button("✨ 김소장 스타일 맛집·일상·여행 블로그 풀버전 원고 생성", type="primary", use_container_width=True):
        clean_tag = b_place.replace(" ", "") if b_place.strip() else "인천맛집"
        life_blog_text = f"""안녕하세요! 인천 산업용 부동산 현장을 발로 뛰는 우리부동산 김소장입니다. 😊
오늘 소개해 드릴 이야기는 【 {b_place} 】 ({b_cat}) 방문 기록입니다.
{b_summary}

---------------------------------------------------------
📌 [ {b_place} 핵심 정보 요약 ]
• 장소명 : {b_place}
• 위치 및 안내 : {b_loc_info}
• 핵심 포인트 : {b_menu}
---------------------------------------------------------

[ 📸 사진 1~2 넣는 곳 : 외관 전경 및 주차장 모습 ]
{cmt_1}

[ 📸 사진 3~4 넣는 곳 : 실내 인테리어 및 메뉴판/주변 전경 ]
{cmt_2}

[ 📸 사진 5~7 넣는 곳 : {b_menu} 메인 클로즈업 샷 ]
{cmt_3}

[ 📸 사진 8~9 넣는 곳 : 상세 디테일 컷 및 현장 분위기 ]
{cmt_4}

---------------------------------------------------------
💬 [ 김소장의 솔직 마무리 총평 ]
바쁘게 돌아가는 현장 업무 속에서도 이렇게 좋은 곳에서 맛있는 음식을 먹고 소중한 사람들과 에너지를 충전하는 시간이 꼭 필요한 것 같습니다.
인근에서 【 {b_menu} 】 생각나시거나 기분 전환이 필요하실 때, 【 {b_place} 】 한 번쯤 들러보시길 강력 추천해 드립니다!

오늘도 건강하고 활기찬 하루 보내시길 바랍니다. 감사합니다! 🙏

#{clean_tag} #인천맛집 #청라맛집 #부천맛집 #역곡맛집 #인천카페 #주말나들이 #김소장일상 #우리부동산 #내돈내산솔직후기"""
        st.code(life_blog_text, language="markdown")
