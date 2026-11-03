import streamlit as st
import pandas as pd
import datetime
import json
import os
import urllib.parse

# ==========================================
# 0. 페이지 기본 설정 및 부업무 전용 UI 스타일링 (Agent B)
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
# 1. 상수 및 부업무 전용 로컬 DB 초기화 (Agent A)
# ==========================================
ADMIN_PW = "563011"
SUB_CACHE_FILE = "local_backup_cache_sub.json"

SUB_MENUS = [
    "⚖️ 1. 인천공장·창고 & 수도권아파트 법원 경매 분석기",
    "📅 2. 수도권 아파트 분양 & 공공임대 청약 캘린더 알림",
    "🍽️ 3. 김소장 & 청라어니스트아재 맛집·일상 블로그 스튜디오",
    "🔥 4. 네이버 키워드 트렌드 & 조회수 폭발 TOP 5 추천 에이전트"
]

DEFAULT_AUCTIONS = [
    {
        "사건번호": "2025타경 51204",
        "관할법원": "인천지방법원 본원 경매4계",
        "물건종류": "공장 (일반철골조)",
        "소재지": "인천광역시 서구 석남동 223-XX (일반공업지역)",
        "토지_건물면적": "토지 310평 / 건물 245평 (1층 180평, 2층 사무실 65평)",
        "감정가": 245000,
        "최저입찰가": 120050,
        "유찰상태": "49% (2회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
        "기계기구_설비": "호이스트 5톤 2기, 수전설비 250kW, 층고 8.5m (일괄매각)",
        "권리분석핵심": "선순위 근저당 말소기준권리 이후 임차인 없음 (인도명령 대상, 권리관계 깨끗함)",
        "예상낙찰가율": "62~66%"
    },
    {
        "사건번호": "2025타경 60889",
        "관할법원": "인천지방법원 본원 경매7계",
        "물건종류": "공장 (대형 제조형)",
        "소재지": "인천광역시 서구 가좌동 482-XX (일반공업지역)",
        "토지_건물면적": "전용 115평 (지상 1층 5톤 화물차 도어투도어 진입)",
        "감정가": 138000,
        "최저입찰가": 96600,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=19)).strftime("%Y-%m-%d"),
        "기계기구_설비": "층고 7m, 호이스트 2.8톤 1기, 바닥 에폭시 하드너 완비",
        "권리분석핵심": "대항력 없는 후순위 사업자 임차인 점유 중 (보증금 배당으로 명도 저항 낮음)",
        "예상낙찰가율": "75~78%"
    },
    {
        "사건번호": "2025타경 33910",
        "관할법원": "인천지방법원 본원 경매2계",
        "물건종류": "창고 및 공장용지",
        "소재지": "인천광역시 서구 원창동 381-XX (북항배후단지)",
        "토지_건물면적": "토지 450평 / 건물 1층 220평 (40ft 츄레라 진입 수월)",
        "감정가": 320000,
        "최저입찰가": 224000,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=26)).strftime("%Y-%m-%d"),
        "기계기구_설비": "동력 100kW, 대형 단독 마당 사용, 층고 9m",
        "권리분석핵심": "채무자(소유자) 직접 점유 중. 유치권 신고 없으며 공과금 체납만 현장 확인 요망",
        "예상낙찰가율": "78~82%"
    },
    {
        "사건번호": "2025타경 77412",
        "관할법원": "인천지방법원 본원 경매11계",
        "물건종류": "수도권 아파트",
        "소재지": "인천광역시 서구 청라동 청라국제도시 역세권 대장주 84㎡",
        "토지_건물면적": "전용 25.7평 (34평형, 로얄동 18층)",
        "감정가": 89000,
        "최저입찰가": 62300,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=17)).strftime("%Y-%m-%d"),
        "기계기구_설비": "7호선 연장 역세권, 초품아 단지, 커낼웨이 조망",
        "권리분석핵심": "소유자 가족 거주 중, 등기부상 인수 권리 전혀 없음 (실거주 및 투자 급매 대비 메리트 높음)",
        "예상낙찰가율": "84~88%"
    },
    {
        "사건번호": "2025타경 30918",
        "관할법원": "인천지방법원 부천지원 경매3계",
        "물건종류": "수도권 아파트",
        "소재지": "경기도 부천시 소사구 역곡동 역곡역세권 브랜드 대단지 84㎡",
        "토지_건물면적": "전용 25.7평 (34평형, 남향 중층)",
        "감정가": 76000,
        "최저입찰가": 53200,
        "유찰상태": "70% (1회 유찰)",
        "매각기일": (datetime.date.today() + datetime.timedelta(days=9)).strftime("%Y-%m-%d"),
        "기계기구_설비": "1호선 역곡역 도보권, 시장·초중고 인접, 신혼부부 선호도 최상",
        "권리분석핵심": "선순위 임차인 없음 (말소기준권리 이후 전입), 명도 수월 및 주담대 한도 양호",
        "예상낙찰가율": "85~89%"
    }
]

