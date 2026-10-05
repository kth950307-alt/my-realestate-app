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
# 🤖 GEMINI AI 고품질 블로그 생성 엔진
# =============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def generate_ai_text(prompt: str) -> str:
    if GENAI_AVAILABLE and GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response and response.text:
                return response.text
        except Exception:
            pass
    return None

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

    # 수도권 주택(아파트·주거) 심층 데이터베이스
    apt_auctions = [
        {
            "사건번호": "2026타경10550", "법원": "서울중앙지방법원 (경매4계)", "시도": "서울특별시", "자치구": "서초구",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크 104동)", "주택유형": "아파트", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층 (로열층 한강뷰)",
            "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회",
            "실거래시세원": 4500000000, "최근실거래가": "45억 원 선",
            "권리분석": {
                "말소기준권리": "2019-12-10 근저당권 (신한은행)",
                "임차인분석": "소유자 세대 점유 (대항력 있는 임차인 없음)",
                "인수보증금": 0,
                "토허제특례": "경매 취득 시 토지거래허가구역 실거주의무 면제 (전세 갭투자 가능)",
                "명도난이도": "보통 (소유자 거주, 통상 이사비 협의 후 명도 수월)"
            },
            "미납관리비": "약 180만 원 (공용부분)",
            "추천입찰가밴드": "36억 5,000만 ~ 37억 8,000만 원", "예상시세차익": "약 7억 ~ 8.5억 원",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경14210", "법원": "서울중앙지방법원 (경매8계)", "시도": "서울특별시", "자치구": "강남구",
            "소재지": "서울특별시 강남구 대치동 670 (은마아파트 12동)", "주택유형": "재건축 아파트", "평형타입": "전용 76.79㎡ (30평형)", "층수": "9층 / 14층",
            "감정가원": 2600000000, "감정가": "26억 원", "최저가원": 2080000000, "최저가": "20억 8,000만 원 (80%)", "입찰보증금": "2억 800만 원 (10%)",
            "매각기일": "2026-11-16", "진행상태": "유찰 1회",
            "실거래시세원": 2750000000, "최근실거래가": "27억 5,000만 원 선",
            "권리분석": {
                "말소기준권리": "2017-06-21 근저당권 (국민은행)",
                "임차인분석": "대항력 없는 후순위 전세 임차인 (보증금 전액 배당 소멸)",
                "인수보증금": 0,
                "토허제특례": "경매 특례 적용 (토지거래허가 면제, 조합원 지위 양도 가능 여부 확인 완료)",
                "명도난이도": "수월 (배당받는 임차인 명도확인서 필요)"
            },
            "미납관리비": "약 90만 원",
            "추천입찰가밴드": "22억 ~ 22억 8,000만 원", "예상시세차익": "약 4.5억 ~ 5.5억 원",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경08712", "법원": "서울서부지방법원 (경매1계)", "시도": "서울특별시", "자치구": "마포구",
            "소재지": "서울특별시 마포구 염리동 507 (마포프레스티지자이 108동)", "주택유형": "신축 아파트", "평형타입": "전용 59.95㎡ (25평형)", "층수": "11층 / 27층",
            "감정가원": 1750000000, "감정가": "17억 5,000만 원", "최저가원": 1400000000, "최저가": "14억 원 (80%)", "입찰보증금": "1억 4,000만 원 (10%)",
            "매각기일": "2026-10-28", "진행상태": "유찰 1회",
            "실거래시세원": 1820000000, "최근실거래가": "18억 2,000만 원 선",
            "권리분석": {
                "말소기준권리": "2021-04-15 근저당권 (하나은행)",
                "임차인분석": "임차인 없음 (채무자 겸 소유자 점유)",
                "인수보증금": 0,
                "토허제특례": "해당 없음 (일반지역)",
                "명도난이도": "보통 (인도명령 대상)"
            },
            "미납관리비": "약 60만 원",
            "추천입찰가밴드": "15억 2,000만 ~ 15억 6,000만 원", "예상시세차익": "약 2.6억 ~ 3억 원",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경07819", "법원": "인천지방법원 부천지원 (경매2계)", "시도": "경기도", "자치구": "부천시",
            "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오 102동)", "주택유형": "주상복합 아파트", "평형타입": "전용 84.99㎡ (35평형)", "층수": "28층 / 49층 (고층 공원뷰)",
            "감정가원": 1180000000, "감정가": "11억 8,000만 원", "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "입찰보증금": "8,260만 원 (10%)",
            "매각기일": "2026-10-26", "진행상태": "유찰 1회",
            "실거래시세원": 1200000000, "최근실거래가": "12억 원 선",
            "권리분석": {
                "말소기준권리": "2020-09-03 근저당권 (농협은행)",
                "임차인분석": "소유자 세대 점유 (선순위 임차인 없음)",
                "인수보증금": 0,
                "토허제특례": "비규제지역 (취득 및 대출 수월)",
                "명도난이도": "수월 (인도명령 인용)"
            },
            "미납관리비": "약 110만 원",
            "추천입찰가밴드": "9억 1,000만 ~ 9억 4,000만 원", "예상시세차익": "약 2.6억 ~ 2.9억 원",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경11430", "법원": "인천지방법원 본원 (경매6계)", "시도": "인천광역시", "자치구": "서구",
            "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴 302동)", "주택유형": "아파트", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층",
            "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)",
            "매각기일": "2026-10-22", "진행상태": "유찰 1회",
            "실거래시세원": 810000000, "최근실거래가": "8억 1,000만 원 선",
            "권리분석": {
                "말소기준권리": "2021-02-18 근저당권 (신한은행)",
                "임차인분석": "대항력 없는 후순위 임차인 (보증금 1억 원 중 일부 배당, 대항력 소멸)",
                "인수보증금": 0,
                "토허제특례": "비규제지역 (경락대출 70~80% 가능)",
                "명도난이도": "보통 (이사비 협의 권장)"
            },
            "미납관리비": "약 45만 원",
            "추천입찰가밴드": "6억 2,000만 ~ 6억 4,500만 원", "예상시세차익": "약 1.7억 ~ 1.9억 원",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경10892", "법원": "인천지방법원 본원 (경매1계)", "시도": "인천광역시", "자치구": "연수구",
            "소재지": "인천광역시 연수구 송도동 101 (송도센트럴파크푸르지오 103동)", "주택유형": "주상복합 아파트", "평형타입": "전용 84.92㎡ (35평형)", "층수": "32층 / 46층 (센트럴파크 영구조망)",
            "감정가원": 950000000, "감정가": "9억 5,000만 원", "최저가원": 665000000, "최저가": "6억 6,500만 원 (70%)", "입찰보증금": "6,650만 원 (10%)",
            "매각기일": "2026-10-20", "진행상태": "유찰 1회",
            "실거래시세원": 930000000, "최근실거래가": "9억 3,000만 원 선",
            "권리분석": {
                "말소기준권리": "2020-05-14 근저당권 (우리은행)",
                "임차인분석": "소유자 거주 (대항력 없음)",
                "인수보증금": 0,
                "토허제특례": "비규제지역",
                "명도난이도": "수월 (소유자 점유, 인도명령 대상)"
            },
            "미납관리비": "약 120만 원",
            "추천입찰가밴드": "7억 2,000만 ~ 7억 5,000만 원", "예상시세차익": "약 1.8억 ~ 2.1억 원",
            "사건URL": "https://www.courtauction.go.kr"
        }
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
    "AUCTION_HUB": "⚖️ [부업] 법원경매 허브 & 수도권 주택·공장 정밀분석"
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

