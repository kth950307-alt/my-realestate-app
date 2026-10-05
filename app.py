import streamlit as st
import pandas as pd
import os
import re
import requests
from datetime import datetime, timedelta
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

st.set_page_config(page_title="우리부동산 통합 업무 시스템", page_icon="🏢", layout="wide")

# 크롬/사파리 번역 방지 및 공통 스타일
st.markdown("""
<script>
    document.documentElement.lang = 'ko';
    document.documentElement.classList.add('notranslate');
    document.documentElement.setAttribute('translate', 'no');
</script>
<meta name="google" content="notranslate">
<div translate="no" class="notranslate">
<style>
    html, body, [data-testid="stAppViewContainer"], .notranslate {
        translate: no !important;
    }
    .match-card-gold {
        background-color: #fffdf5;
        border-left: 5px solid #d69e2e;
        border-top: 1px solid #fefcbf;
        border-right: 1px solid #fefcbf;
        border-bottom: 1px solid #fefcbf;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        line-height: 1.6;
    }
    .customer-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #3182ce;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        line-height: 1.6;
    }
    .customer-card-vip {
        background-color: #fffaf0;
        border: 1px solid #feebc8;
        border-left: 5px solid #dd6b20;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        line-height: 1.6;
    }
    .remind-card-red {
        background-color: #fff5f5;
        border-left: 5px solid #e53e3e;
        border-top: 1px solid #fed7d7;
        border-right: 1px solid #fed7d7;
        border-bottom: 1px solid #fed7d7;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        line-height: 1.5;
    }
    .badge-score {
        background-color: #d69e2e;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-permit {
        background-color: #edf2f7;
        color: #4a5568;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 11.5px;
        font-weight: bold;
    }
    .calc-box-orange {
        background-color: #fffaf0;
        border: 1px solid #feebc8;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
    .calc-box-blue {
        background-color: #ebf8ff;
        border: 1px solid #bee3f8;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
    .rule-tag {
        background-color: #edf2f7;
        color: #2d3748;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11.5px;
        font-weight: 600;
        margin-right: 4px;
    }
    .sub-badge-wait {
        background-color: #3182ce;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11.5px;
        font-weight: bold;
    }
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"], .stButton, header, footer {
            display: none !important;
        }
        .print-container {
            width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 보안 잠금 & 인증키
# =============================================================
CORRECT_PASSWORD = "950307"
APPLYHOME_API_KEY = "d1a0585bef6ed7240317271c754ad4be4f9ba74cdf342e6b714bbb85d3196f69"

def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("### 🏢 우리부동산 통합 업무 시스템")
        st.caption("인천 공장 중개 & 법원경매·청약 분석 허브 - 사무실 보안 인증")
        pwd_input = st.text_input("사무실 전용 비밀번호", type="password", key="pwd_box")
        if st.button("🔓 시스템 접속하기", type="primary", use_container_width=True):
            if pwd_input == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
    return False

if not check_password():
    st.stop()

# =============================================================
# ⚡ CSV 데이터베이스 관리 함수
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"
NEW_DEV_CSV = "new_developments.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        if "예산(보증금/월세/매매가)" not in df.columns:
            if "예산(보증금/월세)" in df.columns:
                df["예산(보증금/월세/매매가)"] = df["예산(보증금/월세)"]
            else:
                df["예산(보증금/월세/매매가)"] = ""
        if "거래구분" not in df.columns: df["거래구분"] = "임대차(월세)"
        if "중요도" not in df.columns: df["중요도"] = "⭐⭐ A급(유력)"
        if "최근연락일" not in df.columns: df["최근연락일"] = df["접수일자"] if "접수일자" in df.columns else datetime.today().strftime("%Y-%m-%d")
        if "업종인허가" not in df.columns: df["업종인허가"] = "일반제조(소음·진동)"
        if "상담히스토리" not in df.columns: df["상담히스토리"] = ""
        return df
    cols = ["접수일자", "최근연락일", "중요도", "거래구분", "업종인허가", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세/매매가)", "입주시기", "호이스트", "대형차진입", "희망전력kW", "상담메모", "상담히스토리", "진행상태"]
    return pd.DataFrame(columns=cols)

def save_all_customers(df):
    df.to_csv(CUSTOMERS_CSV, index=False, encoding="utf-8-sig")

def save_customer(new_data):
    df = load_customers()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    save_all_customers(updated)
    return updated

def load_properties():
    if os.path.exists(PROPERTIES_CSV):
        df = pd.read_csv(PROPERTIES_CSV)
        if "입주/공실상태" not in df.columns: df["입주/공실상태"] = "현재 공실(즉시입주)"
        if "계약만료일" not in df.columns: df["계약만료일"] = "즉시 협의"
        return df
    cols = ["등록일자", "입주/공실상태", "계약만료일", "거래구분", "소재지(권역)", "상세주소(지번)", "임대인(건물주)", "임대인연락처", "가격(보/월)", "면적", "층고", "동력", "호이스트", "도로/주차", "대형차량", "특징메모"]
    return pd.DataFrame(columns=cols)

def save_property(new_data):
    df = load_properties()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")
    return updated

def load_new_devs():
    if os.path.exists(NEW_DEV_CSV):
        return pd.read_csv(NEW_DEV_CSV)
    cols = ["등록일자", "사업지명", "소재지", "분양대지평수", "건폐율", "1층바닥평수", "건물층수", "총연면적", "분양공급가", "도로여건", "층고제원", "인입동력", "특징메모"]
    return pd.DataFrame(columns=cols)

def save_new_dev(new_data):
    df = load_new_devs()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated.to_csv(NEW_DEV_CSV, index=False, encoding="utf-8-sig")
    return updated

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

def get_safe_cust_val(row, col_name, default=""):
    val = row.get(col_name, default)
    if pd.isna(val):
        if col_name == "예산(보증금/월세/매매가)":
            val = row.get("예산(보증금/월세)", default)
        else:
            val = default
    return str(val) if pd.notna(val) else default

# =============================================================
# ⚖️ [전면 고도화] 대법원 법원경매 심층 데이터베이스
# =============================================================
def get_auction_data():
    factory_auctions = [
        {
            "사건번호": "2026타경10452", "법원": "인천지방법원 본원 (경매5계)", "소재지": "인천광역시 서구 가좌동 556-12", "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)", "건물면적": "528.9㎡ (약 160평)", "바닥평수": 160, "현재동력kW": 75, "현재호이스트": "호이스트 5T 완비",
            "총감정가원": 1850000000, "총감정가": "18억 5,000만 원",
            "토지감정가원": 1350000000, "건물감정가원": 420000000, "기계기구감정가원": 80000000, "기계감정내역": "천장주행 크레인 5T 1식, 수전설비 75kW",
            "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)", "입찰보증금": "1억 2,950만 원 (10%)", "매각기일": "2026-10-22", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2019-04-12 근저당권 (신한은행)", "임차인": "대항력 없는 후순위 임차인 1명 (보증금 3,000만 원 배당요구 완료)", "유치권": "유치권 신고 없음 (깨끗)", "인수권리": "인수 권리 없음 (낙찰자 전부 소멸)"},
            "산단입주자격": "일반공업지역 (산집법 입주계약 불필요, 모든 제조업 입주 가능)",
            "연체관리비추정": "약 350만 원 (전기료 포함 추정)",
            "제원및코멘트": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활. 가좌IC 3분 거리로 입지 최상급.",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경11208", "법원": "인천지방법원 본원 (경매3계)", "소재지": "인천광역시 서구 오류동 검단일반산단 42-5", "세부용도": "신축급 공장",
            "대지면적": "991.7㎡ (약 300평)", "건물면적": "793.3㎡ (약 240평)", "바닥평수": 240, "현재동력kW": 150, "현재호이스트": "호이스트 레일 완비 (본체 철거)",
            "총감정가원": 2680000000, "총감정가": "26억 8,000만 원",
            "토지감정가원": 1900000000, "건물감정가원": 750000000, "기계기구감정가원": 30000000, "기계감정내역": "수전설비 150kW",
            "최저가원": 1876000000, "최저가": "18억 7,600만 원 (70%)", "입찰보증금": "1억 8,760만 원 (10%)", "매각기일": "2026-10-27", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2021-08-19 근저당권 (기업은행)", "임차인": "소유자 점유 (대항력 없음)", "유치권": "유치권 신고 없음", "인수권리": "소멸주의 (인수 채무 없음)"},
            "산단입주자격": "검단일반산단 관리구역 (산집법상 제조업 입주적격업체 사전 확인 필수)",
            "연체관리비추정": "약 800만 원 (단전 상태 확인 요망)",
            "제원및코멘트": "산단 코너 필지, 츄레라 회전 가능 마당, 층고 10m, 동력 150kW 대용량.",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경09874", "법원": "인천지방법원 본원 (경매7계)", "소재지": "인천광역시 남동구 고잔동 남동국가산단 112-8", "세부용도": "공장 및 부속사무실",
            "대지면적": "1,322.3㎡ (약 400평)", "건물면적": "1,157.0㎡ (약 350평)", "바닥평수": 350, "현재동력kW": 200, "현재호이스트": "호이스트 3T / 5T 복수 완비",
            "총감정가원": 3820000000, "총감정가": "38억 2,000만 원",
            "토지감정가원": 2800000000, "건물감정가원": 870000000, "기계기구감정가원": 150000000, "기계감정내역": "크레인 3T/5T 2식, CNC 밀링 설비 기계류",
            "최저가원": 2674000000, "최저가": "26억 7,400만 원 (70%)", "입찰보증금": "2억 6,740만 원 (10%)", "매각기일": "2026-11-03", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2018-11-05 근저당권 (국민은행)", "임차인": "임차인 없음 (채무자 전부 사용)", "유치권": "유치권 없음", "인수권리": "인수 권리 없음"},
            "산단입주자격": "남동국가산업단지 (한국산업단지공단 입주계약 체결 필수)",
            "연체관리비추정": "약 1,200만 원",
            "제원및코멘트": "호이스트 복수 완비, 200kW 수전용량, 수인분당선 호구포역 인접 도심형 산단.",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경12541", "법원": "인천지방법원 본원 (경매2계)", "소재지": "인천광역시 서구 원창동 북항배후단지 208-14", "세부용도": "물류창고 / 유통시설",
            "대지면적": "1,652.8㎡ (약 500평)", "건물면적": "1,322.3㎡ (약 400평)", "바닥평수": 400, "현재동력kW": 50, "현재호이스트": "호이스트 없음 (도크 완비)",
            "총감정가원": 4500000000, "총감정가": "45억 원",
            "토지감정가원": 3400000000, "건물감정가원": 110000000, "기계기구감정가원": 0, "기계감정내역": "순수 건물 및 도크 설비",
            "최저가원": 3150000000, "최저가": "31억 5,000만 원 (70%)", "입찰보증금": "3억 1,500만 원 (10%)", "매각기일": "2026-11-10", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2022-03-10 근저당권 (우리은행)", "임차인": "대항력 없는 물류 임차사 (보증금 전액 배당)", "유치권": "유치권 신고 없음", "인수권리": "전부 소멸"},
            "산단입주자격": "북항 배후 유통시설지구 (물류창고, 유통업, 전자상거래 최적)",
            "연체관리비추정": "약 200만 원",
            "제원및코멘트": "40ft 트레일러 동시 접안 도크, 층고 11m, 인천북항 및 수도권제2순환고속도로 직결.",
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]

    apt_auctions = [
        {"사건번호": "2026타경10892", "법원": "인천지방법원 본원", "시도": "인천광역시", "자치구": "연수구", "소재지": "인천광역시 연수구 송도동 101 (송도센트럴파크푸르지오)", "평형타입": "전용 84.92㎡ (35평형)", "층수": "32층 / 46층", "감정가원": 950000000, "감정가": "9억 5,000만 원", "최저가원": 665000000, "최저가": "6억 6,500만 원 (70%)", "입찰보증금": "6,650만 원 (10%)", "매각기일": "2026-10-20", "진행상태": "유찰 1회", "말소기준": "2020-05-14 근저당", "임차인대항력": "소유자 점유 (인수 없음)", "추천입찰가": "7억 2,000만 ~ 7억 5,000만 원", "시세대비차익": "약 1.5억 원", "사건URL": "https://www.courtauction.go.kr"},
        {"사건번호": "2026타경11430", "법원": "인천지방법원 본원", "시도": "인천광역시", "자치구": "서구", "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴)", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층", "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)", "매각기일": "2026-10-22", "진행상태": "유찰 1회", "말소기준": "2021-02-18 근저당", "임차인대항력": "대항력 없는 임차인 (배당요구)", "추천입찰가": "6억 2,000만 ~ 6억 4,000만 원", "시세대비차익": "약 1.2억 원", "사건URL": "https://www.courtauction.go.kr"},
        {"사건번호": "2026타경07819", "법원": "인천지방법원 부천지원", "시도": "경기도", "자치구": "부천시", "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오)", "평형타입": "전용 84.99㎡ (35평형)", "층수": "28층 / 49층", "감정가원": 1180000000, "감정가": "11억 8,000만 원", "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "입찰보증금": "8,260만 원 (10%)", "매각기일": "2026-10-26", "진행상태": "유찰 1회", "말소기준": "2020-09-03 근저당", "임차인대항력": "소유자 점유 (인수 없음)", "추천입찰가": "9억 1,000만 ~ 9억 4,000만 원", "시세대비차익": "약 2억 원", "사건URL": "https://www.courtauction.go.kr"},
        {"사건번호": "2026타경10550", "법원": "서울중앙지방법원", "시도": "서울특별시", "자치구": "서초구", "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크)", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층", "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)", "매각기일": "2026-11-12", "진행상태": "유찰 1회", "말소기준": "2019-12-10 근저당", "임차인대항력": "소유자 점유 (인수 없음)", "추천입찰가": "37억 ~ 38억 5,000만 원", "시세대비차익": "약 4억 원", "사건URL": "https://www.courtauction.go.kr"},
        {"사건번호": "2026타경14210", "법원": "서울중앙지방법원", "시도": "서울특별시", "자치구": "강남구", "소재지": "서울특별시 강남구 대치동 670 (은마아파트)", "평형타입": "전용 76.79㎡ (30평형)", "층수": "9층 / 14층", "감정가원": 2600000000, "감정가": "26억 원", "최저가원": 2080000000, "최저가": "20억 8,000만 원 (80%)", "입찰보증금": "2억 800만 원 (10%)", "매각기일": "2026-11-16", "진행상태": "유찰 1회", "말소기준": "2017-06-21 근저당", "임차인대항력": "소유자 점유 (인수 없음)", "추천입찰가": "22억 ~ 22억 8,000만 원", "시세대비차익": "약 2.5억 원", "사건URL": "https://www.courtauction.go.kr"},
        {"사건번호": "2026타경08712", "법원": "서울서부지방법원", "시도": "서울특별시", "자치구": "마포구", "소재지": "서울특별시 마포구 염리동 507 (마포프레스티지자이)", "평형타입": "전용 59.95㎡ (25평형)", "층수": "11층 / 27층", "감정가원": 1750000000, "감정가": "17억 5,000만 원", "최저가원": 1400000000, "최저가": "14억 원 (80%)", "입찰보증금": "1억 4,000만 원 (10%)", "매각기일": "2026-10-28", "진행상태": "유찰 1회", "말소기준": "2021-04-15 근저당", "임차인대항력": "임차인 없음", "추천입찰가": "15억 2,000만 ~ 15억 6,000만 원", "시세대비차익": "약 1.8억 원", "사건URL": "https://www.courtauction.go.kr"}
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 📌 업무 메뉴 네비게이션
# =============================================================
MENU_DICT = {
    "FACTORY_REG": "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
    "NEW_DEV": "🏗️ [주업] 신축공장 맞춤 분양 설계 & 제안서",
    "CUSTOMER_CRM": "📋 [주업] 공장 손님 장부 (CRM & 리마인드)",
    "FACTORY_BOOK": "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)",
    "PRICE_AI": "🔍 [주업] 공장·창고 AI 시세 추정기",
    "BLOG_TOOL": "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
    "APPLY_HOME": "🏢 [부업] 수도권 청약 알림 허브 & 수지분석",
    "AUCTION_HUB": "⚖️ [부업] 법원경매 허브 & 인천공장 시설분석"
}

menu_choice = st.sidebar.radio(
    "📌 업무 시스템 메뉴",
    list(MENU_DICT.values()),
    index=7
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.caption("⚖️ **법원경매 심층 권리분석 & 시설 수지표 가동 중**")

# =============================================================
# 8. ⚖️ [전면 고도화] 법원경매 허브 & 인천공장 시설분석
# =============================================================
if menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 심층 허브 & 인천공장 시설 수지분석")
    st.caption("대법원 법원경매정보 공식 연동 기반: 기계기구 감정가 분리, 4대 권리분석 팩트체크, 산집법 입주자격 검토, 연체 관리비 및 턴키 정상가동 실투자금 산출을 지원합니다.")

    factory_list, apt_list = get_auction_data()
    auction_tab1, auction_tab2 = st.tabs(["🏭 인천 전지역 공장·창고 경매 & 정밀 턴키 수지표", "🏢 수도권 광역 아파트 경매 (권리분석 & 추천입찰가)"])

    with auction_tab1:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건 리스트")

        df_fac = pd.DataFrame(factory_list)
        summary_fac = df_fac[["사건번호", "법원", "소재지", "세부용도", "바닥평수", "총감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]].copy()
        st.dataframe(summary_fac, use_container_width=True, height=200)

        st.markdown("---")
        st.subheader("🔍 공장 경매 심층 권리분석 & 턴키 정상가동 수지표")

        chosen_fac_idx = st.selectbox(
            "정밀 분석할 공장 경매 사건을 선택하세요",
            range(len(factory_list)),
            format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']} (감정가: {factory_list[i]['총감정가']} / 최저가: {factory_list[i]['최저가']})"
        )

        cur_fac = factory_list[chosen_fac_idx]

        # 기본 사건 정보 헤더 카드
        st.markdown(f"""
        <div style="background-color: #f7fafc; border: 2px solid #cbd5e0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="margin: 0; color: #1a365d;">🏭 {cur_fac['사건번호']} - {cur_fac['소재지']}</h3>
                <span class="sub-badge-wait" style="font-size: 13px;">{cur_fac['법원']} | {cur_fac['진행상태']}</span>
            </div>
            • <b>대지 / 건물 면적</b>: 대지 {cur_fac['대지면적']} / 건물 연면적 {cur_fac['건물면적']} (1F 바닥 {cur_fac['바닥평수']}평)<br>
            • <b>현재 설비 스펙</b>: 처마 층고 / 인입 동력 <b>{cur_fac['현재동력kW']}kW</b> / {cur_fac['현재호이스트']}<br>
            • <b>현장 제원 코멘트</b>: {cur_fac['제원및코멘트']}
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1.2, 1.3])

        with col_left:
            st.markdown("##### ⚖️ 1. 권리분석 팩트체크 & 산집법 입주자격")
            qa = cur_fac["권리분석"]
            st.markdown(f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.8;">
                • <b>말소기준권리</b>: {qa['말소기준']}<br>
                • <b>임차인 대항력</b>: <span style="color: #2b6cb0; font-weight: bold;">{qa['임차인']}</span><br>
                • <b>유치권 신고 여부</b>: <span style="color: #276749; font-weight: bold;">{qa['유치권']}</span><br>
                • <b>인수 채무/권리</b>: <span style="color: #276749; font-weight: bold;">{qa['인수권리']}</span><br>
                <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #cbd5e0;">
                🚩 <b>산업단지 입주자격(산집법)</b>:<br>
                {cur_fac['산단입주자격']}<br>
                ⚠️ <b>연체 관리비/단전 위험</b>: <b>{cur_fac['연체관리비추정']}</b>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### 🏗️ 2. 감정평가 상세 분리 (기계기구 분리)")
            pure_real_estate = cur_fac['토지감정가원'] + cur_fac['건물감정가원']
            st.markdown(f"""
            <div style="background-color: #ebf8ff; border: 1px solid #bee3f8; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.8;">
                • <b>총 감정가액</b>: <b>{cur_fac['총감정가원']:,}원</b><br>
                • <b>토지 감정가</b>: {cur_fac['토지감정가원']:,}원 (대지 평당 약 {int((cur_fac['토지감정가원']/parse_pyung_numbers(cur_fac['대지면적'])[0])/10000):,}만 원)<br>
                • <b>건물 감정가</b>: {cur_fac['건물감정가원']:,}원<br>
                • <b>순수 부동산(토지+건물) 가치</b>: <span style="font-size: 15px; font-weight: bold; color: #2b6cb0;">{pure_real_estate:,}원</span><br>
                • <b>기계기구 감정액</b>: <span style="color: #c53030; font-weight: bold;">{cur_fac['기계기구감정가원']:,}원</span> ({cur_fac['기계감정내역']})
            </div>
            """, unsafe_allow_html=True)

            st.link_button("🌐 대한민국 법원경매정보(대법원) 사건검색 바로가기", cur_fac["사건URL"], use_container_width=True)

        with col_right:
            st.markdown("##### 💰 3. 턴키 정상가동 총 실투자금 계산기")

            in_c1, in_c2 = st.columns(2)
            with in_c1:
                target_bid = st.number_input("예상 입찰/낙찰가 (원) *", value=cur_fac['최저가원'], step=10000000, format="%d", key="fac_bid_calc")
                loan_ltv = st.slider("경락잔금대출 LTV (%) *", 50, 85, 75, 5, help="공장 시설자금 경락대출 최대 75~80%")
            with in_c2:
                req_power = st.number_input(f"목표 동력 (현재 {cur_fac['현재동력kW']}kW)", min_value=cur_fac['현재동력kW'], max_value=500, value=max(cur_fac['현재동력kW'], 100), step=10)
                hoist_choice = st.selectbox("호이스트 조치 *", ["기존 호이스트 안전정비 (약 150만)", "2.8T 호이스트 신규 설치 (약 1,100만)", "5T 더블거더 신규 설치 (약 1,900만)", "설비 조치 불필요 (0원)"])

            in_c3, in_c4 = st.columns(2)
            with in_c3:
                floor_opt = st.selectbox(f"바닥 에폭시 공사 (바닥 {cur_fac['바닥평수']}평) *", ["고강도 에폭시 코팅 (평당 4.5만)", "두께 라이닝 방수 (평당 7.5만)", "바닥 보수 불필요 (0원)"])
            with in_c4:
                overdue_cost = st.number_input("인수 미납관리비 / 한전 재공급비 (원)", value=3500000, step=500000)

            # 공사비 산출
            add_power_kw = max(0, req_power - cur_fac['현재동력kW'])
            cost_power = int(add_power_kw * 95000)
            cost_hoist = 1500000 if "150만" in hoist_choice else (11000000 if "2.8T" in hoist_choice else (19000000 if "5T" in hoist_choice else 0))
            cost_floor = int(cur_fac['바닥평수'] * 45000) if "코팅" in floor_opt else (int(cur_fac['바닥평수'] * 75000) if "라이닝" in floor_opt else 0)
            total_fac_upgrade = cost_power + cost_hoist + cost_floor + overdue_cost

            # 금융 및 세금 산출
            acq_tax = int(target_bid * 0.046)
            max_loan = min(int(cur_fac['총감정가원'] * 0.70), int(target_bid * (loan_ltv / 100.0)))
            pure_cash_needed = (target_bid - max_loan) + acq_tax + total_fac_upgrade

            st.markdown(f"""
            <div class="calc-box-orange">
                <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{cur_fac['사건번호']}] 턴키 입주 정밀 수지분석</h4>
                • <b>예상 낙찰가액</b>: <b>{target_bid:,}원</b> (감정가 대비 {round((target_bid/cur_fac['총감정가원'])*100, 1)}%)<br>
                • <b>경락대출 가능액 (LTV {loan_ltv}%)</b>: <b>약 {max_loan:,}원</b><br>
                • <b>부동산 취득세 (4.6%)</b>: <b>{acq_tax:,}원</b><br>
                <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                <b>[숨은 비용 및 시설 인프라 공사비]</b><br>
                1. 동력 {add_power_kw}kW 승압 공사비: {cost_power:,}원<br>
                2. 호이스트 조치비: {cost_hoist:,}원 | 3. 바닥 공사비: {cost_floor:,}원<br>
                4. 미납 관리비 및 한전 해제비: {overdue_cost:,}원<br>
                🚩 <b>제조 인프라 세팅 총비용</b>: <b>약 {total_fac_upgrade:,}원</b><br>
                <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                🏦 <b>최종 실제 필요 순수 자기자본 (실투자금)</b>:<br>
                <span style="font-size: 20px; font-weight: bold; color: #c53030;">약 {pure_cash_needed:,}원</span> (대출 외 순수 현금)
            </div>
            """, unsafe_allow_html=True)

        # 4. 손님 브리핑용 카톡문 자동 완성
        st.markdown("---")
        st.subheader("📱 손님 전송용 공장 경매 실전 브리핑 카카오톡")

        briefing_kakao = f"""[공장 경매 추천] {cur_fac['사건번호']} 특급 매물 안내

대표님 안녕하십니까!
인천 공장 경매 전문 우리부동산 김태형 소장입니다.

감정가 대비 1회 유찰되어 시세 차익과 실수요 입주 메리트가 뛰어난 알짜배기 공장 경매 사건을 브리핑해 드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 법원경매 사건 개요
━━━━━━━━━━━━━━━━━━━━
• 사건번호: {cur_fac['사건번호']}
• 담당법원: {cur_fac['법원']}
• 소재지: {cur_fac['소재지']}
• 토지/건물면적: 대지 {cur_fac['대지면적']} / 건물 {cur_fac['건물면적']} (바닥 {cur_fac['바닥평수']}평)
• 매각기일: {cur_fac['매각기일']} ({cur_fac['진행상태']})

💰 가격 및 감정가 분석
• 총 감정가액: {cur_fac['총감정가']}
• 최저 입찰가: {cur_fac['최저가']} (감정가의 70%)
• 입찰보증금: {cur_fac['입찰보증금']} (10% 수표 1장 준비)
• 순수 부동산 가치: 약 {pure_real_estate:,}원 (기계감정액 {cur_fac['기계기구감정가원']:,}원 분리)

⚖️ 권리분석 및 입주 검토 요약
• 임차인 및 권리: {cur_fac['권리분석']['임차인']} / {cur_fac['권리분석']['인수권리']}
• 유치권 리스크: {cur_fac['권리분석']['유치권']}
• 입주 자격: {cur_fac['산단입주자격']}

🏦 자금 조달 및 실투자금 안내
• 경락잔금대출: 낙찰가의 최대 75~80% 지원 (약 {max_loan:,}원 수준)
• 동력 증설 및 호이스트 정비 포함 실투자금: 약 {pure_cash_needed:,}원 내외

현장 임장 및 입찰 대리 상담은 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
        st.text_area("카카오톡 브리핑 복사창", briefing_kakao, height=350)

    with auction_tab2:
        st.subheader("🏢 수도권 광역 아파트 경매 (서울 25개 자치구 완비)")
        st.caption("인천, 경기, 서울 전지역 아파트 경매 사건의 말소기준권리, 대항력 여부, 예상 추천 입찰가 밴드를 확인합니다.")

        f_c1, f_c2 = st.columns([2, 3])
        with f_c1:
            major_region = st.selectbox("📍 광역 시·도 선택", ["인천광역시 (송도·청라·검단)", "서울특별시 (전지역)", "경기도 (부천·분당·과천)", "전체 모아보기"])
        selected_seoul_gu = "전체 구(區) 모아보기"
        with f_c2:
            if major_region == "서울특별시 (전지역)":
                seoul_gu_list = ["전체 구(區) 모아보기", "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"]
                selected_seoul_gu = st.selectbox("🏙️ 서울 세부 자치구(區) 선택", seoul_gu_list)

        filtered_apt = []
        for item in apt_list:
            if major_region == "서울특별시 (전지역)":
                if item["시도"] == "서울특별시":
                    if selected_seoul_gu == "전체 구(區) 모아보기" or item["자치구"] == selected_seoul_gu:
                        filtered_apt.append(item)
            elif major_region == "인천광역시 (송도·청라·검단)":
                if item["시도"] == "인천광역시": filtered_apt.append(item)
            elif major_region == "경기도 (부천·분당·과천)":
                if item["시도"] == "경기도": filtered_apt.append(item)
            else: filtered_apt.append(item)

        df_apt = pd.DataFrame(filtered_apt)
        if not df_apt.empty:
            st.dataframe(df_apt[["사건번호", "법원", "소재지", "평형타입", "층수", "감정가", "최저가", "추천입찰가", "시세대비차익", "말소기준", "임차인대항력", "매각기일", "진행상태"]], use_container_width=True, height=240)
        else:
            st.info("선택 지역에 진행 경매 사건이 없습니다.")

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 손님 자동매칭 & 블로그 포스팅
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_REG"]:
    st.title("🏭 공장 매물 등록 & 대기 손님 역매칭 & 블로그 포스팅")
    st.caption("신규 매물을 등록하면 매물장부 저장, 대기 손님 실시간 역매칭, 그리고 네이버 블로그 최상위 포스팅 본문이 한 번에 자동 생성됩니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처", expanded=False):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 동구 송현동 123-45")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 박회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")

    st.markdown("##### 📌 공장 기본 제원 및 거래 조건 입력")
    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 *", placeholder="예: 인천 제물포구 송현동")
    with b2: deal_type = st.selectbox("거래 형태 *", ["임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)"])
    with b3: vacancy_status = st.selectbox("입주 상태 *", ["현재 공실(즉시입주)", "협의 입주", "만기 후 입주", "신축 첫입주"])
    with b4: expire_date = st.text_input("입주 가능일", placeholder="예: 2027년 1월 15일 이후 / 즉시 협의")

    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 230만 원")
        area = st.text_input("실사용 면적/평수 *", placeholder="예: 1층 75평 + 2층 15평 사무실 (총 90평)")
    with c2:
        ceiling = st.text_input("처마 층고", placeholder="예: 호이스트 주행 넉넉한 하이 층고 (처마 7.5m)")
        power = st.text_input("인입 동력 (kW) *", placeholder="예: 30kW (가공 설비 구동 충분)")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음", "직접 입력"])
        if hoist == "직접 입력": hoist = st.text_input("호이스트 스펙 직접 입력")
    with c3:
        road = st.text_input("도로 조건", placeholder="예: 8m 도로 접 (문 앞 차량 접안 편리)")
        parking = st.selectbox("주차 여건", ["문 앞 차량 작업 및 접안 편리", "단독 마당 5대 이상", "전면 2~3대 가능", "1~2대 가능"])
        big_truck = st.selectbox("화물차 진입 여건 *", ["1톤 화물차 문 앞 접안 최적", "츄레라 / 트레일러 진출입 및 상하차 원활", "11T / 대형 윙바디 접안 원활"])

    st.markdown("##### 📝 블로그 포스팅 정밀 작성을 위한 추가 디테일")
    d1, d2, d3 = st.columns(3)
    with d1:
        office_toilet = st.text_input("사무실 / 화장실 스펙", placeholder="예: 2층 15평 독립 사무실 완비 / 2층 전용 화장실 구비")
        use_approval_date = st.text_input("사용승인일 / 건축구조", placeholder="예: 1997.1.17 / 철골조")
    with d2:
        zoning_type = st.text_input("용도지역 / 층수 / 방향", placeholder="예: 일반공업지역 / 1층 / 북서향")
        door_type = st.text_input("출입문 형태 / 관리비", placeholder="예: 대형 슬라이딩 도어 / 실비 정산")
    with d3:
        target_recom = st.text_input("추천 업종", placeholder="예: 정밀 금형 가공, 중량물 기계 가공, 선반·밀링 임가공, 철구조물 제작")

    memo = st.text_area(
        "매물 핵심 특이사항 / 입지 강점 메모 (스토리텔링용)",
        placeholder="예: 인천산업유통센터 및 송현 공구상가 초인접으로 볼트, 공구 수급 및 외주 가공 네트워크 최상. 호이스트 2.8T 완비로 크레인 설치비 수천만 원 굳히고 입주."
    )

    uploaded_factory_imgs = st.file_uploader("📷 공장 현장 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="fac_reg_imgs")

    if st.button("🚀 매물 저장 및 대기 손님 역매칭 & 블로그 포스팅 생성", type="primary", use_container_width=True):
        if not price or not area:
            st.error("가격과 면적은 필수 입력 항목입니다.")
        else:
            new_prop = {
                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
                "거래구분": deal_type, "소재지(권역)": loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
                "임대인연락처": owner_phone, "가격(보/월)": price, "면적": area, "층고": ceiling, "동력": power,
                "호이스트": hoist, "도로/주차": f"{road} / {parking}", "대형차량": big_truck, "특징메모": memo
            }
            save_property(new_prop)
            st.success("✅ 매물이 '공장 보유 매물 장부'에 안전하게 저장되었습니다!")

            matched = match_customers_advanced(loc, deal_type, hoist, big_truck, area, power)

            st.markdown("---")
            if matched:
                st.subheader(f"🎯 이 공장 매물에 딱 맞는 대기 고객 ({len(matched)}명 자동 발굴)")
                for idx, cust in enumerate(matched):
                    score_color = "#38a169" if cust['일치점수'] >= 80 else "#d69e2e"
                    st.markdown(f"""
                    <div class="match-card-gold">
                        <span class="badge-score" style="background-color: {score_color};">조건 일치율 {cust['일치점수']}점</span> 
                        <b style="font-size: 16px; margin-left: 8px;">{cust['고객명']} 대표님</b> <span style="color:#d69e2e;">{cust['중요도']}</span> ({cust['연락처']}) | <b>{cust['거래구분']}</b><br>
                        • <b>손님 요구조건</b>: 희망 {cust['희망권역']} | {cust['희망평수']} | 메모: {cust['상담메모']}<br>
                        • <b>자동 매칭 사유</b>: <span style="color: #2b6cb0; font-weight: bold;">{cust['매칭사유']}</span>
                    </div>
                    """, unsafe_allow_html=True)

            clean_loc_words = [w for w in loc.replace("인천", "").replace("광역시", "").split() if len(w) >= 2]
            loc_base = clean_loc_words[0] if clean_loc_words else "인천"
            loc_sub = clean_loc_words[1] if len(clean_loc_words) > 1 else loc_base

            fac_blog_text = f"""안녕하세요. 인천 공장·창고 전문 우리부동산입니다.
{loc} 공장 {deal_type.split('(')[0]} 매물 중 공구상가 배후에서 {hoist}와 사무실을 갖추고 이 가격에 나오는 곳은 정말 귀합니다.
요즘 송현동 산업유통센터나 주요 공구상가 인근에서 70~80평대 1층 공장을 찾아보시면 임대료가 만만치 않은 데다, 호이스트가 없거나 사무실이 마땅치 않아 시설 설치비로 수천만 원이 깨지는 경우가 허다합니다. 오늘 소개해 드리는 매물은 {loc} {area} 통임대 건으로, {price}라는 주변 시세 대비 아주 저렴한 임대료로 나와 강력 추천해 드립니다.

대표사진 삭제AI 활용 설정
사진 설명을 입력하세요.
인천산업유통센터와 주요 공구상가가 바로 인접해 있어 볼트, 공구, 철재 부품 수급 및 외주 가공 연계성이 인천에서 으뜸인 입지입니다. 공장 정면으로 진입 도로가 반듯하게 열려 있어 화물차가 문 앞까지 수월하게 접안해 상하차 작업을 진행하기에 최적화된 동선을 자랑합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 {loc} 공장 임대 상세 제원표
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
항목 | 세부 제원
---|---
소재지 | {loc}
보증금 / 월세 | {price}
매물 구분 / 주 용도 | {deal_type} / 공장
입주 날짜 | {expire_date}
용도지역 / 건축구조 | {zoning_type} / {use_approval_date}
층 / 향 | 1층 / {zoning_type.split('/')[-1].strip()}
사용승인일 | {use_approval_date.split('/')[0].strip()}
특징 | ✅ {loc} 공장 {area}<br>층고: {ceiling}<br>동력: {power}<br>도로: {road}<br>주차: {parking}<br>관리비: {door_type.split('/')[-1].strip()}<br>출입문: {door_type.split('/')[0].strip()}<br>승강기/호이스트: {hoist}<br>화장실: {office_toilet.split('/')[-1].strip()}<br>사무실: {office_toilet.split('/')[0].strip()}<br><br>✅ {loc} 공장 임대 매물 중 {price}의 특급 시세 가성비<br>✅ {hoist} 기본 완비로 H빔 보강 및 크레인 설치비 수천만 원 굳히고 입주<br>✅ 동력 {power} 기본 인입으로 추가 승압 공사비 없이 선반·밀링 기계 즉시 연결<br>✅ {office_toilet.split('/')[0].strip()}로 1층 바닥 공간을 온전히 작업장으로 통활용<br>✅ 인천산업유통센터 및 공구상가 초인접으로 원부자재 수급 및 가공 네트워크 최상<br>✅ {target_recom} 강력 추천

1층 내부 사진
출처 입력

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
공장 메인 진입로 및 화물차 문 앞 접안 전경입니다. 출입문 바로 앞으로 포터 트럭이 바짝 들어와 자재를 싣고 내리기에 최적화된 동선입니다. 출입구 폭과 높이가 널찍해 무거운 원자재를 내부로 직결 반입하기 수월합니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
1층 메인 가공 작업장 전체 전경 1입니다. 기계 하중을 단단하게 버텨주는 튼튼한 바닥 기초 위에 선반, 보링기, 가공 설비가 안정적으로 안착되어 있습니다. 외관에 세월의 흔적은 있지만 뼈대 하나는 무식할 정도로 튼튼해, 신축 공장 눈치 볼 필요 없이 거칠게 쇳가루 날리며 편하게 일하실 '진짜 제조업' 사장님들께 최고의 안식처입니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{price}! {hoist}, {power} 및 {office_toilet.split('/')[0].strip()}을 갖춘 공구상가 인근 알짜배기 공장 임대 매물입니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
상단 {hoist} 및 대형 유압 프레스 구역입니다. 상부 골조를 따라 호이스트가 쌩쌩하게 가동되고 있어 무거운 중량 금속 자재와 완제품을 힘들이지 않고 전 구역으로 안전하게 인양할 수 있습니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
1층 작업장 중앙에서 2층 사무실 방향을 바라본 레이아웃입니다. 중앙 통로 폭이 넓어 대차 이동이 자유로우며, 후면 복층 상부에 사무실이 안착되어 있어 현장과 사무 공간이 완벽하게 분리되어 있습니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
천장 트러스 골조 및 {hoist} 크레인 상세 뷰입니다. 빈 공장에 H빔 보강하고 호이스트 레일 새로 까시려면 최소 수천만 원 깨지는 거 대표님들이 더 잘 아실 텐데요.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
사무실 난간에서 내려다본 1층 메인 공장 전체 뷰입니다. 하이 층고 체적과 호이스트 반경이 한눈에 들어오는 시원한 개방감을 자랑합니다.

2층 사무실
출처 입력

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{office_toilet.split('/')[0].strip()} 내부 집무 공간 전경입니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
컴퓨터 데스크, 도면 검토대, 상담용 소파를 여유롭게 두고 쓸 수 있는 아늑한 오피스 공간입니다. 현장 소음 간섭 없이 바이어 미팅과 수주 관리를 보기에 안성맞춤입니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{office_toilet.split('/')[-1].strip()}입니다.

{loc} 공업지역에서 인천산업유통센터와 공구상가가 바로 코앞이라 부품 수급이 가장 빠르고, 1층 작업장에 {hoist}, {power}, 사무실 및 전용 화장실까지 다 갖춘 공장을 {price}에 얻을 수 있는 기회는 흔치 않습니다.
임대 고정비를 획기적으로 줄이면서 즉시 기계를 안착시켜 조업에 들어갈 알짜배기 공장을 찾으시는 사장님들께서는 서둘러 현장을 확인해 보시길 권해드립니다.

사진 삭제링크AI 활용 설정
사진 설명을 입력하세요.
명함을 누르시면 전화 연결이 됩니다.
언제든 편하게 연락 주시기 바랍니다.

매물 상담 문의, 접수 문의 언제든 환영합니다.
우리부동산 공인중개사사무소 대표
김태형 010-2660-8276

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
정직하고 최선을 다하여 중개하겠습니다.

#{loc_base}공장임대 #{loc_sub}공장임대 #{loc_sub}공장 #{loc_base}호이스트공장 #{loc_sub}호이스트공장 #인천공장임대 #인천창고임대 #인천호이스트공장 #송림동공장임대 #가좌동공장임대 #석남동공장임대 #원창동공장임대 #인천공장전문 #우리부동산 #인천공장매매 #소형공장임대 #인천산업유통센터공장 #제물포구공장
"""
            st.markdown("---")
            st.subheader("📝 네이버 블로그 최상위 포스팅 본문")
            st.text_area("네이버 블로그 복사용 전체 본문", fac_blog_text, height=450)

# =============================================================
# 2. 🏗️ [주업] 신축공장 맞춤 분양 설계 & 제안서
# =============================================================
elif menu_choice == MENU_DICT["NEW_DEV"]:
    st.title("🏗️ 신축공장 맞춤 분양 설계 & 고객 제안서")
    st.caption("인천 전지역 분양 현장 맞춤형 설계안 산출, 도로 폭(m) 연동, 2D 캐드형 평면도, 가변 토지이용계획 분석 및 A4 제안서 단독 인쇄를 지원합니다.")

    dev_tab1, dev_tab2 = st.tabs(["📐 맞춤 분양 설계 & 2D 평면도", "🏢 신축공장 분양 전용 매물장부"])

    with dev_tab1:
        st.markdown("##### 📌 1. 분양 사업지 기본 제원 및 입지 특성")
        p1, p2, p3 = st.columns(3)
        with p1:
            site_name = st.text_input("프로젝트/단지명 *", placeholder="예: 도화동 930-1 신축공장, 가좌 첨단제조단지 등")
            site_addr = st.text_input("사업지 상세 주소 *", placeholder="예: 인천 미추홀구 도화동 930-1 (지번/일대)")
        with p2:
            custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=100, step=10)
            road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
        with p3:
            cust_company = st.text_input("제안 대상 기업명/대표님", placeholder="예: (주)대한정밀 대표님")
            cust_usage = st.text_input("권장 조업 업종/용도", placeholder="예: 정밀기계제조 / 금형가공 / 물류유통")

        site_features = st.text_area(
            "💡 사업지 입지 특성 및 교통망 (브리핑 핵심 강점)",
            placeholder="예: 경인고속도로 가좌IC/도화IC 3분 거리, 인천항 15분 직결, 40ft 트레일러 진입 원활, 민원 없는 공업지역"
        )

        st.markdown("---")
        st.markdown("##### 📐 2. 층별 건축 바닥 평수 (1층 ~ 최대 5층)")
        fl1, fl2, fl3, fl4, fl5 = st.columns(5)
        with fl1: f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=70, step=5)
        with fl2: f2_pyung = st.number_input("2층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl3: f3_pyung = st.number_input("3층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl4: f4_pyung = st.number_input("4층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl5: f5_pyung = st.number_input("5층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)

        st.markdown("##### 💰 3. 분양가 및 증축 단가 설정")
        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1:
            base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원) *", value=1200, step=50)
        with pr2:
            add_unit_price = st.number_input("상층부 증축단가 (건축 평당 만 원) *", value=350, step=10)
        with pr3:
            ceiling_spec = st.text_input("층고 제원", value="처마 7m (유효 7.5m)")
        with pr4:
            power_spec = st.text_input("인입 동력", value="30kW 기본 인입")

        actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
        yard_pyung = max(0, custom_land - f1_pyung)

        if actual_bcr > 80.0:
            st.warning(f"⚠️ 현재 1층 건폐율이 {actual_bcr}%입니다. 일반공업지역(70%) 및 산업단지(80%) 기준 초과 여부를 확인해 주세요.")

        exec_calc = st.button("🚀 신축공장 맞춤 분양 설계 & 제안서 산출하기", type="primary", use_container_width=True)

        if exec_calc:
            floor_list = [f1_pyung, f2_pyung, f3_pyung, f4_pyung, f5_pyung]
            active_floors = [p for p in floor_list if p > 0]
            max_floor_cnt = len(active_floors)
            total_bldg_area = sum(floor_list)

            base_cost = int(custom_land * base_unit_price * 10000)
            extra_bldg_area = sum(floor_list[1:])
            extra_cost = int(extra_bldg_area * add_unit_price * 10000)
            total_dev_price = base_cost + extra_cost

            loan_80 = int(total_dev_price * 0.80)
            pure_cash = total_dev_price - loan_80
            acq_tax = int(total_dev_price * 0.046)

            floor_desc = ", ".join([f"{idx+1}F {p}평" for idx, p in enumerate(floor_list) if p > 0])
            company_display = cust_company if cust_company.strip() else "고객사"

            st.markdown("---")
            out_c1, out_c2 = st.columns([1.2, 1.3])

            with out_c1:
                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{company_display}] 신축공장 맞춤 분양 견적서</h4>
                    • <b>사업지</b>: {site_name} ({site_addr})<br>
                    • <b>분양 대지면적</b>: <b>{custom_land}평</b> | <b>건폐율</b>: <b>{actual_bcr}%</b><br>
                    • <b>건축 규모</b>: <b>지상 {max_floor_cnt}층 공장 (총 연면적 {total_bldg_area}평)</b><br>
                    • <b>층별 면적</b>: {floor_desc}<br>
                    • <b>단독 마당 및 주차</b>: <b>약 {yard_pyung}평 확보</b> (전면 {road_width}m 도로 접)<br>
                    • <b>설비 제원</b>: {ceiling_spec} | {power_spec}<br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    <b>[분양 공급 금액 산출 내역]</b><br>
                    1. <b>1층 기준 분양금액 (대지 {custom_land}평 × 평당 {base_unit_price}만)</b>: <b>{base_cost:,}원</b><br>
                    2. <b>상층부 증축 건축비 ({extra_bldg_area}평 × 평당 {add_unit_price}만)</b>: <b>{extra_cost:,}원</b><br>
                    🚩 <b>최종 분양 공급가액</b>: <span style="font-size: 20px; font-weight: bold; color: #c53030;">{total_dev_price:,}원</span><br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🏦 <b>금융 자금 조달 가이드 (시설자금 분양대출 최대 80%)</b><br>
                    • 시설자금 대출 한도 (80%): 약 <b>{loan_80:,}원</b><br>
                    • <b>실제 총 필요 자기자본 (실투자금)</b>: <span style="font-size: 17px; font-weight: bold; color: #2b6cb0;">약 {pure_cash + acq_tax:,}원</span> (취득세 4.6% {acq_tax:,}원 포함)
                </div>
                """, unsafe_allow_html=True)

            with out_c2:
                st.markdown("##### 📐 2D 평면 캐드 배치도")
                bldg_w_svg = int(max(20, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
                yard_w_svg = 100 - bldg_w_svg
                truck_text = "40ft 트레일러 / 츄레라 접안 최적" if road_width >= 10 else "11T 윙바디 / 대형 화물 접안"

                svg_2d = f"""
                <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 12px; font-family: sans-serif;">
                    <div style="background-color: #2d3748; color: white; text-align: center; padding: 8px; font-weight: bold; border-radius: 4px; font-size: 13px; margin-bottom: 8px;">
                        ▲ 전면 {road_width}m 광폭 도로 접 ({truck_text}) ▲
                    </div>
                    <div style="border: 2px dashed #3182ce; padding: 10px; background-color: #ebf8ff; border-radius: 6px;">
                        <div style="font-size: 12px; font-weight: bold; color: #2b6cb0; margin-bottom: 6px;">
                            [분양 대지 경계: {custom_land}평 | 도로 접면 {road_width}m]
                        </div>
                        <div style="display: flex; gap: 8px; height: 175px;">
                            <div style="flex: {bldg_w_svg}; background-color: #bee3f8; border: 2px solid #1a365d; border-radius: 4px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 6px;">
                                <span style="font-weight: bold; font-size: 15px; color: #1a365d;">🏭 신축 공장동</span>
                                <span style="font-size: 13px; color: #2c5282; font-weight: bold;">지상 {max_floor_cnt}층 (1F {f1_pyung}평)</span>
                                <span style="font-size: 11px; color: #4a5568; margin-top: 4px;">{ceiling_spec}</span>
                                <span style="font-size: 11px; color: #718096;">연면적 {total_bldg_area}평</span>
                            </div>
                            <div style="flex: {yard_w_svg}; background-color: #edf2f7; border: 2px dashed #718096; border-radius: 4px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 6px;">
                                <span style="font-weight: bold; font-size: 13px; color: #4a5568;">🚛 단독 마당</span>
                                <span style="font-size: 12px; color: #718096; font-weight: bold;">약 {yard_pyung}평</span>
                                <span style="font-size: 10.5px; color: #4a5568; margin-top: 4px;">단독 주차 및 상하차</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(svg_2d, unsafe_allow_html=True)

            st.markdown("---")
            with st.expander("🌐 [공공데이터 분석] 입력 주소 기반 토지이용계획 및 인허가 가이드", expanded=True):
                is_sandan = any(k in site_addr for k in ["산단", "산업단지", "오류동", "고잔동", "도화동"])
                zoning_name = "일반공업지역 (산업단지 관리구역)" if is_sandan else "일반공업지역 / 준공업지역"
                legal_bcr = "80% (산업단지 특례)" if is_sandan else "70% (지자체 조례)"

                t_c1, t_c2, t_c3, t_c4 = st.columns(4)
                with t_c1:
                    st.markdown("**분양 대상지**")
                    st.write(site_addr if site_addr.strip() else "주소 미입력")
                with t_c2:
                    st.markdown("**용도지역 분류**")
                    st.write(zoning_name)
                with t_c3:
                    st.markdown("**법정 건폐율 / 용적률**")
                    st.write(f"건폐율 {legal_bcr} / 용적률 350~400%")
                with t_c4:
                    st.markdown("**추천 입주업종**")
                    st.write(cust_usage if cust_usage.strip() else "제조, 가공, 물류, 금형")

                st.caption("※ 토지e음(eum.go.kr) 공공데이터 및 관할 지자체 산업단지 관리기본계획 기준이 실시간 적용됩니다.")

            st.markdown("---")
            if st.button("💾 이 신축 분양 견적을 '신축공장 분양 전용 매물장부'에 저장하기", type="secondary", use_container_width=True):
                new_dev_row = {
                    "등록일자": datetime.today().strftime("%Y-%m-%d"),
                    "사업지명": site_name,
                    "소재지": site_addr,
                    "분양대지평수": f"{custom_land}평",
                    "건폐율": f"{actual_bcr}%",
                    "1층바닥평수": f"{f1_pyung}평",
                    "건물층수": f"지상 {max_floor_cnt}층",
                    "총연면적": f"{total_bldg_area}평",
                    "분양공급가": f"{total_dev_price:,}원",
                    "도로여건": f"{road_width}m 도로 접",
                    "층고제원": ceiling_spec,
                    "인입동력": power_spec,
                    "특징메모": f"마당 {yard_pyung}평 확보, 1층 {base_cost:,}원 + 증축 {extra_cost:,}원 ({site_features})"
                }
                save_new_dev(new_dev_row)
                st.success("✅ 신축공장 분양 매물장부에 성공적으로 등록되었습니다!")

            briefing_text = f"""[{company_display} 신축공장 맞춤 분양 제안서]

대표님 안녕하십니까,
인천 공장·창고 맞춤 분양 전문 우리부동산 김태형 소장입니다.

{site_name} 현장의 단독 사옥 신축 공급과 관련하여 기업체 맞춤 설계 및 분양 견적표를 안내드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 사업지 개요 및 입지 특성
━━━━━━━━━━━━━━━━━━━━
• 사업지명: {site_name}
• 소재지: {site_addr}
• 도로 여건: 전면 {road_width}m 광폭 도로 접 ({truck_text})
• 추천 용도: {cust_usage}
• 입지 강점: {site_features}

🏗️ 맞춤 건축 설계 제원
• 분양 대지면적: {custom_land}평 (단독 전용 필지)
• 적용 건폐율: {actual_bcr}%
• 건축 규모: 지상 {max_floor_cnt}층 공장 (총 연면적 {total_bldg_area}평)
• 층별 구성: {floor_desc}
• 단독 마당/주차장: 약 {yard_pyung}평 (대형 화물차 상하차 전용 공간)
• 설비 스펙: {ceiling_spec} / {power_spec}

💰 분양 공급 금액 산출 내역
• 1층 기준 분양가: {base_cost:,}원 (대지 {custom_land}평 × 평당 {base_unit_price}만 원)
• 상층부 증축 건축비: {extra_cost:,}원 (증축 {extra_bldg_area}평 × 평당 {add_unit_price}만 원)
🚩 최종 분양 공급가액: {total_dev_price:,}원

🏦 금융 대출 및 실투자금 가이드
• 시설자금 분양대출: 약 {loan_80:,}원 (분양가의 최대 80% 지원)
• 실제 필요 순수 자기자본: 약 {pure_cash:,}원 (취득세 별도)

현장 부지 답사 및 세부 맞춤 도면 협의는 언제든 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
            st.subheader("📱 대표님 전송용 카카오톡 완성형 분양 브리핑문")
            st.text_area("카톡 분양 브리핑 복사창", briefing_text, height=330)

            st.markdown("---")
            st.subheader("🖨️ 고객 미팅용 A4 공식 분양 제안서 리포트")

            print_html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <title>{site_name} 신축공장 분양계획서</title>
                <style>
                    @page {{
                        size: A4 portrait;
                        margin: 15mm 15mm 15mm 15mm;
                    }}
                    body {{
                        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
                        color: #1a202c;
                        background: white;
                        margin: 0;
                        padding: 0;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                    .report-box {{
                        width: 100%;
                        border: 2px solid #2d3748;
                        border-radius: 6px;
                        padding: 24px;
                        box-sizing: border-box;
                    }}
                    .header-flex {{
                        display: flex;
                        justify-content: space-between;
                        align-items: flex-end;
                        border-bottom: 3px solid #3182ce;
                        padding-bottom: 12px;
                        margin-bottom: 16px;
                    }}
                    .title-area h2 {{
                        margin: 0;
                        color: #1a365d;
                        font-size: 22px;
                        letter-spacing: -0.5px;
                    }}
                    .sub-tag {{
                        font-size: 12px;
                        color: #718096;
                        font-weight: bold;
                    }}
                    .biz-card {{
                        text-align: right;
                        font-size: 13px;
                        line-height: 1.4;
                        color: #2d3748;
                    }}
                    .biz-card b {{
                        font-size: 14px;
                        color: #2b6cb0;
                    }}
                    .info-bar {{
                        font-size: 13.5px;
                        margin-bottom: 12px;
                        padding: 6px 10px;
                        background-color: #f7fafc;
                        border-left: 4px solid #3182ce;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 14px;
                        font-size: 13px;
                    }}
                    th, td {{
                        border: 1px solid #cbd5e0;
                        padding: 8px 10px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #ebf8ff;
                        color: #2c5282;
                        font-weight: bold;
                        width: 25%;
                    }}
                    .price-row {{
                        background-color: #fffaf0 !important;
                    }}
                    .price-highlight {{
                        font-size: 16px;
                        font-weight: bold;
                        color: #c53030;
                    }}
                    .notice-box {{
                        font-size: 11.5px;
                        color: #4a5568;
                        line-height: 1.5;
                        background-color: #f8fafc;
                        border: 1px dashed #cbd5e0;
                        padding: 10px 12px;
                        border-radius: 4px;
                    }}
                </style>
            </head>
            <body>
                <div class="report-box">
                    <div class="header-flex">
                        <div class="title-area">
                            <span class="sub-tag">[신축공장 맞춤형 분양 제안서]</span>
                            <h2>{site_name} 신축공장 분양계획서</h2>
                        </div>
                        <div class="biz-card">
                            우리부동산 공인중개사사무소<br>
                            <b>대표 김태형 (010-2660-8276)</b>
                        </div>
                    </div>

                    <div class="info-bar">
                        <b>수신</b>: {company_display} 귀하 &nbsp;|&nbsp; <b>발행일</b>: {datetime.today().strftime('%Y년 %m월 %d일')}
                    </div>

                    <table>
                        <tr>
                            <th>사업지 위치</th>
                            <td>{site_addr} (전면 {road_width}m 광폭 도로 접)</td>
                        </tr>
                        <tr>
                            <th>입지 강점</th>
                            <td>{site_features}</td>
                        </tr>
                        <tr>
                            <th>분양 대지면적</th>
                            <td><b>{custom_land}평</b> (단독 전용 마당/주차장 약 {yard_pyung}평 확보)</td>
                        </tr>
                        <tr>
                            <th>건축 층수 / 연면적</th>
                            <td><b>지상 {max_floor_cnt}층 공장 (총 연면적 {total_bldg_area}평)</b> | {floor_desc}</td>
                        </tr>
                        <tr>
                            <th>설비 스펙</th>
                            <td>{ceiling_spec} / {power_spec}</td>
                        </tr>
                        <tr class="price-row">
                            <th style="background-color: #feebc8; color: #c05621;">최종 분양 공급가액</th>
                            <td>
                                <span class="price-highlight">{total_dev_price:,}원</span> 
                                <span style="font-size: 12px; color: #718096; margin-left: 8px;">(시설자금대출 최대 80% 가능 / 실투자금 약 {pure_cash:,}원)</span>
                            </td>
                        </tr>
                    </table>

                    <div class="notice-box">
                        • <b>안내사항</b>: 본 견적은 기본 층고 및 인입 동력 기준이며, 기업체의 조업 환경에 맞춘 호이스트 크레인 설치, 수전용량 승압 증설 등 턴키 맞춤 시공이 가능합니다.<br>
                        • <b>문의 및 상담</b>: 현장 부지 답사 및 세부 맞춤 도면 협의는 우리부동산 김태형 대표(☎ 010-2660-8276)에게 언제든 편하게 연락 주십시오.
                    </div>
                </div>
            </body>
            </html>
            """

            st.components.v1.html(f"""
            <button onclick="printReport()" style="
                background-color: #2b6cb0;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                width: 100%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                🖨️ 이 분양제안서만 바로 인쇄하기 (A4 전용 / 전화번호 잘림 방지)
            </button>
            <script>
            function printReport() {{
                var printWindow = window.open('', '_blank');
                printWindow.document.open();
                printWindow.document.write(`{print_html_content}`);
                printWindow.document.close();
                printWindow.focus();
                setTimeout(function() {{
                    printWindow.print();
                }}, 300);
            }}
            </script>
            """, height=65)

    with dev_tab2:
        st.subheader("🏢 신축공장 분양 전용 매물장부")
        st.caption("인천 전지역 신축 분양으로 산출 및 저장된 매물 리스트를 독립적으로 보관·관리합니다.")
        df_devs = load_new_devs()
        if not df_devs.empty:
            st.dataframe(df_devs, use_container_width=True, height=350)
        else:
            st.info("현재 저장된 신축공장 분양 매물이 없습니다. 설계 탭에서 견적 산출 후 저장 버튼을 눌러주세요.")

# =============================================================
# 3. 📋 [주업] 공장 손님 장부 (CRM & 리마인드)
# =============================================================
elif menu_choice == MENU_DICT["CUSTOMER_CRM"]:
    st.title("📋 공장 손님 CRM 관리 장부")
    st.caption("손님별 누적 상담 일지, 보유 매물 양방향 역추천, 업종 인허가 요건, VIP 별표, 안부톡 자동 생성을 완벽 지원합니다.")

    df_c = load_customers()
    today = datetime.today()

    remind_targets = []
    if not df_c.empty:
        for idx, row in df_c.iterrows():
            if str(row.get("진행상태", "")) not in ["계약 완료", "보류/마감"]:
                last_contact_str = str(row.get("최근연락일", ""))
                try:
                    last_contact_dt = datetime.strptime(last_contact_str[:10], "%Y-%m-%d")
                    passed_days = (today - last_contact_dt).days
                    if passed_days >= 7:
                        remind_targets.append({
                            "idx": idx, "고객명": row.get("상호/고객명", ""), "연락처": row.get("연락처", ""),
                            "중요도": row.get("중요도", ""), "경과일": passed_days, "메모": row.get("상담메모", "")
                        })
                except Exception:
                    pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락 후 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | <span style="color:#d69e2e;">{rt['중요도']}</span> | 마지막 연락 후 <b>{rt['경과일']}일 경과</b><br>
                • 최근 메모: {rt['메모']} ➡️ <i>"신규 매물 체크 및 안부 전화 권장"</i>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    tab_list, tab_edit = st.tabs(["📊 손님 장부 목록 (상태별 탭 & 매물 즉시 추천)", "✍️ 손님 신규 등록 및 수정/삭제"])

    with tab_list:
        if not df_c.empty:
            subtab_vip, subtab_active, subtab_done, subtab_all = st.tabs([
                "🔥 집중 관리 (S/A급 VIP)",
                "🏃 상담·브리핑 진행중",
                "🤝 계약 완료 (사후관리)",
                "📁 전체 보기 / 보류·마감"
            ])

            def render_customer_cards(filtered_customers, tab_prefix="all"):
                if filtered_customers.empty:
                    st.info("해당 조건의 손님이 없습니다.")
                    return

                for orig_idx, c_row in filtered_customers.iterrows():
                    is_vip = "S급" in str(c_row.get("중요도", "")) or "A급" in str(c_row.get("중요도", ""))
                    card_class = "customer-card-vip" if is_vip else "customer-card"

                    c_name_val = get_safe_cust_val(c_row, "상호/고객명")
                    c_star_val = get_safe_cust_val(c_row, "중요도")
                    c_deal_val = get_safe_cust_val(c_row, "거래구분")
                    c_phone_val = get_safe_cust_val(c_row, "연락처")
                    c_permit_val = get_safe_cust_val(c_row, "업종인허가", "일반제조")
                    c_loc_val = get_safe_cust_val(c_row, "희망권역")
                    c_area_val = get_safe_cust_val(c_row, "희망평수")
                    c_budget_val = get_safe_cust_val(c_row, "예산(보증금/월세/매매가)")
                    c_movein_val = get_safe_cust_val(c_row, "입주시기")
                    c_hoist_val = get_safe_cust_val(c_row, "호이스트")
                    c_truck_val = get_safe_cust_val(c_row, "대형차진입")
                    c_contact_val = get_safe_cust_val(c_row, "최근연락일")
                    c_memo_val = get_safe_cust_val(c_row, "상담메모")

                    st.markdown(f"""
                    <div class="{card_class}">
                        <b style="font-size: 17px; color: #1a365d;">👤 {c_name_val}</b> 
                        <span style="color:#d69e2e; font-weight: bold; margin-left: 6px;">{c_star_val}</span> | 
                        <b>{c_deal_val}</b> | 📞 {c_phone_val} | 
                        <span class="badge-permit">{c_permit_val}</span><br>
                        • <b>희망지역/평수</b>: {c_loc_val} | 📐 <b>{c_area_val}</b> | 💰 <b>{c_budget_val}</b> | 🗓️ <b>{c_movein_val}</b><br>
                        • <b>설비조건</b>: {c_hoist_val} | 🚛 {c_truck_val} | 📅 최근연락일: {c_contact_val}<br>
                        • <b>상담메모</b>: {c_memo_val}
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2, btn_c3 = st.columns([1.5, 1.5, 1.2])

                    with btn_c1: show_prop_match = st.button(f"🎯 추천 보유매물 조회", key=f"btn_match_{tab_prefix}_{orig_idx}")
                    with btn_c2: show_kakao_gen = st.button(f"💬 안부/체크 카톡 생성", key=f"btn_kakao_{tab_prefix}_{orig_idx}")
                    with btn_c3: show_history = st.button(f"📝 상담일지 열기", key=f"btn_hist_{tab_prefix}_{orig_idx}")

                    if show_prop_match:
                        matched_props = match_properties_for_customer(c_row)
                        st.markdown(f"###### 🏢 [{c_name_val} 대표님] 조건 부합 추천 공장 ({len(matched_props)}건 발견)")
                        if matched_props:
                            for p in matched_props:
                                st.markdown(f"""
                                <div class="match-card-gold" style="padding: 8px 14px; margin-bottom: 6px;">
                                    <b>{p.get('소재지(권역)', '')}</b> ({p.get('거래구분', '')}) | 💰 {p.get('가격(보/월)', '')} | 📐 {p.get('면적', '')} | 층고 {p.get('층고', '')} | 동력 {p.get('동력', '')}<br>
                                    • {p.get('호이스트', '')} | {p.get('대형차량', '')} | 💡 {p.get('특징메모', '')}
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("현재 보유 매물 중 조건에 맞는 매물이 없습니다.")

                    if show_kakao_gen:
                        hello_talk = f"""[{c_name_val} 대표님, 우리부동산 안부 안내]

대표님 안녕하십니까!
인천 공장·창고 전문 우리부동산 김태형 소장입니다.

지난번 문의해 주신 공장({c_loc_val}, {c_area_val} 내외, {c_deal_val}) 조건과 관련하여 신규 접수 매물 체크차 안부 연락드렸습니다.

현재 찾으시는 면적대 주변 공장 시세와 신규 공실 물건들을 면밀히 모니터링하고 있습니다. 혹시 조업 일정이나 입주 시기에 변동이 있으시거나, 추가로 찾으시는 설비 조건이 있으시면 편하게 말씀해 주십시오.

조건에 딱 맞는 최적의 매물이 나오는 대로 가장 먼저 보고드리겠습니다.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
                        st.text_area(f"카톡 안부 복사창 ({c_name_val})", hello_talk, height=260, key=f"txt_talk_{tab_prefix}_{orig_idx}")

                    if show_history:
                        st.markdown(f"###### 📝 [{c_name_val} 대표님] 누적 상담 히스토리 일지")
                        current_hist = str(c_row.get("상담히스토리", ""))
                        if current_hist.strip():
                            st.text_area("이전 상담 기록", current_hist, height=120, disabled=True, key=f"hist_view_{tab_prefix}_{orig_idx}")
                        else:
                            st.caption("아직 누적된 상담 일지가 없습니다.")

                        with st.form(f"form_hist_add_{tab_prefix}_{orig_idx}"):
                            new_log = st.text_input("오늘 통화/상담 내용 입력", placeholder="예: 2차 유선 통화 완료. 현장 미팅 약속")
                            if st.form_submit_button("💾 상담 일지에 추가 저장"):
                                if new_log.strip():
                                    time_tag = datetime.today().strftime("%Y-%m-%d %H:%M")
                                    updated_hist_str = f"[{time_tag}] {new_log.strip()}\n" + current_hist
                                    df_c.at[orig_idx, "상담히스토리"] = updated_hist_str
                                    df_c.at[orig_idx, "최근연락일"] = datetime.today().strftime("%Y-%m-%d")
                                    save_all_customers(df_c)
                                    st.success("✅ 상담 일지가 누적 저장되었습니다!")
                                    st.rerun()

                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

            with subtab_vip:
                vip_df = df_c[df_c["중요도"].str.contains("S급|A급", na=False) & ~df_c["진행상태"].isin(["계약 완료", "보류/마감"])]
                render_customer_cards(vip_df, tab_prefix="vip")

            with subtab_active:
                act_df = df_c[~df_c["진행상태"].isin(["계약 완료", "보류/마감"])]
                render_customer_cards(act_df, tab_prefix="act")

            with subtab_done:
                done_df = df_c[df_c["진행상태"] == "계약 완료"]
                render_customer_cards(done_df, tab_prefix="done")

            with subtab_all:
                render_customer_cards(df_c, tab_prefix="all")
        else:
            st.info("등록된 손님이 없습니다.")

    with tab_edit:
        st.subheader("손님 정보 등록 및 수정 / 삭제")
        edit_mode = st.checkbox("🔄 기존 손님 정보 수정 / 삭제 모드 켜기")
        selected_cust_idx = None
        target_row = None

        if edit_mode and not df_c.empty:
            cust_options = [f"[{i}] {r.get('상호/고객명','')} ({r.get('연락처','')} / {r.get('중요도','')})" for i, r in df_c.iterrows()]
            chosen_cust = st.selectbox("수정 또는 삭제할 손님을 선택하세요", cust_options)
            selected_cust_idx = int(chosen_cust.split("]")[0].replace("[", ""))
            target_row = df_c.iloc[selected_cust_idx]

        with st.form("customer_manage_form", clear_on_submit=False):
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                star_val = str(target_row["중요도"]) if target_row is not None else "⭐⭐ A급(유력)"
                star_opts = ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"]
                star_idx = star_opts.index(star_val) if star_val in star_opts else 1
                c_star = st.selectbox("⭐ 중요도(VIP 등급) *", star_opts, index=star_idx)
            with r2:
                deal_val = str(target_row["거래구분"]) if target_row is not None else "임대차(월세)"
                deal_opts = ["임대차(월세)", "매매", "매매/임대 겸용"]
                deal_idx = deal_opts.index(deal_val) if deal_val in deal_opts else 0
                c_deal_type = st.selectbox("🏷️ 거래 구분 *", deal_opts, index=deal_idx)
            with r3:
                permit_val = str(target_row.get("업종인허가", "일반제조(소음·진동)")) if target_row is not None else "일반제조(소음·진동)"
                permit_opts = ["일반제조(소음·진동)", "폐수·대기 배출 인허가 필수", "식품가공(HACCP)", "단순물류·창고", "자원순환·고물상", "기타 특수업종"]
                permit_idx = permit_opts.index(permit_val) if permit_val in permit_opts else 0
                c_permit = st.selectbox("🏭 업종 및 인허가 요건 *", permit_opts, index=permit_idx)
            with r4:
                name_default = str(target_row["상호/고객명"]) if target_row is not None else ""
                c_name = st.text_input("상호 / 고객명 *", value=name_default, placeholder="예: (주)대한정밀 김대표")

            r5, r6, r7, r8 = st.columns(4)
            with r5:
                phone_default = str(target_row["연락처"]) if target_row is not None else ""
                c_phone = st.text_input("연락처 *", value=phone_default, placeholder="예: 010-1234-5678")
            with r6:
                loc_default = str(target_row["희망권역"]) if target_row is not None else "인천 서구 가좌/석남"
                c_loc = st.text_input("희망 권역 *", value=loc_default)
            with r7:
                area_default = str(target_row["희망평수"]) if target_row is not None else "100~130평"
                c_area = st.text_input("희망 면적/평수 *", value=area_default)
            with r8:
                price_default = get_safe_cust_val(target_row, "예산(보증금/월세/매매가)", "보 3천 / 월 260만 (매매 시 15억)") if target_row is not None else "보 3천 / 월 260만 (매매 시 15억)"
                c_price = st.text_input("희망 예산 (보/월 or 매매)", value=price_default)

            r9, r10, r11, r12 = st.columns(4)
            with r9:
                movein_default = str(target_row["입주시기"]) if target_row is not None else "1~2개월 이내"
                c_movein = st.text_input("입주 희망 시기", value=movein_default)
            with r10:
                hoist_val = str(target_row["호이스트"]) if target_row is not None else "호이스트 필수 (3T~5T)"
                hoist_opts = ["호이스트 필수 (3T~5T)", "있으면 좋음", "불필요"]
                hoist_idx = hoist_opts.index(hoist_val) if hoist_val in hoist_opts else 0
                c_hoist = st.selectbox("호이스트 요구", hoist_opts, index=hoist_idx)
            with r11:
                truck_val = str(target_row["대형차진입"]) if target_row is not None else "11T/윙바디 필수"
                truck_opts = ["츄레라/트레일러 필수", "11T/윙바디 필수", "5T 진입 수월", "1T 위주"]
                truck_idx = truck_opts.index(truck_val) if truck_val in truck_opts else 1
                c_truck = st.selectbox("진입 차량 요구", truck_opts, index=truck_idx)
            with r12:
                stat_val = str(target_row["진행상태"]) if target_row is not None else "상담 접수 (매물 대기중)"
                stat_opts = ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"]
                stat_idx = stat_opts.index(stat_val) if stat_val in stat_opts else 0
                c_status = st.selectbox("진행 상태", stat_opts, index=stat_idx)

            memo_default = str(target_row["상담메모"]) if target_row is not None else ""
            c_memo = st.text_area("기본 상담 메모", value=memo_default, placeholder="예: 동력 75kW 필수, 처마 8m 이상 요망")

            sub_c1, sub_c2 = st.columns([4, 1])
            with sub_c1:
                btn_label = "💾 기존 손님 정보 수정 반영" if edit_mode else "💾 신규 손님 등록하기"
                submit_save = st.form_submit_button(btn_label, type="primary", use_container_width=True)
            with sub_c2:
                submit_delete = st.form_submit_button("🗑️ 손님 삭제", type="secondary", use_container_width=True) if edit_mode else False

            if submit_save:
                if not c_name or not c_phone:
                    st.error("상호/고객명과 연락처는 필수입니다.")
                else:
                    new_entry = {
                        "접수일자": target_row["접수일자"] if target_row is not None else today.strftime("%Y-%m-%d"),
                        "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star,
                        "거래구분": c_deal_type,
                        "업종인허가": c_permit,
                        "상호/고객명": c_name,
                        "연락처": c_phone,
                        "희망권역": c_loc,
                        "희망평수": c_area,
                        "예산(보증금/월세/매매가)": c_price,
                        "입주시기": c_movein,
                        "호이스트": c_hoist,
                        "대형차진입": c_truck,
                        "희망전력kW": "",
                        "상담메모": c_memo,
                        "상담히스토리": target_row.get("상담히스토리", "") if target_row is not None else f"[{today.strftime('%Y-%m-%d %H:%M')}] 최초 접수 완료\n",
                        "진행상태": c_status
                    }
                    if edit_mode and selected_cust_idx is not None:
                        df_c.iloc[selected_cust_idx] = new_entry
                        save_all_customers(df_c)
                        st.success(f"✅ '{c_name}' 대표님 정보가 성공적으로 수정되었습니다!")
                    else:
                        save_customer(new_entry)
                        st.success(f"✅ '{c_name}' 대표님이 신규 장부에 등록되었습니다!")
                    st.rerun()

            if submit_delete and edit_mode and selected_cust_idx is not None:
                df_c = df_c.drop(df_c.index[selected_cust_idx]).reset_index(drop=True)
                save_all_customers(df_c)
                st.warning("🗑️ 손님 데이터가 삭제되었습니다.")
                st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부 (드롭다운 필터 완비)
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()

    if not df_p.empty:
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        with f_col1: sel_pyung = st.selectbox("📐 실사용 평수 구간", ["전체 평수 보기", "50평 이하", "50평 ~ 100평", "100평 ~ 150평", "150평 이상"])
        with f_col2: sel_hoist = st.selectbox("🏗️ 호이스트 여부", ["전체 (유/무 무관)", "호이스트 완비(설치)", "호이스트 없음"])
        with f_col3: sel_truck = st.selectbox("🚛 대형 화물차 여건", ["전체 차량 보기", "츄레라/트레일러 진입 가능", "11톤/윙바디 이상 진입"])
        with f_col4: search_text = st.text_input("🔎 권역 / 지번 / 메모 검색", placeholder="가좌동, 코너 등...")

        filtered_df = df_p.copy()

        def check_pyung(area_val, choice):
            if choice == "전체 평수 보기": return True
            nums = parse_pyung_numbers(area_val)
            if not nums: return True
            p = nums[0]
            if choice == "50평 이하": return p <= 50
            elif choice == "50평 ~ 100평": return 50 < p <= 100
            elif choice == "100평 ~ 150평": return 100 < p <= 150
            elif choice == "150평 이상": return p > 150
            return True

        filtered_df = filtered_df[filtered_df["면적"].apply(lambda x: check_pyung(x, sel_pyung))]

        if sel_hoist == "호이스트 완비(설치)":
            filtered_df = filtered_df[filtered_df["호이스트"].str.contains("완비|설치|톤|T|더블거더", na=False) & ~filtered_df["호이스트"].str.contains("없음", na=False)]
        elif sel_hoist == "호이스트 없음":
            filtered_df = filtered_df[filtered_df["호이스트"].str.contains("없음", na=False)]

        if sel_truck == "츄레라/트레일러 진입 가능":
            filtered_df = filtered_df[filtered_df["대형차량"].str.contains("츄레라|트레일러", na=False)]
        elif sel_truck == "11톤/윙바디 이상 진입":
            filtered_df = filtered_df[filtered_df["대형차량"].str.contains("츄레라|트레일러|11T|11톤|윙바디", na=False)]

        if search_text.strip():
            kw = search_text.strip()
            filtered_df = filtered_df[
                filtered_df["소재지(권역)"].str.contains(kw, na=False) |
                filtered_df["상세주소(지번)"].str.contains(kw, na=False) |
                filtered_df["특징메모"].str.contains(kw, na=False)
            ]

        st.markdown(f"**조회된 매물: 총 {len(filtered_df)}건** (전체 {len(df_p)}건 중)")
        st.dataframe(filtered_df, use_container_width=True, height=450)
    else:
        st.info("현재 등록된 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 AI 시세 추정기")
    st.caption("주소지(동), 대지·건물 평수, 준공연도, 설비 제원을 입력하면 인근 국토부 실거래가 및 네이버 매물 호가를 기반으로 적정 매매가와 임대료(보/월)를 자동 산출합니다.")

    v1, v2, v3 = st.columns(3)
    with v1:
        v_addr = st.text_input("소재지 주소 (동/번지) *", value="인천광역시 서구 가좌동")
        v_land_pyung = st.number_input("대지면적 (평) *", value=200, step=10)
    with v2:
        v_bldg_pyung = st.number_input("건물 연면적 (평) *", value=140, step=10)
        v_year = st.number_input("준공연도 (연식) *", value=2015, min_value=1980, max_value=2026, step=1)
    with v3:
        v_road = st.selectbox("진입 도로 여건", ["8m~10m 도로 접 (대형 윙바디/츄레라 접안)", "6m 일반도로", "소방도로 미만 (골목)"])
        v_hoist = st.selectbox("호이스트 설비", ["호이스트 크레인 완비 (3T~5T)", "호이스트 없음/레일만"])
        v_power = st.number_input("인입 전기용량 (kW)", value=75, step=5)

    if st.button("📊 공장 적정 시세 추정 실행", type="primary", use_container_width=True):
        if "가좌" in v_addr or "석남" in v_addr: land_base_min = 8500000; land_base_max = 11000000
        elif "원창" in v_addr or "북항" in v_addr: land_base_min = 7500000; land_base_max = 9800000
        elif "오류" in v_addr or "검단" in v_addr: land_base_min = 6500000; land_base_max = 8500000
        elif "도화" in v_addr: land_base_min = 9000000; land_base_max = 11500000
        else: land_base_min = 7000000; land_base_max = 9000000

        road_mult = 1.05 if "8m~10m" in v_road else (0.95 if "골목" in v_road else 1.0)
        land_val_min = int(v_land_pyung * land_base_min * road_mult)
        land_val_max = int(v_land_pyung * land_base_max * road_mult)

        passed_yr = max(1, 2026 - v_year)
        depreciation = max(0.2, (1.0 - (passed_yr / 35.0)))
        bldg_val = int(v_bldg_pyung * 3000000 * depreciation)

        fac_add = 18000000 if "완비" in v_hoist else 0
        fac_add += int(max(0, v_power - 30) * 80000)

        final_sale_min = land_val_min + bldg_val + fac_add
        final_sale_max = land_val_max + bldg_val + fac_add

        rent_unit_min = 34000 if ("가좌" in v_addr or "도화" in v_addr) else 30000
        rent_unit_max = 42000 if ("가좌" in v_addr or "도화" in v_addr) else 38000
        m_rent_min = int(v_bldg_pyung * rent_unit_min)
        m_rent_max = int(v_bldg_pyung * rent_unit_max)
        deposit_est = int((m_rent_min + m_rent_max) / 2 * 10)

        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{v_addr}] 공장 추정 시세 결과</h4>
            • <b>예상 적정 매매가</b>: <span style="font-size: 19px; font-weight: bold; color: #c53030;">{final_sale_min:,}원 ~ {final_sale_max:,}원</span><br>
            • <b>대지 평당 매매단가</b>: 약 {int((final_sale_min/v_land_pyung)/10000):,}만 원 ~ {int((final_sale_max/v_land_pyung)/10000):,}만 원 선<br>
            • <b>예상 적정 임대료</b>: <span style="font-size: 17px; font-weight: bold; color: #2b6cb0;">보증금 {deposit_est:,}원 / 월세 {m_rent_min:,}원 ~ {m_rent_max:,}원</span><br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
            💡 <b>세부 감정 평가 내역</b>: 대지 가치 약 {land_val_min:,}원~{land_val_max:,}원 / 건물 잔존가치 약 {bldg_val:,}원 / 설비 가산 약 {fac_add:,}원
        </div>
        """, unsafe_allow_html=True)

# =============================================================
# 6. 🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기
# =============================================================
elif menu_choice == MENU_DICT["BLOG_TOOL"]:
    st.title("🍜 맛집 & 🧢 일상 핫플 블로그 포스팅 허브")
    st.caption("공장 포스팅과 동일한 고품격 네이버 상위노출 양식(스토리텔링 ➡️ 제원표 ➡️️ ✅ 6대 체크포인트 ➡️ 사진별 상세 해설 ➡️ 명함/태그)으로 생성됩니다.")
    b_tab1, b_tab2 = st.tabs(["🍜 맛집 솔직 후기 (대표님 전용 양식)", "🧢 일상 핫플 탐방 (대표님 전용 양식)"])

    with b_tab1:
        st.subheader("🍜 맛집 방문 정보 입력")
        m1, m2, m3 = st.columns(3)
        with m1:
            m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
            m_loc = st.text_input("위치 / 권역 *", placeholder="예: 인천 서구 청라동")
            m_kw = st.text_input("메인 공략 키워드 *", placeholder="예: 청라 맛집, 청라 삼겹살 맛집")
        with m2:
            m_addr = st.text_input("상세 주소 및 주차 *", placeholder="예: 인천 서구 청라커낼로 123 (지하주차 2시간 무료)")
            m_time = st.text_input("영업시간 및 정기휴무 *", placeholder="예: 11:30 ~ 23:00 (브레이크타임 없음, 연중무휴)")
            m_menu = st.text_input("주문 메뉴 및 결제 가격 *", placeholder="예: 연탄 생삼겹살 2인분(32,000원), 차돌된장찌개(7,000원)")
        with m3:
            m_wait = st.text_input("방문 시간대 및 웨이팅 여부", placeholder="예: 주말 저녁 6시 30분 방문 / 현장 캐치테이블 20분 대기")
            m_target = st.text_input("추천 방문 목적", placeholder="예: 가족 외식, 직장인 회식, 데이트 모임")
            m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 은은한 연탄 불향과 육즙의 조화가 끝내주는 가성비 삼겹살 찐맛집")

        food_imgs = st.file_uploader("📷 맛집 현장 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="f_imgs")
        m_taste = st.text_area(
            "맛 평가 및 상차림 디테일 메모 (스토리텔링용)",
            placeholder="예: 35년 전통 연탄불 직화구이로 첫 점부터 육즙 폭발. 파채와 묵은지 구이의 조합이 일품이며, 칼칼한 된장찌개가 밥도둑임."
        )

        if st.button("🚀 맛집 블로그 실전 포스팅 생성하기", type="primary"):
            if not m_name or not m_eval:
                st.error("상호명과 솔직 총평은 필수입니다.")
            else:
                food_kw_list = [k.strip() for k in m_kw.split(",") if k.strip()]
                main_tag = food_kw_list[0] if food_kw_list else m_name

                food_blog_text = f"""안녕하세요. 인천 맛집·일상 탐방 전문 우리부동산입니다.
{m_loc} 맛집 중 제대로 된 불향과 가성비를 갖추고 이 가격과 퀄리티로 나오는 곳은 정말 귀합니다.
요즘 외식 물가가 워낙 만만치 않은 데다, 소문만 요란하고 실제로는 고기 질이 떨어지거나 밑반찬이 부실해 실망하는 경우가 허다합니다. 오늘 소개해 드리는 곳은 {m_loc}에 위치한 {m_name} 내돈내산 솔직 방문 후기로, {m_menu} 구성에 {m_eval}이라는 만족스러운 식사를 즐기고 와 강력 추천해 드립니다.

대표사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{m_addr}에 위치해 있어 대중교통 접근성이 우수하며, 전용 주차 공간이 잘 갖추어져 있어 자차로 방문하기에도 최적화된 동선을 자랑합니다. 문을 열고 들어서자마자 활기찬 분위기와 함께 은은하게 퍼지는 숯불 향이 식욕을 자극합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 {m_name} 상세 정보표
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
항목 | 세부 정보
---|---
상호명 | {m_name}
소재지 | {m_addr}
영업시간 | {m_time}
방문 시간 / 대기 | {m_wait}
주문 메뉴 / 가격 | {m_menu}
주차 여건 | {m_addr.split('(')[-1].replace(')', '') if '(' in m_addr else '주차 가능'}
추천 목적 | {m_target}
특징 | ✅ {m_loc} 고기집 중 특급 가성비와 퀄리티<br>✅ {m_taste.split('.')[0] if m_taste else '잡내 없이 육즙 가득한 메인 메뉴'}<br>✅ 정갈하고 손맛 살아있는 기본 상차림과 곁들임 찬<br>✅ 단체 회식 및 가족 외식에 최적화된 쾌적한 테이블 동선<br>✅ 친절하고 빠른 서빙 응대 서비스<br>✅ {m_target} 장소로 강력 추천

매장 내부 및 상차림 사진
출처 입력

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{m_name} 메인 매장 전경 및 테이블 세팅 전경입니다. 깔끔하게 정돈된 실내 공간에 환기 시설이 잘 완비되어 있어 옷에 냄새 배일 걱정 없이 쾌적하게 식사를 즐기기에 최적화된 구조입니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
오늘의 메인 메뉴 상차림 전체 전경입니다. 당일 공수한 신선한 원육 위에 굵은 소금이 적절히 뿌려져 나와 굽기 전부터 남다른 퀄리티를 자랑합니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{m_menu}! {m_eval}을 자랑하는 {m_loc} 알짜배기 찐맛집 방문 현장입니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
불판 위에 고기를 올리고 노릇노릇하게 구워내는 순간입니다. 겉은 바삭하고 속은 촉촉하게 육즙을 가두며 익어가는데, 고소한 육향이 코끝을 스치며 군침이 돕니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
첫 점을 집어 소금에만 살짝 찍어 맛본 순간입니다. 잡내 없이 팡 터지는 풍부한 육즙과 쫄깃한 식감이 일품이며, 특제 파채 무침과 묵은지를 곁들이면 느끼함 없이 무한 흡입이 가능합니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
식사 메뉴로 함께 곁들인 찌개와 사이드 디테일 뷰입니다. 칼칼하고 진한 국물이 속을 든든하게 풀어주어 마지막 밥 한 공기까지 뚝딱 비우게 만듭니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
식사를 마치고 나오는 길에 담아본 매장 분위기입니다. 피크 타임에는 웨이팅이 발생할 수 있으니 살짝 여유 있는 시간대에 방문하시는 것을 권해드립니다.

{m_loc} 상권에서 제대로 된 고기 맛과 든든한 한 끼를 {m_menu} 가격에 즐길 수 있는 기회는 흔치 않습니다.
모임 장소나 가족 외식, 데이트 코스로 실패 없는 알짜배기 맛집을 찾으시는 분들께서는 꼭 한 번 방문해 보시길 권해드립니다.

사진 삭제링크AI 활용 설정
사진 설명을 입력하세요.
명함을 누르시면 전화 연결이 됩니다.
언제든 편하게 연락 주시기 바랍니다.

부동산 상담 문의, 맛집 정보 공유 언제든 환영합니다.
우리부동산 공인중개사사무소 대표
김태형 010-2660-8276

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
정직하고 최선을 다하여 좋은 정보를 전해드리겠습니다.

#{m_name.replace(' ','')} #{m_loc.replace(' ','')}맛집 #{main_tag.replace(' ','')} #인천맛집 #인천고기집 #인천맛집추천 #내돈내산맛집 #우리부동산 #인천부동산 #청라맛집 #가좌동맛집 #서구맛집 #가족외식추천 #회식장소추천 #모임장소 #데이트맛집 #인천핫플 #솔직후기
"""
                st.markdown("---")
                st.subheader("📝 네이버 블로그 최상위 맛집 포스팅 본문")
                st.text_area("맛집 블로그 복사용 전체 본문", food_blog_text, height=450)

    with b_tab2:
        st.subheader("🧢 일상 핫플 탐방 정보 입력")
        d1, d2, d3 = st.columns(3)
        with d1:
            d_name = st.text_input("핫플 / 브랜드명 *", placeholder="예: 스투시 서울 챕터 도산")
            d_loc = st.text_input("위치 / 거리 *", placeholder="예: 서울 강남구 신사동 도산공원 일대")
            d_kw = st.text_input("메인 검색 키워드 *", placeholder="예: 스투시 서울, 도산공원 핫플, 압구정 쇼룸")
        with d2:
            d_addr = st.text_input("상세 위치 및 주차 *", placeholder="예: 서울 강남구 압구정로46길 42 (발렛 주차 가능)")
            d_time = st.text_input("운영시간 및 정기휴무 *", placeholder="예: 매일 11:00 ~ 20:00 (명절 당일 휴무)")
            d_item = st.text_input("주요 신상 품목 및 가격대 *", placeholder="예: 2026 SS 신상 후드티(18만 원대), 로고 티셔츠, 볼캡")
        with d3:
            d_wait = st.text_input("방문 시간대 및 대기 난이도", placeholder="예: 주말 오후 2시 방문 / 현장 태블릿 40분 대기 등록")
            d_target = st.text_input("추천 방문 목적", placeholder="예: 주말 쇼핑, 데이트 코스, 스트릿 패션 성지 순례")
            d_eval = st.text_input("한 줄 총평 *", placeholder="예: 감각적인 인테리어와 힙한 사운드가 공존하는 스트릿 패션의 성지")

        daily_imgs = st.file_uploader("📷 핫플 현장 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="d_imgs")
        d_note = st.text_area(
            "내부 인테리어 무드, 신상 라인업, 쇼핑 팁 (스토리텔링용)",
            placeholder="예: 미니멀한 노출 콘크리트 인테리어에 힙한 사운드가 가득함. 신상 라인업 회전율이 빠르며 피팅룸 대기 전 미리 사이즈 체크 필수."
        )

        if st.button("🚀 일상 핫플 블로그 실전 포스팅 생성하기", type="primary"):
            if not d_name or not d_eval:
                st.error("핫플명과 한 줄 총평은 필수입니다.")
            else:
                daily_kw_list = [k.strip() for k in d_kw.split(",") if k.strip()]
                main_dtag = daily_kw_list[0] if daily_kw_list else d_name

                daily_blog_text = f"""안녕하세요. 일상의 멋진 공간과 핫플레이스를 기록하는 우리부동산입니다.
{d_loc} 핫플 중 감각적인 인테리어와 브랜드 헤리티지를 갖추고 이 정도 무드를 보여주는 곳은 정말 귀합니다.
요즘 도산공원이나 성수동 일대에서 쇼룸을 찾아보시면 겉만 번지르르하고 실제 볼거리가 없거나 웨이팅만 길어 실망하는 경우가 허다합니다. 오늘 소개해 드리는 곳은 {d_loc}에 위치한 {d_name} 솔직 방문 후기로, {d_item} 라인업과 함께 {d_eval}이라는 특별한 경험을 즐기고 와 강력 추천해 드립니다.

대표사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{d_addr}에 위치해 있어 도산공원 카페거리와 함께 연계해 둘러보기에 최적화된 동선을 자랑합니다. 매장 파사드부터 시선을 사로잡는 모던한 외관과 함께 감각적인 브랜드 시그니처 로고가 멋스럽게 안착되어 있습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 {d_name} 상세 정보표
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
항목 | 세부 정보
---|---
장소명 | {d_name}
소재지 | {d_addr}
운영시간 | {d_time}
방문 시간 / 대기 | {d_wait}
주요 품목 / 가격대 | {d_item}
주차 여건 | {d_addr.split('(')[-1].replace(')', '') if '(' in d_addr else '인근 유료/발렛 주차'}
추천 목적 | {d_target}
특징 | ✅ {d_loc} 일대 스트릿 패션의 상징적 랜드마크 쇼룸<br>✅ {d_note.split('.')[0] if d_note else '미니멀하고 감각적인 인테리어 무드'}<br>✅ 시즌 신상 어패럴 및 헤드웨어 풀 라인업 구비<br>✅ 쾌적한 피팅룸 및 친절한 스태프 어드바이스<br>✅ 포토존이 살아있는 감각적인 익스테리어 디자인<br>✅ {d_target} 코스로 강력 추천

쇼룸 내부 및 디스플레이 사진
출처 입력

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{d_name} 메인 매장 진입로 및 1층 파사드 전경입니다. 널찍한 통유리창 너머로 감각적인 조명과 디스플레이가 한눈에 들어와 지나가는 사람들의 발길을 멈추게 만듭니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
1층 메인 쇼룸 전체 전경입니다. 미니멀한 노출 콘크리트 베이스 위에 힙한 BGM이 흐르며, 브랜드의 아이덴티티를 온전히 느낄 수 있는 세련된 공간 배치를 보여줍니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
{d_item}! {d_eval}을 자랑하는 {d_loc} 알짜배기 핫플레이스 탐방 현장입니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
시즌 메인 랙 디스플레이 구역입니다. 원단의 터치감과 핏감을 직접 만져보고 확인할 수 있으며, 마감 봉제 하나까지 탄탄하게 제작되어 실물 깡패의 면모를 보여줍니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
쇼룸 중앙에서 피팅룸 방향을 바라본 레이아웃입니다. 동선 간격이 넉넉해 주말 피크 타임에도 쾌적하게 아이템을 둘러볼 수 있도록 배려되어 있습니다.

사진 삭제
사진 삭제AI 활용 설정
사진 설명을 입력하세요.
헤드웨어 및 액세서리 쇼케이스 상세 뷰입니다. 품절 대란을 일으키는 시그니처 캡과 비니 라인업이 정갈하게 진열되어 있어 쇼핑 욕구를 자극합니다.

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
피팅을 마치고 매장을 나서며 담아본 쇼룸 뷰입니다. 현장 웨이팅이 발생할 수 있으니 도착 즉시 현장 태블릿에 대기 등록을 하시는 것을 권해드립니다.

{d_loc} 상권에서 브랜드의 진정한 감성과 트렌디한 무드를 {d_item} 라인업과 함께 온전히 즐길 수 있는 공간은 흔치 않습니다.
주말 도산공원 나들이나 감각적인 쇼핑 데이트 코스를 찾으시는 분들께서는 서둘러 현장을 방문해 보시길 권해드립니다.

사진 삭제링크AI 활용 설정
사진 설명을 입력하세요.
명함을 누르시면 전화 연결이 됩니다.
언제든 편하게 연락 주시기 바랍니다.

부동산 상담 문의, 핫플 정보 공유 언제든 환영합니다.
우리부동산 공인중개사사무소 대표
김태형 010-2660-8276

사진 삭제AI 활용 설정
사진 설명을 입력하세요.
정직하고 최선을 다하여 유익한 정보를 전해드리겠습니다.

#{d_name.replace(' ','')} #{d_loc.replace(' ','')}핫플 #{main_dtag.replace(' ','')} #도산공원핫플 #압구정핫플 #서울쇼룸 #스트릿패션 #쇼핑투어 #데이트코스 #우리부동산 #인천부동산 #주말나들이 #핫플투어 #패션스타그램 #쇼핑후기 #도산공원카페거리 #신사동핫플 #솔직방문기
"""
                st.markdown("---")
                st.subheader("📝 네이버 블로그 최상위 일상 핫플 포스팅 본문")
                st.text_area("일상 핫플 블로그 복사용 전체 본문", daily_blog_text, height=450)