DEFAULT_SUBSCRIPTIONS = [
    {
        "분류": "공공분양 / 신혼희망타운",
        "단지명": "부천대장 A5·A6블록 (e편한세상 대장 퍼스티움)",
        "지역": "경기도 부천시 대장신도시",
        "공급규모": "총 1,099세대 (전용 46㎡ · 55㎡)",
        "마감_주요일자": (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
        "분양가_임대조건": "추정분양가 4억 후반~5억 초반 (분양가상한제)",
        "핵심체크사항": "신혼부부·예비신혼부부 특화, 연 1.3% 고정금리 수익공유형 모기지 최대 4억(70%) 지원"
    },
    {
        "분류": "공공분양 / 뉴홈 나눔형",
        "단지명": "인천계양 테크노밸리 A17블록 공공분양/신희타",
        "지역": "인천광역시 계양구 동양동·박촌동 일원",
        "공급규모": "총 747세대 (전용 55㎡ · 59㎡ · 74㎡)",
        "마감_주요일자": (datetime.date.today() + datetime.timedelta(days=25)).strftime("%Y-%m-%d"),
        "분양가_임대조건": "추정분양가 4억 중후반 (시세 70% 수준 공급)",
        "핵심체크사항": "3기 신도시 핵심 입지, 무주택 세대구성원 및 인천시 거주자 우선공급 배점 사전 점검"
    },
    {
        "분류": "민영분양 (분양가상한제)",
        "단지명": "인천 검단신도시 AA29블록 대방 엘리움 / 푸르지오 권역",
        "지역": "인천광역시 서구 검단신도시",
        "공급규모": "총 884세대 (전용 84㎡ · 101㎡)",
        "마감_주요일자": (datetime.date.today() + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
        "분양가_임대조건": "전용 84㎡ 기준 약 5억 6,000만원",
        "핵심체크사항": "인천 1호선 연장 역세권, 실거주의무 확인 및 전매제한 3년, 청약통장 1순위 가점/추첨 병행"
    },
    {
        "분류": "수도권 공공임대 (통합공공임대/행복주택)",
        "단지명": "인천서구(청라·검단) 및 부천권역 LH 행복주택·통합공공임대 예비입주자 모집",
        "지역": "인천 서구 / 경기 부천시 역세권 블록",
        "공급규모": "청년 · 신혼부부 · 일반 무주택 세대구성원 계층별 공급",
        "마감_주요일자": (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
        "분양가_임대조건": "주변 시세의 60~80% 수준 (보증금 전환으로 월 임대료 대폭 절감 가능)",
        "핵심체크사항": "무주택 세대구성원 소득(도시근로자 월평균소득 100~120%) 및 총자산·자동차 가액 기준 필수 확인"
    },
    {
        "분류": "수도권 공공임대 (국민임대 / 10년 공공임대)",
        "단지명": "수도권 서부권(인천 가정·계양·부천 옥길) GH/LH 국민임대 & 분양전환형 공공임대",
        "지역": "인천 서구 가정동 / 경기 부천시 옥길지구",
        "공급규모": "전용 36㎡ · 46㎡ · 59㎡ 정기 모집",
        "마감_주요일자": (datetime.date.today() + datetime.timedelta(days=31)).strftime("%Y-%m-%d"),
        "분양가_임대조건": "보증금 3,500만~6,500만 / 월 임대료 18만~32만원 수준",
        "핵심체크사항": "청약저축 납입인정회차(24회 이상 우대) 및 무주택 기간 배점 관리 필수"
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
    st.session_state.draft_preset_topic = "석남동 원조뼈해장국"
if "draft_preset_cat" not in st.session_state:
    st.session_state.draft_preset_cat = "🍲 인천/청라/석남/부천 내돈내산 맛집 리뷰"
if "draft_preset_kw" not in st.session_state:
    st.session_state.draft_preset_kw = "뼈해장국 특 11,000원, 감자탕 중 35,000원"

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

# ==========================================
# 2. 왼쪽 사이드바: 보안 잠금 & 4대 부업무 스튜디오 메뉴
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
    st.markdown("### ⚡ 빠른 데이터 관리")
    if st.button("🔄 기본 추천 경매/청약 데이터로 초기화", use_container_width=True):
        st.session_state.sub_db = {"auctions": DEFAULT_AUCTIONS, "subscriptions": DEFAULT_SUBSCRIPTIONS}
        save_sub_db(st.session_state.sub_db)
        st.toast("부업무 기본 데이터 복원 완료!", icon="✅")
        st.rerun()

    st.divider()
    st.markdown("#### 💡 2개 프로그램 동시 실행 팁")
    st.info(
        "• **주업무 CRM (`app.py`):**\n`http://localhost:8501`\n\n"
        "• **부업무 센터 (`sub_app.py`):**\n`http://localhost:8502`"
    )

# ==========================================
# 3. 상단 공통 헤더 및 4대 부업무 KPI 요약 바
# ==========================================
st.markdown(f"""
<div class="sub-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <h2 style="margin:0; color:white;">{selected_sub}</h2>
            <p style="margin:4px 0 0 0; opacity:0.9; font-size:0.9rem;">
                김태형 대표 (김소장 · 청라 어니스트 아재) | 투자 분석 · 청약/공공임대 트래커 · 블로그 상위노출 마케팅 센터
            </p>
        </div>
        <div style="background:rgba(255,255,255,0.18); padding:6px 14px; border-radius:8px; font-weight:800; font-size:0.88rem;">
            🟢 독립형 부업무 엔진 가동중 (sub_app.py)
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
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">⚖️ 추적 중인 법원 경매 물건</div><div class="kpi-val">{len(auc_list)}건 <span style="font-size:0.82rem;color:#059669;">(공장 {fac_auc_cnt} · 아파트 {apt_auc_cnt})</span></div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📅 수도권 아파트·공공임대 일정</div><div class="kpi-val" style="color:#2563eb;">{len(sub_list)}건 <span style="font-size:0.82rem;color:#475569;">(D-Day 실시간 추적)</span></div></div>', unsafe_allow_html=True)
with k3:
    st.markdown('<div class="kpi-card"><div class="kpi-title">✍️ 블로그 페르소나 프리셋</div><div class="kpi-val" style="color:#7c3aed;">2종 <span style="font-size:0.82rem;color:#475569;">(김소장 / 청라어니스트아재)</span></div></div>', unsafe_allow_html=True)
with k4:
    st.markdown('<div class="kpi-card"><div class="kpi-title">🔥 이번 주 황금 키워드 추천</div><div class="kpi-val" style="color:#dc2626;">TOP 5 <span style="font-size:0.82rem;color:#475569;">(시즌 트렌드 반영)</span></div></div>', unsafe_allow_html=True)

st.write("")

# ==============================================================================
# [부업무 메뉴 1] ⚖️ 인천공장·창고 & 수도권아파트 법원 경매 분석기
# ==============================================================================
if selected_sub == SUB_MENUS[0]:
    st.subheader("⚖️ 인천지방법원·부천지원 관할 공장·창고 및 수도권 핵심 아파트 경매 트래커")
    st.caption("사건별 감정가 대비 최저입찰가율, 호이스트·수전설비 일괄매각 여부, 선순위 권리분석 및 경락잔금대출(80%) 실투자금을 즉시 계산합니다.")

    ac1, ac2 = st.columns([1.6, 1])
    with ac1:
        auc_filter = st.radio("🔍 경매 물건 구분 필터", ["전체 경매물건 보기", "🏭 인천 공장·창고 경매만", "🏢 수도권 아파트 경매만"], horizontal=True)
    with ac2:
        bid_deposit_rate = st.slider("입찰보증금 비율 설정 (%)", min_value=10, max_value=20, value=10, step=5)

    auc_df = pd.DataFrame(auc_list)
    if not auc_df.empty:
        if auc_filter == "🏭 인천 공장·창고 경매만":
            view_auc = auc_df[auc_df["물건종류"].str.contains("공장|창고", na=False)]
        elif auc_filter == "🏢 수도권 아파트 경매만":
            view_auc = auc_df[auc_df["물건종류"].str.contains("아파트", na=False)]
        else:
            view_auc = auc_df

        for _, row in view_auc.iterrows():
            min_p = int(float(row.get("최저입찰가", 0)))
            app_p = int(float(row.get("감정가", 1)))
            bid_bond = int(min_p * (bid_deposit_rate / 100.0))
            is_apt = "아파트" in str(row.get("물건종류", ""))
            ltv_default = 0.70 if is_apt else 0.80
            loan_est = int(min_p * ltv_default)
            real_equity = min_p - loan_est
            dday_txt, _ = calc_dday_str(row.get("매각기일", ""))
            gcal_link = make_gcal_url(
                title=f"[경매입찰] {row['사건번호']} ({row['소재지']})",
                date_str=row.get("매각기일", ""),
                details=f"감정가: {app_p:,}만원 / 최저가: {min_p:,}만원 / 입찰보증금: {bid_bond:,}만원 / 권리분석: {row['권리분석핵심']}",
                location=row.get("관할법원", "")
            )

            st.markdown(f"""
            <div class="card-box">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="badge-blue">{row['관할법원']}</span>
                        <span class="badge-red">{row['유찰상태']}</span>
                        <span class="badge-green">{dday_txt}</span>
                        <strong style="font-size:1.12rem; margin-left:6px;">[{row['사건번호']}] {row['소재지']} ({row['물건종류']})</strong>
                    </div>
                    <div>
                        <strong style="color:#1e40af; margin-right:10px;">📅 매각기일: {row['매각기일']}</strong>
                        <a href="{gcal_link}" target="_blank" style="background:#059669; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.82rem; font-weight:800;">📅 구글캘린더 등록</a>
                    </div>
                </div>
                <hr style="margin:10px 0;">
                <p style="margin:4px 0;">📐 <b>면적구성:</b> {row['토지_건물면적']} | ⚙️ <b>기계기구/핵심설비:</b> {row['기계기구_설비']}</p>
                <p style="margin:4px 0;">💰 <b>감정가:</b> {app_p:,}만원 ➔ <b style="color:#dc2626; font-size:1.05rem;">최저입찰가: {min_p:,}만원</b> (입찰보증금 {bid_deposit_rate}%: <b>{bid_bond:,}만원</b> 수표 준비)</p>
                <p style="margin:4px 0;">🏦 <b>경락잔금대출({int(ltv_default*100)}% 가정):</b> 약 {loan_est:,}만원 가능 | 👉 <b>예상 필요 현금(자기자본): 약 {real_equity:,}만원</b> (취득세·명도비 별도)</p>
                <p style="margin:4px 0; color:#065f46;">🔍 <b>권리분석 핵심:</b> {row['권리분석핵심']} (예상 적정 낙찰가율: <b>{row['예상낙찰가율']}</b>)</p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("➕ 관심 법원 경매 사건 직접 추가 / 표에서 바로 수정하기 (클릭하여 열기)"):
        edited_auc_df = st.data_editor(auc_df, num_rows="dynamic", use_container_width=True, key="sub_auc_editor")
        if st.button("💾 경매 사건 리스트 변경사항 저장", type="primary"):
            st.session_state.sub_db["auctions"] = edited_auc_df.to_dict(orient="records")
            save_sub_db(st.session_state.sub_db)
            st.toast("경매 리스트가 저장되었습니다!", icon="✅")
            st.rerun()

    st.divider()
    st.markdown("### 🧮 경매 목표 낙찰가 & 경락잔금대출 · 세금 · 부가세 환급 정밀 시뮬레이터")
    ca1, ca2, ca3, ca4 = st.columns(4)
    with ca1:
        sim_type = st.selectbox("물건 유형 선택", ["🏭 공장·창고 경매 (취득세 4.6%)", "🏢 수도권 아파트 경매 (취득세 1.1~3.5%)"])
        sim_app = st.number_input("감정가 (만원)", value=245000 if "공장" in sim_type else 76000, step=5000)
        sim_bid = st.number_input("목표 입찰(낙찰)가 (만원)", value=155000 if "공장" in sim_type else 58000, step=2000)
    with ca2:
        sim_loan_pct = st.slider("경락잔금대출 한도 (%)", 40, 85, 80 if "공장" in sim_type else 70)
        sim_rate = st.number_input("대출 금리 (연 %)", value=4.4, step=0.1)
    with ca3:
        default_tax_idx = 0 if "공장" in sim_type else 1
        sim_tax_pct = st.selectbox("적용 취득세율 (%)", [4.6, 1.1, 3.5, 12.4], index=default_tax_idx)
        sim_evict = st.number_input("예상 명도비 / 미납관리비 / 수리비 (만원)", value=1000, step=200)
    with ca4:
        loan_res = int(sim_bid * (sim_loan_pct / 100.0))
        tax_res = int(sim_bid * (sim_tax_pct / 100.0))
        cash_needed = (sim_bid - loan_res) + tax_res + sim_evict
        m_interest = int((loan_res * (sim_rate / 100.0)) / 12)
        bldg_vat = int(sim_bid * 0.35 * 0.10) if "공장" in sim_type else 0
        st.metric("총 필요 자기자본 (취득세·명도비 포함)", f"{cash_needed:,} 만원", f"감정가 대비 낙찰가율 {(sim_bid/max(sim_app,1))*100:.1f}%")
        st.metric("경락잔금대출 & 월 예상 이자", f"{loan_res:,} 만원", f"월 이자 약 {m_interest:,}만원")
        if bldg_vat > 0:
            st.caption(f"💡 공장 건물분 부가세 별도 징수 시 조기환급 예상액: 약 **{bldg_vat:,}만원**")


# ==============================================================================
# [부업무 메뉴 2] 📅 수도권 아파트 분양 & 공공임대 청약 캘린더 알림 (산단 분양 완전 제외)
# ==============================================================================
elif selected_sub == SUB_MENUS[1]:
    st.subheader("📅 수도권 주요 아파트 분양(신희타/공공/민영) 및 공공임대(행복·국민·통합임대) 청약 캘린더")
    st.caption("부천대장, 인천계양, 검단신도시 등 수도권 핵심 아파트 청약과 LH/GH/IH 공공임대 모집 공고 D-Day를 추적하고 내 구글 캘린더와 연동합니다.")

    sub_df = pd.DataFrame(sub_list)
    sc_f1, sc_f2 = st.columns([1.8, 1])
    with sc_f1:
        sub_cat_filter = st.radio(
            "🏠 청약 / 임대 구분 필터",
            ["전체 일정 보기", "💍 공공분양 · 신혼희망타운", "🏢 수도권 민영분양 (분양가상한제 등)", "🔑 수도권 공공임대 (행복·국민·통합임대)"],
            horizontal=True
        )
    with sc_f2:
        kw_sub = st.text_input("단지명 / 지역 검색 (예: 부천대장, 계양, 청라)", "")

    view_sub = sub_df.copy()
    if not view_sub.empty:
        if "신혼희망타운" in sub_cat_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("공공분양|신혼희망타운|뉴홈", na=False)]
        elif "민영분양" in sub_cat_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("민영", na=False)]
        elif "공공임대" in sub_cat_filter:
            view_sub = view_sub[view_sub["분류"].str.contains("공공임대|행복주택|국민임대", na=False)]

        if kw_sub.strip():
            k_low = kw_sub.strip().lower()
            view_sub = view_sub[view_sub.apply(lambda r: k_low in " ".join(r.astype(str)).lower(), axis=1)]

        for _, srow in view_sub.iterrows():
            dday_str, _ = calc_dday_str(srow.get("마감_주요일자", ""))
            gcal_sub_url = make_gcal_url(
                title=f"[청약/임대] {srow['단지명']}",
                date_str=srow.get("마감_주요일자", ""),
                details=f"구분: {srow['분류']} | 조건: {srow['분양가_임대조건']} | 체크: {srow['핵심체크사항']}",
                location=srow.get("지역", "")
            )
            badge_cls = "badge-purple" if "임대" in srow["분류"] else "badge-blue"
            st.markdown(f"""
            <div class="card-box">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="{badge_cls}">{srow['분류']}</span>
                        <span class="badge-green">{dday_str}</span>
                        <strong style="font-size:1.1rem; margin-left:6px;">{srow['단지명']} ({srow['지역']})</strong>
                    </div>
                    <div>
                        <strong style="color:#dc2626; margin-right:10px;">⏰ 청약/서류 일정: {srow['마감_주요일자']}</strong>
                        <a href="{gcal_sub_url}" target="_blank" style="background:#2563eb; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.82rem; font-weight:800;">📅 구글캘린더 알림 등록</a>
                    </div>
                </div>
                <hr style="margin:8px 0;">
                <p style="margin:4px 0;">🏠 <b>공급규모:</b> {srow['공급규모']} | 💰 <b>분양가 / 임대조건:</b> <b style="color:#0f172a;">{srow['분양가_임대조건']}</b></p>
                <p style="margin:4px 0; color:#1e40af;">✅ <b>필수 체크포인트:</b> {srow['핵심체크사항']}</p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("➕ 신규 아파트 청약 / 수도권 공공임대 공고 일정 직접 추가·수정하기"):
        edited_sub_df = st.data_editor(sub_df, num_rows="dynamic", use_container_width=True, key="sub_cal_editor")
        if st.button("💾 청약/공공임대 캘린더 저장", type="primary"):
            st.session_state.sub_db["subscriptions"] = edited_sub_df.to_dict(orient="records")
            save_sub_db(st.session_state.sub_db)
            st.toast("청약 및 공공임대 캘린더가 업데이트되었습니다!", icon="✅")
            st.rerun()

    st.divider()
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        st.markdown("#### 💍 신혼희망타운 / 뉴홈 전용 모기지 대출 & 자금 계산기")
        sh_price = st.number_input("예상 분양가 (만원)", value=48000, step=1000)
        sh_ltv = st.slider("전용 모기지 대출 비율 (최대 70%, 4억 한도)", 30, 70, 70)
        sh_rate = st.number_input("고정 금리 (연 %, 신희타 1.3% / 나눔형 1.9~3.0%)", value=1.3, step=0.1)
        sh_loan = min(int(sh_price * (sh_ltv / 100.0)), 40000)
        sh_self = sh_price - sh_loan
        sh_monthly_int = int((sh_loan * (sh_rate / 100.0)) / 12)
        st.success(
            f"💰 **총 필요 자기자본:** **{sh_self:,}만원** (계약금 10% 약 `{int(sh_price*0.1):,}만원`)\n\n"
            f"🏦 **전용 모기지 대출액:** **{sh_loan:,}만원** (연 {sh_rate}%) ➔ **월 이자 약 `{sh_monthly_int:,}만원`**"
        )

    with col_sub2:
        st.markdown("#### 🧮 민영주택 청약 가점 (84점 만점) & 공공임대 보증금 전환 계산기")
        calc_tab1, calc_tab2 = st.tabs(["📊 민영 청약 가점 계산 (84점)", "🔑 공공임대 보증금 증액(월세 절감) 계산"])
        with calc_tab1:
            homeless_yrs = st.number_input("무주택 기간 (년, 만 30세 이후 또는 혼인신고일 기준)", 0, 15, 2)
            dependents = st.number_input("부양가족 수 (본인 제외, 배우자·직계존비속)", 0, 6, 1)
            bank_yrs = st.number_input("청약통장 가입기간 (년)", 0, 15, 6)
            p_homeless = min(homeless_yrs * 2 + 2, 32) if homeless_yrs > 0 else 0
            p_dep = min((dependents + 1) * 5, 35)
            p_bank = min(bank_yrs + 2, 17)
            total_score = p_homeless + p_dep + p_bank
            st.info(f"📌 **나의 청약 가점 총점:** **{total_score}점** / 84점 만점 (무주택 {p_homeless}점 + 부양가족 {p_dep}점 + 통장 {p_bank}점)")
        with calc_tab2:
            base_dep = st.number_input("기본 임대보증금 (만원)", value=4500, step=500)
            base_rent = st.number_input("기본 월 임대료 (만원)", value=26, step=2)
            add_dep = st.number_input("추가 납부할 전환보증금 (만원)", value=2000, step=500)
            conv_rate = st.number_input("전환이율 (연 %, LH/GH 통상 6~7%)", value=6.5, step=0.5)
            rent_cut = round((add_dep * (conv_rate / 100.0)) / 12, 1)
            final_rent = max(round(base_rent - rent_cut, 1), 0)
            st.info(f"📉 보증금 **{base_dep + add_dep:,}만원**으로 증액 시 ➔ 월 임대료 **{rent_cut}만원 절감**되어 **월 약 `{final_rent}만원`** 납부!")


# ==============================================================================
# [부업무 메뉴 3] 🍽️ 김소장 & 청라 어니스트 아재 맛집·일상 포토 블로그 오토 스튜디오
# ==============================================================================
elif selected_sub == SUB_MENUS[2]:
    st.subheader("🍽️ 김소장 & 청라 어니스트 아재 맛집 · 일상 · 여행 포토 블로그 오토 스튜디오")
    st.caption("직접 찍은 사진들을 업로드하고 사진별 코멘트를 적어주시면, 네이버 스마트블록/VIEW 상위노출 구조에 맞춘 생생한 내돈내산 원고가 자동 완성됩니다.")

    b1, b2, b3 = st.columns(3)
    with b1:
        blog_nick = st.selectbox(
            "👤 블로그 페르소나 선택",
            [
                "청라 어니스트 아재 (솔직담백 내돈내산 리뷰어)",
                "김소장 (인천 서구 현장을 발로 뛰는 친근한 부동산 소장님)"
            ]
        )
        cat_options = [
            "🍲 인천/청라/석남/부천 내돈내산 맛집 리뷰",
            "🚗 주말 여행 · 태안 해루질 · 나들이 기록",
            "🏀 농구(도약/RESUME) · 러닝 · 운동 일상",
            "🏠 수도권 청약 · 공공임대 · 부동산 현장 이야기"
        ]
        default_cat_idx = cat_options.index(st.session_state.draft_preset_cat) if st.session_state.draft_preset_cat in cat_options else 0
        blog_cat = st.selectbox("📂 포스팅 카테고리", cat_options, index=default_cat_idx)
    with b2:
        place_name = st.text_input("📍 방문 식당 / 여행지 / 포스팅 핵심 주제 *", value=st.session_state.draft_preset_topic)
        loc_info = st.text_input("🗺️ 동네 위치 / 주차 / 영업시간 팁", value="인천 서구 청라동·석남동 일대 (주차 가능)")
    with b3:
        menu_point = st.text_input("🍖 주문 메뉴 및 가격 (또는 핵심 키워드) *", value=st.session_state.draft_preset_kw)
        honest_rate = st.select_slider(
            "⭐ 솔직 만족도 총평",
            options=["⭐⭐⭐ 무난함 (한 번쯤 가볼 만한 곳)", "⭐⭐⭐⭐ 맛집인정 (든든하고 만족스러운 곳)", "⭐⭐⭐⭐⭐ 인생맛집/강력추천 (재방문 200%)"],
            value="⭐⭐⭐⭐⭐ 인생맛집/강력추천 (재방문 200%)"
        )

    extra_memo = st.text_area(
        "💬 추가로 넣고 싶은 생생 에피소드 한 줄 (선택)",
        value="현장 일정 마치고 허기진 상태에서 방문했는데 양도 푸짐하고 잡내 하나 없이 깔끔해서 에너지 제대로 충전하고 왔습니다!",
        height=68
    )

    st.markdown("##### 📸 블로그에 올릴 사진 다중 업로드 (사진을 올리면 사진별 1줄 설명 입력칸이 자동 생성됩니다)")
    uploaded_photos = st.file_uploader(
        "JPG / PNG 사진 여러 장을 한꺼번에 선택해 주세요",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="sub_blog_photos"
    )

    photo_blocks_md = ""
    if uploaded_photos:
        st.markdown("###### 🖼️ 업로드된 사진 미리보기 및 사진별 코멘트 매칭")
        p_cols = st.columns(min(len(uploaded_photos), 3))
        for idx, pf in enumerate(uploaded_photos):
            with p_cols[idx % 3]:
                st.image(pf, use_container_width=True, caption=f"사진 #{idx+1}: {pf.name}")
                p_comment = st.text_input(
                    f"📝 사진 #{idx+1} 설명 입력",
                    key=f"sub_pcomment_{idx}",
                    placeholder="예: 보글보글 끓어오르는 뚝배기 클로즈업 비주얼"
                )
                c_txt = p_comment.strip() if p_comment.strip() else "직접 촬영한 생생한 현장 사진입니다."
                photo_blocks_md += (
                    f"\n📷 **[사진 #{idx+1} 삽입 위치: `{pf.name}`]**\n"
                    f"> 💬 *{c_txt}*\n\n"
                    f"{c_txt} 사진에서 보시는 것처럼 실제 비주얼과 현장 분위기가 기대 이상으로 훌륭했습니다.\n"
                )
    else:
        photo_blocks_md = (
            "\n📷 **[사진 1 삽입 위치: 매장 외부 전경 간판 및 주차장 안내 사진]**\n"
            "> 💬 *찾아가기 수월한 외관과 주차 공간 모습입니다.*\n\n"
            "📷 **[사진 2 삽입 위치: 메뉴판 가격표 및 정갈한 기본 밑반찬 세팅 사진]**\n"
            "> 💬 *가성비와 구성이 한눈에 보이는 메뉴판과 기본 상차림입니다.*\n\n"
            "📷 **[사진 3 삽입 위치: 오늘 주문한 메인 메뉴 클로즈업 및 한 입 디테일 샷]**\n"
            "> 💬 *비주얼부터 군침이 도는 오늘의 메인 하이라이트입니다!*\n"
        )

    is_honest_ajae = "청라 어니스트 아재" in blog_nick
    nick_short = "청라 어니스트 아재" if is_honest_ajae else "김소장"
    greeting_line = (
        "안녕하세요. 청라 솔직리뷰어 **청라 어니스트 아재**입니다! 😊"
        if is_honest_ajae
        else "안녕하세요! 인천 서구 현장을 발로 뛰는 친근한 이웃, **김소장**입니다! 😊"
    )

    clean_tag_name = place_name.replace(" ", "")
    final_blog_md = f"""### 📌 네이버 VIEW / 스마트블록 상위노출 추천 제목 3선 (택 1)
1. {place_name} 내돈내산 솔직 후기! {menu_point} 리얼 먹방 & 방문 꿀팁 ({nick_short})
2. [{loc_info.split('(')[0].strip()}] {place_name} | 주차부터 대표 메뉴({menu_point})까지 100% 내돈내산 찐리뷰
3. 실패 없는 {place_name} 방문기! 직접 다녀와 보고 느낀 솔직 장단점 총정리

---

{greeting_line}

바쁜 일상 속에서도 기분 좋은 에너지를 채우기 위해 오늘 다녀온 곳은 바로 **'{place_name}'**입니다.
광고나 협찬 일절 없이, 100% 제 지갑으로 직접 경험하고 남기는 솔직 담백한 리뷰를 지금 바로 시작해 볼게요!

---

### 📍 1. [{place_name}] 핵심 정보 한눈에 보기
* **방문 장소 / 주제** : **{place_name}**
* **위치 및 주차 팁** : {loc_info}
* **주요 메뉴 / 포인트** : **{menu_point}**
* **{nick_short}의 솔직 평점** : {honest_rate}

---

### 📸 2. 사진으로 보는 생생 현장 & 디테일 리뷰
{photo_blocks_md}
---

### 💡 3. 경험 디테일 & {nick_short}의 솔직 총평
이번에 경험한 핵심 포인트는 바로 **{menu_point}**였습니다.
{extra_memo}

* **좋았던 점** : 기본기가 탄탄하고 디테일이 살아있어 처음부터 끝까지 기분 좋게 즐길 수 있었습니다.
* **총평 및 재방문 의사** : 자극적이지 않으면서도 확실한 매력이 있는 곳이라 근처 지나실 일이 있다면 꼭 한 번 들러보시길 추천합니다! 오늘도 기분 좋은 하루 보내세요.

**#{clean_tag_name} #인천서구맛집 #청라맛집 #석남동맛집 #가좌동맛집 #역곡맛집 #내돈내산솔직후기 #김소장 #청라어니스트아재**
"""

    st.markdown("#### 🟢 완성된 네이버 블로그 포스팅 원고 (우측 상단 복사 아이콘 클릭)")
    st.code(final_blog_md, language="markdown")


# ==============================================================================
# [부업무 메뉴 4] 🔥 네이버 키워드 트렌드 & 조회수 폭발 TOP 5 추천 에이전트
# ==============================================================================
elif selected_sub == SUB_MENUS[3]:
    st.subheader("🔥 네이버 주요 키워드 트렌드 분석 & 이번 주 조회수 폭발 추천 키워드 TOP 5")
    st.caption("블로그 지수를 빠르게 높이고 실제 유입(조회수·문의)을 폭발시키는 '월간 검색량 대비 문서수 경쟁강도(황금키워드)' 분석 및 주간 글감 추천 에이전트입니다.")

    season_col1, season_col2 = st.columns([1.4, 1])
    with season_col1:
        target_theme = st.selectbox(
            "🎯 집중 공략할 블로그 카테고리 테마 선택",
            [
                "🌟 전체 통합 (이번 주 조회수 폭발 황금 키워드 TOP 5)",
                "🍲 청라 · 석남동 · 역곡 · 부천 로컬 맛집 & 핫플 (청라 어니스트 아재)",
                "🏠 부천대장 · 인천계양 청약 & 수도권 공공임대 (정보성 유입 폭발)",
                "🏭 인천 서구 공장 · 창고 실매물 & 산업단지 현장 (김소장 본업 유입)",
                "🚗 주말 해루질 · 농구 · 운동 · 라이프스타일 (이웃 소통 & 체류시간 상승)"
            ]
        )
    with season_col2:
        st.info("💡 **황금 키워드 판별 공식:**\n`경쟁강도 = 누적 문서수 ÷ 월간 총검색량`\n👉 경쟁강도가 **1.5 미만**이면 상위노출 확률이 매우 높은 **초특급 황금 키워드**입니다!")

    kw_database = [
        {
            "테마": "맛집",
            "추천키워드": "석남역 점심 해장국 맛집",
            "월간검색량": 4200,
            "블로그문서수": 1850,
            "경쟁강도": 0.44,
            "등급": "👑 초특급 황금",
            "추천카테고리": "🍲 인천/청라/석남/부천 내돈내산 맛집 리뷰",
            "프리셋메뉴": "뼈해장국 특 11,000원, 수육 한 접시",
            "후킹제목": "석남역 직장인들이 줄 서서 먹는 진짜 해장국집, 내돈내산 솔직 후기 (주차·웨이팅 팁)"
        },
        {
            "테마": "맛집",
            "추천키워드": "청라 커낼웨이 데이트 저녁 맛집",
            "월간검색량": 8900,
            "블로그문서수": 6400,
            "경쟁강도": 0.72,
            "등급": "🔥 조회수 폭발",
            "추천카테고리": "🍲 인천/청라/석남/부천 내돈내산 맛집 리뷰",
            "프리셋메뉴": "시그니처 스테이크 & 파스타 세트 (주차 편한 곳)",
            "후킹제목": "청라 어니스트 아재가 직접 가본 커낼웨이 분위기 깡패 맛집, 광고 뺀 100% 내돈내산 리뷰!"
        },
        {
            "테마": "청약/임대",
            "추천키워드": "부천대장 신혼희망타운 본청약 분양가 모기지",
            "월간검색량": 12400,
            "블로그문서수": 3900,
            "경쟁강도": 0.31,
            "등급": "👑 초특급 황금",
            "추천카테고리": "🏠 수도권 청약 · 공공임대 · 부동산 현장 이야기",
            "프리셋메뉴": "전용 55㎡ 추정분양가 및 1.3% 고정금리 대출 한도 총정리",
            "후킹제목": "부천대장 A5·A6 신혼희망타운 본청약 임박! 필요 현금과 1.3% 대출 월 이자 직접 계산해 봤습니다"
        },
        {
            "테마": "청약/임대",
            "추천키워드": "인천 청년 신혼부부 행복주택 통합공공임대 소득기준",
            "월간검색량": 9600,
            "블로그문서수": 4100,
            "경쟁강도": 0.43,
            "등급": "👑 초특급 황금",
            "추천카테고리": "🏠 수도권 청약 · 공공임대 · 부동산 현장 이야기",
            "프리셋메뉴": "무주택 세대구성원 소득·자산 컷 및 보증금 상호전환 계산법",
            "후킹제목": "월세 10만원대로 거주 가능? 수도권 행복주택·통합공공임대 자격조건과 보증금 전환 꿀팁 총정리"
        },
        {
            "테마": "공장/본업",
            "추천키워드": "인천 서구 가좌동 호이스트 단독공장 임대",
            "월간검색량": 3100,
            "블로그문서수": 1200,
            "경쟁강도": 0.39,
            "등급": "💎 진성고객 유입",
            "추천카테고리": "🏠 수도권 청약 · 공공임대 · 부동산 현장 이야기",
            "프리셋메뉴": "전용 120평 / 호이스트 5톤 / 40ft 츄레라 진입 단독공장",
            "후킹제목": "인천 가좌동·석남동 40ft 츄레라 진입 수월한 단독공장 구할 때 반드시 체크해야 할 3가지 (김소장)"
        },
        {
            "테마": "일상/여행",
            "추천키워드": "태안 진산리 해루질 물때표 준비물 펜션",
            "월간검색량": 7500,
            "블로그문서수": 4800,
            "경쟁강도": 0.64,
            "등급": "🔥 조회수 폭발",
            "추천카테고리": "🚗 주말 여행 · 태안 해루질 · 나들이 기록",
            "프리셋메뉴": "태안 해루질 포인트, 조개·꽃게 수확 꿀팁 및 펜션 바비큐",
            "후킹제목": "초보자도 통 가득 채우는 태안 진산리 해루질 리얼 후기! 필수 준비물부터 물때 보는 법까지"
        },
        {
            "테마": "일상/여행",
            "추천키워드": "나이키 사브리나4 EP 발볼러 사이즈 후기",
            "월간검색량": 6200,
            "블로그문서수": 2100,
            "경쟁강도": 0.34,
            "등급": "👑 초특급 황금",
            "추천카테고리": "🏀 농구(도약/RESUME) · 러닝 · 운동 일상",
            "프리셋메뉴": "발볼 넓은 가드 포지션 실착 접지력·쿠셔닝·사이즈 반업 팁",
            "후킹제목": "발볼 넓은 가드가 직접 뛰어본 나이키 사브리나 4 EP 내돈내산 실착 리뷰 (270 vs 275 사이즈 선택법)"
        }
    ]

    kw_df = pd.DataFrame(kw_database)
    if "맛집" in target_theme:
        view_kw = kw_df[kw_df["테마"] == "맛집"]
    elif "청약" in target_theme:
        view_kw = kw_df[kw_df["테마"] == "청약/임대"]
    elif "공장" in target_theme:
        view_kw = kw_df[kw_df["테마"] == "공장/본업"]
    elif "해루질" in target_theme:
        view_kw = kw_df[kw_df["테마"] == "일상/여행"]
    else:
        view_kw = kw_df.sort_values(by="경쟁강도", ascending=True).head(5)

    st.markdown("#### 🏆 이번 주 블로그에 쓰면 조회수가 가장 잘 터질 추천 키워드 리스트")
    for idx, krow in view_kw.iterrows():
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

    st.markdown("##### ⚡ 선택한 황금 키워드로 3번 블로그 스튜디오 원고 즉시 세팅하기")
    pick_kw_col1, pick_kw_col2 = st.columns([2.2, 1])
    with pick_kw_col1:
        sel_kw_str = st.selectbox("👇 바로 글을 작성할 추천 키워드를 선택하세요", view_kw["추천키워드"].tolist())
    with pick_kw_col2:
        st.write("")
        if st.button("🚀 이 키워드로 블로그 원고 세팅", type="primary", use_container_width=True):
            chosen_row = view_kw[view_kw["추천키워드"] == sel_kw_str].iloc[0]
            st.session_state.draft_preset_topic = chosen_row["추천키워드"]
            st.session_state.draft_preset_cat = chosen_row["추천카테고리"]
            st.session_state.draft_preset_kw = chosen_row["프리셋메뉴"]
            st.success(f"✅ '{sel_kw_str}' 키워드가 [🍽️ 3. 맛집·일상 블로그 스튜디오]에 세팅되었습니다! 왼쪽 메뉴에서 3번을 클릭해 보세요.")

    st.divider()
    st.markdown("#### 🧮 내 키워드 황금비율(경쟁강도) 직접 판별기 & 조회수 폭발 제목 생성기")
    kc1, kc2, kc3, kc4 = st.columns([1.5, 1, 1, 1.2])
    with kc1:
        my_kw = st.text_input("분석할 키워드 입력", value="청라 삼겹살 내돈내산 맛집")
    with kc2:
        my_vol = st.number_input("월간 총 검색량 (PC+모바일)", min_value=10, value=3500, step=100)
    with kc3:
        my_docs = st.number_input("현재 네이버 블로그 총 문서수", min_value=1, value=1900, step=100)
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
1. [솔직비교형] {my_kw}, 직접 다녀와 보고 느낀 장단점 3가지 (100% 내돈내산)
2. [실패방지형] {my_kw} 가기 전에 모르면 손해 보는 주차·웨이팅·대표메뉴 꿀팁 총정리
3. [페르소나형] 청라 어니스트 아재(김소장)가 추천하는 {my_kw}, 재방문 의사 200% 찐후기!
4. [숫자강조형] 단돈 1만원대부터 즐기는 {my_kw} TOP 포인트 5가지 한눈에 보기
5. [궁금증유발] 현지인들만 조용히 찾아간다는 {my_kw}, 과연 소문만큼 맛있을까?"""
    st.code(hook_titles, language="markdown")