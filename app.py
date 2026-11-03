import streamlit as st
import pandas as pd
import datetime
import re
import json
import os
import base64
import urllib.parse
from io import BytesIO

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
# 0. 페이지 기본 설정 및 프로페셔널 UI 스타일링 (Agent B)
# ==========================================
st.set_page_config(
    page_title="우리부동산 통합업무시스템 Pro (본업 CRM)",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    section[data-testid="stSidebar"] .stRadio > div { gap: 6px; }
    section[data-testid="stSidebar"] .stRadio label {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px 12px;
        font-weight: 700;
        width: 100%;
        transition: all 0.15s ease-in-out;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        border-color: #2563eb;
        background-color: #eff6ff;
    }
    .main-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
        color: white;
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .alert-callback {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        border-left: 8px solid #dc2626;
        color: #991b1b;
        padding: 0.95rem 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 10px rgba(220,38,38,0.08);
    }
    .match-box {
        background-color: #eff6ff;
        border: 2px solid #3b82f6;
        border-left: 8px solid #1d4ed8;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .parser-box {
        background-color: #f8fafc;
        border: 2px dashed #3b82f6;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1.2rem;
    }
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-top: 4px solid #1e3a8a;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .kpi-title { font-size: 0.8rem; color: #475569; font-weight: 700; margin-bottom: 4px; }
    .kpi-val { font-size: 1.4rem; color: #0f172a; font-weight: 900; }
    .card-box {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .web-preview-card {
        background-color: #ffffff;
        border: 2px solid #2563eb;
        border-radius: 12px;
        padding: 1.1rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 4px 10px rgba(37,99,235,0.08);
    }
    .sidebar-call-card {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        border-left: 4px solid #e11d48;
        border-radius: 8px;
        padding: 0.65rem 0.8rem;
        margin-bottom: 0.5rem;
        font-size: 0.84rem;
        line-height: 1.4;
    }
    .badge-blue { background-color: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 5px; font-size: 0.78rem; font-weight: 800; }
    .badge-red { background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 5px; font-size: 0.78rem; font-weight: 800; }
    .badge-green { background-color: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 5px; font-size: 0.78rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 상수 및 표준 컬럼 규격 정의 (Agent A)
# ==========================================
ADMIN_PW = "563011"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1oTTZ1ok-quer9_NR5v5hEFYpRiOrR8tAwwo7UPnwRco/edit"

PROP_COLUMNS = [
    "등록일자", "매물번호", "거래구분", "권역", "해당층수", "홈페이지노출",
    "매물제목", "가격설명", "보증금_매매가", "월세", "전용평수", "사무실평수",
    "층고", "전력", "호이스트유무", "호이스트제원", "도로조건", "입주날짜",
    "추천업종", "상세지번", "건물주성함", "건물주연락처", "용도지역",
    "사용승인일", "핵심특징", "대표사진"
]

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

REGIONS = ["석남동", "가좌동", "원창동", "경서동", "도화동", "송림동", "송현동", "오류동", "기타/인천전역"]
DEAL_TYPES = ["공장임대", "공장매매", "창고임대", "창고매매", "신축공장분양", "토지매매", "지식산업센터"]
FLOOR_OPTIONS = [
    "지상 1층", "지상 2층", "지상 3층", "지상 4층",
    "지상 5층 이상", "지하 1층", "건물 전체(통임대/통매매)", "기타(직접입력)"
]
CUST_STATUS_OPTIONS = [
    "🔥 급구(집중케어)", "📞 콜백대기(리마인드)", "👀 매물브리핑완료",
    "🤝 현장미팅예정", "✅ 계약완료", "⏸️ 보류(장기추적)"
]

MENU_LIST = [
    "👥 1. 손님 리마인드 & 매칭 영업소",
    "➕ 2. 새 매물 등록 (+대장파서 & 자동역매칭)",
    "📋 3. 전체 매물 통합장부 & 홈페이지 관리",
    "💬 4. 카톡 멀티 브리핑 & 블로그 원고",
    "🎯 5. 현장 임장 / 물건따기 (복붙 파서)",
    "🏗️ 6. 신축공장분양 대출/취득세 계산기"
]

LOCAL_CACHE_FILE = "local_backup_cache.json"

# ==========================================
# 2. 레거시 뒤틀린 행 자동 복구 + 초고속 인메모리 엔진 (Agent A)
# ==========================================
def repair_legacy_prop_rows(raw_rows):
    """구글 시트에 옛날 컬럼 순서로 밀려 들어간 행(W-103 등)을 감지하여 26개 표준 컬럼으로 자동 교정합니다."""
    if not raw_rows or len(raw_rows) <= 1:
        return pd.DataFrame(columns=PROP_COLUMNS)

    repaired_list = []
    for r in raw_rows[1:]:
        row_padded = list(r) + [""] * (26 - len(r))
        c0 = str(row_padded[0]).strip()
        c1 = str(row_padded[1]).strip()
        c2 = str(row_padded[2]).strip()
        c3 = str(row_padded[3]).strip()
        c4 = str(row_padded[4]).strip()
        c5 = str(row_padded[5]).strip()

        if not any(str(x).strip() for x in row_padded):
            continue

        # 케이스 1: 첫 칸에 매물번호(W-...)가 들어가고 3번째 칸에 공개 여부가 들어간 구버전 밀림 행 자동 교정
        if c0.startswith("W-") and (c2 in ("공개", "노출(공개)", "비공개") or c3 in DEAL_TYPES):
            area_m = re.search(r"\d+", str(row_padded[8]))
            area_val = area_m.group(0) if area_m else "80"
            sub_m = re.search(r"\d+", str(row_padded[9]))
            sub_val = sub_m.group(0) if sub_m else "0"
            hoist_raw = str(row_padded[12]).strip()
            has_h = "있음" if ("호이스트" in hoist_raw and "없음" not in hoist_raw) else "없음"
            repaired_list.append({
                "등록일자": c1 if re.match(r"^\d{4}-\d{2}-\d{2}", c1) else datetime.date.today().strftime("%Y-%m-%d"),
                "매물번호": c0,
                "거래구분": c3 if c3 else "공장임대",
                "권역": c4 if c4 else "석남동",
                "해당층수": "지상 2층" if "2층" in str(row_padded[6]) else "지상 1층",
                "홈페이지노출": "노출(공개)" if ("공개" in c2 and "비공개" not in c2) else "비공개(내부장부용)",
                "매물제목": str(row_padded[6]).strip() or f"[{c4 or '석남동'}] 추천 공장",
                "가격설명": str(row_padded[7]).strip() or "보증금 2,000만 / 월 200만",
                "보증금_매매가": "2000",
                "월세": "200",
                "전용평수": area_val,
                "사무실평수": sub_val,
                "층고": str(row_padded[10]).strip() or "7m",
                "전력": str(row_padded[11]).strip() or "30kW",
                "호이스트유무": has_h,
                "호이스트제원": hoist_raw if has_h == "있음" else "없음",
                "도로조건": str(row_padded[13]).strip() or "5톤 트럭 진입",
                "입주날짜": str(row_padded[15]).strip() or "즉시입주 / 협의가능",
                "추천업종": str(row_padded[14]).strip() or "",
                "상세지번": "",
                "건물주성함": "",
                "건물주연락처": "",
                "용도지역": str(row_padded[16]).strip() or "일반공업지역",
                "사용승인일": "",
                "핵심특징": str(row_padded[20]).strip() or "",
                "대표사진": ""
            })
        # 케이스 2: 날짜는 첫 칸인데 거래구분이 비어있고 4번째 칸에 '공개'가 들어간 밀림 행 교정
        elif c0.startswith("202") and c1.startswith("W-") and c3 in ("공개", "노출(공개)"):
            repaired_list.append({
                "등록일자": c0,
                "매물번호": c1,
                "거래구분": "공장임대",
                "권역": "석남동",
                "해당층수": "지상 2층" if "2층" in str(row_padded[6]) else "지상 1층",
                "홈페이지노출": "노출(공개)",
                "매물제목": str(row_padded[6]).strip() or "석남동 추천 공장",
                "가격설명": "금액 협의",
                "보증금_매매가": "0",
                "월세": "0",
                "전용평수": "100",
                "사무실평수": "0",
                "층고": "-",
                "전력": str(row_padded[9]).strip() or "30kW",
                "호이스트유무": "없음",
                "호이스트제원": "없음",
                "도로조건": "5톤 트럭 진입",
                "입주날짜": "즉시입주 / 협의가능",
                "추천업종": "",
                "상세지번": "",
                "건물주성함": "",
                "건물주연락처": "",
                "용도지역": "일반공업지역",
                "사용승인일": "",
                "핵심특징": "",
                "대표사진": ""
            })
        else:
            # 정상 26개 규격 행
            row_dict = {PROP_COLUMNS[i]: str(row_padded[i]).strip() for i in range(len(PROP_COLUMNS))}
            if not row_dict["홈페이지노출"]:
                row_dict["홈페이지노출"] = "노출(공개)"
            repaired_list.append(row_dict)

    return pd.DataFrame(repaired_list, columns=PROP_COLUMNS)

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
        return None, "gspread 미설치"
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "secrets.toml 미설정"
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

def sync_legacy_first_tab(sh, clean_prop_df):
    """만약 시트 1번 탭이 'properties (매물장부용)'일 경우, 혹시 모를 gid=0 호출에 대비해 해당 탭에도 똑같이 데이터를 복사해 줍니다."""
    try:
        ws_legacy = sh.worksheet("properties (매물장부용)")
        ws_legacy.clear()
        all_vals = [PROP_COLUMNS] + clean_prop_df.astype(str).values.tolist()
        ws_legacy.update("A1", all_vals, value_input_option="USER_ENTERED")
    except Exception:
        pass

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
            # 1. properties 시트 로드 및 뒤틀린 레거시 행 자동 교정
            try:
                ws_p = ensure_worksheet_fast(sh, "properties", PROP_COLUMNS)
                rows_p = ws_p.get_all_values()
                if len(rows_p) > 1:
                    df_rep = repair_legacy_prop_rows(rows_p)
                    st.session_state.mem_db["properties"] = normalize_df(df_rep, PROP_COLUMNS)
            except Exception:
                pass

            # 2. customers 및 hunting 시트 로드
            for s_name, cols in [("customers", CUST_COLUMNS), ("hunting", HUNT_COLUMNS)]:
                try:
                    ws = ensure_worksheet_fast(sh, s_name, cols)
                    rows = ws.get_all_values()
                    if len(rows) > 1:
                        headers = rows[0]
                        df_loaded = pd.DataFrame(rows[1:], columns=headers)
                        st.session_state.mem_db[s_name] = normalize_df(df_loaded, cols)
                except Exception:
                    pass

            save_local_disk_cache({
                k: v.to_dict(orient="records") for k, v in st.session_state.mem_db.items()
            })

def get_fast_df(sheet_name, expected_cols):
    init_memory_db(force_reload=False)
    return st.session_state.mem_db.get(sheet_name, pd.DataFrame(columns=expected_cols)).copy()

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
            if sheet_name == "properties":
                sync_legacy_first_tab(sh, clean_df)
            return True, "구글 스프레드시트 전체 동기화 완료"
        except Exception as e:
            return False, f"메모리 저장 완료 (시트 업데이트 실패: {e})"
    return False, "메모리 및 로컬 캐시 업데이트 완료"

def append_row_fast(sheet_name, expected_cols, row_dict):
    """단건 추가 시에도 전체 테이블 규격을 완벽히 맞춰 덮어쓰기하여 행 밀림을 100% 방지합니다."""
    init_memory_db(force_reload=False)
    clean_row = {col: str(row_dict.get(col, "")) for col in expected_cols}
    cur_df = st.session_state.mem_db[sheet_name]
    new_df = pd.concat([cur_df, pd.DataFrame([clean_row])], ignore_index=True)
    return overwrite_sheet_fast(sheet_name, expected_cols, new_df)

def compress_image_to_base64(uploaded_file):
    """구글 시트 셀 당 50,000자 제한을 절대 넘지 않도록 480x360으로 안전 압축합니다."""
    if uploaded_file is None:
        return ""
    try:
        if PIL_AVAILABLE:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((480, 360))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=65)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            res = f"data:image/jpeg;base64,{b64}"
            return res if len(res) < 48000 else ""
        return ""
    except Exception:
        return ""

# ==========================================
# 3. 스마트 매칭 점수 산출 · 리마인드 판별 · 건축물대장 파서 엔진 (Agent C)
# ==========================================
def parse_num(val, default=0.0):
    try:
        m = re.search(r"[\d.]+", str(val).replace(",", ""))
        return float(m.group(0)) if m else default
    except Exception:
        return default

def parse_building_ledger_text(raw_text):
    """정부24 건축물대장 및 토지이용계획 확인원 복사 원문에서 핵심 스펙을 자동 추출합니다."""
    res = {
        "region": "석남동",
        "jibun": "",
        "zone": "일반공업지역 / 일반철골조",
        "main_use": "일반제조업, 금속가공, 물류창고",
        "area_py": 60.0,
        "office_py": 0.0,
        "approval_date": "",
        "violation": "🟢 정상 (위반건축물 표기 없음)",
        "jimok": "장(공장용지)"
    }
    if not raw_text or not raw_text.strip():
        return res

    txt = raw_text.strip()
    for rg in REGIONS:
        if rg[:2] in txt:
            res["region"] = rg
            break

    jibun_m = re.search(r"(석남동|가좌동|원창동|경서동|도화동|송림동|송현동|오류동)\s*(?:산\s*)?(\d{1,4}(?:-\d{1,4})?)", txt)
    if jibun_m:
        res["jibun"] = f"{jibun_m.group(1)} {jibun_m.group(2)}"
    else:
        num_m = re.search(r"(\d{1,4}-\d{1,4}|\d{1,4}\s*번지)", txt)
        if num_m:
            res["jibun"] = f"{res['region']} {num_m.group(1)}"

    zone_found = next((z for z in ["전용공업지역", "일반공업지역", "준공업지역", "계획관리지역", "자연녹지지역", "일반상업지역"] if z in txt), "일반공업지역")
    struct_found = next((s for s in ["일반철골조", "철골철근콘크리트구조", "철근콘크리트구조", "경량철골조", "벽돌구조"] if s in txt), "일반철골조")
    res["zone"] = f"{zone_found} / {struct_found}"

    if "위반건축물" in txt or ("위반" in txt and "해당없음" not in txt and "없음" not in txt):
        res["violation"] = "🚨 [경고] 위반건축물 표기 감지됨! (대장 원문 필히 확인)"

    if "창고시설" in txt or "창고" in txt:
        res["main_use"] = "창고시설 (물류·보관·유통)"
    elif "제2종근린생활시설" in txt or "제조업소" in txt:
        res["main_use"] = "제2종근린생활시설 (제조업소·공방)"
    elif "공장" in txt:
        res["main_use"] = "공장 (일반제조·정밀가공·사출)"

    if "공장용지" in txt or "지목: 장" in txt or "지목 장" in txt:
        res["jimok"] = "장(공장용지)"
    elif "창고용지" in txt:
        res["jimok"] = "창(창고용지)"
    elif "대지" in txt or "지목 대" in txt:
        res["jimok"] = "대"

    m2_list = re.findall(r"(\d{2,5}(?:\.\d{1,2})?)\s*(?:㎡|m2|제곱미터)", txt)
    if m2_list:
        res["area_py"] = round(float(m2_list[0]) * 0.3025, 1)
        if len(m2_list) > 1:
            res["office_py"] = round(float(m2_list[1]) * 0.3025, 1)
    else:
        py_m = re.search(r"(\d{2,4}(?:\.\d+)?)\s*평", txt)
        if py_m:
            res["area_py"] = float(py_m.group(1))

    date_m = re.search(r"((?:19|20)\d{2}[\.\-\년]\s*\d{1,2}[\.\-\월]\s*\d{1,2})", txt)
    if date_m:
        res["approval_date"] = date_m.group(1).strip()

    return res

if "ledger_parsed_data" not in st.session_state:
    st.session_state.ledger_parsed_data = parse_building_ledger_text("")

def calculate_match_score(prop_row, cust_row):
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
            reasons.append("월세예산충족")
    else:
        if c_max_dep <= 0 or p_price <= c_max_dep * 1.15:
            score += 15
            reasons.append("매매예산충족")

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

due_customers = []
if not df_c_global.empty:
    for idx, r in df_c_global.iterrows():
        if is_callback_due(r.get("리마인드예정일", ""), r.get("진행상태", "")):
            due_customers.append(r)

# ==========================================
# 4. 왼쪽 사이드바: 보안잠금 + 6대 본업 메뉴 + 시트 원클릭 복구 + 콜백 알림판
# ==========================================
with st.sidebar:
    st.markdown("## 🏭 우리부동산 Pro (본업 CRM)")
    st.caption("인천 서구 공장·창고 전문 통합업무시스템")

    auth_pw = st.text_input("🔒 관리자 보안 비밀번호", type="password", value=ADMIN_PW)
    if auth_pw != ADMIN_PW:
        st.error("보안 비밀번호(563011)를 입력해 주세요.")
        st.stop()

    selected_menu = st.radio(
        "📌 본업 업무 메뉴 바로가기 (클릭 시 즉시 전환)",
        MENU_LIST,
        index=0
    )

    st.divider()
    st.markdown("### 🛠️ 시트 & 홈페이지 완벽 동기화")
    if st.button("✨ 시트 뒤틀린 행 자동 복구 및 홈페이지 즉시 동기화", type="primary", use_container_width=True, help="구글 시트의 옛날 밀린 행들을 표준 26개 컬럼으로 자동 정렬하고 홈페이지(index.html)와 100% 일치시킵니다."):
        with st.spinner("구글 시트 표준화 및 동기화 중..."):
            init_memory_db(force_reload=True)
            overwrite_sheet_fast("properties", PROP_COLUMNS, st.session_state.mem_db["properties"])
        st.toast("구글 시트 표준화 및 홈페이지 동기화 완료!", icon="🎉")
        st.rerun()

    if st.button("🔄 구글 시트 최신 데이터 강제 새로고침", use_container_width=True):
        with st.spinner("구글 시트 동기화 중..."):
            init_memory_db(force_reload=True)
        st.toast("최신 시트 데이터를 불러왔습니다!", icon="✅")
        st.rerun()

    st.divider()
    st.markdown("### 🚨 오늘 연락할 손님 (콜백)")
    if due_customers:
        st.error(f"🔥 오늘 연락할 손님 **{len(due_customers)}명**!")
        for dc in due_customers[:6]:
            st.markdown(f"""
            <div class="sidebar-call-card">
                <strong>{dc['중요도']} {dc['고객명']}</strong> ({dc['희망거래']})<br>
                📞 <a href="tel:{dc['연락처']}" style="color:#be123c;font-weight:900;">{dc['연락처']}</a><br>
                📍 {dc['선호권역']} | {dc['최소평수']}평↑ | 호이스트:{dc['호이스트필수']}<br>
                📝 <span style="color:#334155;">{dc['상세메모'][:32] if dc['상세메모'] else '신규매물 브리핑 및 안부'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ 오늘 미처리 콜백 손님이 없습니다.")

    st.divider()
    st.markdown(f"📊 [구글 스프레드시트 원본 열기 ↗]({SPREADSHEET_URL})")
    st.download_button(
        f"👥 손님장부 ({len(df_c_global)}명) CSV 백업",
        data=df_c_global.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"우리부동산_고객장부_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    st.download_button(
        f"📋 매물장부 ({len(df_p_global)}건) CSV 백업",
        data=df_p_global.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"우리부동산_매물장부_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==========================================
# 5. 우측 상단 공통 헤더 및 실시간 4대 KPI 요약 바
# ==========================================
st.markdown(f"""
<div class="main-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <h2 style="margin:0; color:white;">{selected_menu}</h2>
            <p style="margin:4px 0 0 0; opacity:0.9; font-size:0.9rem;">
                우리부동산공인중개사사무소 (대표: 김태형) | 매매 032-582-6200 · 임대 032-576-2600 · 직통 010-2660-8276
            </p>
        </div>
        <div style="background:rgba(255,255,255,0.15); padding:6px 14px; border-radius:8px; font-weight:800; font-size:0.88rem;">
            {'🟢 구글시트 & 홈페이지 실시간 연동중' if sh_conn is not None and conn_msg == 'OK' else '🟡 로컬 안전 캐시 모드'}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
public_cnt = len(df_p_global[df_p_global["홈페이지노출"].str.contains("노출", na=False)]) if not df_p_global.empty else 0
active_cust_cnt = len(df_c_global[~df_c_global["진행상태"].str.contains("완료|보류", na=False)]) if not df_c_global.empty else 0
hoist_cnt = len(df_p_global[df_p_global["호이스트유무"] == "있음"]) if not df_p_global.empty else 0

with k1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🚨 오늘 연락할 리마인드 손님</div><div class="kpi-val" style="color:#dc2626;">{len(due_customers)}명 <span style="font-size:0.82rem;color:#475569;">(진행중 {active_cust_cnt}명)</span></div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📋 전체 보유 매물 (호이스트 보유)</div><div class="kpi-val">{len(df_p_global)}건 <span style="font-size:0.82rem;color:#2563eb;">({hoist_cnt}건)</span></div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🌐 홈페이지(index.html) 실시간 노출</div><div class="kpi-val" style="color:#059669;">{public_cnt}건</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🎯 현장 임장 / 물건따기 타겟</div><div class="kpi-val">{len(df_h_global)}건</div></div>', unsafe_allow_html=True)

st.write("")

# ==============================================================================
# [사이드 메뉴 1] 👥 손님 리마인드 & 매칭 영업소
# ==============================================================================
if selected_menu == MENU_LIST[0]:
    if due_customers:
        due_names = ", ".join([f"{c['고객명']}({c['선호권역']} {c['최소평수']}평↑)" for c in due_customers[:6]])
        st.markdown(f"""
        <div class="alert-callback">
            <div style="font-size:1.05rem; font-weight:900; margin-bottom:4px;">
                🚨 [오늘의 콜백 리마인드 알림] 지금 안부 전화 및 매물 브리핑을 해야 할 손님이 총 <u>{len(due_customers)}명</u> 있습니다!
            </div>
            <div style="font-size:0.92rem; color:#7f1d1d;">
                • 우선 연락 대상: <b>{due_names}</b> ➔ 아래 <b>[🎯 손님 1:1 맞춤 매물 자동 매칭]</b>에서 손님을 선택하고 1클릭으로 카톡/문자 브리핑을 보내보세요!
            </div>
        </div>
        """, unsafe_allow_html=True)

    df_custs = get_fast_df("customers", CUST_COLUMNS)
    df_props = get_fast_df("properties", PROP_COLUMNS)

    with st.expander("➕ 전화 온 신규 손님 빠른 등록 (클릭하여 열기/닫기)", expanded=df_custs.empty):
        with st.form("crm_new_customer_form", clear_on_submit=True):
            c1, c2, c3, c4, c5 = st.columns([1, 1.3, 1.3, 1.1, 1.2])
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
                c_memo = st.text_input("통화 핵심 메모 (리마인드 사항)", placeholder="예: 현재 가좌동 임차중, 만기 임박하여 층고 높은 곳 찾으심")

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

    st.markdown("### 📋 대기 손님 통합 장부 (셀을 더블클릭하여 통화메모·리마인드 날짜를 바로 수정하세요)")
    cf1, cf2, cf3, cf4 = st.columns([1.3, 1.1, 1.1, 2])
    with cf1:
        filter_call = st.selectbox("📞 연락 시기별 필터", ["전체 손님 보기", "🚨 오늘 연락할 손님만 (콜백도래)", "🔥 A급(급구) 손님만"])
    with cf2:
        filter_c_deal = st.selectbox("희망 거래 필터", ["전체"] + DEAL_TYPES)
    with cf3:
        filter_c_reg = st.selectbox("선호 권역 필터", ["전체"] + REGIONS)
    with cf4:
        filter_c_kw = st.text_input("손님 이름 / 연락처 / 업종 / 메모 검색", "")

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
        height=340,
        key="crm_main_editor"
    )

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

    st.divider()

    st.markdown("### 🎯 손님 1:1 맞춤 매물 자동 매칭 & 원클릭 리마인드 카톡/문자 발송")
    if df_custs.empty:
        st.info("위에서 손님을 1명 이상 등록하시면 보유 매물과의 자동 매칭이 시작됩니다.")
    else:
        cust_options = [
            f"[{r['중요도']}] {r['고객명']} ({r['연락처']}) | 희망: {r['선호권역']} {r['희망거래']} {r['최소평수']}평↑ | 리마인드: {r['리마인드예정일']} | 메모: {r['상세메모'][:30]}"
            for _, r in df_custs.iterrows()
        ]
        sel_c_label = st.selectbox("👇 지금 전화하거나 매물을 보내줄 손님을 선택하세요", cust_options)
        sel_c_idx = cust_options.index(sel_c_label)
        sel_c_row = df_custs.iloc[sel_c_idx]

        q_col1, q_col2, q_col3, q_col4 = st.columns([1.5, 1, 1, 1])
        with q_col1:
            st.markdown(f"**📞 직통 전화:** [{sel_c_row['연락처']}](tel:{sel_c_row['연락처']}) | **현재상태:** `{sel_c_row['진행상태']}`")
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

        if df_props.empty:
            st.warning("현재 등록된 매물(properties)이 없습니다. 왼쪽 메뉴 [➕ 2. 새 매물 등록]에서 매물을 먼저 등록해 주세요.")
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
                st.dataframe(m_df, use_container_width=True, height=220)

                top_matches = m_df.head(3)
                kakao_msg = [
                    f"안녕하세요 {sel_c_row['고객명']}님! 인천 서구 공장·창고 전문 우리부동산 김태형 대표공인중개사입니다.",
                    f"지난번 말씀해주신 조건({sel_c_row['선호권역']} / {sel_c_row['최소평수']}평 이상 / {sel_c_row['희망거래']})에 딱 맞는 실매물이 나와 가장 먼저 안내드립니다.\n"
                ]
                for i, (_, mr) in enumerate(top_matches.iterrows(), 1):
                    kakao_msg.append(f"■ 추천 #{i}. [{mr['권역']} {mr['해당층수']}] {mr['매물제목']}")
                    kakao_msg.append(f" • 면적/금액 : 전용 {mr['전용평수']}평 / {mr['가격설명']}")
                    kakao_msg.append(f" • 설비/도로 : 전력 {mr['전력']} / 호이스트 {mr['호이스트']} / {mr['도로조건']}\n")
                kakao_msg.append("👉 실시간 전체 매물 보기: https://threven.github.io/my-realestate-app/")
                kakao_msg.append("시간 괜찮으실 때 연락 주시면 현장 바로 안내해 드리겠습니다. 오늘도 좋은 하루 보내세요!")
                kakao_msg.append("📞 우리부동산 김태형 대표 직통: 010-2660-8276 / 사무실: 032-582-6200")

                full_kakao_str = "\n".join(kakao_msg)
                st.markdown("##### 💬 손님에게 바로 보낼 맞춤형 안부 & 매물 추천 카톡 (우측 상단 복사 아이콘 클릭)")
                st.code(full_kakao_str, language="markdown")
                sms_url = f"sms:{sel_c_row['연락처']}?body={urllib.parse.quote(full_kakao_str)}"
                st.markdown(f'<a href="{sms_url}" style="display:inline-block; background:#2563eb; color:white; padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:800;">📱 {sel_c_row["고객명"]}님께 문자(SMS) 앱으로 즉시 발송하기</a>', unsafe_allow_html=True)
            else:
                st.warning("현재 보유 매물 중 45점 이상 일치하는 매물이 없습니다.")


# ==============================================================================
# [사이드 메뉴 2] ➕ 새 매물 등록 (+ 정부24 건축물대장 파서 & 대기손님 자동 역매칭)
# ==============================================================================
elif selected_menu == MENU_LIST[1]:
    st.subheader("📑 [STEP 1] 정부24 건축물대장 · 토지이용계획 확인원 원문 스마트 파서")
    st.caption("정부24, 세움터, 토지이음에서 복사한 원문 텍스트를 붙여넣고 분석 버튼을 누르면 아래 [STEP 2] 매물 등록 폼에 권역·지번·전용평수·용도지역·사용승인일·위반건축물 여부가 자동으로 입력됩니다.")

    st.markdown('<div class="parser-box">', unsafe_allow_html=True)
    raw_ledger_input = st.text_area(
        "📋 건축물대장 / 토지이용계획 확인원 텍스트 붙여넣기",
        height=105,
        placeholder="예: 대지위치 인천광역시 서구 석남동 223-12 / 지목 공장용지 / 지역지구 일반공업지역 / 주구조 일반철골조 / 주용도 공장 / 연면적 495.86㎡ / 사용승인일 2018-05-20 / 위반건축물 없음"
    )
    if st.button("🔍 대장 원문 1초 정밀 분석 및 아래 등록 폼에 자동 채우기", type="primary", use_container_width=True):
        parsed = parse_building_ledger_text(raw_ledger_input)
        st.session_state.ledger_parsed_data = parsed
        if "경고" in parsed["violation"]:
            st.error(f"{parsed['violation']} | 추출지번: {parsed['jibun']} | 환산평수: 약 {parsed['area_py']}평")
        else:
            st.success(f"✅ 자동 채우기 완료! 소재지: {parsed['jibun'] or parsed['region']} | 지목: {parsed['jimok']} | 용도/구조: {parsed['zone']} | 전용: 약 {parsed['area_py']}평 | {parsed['violation']}")
    st.markdown('</div>', unsafe_allow_html=True)

    lp_data = st.session_state.ledger_parsed_data

    st.subheader("➕ [STEP 2] 신규 공장 · 창고 · 신축공장분양 매물 등록")
    st.caption("새 매물을 등록하면 구글 시트(properties)와 손님용 홈페이지(index.html)에 실시간 반영되며, 이 조건을 기다리던 손님이 즉시 아래에 추천됩니다.")

    c_top1, c_top2, c_top3, c_top4 = st.columns(4)
    with c_top1:
        default_no = f"W-{datetime.datetime.now().strftime('%y%m%d-%H%M')}"
        p_no = st.text_input("매물번호 *", value=default_no)
    with c_top2:
        p_deal = st.selectbox("거래구분 *", DEAL_TYPES)
    with c_top3:
        reg_idx = REGIONS.index(lp_data["region"]) if lp_data["region"] in REGIONS else 0
        p_region = st.selectbox("소재지 (주력 권역) * [파서 연동]", REGIONS, index=reg_idx)
    with c_top4:
        p_show = st.selectbox("홈페이지 노출 설정 *", ["노출(공개)", "비공개(내부장부용)"])

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
        p_area1 = st.number_input("전용 평수 (바닥면적, 평) * [파서 연동]", min_value=0.0, value=float(lp_data["area_py"]), step=5.0)
    with c_fl4:
        p_area2 = st.number_input("2층/부속 사무실 평수 (없으면 0)", min_value=0.0, value=float(lp_data["office_py"]), step=5.0)

    c_ho1, c_ho2, c_ho3, c_ho4 = st.columns([1.1, 1.9, 1.5, 1.5])
    with c_ho1:
        p_hoist_ox = st.radio("호이스트 유무 *", ["없음", "있음"], horizontal=True)
    with c_ho2:
        p_hoist_spec = st.text_input(
            "호이스트 상세 제원 (직접 입력)",
            value="",
            placeholder="예: 5톤 1기, 2.8톤 2기",
            disabled=(p_hoist_ox == "없음")
        )
    with c_ho3:
        p_height = st.text_input("층고 설명 (m)", value="", placeholder="예: 8.5m")
    with c_ho4:
        p_power = st.text_input("계약 전력(동력 kW)", value="", placeholder="예: 75kW")

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
        p_tags = st.text_input("추천 업종 태그 [파서 연동]", value=lp_data["main_use"])

    st.markdown("##### 🔒 중개사 전용 비밀장부 (손님용 홈페이지에는 절대 노출되지 않습니다)")
    c_sec1, c_sec2, c_sec3, c_sec4, c_sec5 = st.columns(5)
    with c_sec1:
        p_jibun = st.text_input("📍 실제 상세 지번 (비공개) [파서 연동]", value=lp_data["jibun"])
    with c_sec2:
        p_owner = st.text_input("👤 건물주/임대인 성함", value="")
    with c_sec3:
        p_phone = st.text_input("📞 건물주 연락처 (비공개)", value="")
    with c_sec4:
        p_zone = st.text_input("용도지역 / 건축구조 [파서 연동]", value=lp_data["zone"])
    with c_sec5:
        app_default = f"{lp_data['approval_date']} ({lp_data['violation']})" if lp_data["approval_date"] else lp_data["violation"]
        p_approval = st.text_input("사용승인일 / 위반여부 [파서 연동]", value=app_default)

    p_feature = st.text_area("💡 핵심 특징 요약 (블로그 체크리스트 및 카톡 브리핑에 자동 삽입)", height=75, value="")

    st.markdown("##### 📸 대표 현장 사진 등록 (업로드 또는 이미지 URL 입력 시 홈페이지 매물 카드에 즉시 반영)")
    c_img1, c_img2 = st.columns(2)
    with c_img1:
        p_img_file = st.file_uploader("방법 1) 대표 사진 파일 업로드 (자동 안전 압축 저장)", type=["jpg", "jpeg", "png", "webp"])
    with c_img2:
        p_img_url = st.text_input("방법 2) 또는 이미지 URL 직접 입력 (비워두면 기본 공장 사진 자동 적용)", value="")

    if st.button("🚀 새 매물 등록하기 (구글 시트 & 홈페이지 즉시 반영 + 대기손님 자동 매칭)", type="primary", use_container_width=True):
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
            st.success(f"🎉 [{final_title}] 매물이 구글 시트(properties) 및 홈페이지 연동 데이터에 즉시 기록되었습니다! 이제 홈페이지를 새로고침하면 바로 뜹니다.")
        else:
            st.warning(f"📌 {msg}")

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
                        "매칭사유": rsn,
                        "상세메모": cr["상세메모"]
                    })
            if waiting_list:
                st.markdown(f"""
                <div class="match-box">
                    <h4 style="margin:0 0 6px 0; color:#1e40af;">🔔 잠깐! 방금 등록하신 [{lp['매물제목']}] 매물을 기다리던 대기 손님이 <u>{len(waiting_list)}명</u> 있습니다! 지금 바로 전화해보세요!</h4>
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(waiting_list), use_container_width=True)


# ==============================================================================
# [사이드 메뉴 3] 📋 전체 매물 통합장부 & 손님용 홈페이지 노출 관리
# ==============================================================================
elif selected_menu == MENU_LIST[2]:
    st.subheader("📋 전체 매물 통합장부 (초고속 검색 · 셀 직접 수정 · 홈페이지 노출 프리뷰)")
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
        height=450,
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
            st.rerun()
        else:
            st.warning(msg)

    st.divider()
    st.markdown("#### 🌐 손님용 홈페이지(`index.html`) 실시간 노출 매물 카드 미리보기")
    pub_df = df_props[df_props["홈페이지노출"].str.contains("노출", na=False)] if not df_props.empty else pd.DataFrame()
    if pub_df.empty:
        st.info("현재 홈페이지에 '노출(공개)'로 설정된 매물이 없습니다.")
    else:
        st.caption(f"현재 총 **{len(pub_df)}건**이 손님용 홈페이지에 공개 중입니다. (상세지번·건물주 연락처는 철저히 차단됩니다)")
        cols_preview = st.columns(3)
        for idx, (_, pr) in enumerate(pub_df.iloc[::-1].head(6).iterrows()):
            with cols_preview[idx % 3]:
                hoist_badge = f"🏗️ 호이스트: {pr['호이스트제원']}" if pr["호이스트유무"] == "있음" else "호이스트 없음"
                st.markdown(f"""
                <div class="web-preview-card">
                    <span class="badge-blue">{pr['권역']} · {pr['거래구분']}</span>
                    <span class="badge-green">{pr['해당층수']}</span>
                    <h4 style="margin:8px 0 4px 0; color:#0f172a;">{pr['매물제목']}</h4>
                    <p style="margin:2px 0; color:#dc2626; font-weight:800; font-size:1.05rem;">{pr['가격설명']}</p>
                    <p style="margin:4px 0; font-size:0.86rem; color:#334155;">
                        📐 전용 <b>{pr['전용평수']}평</b> (사무실 {pr['사무실평수']}평)<br>
                        ⚡ 전력 {pr['전력']} | 📏 층고 {pr['층고']}<br>
                        {hoist_badge} | 🚛 {pr['도로조건']}
                    </p>
                </div>
                """, unsafe_allow_html=True)


# ==============================================================================
# [사이드 메뉴 4] 💬 카톡 멀티 브리핑 & 네이버 블로그 원고 자동생성
# ==============================================================================
elif selected_menu == MENU_LIST[3]:
    st.subheader("💬 손님 전송용 카톡 멀티 브리핑 & 확보 매물 네이버 블로그 상위노출 원고 1클릭 생성")
    df_props_b = get_fast_df("properties", PROP_COLUMNS)

    if df_props_b.empty:
        st.info("등록된 매물이 없습니다. 왼쪽 메뉴 [➕ 2. 새 매물 등록]에서 매물을 먼저 등록해 주세요.")
    else:
        options_list = [
            f"[{r['매물번호']}] ({r['권역']} {r['해당층수']}) {r['매물제목']} - {r['가격설명']}"
            for _, r in df_props_b.iterrows()
        ]
        selected_items = st.multiselect(
            "손님에게 브리핑할 매물을 선택하세요 (여러 개 선택 시 카톡 멀티 브리핑 리스트로 한 번에 묶어줍니다)",
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

                kakao_lines.append("👉 실시간 전체 매물 보기: https://threven.github.io/my-realestate-app/")
                kakao_lines.append("📞 현장 답사 및 상세 문의: 우리부동산 032-582-6200 / 직통 010-2660-8276")
                st.code("\n".join(kakao_lines), language="markdown")

            with b_col2:
                st.markdown("#### 🟢 네이버 블로그 상위노출 포스팅용 원고 (첫 번째 선택 매물 기준)")
                r0 = sel_rows.iloc[0]
                hoist_blog = f"설치 완료 ({r0['호이스트제원']})" if r0['호이스트유무'] == "있음" else "없음 (추후 설치 협의 가능)"
                blog_text = f"""### 📌 추천 상위노출 제목 3선 (택 1)
1. 인천 {r0['권역']} {r0['거래구분']} {r0['해당층수']} 전용 {r0['전용평수']}평 실매물 현장리뷰 ({r0['매물제목']})
2. [{r0['권역']} {r0['거래구분']}] 전용 {r0['전용평수']}평 단독/제조 공장 ({r0['도로조건']} · 호이스트 {hoist_blog}) - 우리부동산 김소장
3. 인천 서구 {r0['권역']} 즉시 가동 가능한 {r0['전용평수']}평 {r0['거래구분']}, 전력 {r0['전력']} · 층고 {r0['층고']} 완비

---

안녕하세요! 인천 서구 공장·창고 전문 파트너, **우리부동산 공인중개사사무소 대표 공인중개사 김태형(김소장)**입니다.
오늘 소개해 드릴 현장은 **{r0['권역']}**에 위치한 작업 효율 뛰어난 **{r0['해당층수']} {r0['거래구분']}** 매물입니다.

📷 **[사진 1 삽입 위치: 공장 건물 외관 및 전면 진입도로 폭 (화물차 진출입로 강조)]**

---
### 📌 [매물 핵심 스펙 한눈에 보기]
| 구분 | 상세 스펙 |
| :--- | :--- |
| **매물번호** | {r0['매물번호']} |
| **소재지역** | 인천광역시 서구 {r0['권역']} ({r0['용도지역']}) |
| **거래조건** | **{r0['가격설명']}** |
| **해당층수** | {r0['해당층수']} |
| **전용면적** | **공장/창고 전용 {r0['전용평수']}평** (사무실 {r0['사무실평수']}평 별도) |
| **유효층고 / 전력** | 층고 {r0['층고']} / 계약전력 {r0['전력']} |
| **호이스트 설비** | {hoist_blog} |
| **진입도로 / 입주** | {r0['도로조건']} / {r0['입주날짜']} |

📷 **[사진 2 삽입 위치: 공장 내부 에폭시 바닥 및 호이스트 레일/층고 사진]**

---
### 💡 [김소장의 현장 실사 체크 포인트]
{r0['핵심특징'] if str(r0['핵심특징']).strip() else '차량 진출입이 수월하고 바닥 에폭시 및 기본 동력 설비가 잘 갖춰져 있어 즉시 가동 가능한 알짜 공장입니다.'}

추천 업종으로는 **[{r0['추천업종'] if str(r0['추천업종']).strip() else '일반 제조업, 정밀가공, 물류창고'}]** 등을 강력 추천합니다.

📷 **[사진 3 삽입 위치: 동력 배전반, 부속 사무실 및 외부 마당 사진]**

---
🏭 **인천 서구 석남동·가좌동·원창동·경서동 공장 매매/임대 문의는 언제든 편하게 연락 주세요!**
- **상호** : 우리부동산 공인중개사사무소 (대표: 김태형)
- **소재지** : 인천 서구 건지로 167 (석남역 인근)
- **대표번호** : 매매 032-582-6200 / 임대 032-576-2600 / **직통 010-2660-8276**
- **실시간 매물 홈페이지** : https://threven.github.io/my-realestate-app/

#인천서구공장 #{r0['권역']}공장 #{r0['권역']}{r0['거래구분']} #인천공장전문 #우리부동산 #김소장"""
                st.code(blog_text, language="markdown")


# ==============================================================================
# [사이드 메뉴 5] 🎯 현장 임장 / 물건따기 (복붙 정규식 파서)
# ==============================================================================
elif selected_menu == MENU_LIST[4]:
    st.subheader("🎯 현장 임장 / 물건따기 장부 (복붙 자동추출 & 시트 연동)")
    raw_paste = st.text_area(
        "📋 1) 현장 메모 / 카톡 / 건축물대장 텍스트 복사·붙여넣기",
        height=90,
        placeholder="예: 석남동 223-12 대성정밀 2층 85평 보3000/월280 동력50kw 호이스트2.8톤 김철수 사장님 010-1234-5678"
    )

    parsed_info = {"region": "석남동", "jibun": "", "floor": "지상 1층", "area": "80", "price": "", "spec": "", "phone": ""}
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
            st.rerun()

    df_hunt = get_fast_df("hunting", HUNT_COLUMNS)
    if not df_hunt.empty:
        st.markdown("#### 📋 누적 임장 장부 (셀 직접 수정 가능)")
        edited_hunt = st.data_editor(df_hunt, num_rows="dynamic", use_container_width=True, height=320)
        if st.button("💾 임장 장부 수정사항 저장", use_container_width=True):
            overwrite_sheet_fast("hunting", HUNT_COLUMNS, edited_hunt)
            st.toast("임장 장부 업데이트 완료!", icon="✅")
            st.rerun()


# ==============================================================================
# [사이드 메뉴 6] 🏗️ 신축공장분양 대출/취득세/부가세 환급 자금계획 계산기 (본업 핵심 영업용)
# ==============================================================================
elif selected_menu == MENU_LIST[5]:
    st.subheader("🏗️ 신축공장분양 · 자가공장 마련 자금계획 & 대출/취득세/부가세 환급 시뮬레이터")
    st.caption("월세 임차 중인 대표님들께 '자가공장 매입/분양 시 실제 들어가는 자기자본과 월 이자 비교표'를 1초 만에 브리핑해 드리는 본업 클로징 도구입니다.")

    sim1, sim2, sim3 = st.columns(3)
    with sim1:
        f_pyeong = st.number_input("분양/매입 평수 (평)", min_value=10.0, value=80.0, step=5.0)
        f_unit_price = st.number_input("평당 분양가/매매가 (만원)", min_value=100, value=1000, step=50)
    with sim2:
        f_loan_ratio = st.slider("시설자금 대출 비율 (%)", min_value=50, max_value=90, value=80, step=5)
        f_interest = st.number_input("예상 대출 금리 (연 %)", min_value=2.0, max_value=8.0, value=4.2, step=0.1)
    with sim3:
        f_tax_discount = st.selectbox("취득세 감면 적용", ["기본 세율 (4.6%)", "지식산업센터/산단 감면 (35% 감면 적용)", "창업중소기업 감면 (50~75% 감면)"])
        current_rent = st.number_input("현재 납부 중인 월세 (비교용, 만원)", min_value=0, value=280, step=10)

    total_price = int(f_pyeong * f_unit_price)
    loan_amt = int(total_price * (f_loan_ratio / 100.0))
    self_cash = total_price - loan_amt
    monthly_interest = int((loan_amt * (f_interest / 100.0)) / 12)
    vat_refund_est = int(total_price * 0.35 * 0.10)

    if "35%" in f_tax_discount:
        acq_tax = int(total_price * 0.046 * 0.65)
    elif "창업" in f_tax_discount:
        acq_tax = int(total_price * 0.046 * 0.50)
    else:
        acq_tax = int(total_price * 0.046)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 매입/분양 금액", f"{total_price:,} 만원", f"건물분 부가세환급 약 {vat_refund_est:,}만")
    m2.metric(f"대출 가능액 ({f_loan_ratio}%)", f"{loan_amt:,} 만원")
    m3.metric("필요 실투자금 (자기자본)", f"{self_cash:,} 만원", f"취득세 약 {acq_tax:,}만 별도")
    diff_rent = current_rent - monthly_interest
    m4.metric("월 예상 이자", f"월 {monthly_interest:,} 만원", f"현재 월세 대비 월 {diff_rent:+,}만 절감")

    sim_report = f"""📊 [우리부동산 신축공장 분양 · 자가공장 매입 자금 시뮬레이션 리포트]
- 검토 면적 : 전용/분양 {f_pyeong}평 (평당 {f_unit_price:,}만원)
- 총 분양/매매가 : {total_price:,}만원 (건물분 부가세 약 {vat_refund_est:,}만원 조기환급 대상)
- 기업 시설자금대출({f_loan_ratio}%) : 약 {loan_amt:,}만원
- 필요 실투자 자기자본 : {self_cash:,}만원 (+ 예상 취득세 약 {acq_tax:,}만원 / {f_tax_discount})
- 월 예상 이자(연 {f_interest}%) : 월 약 {monthly_interest:,}만원
  👉 기존 월세({current_rent:,}만원)와 비교 시 매월 {diff_rent:+,}만원 차이로 내 자가공장 소유 가능!

📞 맞춤 분양 및 기업시설자금 저리대출 상담 : 우리부동산 대표 김태형 (032-582-6200 / 010-2660-8276)"""
    st.code(sim_report, language="markdown")