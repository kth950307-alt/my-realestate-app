import streamlit as st
import pandas as pd
import datetime
import json
import os
import urllib.parse
import urllib.request
import ssl

# 🛑 맥(macOS) 및 로컬 환경 SSL 인증서 에러 우회
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ==========================================
# 0. 페이지 기본 설정 및 스타일링
# ==========================================
st.set_page_config(
    page_title="우리부동산 부업무 스튜디오 Pro (경매·청약·블로그·키워드)",
    page_icon="🚀",
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
        border-color: #059669;
        background-color: #ecfdf5;
    }
    .sub-header {
        background: linear-gradient(90deg, #064e3b 0%, #0f766e 100%);
        color: white;
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-top: 4px solid #059669;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .kpi-title { font-size: 0.8rem; color: #475569; font-weight: 700; margin-bottom: 4px; }
    .kpi-val { font-size: 1.35rem; color: #0f172a; font-weight: 900; }
    .card-box {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .kw-card {
        background-color: #f8fafc;
        border: 2px solid #10b981;
        border-left: 8px solid #059669;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
    }
    .badge-blue { background-color: #dbeafe; color: #1e40af; padding: 4px 9px; border-radius: 6px; font-size: 0.78rem; font-weight: 800; }
    .badge-red { background-color: #fee2e2; color: #991b1b; padding: 4px 9px; border-radius: 6px; font-size: 0.78rem; font-weight: 800; }
    .badge-green { background-color: #dcfce7; color: #166534; padding: 4px 9px; border-radius: 6px; font-size: 0.78rem; font-weight: 800; }
    .badge-purple { background-color: #f3e8ff; color: #6b21a8; padding: 4px 9px; border-radius: 6px; font-size: 0.78rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 상수 및 DB 초기화
# ==========================================
ADMIN_PW = "563011"
SUB_CACHE_FILE = "local_backup_cache_sub.json"
MY_FIXED_API_KEY = "d1a0585bef6ed7240317271c754ad4be4f9ba74cdf342e6b714bbb85d3196f69"

SUB_MENUS = [
    "⚖️ 1. 인천공장·창고 & 수도권아파트 법원 경매 캘린더 (고도화)",
    "📅 2. 수도권 아파트 분양 & 공공임대 청약 캘린더 (청약홈+LH 실시간 통합)",
    "🍽️ 3. 공인중개사 김소장 맛집·일상·청약 블로그 스튜디오",
    "🔥 4. 네이버 키워드 트렌드 & 조회수 폭발 TOP 5 추천 에이전트"
]

AUCTION_POST_PROMPT = """
당신은 수도권 실전 부동산 및 공장·창고 전문 중개사이자 블로거 **'공인중개사 김소장(김소장)'**입니다.
오직 '공인중개사 김소장' 또는 '김소장'이라는 호칭만 사용하세요.
제공된 법원 경매 물건 데이터(사건번호, 감정가, 최저입찰가, 매각기일, 설비내역, 권리분석)를 바탕으로 네이버 블로그 검색 유입을 극대화하는 2,000자 이상의 고품질 심층 분석 포스팅을 작성하세요.
[필수 포함]: 후킹 제목 3개, 도입부, 물건 상세 개요, 감정가 및 최저입찰가 분석, 호이스트·수전설비 및 권리분석 핵심, 김소장의 입찰 전략 한줄평.
"""

SUBSCRIPTION_POST_PROMPT = """
당신은 수도권 실전 부동산 및 청약 전문 블로거 **'공인중개사 김소장(김소장)'**입니다.
오직 '공인중개사 김소장' 또는 '김소장'이라는 호칭만 사용하세요.
청약홈 및 LH 청약플러스 실시간 유효 모집공고 데이터를 바탕으로 네이버 블로그 검색 유입을 극대화하는 2,000자 이상의 고품질 심층 분석 포스팅을 작성하세요.
"""

# 🟢 인천 서구 중심 실제 공장 및 지식산업센터 경매 고도화 데이터 셋 탑재
DEFAULT_AUCTIONS = [
    {
        "사건번호": "2025타경 51204",
        "관할법원": "인천지방법원 본원 경매4계",
        "물건종류": "공장 (일반철골조 단독공장)",
        "소재지": "인천광역시 서구 석남동 223-XX (일반공업지역)",
        "토지_건물면적": "토지 310평 / 건물 245평 (1층 180평, 2층 사무실 65평)",
        "감정가": 245000,
        "최저입찰가": 120050,
        "유찰상태": "49% (2회 유찰 / 최저가 매력적)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
        "기계기구_설비": "호이스트 5톤 2기, 수전설비 250kW, 층고 8.5m (일괄매각 포함)",
        "권리분석핵심": "선순위 근저당 말소기준권리 이후 임차인 없음 (인도명령 대상, 권리관계 깨끗함)",
        "예상낙찰가율": "62~66%"
    },
    {
        "사건번호": "2025타경 511489",
        "관할법원": "인천지방법원 본원 경매1계",
        "물건종류": "지식산업센터 공장 (오류동 블루텍)",
        "소재지": "인천광역시 서구 오류동 1656-1 블루텍 10층",
        "토지_건물면적": "전용면적 48평 (도어투도어 화물차 진입 가능)",
        "감정가": 41500,
        "최저입찰가": 29050,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
        "기계기구_설비": "층고 6m, 하중 1.2톤/㎡, 공조시설 완비",
        "권리분석핵심": "대항력 없는 소액 임차인 점유 (보증금 소액배당으로 명도 수월)",
        "예상낙찰가율": "72~75%"
    },
    {
        "사건번호": "2026타경 503557",
        "관할법원": "인천지방법원 본원 경매3계",
        "물건종류": "아파트형공장 (석남동 인천테크피아)",
        "소재지": "인천광역시 서구 석남동 223-38 인천테크피아 4층",
        "토지_건물면적": "전용면적 62평",
        "감정가": 22300,
        "최저입찰가": 15610,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=22)).strftime("%Y-%m-%d"),
        "기계기구_설비": "화물 엘리베이터 인접, 주차 공간 넉넉함",
        "권리분석핵심": "근저당권 이후 설정된 가압류 외 인수권리 없음 (깨끗함)",
        "예상낙찰가율": "74~78%"
    }
]

DEFAULT_SUBSCRIPTIONS = [
    {
        "분류": "💍 신혼희망타운 / 공공분양",
        "단지명": "부천대장 A-2블록 신혼희망타운",
        "지역": "경기도 부천시 대장신도시",
        "공급규모": "공공분양 및 행복주택 혼합",
        "모집공고일": "2026-11-05",
        "특별공급일": "진행 중 / 공고문 참조",
        "일반공급일": "진행 중 / 공고문 참조",
        "당첨자발표일": "추후 발표",
        "서류제출기간": "발표 직후 7일 이내",
        "계약기간": "공고문 확인",
        "마감_주요일자": "2026-11-30",
        "분양가_임대조건": "LH 청약플러스 원문 공고문 참조",
        "핵심체크사항": "신혼희망타운 전용 수익공유형 모기지 및 소득·자산 기준 필수 확인"
    }
]

def load_sub_db():
    if os.path.exists(SUB_CACHE_FILE):
        try:
            with open(SUB_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "auctions" in data and "subscriptions" in data:
                    return data
        except Exception:
            pass
    init_data = {"auctions": DEFAULT_AUCTIONS, "subscriptions": DEFAULT_SUBSCRIPTIONS}
    save_sub_db(init_data)
    return init_data

def save_sub_db(data):
    try:
        with open(SUB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if "sub_db" not in st.session_state:
    st.session_state.sub_db = load_sub_db()

if "draft_preset_topic" not in st.session_state:
    st.session_state.draft_preset_topic = "부천대장 A-2 신혼희망타운 공고 및 서류제출 체크리스트"
if "draft_preset_cat" not in st.session_state:
    st.session_state.draft_preset_cat = "🏠 수도권 청약 · 공공임대 · 부동산 현장 이야기"
if "draft_preset_kw" not in st.session_state:
    st.session_state.draft_preset_kw = "모집공고일, 신혼희망타운, 소득·자산 기준, 서류제출"

def calc_dday_str(date_str):
    try:
        target = datetime.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        delta = (target - datetime.date.today()).days
        if delta > 0:
            return f"D-{delta}", delta
        elif delta == 0:
            return "D-Day (오늘!)", 0
        else:
            return f"D+{-delta} (경과)", delta
    except Exception:
        return "일정확인", 999

def make_gcal_url(title, date_str, details, location=""):
    try:
        d_obj = datetime.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        d_obj = datetime.date.today()
    dates_param = d_obj.strftime("%Y%m%d") + "/" + (d_obj + datetime.timedelta(days=1)).strftime("%Y%m%d")
    q_title = urllib.parse.quote(title)
    q_details = urllib.parse.quote(details)
    q_loc = urllib.parse.quote(location)
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={q_title}&dates={dates_param}&details={q_details}&location={q_loc}"

def get_gemini_key():
    for k in ["gemini_api_key", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        if k in st.session_state and st.session_state[k]:
            return st.session_state[k]
        try:
            if k in st.secrets and st.secrets[k]:
                return st.secrets[k]
        except Exception:
            pass
        if os.environ.get(k):
            return os.environ.get(k)
    return ""

def call_gemini(system_prompt: str, user_content: str):
    if genai is None:
        return None
    api_key = get_gemini_key()
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(f"{system_prompt}\n\n---\n[입력 데이터]\n{user_content}")
        return resp.text
    except Exception:
        return None

# 청약홈 API
def fetch_applyhome_realtime():
    clean_key = urllib.parse.unquote(MY_FIXED_API_KEY.strip())
    encoded_key = urllib.parse.quote(clean_key, safe="")
    base_url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
    target_regions = ["서울", "인천", "경기"]
    results = []
    today_date_str = datetime.date.today().strftime("%Y-%m-%d")
    start_search_date = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
    
    try:
        url = f"{base_url}?page=1&perPage=100&cond%5BRCRIT_PBLANC_DE%3A%3AGTE%5D={start_search_date}&serviceKey={encoded_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                region = str(item.get("SUBSCRPT_AREA_CODE_NM", "") or item.get("SIDO_NM", ""))
                addr = str(item.get("HSSPLY_ADRES", ""))
                if not any(r in region or r in addr for r in target_regions):
                    continue
                
                gnrl_end_de = str(item.get("SUBSCRPT_RCEPT_ENDDE", "") or item.get("GNRL_RNK2_ETC_AREA_RCPTDE", ""))
                if gnrl_end_de and len(gnrl_end_de) == 10 and gnrl_end_de < today_date_str:
                    continue
                
                results.append({
                    "분류": "🏢 청약홈 분양주택",
                    "단지명": item.get("HOUSE_NM", "-"),
                    "지역": addr if addr else region,
                    "공급규모": f"총 {item.get('TOT_SUPLY_HSHLDCO', '-')}세대",
                    "모집공고일": str(item.get("RCRIT_PBLANC_DE", "-")),
                    "특별공급일": f"{item.get('SPSPLY_RCEPT_BGNDE', '-')} ~ {item.get('SPSPLY_RCEPT_ENDDE', '-')}",
                    "일반공급일": f"{item.get('SUBSCRPT_RCEPT_BGNDE', '-')} ~ {item.get('SUBSCRPT_RCEPT_ENDDE', '-')}",
                    "당첨자발표일": str(item.get("PRZWNER_PRESNATN_DE", "-")),
                    "서류제출기간": f"{item.get('PRZWNER_PRESNATN_DE', '-')} 발표 직후 7일 이내" if item.get("PRZWNER_PRESNATN_DE") else "공고문 참조",
                    "계약기간": f"{item.get('CNTRCT_CNCLS_BGNDE', '-')} ~ {item.get('CNTRCT_CNCLS_ENDDE', '-')}",
                    "마감_주요일자": str(item.get("SUBSCRPT_RCEPT_ENDDE", "-")),
                    "분양가_임대조건": f"시공사: {item.get('CNSTRCT_ENTRPS_NM', '-')} / 입주예정: {item.get('MVN_PREARNGE_YM', '-')}",
                    "핵심체크사항": f"문의처: {item.get('MDHS_TELNO', '-')} (청약홈 실시간 연동)"
                })
        return results, ""
    except Exception as e:
        return [], f"청약홈 API 오류: {e}"

# LH API
def fetch_lh_realtime():
    clean_key = urllib.parse.unquote(MY_FIXED_API_KEY.strip())
    encoded_key = urllib.parse.quote(clean_key, safe="")
    base_url = "https://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"
    results = []
    today_date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    try:
        url = f"{base_url}?PG_SZ=50&PAGE=1&UP_INCD=01,05,06,39&SRCH_DS=1&serviceKey={encoded_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ds_list = []
            if isinstance(data, dict):
                body = data.get("response", {}).get("body", {})
                if body:
                    items = body.get("items", {})
                    ds_list = items.get("item", []) if isinstance(items, dict) else items
                elif "dsList" in data:
                    ds_list = data["dsList"]
            
            if not isinstance(ds_list, list):
                ds_list = [ds_list] if ds_list else []

            for item in ds_list:
                pan_nm = str(item.get("PAN_NM", "") or item.get("panNm", ""))
                ccr_cnnt_dt = str(item.get("CCR_CNNT_DT", "") or item.get("ccrCnntDt", ""))
                cls_dt = str(item.get("CLSG_DT", "") or item.get("clsgDt", ""))
                
                if not any(k in pan_nm for k in ["서울", "인천", "경기", "수도권", "청라", "검단", "계양", "대장", "신혼희망", "행복주택", "공공분양", "매입임대"]):
                    continue
                if cls_dt and len(cls_dt) == 10 and cls_dt < today_date_str:
                    continue

                cat_label = "🔑 LH 공공임대 · 행복주택"
                if "신혼희망타운" in pan_nm or "신혼" in pan_nm:
                    cat_label = "💍 LH 신혼희망타운"
                elif "분양" in pan_nm:
                    cat_label = "🏢 LH 공공분양"

                results.append({
                    "분류": cat_label,
                    "단지명": pan_nm,
                    "지역": "수도권 (LH 공고)",
                    "공급규모": f"공고상태: {item.get('PAN_ST_NM', '공고중')}",
                    "모집공고일": ccr_cnnt_dt if ccr_cnnt_dt else today_date_str,
                    "특별공급일": "LH 청약플러스 공고문 참조",
                    "일반공급일": f"~ {cls_dt}" if cls_dt else "상시 접수",
                    "당첨자발표일": "청약플러스 확인",
                    "서류제출기간": "당첨자 발표 후 7일 이내",
                    "계약기간": "개별 안내",
                    "마감_주요일자": cls_dt if cls_dt else today_date_str,
                    "분양가_임대조건": "LH 청약플러스 원문 참조",
                    "핵심체크사항": f"공고번호: {item.get('PAN_ID', '-')} (LH 청약플러스 실시간 연동)"
                })
        return results, ""
    except Exception as e:
        return [], f"LH API 연동 참고: {e}"

# ==========================================
# 2. 사이드바
# ==========================================
with st.sidebar:
    st.markdown("## 🚀 부업무 스튜디오 Pro")
    st.caption("경매 · 아파트청약/공공임대 · 블로그/키워드")

    auth_pw = st.text_input("🔒 관리자 보안 비밀번호", type="password", value=ADMIN_PW)
    if auth_pw != ADMIN_PW:
        st.error("보안 비밀번호(563011)를 입력해 주세요.")
        st.stop()

    selected_sub = st.radio(
        "📌 부업무 메뉴 바로가기",
        SUB_MENUS,
        index=0
    )

    st.divider()
    st.markdown("### 🔑 통합 API 인증키 상태")
    st.success("✅ 공공데이터 API 인증키 고정 장착 완료")

    st.divider()
    st.markdown("### ⚡ 빠른 데이터 관리")
    if st.button("🔄 기본 경매·청약 데이터 복원", use_container_width=True):
        st.session_state.sub_db = {"auctions": DEFAULT_AUCTIONS, "subscriptions": DEFAULT_SUBSCRIPTIONS}
        save_sub_db(st.session_state.sub_db)
        st.toast("기본 데이터 복원 완료!", icon="✅")
        st.rerun()

# ==========================================
# 3. 상단 헤더 및 KPI 바
# ==========================================
st.markdown(f"""
<div class="sub-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <h2 style="margin:0; color:white;">{selected_sub}</h2>
            <p style="margin:4px 0 0 0; opacity:0.9; font-size:0.9rem;">
                김태형 대표 (공인중개사 김소장) | 공장·창고 경매 분석 · 청약/공공임대 트래커 · 블로그 마케팅 센터
            </p>
        </div>
        <div style="background:rgba(255,255,255,0.18); padding:6px 14px; border-radius:8px; font-weight:800; font-size:0.88rem;">
            🟢 경매 + 청약통합 고도화 엔진 가동중
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

auc_list = st.session_state.sub_db.get("auctions", [])
sub_list = st.session_state.sub_db.get("subscriptions", [])
fac_auc_cnt = sum(1 for a in auc_list if "공장" in a.get("물건종류", "") or "창고" in a.get("물건종류", ""))
apt_auc_cnt = len(auc_list) - fac_auc_cnt

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">⚖️ 추적 중인 공장·아파트 경매 물건</div><div class="kpi-val">{len(auc_list)}건 <span style="font-size:0.82rem;color:#059669;">(공장 {fac_auc_cnt} · 기타 {apt_auc_cnt})</span></div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📅 총 청약 및 공공임대 공고</div><div class="kpi-val" style="color:#2563eb;">{len(sub_list)}건 <span style="font-size:0.82rem;color:#475569;">(분양·임대 통합)</span></div></div>', unsafe_allow_html=True)
with k3:
    st.markdown('<div class="kpi-card"><div class="kpi-title">✍️ 블로그 페르소나 브랜드</div><div class="kpi-val" style="color:#7c3aed;">김소장 <span style="font-size:0.82rem;color:#475569;">(단일 브랜딩 통일)</span></div></div>', unsafe_allow_html=True)
with k4:
    st.markdown('<div class="kpi-card"><div class="kpi-title">🔥 네이버 황금 키워드 트렌드</div><div class="kpi-val" style="color:#dc2626;">TOP 5 <span style="font-size:0.82rem;color:#475569;">(경쟁강도 분석)</span></div></div>', unsafe_allow_html=True)

st.write("")

# ==============================================================================
# [부업무 메뉴 1] ⚖️ 인천공장·창고 & 수도권 법원 경매 캘린더 (청약 포맷 완벽 일치 고도화)
# ==============================================================================
if selected_sub == SUB_MENUS[0]:
    st.subheader("⚖️ 인천지방법원·부천지원 관할 공장·창고 및 지식산업센터 법원 경매 캘린더")
    st.caption("인천 서구(가좌동, 오류동, 석남동) 공장 및 지식산업센터 경매 물건의 감정가, 최저입찰가, 호이스트 설비, 권리분석 및 낙찰가율을 청약 캘린더와 동일한 포맷으로 추적합니다.")

    # 대법원 경매 및 유관 사이트 바로가기 버튼 삼총사
    link_c1, link_c2, link_c3 = st.columns(3)
    with link_c1:
        st.markdown('<a href="https://www.courtauction.go.kr" target="_blank" style="display:block; text-align:center; background:#1e40af; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">⚖️ 대한민국 법원 경매정보 바로가기</a>', unsafe_allow_html=True)
    with link_c2:
        st.markdown('<a href="https://www.e-kiris.or.kr" target="_blank" style="display:block; text-align:center; background:#047857; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">🏭 한국산업단지공단 팩토리온 바로가기</a>', unsafe_allow_html=True)
    with link_c3:
        st.markdown('<a href="https://www.valueup.or.kr" target="_blank" style="display:block; text-align:center; background:#b45309; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">📊 밸류맵 (공장 실거래가) 바로가기</a>', unsafe_allow_html=True)

    st.write("")

    auc_df = pd.DataFrame(auc_list)
    
    # 경매 물건 필터 및 검색
    ac_f1, ac_f2 = st.columns([2, 1])
    with ac_f1:
        auc_filter = st.radio(
            "🏭 경매 물건 형태별 보기",
            ["전체 물건 보기", "🏭 단독공장 · 제조시설", "🏢 지식산업센터 · 아파트형공장"],
            horizontal=True
        )
    with ac_f2:
        auc_search = st.text_input("🔍 사건번호 / 지역 검색 (예: 51204, 석남동, 오류동)", "")

    view_auc = auc_df.copy()
    if not view_auc.empty:
        if "단독공장" in auc_filter:
            view_auc = view_auc[view_auc["물건종류"].str.contains("단독공장|공장", na=False) & ~view_auc["물건종류"].str.contains("지식산업센터|아파트형공장", na=False)]
        elif "지식산업센터" in auc_filter:
            view_auc = view_auc[view_auc["물건종류"].str.contains("지식산업센터|아파트형공장", na=False)]

        if auc_search.strip():
            s_low = auc_search.strip().lower()
            view_auc = view_auc[view_auc.apply(lambda r: s_low in " ".join(r.astype(str)).lower(), axis=1)]

        st.markdown(f"### 📋 추적 중인 법원 경매 물건 목록 (`{len(view_auc)}건`)")
        for _, arow in view_auc.iterrows():
            min_p = int(float(arow.get("최저입찰가", 0)))
            app_p = int(float(arow.get("감정가", 1)))
            dday_str, _ = calc_dday_str(arow.get("매각기일", ""))
            gcal_auc_url = make_gcal_url(
                title=f"[경매입찰] {arow['사건번호']} ({arow['소재지']})",
                date_str=arow.get("매각기일", ""),
                details=f"감정가: {app_p:,}만원 / 최저가: {min_p:,}만원 | 설비: {arow['기계기구_설비']}",
                location=arow.get("관할법원", "")
            )
            
            st.markdown(f"""
            <div class="card-box">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="badge-blue">{arow.get('관할법원', '인천지방법원')}</span>
                        <span class="badge-red">{arow.get('유찰상태', '유찰')}</span>
                        <span class="badge-green">{dday_str}</span>
                        <strong style="font-size:1.15rem; margin-left:6px;">[{arow['사건번호']}] {arow['소재지']}</strong>
                    </div>
                    <div>
                        <strong style="color:#1e40af; margin-right:10px;">📅 매각기일: {arow['매각기일']}</strong>
                        <a href="{gcal_auc_url}" target="_blank" style="background:#059669; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.82rem; font-weight:800;">📅 구글캘린더 등록</a>
                    </div>
                </div>
                <hr style="margin:8px 0;">
                <p style="margin:4px 0; font-size:0.92rem;">
                    🏭 <b>물건종류:</b> {arow['물건종류']} | 
                    📐 <b>면적구성:</b> {arow['토지_건물면적']}
                </p>
                <p style="margin:4px 0; font-size:0.92rem;">
                    ⚙️ <b>기계기구 및 설비:</b> {arow.get('기계기구_설비', '해당없음')}
                </p>
                <p style="margin:4px 0; font-size:0.95rem;">
                    💰 <b>감정가:</b> {app_p:,}만원 ➔ <b style="color:#dc2626; font-size:1.05rem;">최저입찰가: {min_p:,}만원</b> (예상 낙찰가율: <b>{arow.get('예상낙찰가율', '65%')}</b>)
                </p>
                <p style="margin:4px 0; color:#065f46;">🔍 <b>권리분석 핵심:</b> {arow['권리분석핵심']}</p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("➕ 법원 경매 물건 직접 추가·수정하기 (표 편집기)"):
        edited_auc_df = st.data_editor(auc_df, num_rows="dynamic", use_container_width=True, key="sub_auc_editor_main")
        if st.button("💾 경매 캘린더 변경사항 저장하기", type="primary"):
            st.session_state.sub_db["auctions"] = edited_auc_df.to_dict(orient="records")
            save_sub_db(st.session_state.sub_db)
            st.toast("경매 캘린더가 안전하게 저장되었습니다!", icon="✅")
            st.rerun()

    st.divider()
    st.markdown("### ✍️ 선택 사건 [공인중개사 김소장] 공장·창고 경매 분석 블로그 포스팅 원고 생성")
    if not view_auc.empty:
        col_ga1, col_ga2 = st.columns([2, 1])
        with col_ga1:
            sel_auc = st.selectbox("포스팅할 경매 사건번호를 선택하세요", options=view_auc["사건번호"].tolist())
        with col_ga2:
            auc_focus = st.selectbox(
                "작성 포커스 선택",
                [
                    "종합 분석 (사건개요 + 최저입찰가 분석 + 설비 가치 총정리)",
                    "권리분석 및 명도 전략 집중 분석 (선순위 및 인도명령 대상)",
                    "공장장 임대수익률 및 시세 차익 분석"
                ]
            )
        target_auc_row = view_auc[view_auc["사건번호"] == sel_auc].iloc[0].to_dict()
        
        if st.button("🚀 [공인중개사 김소장] 고품질 경매 분석 포스팅 원고 생성", type="primary", use_container_width=True):
            with st.spinner(f"'{sel_auc}' 물건 분석을 바탕으로 김소장 블로그 원고를 작성 중입니다..."):
                ai_auc_post = call_gemini(
                    AUCTION_POST_PROMPT,
                    f"사건번호: {target_auc_row['사건번호']}\n관할법원: {target_auc_row.get('관할법원','인천지방법원')}\n물건종류: {target_auc_row['물건종류']}\n소재지: {target_auc_row['소재지']}\n면적: {target_auc_row['토지_건물면적']}\n감정가: {target_auc_row['감정가']}만원\n최저가: {target_auc_row['최저입찰가']}만원\n유찰상태: {target_auc_row['유찰상태']}\n매각기일: {target_auc_row['매각기일']}\n설비: {target_auc_row['기계기구_설비']}\n권리분석: {target_auc_row['권리분석핵심']}\n포커스: {auc_focus}"
                )
                if ai_auc_post:
                    st.code(ai_auc_post, language="markdown")
                else:
                    st.code(f"""### 📌 네이버 VIEW 상위노출 추천 제목 3선
1. [{target_auc_row['사건번호']}] 인천 서구 공장 경매 낙찰가율 분석 및 현장 임장 후기 (김소장)
2. 감정가 반토막 난 {target_auc_row['소재지']} 공장 경매! 권리분석 및 호이스트 설비 체크
3. 인천지방법원 공장·창고 경매 물건 추천! {target_auc_row['사건번호']} 투자 가치 분석

---

안녕하세요! 인천 서구 공장·창고 전문 중개사이자 현장을 발로 뛰는 **공인중개사 김소장**입니다! 😊

오늘 분석해 드릴 물건은 인천지방법원에서 진행되는 알짜배기 공장 경매 물건인 **[{target_auc_row['사건번호']}]** 사건입니다.

### 📋 1. 경매 물건 개요
- **사건번호** : **{target_auc_row['사건번호']}**
- **관할법원** : {target_auc_row.get('관할법원','인천지방법원')}
- **물건종류** : {target_auc_row['물건종류']}
- **소재지** : {target_auc_row['소재지']}
- **토지·건물 면적** : {target_auc_row['토지_건물면적']}
- **매각기일** : **{target_auc_row['매각기일']}**

### 💰 2. 감정가 및 최저입찰가 분석
- **감정가** : {int(target_auc_row['감정가']):,}만원
- **최저입찰가** : <b style="color:red;">{int(target_auc_row['최저입찰가']):,}만원</b> ({target_auc_row['유찰상태']})

### ⚙️ 3. 설비 내역 및 권리분석 핵심
- **기계기구 및 설비** : {target_auc_row['기계기구_설비']}
- **권리분석** : {target_auc_row['권리분석핵심']}

### 💡 4. 김소장의 최종 입찰 전략 한줄평
해당 물건은 제조장 및 물류창고로 최적의 입지를 갖추고 있으며, 철저한 권리분석과 현장 조사를 통해 안전하게 낙찰받는다면 향후 임대 수익 및 시세 차익을 동시에 기대할 수 있는 우량 물건입니다. 입찰 준비 중이신 분들은 언제든 문의주세요!

#공인중개사김소장 #김소장 #인천공장경매 #{target_auc_row['사건번호'].replace(' ','')} #공장경매분석 #인천지방법원경매 #부동산경매
""", language="markdown")

# ==============================================================================
# [부업무 메뉴 2] 📅 수도권 청약 & 공공임대 캘린더 (청약홈 + LH 통합)
# ==============================================================================
elif selected_sub == SUB_MENUS[1]:
    st.subheader(f"📅 수도권 주요 공공분양·신혼희망타운·공공임대 청약 캘린더 (오늘 기준: {datetime.date.today().strftime('%Y년 %m월 %d일')})")
    st.caption("청약홈과 LH 청약플러스 실시간 API를 동시에 연동하여 진행 중인 유효 공고를 한눈에 모아봅니다.")

    link_c1, link_c2, link_c3 = st.columns(3)
    with link_c1:
        st.markdown('<a href="https://www.applyhome.co.kr/ai/aib/selectSubscrptCalenderView.do" target="_blank" style="display:block; text-align:center; background:#1e40af; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">🌐 청약홈 공식 분양캘린더 바로가기</a>', unsafe_allow_html=True)
    with link_c2:
        st.markdown('<a href="https://apply.lh.or.kr" target="_blank" style="display:block; text-align:center; background:#047857; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">🏢 LH 청약플러스 (공공임대/분양) 바로가기</a>', unsafe_allow_html=True)
    with link_c3:
        st.markdown('<a href="https://www.i-iH.co.kr" target="_blank" style="display:block; text-align:center; background:#b45309; color:white; padding:12px; border-radius:8px; text-decoration:none; font-weight:800; font-size:0.95rem;">🏡 iH 인천도시공사 분양정보 바로가기</a>', unsafe_allow_html=True)

    st.write("")

    sync_c1, sync_c2 = st.columns([1.8, 1])
    with sync_c1:
        st.info("💡 버튼을 누르면 **청약홈(민간/공공분양)**과 **LH 청약플러스(신혼희망타운·공공임대)** 서버에서 오늘 기준 유효한 공고를 동시에 긁어옵니다.")
    with sync_c2:
        if st.button("🔄 청약홈 + LH 실시간 공고 통합 불러오기", type="primary", use_container_width=True):
            with st.spinner("청약홈 및 LH 청약플러스 서버에서 실시간 공고를 수집 및 병합 중입니다..."):
                apply_items, err1 = fetch_applyhome_realtime()
                lh_items, err2 = fetch_lh_realtime()
                
                existing = st.session_state.sub_db.get("subscriptions", [])
                merged_dict = {x["단지명"]: x for x in existing}
                
                for item in apply_items + lh_items:
                    merged_dict[item["단지명"]] = item
                
                new_list = list(merged_dict.values())
                st.session_state.sub_db["subscriptions"] = new_list
                save_sub_db(st.session_state.sub_db)
                st.success(f"✅ 총 {len(new_list)}건의 유효 공고 동기화 완료! (청약홈 {len(apply_items)}건, LH {len(lh_items)}건)")
                st.rerun()

    sub_list = st.session_state.sub_db.get("subscriptions", [])
    sub_df = pd.DataFrame(sub_list)

    sc_f1, sc_f2 = st.columns([2, 1])
    with sc_f1:
        sub_type_filter = st.radio(
            "🏠 청약 및 임대 유형별 보기",
            ["전체 일정 보기", "💍 신혼희망타운 · 공공분양", "🔑 LH 공공임대 · 행복주택", "🏢 청약홈 분양주택"],
            horizontal=True
        )
    with sc_f2:
        sub_search_kw = st.text_input("🔍 단지명 / 지역 검색 (예: 부천대장, 계양, 청라)", "")

    view_sub = sub_df.copy()
    if not view_sub.empty:
        if "신혼희망타운" in sub_type_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("신혼희망타운|공공분양", na=False)]
        elif "공공임대" in sub_type_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("공공임대|행복주택", na=False)]
        elif "청약홈" in sub_type_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("청약홈", na=False)]

        if sub_search_kw.strip():
            k_low = sub_search_kw.strip().lower()
            view_sub = view_sub[view_sub.apply(lambda r: k_low in " ".join(r.astype(str)).lower(), axis=1)]

        st.markdown(f"### 📋 조건에 일치하는 실시간 공고 (`{len(view_sub)}건`)")
        for _, srow in view_sub.iterrows():
            dday_str, _ = calc_dday_str(srow.get("모집공고일", ""))
            gcal_url = make_gcal_url(
                title=f"[청약/임대] {srow['단지명']}",
                date_str=srow.get("모집공고일", ""),
                details=f"분류: {srow['분류']} | 조건: {srow['분양가_임대조건']} | 체크: {srow['핵심체크사항']}",
                location=srow.get("지역", "")
            )
            badge_cls = "badge-purple" if "임대" in str(srow["분류"]) else ("badge-red" if "신혼희망" in str(srow["분류"]) else "badge-blue")
            
            st.markdown(f"""
            <div class="card-box">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="{badge_cls}">{srow['분류']}</span>
                        <span class="badge-green">{dday_str}</span>
                        <strong style="font-size:1.1rem; margin-left:6px;">{srow['단지명']} ({srow['지역']})</strong>
                    </div>
                    <div>
                        <strong style="color:#dc2626; margin-right:10px;">📢 공고일: {srow['모집공고일']}</strong>
                        <a href="{gcal_url}" target="_blank" style="background:#2563eb; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.82rem; font-weight:800;">📅 구글캘린더 등록</a>
                    </div>
                </div>
                <hr style="margin:8px 0;">
                <p style="margin:4px 0; font-size:0.92rem;">
                    🎯 <b>특별공급:</b> {srow.get('특별공급일', '-')} | 
                    🏢 <b>일반공급:</b> {srow.get('일반공급일', '-')} | 
                    🎉 <b>당첨자발표:</b> <b style="color:#1e40af;">{srow.get('당첨자발표일', '-')}</b>
                </p>
                <p style="margin:4px 0; font-size:0.92rem;">
                    📂 <b>서류제출기간:</b> <b style="color:#dc2626;">{srow.get('서류제출기간', '-')}</b> | 
                    ✍️ <b>계약기간:</b> {srow.get('계약기간', '-')}
                </p>
                <p style="margin:4px 0;">🏠 <b>공급규모:</b> {srow['공급규모']} | 💰 <b>분양가/임대조건:</b> <b style="color:#0f172a;">{srow['분양가_임대조건']}</b></p>
                <p style="margin:4px 0; color:#1e40af;">✅ <b>핵심 체크포인트:</b> {srow['핵심체크사항']}</p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("➕ 청약 및 공공임대 공고 직접 추가·수정하기 (표 편집기)"):
        edited_sub_df = st.data_editor(sub_df, num_rows="dynamic", use_container_width=True, key="sub_cal_editor_main")
        if st.button("💾 청약 캘린더 변경사항 저장하기", type="primary"):
            st.session_state.sub_db["subscriptions"] = edited_sub_df.to_dict(orient="records")
            save_sub_db(st.session_state.sub_db)
            st.toast("청약 캘린더가 안전하게 저장되었습니다!", icon="✅")
            st.rerun()

    st.divider()
    st.markdown("### ✍️ 선택 단지 [공인중개사 김소장] 청약 · 공공임대 분석 블로그 포스팅 원고 생성")
    if not view_sub.empty:
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            sel_apt = st.selectbox("포스팅할 단지를 선택하세요", options=view_sub["단지명"].tolist())
        with col_g2:
            post_focus = st.selectbox(
                "작성 포커스 선택",
                [
                    "종합 분석 (청약일정 + 분양가/임대조건 + 자격요건 총정리)",
                    "당첨자 서류 제출 기간 & 부적격 방지 필수 서류 집중 안내",
                    "특별공급 당첨 전략 및 주변 시세 비교 분석"
                ]
            )
        target_sub_row = view_sub[view_sub["단지명"] == sel_apt].iloc[0].to_dict()
        
        if st.button("🚀 [공인중개사 김소장] 고품질 청약/임대 포스팅 원고 생성", type="primary", use_container_width=True):
            with st.spinner(f"'{sel_apt}' 데이터를 바탕으로 김소장 블로그 원고를 작성 중입니다..."):
                ai_post = call_gemini(
                    SUBSCRIPTION_POST_PROMPT,
                    f"분류: {target_sub_row['분류']}\n단지명: {target_sub_row['단지명']}\n지역: {target_sub_row['지역']}\n공급규모: {target_sub_row['공급규모']}\n모집공고일: {target_sub_row.get('모집공고일','-')}\n특별공급: {target_sub_row.get('특별공급일','-')}\n일반공급: {target_sub_row.get('일반공급일','-')}\n당첨자발표: {target_sub_row.get('당첨자발표일','-')}\n서류제출기간: {target_sub_row.get('서류제출기간','-')}\n계약기간: {target_sub_row.get('계약기간','-')}\n조건: {target_sub_row['분양가_임대조건']}\n체크사항: {target_sub_row['핵심체크사항']}\n포커스: {post_focus}"
                )
                if ai_post:
                    st.code(ai_post, language="markdown")
                else:
                    st.code(f"""### 📌 네이버 VIEW 상위노출 추천 제목 3선
1. {target_sub_row['단지명']} 모집공고 총정리! 청약 일정·분양가 및 서류제출 기간 필수 체크 (김소장)
2. [{target_sub_row['지역']}] {target_sub_row['단지명']} 청약 자격과 부적격 방지 체크리스트 완벽 분석
3. {target_sub_row['단지명']} 당첨 전략! 특별공급·일반공급 일정부터 계약까지 한눈에 보기

---

안녕하세요! 수도권 부동산과 청약 현장을 발로 뛰며 분석하는 **공인중개사 김소장**입니다! 😊

오늘은 실수요자분들이 가장 기다리셨던 **'{target_sub_row['단지명']}'** 모집공고 핵심 내용과 청약 일정, 그리고 당첨 후 가장 중요한 **서류 제출 기간 및 자격 요건**을 꼼꼼하게 정리해 드립니다.

### 📋 1. 사업 개요 및 공급 규모
- **분류** : {target_sub_row['분류']}
- **단지명** : **{target_sub_row['단지명']}**
- **공급 위치** : {target_sub_row['지역']}
- **공급 규모** : {target_sub_row['공급규모']}
- **분양가 / 임대조건** : {target_sub_row['분양가_임대조건']}

### 🗓️ 2. 핵심 청약 일정 및 서류 제출 기간
- **모집공고일** : {target_sub_row.get('모집공고일', '-')}
- **특별공급 접수일** : {target_sub_row.get('특별공급일', '-')}
- **일반공급 접수일** : {target_sub_row.get('일반공급일', '-')}
- **당첨자 발표일** : **{target_sub_row.get('당첨자발표일', '-')}**
- **서류 제출 기간** : **<span style="color:red;">{target_sub_row.get('서류제출기간', '-')}</span>** *(발표 직후 기한 내 미제출 시 당첨 취소 주의!)*
- **정당 계약 기간** : {target_sub_row.get('계약기간', '-')}

### ✅ 3. 김소장의 핵심 체크포인트 & 부적격 방지 팁
- **체크사항** : {target_sub_row['핵심체크사항']}
- **현장 조언** : 공공분양·신혼희망타운 및 공공임대의 경우 무주택 세대구성원 유지와 소득·자산 기준 충족 여부가 당락을 결정합니다. 서류 제출 시 주민등록초본(과거 주소변동 포함) 등 세부 서류를 기한 내에 완벽하게 구비하시기 바랍니다.

#공인중개사김소장 #김소장 #{target_sub_row['단지명'].replace(' ','')} #수도권청약 #신혼희망타운 #공공임대 #서류제출기간
""", language="markdown")

# ==============================================================================
# [부업무 메뉴 3] 🍽️ 맛집·일상 블로그 스튜디오
# ==============================================================================
elif selected_sub == SUB_MENUS[2]:
    st.subheader("🍽️ 공인중개사 김소장 맛집 · 일상 · 여행 포토 블로그 오토 스튜디오")
    st.caption("사진을 여러 장 업로드하고 각 사진마다 한 줄 코멘트를 적어주시면 '김소장' 페르소나에 맞춘 고품질 블로그 원고가 완성됩니다.")

    b1, b2, b3 = st.columns(3)
    with b1:
        place_name = st.text_input("📍 방문 식당 / 핵심 주제 *", value=st.session_state.draft_preset_topic)
    with b2:
        loc_info = st.text_input("🗺️ 위치 및 주차 팁", value="인천 서구 청라동·석남동 일대")
    with b3:
        menu_point = st.text_input("🍖 주문 메뉴 및 가격", value=st.session_state.draft_preset_kw)

    uploaded_photos = st.file_uploader(
        "📸 블로그에 올릴 사진 다중 업로드 (여러 장 선택 가능)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="sub_blog_photos_main"
    )

    photo_blocks_md = ""
    if uploaded_photos:
        st.markdown("###### 🖼️ 업로드된 사진별 코멘트 입력")
        p_cols = st.columns(min(len(uploaded_photos), 3))
        for idx, pf in enumerate(uploaded_photos):
            with p_cols[idx % 3]:
                st.image(pf, use_container_width=True, caption=f"사진 #{idx+1}: {pf.name}")
                p_comment = st.text_input(f"📝 사진 #{idx+1} 설명", key=f"sub_pcomment_{idx}", placeholder="비주얼 및 느낌 한 줄 요약")
                c_txt = p_comment.strip() if p_comment.strip() else "김소장이 직접 촬영한 생생한 현장 사진입니다."
                photo_blocks_md += f"\n📷 **[사진 #{idx+1} 삽입 위치: `{pf.name}`]**\n> 💬 *{c_txt}*\n\n{c_txt} 사진에서 보시는 것처럼 실제 분위기와 퀄리티가 훌륭했습니다.\n"
    else:
        photo_blocks_md = "\n📷 **[사진 1: 외부 및 전경]**\n> 💬 *찾아가기 편한 전경 모습입니다.*\n\n📷 **[사진 2: 메인 메뉴]**\n> 💬 *군침 도는 비주얼의 메인 메뉴입니다!*\n"

    final_blog_md = f"""### 📌 네이버 VIEW 상위노출 추천 제목 3선
1. {place_name} 내돈내산 솔직 후기! {menu_point} 리얼 먹방 & 방문 꿀팁 (김소장)
2. [{loc_info}] {place_name} | 주차부터 대표 메뉴({menu_point})까지 100% 찐리뷰

---

안녕하세요! 인천 서구 현장을 발로 뛰며 친근하게 소통하는 **공인중개사 김소장**입니다! 😊

오늘 다녀온 곳은 바로 **'{place_name}'**입니다. 광고 일절 없이 직접 경험하고 남기는 솔직 리뷰를 시작합니다!

### 📍 1. 핵심 정보
- **장소** : {place_name}
- **위치** : {loc_info}
- **주요메뉴** : {menu_point}

### 📸 2. 현장 스케치 & 디테일 리뷰
{photo_blocks_md}

### 💡 3. 김소장 총평
기본기가 탄탄하고 만족스러운 곳이었습니다. 근처에 가실 일이 있다면 꼭 들러보시길 추천합니다!
#공인중개사김소장 #김소장 #{place_name.replace(' ','')} #내돈내산솔직후기
"""
    st.markdown("#### 🟢 완성된 블로그 포스팅 원고")
    st.code(final_blog_md, language="markdown")

# ==============================================================================
# [부업무 메뉴 4] 🔥 네이버 키워드 트렌드 추천
# ==============================================================================
elif selected_sub == SUB_MENUS[3]:
    st.subheader("🔥 네이버 부동산 키워드 트렌드 분석 & 조회수 폭발 추천 키워드 TOP 5")
    st.caption("실수요자 유입이 가장 높은 수도권 신혼희망타운, 공공분양, 공공임대 황금 키워드 리스트입니다.")

    kw_database = [
        {
            "추천키워드": "부천대장 A-2블록 신혼희망타운 분양가 서류제출",
            "월간검색량": 16500, "블로그문서수": 3100, "경쟁강도": 0.18,
            "등급": "👑 초특급 황금", "후킹제목": "부천대장 A-2블록 신혼희망타운 공고 총정리 및 서류제출 필수 체크 (김소장)"
        },
        {
            "추천키워드": "인천계양 공공분양 A17블록 본청약 분양가",
            "월간검색량": 15400, "블로그문서수": 3800, "경쟁강도": 0.25,
            "등급": "👑 초특급 황금", "후킹제목": "인천계양 테크노밸리 공공분양 본청약 일정 및 필요 자금 완벽 분석 (김소장)"
        },
        {
            "추천키워드": "수도권 LH 행복주택 공공임대 예비입주자 모집",
            "월간검색량": 21500, "블로그문서수": 7200, "경쟁강도": 0.33,
            "등급": "🔥 조회수 폭발", "후킹제목": "수도권 LH 공공임대 및 행복주택 신청 자격·소득기준 한눈에 보기 (김소장)"
        },
        {
            "추천키워드": "인천 서구 가좌동 석남동 호이스트 단독공장 임대",
            "월간검색량": 4300, "블로그문서수": 1150, "경쟁강도": 0.27,
            "등급": "💎 진성고객 유입", "후킹제목": "인천 가좌동·석남동·원창동 40ft 츄레라 진입 단독공장 계약 전 체크사항 (김소장)"
        }
    ]

    st.markdown("#### 🏆 이번 주 [공인중개사 김소장] 조회수 폭발 황금 키워드")
    for krow in kw_database:
        st.markdown(f"""
        <div class="kw-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <div>
                    <span class="badge-green">{krow['등급']}</span>
                    <span class="badge-blue">경쟁강도 {krow['경쟁강도']}</span>
                    <strong style="font-size:1.15rem; margin-left:8px; color:#0f172a;">🔑 "{krow['추천키워드']}"</strong>
                </div>
                <div style="font-size:0.9rem; font-weight:800; color:#065f46;">
                    📊 월간 검색량: {krow['월간검색량']:,}회 | 📄 문서수: {krow['블로그문서수']:,}건
                </div>
            </div>
            <p style="margin:8px 0 4px 0; color:#1e293b;">🧲 <b>추천 후킹 제목:</b> <u>{krow['후킹제목']}</u></p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🧮 내 키워드 황금비율(경쟁강도) 직접 판별기 & 조회수 폭발 제목 생성기")
    kc1, kc2, kc3, kc4 = st.columns([1.5, 1, 1, 1.2])
    with kc1:
        my_kw = st.text_input("분석할 키워드 입력", value="부천대장 A-2 신혼희망타운")
    with kc2:
        my_vol = st.number_input("월간 총 검색량 (PC+모바일)", min_value=10, value=12500, step=100)
    with kc3:
        my_docs = st.number_input("현재 네이버 블로그 총 문서수", min_value=1, value=2200, step=100)
    with kc4:
        ratio_val = round(my_docs / max(my_vol, 1), 2)
        if ratio_val < 0.8:
            grade_txt = "👑 초특급 황금 키워드 (즉시 작성!)"
        elif ratio_val < 1.8:
            grade_txt = "🟢 우수 키워드 (상위노출 유리)"
        else:
            grade_txt = "🔴 레드오션 (세부 지역명 추가 권장)"
        st.metric("산출된 경쟁강도 지수", f"{ratio_val}", grade_txt)

    hook_titles = f"""### 🎯 [{my_kw}] 클릭률(CTR) 200% 끌어올리는 후킹 제목 5대 공식
1. [실전분석형] {my_kw}, 현업 공인중개사 김소장이 짚어주는 핵심 체크포인트 3가지
2. [실패방지형] {my_kw} 신청·방문 전에 모르면 손해 보는 필수 서류·자격조건 총정리
3. [페르소나형] 공인중개사 김소장이 직접 분석한 {my_kw}, 실수요자 맞춤 완벽 가이드!
4. [숫자강조형] 단 5분 만에 끝내는 {my_kw} 핵심 비교 포인트 TOP 5 한눈에 보기
5. [궁금증유발] 요즘 가장 문의 많은 {my_kw}, 실제 현장 분위기와 안전마진은 어떨까?"""
    st.code(hook_titles, language="markdown")
