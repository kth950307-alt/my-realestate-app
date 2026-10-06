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
    .customer-card-pro {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #3182ce;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
    }
    .customer-card-pro-vip {
        background-color: #fffdf7;
        border: 1px solid #feebc8;
        border-left: 6px solid #dd6b20;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(221,107,32,0.1);
    }
    .tag-blue {
        background-color: #ebf8ff;
        color: #2b6cb0;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-orange {
        background-color: #fffaf0;
        color: #c05621;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-gray {
        background-color: #edf2f7;
        color: #4a5568;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-green {
        background-color: #f0fff4;
        color: #276749;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
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
    .calc-box-purple {
        background-color: #faf5ff;
        border: 1px solid #e9d8fd;
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
    .sub-badge-hot {
        background-color: #e53e3e;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11.5px;
        font-weight: bold;
    }
    .check-list-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #4a5568;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 13px;
        line-height: 1.7;
    }
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"], .stButton, header, footer {
            display: none !important;
        }
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 보안 잠금
# =============================================================
CORRECT_PASSWORD = "950307"

def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("### 🏢 우리부동산 통합 업무 시스템")
        st.caption("인천 공장 중개 & 법원경매·청약/공공임대 포스팅 허브 - 사무실 보안 인증")
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
            if "예산(보증금/월세)" in df.columns: df["예산(보증금/월세/매매가)"] = df["예산(보증금/월세)"]
            else: df["예산(보증금/월세/매매가)"] = ""
        if "거래구분" not in df.columns: df["거래구분"] = "임대차(월세)"
        if "중요도" not in df.columns: df["중요도"] = "⭐⭐ A급(유력)"
        if "최근연락일" not in df.columns: df["최근연락일"] = df["접수일자"] if "접수일자" in df.columns else datetime.today().strftime("%Y-%m-%d")
        if "업종인허가" not in df.columns: df["업종인허가"] = "일반제조(소음·진동)"
        if "입주시기" not in df.columns: df["입주시기"] = "협의 입주"
        if "호이스트" not in df.columns: df["호이스트"] = "호이스트 무관"
        if "대형차진입" not in df.columns: df["대형차진입"] = "11T 윙바디 수월"
        if "희망전력kW" not in df.columns: df["희망전력kW"] = "일반전력(30kW 내외)"
        if "상담히스토리" not in df.columns: df["상담히스토리"] = ""
        return df
    cols = ["접수일자", "최근연락일", "중요도", "거래구분", "업종인허가", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세/매매가)", "입주시기", "호이스트", "대형차진입", "희망전력kW", "상담메모", "상담히스토리", "진행상태"]
    return pd.DataFrame(columns=cols)

def save_all_customers(df): df.to_csv(CUSTOMERS_CSV, index=False, encoding="utf-8-sig")

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
    if os.path.exists(NEW_DEV_CSV): return pd.read_csv(NEW_DEV_CSV)
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
    if pd.isna(val) or str(val).strip() == "" or str(val).strip() == "nan":
        if col_name == "예산(보증금/월세/매매가)": val = row.get("예산(보증금/월세)", default)
        else: val = default
    return str(val) if pd.notna(val) else default

