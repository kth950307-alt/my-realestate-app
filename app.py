import streamlit as st
import pandas as pd
import datetime
import re
import json
import os
import base64
from io import BytesIO

# 외부 라이브러리 안전 임포트
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

# Streamlit 부분 렌더링(깜빡임 방지) 데코레이터 호환 처리
if hasattr(st, "fragment"):
    st_fragment = st.fragment
elif hasattr(st, "experimental_fragment"):
    st_fragment = st.experimental_fragment
else:
    def st_fragment(func):
        return func

# ==========================================
# 0. 페이지 기본 설정 및 스타일링
# ==========================================
st.set_page_config(
    page_title="우리부동산 통합업무시스템 Pro",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
        color: white;
        padding: 1.25rem 1.6rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .status-ok {
        background-color: #ecfdf5;
        border-left: 5px solid #10b981;
        color: #065f46;
        padding: 0.65rem 1rem;
        border-radius: 6px;
        font-weight: 700;
        margin-bottom: 0.7rem;
    }
    .alert-callback {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        border-left: 8px solid #dc2626;
        color: #991b1b;
        padding: 1rem 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 10px rgba(220,38,38,0.08);
    }
    .match-box {
        background-color: #eff6ff;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .kpi-title { font-size: 0.8rem; color: #475569; font-weight: 700; margin-bottom: 3px; }
    .kpi-val { font-size: 1.35rem; color: #0f172a; font-weight: 900; }
    .card-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.15rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .sidebar-call-card {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        border-left: 4px solid #e11d48;
        border-radius: 8px;
        padding: 0.65rem 0.8rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
    }
    .badge-blue { background-color: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
    .badge-red { background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
    .badge-green { background-color: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 상수 및 표준 컬럼 규격 정의 (구글 시트 & index.html 완벽 호환)
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1oTTZ1ok-quer9_NR5v5hEFYpRiOrR8tAwwo7UPnwRco/edit"

PROP_COLUMNS = [
    "등록일자", "매물번호", "거래구분", "권역", "해당층수", "홈페이지노출",
    "매물제목", "가격설명", "보증금_매매가", "월세", "전용평수", "사무실평수",
    "층고", "전력", "호이스트유무", "호이스트제원", "도로조건", "입주날짜",
    "추천업종", "상세지번", "건물주성함", "건물주연락처", "용도지역",
    "사용승인일", "핵심특징", "대표사진"
]

# 고객 CRM 장부: 리마인드예정일, 최근통화일, 중요도 추가로 콜백 영업 완벽 지원
CUST_COLUMNS = [
    "등록일자", "중요도", "고객명", "연락처", "희망거래", "선호권역", "희망층수",
    "최소평수", "최대예산_보증금", "최대월세", "필수전력", "호이스트필수",
    "업종", "진행상태", "최근통화일", "리마인드예정일", "상세메모"
]

HUNT_COLUMNS = [
    "등록일자", "권역", "상세지번", "건물명_상호", "해당층수", "예상평수",
    "예상금액", "동력_호이스트", "소유자성함", "연락처", "현장상태",
    "접촉결과", "추후일정_메모"
]

REGIONS = ["석남동", "가좌동", "원창동", "경서동", "도화동", "송림동", "송현동", "기타/인천전역"]
DEAL_TYPES = ["공장임대", "공장매매", "창고임대", "창고매매", "신축공장분양", "토지매매", "지식산업센터"]
FLOOR_OPTIONS = [
    "지상 1층", "지상 2층", "지상 3층", "지상 4층",
    "지상 5층 이상", "지하 1층", "건물 전체(통임대/통매매)", "기타(직접입력)"
]
CUST_STATUS_OPTIONS = ["🔥 급구(집중케어)", "📞 콜백대기(리마인드)", "👀 매물브리핑완료", "🤝 현장미팅예정", "✅ 계약완료", "⏸️ 보류"]

LOCAL_CACHE_FILE = "local_backup_cache.json"

# ==========================================
# 2. 초고속 인메모리 우선(In-Memory First) + 비동기 시트 동기화 엔진
# ==========================================
def load_local_disk_cache():
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            with open(LOCAL_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"properties": [], "customers": [], "hunting": []}

def save_local_disk_cache(cache_data):
    try:
        with open(LOCAL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

@st.cache_resource(show_spinner=False)
def get_gsheet_workbook():
    if not GSPREAD_AVAILABLE:
        return None, "gspread 라이브러리 미설치"
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "secrets.toml 내 [gcp_service_account] 없음"
        
        sec = dict(st.secrets["gcp_service_account"])
        if "private_key" in sec:
            sec["private_key"] = sec["private_key"].replace("\\n", "\n").strip()

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(sec, scopes=scopes)
        client = gspread.authorize(creds)
        sh = client.open_by_url(SPREADSHEET_URL)
        return sh, "OK"
    except Exception as e:
        return None, str(e)

def ensure_worksheet_fast(sh, title, columns):
    try:
        ws = sh.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(columns) + 5)
        ws.append_row(columns)
        return ws
    return ws

def normalize_df(records_or_df, expected_cols):
    if isinstance(records_or_df, pd.DataFrame):
        df = records_or_df.copy()
    elif records_or_df:
        df = pd.DataFrame(records_or_df)
    else:
        df = pd.DataFrame(columns=expected_cols)
    for col in expected_cols:
        if col not in df.columns:
            if col == "중요도":
                df[col] = "⭐ 일반"
            elif col == "진행상태":
                df[col] = "📞 콜백대기(리마인드)"
            elif col in ("최근통화일", "리마인드예정일"):
                df[col] = datetime.date.today().strftime("%Y-%m-%d")
            else:
                df[col] = ""
    return df[expected_cols].fillna("").astype(str)

def init_memory_db(force_reload=False):
    if "mem_db" not in st.session_state or force_reload:
        disk_cache = load_local_disk_cache()
        st.session_state.mem_db = {
            "properties": normalize_df(disk_cache.get("properties", []), PROP_COLUMNS),
            "customers": normalize_df(disk_cache.get("customers", []), CUST_COLUMNS),
            "hunting": normalize_df(disk_cache.get("hunting", []), HUNT_COLUMNS),
        }
        sh, status = get_gsheet_workbook()
        if sh is not None and status == "OK":
            sheet_specs = [
                ("properties", PROP_COLUMNS),
                ("customers", CUST_COLUMNS),
                ("hunting", HUNT_COLUMNS)
            ]
            for s_name, cols in sheet_specs:
                try:
                    ws = ensure_worksheet_fast(sh, s_name, cols)
                    rows = ws.get_all_values()
                    if len(rows) > 1:
                        headers = rows[0]
                        df_loaded = pd.DataFrame(rows[1:], columns=headers)
                        st.session_state.mem_db[s_name] = normalize_df(df_loaded, cols)
                    elif len(rows) == 0:
                        ws.append_row(cols)
                except Exception:
                    pass
            save_local_disk_cache({
                k: v.to_dict(orient="records") for k, v in st.session_state.mem_db.items()
            })

def get_fast_df(sheet_name, expected_cols):
    init_memory_db(force_reload=False)
    return st.session_state.mem_db.get(sheet_name, pd.DataFrame(columns=expected_cols)).copy()

def append_row_fast(sheet_name, expected_cols, row_dict):
    init_memory_db(force_reload=False)
    clean_row = {col: str(row_dict.get(col, "")) for col in expected_cols}
    
    cur_df = st.session_state.mem_db[sheet_name]
    new_df = pd.concat([cur_df, pd.DataFrame([clean_row])], ignore_index=True)
    st.session_state.mem_db[sheet_name] = normalize_df(new_df, expected_cols)
    
    save_local_disk_cache({
        k: v.to_dict(orient="records") for k, v in st.session_state.mem_db.items()
    })

    sh, status = get_gsheet_workbook()
    if sh is not None and status == "OK":
        try:
            ws = ensure_worksheet_fast(sh, sheet_name, expected_cols)
            headers = ws.row_values(1)
            if headers != expected_cols:
                ws.update("A1", [expected_cols])
            ordered_vals = [clean_row[col] for col in expected_cols]
            ws.append_row(ordered_vals, value_input_option="USER_ENTERED")
            return True, "구글 스프레드시트 실시간 기록 완료"
        except Exception as e:
            return False, f"메모리/로컬 저장 완료 (구글 시트 동기화 지연: {e})"
    return False, f"메모리/로컬 저장 완료 ({status})"

def overwrite_sheet_fast(sheet_name, expected_cols, edited_df):
    init_memory_db(force_reload=False)
    clean_df = normalize_df(edited_df, expected_cols)
    st.session_state.mem_db[sheet_name] = clean_df

    save_local_disk_cache({
        k: v.to_dict(orient="records") for k, v in st.session_state.mem_db.items()
    })

    sh, status = get_gsheet_workbook()
    if sh is not None and status == "OK":
        try:
            ws = ensure_worksheet_fast(sh, sheet_name, expected_cols)
            ws.clear()
            all_values = [expected_cols] + clean_df.astype(str).values.tolist()
            ws.update("A1", all_values, value_input_option="USER_ENTERED")
            return True, "구글 스프레드시트 전체 동기화 완료"
        except Exception as e:
            return False, f"메모리 저장 완료 (시트 업데이트 실패: {e})"
    return False, "메모리 및 로컬 캐시 업데이트 완료"

def compress_image_to_base64(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        if PIL_AVAILABLE:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((800, 600))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
        else:
            b64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return ""

# ==========================================
# 3. 스마트 매칭 점수 계산 엔진 (매물 <-> 손님 양방향)
# ==========================================
def parse_num(val, default=0.0):
    try:
        m = re.search(r"[\d.]+", str(val).replace(",", ""))
        return float(m.group(0)) if m else default
    except Exception:
        return default

def calculate_match_score(prop_row, cust_row):
    """매물 1건과 고객 1명의 조건 적합도를 100점 만점으로 산출합니다."""
    score = 0
    reasons = []

    p_deal = str(prop_row.get("거래구분", ""))
    c_deal = str(cust_row.get("희망거래", ""))
    if p_deal == c_deal or (p_deal[:2] == c_deal[:2]):
        score += 30
        reasons.append("거래일치")

    p_reg = str(prop_row.get("권역", ""))
    c_reg = str(cust_row.get("선호권역", ""))
    if c_reg in ("전체(인천서구)", "전체", "") or p_reg in c_reg or c_reg in p_reg:
        score += 25
        reasons.append(f"권역({p_reg})")

    p_area = parse_num(prop_row.get("전용평수", 0), 0)
    c_area = parse_num(cust_row.get("최소평수", 0), 0)
    if c_area <= 0 or (p_area >= c_area * 0.8 and p_area <= c_area * 1.6):
        score += 20
        reasons.append(f"평수적합({int(p_area)}평)")
    elif p_area >= c_area * 0.7:
        score += 10
        reasons.append(f"평수근접({int(p_area)}평)")

    p_price = parse_num(prop_row.get("보증금_매매가", 0), 0)
    p_rent = parse_num(prop_row.get("월세", 0), 0)
    c_max_dep = parse_num(cust_row.get("최대예산_보증금", 0), 0)
    c_max_rent = parse_num(cust_row.get("최대월세", 0), 0)

    if "임대" in p_deal:
        if c_max_rent <= 0 or p_rent <= c_max_rent * 1.15:
            score += 15
            reasons.append("월세예산내")
    else:
        if c_max_dep <= 0 or p_price <= c_max_dep * 1.15:
            score += 15
            reasons.append("매매예산내")

    p_hoist = str(prop_row.get("호이스트유무", "없음"))
    c_hoist = str(cust_row.get("호이스트필수", "무관"))
    if "필수" in c_hoist:
        if p_hoist == "있음":
            score += 10
            reasons.append("호이스트보유")
        else:
            score -= 20
    else:
        score += 10

    return max(score, 0), ", ".join(reasons)

def is_callback_due(remind_str, status_str):
    """오늘 또는 이전 날짜로 리마인드 예정일이 도래했는지 판별합니다."""
    if "완료" in str(status_str) or "보류" in str(status_str):
        return False
    s = str(remind_str).strip()
    if not s:
        return True
    try:
        dt = datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
        return dt <= datetime.date.today()
    except Exception:
        return True

# 최초 1회 메모리 로드 실행
init_memory_db(force_reload=False)
sh_conn, conn_msg = get_gsheet_workbook()

df_p_global = get_fast_df("properties", PROP_COLUMNS)
df_c_global = get_fast_df("customers", CUST_COLUMNS)
df_h_global = get_fast_df("hunting", HUNT_COLUMNS)

# 오늘 연락해야 할 콜백 손님 자동 추출
due_customers = []
if not df_c_global.empty:
    for idx, r in df_c_global.iterrows():
        if is_callback_due(r.get("리마인드예정일", ""), r.get("진행상태", "")):
            due_customers.append(r)

# ==========================================
# 4. 왼쪽 사이드바: 상시 고정형 [오늘 연락할 손님 리마인드 보드]
# ==========================================
with st.sidebar:
    st.markdown("### 📞 오늘 연락할 손님 (콜백 알림)")
    if due_customers:
        st.error(f"🔥 오늘 챙겨야 할 손님 **{len(due_customers)}명**이 있습니다!")
        for dc in due_customers[:8]:
            st.markdown(f"""
            <div class="sidebar-call-card">
                <strong>{dc['중요도']} {dc['고객명']}</strong> ({dc['희망거래']})<br>
                📞 <a href="tel:{dc['연락처']}" style="color:#be123c;font-weight:900;">{dc['연락처']}</a><br>
                📍 {dc['선호권역']} | {dc['최소평수']}평↑ | 호이스트:{dc['호이스트필수']}<br>
                📝 <span style="color:#334155;">{dc['상세메모'][:35] if dc['상세메모'] else '안부 및 신규매물 브리핑 요망'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ 오늘 예정된 미처리 콜백 손님이 없습니다.")

    st.divider()
    st.markdown("### ⚙️ 구글 시트 & 홈페이지 제어")
    if sh_conn is not None and conn_msg == "OK":
        st.caption("🟢 구글 시트 양방향 실시간 연결됨")
    else:
        st.caption(f"🟡 로컬 캐시 모드 ({conn_msg})")

    if st.button("🔄 구글 시트 최신 데이터 강제 동기화", use_container_width=True):
        with st.spinner("구글 시트 동기화 중..."):
            init_memory_db(force_reload=True)
        st.toast("최신 시트 데이터를 불러왔습니다!", icon="✅")
        st.rerun()

    st.markdown(f"📊 [구글 스프레드시트 원본 열기 ↗]({SPREADSHEET_URL})")
    
    st.divider()
    st.markdown("#### 📥 3대 장부 엑셀(CSV) 즉시 백업")
    st.download_button(
        f"👥 손님장부 ({len(df_c_global)}명) 다운로드",
        data=df_c_global.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"우리부동산_고객장부_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    st.download_button(
        f"📋 매물장부 ({len(df_p_global)}건) 다운로드",
        data=df_p_global.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"우리부동산_매물장부_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    st.download_button(
        f"🎯 임장장부 ({len(df_h_global)}건) 다운로드",
        data=df_h_global.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"우리부동산_임장장부_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==========================================
# 5. 상단 헤더 & 오늘 연락할 손님 최우선 경고 배너
# ==========================================
st.markdown("""
<div class="main-header">
    <h2 style="margin:0; color:white;">🏭 우리부동산 영업·매칭 통합시스템 Pro (손님 리마인드 & 홈페이지 실시간 연동)</h2>
    <p style="margin:5px 0 0 0; opacity:0.92; font-size:0.92rem;">
        주력 권역: 석남동 · 가좌동 · 원창동 · 경서동 · 도화동 · 송림동 · 송현동 | 대표 공인중개사 김태형 (032-582-6200 / 010-2660-8276)
    </p>
</div>
""", unsafe_allow_html=True)

# 상단 콜백 리마인드 경고 배너 (손님 놓침 완벽 방지)
if due_customers:
    due_names = ", ".join([f"{c['고객명']}({c['선호권역']} {c['최소평수']}평↑)" for c in due_customers[:5]])
    st.markdown(f"""
    <div class="alert-callback">
        <div style="font-size:1.05rem; font-weight:900; margin-bottom:4px;">
            🚨 [오늘의 콜백 리마인드 알림] 지금 연락해야 할 손님이 총 <u>{len(due_customers)}명</u> 있습니다! (손님 안부 전화가 계약을 만듭니다)
        </div>
        <div style="font-size:0.92rem; color:#7f1d1d;">
            • 우선 연락 대상: <b>{due_names}</b> {'외 다수' if len(due_customers) > 5 else ''} ➔ 아래 <b>[👥 1. 손님 리마인드 장부 & 자동 매칭]</b> 탭에서 바로 매칭 매물을 확인하고 카톡/전화를 걸어보세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

# 상단 4대 업무 요약 KPI 바
k1, k2, k3, k4 = st.columns(4)
public_cnt = len(df_p_global[df_p_global["홈페이지노출"].str.contains("노출", na=False)]) if not df_p_global.empty else 0
active_cust_cnt = len(df_c_global[~df_c_global["진행상태"].str.contains("완료|보류", na=False)]) if not df_c_global.empty else 0

with k1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📞 오늘 연락할 리마인드 손님</div><div class="kpi-val" style="color:#dc2626;">{len(due_customers)}명 <span style="font-size:0.85rem;color:#475569;">(전체 진성손님 {active_cust_cnt}명)</span></div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📋 전체 보유 매물</div><div class="kpi-val">{len(df_p_global)}건</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🌐 홈페이지(index.html) 공개 매물</div><div class="kpi-val" style="color:#1d4ed8;">{public_cnt}건</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🎯 현장 임장 / 물건따기 타겟</div><div class="kpi-val">{len(df_h_global)}건</div></div>', unsafe_allow_html=True)

st.write("")

# ==========================================
# 6. 주업무 시스템 (손님 리마인드 장부를 1번 메인 탭으로 전면 배치!)
# ==========================================
main_tabs = st.tabs([
    "👥 1. 손님 리마인드 장부 & 자동 매칭 영업소 (메인)",
    "➕ 2. 새 매물 등록 (+대기손님 즉시 역매칭)",
    "📋 3. 전체 매물 통합장부 & 홈페이지 노출 관리",
    "💬 4. 카톡 멀티 브리핑 & 네이버 블로그 자동생성"
])

# ------------------------------------------
# [탭 1] 손님 리마인드 장부 & 양방향 스마트 매칭 영업소 (대폭 고도화)
# ------------------------------------------
@st_fragment
def render_crm_command_center():
    st.subheader("👥 찾는 손님(매수·임차) 리마인드 관리 & 보유 매물 원클릭 매칭")
    st.caption("전화 온 손님을 등록해 두면 리마인드 날짜에 맞춰 알림을 띄워주며, 손님을 선택하는 즉시 우리 매물 중 조건이 맞는 공장을 찾아 카톡 브리핑 문구까지 자동으로 뽑아줍니다.")

    df_custs = get_fast_df("customers", CUST_COLUMNS)
    df_props = get_fast_df("properties", PROP_COLUMNS)

    # 1) 상단: 손님 빠른 등록 아코디언 (평소엔 깔끔하게 열려 있거나 바로 입력 가능)
    with st.expander("➕ 전화 온 신규 손님 빠른 등록 (클릭하여 열기/닫기)", expanded=df_custs.empty):
        with st.form("crm_new_customer_form", clear_on_submit=True):
            c1, c2, c3, c4, c5 = st.columns([1, 1.2, 1.3, 1.1, 1.2])
            with c1:
                c_imp = st.selectbox("중요도 *", ["🔥 A급(급구)", "⭐ 일반", "💎 VIP(매수/대형)"])
            with c2:
                c_name = st.text_input("손님 성함 / 업체명 *", placeholder="예: 대성정밀 김대표님")
            with c3:
                c_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
            with c4:
                c_deal = st.selectbox("희망 거래 *", DEAL_TYPES)
            with c5:
                c_reg = st.selectbox("선호 권역 *", ["전체(인천서구)"] + REGIONS)

            c6, c7, c8, c9, c10 = st.columns(5)
            with c6:
                c_floor = st.selectbox("희망 층수", ["전체(무관)"] + FLOOR_OPTIONS)
            with c7:
                c_area = st.number_input("최소 필요 평수 (평)", min_value=0, value=80, step=10)
            with c8:
                c_dep = st.number_input("최대 보증금/매매예산 (만)", min_value=0, value=5000, step=500)
            with c9:
                c_rent = st.number_input("최대 월세 예산 (만)", min_value=0, value=300, step=20)
            with c10:
                c_hoist = st.selectbox("호이스트 필수 여부", ["무관", "있음 필수"])

            c11, c12, c13, c14 = st.columns([1.2, 1.2, 1, 2.2])
            with c11:
                c_power = st.text_input("필요 전력(kW) / 업종", placeholder="예: 100kW / 금속가공")
            with c12:
                c_status = st.selectbox("현재 진행상태", CUST_STATUS_OPTIONS)
            with c13:
                default_remind = datetime.date.today() + datetime.timedelta(days=3)
                c_remind = st.date_input("⏰ 다음 연락(리마인드) 날짜", value=default_remind)
            with c14:
                c_memo = st.text_input("통화 핵심 메모 (리마인드 사항)", placeholder="예: 현재 가좌동 임차중, 12월 만기라 11월 초에 다시 물건 보내드리기로 함")

            sub_c = st.form_submit_button("💾 손님 장부(customers)에 즉시 등록 및 매칭 시작", type="primary", use_container_width=True)
            if sub_c:
                new_cust = {
                    "등록일자": datetime.date.today().strftime("%Y-%m-%d"),
                    "중요도": c_imp,
                    "고객명": c_name if c_name.strip() else "신규문의고객",
                    "연락처": c_phone,
                    "희망거래": c_deal,
                    "선호권역": c_reg,
                    "희망층수": c_floor,
                    "최소평수": str(c_area),
                    "최대예산_보증금": str(c_dep),
                    "최대월세": str(c_rent),
                    "필수전력": c_power,
                    "호이스트필수": c_hoist,
                    "업종": c_power,
                    "진행상태": c_status,
                    "최근통화일": datetime.date.today().strftime("%Y-%m-%d"),
                    "리마인드예정일": c_remind.strftime("%Y-%m-%d"),
                    "상세메모": c_memo
                }
                append_row_fast("customers", CUST_COLUMNS, new_cust)
                st.toast(f"고객 등록 완료: {c_name}", icon="👥")
                st.rerun()

    # 2) 중단: 전체 손님 장부 필터 & 실시간 편집 테이블 (넓은 화면)
    st.markdown("#### 📋 대기 손님 통합 장부 (셀을 더블클릭하여 통화내용·리마인드 날짜를 바로 수정하세요)")
    cf1, cf2, cf3, cf4 = st.columns([1.2, 1.2, 1.2, 2])
    with cf1:
        filter_call = st.selectbox("📞 연락 시기별 보기", ["전체 손님 보기", "🚨 오늘 연락할 손님만 (콜백도래)", "🔥 A급(급구) 손님만"])
    with cf2:
        filter_c_deal = st.selectbox("희망 거래 필터", ["전체"] + DEAL_TYPES)
    with cf3:
        filter_c_reg = st.selectbox("선호 권역 필터", ["전체"] + REGIONS)
    with cf4:
        filter_c_kw = st.text_input("손님 이름 / 연락처 / 메모 검색", "")

    view_cust = df_custs.copy()
    is_c_filtered = False
    if not view_cust.empty:
        if filter_call == "🚨 오늘 연락할 손님만 (콜백도래)":
            mask_due = view_cust.apply(lambda r: is_callback_due(r.get("리마인드예정일", ""), r.get("진행상태", "")), axis=1)
            view_cust = view_cust[mask_due]
            is_c_filtered = True
        elif filter_call == "🔥 A급(급구) 손님만":
            view_cust = view_cust[view_cust["중요도"].str.contains("A급", na=False) | view_cust["진행상태"].str.contains("급구", na=False)]
            is_c_filtered = True

        if filter_c_deal != "전체":
            view_cust = view_cust[view_cust["희망거래"] == filter_c_deal]
            is_c_filtered = True
        if filter_c_reg != "전체":
            view_cust = view_cust[view_cust["선호권역"].str.contains(filter_c_reg, na=False)]
            is_c_filtered = True
        if filter_c_kw.strip():
            kw = filter_c_kw.strip().lower()
            view_cust = view_cust[view_cust.apply(lambda r: kw in " ".join(r.astype(str)).lower(), axis=1)]
            is_c_filtered = True

    cust_col_cfg = {
        "중요도": st.column_config.SelectboxColumn("중요도", options=["🔥 A급(급구)", "⭐ 일반", "💎 VIP(매수/대형)"], required=True),
        "진행상태": st.column_config.SelectboxColumn("진행상태", options=CUST_STATUS_OPTIONS, required=True),
        "희망거래": st.column_config.SelectboxColumn("희망거래", options=DEAL_TYPES),
        "호이스트필수": st.column_config.SelectboxColumn("호이스트필수", options=["무관", "있음 필수"]),
    }

    edited_cust = st.data_editor(
        view_cust,
        column_config=cust_col_cfg,
        num_rows="dynamic",
        use_container_width=True,
        height=300,
        key="crm_main_editor"
    )

    btn_c1, btn_c2 = st.columns([1.5, 1])
    with btn_c1:
        if st.button("💾 손님 장부 수정사항(통화메모/리마인드날짜) 구글 시트에 즉시 저장", type="primary", use_container_width=True):
            if is_c_filtered:
                base_c = df_custs.copy()
                base_c.loc[view_cust.index] = edited_cust
                target_c = base_c
            else:
                target_c = edited_cust
            ok, msg = overwrite_sheet_fast("customers", CUST_COLUMNS, target_c)
            if ok:
                st.toast("손님 장부 업데이트 완료!", icon="✅")
                st.rerun()
            else:
                st.warning(msg)
    with btn_c2:
        st.caption("💡 팁: 손님과 통화한 후 [최근통화일]과 [리마인드예정일]만 바꿔 저장해도 영업 누수가 0%가 됩니다.")

    st.divider()

    # 3) 하단: 선택한 손님 1:1 맞춤 매물 자동 매칭 & 원클릭 카톡 브리핑 생성기
    st.markdown("#### 🎯 손님 1:1 맞춤 매물 자동 매칭 & 원클릭 리마인드 카톡 발송")
    if df_custs.empty:
        st.info("위에서 손님을 1명 이상 등록하시면 보유 매물과의 자동 매칭이 시작됩니다.")
    else:
        cust_options = [
            f"[{r['중요도']}] {r['고객명']} ({r['연락처']}) | 희망: {r['선호권역']} {r['희망거래']} {r['최소평수']}평↑ | 리마인드: {r['리마인드예정일']} | 메모: {r['상세메모'][:25]}"
            for _, r in df_custs.iterrows()
        ]
        sel_c_label = st.selectbox("👇 지금 전화하거나 매물을 보내줄 손님을 선택하세요", cust_options)
        sel_c_idx = cust_options.index(sel_c_label)
        sel_c_row = df_custs.iloc[sel_c_idx]

        # 통화 완료 후 리마인드 날짜 원클릭 연기 버튼
        q_col1, q_col2, q_col3, q_col4 = st.columns([1.4, 1, 1, 1])
        with q_col1:
            st.markdown(f"**📞 직통 전화:** [{sel_c_row['연락처']}](tel:{sel_c_row['연락처']}) | **진행상태:** `{sel_c_row['진행상태']}`")
        with q_col2:
            if st.button("✅ 오늘 통화완료 (+3일 뒤 리마인드)", use_container_width=True):
                df_custs.at[sel_c_row.name, "최근통화일"] = datetime.date.today().strftime("%Y-%m-%d")
                df_custs.at[sel_c_row.name, "리마인드예정일"] = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
                overwrite_sheet_fast("customers", CUST_COLUMNS, df_custs)
                st.toast("통화일 갱신 및 3일 뒤 리마인드 설정 완료!", icon="📞")
                st.rerun()
        with q_col3:
            if st.button("📅 다음 주 연락 (+7일 뒤 리마인드)", use_container_width=True):
                df_custs.at[sel_c_row.name, "최근통화일"] = datetime.date.today().strftime("%Y-%m-%d")
                df_custs.at[sel_c_row.name, "리마인드예정일"] = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                overwrite_sheet_fast("customers", CUST_COLUMNS, df_custs)
                st.toast("다음 주 리마인드 설정 완료!", icon="📅")
                st.rerun()
        with q_col4:
            if st.button("🎉 이 손님 계약완료 처리", use_container_width=True):
                df_custs.at[sel_c_row.name, "진행상태"] = "✅ 계약완료"
                overwrite_sheet_fast("customers", CUST_COLUMNS, df_custs)
                st.toast("축하합니다! 계약완료 처리되었습니다.", icon="🎉")
                st.rerun()

        # 보유 매물 중 조건 매칭 실행
        if df_props.empty:
            st.warning("현재 등록된 매물(properties)이 없습니다. [2. 새 매물 등록] 탭에서 매물을 등록해 주세요.")
        else:
            matches = []
            for _, pr in df_props.iterrows():
                sc, rsn = calculate_match_score(pr, sel_c_row)
                if sc >= 45:
                    matches.append({
                        "매칭점수": sc,
                        "매칭사유": rsn,
                        "매물번호": pr["매물번호"],
                        "권역": pr["권역"],
                        "해당층수": pr["해당층수"],
                        "전용평수": pr["전용평수"],
                        "가격설명": pr["가격설명"],
                        "전력": pr["전력"],
                        "호이스트": f"{pr['호이스트유무']}({pr['호이스트제원']})",
                        "도로조건": pr["도로조건"],
                        "매물제목": pr["매물제목"],
                        "상세지번(비공개)": pr["상세지번"],
                        "건물주연락처": pr["건물주연락처"]
                    })

            if matches:
                m_df = pd.DataFrame(matches).sort_values(by="매칭점수", ascending=False)
                st.success(f"🔥 **{sel_c_row['고객명']}** 님 조건에 부합하는 추천 매물이 **{len(m_df)}건** 자동 매칭되었습니다!")
                st.dataframe(m_df, use_container_width=True, height=210)

                # 상위 매칭 매물로 즉시 손님 맞춤형 안부+추천 카톡 문구 생성
                top_matches = m_df.head(3)
                kakao_msg = [
                    f"안녕하세요 {sel_c_row['고객명']}님! 인천 서구 공장·창고 전문 우리부동산 김태형 대표공인중개사입니다.",
                    f"지난번 말씀해주신 조건({sel_c_row['선호권역']} / {sel_c_row['최소평수']}평 이상 / {sel_c_row['희망거래']})에 딱 맞는 알짜 매물이 나와 가장 먼저 연락드립니다.\n"
                ]
                for i, (_, mr) in enumerate(top_matches.iterrows(), 1):
                    kakao_msg.append(f"■ 추천 #{i}. [{mr['권역']} {mr['해당층수']}] {mr['매물제목']}")
                    kakao_msg.append(f" • 면적/금액 : 전용 {mr['전용평수']}평 / {mr['가격설명']}")
                    kakao_msg.append(f" • 설비/도로 : 전력 {mr['전력']} / 호이스트 {mr['호이스트']} / {mr['도로조건']}\n")
                kakao_msg.append("시간 괜찮으실 때 편하게 연락 주시면 현장 바로 안내해 드리겠습니다!")
                kakao_msg.append("📞 우리부동산 김태형 대표 직통: 010-2660-8276 / 사무실: 032-582-6200")

                st.markdown("##### 💬 손님에게 바로 보낼 맞춤형 안부 & 매물 추천 카톡 (우측 상단 복사 아이콘 클릭)")
                st.code("\n".join(kakao_msg), language="markdown")
            else:
                st.warning("현재 보유 매물 중 45점 이상 일치하는 매물이 없습니다.")

with main_tabs[0]:
    render_crm_command_center()

# ------------------------------------------
# [탭 2] 새 매물 등록 (+ 등록 즉시 대기 손님 자동 역매칭 알림)
# ------------------------------------------
@st_fragment
def render_new_property_tab():
    st.subheader("➕ 신규 공장 · 창고 · 신축공장분양 매물 등록 (+대기손님 자동 역매칭)")
    st.caption("매물을 등록하면 구글 시트와 손님용 홈페이지(index.html)에 실시간 반영되며, 동시에 이 조건을 기다리던 손님 명단이 즉시 아래에 나타납니다.")

    c_top1, c_top2, c_top3, c_top4 = st.columns(4)
    with c_top1:
        default_no = f"W-{datetime.datetime.now().strftime('%y%m%d-%H%M')}"
        p_no = st.text_input("매물번호 *", value=default_no)
    with c_top2:
        p_deal = st.selectbox("거래구분 *", DEAL_TYPES)
    with c_top3:
        p_region = st.selectbox("소재지 (주력 7대 권역) *", REGIONS)
    with c_top4:
        p_show = st.selectbox("홈페이지 노출 설정 *", ["노출(공개)", "비공개(내부장부용)"])

    # 층수 선택 세분화
    c_fl1, c_fl2, c_fl3, c_fl4 = st.columns(4)
    with c_fl1:
        p_floor_sel = st.selectbox("해당 층수 선택 *", FLOOR_OPTIONS, index=0)
    with c_fl2:
        if p_floor_sel == "기타(직접입력)":
            p_floor_custom = st.text_input("층수 직접 입력 *", value="", placeholder="")
            p_floor = p_floor_custom.strip() if p_floor_custom.strip() else "기타층"
        else:
            st.text_input("적용될 층수", value=p_floor_sel, disabled=True)
            p_floor = p_floor_sel
    with c_fl3:
        p_area1 = st.number_input("전용 평수 (공장/창고 바닥면적, 평) *", min_value=0.0, value=60.0, step=5.0)
    with c_fl4:
        p_area2 = st.number_input("2층/부속 사무실 평수 (없으면 0)", min_value=0.0, value=0.0, step=5.0)

    # 호이스트 유무('있음'/'없음') 및 빈 입력창
    c_ho1, c_ho2, c_ho3, c_ho4 = st.columns([1.1, 1.9, 1.5, 1.5])
    with c_ho1:
        p_hoist_ox = st.radio("호이스트 유무 *", ["없음", "있음"], horizontal=True)
    with c_ho2:
        p_hoist_spec = st.text_input(
            "호이스트 상세 제원 (직접 입력)",
            value="",
            placeholder="",
            disabled=(p_hoist_ox == "없음")
        )
    with c_ho3:
        p_height = st.text_input("층고 설명 (m)", value="", placeholder="")
    with c_ho4:
        p_power = st.text_input("계약 전력(동력 kW)", value="", placeholder="")

    c_mid1, c_mid2, c_mid3, c_mid4 = st.columns([2.2, 1.1, 1.1, 1.2])
    with c_mid1:
        p_title = st.text_input("홈페이지/블로그용 매물 제목 (비워두면 자동 생성) *", value="", placeholder="")
    with c_mid2:
        p_deposit = st.number_input("보증금 또는 매매·분양가 (만원) *", min_value=0, value=2000, step=100)
    with c_mid3:
        p_rent = st.number_input("월세 (만원, 매매 시 0)", min_value=0, value=200, step=10)
    with c_mid4:
        if p_area1 > 0:
            if "임대" in p_deal:
                unit_p = p_rent / p_area1
                st.text_input("💡 평당 월세 자동계산", value=f"평당 약 {unit_p:,.1f}만원", disabled=True)
            else:
                unit_p = p_deposit / p_area1
                st.text_input("💡 평당 매매가 자동계산", value=f"평당 약 {unit_p:,.0f}만원", disabled=True)
        else:
            st.text_input("💡 평당 단가", value="-", disabled=True)

    c_sub1, c_sub2, c_sub3 = st.columns(3)
    with c_sub1:
        p_road = st.selectbox("도로 / 차량 진입 조건", ["5톤 트럭 진입", "11톤 윙바디 진입", "25톤/40ft 컨테이너(츄레라) 진입", "1톤~2.5톤 진입", "기타/협의"])
    with c_sub2:
        p_movein = st.text_input("입주 날짜", value="즉시입주 / 협의가능")
    with c_sub3:
        p_tags = st.text_input("추천 업종 태그", value="", placeholder="")

    st.markdown("##### 🔒 중개사 전용 비밀장부 (손님용 홈페이지에는 절대 노출되지 않습니다)")
    c_sec1, c_sec2, c_sec3, c_sec4, c_sec5 = st.columns(5)
    with c_sec1:
        p_jibun = st.text_input("📍 실제 상세 지번 (비공개)", value="")
    with c_sec2:
        p_owner = st.text_input("👤 건물주/임대인 성함", value="")
    with c_sec3:
        p_phone = st.text_input("📞 건물주 연락처 (비공개)", value="")
    with c_sec4:
        p_zone = st.text_input("용도지역 / 건축구조", value="일반공업지역 / 일반철골조")
    with c_sec5:
        p_approval = st.text_input("사용승인일", value="")

    p_feature = st.text_area("💡 핵심 특징 요약 (블로그 체크리스트 및 카톡 브리핑에 자동 삽입)", height=70, value="")

    st.markdown("##### 📸 대표 현장 사진 등록 (업로드 또는 이미지 URL 입력 시 홈페이지 매물 카드에 즉시 반영)")
    c_img1, c_img2 = st.columns(2)
    with c_img1:
        p_img_file = st.file_uploader("방법 1) 대표 사진 파일 업로드 (자동 초경량 압축 저장)", type=["jpg", "jpeg", "png", "webp"])
    with c_img2:
        p_img_url = st.text_input("방법 2) 또는 이미지 URL 직접 입력 (비워두면 기본 공장 사진 자동 적용)", value="")

    if st.button("🚀 새 매물 등록하기 (구글 시트 & 홈페이지 반영 + 대기손님 자동 매칭)", type="primary", use_container_width=True):
        if "임대" in p_deal:
            price_str = f"보증금 {p_deposit:,}만 / 월 {p_rent:,}만"
        else:
            price_str = f"매매/분양가 {p_deposit:,}만원"

        final_title = p_title.strip() if p_title.strip() else f"[{p_region}] {p_floor} 전용 {int(p_area1)}평 {p_deal}"
        final_hoist_spec = p_hoist_spec.strip() if (p_hoist_ox == "있음" and p_hoist_spec.strip()) else ("보유" if p_hoist_ox == "있음" else "없음")
        img_data = compress_image_to_base64(p_img_file) if p_img_file else p_img_url.strip()

        new_row = {
            "등록일자": datetime.date.today().strftime("%Y-%m-%d"),
            "매물번호": p_no,
            "거래구분": p_deal,
            "권역": p_region,
            "해당층수": p_floor,
            "홈페이지노출": p_show,
            "매물제목": final_title,
            "가격설명": price_str,
            "보증금_매매가": str(p_deposit),
            "월세": str(p_rent),
            "전용평수": str(p_area1),
            "사무실평수": str(p_area2),
            "층고": p_height.strip() if p_height.strip() else "-",
            "전력": p_power.strip() if p_power.strip() else "-",
            "호이스트유무": p_hoist_ox,
            "호이스트제원": final_hoist_spec,
            "도로조건": p_road,
            "입주날짜": p_movein,
            "추천업종": p_tags,
            "상세지번": p_jibun,
            "건물주성함": p_owner,
            "건물주연락처": p_phone,
            "용도지역": p_zone,
            "사용승인일": p_approval,
            "핵심특징": p_feature,
            "대표사진": img_data
        }

        ok, msg = append_row_fast("properties", PROP_COLUMNS, new_row)
        st.session_state["last_registered_prop"] = new_row
        if ok:
            st.toast(f"등록 완료: {final_title}", icon="🎉")
            st.success(f"🎉 [{final_title}] 매물이 구글 시트 및 홈페이지 연동 데이터에 즉시 기록되었습니다!")
        else:
            st.warning(f"📌 {msg}")

    # 방금 등록한 매물이 있을 경우, 이 물건을 기다리던 대기 손님을 즉시 자동 추천!
    if "last_registered_prop" in st.session_state:
        lp = st.session_state["last_registered_prop"]
        df_c_now = get_fast_df("customers", CUST_COLUMNS)
        if not df_c_now.empty:
            waiting_list = []
            for _, cr in df_c_now.iterrows():
                if "완료" in str(cr.get("진행상태", "")):
                    continue
                sc, rsn = calculate_match_score(lp, cr)
                if sc >= 50:
                    waiting_list.append({
                        "매칭점수": f"{sc}점",
                        "중요도": cr["중요도"],
                        "고객명": cr["고객명"],
                        "연락처": cr["연락처"],
                        "희망조건": f"{cr['선호권역']} {cr['희망거래']} {cr['최소평수']}평↑",
                        "매칭이유": rsn,
                        "상세메모": cr["상세메모"]
                    })
            if waiting_list:
                st.markdown(f"""
                <div class="match-box">
                    <h4 style="margin:0 0 6px 0; color:#1e40af;">🔔 잠깐! 방금 등록하신 [{lp['매물제목']}] 매물을 기다리던 손님이 <u>{len(waiting_list)}명</u> 있습니다! 지금 바로 전화해보세요!</h4>
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(waiting_list), use_container_width=True)

with main_tabs[1]:
    render_new_property_tab()

# ------------------------------------------
# [탭 3] 전체 매물 통합장부 & 홈페이지 노출 관리
# ------------------------------------------
@st_fragment
def render_ledger_tab():
    st.subheader("📋 전체 매물 통합장부 (초고속 검색 · 드롭다운 셀 수정 · 홈페이지 노출 관리)")
    df_props = get_fast_df("properties", PROP_COLUMNS)

    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    with f_col1:
        f_reg = st.multiselect("권역 필터", REGIONS, default=[])
    with f_col2:
        f_deal = st.multiselect("거래구분 필터", DEAL_TYPES, default=[])
    with f_col3:
        f_floor = st.multiselect("층수 필터", FLOOR_OPTIONS, default=[])
    with f_col4:
        f_hoist = st.selectbox("호이스트 필터", ["전체", "있음", "없음"])
    with f_col5:
        f_kw = st.text_input("통합 검색어 (지번/건물주/특징)", "")

    filtered_df = df_props.copy()
    is_filtered = False
    if f_reg:
        filtered_df = filtered_df[filtered_df["권역"].isin(f_reg)]
        is_filtered = True
    if f_deal:
        filtered_df = filtered_df[filtered_df["거래구분"].isin(f_deal)]
        is_filtered = True
    if f_floor:
        filtered_df = filtered_df[filtered_df["해당층수"].isin(f_floor)]
        is_filtered = True
    if f_hoist != "전체":
        filtered_df = filtered_df[filtered_df["호이스트유무"] == f_hoist]
        is_filtered = True
    if f_kw.strip():
        kw = f_kw.strip().lower()
        mask = filtered_df.apply(lambda r: kw in " ".join(r.astype(str)).lower(), axis=1)
        filtered_df = filtered_df[mask]
        is_filtered = True

    st.caption(f"조회된 매물: **{len(filtered_df)}건** (전체 {len(df_props)}건) | `홈페이지노출`을 `노출(공개)`로 바꾸고 저장하면 손님용 홈페이지(index.html)에 즉시 나타납니다.")
    
    col_cfg = {
        "홈페이지노출": st.column_config.SelectboxColumn("홈페이지노출", options=["노출(공개)", "비공개(내부장부용)"], required=True),
        "거래구분": st.column_config.SelectboxColumn("거래구분", options=DEAL_TYPES, required=True),
        "권역": st.column_config.SelectboxColumn("권역", options=REGIONS, required=True),
        "해당층수": st.column_config.SelectboxColumn("해당층수", options=FLOOR_OPTIONS, required=True),
        "호이스트유무": st.column_config.SelectboxColumn("호이스트유무", options=["없음", "있음"], required=True),
    }

    edited_sub = st.data_editor(
        filtered_df,
        column_config=col_cfg,
        num_rows="dynamic",
        use_container_width=True,
        height=420,
        key="fast_prop_editor"
    )

    if st.button("💾 수정된 매물 장부 구글 시트 & 홈페이지에 즉시 반영", type="primary", use_container_width=True):
        if is_filtered:
            base_df = df_props.copy()
            base_df.loc[filtered_df.index] = edited_sub
            target_df = base_df
        else:
            target_df = edited_sub
            
        ok, msg = overwrite_sheet_fast("properties", PROP_COLUMNS, target_df)
        if ok:
            st.toast("구글 시트 동기화 완료!", icon="✅")
            st.success("✅ 구글 스프레드시트(properties) 및 홈페이지 노출 상태가 즉시 업데이트되었습니다!")
        else:
            st.warning(msg)

with main_tabs[2]:
    render_ledger_tab()

# ------------------------------------------
# [탭 4] 손님 전송용 카톡 멀티 브리핑 & 블로그 자동생성
# ------------------------------------------
@st_fragment
def render_briefing_tab():
    st.subheader("💬 손님 전송용 카톡 멀티 브리핑 & 네이버 블로그 원고 1클릭 생성")
    df_props_b = get_fast_df("properties", PROP_COLUMNS)

    if df_props_b.empty:
        st.info("등록된 매물이 없습니다. [2. 새 매물 등록] 탭에서 매물을 먼저 등록해 주세요.")
    else:
        options_list = [
            f"[{r['매물번호']}] ({r['권역']} {r['해당층수']}) {r['매물제목']} - {r['가격설명']}"
            for _, r in df_props_b.iterrows()
        ]
        selected_items = st.multiselect(
            "손님에게 브리핑할 매물을 선택하세요 (여러 개 선택 시 카톡 멀티 브리핑 리스트로 자동 묶음)",
            options_list,
            default=[options_list[-1]]
        )

        if selected_items:
            sel_indices = [options_list.index(item) for item in selected_items]
            sel_rows = df_props_b.iloc[sel_indices]

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown("#### 📱 카카오톡 손님 전송용 브리핑 텍스트 (우측 상단 복사 아이콘 클릭)")
                kakao_lines = [
                    "🏭 [우리부동산 공장·창고 맞춤 매물 브리핑]",
                    "안녕하십니까, 인천 서구 공장 전문 우리부동산 김태형 대표공인중개사입니다.",
                    "요청하신 조건에 부합하는 추천 실매물 안내드립니다.\n"
                ]
                for idx, (_, r) in enumerate(sel_rows.iterrows(), 1):
                    hoist_txt = f"있음 ({r['호이스트제원']})" if r['호이스트유무'] == "있음" else "없음"
                    kakao_lines.append(f"■ 추천매물 #{idx}. {r['매물제목']}")
                    kakao_lines.append(f" • 소재권역 : 인천 서구 {r['권역']} ({r['거래구분']})")
                    kakao_lines.append(f" • 해당층수 : {r['해당층수']}")
                    kakao_lines.append(f" • 면적정보 : 전용 {r['전용평수']}평 (부속사무실 {r['사무실평수']}평)")
                    kakao_lines.append(f" • 금액조건 : {r['가격설명']}")
                    kakao_lines.append(f" • 층고/전력 : 층고 {r['층고']} / 전력 {r['전력']}")
                    kakao_lines.append(f" • 호이스트 : {hoist_txt}")
                    kakao_lines.append(f" • 차량진입 : {r['도로조건']} / 입주: {r['입주날짜']}")
                    if str(r['핵심특징']).strip():
                        kakao_lines.append(f" • 핵심특징 : {r['핵심특징']}")
                    kakao_lines.append("")

                kakao_lines.append("📞 현장 답사 및 상세 문의: 우리부동산 032-582-6200 / 직통 010-2660-8276")
                st.code("\n".join(kakao_lines), language="markdown")

            with b_col2:
                st.markdown("#### 🟢 네이버 블로그 포스팅용 원고 (첫 번째 선택 매물 기준)")
                r0 = sel_rows.iloc[0]
                hoist_blog = f"설치 완료 ({r0['호이스트제원']})" if r0['호이스트유무'] == "있음" else "없음 (추후 설치 협의 가능)"
                blog_text = f"""[제목] 인천 {r0['권역']} {r0['거래구분']} {r0['해당층수']} 전용 {r0['전용평수']}평 실매물 현장리뷰 ({r0['매물제목']})

안녕하세요! 인천 서구 공장·창고 전문 파트너, 우리부동산 공인중개사사무소 김소장입니다.
오늘 소개해 드릴 현장은 **{r0['권역']}**에 위치한 작업 효율 뛰어난 **{r0['해당층수']} {r0['거래구분']}** 매물입니다.

---
📌 [매물 핵심 스펙 한눈에 보기]
• 매물번호 : {r0['매물번호']}
• 소재지역 : 인천광역시 서구 {r0['권역']} ({r0['용도지역']})
• 거래조건 : {r0['가격설명']}
• 해당층수 : {r0['해당층수']}
• 전용면적 : 공장/창고 전용 {r0['전용평수']}평 (사무실 {r0['사무실평수']}평 별도)
• 유효층고 : {r0['층고']}
• 계약전력 : {r0['전력']}
• 호이스트 : {hoist_blog}
• 진입도로 : {r0['도로조건']}
• 입주시기 : {r0['입주날짜']}
---

💡 [김소장의 현장 체크 포인트]
{r0['핵심특징'] if str(r0['핵심특징']).strip() else '차량 진출입이 수월하고 바닥 에폭시 및 기본 동력 설비가 잘 갖춰져 있어 즉시 가동 가능한 알짜 공장입니다.'}

추천 업종으로는 [{r0['추천업종'] if str(r0['추천업종']).strip() else '일반 제조업, 정밀가공, 물류창고'}] 등을 강력 추천합니다.

🏭 인천 서구 석남동·가좌동·원창동·경서동 공장 매매/임대 문의는 언제든 편하게 연락 주세요!
• 상호 : 우리부동산 공인중개사사무소 (대표: 김태형)
• 소재지 : 인천 서구 건지로 167 (석남역 인근)
• 대표번호 : 매매 032-582-6200 / 임대 032-576-2600"""
                st.code(blog_text, language="markdown")

with main_tabs[3]:
    render_briefing_tab()

# ==========================================
# 7. 확장 업무 시스템 (탭 5 ~ 탭 9 : 임장 / 경매 / 청약 / 신축분양 / 김소장 블로그 100% 유지)
# ==========================================
st.divider()
st.markdown("### 🛠️ [확장 업무 시스템] 5. 현장 임장(복붙 파서) · 6. 공장/아파트 경매 · 7. 수도권 청약 캘린더 · 8. 신축공장분양 대출계산기 · 9. 김소장 맛집/일상 블로그")

ext_tabs = st.tabs([
    "🎯 5. 현장 임장 / 물건따기 (복붙 자동추출)",
    "⚖️ 6. 인천공장 & 수도권아파트 경매 (고도화)",
    "📅 7. 수도권 아파트 & 산업단지 청약 캘린더",
    "🏗️ 8. 신축공장분양 전용관 (80% 대출/취득세 계산기)",
    "🍽️ 9. 김소장 맛집 · 일상 · 여행 블로그 생성기"
])

# ------------------------------------------
# [탭 5] 현장 임장 / 물건따기 (복붙 정규식 자동 추출기)
# ------------------------------------------
@st_fragment
def render_hunting_tab():
    st.subheader("🎯 현장 임장 / 물건따기 장부 (hunting 시트 실시간 연동)")
    raw_paste = st.text_area(
        "현장에서 적어둔 메모나 카톡, 건축물대장 텍스트를 그대로 붙여넣으세요 (자동으로 아래 입력칸에 채워집니다)",
        height=80,
        placeholder="예: 석남동 223-12 대성정밀 2층 85평 보3000/월280 동력50kw 호이스트2.8톤 김철수 사장님 010-1234-5678"
    )

    parsed_info = {"region": "석남동", "jibun": "", "floor": "지상 1층", "area": "", "price": "", "spec": "", "phone": ""}
    if raw_paste.strip():
        for rg in REGIONS:
            if rg[:2] in raw_paste:
                parsed_info["region"] = rg
                break
        m_jibun = re.search(r"(\d{1,4}(?:-\d{1,4})?\s*번지|\d{1,4}-\d{1,4})", raw_paste)
        if m_jibun:
            parsed_info["jibun"] = m_jibun.group(1)
        m_area = re.search(r"(\d+(?:\.\d+)?)\s*평", raw_paste)
        if m_area:
            parsed_info["area"] = m_area.group(1)
        m_phone = re.search(r"(01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}|032[-.\s]?\d{3,4}[-.\s]?\d{4})", raw_paste)
        if m_phone:
            parsed_info["phone"] = m_phone.group(1)
        m_floor = re.search(r"(지하\s*\d+층|\d+층|전층|통임대)", raw_paste)
        if m_floor:
            parsed_info["floor"] = m_floor.group(1)
        m_spec = re.findall(r"(\d+\s*(?:kw|kW|톤|t)|호이스트\s*[\d.]*톤?)", raw_paste)
        if m_spec:
            parsed_info["spec"] = ", ".join(m_spec)

    with st.form("hunting_fast_form"):
        h1, h2, h3, h4 = st.columns(4)
        with h1:
            h_reg = st.selectbox("권역", REGIONS, index=REGIONS.index(parsed_info["region"]) if parsed_info["region"] in REGIONS else 0)
            h_owner = st.text_input("소유자(건물주) 성함")
        with h2:
            h_jibun = st.text_input("상세 지번 *", value=parsed_info["jibun"])
            h_phone = st.text_input("연락처", value=parsed_info["phone"])
        with h3:
            h_bldg = st.text_input("건물명 / 현재 상호")
            h_floor = st.text_input("해당 층수", value=parsed_info["floor"])
        with h4:
            h_area = st.text_input("예상 평수", value=parsed_info["area"])
            h_price = st.text_input("예상 금액 (보/월/매매)", value=parsed_info["price"])

        h5, h6, h7 = st.columns(3)
        with h5:
            h_spec = st.text_input("동력 / 호이스트", value=parsed_info["spec"])
        with h6:
            h_state = st.selectbox("현장 상태", ["가동중(자가)", "가동중(임차인)", "공실(즉시가능)", "신축공사중", "명도예정"])
        with h7:
            h_res = st.selectbox("접촉 결과", ["1차 명함전달", "매도/임대 의사있음", "시세문의", "추후 재방문 요망", "물건확보 완료"])

        h_memo = st.text_input("추후 일정 / 현장 메모")
        sub_hunt = st.form_submit_button("🎯 현장 임장 데이터 구글 시트(hunting) 저장", type="primary", use_container_width=True)

        if sub_hunt:
            hunt_row = {
                "등록일자": datetime.date.today().strftime("%Y-%m-%d"),
                "권역": h_reg,
                "상세지번": h_jibun,
                "건물명_상호": h_bldg,
                "해당층수": h_floor,
                "예상평수": h_area,
                "예상금액": h_price,
                "동력_호이스트": h_spec,
                "소유자성함": h_owner,
                "연락처": h_phone,
                "현장상태": h_state,
                "접촉결과": h_res,
                "추후일정_메모": h_memo
            }
            append_row_fast("hunting", HUNT_COLUMNS, hunt_row)
            st.toast("임장 기록 저장 완료!", icon="🎯")
            st.success("✅ 현장 임장 기록이 hunting 시트에 즉시 저장되었습니다!")

    df_hunt = get_fast_df("hunting", HUNT_COLUMNS)
    if not df_hunt.empty:
        st.dataframe(df_hunt, use_container_width=True)

with ext_tabs[0]:
    render_hunting_tab()

# ------------------------------------------
# [탭 6] 인천공장 & 수도권아파트 법원 경매 분석
# ------------------------------------------
@st_fragment
def render_auction_tab():
    st.subheader("⚖️ 인천지방법원 관할 공장·창고 및 수도권 핵심 아파트 경매 분석 시스템")
    auc_data = [
        {
            "사건번호": "2025타경 51204",
            "관할법원": "인천지방법원 본원 경매4계",
            "물건종류": "공장 (일반철골조)",
            "소재지": "인천광역시 서구 석남동 223-XX",
            "토지/건물면적": "토지 310평 / 건물 245평 (1층 180평, 2층 사무실 65평)",
            "감정가": 245000,
            "최저입찰가": 120050,
            "최저비율": "49% (2회 유찰)",
            "매각기일": "2026-11-12",
            "기계기구/설비": "호이스트 5톤 2기, 수전설비 250kW (감정가 포함 일괄매각)",
            "권리분석핵심": "선순위 근저당 말소기준권리 이후 임차인 없음 (인도명령 대상, 권리관계 깨끗함)",
            "예상낙찰가율": "62~66%"
        },
        {
            "사건번호": "2025타경 60889",
            "관할법원": "인천지방법원 본원 경매7계",
            "물건종류": "공장 (지식산업센터 대평수)",
            "소재지": "인천광역시 서구 가좌동 482-XX",
            "토지/건물면적": "전용 115평 (지상 1층 드라이브인 도어투도어)",
            "감정가": 138000,
            "최저입찰가": 96600,
            "최저비율": "70% (1회 유찰)",
            "매각기일": "2026-11-19",
            "기계기구/설비": "층고 7m, 호이스트 2.8톤 1기, 바닥 하드너 완비",
            "권리분석핵심": "대항력 없는 사업자 임차인 점유 중 (보증금 전액 배당 예상, 명도 수월)",
            "예상낙찰가율": "75~78%"
        },
        {
            "사건번호": "2025타경 33910",
            "관할법원": "인천지방법원 본원 경매2계",
            "물건종류": "창고 및 공장용지",
            "소재지": "인천광역시 서구 원창동 381-XX",
            "토지/건물면적": "토지 450평 / 건물 1층 220평 (40ft 컨테이너 진입)",
            "감정가": 320000,
            "최저입찰가": 224000,
            "최저비율": "70% (1회 유찰)",
            "매각기일": "2026-11-26",
            "기계기구/설비": "동력 100kW, 대형 마당 단독 사용, 층고 8.5m",
            "권리분석핵심": "채무자(소유자) 직접 점유 중. 체납 관리비 및 공과금 인수 여부만 현장 확인 요망",
            "예상낙찰가율": "78~82%"
        },
        {
            "사건번호": "2025타경 77412",
            "관할법원": "인천지방법원 부천지원 경매3계",
            "물건종류": "수도권 아파트",
            "소재지": "인천광역시 서구 청라동 청라국제도시 대장주 84㎡",
            "토지/건물면적": "전용 25.7평 (34평형, 로얄동 18층)",
            "감정가": 89000,
            "최저입찰가": 62300,
            "최저비율": "70% (1회 유찰)",
            "매각기일": "2026-11-17",
            "기계기구/설비": "7호선 연장 역세권, 초품아 단지",
            "권리분석핵심": "소유자 거주 중, 등기부상 인수 권리 전혀 없음",
            "예상낙찰가율": "84~88%"
        }
    ]

    auc_df = pd.DataFrame(auc_data)
    ac1, ac2 = st.columns([1.5, 1])
    with ac1:
        auc_filter = st.radio("물건 구분 필터", ["전체 경매물건", "공장·창고 경매만", "수도권 아파트 경매만"], horizontal=True)
    with ac2:
        bid_deposit_rate = st.slider("입찰보증금 비율 (%)", 10, 20, 10)

    if auc_filter == "공장·창고 경매만":
        view_auc = auc_df[auc_df["물건종류"].str.contains("공장|창고")]
    elif auc_filter == "수도권 아파트 경매만":
        view_auc = auc_df[auc_df["물건종류"].str.contains("아파트")]
    else:
        view_auc = auc_df

    for _, row in view_auc.iterrows():
        min_p = int(row["최저입찰가"])
        app_p = int(row["감정가"])
        bid_bond = int(min_p * (bid_deposit_rate / 100))
        loan_est = int(min_p * 0.80)
        real_equity = min_p - loan_est

        st.markdown(f"""
        <div class="card-box">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="badge-blue">{row['관할법원']}</span>
                    <span class="badge-red">{row['최저비율']}</span>
                    <strong style="font-size:1.1rem; margin-left:8px;">[{row['사건번호']}] {row['소재지']} ({row['물건종류']})</strong>
                </div>
                <div style="font-weight:700; color:#1e40af;">매각기일: {row['매각기일']}</div>
            </div>
            <hr style="margin:8px 0;">
            <p style="margin:4px 0;">📐 <b>면적/스펙:</b> {row['토지/건물면적']} | ⚙️ <b>설비/특징:</b> {row['기계기구/설비']}</p>
            <p style="margin:4px 0;">💰 <b>감정가:</b> {app_p:,}만원 ➔ <b style="color:#dc2626;">최저입찰가: {min_p:,}만원</b> (입찰보증금 {bid_deposit_rate}%: <b>{bid_bond:,}만원</b>)</p>
            <p style="margin:4px 0;">🏦 <b>경락잔금대출(80% 가정):</b> 약 {loan_est:,}만원 가능 | <b>예상 실투자금: 약 {real_equity:,}만원</b></p>
            <p style="margin:4px 0; color:#065f46;">🔍 <b>권리분석 요약:</b> {row['권리분석핵심']} (예상 낙찰가율: {row['예상낙찰가율']})</p>
        </div>
        """, unsafe_allow_html=True)

with ext_tabs[1]:
    render_auction_tab()

# ------------------------------------------
# [탭 7] 수도권 아파트 & 산업단지 청약 캘린더
# ------------------------------------------
@st_fragment
def render_subscription_tab():
    st.subheader("📅 수도권 주요 아파트(LH/신혼희망타운/민영) 및 산업단지 분양 캘린더")
    sub_data = [
        {
            "분양구분": "공공분양 / 신혼희망타운",
            "단지명": "부천대장 A5·A6블록 (e편한세상 대장 퍼스티움)",
            "지역": "경기도 부천시 대장신도시",
            "공급규모": "총 1,099세대 (전용 46㎡ · 55㎡)",
            "청약일정": "2026년 하반기 본청약 / 당첨자 관리 중",
            "분양가(추정)": "3.3㎡당 약 1,850만~1,950만원 수준 (분양가상한제)",
            "핵심체크": "신혼부부·예비신혼부부 특화, 연 1.3% 고정금리 수익공유형 모기지 지원"
        },
        {
            "분양구분": "민영분양 (분양가상한제)",
            "단지명": "인천 검단신도시 AA29블록 푸르지오",
            "지역": "인천광역시 서구 검단신도시",
            "공급규모": "총 884세대 (전용 84㎡ · 101㎡)",
            "청약일정": "2026-11-09 특별공급 / 2026-11-10 1순위",
            "분양가(추정)": "전용 84㎡ 기준 약 5억 6,000만원",
            "핵심체크": "인천 1호선 연장 역세권, 거주의무 없음, 전매제한 3년"
        },
        {
            "분양구분": "산업단지 / 지식산업센터 분양",
            "단지명": "인천 서구 가좌·석남 첨단메카 트윈타워 (신축공장)",
            "지역": "인천광역시 서구 가좌동 (주력권역)",
            "공급규모": "제조형 드라이브인 공장 140호실",
            "청약일정": "선착순 호실 지정 계약 중 (즉시 입주/분양)",
            "분양가(추정)": "평당 920만~1,050만원 (중도금 무이자, 잔금대출 80%)",
            "핵심체크": "1층~4층 5톤 화물차 도어투도어 진입, 층고 6.5m, 호이스트 설치 가능 구조"
        }
    ]
    st.dataframe(pd.DataFrame(sub_data), use_container_width=True, height=200)

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        homeless_yrs = st.number_input("무주택 기간 (년, 만 30세 이후 기준)", 0, 20, 2)
    with sc2:
        dependents = st.number_input("부양가족 수 (본인 제외)", 0, 10, 1)
    with sc3:
        bank_yrs = st.number_input("청약통장 가입기간 (년)", 0, 20, 5)

    score_calc = min(homeless_yrs * 2 + 2, 32) + min((dependents + 1) * 5, 35) + min(bank_yrs + 2, 17)
    st.info(f"📌 **민영주택 예상 청약 가점:** 약 **{score_calc}점** / 84점 만점")

with ext_tabs[2]:
    render_subscription_tab()

# ------------------------------------------
# [탭 8] 신축공장분양 전용관 (80~90% 대출 & 취득세 감면 시뮬레이터)
# ------------------------------------------
@st_fragment
def render_loan_sim_tab():
    st.subheader("🏗️ 신축공장분양 · 자가공장 마련 자금계획 & 대출 시뮬레이터")
    sim1, sim2, sim3 = st.columns(3)
    with sim1:
        f_pyeong = st.number_input("분양/매입 평수 (평)", min_value=10.0, value=80.0, step=5.0)
        f_unit_price = st.number_input("평당 분양가/매매가 (만원)", min_value=100, value=1000, step=50)
    with sim2:
        f_loan_ratio = st.slider("시설자금 대출 비율 (%)", min_value=50, max_value=90, value=80, step=5)
        f_interest = st.number_input("예상 대출 금리 (연 %)", min_value=2.0, max_value=8.0, value=4.2, step=0.1)
    with sim3:
        f_tax_discount = st.selectbox("취득세 감면 적용", ["기본 세율 (4.6%)", "지식산업센터/산단 감면 (35% 감면)", "창업중소기업 감면 (50~75% 감면)"])
        current_rent = st.number_input("현재 납부 중인 월세 (비교용, 만원)", min_value=0, value=280, step=10)

    total_price = int(f_pyeong * f_unit_price)
    loan_amt = int(total_price * (f_loan_ratio / 100.0))
    self_cash = total_price - loan_amt
    monthly_interest = int((loan_amt * (f_interest / 100.0)) / 12)

    if "35%" in f_tax_discount:
        acq_tax = int(total_price * 0.046 * 0.65)
    elif "창업" in f_tax_discount:
        acq_tax = int(total_price * 0.046 * 0.50)
    else:
        acq_tax = int(total_price * 0.046)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 매입/분양 금액", f"{total_price:,} 만원")
    m2.metric(f"대출 가능액 ({f_loan_ratio}%)", f"{loan_amt:,} 만원")
    m3.metric("필요 실투자금 (자기자본)", f"{self_cash:,} 만원", f"취득세 약 {acq_tax:,}만 별도")
    diff_rent = current_rent - monthly_interest
    m4.metric("월 예상 이자", f"월 {monthly_interest:,} 만원", f"현재 월세 대비 {diff_rent:+,}만 절감")

with ext_tabs[3]:
    render_loan_sim_tab()

# ------------------------------------------
# [탭 9] 김소장 맛집 · 일상 · 여행 블로그 생성기
# ------------------------------------------
@st_fragment
def render_lifestyle_blog_tab():
    st.subheader("🍽️ 김소장 & 청라 어니스트 아재 맛집 · 일상 · 여행 블로그 원고 생성기")
    b1, b2, b3 = st.columns(3)
    with b1:
        blog_nick = st.selectbox("블로그 페르소나 선택", ["김소장 (친근한 동네 부동산 소장님)", "청라 어니스트 아재 (솔직담백 내돈내산 리뷰어)"])
    with b2:
        place_name = st.text_input("방문 장소 / 식당 / 여행지 이름", placeholder="예: 석남동 뼈해장국 맛집 / 태안 해루질 펜션")
    with b3:
        menu_point = st.text_input("주문 메뉴 및 핵심 한줄평", placeholder="예: 묵은지 감자탕 대자, 고기가 정말 부드러움")

    if st.button("✍️ 블로그 포스팅 초안 즉시 생성", use_container_width=True):
        p_name = place_name if place_name.strip() else "인천 서구 숨은 맛집"
        nick_clean = blog_nick.split("(")[0].strip()
        st.code(f"""[제목] {p_name} 내돈내산 솔직 방문 후기! ({nick_clean} 추천)

안녕하세요, {nick_clean}입니다!
오늘도 인천 서구 석남동·가좌동 현장을 발로 뛰며 바쁜 하루를 보내고, 든든하게 한 끼 해결하러 다녀온 **{p_name}** 솔직 후기를 남겨봅니다.

📍 방문 포인트 및 메뉴 후기
• 오늘의 픽 : {menu_point if menu_point.strip() else '대표 시그니처 메뉴'}
• 분위기 및 주차 : 매장 깔끔하고 동료들이나 가족과 함께 방문하기 딱 좋은 곳입니다.

자극적이지 않으면서도 깊은 맛이 일품이라 재방문 의사 100%입니다!""", language="markdown")

with ext_tabs[4]:
    render_lifestyle_blog_tab()