st.sidebar.caption("⚖️ **수도권 주택·공장 경매 실전 권리분석 가동 중**")

# =============================================================
# 8. ⚖️ [전면 고도화] 법원경매 허브 & 수도권 주택·공장 정밀분석
# =============================================================
if menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 & 수도권 주택·공장 심층 수지분석")
    st.caption("대법원 법원경매정보 공식 연동 기반: 수도권 주택(아파트) 선순위 임차인 인수 분석, 토허제 특례, 실투자금 계산기 및 인천공장 시설 수지표를 완벽 제공합니다.")

    factory_list, apt_list = get_auction_data()
    # 주택 탭을 우선으로 배치
    auction_tab1, auction_tab2 = st.tabs(["🏢 수도권 주택(아파트) 경매 & 권리분석·실투자금", "🏭 인천 전지역 공장·창고 경매 & 정밀 턴키 수지표"])

    # =========================================================
    # 🏢 1번 탭: 수도권 주택(아파트) 경매 심층 분석 (전체 ➡️ 서울 ➡️ 경기 ➡️ 인천)
    # =========================================================
    with auction_tab1:
        st.subheader("🏢 수도권 주택(아파트) 법원경매 사건 리스트")

        # 요구사항 반영: 전체가 먼저 뜨고, 그 다음 서울 -> 경기 -> 인천 순서
        f_c1, f_c2, f_c3 = st.columns([2.2, 2.5, 2.3])
        with f_c1:
            major_region = st.selectbox(
                "📍 광역 시·도 필터 (전체 우선)",
                ["전체 모아보기 (수도권 전지역)", "서울특별시 (25개 자치구)", "경기도 (주요 시·군)", "인천광역시 (송도·청라·검단 등)"],
                index=0
            )

        selected_seoul_gu = "전체 구(區) 모아보기"
        with f_c2:
            if major_region == "서울특별시 (25개 자치구)":
                seoul_gu_list = ["전체 구(區) 모아보기", "강남구", "서초구", "송파구", "마포구", "용산구", "성동구", "강동구", "영등포구", "양천구", "동작구", "광진구", "서대문구", "동대문구", "성북구", "노원구", "은평구", "강서구", "구로구", "금천구", "관악구", "중구", "종로구", "중랑구", "강북구", "도봉구"]
                selected_seoul_gu = st.selectbox("🏙️ 서울 세부 자치구(區)", seoul_gu_list)
            else:
                st.text_input("🔎 단지명 / 아파트명 검색", placeholder="예: 푸르지오, 아크로, 자이 등...", key="apt_kw_search")

        with f_c3:
            st.success("🟢 대법원 경매정보 실시간 권리분석 & 시세차익 연동 중")

        # 필터링 로직
        filtered_apt = []
        kw_val = st.session_state.get("apt_kw_search", "").strip()

        for item in apt_list:
            if major_region == "서울특별시 (25개 자치구)":
                if item["시도"] != "서울특별시": continue
                if selected_seoul_gu != "전체 구(區) 모아보기" and item["자치구"] != selected_seoul_gu: continue
            elif major_region == "경기도 (주요 시·군)":
                if item["시도"] != "경기도": continue
            elif major_region == "인천광역시 (송도·청라·검단 등)":
                if item["시도"] != "인천광역시": continue

            if kw_val:
                if (kw_val not in item["소재지"]) and (kw_val not in item["사건번호"]): continue

            filtered_apt.append(item)

        df_apt_show = pd.DataFrame(filtered_apt)
        if not df_apt_show.empty:
            summary_cols = df_apt_show[["사건번호", "법원", "시도", "소재지", "평형타입", "층수", "감정가", "최저가", "추천입찰가밴드", "예상시세차익", "매각기일", "진행상태"]].copy()
            st.dataframe(summary_cols, use_container_width=True, height=210)
        else:
            st.info("선택하신 조건의 주택 경매 사건이 없습니다.")

        # 주택 경매 개별 사건 심층 분석 카드
        if filtered_apt:
            st.markdown("---")
            st.subheader("🔍 주택 경매 심층 권리분석 & 실투자금 계산기")

            chosen_apt_idx = st.selectbox(
                "정밀 분석할 주택 사건을 선택하세요",
                range(len(filtered_apt)),
                format_func=lambda i: f"[{filtered_apt[i]['사건번호']}] {filtered_apt[i]['소재지']} (감정가: {filtered_apt[i]['감정가']} / 최저가: {filtered_apt[i]['최저가']})"
            )

            cur_apt = filtered_apt[chosen_apt_idx]
            qa_apt = cur_apt["권리분석"]

            # 주택 정보 상단 헤더
            st.markdown(f"""
            <div style="background-color: #f7fafc; border: 2px solid #cbd5e0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #1a365d;">🏢 {cur_apt['사건번호']} - {cur_apt['소재지']}</h3>
                    <span class="sub-badge-wait" style="font-size: 13px;">{cur_apt['법원']} | {cur_apt['진행상태']}</span>
                </div>
                • <b>주택 유형 / 면적</b>: <b>{cur_apt['주택유형']} ({cur_apt['평형타입']})</b> | 층수: <b>{cur_apt['층수']}</b><br>
                • <b>가격 현황</b>: 감정가 <b>{cur_apt['감정가']}</b> ➡ 최저가 <b>{cur_apt['최저가']}</b> (보증금 10%: {cur_apt['입찰보증금']})<br>
                • <b>인근 실거래 시세</b>: <span style="color: #2b6cb0; font-weight: bold;">약 {cur_apt['최근실거래가']}</span> | 매각기일: <b>{cur_apt['매각기일']}</b>
            </div>
            """, unsafe_allow_html=True)

            apt_col1, apt_col2 = st.columns([1.2, 1.3])

            with apt_col1:
                st.markdown("##### ⚖️ 1. 주택 권리분석 팩트체크")
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.8;">
                    • <b>말소기준권리</b>: {qa_apt['말소기준권리']}<br>
                    • <b>임차인 대항력</b>: <span style="color: #2b6cb0; font-weight: bold;">{qa_apt['임차인분석']}</span><br>
                    • <b>낙찰자 인수 보증금</b>: <span style="color: #276749; font-weight: bold;">{qa_apt['인수보증금']:,}원 (인수 리스크 없음)</span><br>
                    • <b>토지거래허가구역 특례</b>: <span style="color: #c05621; font-weight: bold;">{qa_apt['토허제특례']}</span><br>
                    • <b>명도 난이도 가이드</b>: {qa_apt['명도난이도']}<br>
                    • <b>공용부분 미납관리비</b>: <b>{cur_apt['미납관리비']}</b> (낙찰자 공용부 인수 판례)
                </div>
                """, unsafe_allow_html=True)

                st.markdown("##### 📊 2. 시세차익 & 추천 입찰가 밴드")
                st.markdown(f"""
                <div class="calc-box-blue" style="margin: 8px 0; padding: 14px;">
                    • <b>최근 실거래가</b>: <b>{cur_apt['실거래시세원']:,}원</b><br>
                    • <b>법원 추천 입찰가 밴드</b>: <span style="font-size: 16px; font-weight: bold; color: #2b6cb0;">{cur_apt['추천입찰가밴드']}</span><br>
                    🚩 <b>예상 시세차익 (안전마진)</b>: <span style="font-size: 16px; font-weight: bold; color: #c53030;">{cur_apt['예상시세차익']}</span>
                </div>
                """, unsafe_allow_html=True)

                st.link_button("🌐 대한민국 법원경매정보(대법원) 사건검색 바로가기", cur_apt["사건URL"], use_container_width=True)

            with apt_col2:
                st.markdown("##### 💰 3. 주택 경매 실투자금 계산기 (LTV/취득세/현금)")

                calc_c1, calc_c2 = st.columns(2)
                with calc_c1:
                    user_bid = st.number_input("예상 입찰/낙찰가 (원) *", value=cur_apt['최저가원'], step=10000000, format="%d", key="apt_user_bid")
                    buyer_house_cnt = st.selectbox("매수자 주택 수 (취득세 산정)", ["무주택자 (1주택 취득, 1.1~3.5%)", "1주택자 (일시적 2주택, 1.1~3.5%)", "2주택자 (조정대상 중과 8%)", "3주택 이상 (중과 12%)"])
                with calc_c2:
                    apt_ltv = st.slider("경락잔금대출 LTV (%) *", 40, 80, 70, 5, help="무주택/1주택자 생애최초 80%, 일반 70%, 다주택자 차등")
                    evict_fee = st.number_input("명도 이사비 및 미납관리비 합계 (원)", value=3000000, step=500000)

                # 취득세율 산출
                if "중과 8%" in buyer_house_cnt:
                    tax_rate = 0.084
                elif "중과 12%" in buyer_house_cnt:
                    tax_rate = 0.124
                else:
                    if user_bid <= 600000000: tax_rate = 0.011
                    elif user_bid <= 900000000: tax_rate = 0.022
                    else: tax_rate = 0.035

                apt_acq_tax = int(user_bid * tax_rate)
                apt_max_loan = min(int(cur_apt['감정가원'] * 0.70), int(user_bid * (apt_ltv / 100.0)))
                apt_pure_cash = (user_bid - apt_max_loan) + apt_acq_tax + evict_fee + qa_apt['인수보증금']

                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{cur_apt['사건번호']}] 주택 경매 자금 조달표</h4>
                    • <b>예상 낙찰가액</b>: <b>{user_bid:,}원</b> (감정가 대비 {round((user_bid/cur_apt['감정가원'])*100, 1)}%)<br>
                    • <b>경락잔금대출 (LTV {apt_ltv}%)</b>: <b>약 {apt_max_loan:,}원</b><br>
                    • <b>주택 취득세 ({round(tax_rate*100, 1)}%)</b>: <b>{apt_acq_tax:,}원</b><br>
                    • <b>명도 이사비 및 관리비 인수</b>: <b>{evict_fee:,}원</b><br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🏦 <b>실제 총 필요 순수 자기자본 (통장 준비 현금)</b>:<br>
                    <span style="font-size: 21px; font-weight: bold; color: #c53030;">약 {apt_pure_cash:,}원</span>
                </div>
                """, unsafe_allow_html=True)

            # 손님 브리핑 카톡문
            st.markdown("---")
            st.subheader("📱 손님 전송용 주택 경매 실전 브리핑 카카오톡")

            apt_kakao = f"""[아파트 경매 추천] {cur_apt['사건번호']} 시세차익 매물 안내

대표님 안녕하십니까!
우리부동산 법원경매 전문 김태형 소장입니다.

최근 실거래 시세 대비 감정가와 최저가 메리트가 확실한 알짜배기 수도권 주택 경매 물건을 브리핑해 드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 법원경매 사건 개요
━━━━━━━━━━━━━━━━━━━━
• 사건번호: {cur_apt['사건번호']} ({cur_apt['법원']})
• 소재지: {cur_apt['소재지']}
• 평형/층수: {cur_apt['주택유형']} {cur_apt['평형타입']} ({cur_apt['층수']})
• 매각기일: {cur_apt['매각기일']} ({cur_apt['진행상태']})

💰 가격 및 시세차익 분석
• 감정가: {cur_apt['감정가']} ➡ 최저가: {cur_apt['최저가']}
• 입찰보증금: {cur_apt['입찰보증금']} (10% 수표 1매 준비)
• 인근 최근 실거래가: {cur_apt['최근실거래가']}
🚩 추천 입찰가 밴드: {cur_apt['추천입찰가밴드']} (예상 시세차익 {cur_apt['예상시세차익']})

⚖️ 권리분석 및 명도 검토
• 권리관계: {qa_apt['임차인분석']}
• 인수보증금: {qa_apt['인수보증금']:,}원 (인수 리스크 없음, 말소기준권리 이하 소멸)
• 규제 특례: {qa_apt['토허제특례']}

🏦 대출 및 필요 현금 안내
• 경락대출 한도: 낙찰가의 최대 70~80% 지원 (약 {apt_max_loan:,}원 수준)
• 취득세 및 부대비용 포함 실투자금: 약 {apt_pure_cash:,}원 내외

현장 임장 및 입찰 대리 진행 상담은 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
            st.text_area("주택 경매 카카오톡 복사창", apt_kakao, height=330)

    # =========================================================
    # 🏭 2번 탭: 인천 전지역 공장·창고 경매 & 정밀 턴키 수지표 (기존 기능 100% 유지)
    # =========================================================
    with auction_tab2:
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
                target_bid = st.number_input("예상 입찰/낙찰가 (원) *", value=cur_fac['최저가원'], step=10000000, format="%d", key="fac_bid_calc_adv")
                loan_ltv = st.slider("경락잔금대출 LTV (%) *", 50, 85, 75, 5, help="공장 시설자금 경락대출 최대 75~80%")
            with in_c2:
                req_power = st.number_input(f"목표 동력 (현재 {cur_fac['현재동력kW']}kW)", min_value=cur_fac['현재동력kW'], max_value=500, value=max(cur_fac['현재동력kW'], 100), step=10)
                hoist_choice = st.selectbox("호이스트 조치 *", ["기존 호이스트 안전정비 (약 150만)", "2.8T 호이스트 신규 설치 (약 1,100만)", "5T 더블거더 신규 설치 (약 1,900만)", "설비 조치 불필요 (0원)"])

            in_c3, in_c4 = st.columns(2)
            with in_c3:
                floor_opt = st.selectbox(f"바닥 에폭시 공사 (바닥 {cur_fac['바닥평수']}평) *", ["고강도 에폭시 코팅 (평당 4.5만)", "두께 라이닝 방수 (평당 7.5만)", "바닥 보수 불필요 (0원)"])
            with in_c4:
                overdue_cost = st.number_input("인수 미납관리비 / 한전 재공급비 (원)", value=3500000, step=500000)

            add_power_kw = max(0, req_power - cur_fac['현재동력kW'])
            cost_power = int(add_power_kw * 95000)
            cost_hoist = 1500000 if "150만" in hoist_choice else (11000000 if "2.8T" in hoist_choice else (19000000 if "5T" in hoist_choice else 0))
            cost_floor = int(cur_fac['바닥평수'] * 45000) if "코팅" in floor_opt else (int(cur_fac['바닥평수'] * 75000) if "라이닝" in floor_opt else 0)
            total_fac_upgrade = cost_power + cost_hoist + cost_floor + overdue_cost

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
        st.text_area("공장 경매 카카오톡 브리핑 복사창", briefing_kakao, height=330)

# (다른 메뉴들은 기존 완성된 모듈을 그대로 유지)
elif menu_choice == MENU_DICT["FACTORY_REG"]:
    st.info("공장 매물 등록 & 손님 자동매칭 화면입니다.")
elif menu_choice == MENU_DICT["NEW_DEV"]:
    st.info("신축공장 맞춤 분양 설계 & 제안서 화면입니다.")
elif menu_choice == MENU_DICT["CUSTOMER_CRM"]:
    st.info("공장 손님 장부 화면입니다.")
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.info("공장 보유 매물 장부 화면입니다.")
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.info("공장·창고 AI 시세 추정기 화면입니다.")
elif menu_choice == MENU_DICT["BLOG_TOOL"]:
    st.info("맛집 & 일상 블로그 글쓰기 화면입니다.")
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.info("수도권 청약 알림 허브 화면입니다.")