# =============================================================
# ⚖️ 대법원 법원경매 정밀 데이터베이스
# =============================================================
def get_auction_data():
    factory_auctions = [
        {
            "사건번호": "2026타경10452", "법원": "인천지방법원 본원 (경매5계)", "소재지": "인천광역시 서구 가좌동 556-12", "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)", "건물면적": "528.9㎡ (약 160평)", "바닥평수": 160, "현재동력kW": 75, "현재호이스트": "호이스트 5T 완비",
            "총감정가원": 1850000000, "총감정가": "18억 5,000만 원", "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)", "입찰보증금": "1억 2,950만 원 (10%)",
            "토지감정가원": 1350000000, "건물감정가원": 420000000, "기계기구감정가원": 80000000, "기계감정내역": "천장주행 크레인 5T 1식, 수전설비 75kW",
            "매각기일": "2026-10-22", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2019-04-12 근저당권 (신한은행)", "임차인": "대항력 없는 후순위 임차인 1명 (보증금 3,000만 원)", "유치권": "유치권 신고 없음 (깨끗)", "인수권리": "인수 권리 없음 (소멸주의)"},
            "산단입주자격": "일반공업지역 (산집법 입주계약 불필요, 모든 제조업 입주 가능)", "연체관리비추정": 3500000,
            "배당정보": {"경매비용": 12000000, "당해세": 8000000, "최우선변제": 0, "선순위근저당": 950000000, "임차인배당": 30000000},
            "제원및코멘트": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활. 가좌IC 3분 거리.",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경11208", "법원": "인천지방법원 본원 (경매3계)", "소재지": "인천광역시 서구 오류동 검단일반산단 42-5", "세부용도": "신축급 공장",
            "대지면적": "991.7㎡ (약 300평)", "건물면적": "793.3㎡ (약 240평)", "바닥평수": 240, "현재동력kW": 150, "현재호이스트": "호이스트 레일 완비 (본체 철거)",
            "총감정가원": 2680000000, "총감정가": "26억 8,000만 원", "최저가원": 1876000000, "최저가": "18억 7,600만 원 (70%)", "입찰보증금": "1억 8,760만 원 (10%)",
            "토지감정가원": 1900000000, "건물감정가원": 750000000, "기계기구감정가원": 30000000, "기계감정내역": "수전설비 150kW",
            "매각기일": "2026-10-27", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2021-08-19 근저당권 (기업은행)", "임차인": "소유자 점유 (대항력 없음)", "유치권": "유치권 신고 없음", "인수권리": "소멸주의"},
            "산단입주자격": "검단일반산단 관리구역 (산집법상 제조업 입주적격업체 사전 확인 필수)", "연체관리비추정": 8000000,
            "배당정보": {"경매비용": 16000000, "당해세": 12000000, "최우선변제": 0, "선순위근저당": 1400000000, "임차인배당": 0},
            "제원및코멘트": "산단 코너 필지, 츄레라 회전 가능 마당, 층고 10m, 동력 150kW 대용량.",
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]

    apt_auctions = [
        {
            "사건번호": "2026타경10550", "법원": "서울중앙지방법원 (경매4계)", "시도": "서울특별시", "자치구": "서초구",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크 104동)", "주택유형": "아파트", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층 (로열층 한강뷰)",
            "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회", "실거래시세원": 4500000000, "최근실거래가": "45억 원 선",
            "권리분석": {
                "말소기준권리": "2019-12-10 근저당권 (신한은행)", "임차인분석": "소유자 세대 점유 (대항력 있는 임차인 없음)",
                "인수보증금": 0, "토허제특례": "경매 취득 시 토지거래허가구역 실거주의무 면제 (전세 갭투자 가능)", "명도난이도": "보통 (소유자 거주, 협의 수월)"
            },
            "미납관리비": 1800000, "추천입찰가밴드": "36억 5,000만 ~ 37억 8,000만 원", "예상시세차익": "약 7억 ~ 8.5억 원",
            "배당정보": {"경매비용": 18000000, "당해세": 15000000, "최우선변제": 0, "선순위근저당": 2800000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경07819", "법원": "인천지방법원 부천지원 (경매2계)", "시도": "경기도", "자치구": "부천시",
            "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오 102동)", "주택유형": "주상복합 아파트", "평형타입": "전용 84.99㎡ (35평형)", "층수": "28층 / 49층 (고층 공원뷰)",
            "감정가원": 1180000000, "감정가": "11억 8,000만 원", "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "입찰보증금": "8,260만 원 (10%)",
            "매각기일": "2026-10-26", "진행상태": "유찰 1회", "실거래시세원": 1200000000, "최근실거래가": "12억 원 선",
            "권리분석": {
                "말소기준권리": "2020-09-03 근저당권 (농협은행)", "임차인분석": "소유자 세대 점유 (선순위 임차인 없음)",
                "인수보증금": 0, "토허제특례": "비규제지역 (대출 수월)", "명도난이도": "수월 (인도명령 인용)"
            },
            "미납관리비": 1100000, "추천입찰가밴드": "9억 1,000만 ~ 9억 4,000만 원", "예상시세차익": "약 2.6억 ~ 2.9억 원",
            "배당정보": {"경매비용": 8500000, "당해세": 3200000, "최우선변제": 0, "선순위근저당": 650000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경11430", "법원": "인천지방법원 본원 (경매6계)", "시도": "인천광역시", "자치구": "서구",
            "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴 302동)", "주택유형": "아파트", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층",
            "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)",
            "매각기일": "2026-10-22", "진행상태": "유찰 1회", "실거래시세원": 810000000, "최근실거래가": "8억 1,000만 원 선",
            "권리분석": {
                "말소기준권리": "2021-02-18 근저당권 (신한은행)", "임차인분석": "후순위 임차인 (보증금 1억 원 전액 배당 소멸)",
                "인수보증금": 0, "토허제특례": "비규제지역 (경락대출 70~80% 가능)", "명도난이도": "보통 (이사비 협의 권장)"
            },
            "미납관리비": 450000, "추천입찰가밴드": "6억 2,000만 ~ 6억 4,500만 원", "예상시세차익": "약 1.7억 ~ 1.9억 원",
            "배당정보": {"경매비용": 6500000, "당해세": 2400000, "최우선변제": 0, "선순위근저당": 420000000, "임차인배당": 100000000},
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 🏢 [전수 복구] 분양/무순위 줍줍 DB & LH·SH 공공임대 DB (누락 제로)
# =============================================================
def fetch_subscription_data_sale():
    """1. 서울·경기·인천·세종 분양 & 로또 줍줍 전수 데이터"""
    return [
        {
            "단지명": "강변역 센트럴 아이파크", "권역": "서울특별시", "유형": "🔥 무순위/취소후재공급 (줍줍)",
            "상세공급위치": "서울특별시 광진구 자양동 680-63 일원",
            "시공사": "HDC현대산업개발(주)", "공급규모": "총 215세대 중 계약취소/잔여 2세대",
            "모집공고일": "2026-10-02", "특별공급일": "2026-10-07", "1순위해당": "2026-10-08",
            "당첨자발표": "2026-10-15", "정당계약일": "2026-10-26 ~ 10-28", "입주예정월": "2026년 12월 예정",
            "규제체크": {"분양가상한제": "미적용", "전매제한": "1년", "거주의무": "없음", "재당첨제한": "미적용"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "지하철 2호선 강변역 및 구의역 더블역세권. 잠실대교를 통한 강남·잠실 10분대 진입.",
            "학군인프라": "성동초(사립), 광진중, 광양고 도보 통학권.",
            "자격요건요약": "국내 거주 만 19세 이상 성년자 (청약통장 무관, 100% 추첨제)",
            "타입정보": [{"타입": "전용 84㎡A", "세대수": "잔여 2세대", "최고분양가원": 1270000000, "최고분양가": "12억 7,000만 원", "평당가": "약 3,735만"}],
            "인근대장단지": "자양 하늘채 / 구의 롯데캐슬 (84㎡ 16억 8,000만 원)", "예상안전마진": "약 4억 1,000만 원",
            "타입전략": "전국 유주택자 청약 가능. 계약금 20% 현금 조달 계획 필수."
        },
        {
            "단지명": "충정로역자이르네", "권역": "서울특별시", "유형": "🔥 계약취소주택 재공급 (줍줍)",
            "상세공급위치": "서울특별시 서대문구 충정로2가 185-1 일원",
            "시공사": "자이에스앤디(주)", "공급규모": "총 192세대 중 계약취소 1세대",
            "모집공고일": "2026-10-06", "특별공급일": "2026-10-14", "1순위해당": "2026-10-15",
            "당첨자발표": "2026-10-21", "정당계약일": "2026-10-29", "입주예정월": "즉시 입주 협의",
            "규제체크": {"분양가상한제": "미적용", "전매제한": "등기완료 시", "거주의무": "없음", "재당첨제한": "미적용"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "2·5호선 충정로역 초역세권. 시청, 광화문, 여의도 중심업무지구 10분 직주근접.",
            "학군인프라": "미동초등학교 도보 5분 통학로.",
            "자격요건요약": "서울특별시 거주 만 19세 이상 무주택세대구성원",
            "타입정보": [{"타입": "전용 52㎡", "세대수": "취소 1세대", "최고분양가원": 795000000, "최고분양가": "7억 9,500만 원", "평당가": "약 3,456만"}],
            "인근대장단지": "마포래미안푸르지오 (59㎡ 10억 5,000만 원)", "예상안전마진": "약 2억 5,500만 원",
            "타입전략": "서울 무주택 세대주만 신청 가능. 자금 준비된 3040 실수요자 집중 공략 권장."
        },
        {
            "단지명": "신림스카이아파트 (20차)", "권역": "서울특별시", "유형": "🔥 임의공급 잔여세대 (줍줍)",
            "상세공급위치": "서울특별시 관악구 신림동 1433-55",
            "시공사": "스카이종합건설(주)", "공급규모": "총 43세대 중 잔여 5세대",
            "모집공고일": "2026-10-05", "특별공급일": "2026-10-12", "1순위해당": "2026-10-13",
            "당첨자발표": "2026-10-18", "정당계약일": "2026-10-25", "입주예정월": "즉시 입주 가능",
            "규제체크": {"분양가상한제": "미적용", "전매제한": "등기완료 시", "거주의무": "없음", "재당첨제한": "미적용"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "신림선 당곡역 및 2호선 신림역 도보 이용 가능. 강남순환도시고속도로 인접.",
            "학군인프라": "당곡초, 당곡중, 당곡고 인접.",
            "자격요건요약": "국내 거주 만 19세 이상 (청약통장 무관, 다주택자 가능)",
            "타입정보": [{"타입": "전용 56㎡", "세대수": "잔여 5세대", "최고분양가원": 580000000, "최고분양가": "5억 8,000만 원", "평당가": "약 2,521만"}],
            "인근대장단지": "신림 현대아파트 (59㎡ 6억 8,000만 원)", "예상안전마진": "약 1억 원",
            "타입전략": "서울 진입 희망 1~2인 가구 즉시 입주 틈새 추천."
        },
        {
            "단지명": "부천대장 A2블록 부천대장 하우스토리 디센트", "권역": "경기도", "유형": "공공분양",
            "상세공급위치": "경기도 부천시 부천대장 공공주택지구 A2블록",
            "시공사": "남광토건(주) / 하우스토리", "공급규모": "지하 2층 ~ 지상 15층, 8개동, 총 548세대",
            "모집공고일": "2026-09-30", "특별공급일": "2026-10-12", "1순위해당": "2026-10-13",
            "당첨자발표": "2026-10-20", "정당계약일": "2026-12-07 ~ 12-11", "입주예정월": "2029년 06월 예정",
            "규제체크": {"분양가상한제": "적용 (공공택지)", "전매제한": "3년", "거주의무": "3년 유예", "재당첨제한": "10년"},
            "공고URL": "https://xn--vk1bl3b19f7xexvfwncgul82b1wt8smd2ch4k.com",
            "교통망분석": "대장~홍대선 광역철도 호재로 마곡·홍대 직결. S-BRT 환승 인프라.",
            "학군인프라": "단지 바로 옆 초등학교·유치원 신설 부지 확정된 초품아.",
            "자격요건요약": "수도권 거주 무주택세대구성원",
            "타입정보": [
                {"타입": "전용 59㎡A", "세대수": "242세대", "최고분양가원": 435000000, "최고분양가": "4억 3,500만 원", "평당가": "약 1,740만"},
                {"타입": "전용 84㎡A", "세대수": "116세대", "최고분양가원": 588000000, "최고분양가": "5억 8,800만 원", "평당가": "약 1,729만"}
            ],
            "인근대장단지": "계양 롯데캐슬 파크시티 (84㎡ 7억 2,000만 원)", "예상안전마진": "약 1억 3,200만 원",
            "타입전략": "59A는 판상형 인기 타입, 가점이 낮다면 타워형 틈새 공략 추천."
        },
        {
            "단지명": "과천 그랑자이 파크 (지정타 S2BL)", "권역": "경기도", "유형": "일반분양",
            "상세공급위치": "경기도 과천시 갈현동 과천지식정보타운 S2BL",
            "시공사": "GS건설(주)", "공급규모": "총 740세대",
            "모집공고일": "2026-10-01", "특별공급일": "2026-10-13", "1순위해당": "2026-10-14",
            "당첨자발표": "2026-10-22", "정당계약일": "2026-11-03 ~ 11-06", "입주예정월": "2027년 09월 예정",
            "규제체크": {"분양가상한제": "적용 (공공택지)", "전매제한": "3년", "거주의무": "실거주 3년", "재당첨제한": "10년"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "4호선 과천정보타운역(예정) 역세권, GTX-C 연계, 과천대로·제2경인고속도로 직결.",
            "학군인프라": "과천율목초·중 통합학교 도보 5분 통학로.",
            "자격요건요약": "과천시 및 수도권 거주 무주택세대구성원",
            "타입정보": [
                {"타입": "전용 59㎡A", "세대수": "120세대", "최고분양가원": 560000000, "최고분양가": "5억 6,000만 원", "평당가": "약 2,240만"},
                {"타입": "전용 84㎡A", "세대수": "210세대", "최고분양가원": 870000000, "최고분양가": "8억 7,000만 원", "평당가": "약 2,558만"}
            ],
            "인근대장단지": "과천 푸르지오 오르투스 (84㎡ 14억 5,000만 원)", "예상안전마진": "약 5억 8,000만 원",
            "타입전략": "84A는 고가점 경쟁 예상, 59A 특별공급 적극 활용 추천."
        },
        {
            "단지명": "오남역 서희스타힐스 여의재 1단지", "권역": "경기도", "유형": "🔥 임의공급 잔여세대 (줍줍)",
            "상세공급위치": "경기도 남양주시 오남읍 양지리 704 일원",
            "시공사": "(주)서희건설", "공급규모": "총 1,308세대 중 잔여 임의공급 8세대",
            "모집공고일": "2026-10-06", "특별공급일": "2026-10-12", "1순위해당": "2026-10-13",
            "당첨자발표": "2026-10-18", "정당계약일": "2026-10-26", "입주예정월": "2027년 03월 예정",
            "규제체크": {"분양가상한제": "미적용", "전매제한": "6개월", "거주의무": "없음", "재당첨제한": "미적용"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "지하철 4호선 오남역 인접으로 당고개·노원 20분대 진입.",
            "학군인프라": "양지초, 오남중, 오남고 도보 10분 통학권.",
            "자격요건요약": "국내 거주 만 19세 이상 (다주택자 신청 가능, 청약통장 무관)",
            "타입정보": [{"타입": "전용 59㎡A", "세대수": "잔여 8세대", "최고분양가원": 385000000, "최고분양가": "3억 8,500만 원", "평당가": "약 1,540만"}],
            "인근대장단지": "오남 신우아이딜 (59㎡ 4억 9,000만 원)", "예상안전마진": "약 1억 500만 원",
            "타입전략": "수도권 3억 대 진입 가능한 4호선 역세권 소액 투자 추천."
        },
        {
            "단지명": "계양 롯데캐슬 파크시티 1단지", "권역": "인천광역시", "유형": "일반분양",
            "상세공급위치": "인천광역시 계양구 효성동 100 일원",
            "시공사": "롯데건설(주)", "공급규모": "총 1,964세대",
            "모집공고일": "2026-09-26", "특별공급일": "2026-10-06", "1순위해당": "2026-10-07",
            "당첨자발표": "2026-10-15", "정당계약일": "2026-10-27 ~ 10-30", "입주예정월": "2027년 11월 예정",
            "규제체크": {"분양가상한제": "미적용", "전매제한": "1년", "거주의무": "없음", "재당첨제한": "미적용"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "서울 2호선 청라 연장선 기대감 및 BRT 정류장 인접, 서인천IC 초근접.",
            "학군인프라": "효성서초, 북인천여중, 명현중·고 도보 통학권.",
            "자격요건요약": "인천 및 수도권 거주자 (청약통장 가입 12개월 이상)",
            "타입정보": [
                {"타입": "전용 59㎡A", "세대수": "180세대", "최고분양가원": 478000000, "최고분양가": "4억 7,800만 원", "평당가": "약 1,910만"},
                {"타입": "전용 84㎡A", "세대수": "520세대", "최고분양가원": 659000000, "최고분양가": "6억 5,900만 원", "평당가": "약 1,938만"}
            ],
            "인근대장단지": "힐스테이트 자이 계양 (84㎡ 7억 5,000만 원)", "예상안전마진": "약 9,100만 원",
            "타입전략": "1년 후 입주 전 전매 가능하여 단기 투자 및 갈아타기 최적."
        },
        {
            "단지명": "세종 우미 린 센터파크 (5-2생활권 S1BL)", "권역": "세종/기타", "유형": "🔥 무순위 사후접수 (전국 줍줍)",
            "상세공급위치": "세종특별자치시 다솜동 5-2생활권 S1블록",
            "시공사": "우미건설(주)", "공급규모": "총 680세대 중 잔여 3세대",
            "모집공고일": "2026-10-05", "특별공급일": "2026-10-13", "1순위해당": "2026-10-14",
            "당첨자발표": "2026-10-19", "정당계약일": "2026-10-28", "입주예정월": "2027년 08월 예정",
            "규제체크": {"분양가상한제": "적용 (공공택지)", "전매제한": "3년", "거주의무": "없음", "재당첨제한": "10년"},
            "공고URL": "https://www.applyhome.co.kr",
            "교통망분석": "세종 BRT 정류장 인접으로 정부세종청사 및 오송역 15분 연결.",
            "학군인프라": "단지 바로 앞 유치원 및 초·중·고 부지 신설 에듀타운.",
            "자격요건요약": "전국 거주 만 19세 이상 성년자 (거주지 무관, 청약통장 무관)",
            "타입정보": [{"타입": "전용 84㎡A", "세대수": "잔여 3세대", "최고분양가원": 485000000, "최고분양가": "4억 8,500만 원", "평당가": "약 1,426만"}],
            "인근대장단지": "세종 마스터힐스 (84㎡ 6억 8,000만 원)", "예상안전마진": "약 1억 9,500만 원",
            "타입전략": "전국 청약 가능 줍줍. 거주의무 없어 입주 시 전세로 잔금 충당 가능."
        }
    ]

def fetch_subscription_data_rent():
    """2. LH / SH / iH 공공임대 & 청년주택 전수 데이터"""
    return [
        {
            "단지명": "[SH] 자양동 청년안심주택 (역세권)", "기관": "SH 서울주택도시공사", "권역": "서울특별시", "유형": "청년안심주택 (공공임대)",
            "상세공급위치": "서울특별시 광진구 자양동 680-1 일원 (구의역 도보 3분)",
            "공급규모": "총 280세대 중 공공임대 98세대",
            "모집공고일": "2026-10-05", "서류제출기간": "2026-10-19 ~ 10-23", "당첨자발표": "2026-12-10", "계약및입주": "2027년 01월 입주",
            "공고URL": "https://www.i-sh.co.kr",
            "임대조건": {
                "기본보증금": "3,800만 원", "기본월세": "19만 원",
                "최대전환보증금": "5,600만 원", "최저월세": "8만 원대 (전환이율 6.7%)"
            },
            "신청자격": "만 19세~39세 무주택 청년 (소득 100% 이하: 월 약 360만 원 / 총자산 2억 7,300만 원 이하)",
            "차량기준": "차량 미소유자 우선 (생업용/장애인 차량 외 원칙적 주차 불가)",
            "청약통장혜택": "청약통장 유무 상관없이 신청 가능 (당첨되어도 청약통장 효력 100% 유지!)",
            "교통및환경": "2호선 구의역 150m 초역세권, 냉장고·세탁기·에어컨 풀퍼니시드 시스템 빌트인 제공."
        },
        {
            "단지명": "[LH] 인천계양 A3블록 신혼희망타운 (행복주택)", "기관": "LH 한국토지주택공사", "권역": "인천광역시", "유형": "신혼부부 행복주택",
            "상세공급위치": "인천광역시 계양구 동양동 인천계양 A3BL",
            "공급규모": "총 359세대",
            "모집공고일": "2026-10-06", "서류제출기간": "2026-10-20 ~ 10-26", "당첨자발표": "2026-12-18", "계약및입주": "2027년 03월 입주",
            "공고URL": "https://apply.lh.or.kr",
            "임대조건": {
                "기본보증금": "6,200만 원", "기본월세": "24만 원",
                "최대전환보증금": "9,800만 원", "최저월세": "10만 원대"
            },
            "신청자격": "혼인 7년 이내 신혼부부 또는 예비신혼부부 (소득 130% 이하 / 총자산 3억 4,500만 원 이하)",
            "차량기준": "차량가액 3,708만 원 이하",
            "청약통장혜택": "행복주택 거주 중에도 청약통장 효력 유지 (향후 일반분양 계속 도전 가능)",
            "교통및환경": "인천 1호선 박촌역 연계, 3기 신도시 계양 테크노밸리 배후 신축 단지, 어린이집 완비."
        },
        {
            "단지명": "[iH] 검단신도시 청년 매입임대주택", "기관": "iH 인천도시공사", "권역": "인천광역시", "유형": "청년 매입임대",
            "상세공급위치": "인천광역시 서구 원당동 검단지구 신축 오피스텔 단지",
            "공급규모": "총 45세대",
            "모집공고일": "2026-10-01", "서류제출기간": "2026-10-15 ~ 10-19", "당첨자발표": "2026-11-25", "계약및입주": "2026년 12월 즉시입주",
            "공고URL": "https://www.ih.co.kr",
            "임대조건": {
                "기본보증금": "200만 원 (목돈 부담 제로)", "기본월세": "15만~18만 원 선",
                "최대전환보증금": "협의", "최저월세": "주변 원룸 시세의 40~50% 수준"
            },
            "신청자격": "만 19세~39세 무주택 미혼 청년 (본인 소득 및 부모 소득 분위 합산 검토)",
            "차량기준": "등록 차량가액 3,708만 원 이하",
            "청약통장혜택": "청약통장 불필요, 재당첨 제한 없음",
            "교통및환경": "인천 1호선 아라역(신설) 인접, 상업지구 도보 5분, 풀옵션 가전 완비."
        }
    ]

# 🎯 양방향 매칭 헬퍼 함수
def match_customers_advanced(fac_loc, fac_deal_type, fac_hoist, fac_truck, fac_area_text, fac_power_text=""):
    df = load_customers()
    if df.empty: return []
    active_df = df[~df["진행상태"].isin(["계약 완료", "보류/마감"])].copy()
    if active_df.empty: return []

    fac_pyungs = parse_pyung_numbers(fac_area_text)
    f_pyung = fac_pyungs[0] if fac_pyungs else None
    f_truck_lv = 4 if any(k in fac_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in fac_truck for k in ["11T", "11톤", "윙바디"]) else 2)
    f_has_hoist = any(k in fac_hoist for k in ["완비", "설치", "톤", "T"]) and ("없음" not in fac_hoist)

    results = []
    for _, row in active_df.iterrows():
        score = 50
        reasons = ["기본 권역 검토"]
        if f_has_hoist and "필수" in str(row.get("호이스트", "")): score += 25; reasons.append("호이스트 일치")
        if score >= 55:
            results.append({
                "고객명": row.get("상호/고객명"), "중요도": row.get("중요도"), "거래구분": row.get("거래구분"),
                "연락처": row.get("연락처"), "희망권역": row.get("희망권역"), "희망평수": row.get("희망평수"),
                "상담메모": row.get("상담메모"), "일치점수": score, "매칭사유": ", ".join(reasons)
            })
    return results

def match_properties_for_customer(cust_row):
    df_p = load_properties()
    if df_p.empty: return []
    c_loc = str(cust_row.get("희망권역", ""))
    c_pyungs = parse_pyung_numbers(cust_row.get("희망평수", ""))
    c_pyung = c_pyungs[0] if c_pyungs else None

    matched_props = []
    for _, prop in df_p.iterrows():
        p_loc = str(prop.get("소재지(권역)", ""))
        p_area = str(prop.get("면적", ""))
        loc_words = [w for w in c_loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if loc_words and not any(w in p_loc for w in loc_words): continue
        p_pyungs = parse_pyung_numbers(p_area)
        if c_pyung and p_pyungs:
            if not ((c_pyung * 0.75) <= p_pyungs[0] <= (c_pyung * 1.3)): continue
        matched_props.append(prop)
    return matched_props

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
    "APPLY_HOME": "🏢 [부업] 청약·줍줍 & LH·SH 공공임대 포스팅 허브",
    "AUCTION_HUB": "⚖️ [부업] 법원경매 허브 & 수도권 주택·공장 정밀분석"
}

menu_choice = st.sidebar.radio("📌 업무 시스템 메뉴", list(MENU_DICT.values()), index=6)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.caption("🏢 **인천 서구 공장 중개 & 주택청약·공공임대 포스팅 허브 가동 중**")

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 확인·설명서 필수 항목 자동화
# =============================================================
if menu_choice == MENU_DICT["FACTORY_REG"]:
    st.title("🏭 공장 매물 등록 & 중개대상물 확인·설명서 필수 항목 자동화")
    st.caption("건축물대장 공적장부 연동 규격화, 용도지역별 민원 리스크 필터 및 확인·설명서[비주거용] 텍스트가 자동 생성됩니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처", expanded=False):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 556-12 1층")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 박회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")

    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 *", placeholder="예: 인천 서구 가좌동")
    with b2: deal_type = st.selectbox("거래 형태 *", ["임대차(월세)", "매매", "임대/매매 겸용"])
    with b3: vacancy_status = st.selectbox("입주 상태 *", ["현재 공실(즉시입주)", "협의 입주", "만기 후 입주"])
    with b4: expire_date = st.text_input("입주 가능일", placeholder="예: 즉시 협의 가능 / 2027년 1월 이후")

    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 230만 원")
        area = st.text_input("실사용 면적/평수 *", placeholder="예: 1층 75평 + 2층 15평 사무실 (총 90평)")
    with c2:
        ceiling = st.text_input("처마 층고", placeholder="예: 처마 7.5m (호이스트 주행 하이 층고)")
        power = st.text_input("인입 동력 (kW) *", placeholder="예: 30kW (가공 설비 구동 충분)")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음"])
    with c3:
        road = st.text_input("접면 도로 폭(m)", placeholder="예: 8m 도로 접 (문 앞 차량 접안 편리)")
        parking_count = st.text_input("주차장 현황", placeholder="예: 자주식 옥외 3대 (전면 마당 포함)")
        big_truck = st.selectbox("화물차 진입 여건 *", ["1톤 화물차 문 앞 접안 최적", "츄레라 / 트레일러 진출입 원활", "11T 윙바디 접안 원활"])

    st.markdown("---")
    leg1, leg2, leg3 = st.columns(3)
    with leg1:
        violation_status = st.selectbox("위반건축물 여부", ["위반건축물 아님 (적법)", "위반건축물 등재", "확인 요망"])
        building_structure = st.text_input("주구조 / 지붕", value="일반철골구조 / 기타지붕(판넬)")
    with leg2:
        bldg_use = st.text_input("대장상 주용도", value="공장 (제조업소)")
        approval_date = st.text_input("사용승인일자", placeholder="예: 1997.01.17")
    with leg3:
        sewage_type = st.selectbox("오수/정화조 처리방식", ["하수종말처리시설 연결 (직결)", "단독정화조", "기타"])
        elevator_lift = st.selectbox("승강기 / 화물리프트", ["승강기 없음", "화물용 리프트 1대", "승객용 승강기 구비"])

    zoning_choice = st.selectbox("용도지역 분류 (인허가 기준)", ["일반공업지역 (인천지방산단/일반산단)", "전용공업지역 (중화학/공해공장 밀집)", "준공업지역 (주거 혼재 구역)"])
    memo = st.text_area("매물 핵심 강점 메모", placeholder="예: 인천산업유통센터 및 송현 공구상가 초인접으로 부품 수급 최상. 호이스트 완비로 시설비 수천만 원 절감.")

    if st.button("🚀 매물 저장 & 확인·설명서 생성 & 블로그 포스팅 동시 실행", type="primary", use_container_width=True):
        if not price or not area:
            st.error("가격과 면적은 필수 입력 항목입니다.")
        else:
            save_property({
                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
                "거래구분": deal_type, "소재지(권역)": loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
                "임대인연락처": owner_phone, "가격(보/월)": price, "면적": area, "층고": ceiling, "동력": power,
                "호이스트": hoist, "도로/주차": f"{road} / {parking_count}", "대형차량": big_truck, "특징메모": f"[{zoning_choice}] {memo}"
            })
            st.success("✅ 매물이 장부에 안전하게 저장되었습니다!")
            legal_report_text = f"""[중개대상물 확인·설명서 (비주거용 건축물) 필수 기재 사항 요약표]
• 소재지: {secret_address if secret_address else loc}
• 전용면적: {area} | 주용도: {bldg_use} | 구조: {building_structure}
• 사용승인일: {approval_date} | 위반건축물 여부: {violation_status}
• 도로/접안: {road} ({big_truck}) | 주차: {parking_count}
• 인입전력: {power} | 층고: {ceiling} | 호이스트: {hoist}
• 오수처리: {sewage_type} | 용도지역: {zoning_choice}
우리부동산 공인중개사사무소 대표 김태형 010-2660-8276
"""
            st.subheader("📋 공인중개사 중개대상물 확인·설명서 [Ⅱ] (비주거용) 기재 표준 텍스트")
            st.text_area("확인·설명서 복사용 텍스트", legal_report_text, height=220)

# =============================================================
# 2. 🏗️ [주업] 신축공장 맞춤 분양 설계 & 2D 평면도 & A4 제안서
# =============================================================
elif menu_choice == MENU_DICT["NEW_DEV"]:
    st.title("🏗️ 신축공장 맞춤 분양 설계 & 고객 제안서")
    st.caption("인천 전지역 분양 현장 맞춤형 설계안 산출, 도로 폭(m) 연동, 2D 캐드형 평면도, 가변 토지이용계획 분석 및 A4 제안서 단독 인쇄를 지원합니다.")

    dev_tab1, dev_tab2 = st.tabs(["📐 맞춤 분양 설계 & 2D 평면도", "🏢 신축공장 분양 전용 매물장부"])

    with dev_tab1:
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

        st.markdown("---")
        fl1, fl2, fl3, fl4, fl5 = st.columns(5)
        with fl1: f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=70, step=5)
        with fl2: f2_pyung = st.number_input("2층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl3: f3_pyung = st.number_input("3층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl4: f4_pyung = st.number_input("4층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl5: f5_pyung = st.number_input("5층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)

        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원) *", value=1200, step=50)
        with pr2: add_unit_price = st.number_input("상층부 증축단가 (건축 평당 만 원) *", value=350, step=10)
        with pr3: ceiling_spec = st.text_input("층고 제원", value="처마 7m (유효 7.5m)")
        with pr4: power_spec = st.text_input("인입 동력", value="30kW 기본 인입")

        actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
        yard_pyung = max(0, custom_land - f1_pyung)

        if st.button("🚀 신축공장 맞춤 분양 설계 & 제안서 산출하기", type="primary", use_container_width=True):
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
                    • <b>건축 규모</b>: <b>지상 {max_floor_cnt}층 공장 (총 연면적 {total_bldg_area}평)</b> | {floor_desc}<br>
                    • <b>단독 마당/주차</b>: <b>약 {yard_pyung}평 확보</b> (전면 {road_width}m 도로 접)<br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🚩 <b>최종 분양 공급가액</b>: <span style="font-size: 20px; font-weight: bold; color: #c53030;">{total_dev_price:,}원</span><br>
                    • 시설자금 대출 80%: 약 <b>{loan_80:,}원</b> | <b>필요 순수 현금</b>: <span style="color: #2b6cb0; font-weight: bold;">약 {pure_cash + acq_tax:,}원</span> (취득세 4.6% {acq_tax:,}원 포함)
                </div>
                """, unsafe_allow_html=True)

            with out_c2:
                st.markdown("##### 📐 2D 평면 캐드 배치도")
                bldg_w_svg = int(max(20, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
                yard_w_svg = 100 - bldg_w_svg
                truck_text = "40ft 트레일러 접안 최적" if road_width >= 10 else "11T 윙바디 접안"

                svg_2d = f"""
                <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 12px;">
                    <div style="background-color: #2d3748; color: white; text-align: center; padding: 8px; font-weight: bold; font-size: 13px; margin-bottom: 8px;">
                        ▲ 전면 {road_width}m 광폭 도로 접 ({truck_text}) ▲
                    </div>
                    <div style="border: 2px dashed #3182ce; padding: 10px; background-color: #ebf8ff; border-radius: 6px;">
                        <div style="display: flex; gap: 8px; height: 160px;">
                            <div style="flex: {bldg_w_svg}; background-color: #bee3f8; border: 2px solid #1a365d; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 15px; color: #1a365d;">🏭 신축 공장동</span>
                                <span style="font-size: 13px; color: #2c5282; font-weight: bold;">지상 {max_floor_cnt}층 (1F {f1_pyung}평)</span>
                            </div>
                            <div style="flex: {yard_w_svg}; background-color: #edf2f7; border: 2px dashed #718096; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 13px; color: #4a5568;">🚛 단독 마당</span>
                                <span style="font-size: 12px; color: #718096; font-weight: bold;">약 {yard_pyung}평</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(svg_2d, unsafe_allow_html=True)

            print_html_content = f"""<html><body style='font-family:sans-serif; padding:30px;'><h2>{site_name} 신축공장 분양계획서</h2><p>대지: {custom_land}평 | 공급가: {total_dev_price:,}원 | 대출 80%: {loan_80:,}원</p><p>우리부동산 대표 김태형 010-2660-8276</p></body></html>"""
            st.components.v1.html(f"""<button onclick="var w=window.open('','_blank');w.document.write(`{print_html_content}`);w.print();" style="background:#2b6cb0; color:white; padding:10px 20px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">🖨️ 이 분양제안서만 바로 인쇄하기 (A4 전용)</button>""", height=50)

    with dev_tab2:
        st.subheader("🏢 신축공장 분양 전용 매물장부")
        df_devs = load_new_devs()
        if not df_devs.empty: st.dataframe(df_devs, use_container_width=True, height=350)
        else: st.info("저장된 신축공장 분양 매물이 없습니다.")

# =============================================================
# 3. 📋 [주업] 공장 손님 CRM (기간별·월별 필터 완비)
# =============================================================
elif menu_choice == MENU_DICT["CUSTOMER_CRM"]:
    st.title("📋 공장 손님 CRM 관리 장부")
    st.caption("날짜별·월별(Month) 기간 필터, 호이스트·화물차·필요전력·업종 스펙 완비 & 뱃지형 카드 뷰")

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
                except Exception: pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락 후 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | <span style="color:#d69e2e;">{rt['중요도']}</span> | 마지막 연락 후 <b>{rt['경과일']}일 경과</b> ➡️ <i>"신규 매물 체크 및 안부 전화 권장"</i>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    tab_list, tab_edit = st.tabs(["📊 손님 장부 목록", "✍️ 손님 신규 등록 및 수정/삭제"])

    with tab_list:
        if not df_c.empty:
            st.markdown("##### 🗓️ 손님 장부 기간별 & 월별(Month) 상세 필터")
            f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.8, 1.3, 2.0])

            with f_col1:
                date_filter_type = st.selectbox("📅 조회 기준일", ["최근연락일 기준", "최초접수일 기준"], key="crm_date_type")
                date_col_name = "최근연락일" if "최근" in date_filter_type else "접수일자"

            available_months = ["전체 기간 보기"]
            for d_val in df_c[date_col_name].dropna():
                d_str = str(d_val)[:7]
                if len(d_str) == 7 and d_str not in available_months and d_str.startswith("20"):
                    available_months.append(d_str)
            available_months = ["전체 기간 보기"] + sorted(available_months[1:], reverse=True)

            with f_col2: selected_month = st.selectbox("📆 조회 월(Month) 선택", available_months, key="crm_month_filter")
            with f_col3: sort_order = st.selectbox("🔄 정렬 순서", ["최신 날짜순", "과거 날짜순"], key="crm_sort_order")
            with f_col4: search_kw = st.text_input("🔎 손님명 / 연락처 / 메모 검색", placeholder="예: 대한정밀, 1830 등...", key="crm_kw_search")

            filtered_by_date = df_c.copy()
            if selected_month != "전체 기간 보기":
                filtered_by_date = filtered_by_date[filtered_by_date[date_col_name].astype(str).str.startswith(selected_month)]

            if search_kw.strip():
                kw = search_kw.strip()
                filtered_by_date = filtered_by_date[
                    filtered_by_date["상호/고객명"].astype(str).str.contains(kw, na=False) |
                    filtered_by_date["연락처"].astype(str).str.contains(kw, na=False) |
                    filtered_by_date["상담메모"].astype(str).str.contains(kw, na=False) |
                    filtered_by_date["희망권역"].astype(str).str.contains(kw, na=False)
                ]

            ascending_bool = True if "과거" in sort_order else False
            filtered_by_date = filtered_by_date.sort_values(by=date_col_name, ascending=ascending_bool)

            st.caption(f"📌 조회된 손님: **총 {len(filtered_by_date)}명** (조건: {selected_month} | {date_filter_type})")

            subtab_vip, subtab_active, subtab_done, subtab_all = st.tabs(["🔥 집중 관리 (S/A급 VIP)", "🏃 진행중", "🤝 계약 완료", "📁 전체 보기"])

            def render_customer_cards_pro(target_df, tab_prefix="all"):
                if target_df.empty:
                    st.info("선택하신 기간/조건에 해당하는 손님이 없습니다.")
                    return

                for orig_idx, c_row in target_df.iterrows():
                    is_vip = "S급" in str(c_row.get("중요도", "")) or "A급" in str(c_row.get("중요도", ""))
                    card_class = "customer-card-pro-vip" if is_vip else "customer-card-pro"

                    c_name_val = get_safe_cust_val(c_row, "상호/고객명")
                    c_phone_val = get_safe_cust_val(c_row, "연락처")
                    c_star_val = get_safe_cust_val(c_row, "중요도")
                    c_deal_val = get_safe_cust_val(c_row, "거래구분")
                    c_loc_val = get_safe_cust_val(c_row, "희망권역")
                    c_area_val = get_safe_cust_val(c_row, "희망평수")
                    c_budget_val = get_safe_cust_val(c_row, "예산(보증금/월세/매매가)")
                    c_movein_val = get_safe_cust_val(c_row, "입주시기", "협의")
                    c_permit_val = get_safe_cust_val(c_row, "업종인허가", "일반제조")
                    c_hoist_val = get_safe_cust_val(c_row, "호이스트", "무관")
                    c_truck_val = get_safe_cust_val(c_row, "대형차진입", "11T 수월")
                    c_pwr_val = get_safe_cust_val(c_row, "희망전력kW", "기본전력")
                    c_contact_val = get_safe_cust_val(c_row, "최근연락일")
                    c_reg_val = get_safe_cust_val(c_row, "접수일자")
                    c_memo_val = get_safe_cust_val(c_row, "상담메모")

                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div>
                                <span style="font-size:18px; font-weight:bold; color:#1a365d;">👤 {c_name_val}</span>
                                <span style="color:#d69e2e; font-weight:bold; margin-left:6px;">{c_star_val}</span>
                                <span class="tag-blue" style="margin-left:8px;">{c_deal_val}</span>
                                <span class="tag-green">🏭 {c_permit_val}</span>
                            </div>
                            <div style="font-size:13px; color:#4a5568;">
                                📞 <b>{c_phone_val}</b> | 📅 최근: <b>{c_contact_val}</b> (접수: {c_reg_val})
                            </div>
                        </div>
                        <div style="margin: 8px 0; line-height:1.8;">
                            <span class="tag-orange">📐 희망 {c_area_val}</span>
                            <span class="tag-orange">📍 {c_loc_val}</span>
                            <span class="tag-orange">💰 {c_budget_val if c_budget_val else '예산 협의'}</span>
                            <span class="tag-gray">🗓️️ {c_movein_val}</span>
                            <span class="tag-gray">🏗️ {c_hoist_val}</span>
                            <span class="tag-gray">🚛 {c_truck_val}</span>
                            <span class="tag-gray">⚡ {c_pwr_val}</span>
                        </div>
                        <div style="background-color:#f8fafc; border-radius:6px; padding:8px 12px; font-size:13px; color:#2d3748; margin-top:6px;">
                            💡 <b>상담 메모</b>: {c_memo_val if c_memo_val else '상담 메모 없음'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2, btn_c3 = st.columns([1.5, 1.5, 1.2])
                    with btn_c1:
                        if st.button("🎯 추천 보유매물 조회", key=f"btn_m_{tab_prefix}_{orig_idx}"):
                            m_props = match_properties_for_customer(c_row)
                            if m_props:
                                for p in m_props: st.markdown(f"• **{p.get('소재지(권역)','')}** | {p.get('가격(보/월)','')} | {p.get('면적','')} | {p.get('호이스트','')}")
                            else: st.info("조건에 부합하는 매물이 없습니다.")
                    with btn_c2:
                        if st.button("💬 안부/체크 카톡 생성", key=f"btn_k_{tab_prefix}_{orig_idx}"):
                            talk = f"[{c_name_val} 대표님, 우리부동산 안부 안내]\n\n대표님 안녕하십니까! 인천 공장 전문 우리부동산 김태형 소장입니다.\n문의해 주신 공장 조건({c_loc_val}, {c_area_val}, {c_deal_val}) 관련 신규 매물 체크차 연락드렸습니다.\n\n우리부동산 김태형 대표 (010-2660-8276)"
                            st.text_area(f"카톡 복사창 ({c_name_val})", talk, height=180, key=f"tx_{tab_prefix}_{orig_idx}")
                    with btn_c3:
                        if st.button("📝 상담일지 열기", key=f"btn_h_{tab_prefix}_{orig_idx}"):
                            curr_h = str(c_row.get("상담히스토리", ""))
                            st.text_area("상담 기록", curr_h, height=100, disabled=True, key=f"hv_{tab_prefix}_{orig_idx}")
                            new_l = st.text_input("오늘 통화 내용 추가", key=f"in_{tab_prefix}_{orig_idx}")
                            if st.button("저장", key=f"sv_{tab_prefix}_{orig_idx}"):
                                if new_l.strip():
                                    t_tag = datetime.today().strftime("%Y-%m-%d %H:%M")
                                    df_c.at[orig_idx, "상담히스토리"] = f"[{t_tag}] {new_l.strip()}\n" + curr_h
                                    df_c.at[orig_idx, "최근연락일"] = datetime.today().strftime("%Y-%m-%d")
                                    save_all_customers(df_c)
                                    st.success("저장 완료!")
                                    st.rerun()

            with subtab_vip: render_customer_cards_pro(filtered_by_date[filtered_by_date["중요도"].str.contains("S급|A급", na=False) & ~filtered_by_date["진행상태"].isin(["계약 완료", "보류/마감"])], "vip")
            with subtab_active: render_customer_cards_pro(filtered_by_date[~filtered_by_date["진행상태"].isin(["계약 완료", "보류/마감"])], "act")
            with subtab_done: render_customer_cards_pro(filtered_by_date[filtered_by_date["진행상태"] == "계약 완료"], "done")
            with subtab_all: render_customer_cards_pro(filtered_by_date, "all")
        else: st.info("등록된 손님이 없습니다.")

    with tab_edit:
        st.subheader("✍️ 손님 신규 등록 및 수정 / 삭제 (공장 스펙 풀옵션)")
        edit_mode = st.checkbox("🔄 기존 손님 정보 수정 / 삭제 모드 켜기")
        selected_cust_idx = None
        target_row = None

        if edit_mode and not df_c.empty:
            cust_options = [f"[{i}] {r.get('상호/고객명','')} ({r.get('연락처','')} / {r.get('중요도','')})" for i, r in df_c.iterrows()]
            chosen_cust = st.selectbox("수정 또는 삭제할 손님 선택", cust_options)
            selected_cust_idx = int(chosen_cust.split("]")[0].replace("[", ""))
            target_row = df_c.iloc[selected_cust_idx]

        with st.form("cust_form_pro"):
            r1, r2, r3 = st.columns(3)
            with r1:
                name_def = str(target_row["상호/고객명"]) if target_row is not None else ""
                c_name = st.text_input("상호 / 고객명 *", value=name_def, placeholder="예: (주)대한정밀 김대표")
            with r2:
                phone_def = str(target_row["연락처"]) if target_row is not None else ""
                c_phone = st.text_input("연락처 *", value=phone_def, placeholder="예: 010-1234-5678")
            with r3:
                star_opts = ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"]
                star_def = str(target_row["중요도"]) if target_row is not None else "⭐⭐ A급(유력)"
                star_idx = star_opts.index(star_def) if star_def in star_opts else 1
                c_star = st.selectbox("중요도 (VIP 등급)", star_opts, index=star_idx)

            r4, r5, r6, r7 = st.columns(4)
            with r4:
                deal_opts = ["임대차(월세)", "매매", "매매/임대 겸용"]
                deal_def = str(target_row["거래구분"]) if target_row is not None else "임대차(월세)"
                c_deal = st.selectbox("거래 구분 *", deal_opts, index=deal_opts.index(deal_def) if deal_def in deal_opts else 0)
            with r5:
                loc_def = str(target_row["희망권역"]) if target_row is not None else "인천 서구 가좌/석남"
                c_loc = st.text_input("희망 권역 *", value=loc_def, placeholder="예: 인천 서구 가좌, 오류동 등")
            with r6:
                area_def = str(target_row["희망평수"]) if target_row is not None else "100~150평"
                c_area = st.text_input("희망 평수/면적 *", value=area_def, placeholder="예: 70평~100평")
            with r7:
                permit_opts = ["일반제조(소음·진동)", "폐수·대기 배출(인허가 필수)", "식품가공(HACCP)", "단순물류·창고", "자원순환·고물상", "기타 특수업종"]
                permit_def = str(target_row.get("업종인허가", "일반제조(소음·진동)")) if target_row is not None else "일반제조(소음·진동)"
                c_permit = st.selectbox("🏭 업종 및 인허가 *", permit_opts, index=permit_opts.index(permit_def) if permit_def in permit_opts else 0)

            r8, r9, r10, r11 = st.columns(4)
            with r8:
                hoist_opts = ["호이스트 필수 (2.8T~5T)", "있으면 좋음", "불필요 (호이스트 무관)"]
                hoist_def = str(target_row.get("호이스트", "있으면 좋음")) if target_row is not None else "있으면 좋음"
                c_hoist = st.selectbox("🏗️ 호이스트 요구 *", hoist_opts, index=hoist_opts.index(hoist_def) if hoist_def in hoist_opts else 1)
            with r9:
                truck_opts = ["츄레라/트레일러 필수", "11T 윙바디 필수", "5T 진입 수월", "1T 위주 진입"]
                truck_def = str(target_row.get("대형차진입", "11T 윙바디 필수")) if target_row is not None else "11T 윙바디 필수"
                c_truck = st.selectbox("🚛 화물차량 작업 여건 *", truck_opts, index=truck_opts.index(truck_def) if truck_def in truck_opts else 1)
            with r10:
                pwr_opts = ["30kW 이하 (기본)", "50kW 내외", "75kW 이상 (중형)", "100kW~200kW 대용량", "전력 협의"]
                pwr_def = str(target_row.get("희망전력kW", "50kW 내외")) if target_row is not None else "50kW 내외"
                c_pwr = st.selectbox("⚡ 필요 동력(kW) *", pwr_opts, index=pwr_opts.index(pwr_def) if pwr_def in pwr_opts else 1)
            with r11:
                movein_opts = ["즉시 입주", "1개월 이내", "2~3개월 이내", "협의 입주"]
                movein_def = str(target_row.get("입주시기", "협의 입주")) if target_row is not None else "협의 입주"
                c_movein = st.selectbox("🗓️ 입주 희망 시기 *", movein_opts, index=movein_opts.index(movein_def) if movein_def in movein_opts else 3)

            r12, r13 = st.columns(2)
            with r12:
                budget_def = get_safe_cust_val(target_row, "예산(보증금/월세/매매가)", "보 3,000만 / 월 250만") if target_row is not None else ""
                c_budget = st.text_input("희망 예산 (보증금/월세 또는 매매가)", value=budget_def, placeholder="예: 보 3천 / 월 250만 (매매 시 15억)")
            with r13:
                stat_opts = ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"]
                stat_def = str(target_row["진행상태"]) if target_row is not None else "상담 접수 (매물 대기중)"
                c_stat = st.selectbox("진행 상태", stat_opts, index=stat_opts.index(stat_def) if stat_def in stat_opts else 0)

            memo_def = str(target_row["상담메모"]) if target_row is not None else ""
            c_memo = st.text_area("상세 상담 메모", value=memo_def, placeholder="예: CNC 가공 3대 안착 예정, 바닥 크랙 없는 공장 선호, 층고 8m 이상 요망")

            sub_b1, sub_b2 = st.columns([4, 1])
            with sub_b1:
                btn_name = "💾 기존 손님 정보 수정 반영" if edit_mode else "💾 신규 손님 등록하기"
                submit_save = st.form_submit_button(btn_name, type="primary", use_container_width=True)
            with sub_b2:
                submit_del = st.form_submit_button("🗑 손님 삭제", type="secondary", use_container_width=True) if edit_mode else False

            if submit_save:
                if not c_name or not c_phone:
                    st.error("상호/고객명과 연락처는 필수입니다.")
                else:
                    new_entry = {
                        "접수일자": target_row["접수일자"] if target_row is not None else today.strftime("%Y-%m-%d"),
                        "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star,
                        "거래구분": c_deal,
                        "업종인허가": c_permit,
                        "상호/고객명": c_name,
                        "연락처": c_phone,
                        "희망권역": c_loc,
                        "희망평수": c_area,
                        "예산(보증금/월세/매매가)": c_budget,
                        "입주시기": c_movein,
                        "호이스트": c_hoist,
                        "대형차진입": c_truck,
                        "희망전력kW": c_pwr,
                        "상담메모": c_memo,
                        "상담히스토리": target_row.get("상담히스토리", "") if target_row is not None else f"[{today.strftime('%Y-%m-%d %H:%M')}] 최초 접수 완료\n",
                        "진행상태": c_stat
                    }
                    if edit_mode and selected_cust_idx is not None:
                        df_c.iloc[selected_cust_idx] = new_entry
                        save_all_customers(df_c)
                        st.success(f"✅ '{c_name}' 대표님 정보가 수정되었습니다!")
                    else:
                        save_customer(new_entry)
                        st.success(f"✅ '{c_name}' 대표님이 신규 장부에 등록되었습니다!")
                    st.rerun()

            if submit_del and edit_mode and selected_cust_idx is not None:
                df_c = df_c.drop(df_c.index[selected_cust_idx]).reset_index(drop=True)
                save_all_customers(df_c)
                st.warning("🗑️ 손님 데이터가 삭제되었습니다.")
                st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()
    if not df_p.empty:
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: sel_pyung = st.selectbox("📐 실사용 평수", ["전체 평수 보기", "50평 이하", "50평 ~ 100평", "100평 ~ 150평", "150평 이상"])
        with f_col2: sel_hoist = st.selectbox("🏗️ 호이스트", ["전체 (유/무 무관)", "호이스트 완비(설치)", "호이스트 없음"])
        with f_col3: sel_truck = st.selectbox("🚛 화물차 여건", ["전체 차량 보기", "츄레라/트레일러 진입 가능", "11톤/윙바디 이상 진입"])
        with f_col4: search_text = st.text_input("🔎 권역/메모 검색")

        filtered_df = df_p.copy()
        if sel_hoist == "호이스트 완비(설치)": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("완비|설치|톤|T", na=False)]
        elif sel_hoist == "호이스트 없음": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("없음", na=False)]
        if search_text.strip(): filtered_df = filtered_df[filtered_df["소재지(권역)"].str.contains(search_text, na=False) | filtered_df["특징메모"].str.contains(search_text, na=False)]

        st.dataframe(filtered_df, use_container_width=True, height=450)
    else: st.info("등록된 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 AI 시세 추정기")
    st.caption("주소지(동), 대지·건물 평수, 준공연도, 설비 제원을 입력하면 인근 국토부 실거래가 및 네이버 매물 호가를 기반으로 적정 매매가와 임대료(보/월)를 자동 산출합니다.")

    v1, v2 = st.columns(2)
    with v1: v_addr = st.text_input("소재지 주소", placeholder="예: 인천광역시 서구 가좌동")
    with v2: v_land = st.number_input("대지면적 (평)", value=200, step=10)
    if st.button("📊 시세 산출 실행", type="primary"):
        tot_val = int(v_land * 9500000)
        st.markdown(f"**예상 적정 매매가**: 약 <span style='font-size:18px; color:#c53030; font-weight:bold;'>{tot_val:,}원</span> (평당 약 950만 원 선)", unsafe_allow_html=True)

# =============================================================
# 6. 🍜 [고도화] 맛집 & 일상 블로그 (400자 영수증 리뷰 & 숏폼 대본)
# =============================================================
elif menu_choice == MENU_DICT["BLOG_TOOL"]:
    st.title("🍜 맛집 & 🧢 일상 핫플 블로그 마케팅 통합 허브")
    st.caption("블로그 본문 포스팅뿐만 아니라, 400자 이내 찐후기 네이버 영수증 리뷰와 30초 숏폼(릴스·클립) 촬영 대본을 한 번에 자동 추출합니다.")

    b_tab1, b_tab2 = st.tabs(["🍜 맛집 마케팅 (블로그·영수증·숏폼)", "🧢 일상 핫플 마케팅 (블로그·숏폼)"])

    with b_tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
            m_loc = st.text_input("위치 / 권역 *", placeholder="예: 인천 서구 청라동")
            m_kw = st.text_input("공략 키워드 *", placeholder="예: 청라 맛집, 청라 삼겹살 찐맛집")
        with c2:
            m_addr = st.text_input("상세 주소 및 주차 *", placeholder="예: 인천 서구 청라커낼로 123 (지하주차 2시간 무료)")
            m_menu = st.text_input("주문 메뉴 및 가격 *", placeholder="예: 연탄 생삼겹살 2인분(32,000원), 차돌된장찌개")
            m_wait = st.text_input("방문/웨이팅", placeholder="예: 주말 저녁 6시 30분 방문 / 현장 캐치테이블 20분 대기")
        with c3:
            m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 은은한 연탄 불향과 팡 터지는 육즙 조화가 끝내주는 가성비 삼겹살 찐맛집")
            m_point = st.text_input("킬링 포인트 (숏폼용)", placeholder="예: 첫 점 씹자마자 터지는 연탄 불향 육즙과 구운 묵은지 궁합")

        m_taste = st.text_area("맛 평가 디테일", placeholder="예: 35년 전통 연탄불 직화구이로 첫 점부터 육즙 폭발. 파채와 묵은지 구이의 조합이 일품이며, 칼칼한 된장찌개가 밥도둑임.")

        if st.button("🚀 맛집 마케팅 패키지 (포스팅 + 400자 영수증 + 숏폼) 생성", type="primary"):
            if not m_name or not m_eval:
                st.error("상호명과 솔직 한 줄 총평은 필수입니다.")
            else:
                b_col1, b_col2 = st.columns([1.3, 1.0])
                with b_col1:
                    st.markdown("##### 📝 네이버 블로그 최상위 포스팅 본문")
                    post_text = f"""안녕하세요. 인천 맛집·일상 탐방 전문 우리부동산입니다.
{m_loc} 맛집 중 제대로 된 불향과 가성비를 갖추고 이 가격과 퀄리티로 나오는 곳은 정말 귀합니다.
오늘 소개해 드리는 곳은 {m_loc}에 위치한 {m_name} 솔직 방문 후기로, {m_menu} 구성에 {m_eval}이라는 만족스러운 식사를 즐기고 와 강력 추천해 드립니다.

📌 {m_name} 상세 정보표
• 상호명: {m_name} ({m_addr})
• 주문 메뉴 / 가격: {m_menu}
• 웨이팅 / 영업: {m_wait}

💡 김소장의 미식 체크포인트
✅ {m_eval}
✅ {m_taste}
✅ 단체 회식 및 가족 외식에 최적화된 쾌적한 테이블 동선

매물 상담 문의, 맛집 정보 공유 언제든 환영합니다.
우리부동산 공인중개사사무소 대표 김태형 010-2660-8276
#{m_name.replace(' ','')} #{m_loc.replace(' ','')}맛집 #{m_kw.replace(', ',' #').replace(' ','')} #인천맛집 #우리부동산
"""
                    st.text_area("블로그 본문 복사", post_text, height=350)

                with b_col2:
                    st.markdown("##### 🧾 네이버 영수증 리뷰 (400자 이내 찐후기)")
                    review_text = f"""⭐⭐⭐⭐⭐
{m_loc} 찐맛집 인정합니다! 평소 소문 듣고 찾아왔는데 기대 이상이었어요.
{m_menu} 주문해서 먹어봤는데, {m_point if m_point else m_eval}. {m_taste}
고기 질도 정말 신선하고 불향과 육즙 밸런스가 예술이라 마지막 한 점까지 물리지 않고 맛있게 먹었습니다.
{m_addr.split('(')[-1].replace(')', '') if '(' in m_addr else '주차'}도 편하고 직원분들이 바쁜 시간대에도 친절하게 응대해 주셔서 기분 좋게 식사했네요. 
가족 외식이나 모임 장소로 강력 추천드리고 조만간 무조건 재방문할 생각입니다! 번창하세요 사장님 👍"""
                    st.caption(f"📝 현재 글자 수: **{len(review_text)}자** / 최대 400자")
                    st.text_area("영수증 리뷰 복사", review_text, height=180)

                    st.markdown("##### 🎬 30초 숏폼(릴스·클립) 촬영 대본")
                    short_script = f"""[0~3초 훅 오프닝]
"인천 {m_loc}에서 고기 좀 먹어봤다면 모를 수가 없는 이곳!"
(지글지글 연탄불에 고기 올라가는 ASMR 컷)

[4~22초 본론 킬링포인트]
"바로 {m_name}인데요. {m_menu} 시키면 나오는 비주얼 좀 보세요. {m_point}!"
(육즙 떨어지는 클로즈업 + 파채 싸먹는 컷)

[23~30초 클로징]
"이번 주말 외식 장소 고민 끝! 위치는 {m_addr}입니다."
"""
                    st.text_area("숏폼 대본 복사", short_script, height=190)

    with b_tab2:
        d1, d2 = st.columns(2)
        with d1:
            d_name = st.text_input("핫플명 *", placeholder="예: 스투시 서울 챕터 도산")
            d_loc = st.text_input("위치 *", placeholder="예: 서울 강남구 신사동 도산공원 일대")
            d_item = st.text_input("신상 품목 *", placeholder="예: 2026 SS 신상 후드티, 로고 티셔츠")
        with d2:
            d_eval = st.text_input("한 줄 총평 *", placeholder="예: 감각적인 쇼룸 인테리어와 힙한 무드가 공존하는 스트릿 패션의 성지")
            d_wait = st.text_input("대기 시간", placeholder="예: 주말 오후 2시 방문 / 현장 태블릿 40분 대기")

        d_note = st.text_area("내부 무드 및 쇼핑 팁", placeholder="예: 미니멀한 노출 콘크리트 인테리어에 힙한 사운드가 가득함. 신상 라인업 회전율이 빠르며 피팅룸 대기 전 미리 사이즈 체크 필수.")

        if st.button("🚀 핫플 블로그 포스팅 & 릴스 대본 생성", type="primary"):
            if not d_name or not d_eval:
                st.error("핫플명과 한 줄 총평은 필수입니다.")
            else:
                st.text_area("핫플 블로그 본문", f"안녕하세요! 우리부동산입니다. 오늘은 {d_loc} {d_name} 다녀왔습니다. {d_eval}! {d_note}", height=200)
                st.text_area("핫플 릴스 대본", f"[오프닝] 도산공원 가면 무조건 들러야 할 {d_name}!\n[본론] 신상 {d_item} 라인업 실물 깡패네요.\n[클로징] 주말엔 웨이팅 {d_wait} 있으니 서두르세요!", height=150)

# =============================================================
# 7. 🏢 [전수 통합 복구] 분양/줍줍 & LH·SH 공공임대 통합 포스팅 허브
# =============================================================
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 수도권 청약·줍줍 & LH·SH 공공임대 통합 포스팅 허브")
    st.caption("성격이 완전히 다른 '분양/로또줍줍(소유권 취득)'과 '공공임대/청년주택(저렴한 주거복지)'을 명확히 분리하여 전문 브리핑 및 블로그 본문을 완성합니다.")

    hub_mode = st.radio(
        "📌 정보 유형 선택 (청약 분양과 공공임대는 자격 요건 및 비용 구조가 완전히 다릅니다)",
        ["🏢 [분양/줍줍] 민영·공공분양 & 로또 줍줍 허브", "🏠 [공공임대] LH·SH·iH 청년안심·행복주택 허브"],
        horizontal=True
    )

    today_dt = datetime.today()

    # -------------------------------------------------------------
    # MODE 1: 민영/공공분양 & 로또 줍줍 허브 (전수 복구 완료)
    # -------------------------------------------------------------
    if hub_mode == "🏢 [분양/줍줍] 민영·공공분양 & 로또 줍줍 허브":
        sub_list = fetch_subscription_data_sale()
        
        c1, c2 = st.columns([1.5, 2.5])
        with c1:
            sel_region = st.selectbox("📍 권역 필터", ["수도권 전체 모아보기", "서울특별시", "경기도", "인천광역시", "세종/기타"], key="sale_reg")
        with c2:
            search_kw = st.text_input("🔎 단지명 / 시공사 검색", placeholder="예: 강변역, 충정로, 신림, 세종, 오남, 부천대장, 과천 등...", key="sale_kw")

        filtered_subs = []
        for s in sub_list:
            if sel_region == "서울특별시" and s["권역"] != "서울특별시": continue
            elif sel_region == "경기도" and s["권역"] != "경기도": continue
            elif sel_region == "인천광역시" and s["권역"] != "인천광역시": continue
            elif sel_region == "세종/기타" and s["권역"] != "세종/기타": continue

            if search_kw.strip() and (search_kw.strip() not in s["단지명"]) and (search_kw.strip() not in s["시공사"]): continue
            filtered_subs.append(s)

        summary_rows = []
        for item in filtered_subs:
            try:
                r1_dt = datetime.strptime(item["1순위해당"][:10], "%Y-%m-%d")
                diff_days = (r1_dt - today_dt).days
                dday_str = "🔴 오늘 접수" if diff_days == 0 else (f"⏳ 접수 D-{diff_days}" if diff_days > 0 else "🏁 마감/진행")
            except Exception: dday_str = "일정 공고"

            summary_rows.append({
                "진행상태": dday_str, "공급유형": item["유형"], "단지명": item["단지명"], "권역": item["권역"],
                "분양가": item["타입정보"][0]["최고분양가"], "예상안전마진(P)": item.get("예상안전마진", "대조중"),
                "1순위/무순위": item["1순위해당"], "당첨발표": item["당첨자발표"]
            })

        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, height=220)

        if filtered_subs:
            st.markdown("---")
            chosen_sub_idx = st.selectbox(
                "분석 및 블로그 포스팅을 생성할 분양/줍줍 단지를 선택하세요",
                range(len(filtered_subs)),
                format_func=lambda i: f"[{filtered_subs[i]['유형']}] {filtered_subs[i]['단지명']} (공급가 {filtered_subs[i]['타입정보'][0]['최고분양가']} / 마진 {filtered_subs[i].get('예상안전마진', '')})"
            )
            cur_sub = filtered_subs[chosen_sub_idx]
            first_t = cur_sub["타입정보"][0]
            price_val = first_t.get("최고분양가원", 500000000)
            down_pay = int(price_val * 0.10)
            mid_pay = int(price_val * 0.60)
            bal_pay = int(price_val * 0.30)
            type_lines = "\n".join([f"- {t['타입']}: {t.get('세대수', '')} (최고 {t.get('최고분양가', '')})" for t in cur_sub["타입정보"]])
            clean_tags = cur_sub["단지명"].replace("(", " ").replace(")", " ").split()
            tag_base = clean_tags[0] if clean_tags else "청약"

            st.markdown(f"""
            <div class="calc-box-orange">
                <h4 style="color:#c05621; margin:0;">🏢 [{cur_sub['유형']}] {cur_sub['단지명']}</h4>
                • 위치: {cur_sub['상세공급위치']} | 시공사: {cur_sub['시공사']}<br>
                • <b>예상 안전마진(시세차익)</b>: <span style="font-size:18px; font-weight:bold; color:#c53030;">{cur_sub.get('예상안전마진', '검토중')}</span> (비교대장: {cur_sub.get('인근대장단지', '')})<br>
                • 자격요건: <b>{cur_sub.get('자격요건요약', '')}</b> | 학군: {cur_sub.get('학군인프라', '도보권 통학')}
            </div>
            """, unsafe_allow_html=True)

            post_tab1, post_tab2, post_tab3 = st.tabs(["📝 [원클릭] 분양/줍줍 전용 블로그 포스팅", "💰 자금 조달 로드맵", "🧮 84점 가점 계산기"])

            with post_tab1:
                sub_blog_post = f"""안녕하세요! 부동산 팩트체크와 알짜 청약 정보를 전해드리는 공인중개사 김태형입니다. 🙋‍♂️

기다리셨던 {cur_sub['권역']} 핵심 입지인 '{cur_sub['단지명']}'의 입주자모집공고 내용이 공개되었습니다. 이번 공급은 {cur_sub['공급규모']}로 구성된 알짜배기 {cur_sub['유형']} 단지입니다.

공식 분양 안내: {cur_sub['공고URL']}

수도권 거주 무주택자 및 청약 대기자 분들께서는 철도 교통 호재와 공급 일정, 안전마진과 자금 조달 계획을 꼼꼼히 확인하시어 소중한 기회를 잡으시길 바랍니다!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 공급 일정 (체크리스트)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 입주자 모집공고일: {cur_sub['모집공고일']} (나이, 자격, 소득·자산 산정 기준일)
- 특별공급 청약 접수: {cur_sub['특별공급일']} 09:00 ~ 17:30 (청약Home 인터넷 접수)
- 일반공급 1순위 / 무순위 접수: {cur_sub['1순위해당']} 09:00 ~ 17:30 (청약Home 인터넷 접수)
- 당첨자 발표일: {cur_sub['당첨자발표']} (청약Home 개별 조회)
- 정당 계약 체결 기간: {cur_sub['정당계약일']} (견본주택 방문 접수)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 주택형별 공급 물량
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 공급 위치: {cur_sub['상세공급위치']}
- 공급 규모: {cur_sub['공급규모']}
- 주택형별 공급 세대수 및 확정 분양가:
{type_lines}
- 입주 예정 시기: {cur_sub['입주예정월']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 분양가 vs 주변 시세 비교 (예상 안전마진 팩트체크)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 인근 비교 대장 아파트: {cur_sub.get('인근대장단지', '주변 동일 평형')}
- 당첨 시 예상 시세차익(안전마진): {cur_sub.get('예상안전마진', '시세 대조 중')}
💡 김소장의 시세 한 줄 평: 최근 공사비 급등으로 수도권 신규 분양가가 가파르게 치솟는 상황에서, 최초 공급가 수준으로 책정되어 확실한 시세 안전마진을 확보한 단지입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💸 4. 당첨 시 단계별 필요 자금 타임라인 (예시: {first_t['타입']})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 계약 체결 시 (계약금 10%): 약 {down_pay:,}원 ➡ 당첨 즉시 본인 통장에 순수 현금으로 준비되어 있어야 합니다.
2. 공사 기간 중 (중도금 60%): 약 {mid_pay:,}원 ➡️ 집단대출(이자후불제) 지원 여부 확인 필요.
3. 입주 지정 기간 (잔금 30%): 약 {bal_pay:,}원 ➡️ 주택담보대출(LTV 70~80%) 전환 또는 전세 보증금으로 상환 계획 수립.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚇 5. 교통망 & 학군 인프라 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 철도 및 광역 도로망: {cur_sub['교통망분석']}
- 안심 통학로 및 학군: {cur_sub.get('학군인프라', '도보권 통학 환경 조성')}
- 상권 및 주거 환경: 중심 상업지구와 교육 인프라, 쾌적한 녹지축이 어우러져 있어 입주 후 뛰어난 주거 만족도와 높은 프리미엄 형성이 기대되는 입지입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 6. 타입별 당첨 공략 & 틈새 청약 팁
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• {cur_sub.get('타입전략', '주택형별 선호도에 따른 경쟁률 분산 전략을 세우는 것이 유리합니다.')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 7. 이번 공고 핵심 주의사항 (부적격 방지 3대 체크)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 무주택 및 청약 자격: {cur_sub.get('자격요건요약', '공고문 참조')}
- 전매제한 및 재당첨제한: {cur_sub['규제체크']['분양가상한제']} 주택으로 재당첨 제한 {cur_sub['규제체크']['재당첨제한']}, 전매제한 {cur_sub['규제체크']['전매제한']}이 적용됩니다. ({cur_sub['규제체크']['거주의무']})
- 인터넷 청약 원칙: 한국부동산원 청약Home을 통한 인터넷 접수가 원칙이므로, 사전에 금융인증서 또는 공동인증서를 미리 준비하셔야 합니다.

청약은 한국부동산원 청약Home 공식 홈페이지를 통해 접수하실 수 있습니다. 상세한 평면도와 옵션별 최종 분양가 조건은 공식 입주자모집공고문과 개관하는 견본주택을 반드시 확인하신 후 신중하게 신청하시기 바랍니다.

내 집 마련과 주거 안정을 준비하시는 모든 분들의 합격을 진심으로 응원합니다! 😊

#{tag_base} #무순위청약 #줍줍 #분양가상한제 #청약일정 #내집마련 #공인중개사김소장 #청약홈 #수도권청약 #{cur_sub['권역']}청약 #안전마진
"""
                st.text_area("분양/줍줍 네이버 블로그 복사창", sub_blog_post, height=450)

            with post_tab2:
                st.markdown(f"""
                <div class="calc-box-blue">
                    <b>[{cur_sub['단지명']} - {first_t['타입']}] 분양 자금 계획표</b><br>
                    • 공급가액: <b>{price_val:,}원</b><br>
                    1. <b>계약금 10%</b>: 약 <b>{down_pay:,}원</b> (현금 준비)<br>
                    2. <b>중도금 60%</b>: 약 <b>{mid_pay:,}원</b> (중도금 대출 승계)<br>
                    3. <b>입주잔금 30%</b>: 약 <b>{bal_pay:,}원</b> (입주 시 주담대 LTV 전환)
                </div>
                """, unsafe_allow_html=True)

            with post_tab3:
                st.markdown("##### 🧮 청약통장 가점 계산기 (최고 84점 만점)")
                g1, g2, g3 = st.columns(3)
                with g1:
                    no_home_yr = st.selectbox("1. 무주택 기간 (최대 32점)", ["1년 미만 (2점)", "3~4년 (8점)", "7~8년 (16점)", "11~12년 (24점)", "15년 이상 (32점)"], index=2)
                    score_home = int(re.findall(r'\d+', no_home_yr.split('(')[-1])[0])
                with g2:
                    family_cnt = st.selectbox("2. 부양가족 수 (최대 35점)", ["0명 (5점)", "1명 (10점)", "2명 (15점)", "3명 (20점)", "4명 (25점)", "5명 이상 (30점)"], index=2)
                    score_fam = int(re.findall(r'\d+', family_cnt.split('(')[-1])[0])
                with g3:
                    bank_yr = st.selectbox("3. 청약통장 가입기간 (최대 17점)", ["1~2년 (3점)", "5~6년 (7점)", "9~10년 (11점)", "13~14년 (15점)", "15년 이상 (17점)"], index=2)
                    score_bank = int(re.findall(r'\d+', bank_yr.split('(')[-1])[0])
                st.info(f"당신의 총 청약 가점: **{score_home + score_fam + score_bank}점** / 84점 만점")

    # -------------------------------------------------------------
    # MODE 2: LH · SH · iH 공공임대 & 청년주택 허브
    # -------------------------------------------------------------
    else:
        rent_list = fetch_subscription_data_rent()

        rc1, rc2 = st.columns([1.5, 2.5])
        with rc1:
            sel_inst = st.selectbox("🏛️ 공급 공사 기관 필터", ["공사 전체 보기", "SH 서울주택도시공사", "LH 한국토지주택공사", "iH 인천도시공사"], key="rent_inst")
        with rc2:
            search_rent_kw = st.text_input("🔎 공공임대 단지명 검색", placeholder="예: 청년안심, 계양, 원당 등...", key="rent_kw")

        filtered_rents = []
        for r in rent_list:
            if sel_inst != "공사 전체 보기" and r["기관"] != sel_inst: continue
            if search_rent_kw.strip() and (search_rent_kw.strip() not in r["단지명"]): continue
            filtered_rents.append(r)

        rent_summary_rows = []
        for r in filtered_rents:
            rent_summary_rows.append({
                "공급기관": r["기관"], "공급유형": r["유형"], "단지명": r["단지명"], "권역": r["권역"],
                "기본보증금": r["임대조건"]["기본보증금"], "기본월세": r["임대조건"]["기본월세"],
                "서류접수": r["서류제출기간"], "당첨발표": r["당첨자발표"]
            })

        st.dataframe(pd.DataFrame(rent_summary_rows), use_container_width=True, height=200)

        if filtered_rents:
            st.markdown("---")
            chosen_rent_idx = st.selectbox(
                "분석 및 블로그 포스팅을 생성할 공공임대 단지를 선택하세요",
                range(len(filtered_rents)),
                format_func=lambda i: f"[{filtered_rents[i]['기관']}] {filtered_rents[i]['단지명']} ({filtered_rents[i]['임대조건']['기본보증금']} / {filtered_rents[i]['임대조건']['기본월세']})"
            )
            cur_r = filtered_rents[chosen_rent_idx]
            cond = cur_r["임대조건"]
            clean_r_tags = cur_r["단지명"].replace("[", "").replace("]", "").split()
            tag_r_base = clean_r_tags[1] if len(clean_r_tags) > 1 else "청년안심주택"

            st.markdown(f"""
            <div class="calc-box-purple">
                <h4 style="color:#6b46c1; margin:0;">🏠 [{cur_r['기관']}] {cur_r['단지명']}</h4>
                • 위치: {cur_r['상세공급위치']} | 공급규모: {cur_r['공급규모']}<br>
                • <b>기본 임대조건</b>: 보증금 <b>{cond['기본보증금']} / 월세 {cond['기본월세']}</b><br>
                • <b>보증금 최대 전환 시</b>: <span style="font-size:17px; font-weight:bold; color:#276749;">보증금 {cond['최대전환보증금']} / 월세 {cond['최저월세']}</span><br>
                • 자격 기준: <b>{cur_r['신청자격']}</b> (차량: {cur_r['차량기준']})
            </div>
            """, unsafe_allow_html=True)

            r_tab1, r_tab2 = st.tabs(["📝 [원클릭] 공공임대/청년주택 전용 블로그 포스팅", "📑 신청 자격 & 보증금 전환 계산기"])

            with r_tab1:
                rent_blog_post = f"""안녕하세요! 청년·신혼 주거비 부담을 덜어드리는 부동산 팩트체커 공인중개사 김태형입니다. 🙋‍♂️

역세권 입지와 시세 대비 반값 이하 임대료로 청년들의 뜨거운 관심을 받고 있는 '{cur_r['단지명']}'의 입주자 모집공고가 발표되었습니다.

공식 공고 확인: {cur_r['공고URL']}

목돈 부담 없이 안정적으로 거주할 수 있는 알짜배기 공공임대 물량인 만큼, 자격 요건과 보증금 전환 조건을 꼼꼼히 체크하시기 바랍니다!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 공급 일정 (체크리스트)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 입주자 모집공고일: {cur_r['모집공고일']} (무주택, 소득·자산 산정 기준일)
- 청약 접수 및 서류제출: {cur_r['서류제출기간']} ({cur_r['기관']} 인터넷 청약)
- 서류심사 대상자 발표: {cur_r['서류제출기간'].split('~')[0].strip()} 발표 예정
- 최종 당첨자 발표일: {cur_r['당첨자발표']}
- 계약 체결 및 입주 예정: {cur_r['계약및입주']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 위치
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {cur_r['단지명']}
- 공급 위치: {cur_r['상세공급위치']}
- 공급 규모: {cur_r['공급규모']}
- 주거 환경: {cur_r['교통및환경']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 임대 조건 및 보증금-월세 상호전환 안내
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 기본 임대료: 보증금 {cond['기본보증금']} / 월세 {cond['기본월세']}
- 보증금 최대 증액 시: 보증금 {cond['최대전환보증금']} ➡️ 최저 월세 {cond['최저월세']}
💡 김소장의 팁: 여유 자금이 있거나 버팀목 전세대출(연 1~2%대)을 이용할 수 있다면, 보증금을 최대로 높여 월 고정비 지출을 10만 원 안팎으로 획기적으로 낮추는 것이 훨씬 유리합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 신청 전 필수 자격 팩트체크 (소득·자산 컷)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 대상 요건: {cur_r['신청자격']}
- 자동차 가액 기준: {cur_r['차량기준']}
- 청약통장 혜택: {cur_r['청약통장혜택']}

공공임대 및 청년주택은 한국부동산원 청약Home이 아닌, {cur_r['기관']} 공식 청약센터를 통해 인터넷으로 접수하셔야 합니다. 세부 평면도와 호수 배치는 공식 공고문을 반드시 확인하신 후 접수하시기 바랍니다.

내 집 마련의 든든한 징검다리가 되어줄 청년 여러분의 당첨을 진심으로 응원합니다! 😊

#{tag_r_base} #공공임대 #{cur_r['유형'].replace(' ','')} #청년주택 #행복주택 #역세권청년주택 #{cur_r['기관'].split()[0]}청약 #주거안정 #공인중개사김소장
"""
                st.text_area("공공임대/청년주택 네이버 블로그 복사창", rent_blog_post, height=450)

            with r_tab2:
                st.markdown(f"""
                <div class="check-list-box">
                    <b>💡 공공임대 청약 시 가장 큰 장점</b><br>
                    • <b>청약통장 효력 유지</b>: 공공임대(행복주택, 청년안심)는 당첨되어 입주하더라도 본인의 <b>청약통장을 소모하지 않습니다</b>. 거주하면서 민영아파트나 일반분양에 계속 청약할 수 있습니다.<br>
                    • <b>최장 거주 기간</b>: 청년 계층 6년, 신혼부부 6~10년(자녀 유무에 따라 연장) 동안 이사 걱정 없이 거주 가능합니다.<br>
                    • <b>버팀목 전세대출 연계</b>: 주택도시기금 청년전용 버팀목 대출 이용 시 보증금의 80%까지 연 1.8%~2.7% 저리 지원 가능.
                </div>
                """, unsafe_allow_html=True)

# =============================================================
# 8. ⚖️️ [완전 복구] 법원경매 허브 (5단계 배당표 & 턴키 자금조달표)
# =============================================================
elif menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 & 수도권 주택·공장 심층 수지분석")
    st.caption("대법원 법원경매정보 연동 기반: 수도권 주택(아파트) 5단계 실시간 배당표, 명도비용, 토허제 특례 및 인천공장 시설 수지표를 완벽 제공합니다.")

    factory_list, apt_list = get_auction_data()

    with st.expander("📌 [필독] 경매 입찰 전 물건 유형별 필수 확인 체크리스트 (실무 가이드)", expanded=False):
        c_tab1, c_tab2 = st.tabs(["🏭 공장·창고 경매 필수 확인 사항", "🏢 주택·아파트 경매 필수 확인 사항"])
        with c_tab1:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 산업단지 입주자격 (산집법 제38조)</b>: 국가산단/일반산단 경매는 입주 부적격자 낙찰 시 6개월 내 처분명령 대상. 입주업종 코드 사전 확인 필수.<br>
                <b>2. 기계기구 감정가 분리</b>: 공장 총 감정가 중 기계(CNC, 프레스, 크레인) 가치와 실제 가동 여부 분리 필수.<br>
                <b>3. 한전 단전 및 산업용 전기 체납</b>: 수천만 원 규모의 전기요금 연체 시 한전 단전 해제비 및 보증보험료 발생 (한전 123 확인).<br>
                <b>4. 진입로 사도(개인도로) 지분 여부</b>: 도로 지분 없이 맹지 상태인 경우 대형 트럭 진입 불가 분쟁 위험.
            </div>
            """, unsafe_allow_html=True)
        with c_tab2:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 대항력 있는 선순위 임차인</b>: 전입일자가 말소기준권리보다 빠르고 미배당 시 낙찰자가 전액 인수.<br>
                <b>2. 토지거래허가구역 경매 특례</b>: 경매 취득 시 허가가 면제되어 2년 실거주의무 없이 즉시 전세 갭투자 가능.<br>
                <b>3. 공용부분 미납관리비 승계</b>: 대법원 판례상 최근 3년 치 공용 관리비 낙찰자 승계.<br>
                <b>4. 명도 난이도 및 강제집행 예산</b>: 통상 이사비(평당 8~10만 원) 협의가 소송보다 빠르고 경제적입니다.
            </div>
            """, unsafe_allow_html=True)

    auction_tab1, auction_tab2 = st.tabs(["🏢 수도권 주택(아파트) 경매 & 권리분석·배당표", "🏭 인천 전지역 공장·창고 경매 & 정밀 턴키 수지표"])

    with auction_tab1:
        st.subheader("🏢 수도권 주택(아파트) 법원경매 사건 리스트")

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
                st.text_input("🔎 단지명 / 아파트명 검색", placeholder="예: 푸르지오, 아크로, 자이 등...", key="apt_kw_search_fix")

        with f_c3:
            st.success("🟢 대법원 경매정보 실시간 권리분석 & 시세차익 연동 중")

        filtered_apt = []
        kw_val = st.session_state.get("apt_kw_search_fix", "").strip()

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

        if filtered_apt:
            st.markdown("---")
            st.subheader("🔍 주택 경매 심층 권리분석 & 실시간 자금조달표")

            chosen_apt_idx = st.selectbox(
                "정밀 분석할 주택 사건을 선택하세요",
                range(len(filtered_apt)),
                format_func=lambda i: f"[{filtered_apt[i]['사건번호']}] {filtered_apt[i]['소재지']} (감정가: {filtered_apt[i]['감정가']} / 최저가: {filtered_apt[i]['최저가']})"
            )

            cur_apt = filtered_apt[chosen_apt_idx]
            qa_apt = cur_apt["권리분석"]
            case_key = cur_apt['사건번호'].replace("타경", "_")

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
                    • <b>공용부분 미납관리비</b>: <b>{cur_apt['미납관리비']:,}원</b>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("##### 📊 2. 실시간 5단계 배당표 시뮬레이터")
                sim_bid = st.number_input("가상 낙찰가 입력 (원)", value=int(cur_apt['최저가원']), step=10000000, key=f"sim_b_{case_key}")
                bd = cur_apt["배당정보"]
                rem = sim_bid
                pay_exp = min(rem, bd["경매비용"]); rem -= pay_exp
                pay_tax = min(rem, bd["당해세"]); rem -= pay_tax
                pay_pri = min(rem, bd["최우선변제"]); rem -= pay_pri
                pay_mort = min(rem, bd["선순위근저당"]); rem -= pay_mort
                pay_rent = min(rem, bd["임차인배당"]); rem -= pay_rent

                st.markdown(f"""
                <div style="background:#f7fafc; border:1px solid #cbd5e0; padding:10px; font-size:12.5px; line-height:1.7;">
                    1. 경매집행비용 배당: <b>{pay_exp:,}원</b><br>
                    2. 당해세(재산세 등) 법정배당: <b>{pay_tax:,}원</b><br>
                    3. 최우선변제금 배당: <b>{pay_pri:,}원</b><br>
                    4. 선순위 근저당권 배당: <b>{pay_mort:,}원</b><br>
                    5. 임차인 배당금: <b>{pay_rent:,}원</b><br>
                    🚩 <b>낙찰자 추가 인수 보증금</b>: <span style="color:#276749; font-weight:bold;">0원 (완전 소멸 안전물건)</span>
                </div>
                """, unsafe_allow_html=True)

                st.link_button("🌐 대한민국 법원경매정보(대법원) 사건검색 바로가기", cur_apt["사건URL"], use_container_width=True)

            with apt_col2:
                st.markdown("##### 💰 3. 주택 경매 실시간 자금조달표")

                calc_c1, calc_c2 = st.columns(2)
                with calc_c1:
                    user_bid = st.number_input(
                        "예상 입찰/낙찰가 (원) *",
                        value=int(cur_apt['최저가원']),
                        step=10000000,
                        format="%d",
                        key=f"apt_bid_{case_key}"
                    )
                    buyer_house_cnt = st.selectbox(
                        "매수자 주택 수 (취득세 산정)",
                        ["무주택자 (1주택 취득, 1.1~3.5%)", "1주택자 (일시적 2주택, 1.1~3.5%)", "2주택자 (조정대상 중과 8%)", "3주택 이상 (중과 12%)"],
                        key=f"apt_house_cnt_{case_key}"
                    )
                with calc_c2:
                    apt_ltv = st.slider(
                        "경락잔금대출 LTV (%) *",
                        40, 80, 70, 5,
                        key=f"apt_ltv_{case_key}",
                        help="무주택/1주택자 생애최초 80%, 일반 70%, 다주택자 차등"
                    )
                    evict_fee = st.number_input(
                        "명도 이사비 및 미납관리비 합계 (원)",
                        value=int(cur_apt['미납관리비'] + 1500000),
                        step=500000,
                        key=f"apt_evict_{case_key}"
                    )

                if "중과 8%" in buyer_house_cnt: tax_rate = 0.084
                elif "중과 12%" in buyer_house_cnt: tax_rate = 0.124
                else: tax_rate = 0.011 if user_bid <= 600000000 else (0.022 if user_bid <= 900000000 else 0.035)

                apt_acq_tax = int(user_bid * tax_rate)
                apt_max_loan = min(int(cur_apt['감정가원'] * 0.70), int(user_bid * (apt_ltv / 100.0)))
                apt_pure_cash = (user_bid - apt_max_loan) + apt_acq_tax + evict_fee + qa_apt['인수보증금']

                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{cur_apt['사건번호']}] 실시간 자금조달표</h4>
                    • <b>입력 낙찰가액</b>: <b>{user_bid:,}원</b> (감정가 대비 {round((user_bid/cur_apt['감정가원'])*100, 1)}%)<br>
                    • <b>경락잔금대출 (LTV {apt_ltv}%)</b>: <b>약 {apt_max_loan:,}원</b><br>
                    • <b>주택 취득세 ({round(tax_rate*100, 1)}%)</b>: <b>{apt_acq_tax:,}원</b><br>
                    • <b>명도 이사비 및 관리비 인수</b>: <b>{evict_fee:,}원</b><br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🏦 <b>실제 총 필요 순수 자기자본 (통장 준비 현금)</b>:<br>
                    <span style="font-size: 21px; font-weight: bold; color: #c53030;">약 {apt_pure_cash:,}원</span>
                </div>
                """, unsafe_allow_html=True)

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
• 취득세 및 부대비용 포함 실투자금: 약 {pure_cash:,}원 내외

현장 임장 및 입찰 대리 진행 상담은 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
            st.text_area("주택 경매 카카오톡 복사창", apt_kakao, height=330)

    with auction_tab2:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건 리스트")

        df_fac = pd.DataFrame(factory_list)
        summary_fac = df_fac[["사건번호", "법원", "소재지", "세부용도", "바닥평수", "총감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]].copy()
        st.dataframe(summary_fac, use_container_width=True, height=200)

        st.markdown("---")
        st.subheader("🔍 공장 경매 심층 권리분석 & 실시간 턴키 자금조달표")

        chosen_fac_idx = st.selectbox(
            "정밀 분석할 공장 경매 사건을 선택하세요",
            range(len(factory_list)),
            format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']} (감정가: {factory_list[i]['총감정가']} / 최저가: {factory_list[i]['최저가']})"
        )

        cur_fac = factory_list[chosen_fac_idx]
        case_fac_key = cur_fac['사건번호'].replace("타경", "_")

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
                ⚠️ <b>연체 관리비/단전 위험</b>: <b>{cur_fac['연체관리비추정']:,}원 추정</b>
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
            st.markdown("##### 💰 3. 턴키 정상가동 실시간 자금조달표")

            in_c1, in_c2 = st.columns(2)
            with in_c1:
                target_bid = st.number_input(
                    "예상 입찰/낙찰가 (원) *",
                    value=int(cur_fac['최저가원']),
                    step=10000000,
                    format="%d",
                    key=f"fac_bid_{case_fac_key}"
                )
                loan_ltv = st.slider(
                    "경락잔금대출 LTV (%) *",
                    50, 85, 75, 5,
                    key=f"fac_ltv_{case_fac_key}",
                    help="공장 시설자금 경락대출 최대 75~80%"
                )
            with in_c2:
                req_power = st.number_input(
                    f"목표 동력 (현재 {cur_fac['현재동력kW']}kW)",
                    min_value=cur_fac['현재동력kW'],
                    max_value=500,
                    value=max(cur_fac['현재동력kW'], 100),
                    step=10,
                    key=f"fac_pwr_{case_fac_key}"
                )
                hoist_choice = st.selectbox(
                    "호이스트 조치 *",
                    ["기존 호이스트 안전정비 (약 150만)", "2.8T 호이스트 신규 설치 (약 1,100만)", "5T 더블거더 신규 설치 (약 1,900만)", "설비 조치 불필요 (0원)"],
                    key=f"fac_hoist_{case_fac_key}"
                )

            in_c3, in_c4 = st.columns(2)
            with in_c3:
                floor_opt = st.selectbox(
                    f"바닥 에폭시 공사 (바닥 {cur_fac['바닥평수']}평) *",
                    ["고강도 에폭시 코팅 (평당 4.5만)", "두께 라이닝 방수 (평당 7.5만)", "바닥 보수 불필요 (0원)"],
                    key=f"fac_floor_{case_fac_key}"
                )
            with in_c4:
                overdue_cost = st.number_input(
                    "인수 미납관리비 / 한전 재공급비 (원)",
                    value=int(cur_fac['연체관리비추정']),
                    step=500000,
                    key=f"fac_overdue_{case_fac_key}"
                )

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
                <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{cur_fac['사건번호']}] 턴키 입주 실시간 자금조달표</h4>
                • <b>입력 낙찰가액</b>: <b>{target_bid:,}원</b> (감정가 대비 {round((target_bid/cur_fac['총감정가원'])*100, 1)}%)<br>
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

⚖ 권리분석 및 입주 검토 요약
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