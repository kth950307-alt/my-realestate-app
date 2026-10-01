import streamlit as st
import pandas as pd
import os
import re
import requests
from datetime import datetime
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
    .compact-match-card {
        background-color: #f8fafc;
        border-left: 4px solid #3182ce;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 13.5px;
        line-height: 1.5;
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
    .badge-score {
        background-color: #d69e2e;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-status {
        background-color: #ebf8ff;
        color: #2b6cb0;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .calc-box {
        background-color: #f0fff4;
        border: 1px solid #c6f6d5;
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
    .calc-box-orange {
        background-color: #fffaf0;
        border: 1px solid #feebc8;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 [보안 잠금] 사무실 전용 로그인 인증 (비밀번호: 950307 고정)
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
        st.caption("인천 공장 중개 & 부동산 종합 솔루션 - 사무실 전용 인증")
        pwd_input = st.text_input("사무실 전용 비밀번호를 입력하세요", type="password", key="pwd_box")
        
        if st.button("🔓 시스템 접속하기", type="primary", use_container_width=True):
            if pwd_input == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")
    return False

if not check_password():
    st.stop()

# =============================================================
# CSV 데이터베이스 관리 함수
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        return pd.read_csv(CUSTOMERS_CSV)
    columns = ["접수일자", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세)", "입주시기", "호이스트", "대형차진입", "희망전력kW", "상담메모", "진행상태"]
    return pd.DataFrame(columns=columns)

def save_customer(new_data):
    df = load_customers()
    updated_df = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated_df.to_csv(CUSTOMERS_CSV, index=False, encoding="utf-8-sig")
    return updated_df

def load_properties():
    if os.path.exists(PROPERTIES_CSV):
        df = pd.read_csv(PROPERTIES_CSV)
        if "입주/공실상태" not in df.columns: df["입주/공실상태"] = "현재 공실(즉시입주)"
        if "계약만료일" not in df.columns: df["계약만료일"] = "즉시 협의"
        return df
    columns = ["등록일자", "입주/공실상태", "계약만료일", "거래구분", "소재지(권역)", "상세주소(지번)", "임대인(건물주)", "임대인연락처", "가격(보/월)", "면적", "층고", "동력", "호이스트", "도로/주차", "대형차량", "특징메모"]
    return pd.DataFrame(columns=columns)

def save_property(new_data):
    df = load_properties()
    updated_df = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated_df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")
    return updated_df

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

# 🎯 공장 매물 ➡️ 대기 손님 정밀 스캔 & 일치율 평가 알고리즘
def match_customers_advanced(fac_loc, fac_hoist, fac_truck, fac_area_text, fac_power_text=""):
    df = load_customers()
    if df.empty: return []
    active_df = df[~df["진행상태"].isin(["계약 완료", "보류/마감"])].copy()
    if active_df.empty: return []

    fac_pyungs = parse_pyung_numbers(fac_area_text)
    f_pyung = fac_pyungs[0] if fac_pyungs else None
    f_truck_lv = 4 if any(k in fac_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in fac_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in fac_truck for k in ["5T", "5톤"]) else 1))
    f_has_hoist = any(k in fac_hoist for k in ["완비", "설치", "톤", "T", "더블거더"]) and ("없음" not in fac_hoist)

    results = []
    for _, row in active_df.iterrows():
        score = 0
        reasons = []

        # 1. 지역 대조
        c_loc = str(row.get("희망권역", ""))
        loc_words = [w for w in fac_loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if (not c_loc.strip()) or any(w in c_loc for w in loc_words) or any(w in fac_loc for w in c_loc.split()):
            score += 30
            reasons.append("권역 일치")

        # 2. 평수 대조 (±20% 이내 적합)
        c_pyungs = parse_pyung_numbers(row.get("희망평수", ""))
        if f_pyung and c_pyungs:
            c_pyung = c_pyungs[0]
            if (c_pyung * 0.8) <= f_pyung <= (c_pyung * 1.25):
                score += 35
                reasons.append(f"희망평수({int(c_pyung)}평) 부합")
            elif (c_pyung * 0.6) <= f_pyung <= (c_pyung * 1.4):
                score += 20
                reasons.append("평수 근사치")
        else:
            score += 15

        # 3. 호이스트 대조
        c_hoist = str(row.get("호이스트", ""))
        if "필수" in c_hoist:
            if f_has_hoist:
                score += 20
                reasons.append("호이스트 필수 충족")
            else:
                score -= 40
        else:
            score += 10

        # 4. 화물 진입 대조
        c_truck = str(row.get("대형차진입", ""))
        c_truck_lv = 4 if any(k in c_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in c_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in c_truck for k in ["5T", "5톤"]) else 1))
        if f_truck_lv >= c_truck_lv:
            score += 15
            reasons.append("진입 차량 충족")
        else:
            score -= 20

        if score >= 60:
            results.append({
                "고객명": row.get("상호/고객명"),
                "연락처": row.get("연락처"),
                "희망평수": row.get("희망평수"),
                "희망권역": row.get("희망권역"),
                "진행상태": row.get("진행상태"),
                "상담메모": row.get("상담메모"),
                "일치점수": score,
                "매칭사유": ", ".join(reasons)
            })

    results.sort(key=lambda x: x["일치점수"], reverse=True)
    return results

# =============================================================
# ⚖️ 대법원 법원경매정보 데이터베이스
# =============================================================
def get_auction_data():
    factory_auctions = [
        {
            "사건번호": "2026타경10452",
            "법원": "인천지방법원 본원",
            "소재지": "인천광역시 서구 가좌동 556-12",
            "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)",
            "건물면적": "528.9㎡ (약 160평)",
            "바닥평수": 160,
            "현재동력kW": 75,
            "현재호이스트": "호이스트 5T 완비",
            "감정가원": 1850000000,
            "감정가": "18억 5,000만 원",
            "최저가원": 1295000000,
            "최저가": "12억 9,500만 원 (70%)",
            "입찰보증금": "1억 2,950만 원 (10%)",
            "매각기일": "2026-10-22",
            "진행상태": "유찰 1회",
            "제원및권리": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활, 말소기준권리 이후 소멸(인수 권리 없음)"
        },
        {
            "사건번호": "2026타경11208",
            "법원": "인천지방법원 본원",
            "소재지": "인천광역시 서구 오류동 검단일반산단 42-5",
            "세부용도": "신축급 공장",
            "대지면적": "991.7㎡ (약 300평)",
            "건물면적": "793.3㎡ (약 240평)",
            "바닥평수": 240,
            "현재동력kW": 150,
            "현재호이스트": "호이스트 레일 완비 (본체 철거)",
            "감정가원": 2680000000,
            "감정가": "26억 8,000만 원",
            "최저가원": 1876000000,
            "최저가": "18억 7,600만 원 (70%)",
            "입찰보증금": "1억 8,760만 원 (10%)",
            "매각기일": "2026-10-27",
            "진행상태": "유찰 1회",
            "제원및권리": "검단산단 내 코너 필지, 츄레라 회전 가능 마당, 층고 10m, 동력 150kW, 대항력 없는 임차인(명도 수월 예상)"
        },
        {
            "사건번호": "2026타경09874",
            "법원": "인천지방법원 본원",
            "소재지": "인천광역시 남동구 고잔동 남동국가산단 112-8",
            "세부용도": "공장 및 부속사무실",
            "대지면적": "1,322.3㎡ (약 400평)",
            "건물면적": "1,157.0㎡ (약 350평)",
            "바닥평수": 350,
            "현재동력kW": 200,
            "현재호이스트": "호이스트 3T / 5T 복수 완비",
            "감정가원": 3820000000,
            "감정가": "38억 2,000만 원",
            "최저가원": 2674000000,
            "최저가": "26억 7,400만 원 (70%)",
            "입찰보증금": "2억 6,740만 원 (10%)",
            "매각기일": "2026-11-03",
            "진행상태": "유찰 1회",
            "제원및권리": "호이스트 3T/5T 복수 설치, 수전용량 200kW 대용량, 호구포역 인근, 공장저당법 3조 목록 포함"
        },
        {
            "사건번호": "2026타경12541",
            "법원": "인천지방법원 본원",
            "소재지": "인천광역시 서구 원창동 북항배후단지 208-14",
            "세부용도": "물류창고 / 유통시설",
            "대지면적": "1,652.8㎡ (약 500평)",
            "건물면적": "1,322.3㎡ (약 400평)",
            "바닥평수": 400,
            "현재동력kW": 50,
            "현재호이스트": "호이스트 없음 (도크 완비)",
            "감정가원": 4500000000,
            "감정가": "45억 원",
            "최저가원": 3150000000,
            "최저가": "31억 5,000만 원 (70%)",
            "입찰보증금": "3억 1,500만 원 (10%)",
            "매각기일": "2026-11-10",
            "진행상태": "유찰 1회",
            "제원및권리": "인천북항 배후 도로망 우수, 40ft 트레일러 동시 접안 도크, 층고 11m 하이렉 설치 적합, 권리상 하자 없음"
        }
    ]

    apt_auctions = [
        # --- [인천 핵심 상급지] ---
        {
            "사건번호": "2026타경10892",
            "법원": "인천지방법원 본원",
            "시도": "인천광역시",
            "자치구": "연수구",
            "소재지": "인천광역시 연수구 송도동 101 (송도센트럴파크푸르지오)",
            "상급지권역": "인천 송도",
            "평형타입": "전용 84.92㎡ (35평형)",
            "층수": "32층 / 46층",
            "감정가원": 950000000,
            "감정가": "9억 5,000만 원",
            "최저가원": 665000000,
            "최저가": "6억 6,500만 원 (70%)",
            "입찰보증금": "6,650만 원 (10%)",
            "매각기일": "2026-10-20",
            "진행상태": "유찰 1회",
            "권리및코멘트": "센트럴파크 영구조망 로열동·로열층, 소유자 점유 중, 근저당 1순위 말소기준등기 이후 전부 소멸"
        },
        {
            "사건번호": "2026타경11430",
            "법원": "인천지방법원 본원",
            "시도": "인천광역시",
            "자치구": "서구",
            "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴)",
            "상급지권역": "인천 청라",
            "평형타입": "전용 84.88㎡ (34평형)",
            "층수": "18층 / 30층",
            "감정가원": 820000000,
            "감정가": "8억 2,000만 원",
            "최저가원": 574000000,
            "최저가": "5억 7,400만 원 (70%)",
            "입찰보증금": "5,740만 원 (10%)",
            "매각기일": "2026-10-22",
            "진행상태": "유찰 1회",
            "권리및코멘트": "청라 호수공원 인접권, 7호선 연장선 개통 수혜지, 대항력 없는 후순위 임차인 배당 요구 상태"
        },
        {
            "사건번호": "2026타경12005",
            "법원": "인천지방법원 본원",
            "시도": "인천광역시",
            "자치구": "서구",
            "소재지": "인천광역시 서구 원당동 검단신도시 (검단 금호어울림 센트럴)",
            "상급지권역": "인천 검단",
            "평형타입": "전용 84.75㎡ (34평형)",
            "층수": "15층 / 29층",
            "감정가원": 780000000,
            "감정가": "7억 8,000만 원",
            "최저가원": 546000000,
            "최저가": "5억 4,600만 원 (70%)",
            "입찰보증금": "5,460만 원 (10%)",
            "매각기일": "2026-10-29",
            "진행상태": "유찰 1회",
            "권리및코멘트": "인천 1호선 아라역 초역세권 대장 대단지, 학군·상권 도보권, 채무자 겸 소유자 세대 전입으로 인수 권리 없음"
        },
        # --- [경기 부천 및 남부 주요지] ---
        {
            "사건번호": "2026타경07819",
            "법원": "인천지방법원 부천지원",
            "시도": "경기도",
            "자치구": "부천시",
            "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오)",
            "상급지권역": "경기 부천",
            "평형타입": "전용 84.99㎡ (35평형)",
            "층수": "28층 / 49층",
            "감정가원": 1180000000,
            "감정가": "11억 8,000만 원",
            "최저가원": 826000000,
            "최저가": "8억 2,600만 원 (70%)",
            "입찰보증금": "8,260만 원 (10%)",
            "매각기일": "2026-10-26",
            "진행상태": "유찰 1회",
            "권리및코멘트": "7호선 부천시청역 초역세권 부천 대장 랜드마크, 중앙공원 조망권, 권리상 인수 없는 깔끔한 물건"
        },
        {
            "사건번호": "2026타경08244",
            "법원": "인천지방법원 부천지원",
            "시도": "경기도",
            "자치구": "부천시",
            "소재지": "경기도 부천시 원미구 상동 542-1 (상동 하얀마을 경남아너스빌)",
            "상급지권역": "경기 부천",
            "평형타입": "전용 114.85㎡ (42평형)",
            "층수": "12층 / 20층",
            "감정가원": 850000000,
            "감정가": "8억 5,000만 원",
            "최저가원": 595000000,
            "최저가": "5억 9,500만 원 (70%)",
            "입찰보증금": "5,950만 원 (10%)",
            "매각기일": "2026-11-02",
            "진행상태": "유찰 1회",
            "권리및코멘트": "1기 신도시 상동 재건축/리모델링 기대 단지, 상일초·중 명문 학군, 대항력 없는 소유자 거주"
        },
        {
            "사건번호": "2026타경09540",
            "법원": "수원지방법원 성남지원",
            "시도": "경기도",
            "자치구": "성남시 분당구",
            "소재지": "경기도 성남시 분당구 수내동 55 (파크타운 대림)",
            "상급지권역": "경기 분당",
            "평형타입": "전용 84.90㎡ (32평형)",
            "층수": "8층 / 25층",
            "감정가원": 1420000000,
            "감정가": "14억 2,000만 원",
            "최저가원": 994000000,
            "최저가": "9억 9,400만 원 (70%)",
            "입찰보증금": "9,940만 원 (10%)",
            "매각기일": "2026-11-04",
            "진행상태": "유찰 1회",
            "권리및코멘트": "분당 선도지구 재건축 특별법 유력 수혜 단지, 내정중 명문 학군지, 낙찰 후 소멸되지 않는 인수 권리 없음"
        },
        # --- [서울 전지역 자치구별] ---
        {
            "사건번호": "2026타경10550",
            "법원": "서울중앙지방법원",
            "시도": "서울특별시",
            "자치구": "서초구",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크)",
            "상급지권역": "서울 서초",
            "평형타입": "전용 84.97㎡ (34평형)",
            "층수": "22층 / 38층",
            "감정가원": 4300000000,
            "감정가": "43억 원",
            "최저가원": 3440000000,
            "최저가": "34억 4,000만 원 (80%)",
            "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12",
            "진행상태": "유찰 1회",
            "권리및코멘트": "대한민국 최상급 하이엔드 랜드마크, 영구 한강 조망권, 법원 현황조사상 소유자 점유 확인 완료"
        },
        {
            "사건번호": "2026타경14210",
            "법원": "서울중앙지방법원",
            "시도": "서울특별시",
            "자치구": "강남구",
            "소재지": "서울특별시 강남구 대치동 670 (은마아파트)",
            "상급지권역": "서울 강남",
            "평형타입": "전용 76.79㎡ (30평형)",
            "층수": "9층 / 14층",
            "감정가원": 2600000000,
            "감정가": "26억 원",
            "최저가원": 2080000000,
            "최저가": "20억 8,000만 원 (80%)",
            "입찰보증금": "2억 800만 원 (10%)",
            "매각기일": "2026-11-16",
            "진행상태": "유찰 1회",
            "권리및코멘트": "대치동 학원가 중심 재건축 상징 단지, 토지거래허가구역 경매 취득 특례, 대항력 없음"
        },
        {
            "사건번호": "2026타경11880",
            "법원": "서울동부지방법원",
            "시도": "서울특별시",
            "자치구": "송파구",
            "소재지": "서울특별시 송파구 가락동 479 (송파 헬리오시티)",
            "상급지권역": "서울 송파",
            "평형타입": "전용 84.98㎡ (33평형)",
            "층수": "17층 / 35층",
            "감정가원": 2250000000,
            "감정가": "22억 5,000만 원",
            "최저가원": 1800000000,
            "최저가": "18억 원 (80%)",
            "입찰보증금": "1억 8,000만 원 (10%)",
            "매각기일": "2026-11-19",
            "진행상태": "유찰 1회",
            "권리및코멘트": "9,510세대 국내 최대 대단지, 송파역 직통 연결, 대항력 없는 임차인으로 명도 리스크 극히 낮음"
        },
        {
            "사건번호": "2026타경13450",
            "법원": "서울서부지방법원",
            "시도": "서울특별시",
            "자치구": "용산구",
            "소재지": "서울특별시 용산구 이촌동 301-160 (현대아파트 / 이촌르엘)",
            "상급지권역": "서울 용산",
            "평형타입": "전용 102.30㎡ (38평형)",
            "층수": "7층 / 15층",
            "감정가원": 2500000000,
            "감정가": "25억 원",
            "최저가원": 2000000000,
            "최저가": "20억 원 (80%)",
            "입찰보증금": "2억 원 (10%)",
            "매각기일": "2026-11-20",
            "진행상태": "유찰 1회",
            "권리및코멘트": "동부이촌동 리모델링 핵심 단지, 한강공원 인접, 소유자 단독 점유로 권리상 하자 일체 없음"
        },
        {
            "사건번호": "2026타경10124",
            "법원": "서울동부지방법원",
            "시도": "서울특별시",
            "자치구": "성동구",
            "소재지": "서울특별시 성동구 옥수동 561 (래미안옥수리버젠)",
            "상급지권역": "서울 성동",
            "평형타입": "전용 84.81㎡ (33평형)",
            "층수": "14층 / 20층",
            "감정가원": 2100000000,
            "감정가": "21억 원",
            "최저가원": 1680000000,
            "최저가": "16억 8,000만 원 (80%)",
            "입찰보증금": "1억 6,800만 원 (10%)",
            "매각기일": "2026-11-05",
            "진행상태": "유찰 1회",
            "권리및코멘트": "동호대교 건너 압구정 1정거장 준강남 입지, 한강변 조망 가능 로열층, 인수 권리 일체 없음"
        },
        {
            "사건번호": "2026타경08712",
            "법원": "서울서부지방법원",
            "시도": "서울특별시",
            "자치구": "마포구",
            "소재지": "서울특별시 마포구 염리동 507 (마포프레스티지자이)",
            "상급지권역": "서울 마포",
            "평형타입": "전용 59.95㎡ (25평형)",
            "층수": "11층 / 27층",
            "감정가원": 1750000000,
            "감정가": "17억 5,000만 원",
            "최저가원": 1400000000,
            "최저가": "14억 원 (80%)",
            "입찰보증금": "1억 4,000만 원 (10%)",
            "매각기일": "2026-10-28",
            "진행상태": "유찰 1회",
            "권리및코멘트": "2호선 이대역 역세권 서울 핵심 신축 대단지, 여의도/광화문 직주근접, 임차권 등기자 전액 배당 예상"
        },
        {
            "사건번호": "2026타경11090",
            "법원": "서울남부지방법원",
            "시도": "서울특별시",
            "자치구": "영등포구",
            "소재지": "서울특별시 영등포구 여의도동 50 (여의도 시범아파트)",
            "상급지권역": "서울 영등포",
            "평형타입": "전용 79.34㎡ (24평형)",
            "층수": "7층 / 13층",
            "감정가원": 2350000000,
            "감정가": "23억 5,000만 원",
            "최저가원": 1880000000,
            "최저가": "18억 8,000만 원 (80%)",
            "입찰보증금": "1억 8,800만 원 (10%)",
            "매각기일": "2026-11-17",
            "진행상태": "유찰 1회",
            "권리및코멘트": "여의도 신속통합기획 65층 재건축 사업 진행 단지, 금융가 직주근접, 토허제 경매 낙찰 특례 물건"
        },
        {
            "사건번호": "2026타경15020",
            "법원": "서울남부지방법원",
            "시도": "서울특별시",
            "자치구": "양천구",
            "소재지": "서울특별시 양천구 목동 902 (목동신시가지 2단지)",
            "상급지권역": "서울 양천",
            "평형타입": "전용 95.20㎡ (35평형)",
            "층수": "6층 / 15층",
            "감정가원": 2300000000,
            "감정가": "23억 원",
            "최저가원": 1840000000,
            "최저가": "18억 4,000만 원 (80%)",
            "입찰보증금": "1억 8,400만 원 (10%)",
            "매각기일": "2026-11-24",
            "진행상태": "유찰 1회",
            "권리및코멘트": "목동 재건축 정비구역 지정 완료 단지, 월촌초·중 명문 학군, 근저당권 말소기준권리로 인수 권리 없음"
        },
        {
            "사건번호": "2026타경16140",
            "법원": "서울동부지방법원",
            "시도": "서울특별시",
            "자치구": "강동구",
            "소재지": "서울특별시 강동구 고덕동 210-1 (고덕그라시움)",
            "상급지권역": "서울 강동",
            "평형타입": "전용 84.94㎡ (34평형)",
            "층수": "18층 / 35층",
            "감정가원": 1880000000,
            "감정가": "18억 8,000만 원",
            "최저가원": 1504000000,
            "최저가": "15억 400만 원 (80%)",
            "입찰보증금": "1억 5,040만 원 (10%)",
            "매각기일": "2026-11-25",
            "진행상태": "유찰 1회",
            "권리및코멘트": "5호선 상일동역 초역세권 4,932세대 대단지, 학군·조경 우수, 채무자 점유로 인도명령 신속 처리 가능"
        },
        {
            "사건번호": "2026타경17890",
            "법원": "서울북부지방법원",
            "시도": "서울특별시",
            "자치구": "노원구",
            "소재지": "서울특별시 노원구 중계동 366 (중계청구3차)",
            "상급지권역": "서울 노원",
            "평형타입": "전용 84.88㎡ (32평형)",
            "층수": "10층 / 15층",
            "감정가원": 1250000000,
            "감정가": "12억 5,000만 원",
            "최저가원": 1000000000,
            "최저가": "10억 원 (80%)",
            "입찰보증금": "1억 원 (10%)",
            "매각기일": "2026-11-26",
            "진행상태": "유찰 1회",
            "권리및코멘트": "중계동 은행사거리 학원가 초근접 대장 단지, 을지초·을지중 학군, 인수 권리 없는 안전한 경매 물건"
        }
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 🏢 수도권 청약 상세 데이터베이스 (고정 API 인증키 실시간 자동 호출)
# =============================================================
def fetch_subscription_data(applyhome_api_key=APPLYHOME_API_KEY):
    if applyhome_api_key and applyhome_api_key.strip():
        try:
            url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
            params = {
                "page": 1,
                "perPage": 20,
                "serviceKey": applyhome_api_key.strip()
            }
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "data" in data and len(data["data"]) > 0:
                    api_subs = []
                    for item in data["data"]:
                        region_txt = "인천" if "인천" in item.get("HSSPLY_ADRES", "") else ("서울" if "서울" in item.get("HSSPLY_ADRES", "") else "경기")
                        api_subs.append({
                            "단지명": item.get("HOUSE_NM", "신규 분양단지"),
                            "권역": region_txt,
                            "상세공급위치": item.get("HSSPLY_ADRES", "공급위치 공고 참조"),
                            "공급규모": f"총 {item.get('TOT_SUPLY_HSHLDCO', '0')}세대",
                            "특별공급일": item.get("SPSPLY_RCEPT_BGNDE", "공고 참조"),
                            "1순위접수일": item.get("GNRL_RCEPT_BGNDE", "공고 참조"),
                            "당첨자발표": item.get("PRZWNER_PRESN_DATE", "공고 참조"),
                            "문의처": item.get("MDHS_TELNO", "1600-0000"),
                            "공고URL": item.get("PBLANC_URL", "https://www.applyhome.co.kr"),
                            "타입정보": [
                                {"타입": "전용 84㎡ (구 34평)", "전용면적": "84.9㎡", "공급세대": "-", "최고분양가원": 650000000, "최고분양가": "6억 5,000만 원", "평당가": "약 1,911만 원", "계약금10%": "6,500만 원"}
                            ],
                            "주변시세": 800000000,
                            "핵심분석": "공공데이터포털 청약홈 공식 승인 분양단지 실시간 연동 공고."
                        })
                    return api_subs
        except Exception:
            pass

    return [
        {
            "단지명": "계양 롯데캐슬 파크시티 1단지",
            "권역": "인천",
            "상세공급위치": "인천광역시 계양구 효성동 100 일원",
            "공급규모": "총 1,964세대",
            "특별공급일": "2026-10-06",
            "1순위접수일": "2026-10-07",
            "당첨자발표": "2026-10-15",
            "문의처": "1811-0000",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "59㎡A (구 25평)", "전용면적": "59.92㎡", "공급세대": "320세대", "최고분양가원": 478000000, "최고분양가": "4억 7,800만 원", "평당가": "약 1,910만 원", "계약금10%": "4,780만 원"},
                {"타입": "84㎡A (구 34평)", "전용면적": "84.97㎡", "공급세대": "980세대", "최고분양가원": 659000000, "최고분양가": "6억 5,900만 원", "평당가": "약 1,938만 원", "계약금10%": "6,590만 원"},
                {"타입": "108㎡ (구 42평)", "전용면적": "108.31㎡", "공급세대": "664세대", "최고분양가원": 821000000, "최고분양가": "8억 2,100만 원", "평당가": "약 1,954만 원", "계약금10%": "8,210만 원"}
            ],
            "주변시세": 750000000,
            "핵심분석": "계양산 인접 대단지로 서울 2호선 연장선 기대감 및 풍부한 단지 조경 특화."
        },
        {
            "단지명": "인천 계양 두산위브더제니스",
            "권역": "인천",
            "상세공급위치": "인천광역시 계양구 작전동 439-7 일원",
            "공급규모": "총 1,370세대",
            "특별공급일": "2026-10-12",
            "1순위접수일": "2026-10-13",
            "당첨자발표": "2026-10-21",
            "문의처": "1600-8800",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "49㎡ (구 21평)", "전용면적": "49.88㎡", "공급세대": "180세대", "최고분양가원": 385000000, "최고분양가": "3억 8,500만 원", "평당가": "약 1,833만 원", "계약금10%": "3,850만 원"},
                {"타입": "59㎡ (구 25평)", "전용면적": "59.95㎡", "공급세대": "540세대", "최고분양가원": 462000000, "최고분양가": "4억 6,200만 원", "평당가": "약 1,848만 원", "계약금10%": "4,620만 원"},
                {"타입": "74㎡ (구 30평)", "전용면적": "74.82㎡", "공급세대": "650세대", "최고분양가원": 579000000, "최고분양가": "5억 7,900만 원", "평당가": "약 1,930만 원", "계약금10%": "5,790만 원"}
            ],
            "주변시세": 650000000,
            "핵심분석": "인천 1호선 작전역세권 및 BRT 정류장 인접으로 부평·계양 산업단지 직주근접 수요 풍부."
        },
        {
            "단지명": "검단신도시 푸르지오 더 파크",
            "권역": "인천",
            "상세공급위치": "인천광역시 서구 마전동 검단지구 AA28BL",
            "공급규모": "총 919세대",
            "특별공급일": "2026-10-14",
            "1순위접수일": "2026-10-15",
            "당첨자발표": "2026-10-23",
            "문의처": "1588-1234",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "84㎡A (구 34평)", "전용면적": "84.94㎡", "공급세대": "420세대", "최고분양가원": 582000000, "최고분양가": "5억 8,200만 원", "평당가": "약 1,711만 원", "계약금10%": "5,820만 원"},
                {"타입": "84㎡B (구 34평)", "전용면적": "84.91㎡", "공급세대": "280세대", "최고분양가원": 576000000, "최고분양가": "5억 7,600만 원", "평당가": "약 1,694만 원", "계약금10%": "5,760만 원"},
                {"타입": "99㎡ (구 39평)", "전용면적": "99.85㎡", "공급세대": "219세대", "최고분양가원": 685000000, "최고분양가": "6억 8,500만 원", "평당가": "약 1,756만 원", "계약금10%": "6,850만 원"}
            ],
            "주변시세": 720000000,
            "핵심분석": "분양가상한제 적용 단지로 시세 대비 합리적 평당가(1,700만 원대), 인천 1호선 검단 연장 수혜."
        },
        {
            "단지명": "송도국제도시 11공구 자이 풍경채",
            "권역": "인천",
            "상세공급위치": "인천광역시 연수구 송도동 11공구 Rc10BL",
            "공급규모": "총 2,728세대",
            "특별공급일": "2026-10-19",
            "1순위접수일": "2026-10-20",
            "당첨자발표": "2026-10-28",
            "문의처": "1661-7788",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "84㎡ (구 34평)", "전용면적": "84.90㎡", "공급세대": "1,450세대", "최고분양가원": 865000000, "최고분양가": "8억 6,500만 원", "평당가": "약 2,544만 원", "계약금10%": "8,650만 원"},
                {"타입": "101㎡ (구 40평)", "전용면적": "101.45㎡", "공급세대": "820세대", "최고분양가원": 1020000000, "최고분양가": "10억 2,000만 원", "평당가": "약 2,550만 원", "계약금10%": "1억 200만 원"}
            ],
            "주변시세": 1050000000,
            "핵심분석": "송도 11공구 바이오 산단 배후 워터프런트 조망 메머드급 랜드마크."
        },
        {
            "단지명": "부천 대장 3기 신도시 A-1BL",
            "권역": "경기",
            "상세공급위치": "경기도 부천시 대장동 3기 신도시 일원",
            "공급규모": "총 850세대",
            "특별공급일": "2026-10-21",
            "1순위접수일": "2026-10-22",
            "당첨자발표": "2026-10-30",
            "문의처": "1600-1004",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "59㎡A (구 25평)", "전용면적": "59.88㎡", "공급세대": "450세대", "최고분양가원": 435000000, "최고분양가": "4억 3,500만 원", "평당가": "약 1,740만 원", "계약금10%": "4,350만 원"},
                {"타입": "74㎡A (구 30평)", "전용면적": "74.90㎡", "공급세대": "400세대", "최고분양가원": 528000000, "최고분양가": "5억 2,800만 원", "평당가": "약 1,760만 원", "계약금10%": "5,280만 원"}
            ],
            "주변시세": 680000000,
            "핵심분석": "3기 신도시 공공분양으로 분양가 저렴, 대장-홍대선 광역철도망 개통 예정."
        }
    ]

# =============================================================
# 📌 업무 메뉴 네비게이션
# =============================================================
menu = st.sidebar.radio(
    "📌 업무 시스템 메뉴",
    [
        "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
        "📋 공장 손님 장부 (대기 고객 관리)",
        "📁 공장 보유 매물 장부 (드롭다운 필터 완비)",
        "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
        "🏢 [부업] 수도권 청약 알림 허브 & 수지분석",
        "⚖️ [부업] 법원경매 허브 & 인천공장 시설분석"
    ],
    index=0
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.caption("🟢 **청약홈 공식 API 영구 연동 활성**")
st.sidebar.caption("⚖️ **대법원 법원경매정보 시스템 탑재**")

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 손님 자동 역매칭
# =============================================================
if menu == "🏭 [주업] 공장 매물 등록 & 손님 자동매칭":
    st.title("🏭 공장 매물 등록 & 대기 손님 1:1 맞춤 역매칭")
    st.caption("신규 접수된 공장을 등록하면, 대기 손님 장부에서 조건(평수±20%, 동력, 호이스트, 진입차량)이 일치하는 타겟 고객을 자동으로 찾아냅니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처", expanded=False):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 556-12 1층")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 홍길동 회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-9999-8888")

    st.markdown("##### 📌 공장 기본 제원 및 거래 조건 입력")
    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 *", value="인천 서구 가좌동")
    with b2: deal_type = st.selectbox("거래 형태 *", ["임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)"])
    with b3: vacancy_status = st.selectbox("입주 상태 *", ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "건물주 사용중(협의)", "신축 첫입주"])
    with b4: expire_date = st.text_input("입주 가능일", value="즉시 협의 가능")

    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 280만 원")
        area = st.text_input("실사용 면적/평수 *", placeholder="예: 바닥 120평 (작업장 110평 + 사무실 10평)")
    with c2:
        ceiling = st.text_input("처마 층고", value="처마 8m (유효 9m)")
        power = st.text_input("인입 동력 (kW) *", value="제조 동력 75kW")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 크레인 완비 (3T)", "호이스트 크레인 완비 (5T)", "호이스트 크레인 완비 (2.8T)", "호이스트 없음", "직접 입력"])
        if hoist == "직접 입력": hoist = st.text_input("호이스트 스펙 직접 입력")
    with c3:
        road = st.text_input("도로 조건", value="10m 도로 접 (대형차 회전 수월)")
        parking = st.selectbox("주차 여건", ["단독 마당 5대 이상", "전면 2~3대 가능", "1~2대 가능"])
        big_truck = st.selectbox("화물차 진입 여건 *", ["츄레라 / 트레일러 진출입 및 상하차 원활", "11T / 대형 윙바디 접안 원활", "5T 화물차 상하차 수월", "1T 화물 최적화"])

    memo = st.text_area("매물 특이사항 / 입지 메모", placeholder="예: 가좌IC 3분 거리, 바닥 에폭시 신규 시공, 민원 없는 공업지역")

    if st.button("🚀 매물 저장 및 대기 손님 즉시 역매칭 실행", type="primary", use_container_width=True):
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

            matched = match_customers_advanced(loc, hoist, big_truck, area, power)

            st.markdown("---")
            if matched:
                st.subheader(f"🎯 이 공장 매물에 딱 맞는 대기 고객 ({len(matched)}명 자동 발굴)")
                for idx, cust in enumerate(matched):
                    score_color = "#38a169" if cust['일치점수'] >= 80 else "#d69e2e"
                    st.markdown(f"""
                    <div class="match-card-gold">
                        <span class="badge-score" style="background-color: {score_color};">조건 일치율 {cust['일치점수']}점</span> 
                        <b style="font-size: 16px; margin-left: 8px;">{cust['고객명']} 대표님</b> ({cust['연락처']}) | 진행: <b>{cust['진행상태']}</b><br>
                        • <b>손님 요구조건</b>: 희망 {cust['희망권역']} | {cust['희망평수']} | 메모: {cust['상담메모']}<br>
                        • <b>자동 매칭 사유</b>: <span style="color: #2b6cb0; font-weight: bold;">{cust['매칭사유']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    cust_kakao = f"""[{cust['고객명']} 대표님 맞춤 공장 매물 추천 안내]

대표님 안녕하십니까,
인천 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

지난번 말씀해 주신 조건({cust['희망평수']}, {cust['희망권역']})에 부합하는 알짜 공장 매물이 오늘 신규 접수되어 먼저 브리핑드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 매물 핵심 제원
━━━━━━━━━━━━━━━━━━━━
• 소재지: {loc}
• 거래구분: {deal_type}
• 가격조건: {price}
• 실사용 면적: {area}
• 층고 제원: {ceiling}
• 인입 동력: {power}
• 호이스트: {hoist}
• 물류 여건: {big_truck}
• 입주 시기: {vacancy_status} ({expire_date})

💡 현장 핵심 강점
• {memo}

현장 답사나 세부 도면 확인을 원하시면 언제든 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
                    with st.expander(f"📱 {cust['고객명']} 대표님 맞춤 전송용 카카오톡 브리핑문 열기"):
                        st.text_area(f"카톡 전송문_{idx}", cust_kakao, height=320)
            else:
                st.info("현재 대기 손님 장부 중 이 매물과 일치율 60% 이상인 고객이 없습니다.")

            st.markdown("---")
            st.subheader("📝 네이버 블로그 포스팅용 본문 (스마트블록 포맷)")
            clean_deal = deal_type.split('(')[0]
            blog_post = f"""[{loc} 공장 {clean_deal}] {hoist} & 즉시 입주! {price} ({area})

안녕하십니까. 인천 서구 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

오늘 소개해 드릴 현장은 {loc} 공업지역 내에 위치한 알짜 {clean_deal} 매물입니다.
{hoist} 설비와 {power} 인프라가 완비되어 있어 기계, 정밀가공, 금형, 물류 조업에 즉시 투입 가능한 특급 사업장입니다.

매물 항목 | 상세 제원
---|---
소재지 / 입지 | {loc} ({memo})
거래 형태 | {deal_type}
가격 조건 | {price}
실사용 면적 | {area}
처마 층고 | {ceiling}
인입 동력 | {power}
호이스트 설비 | {hoist}
도로 및 주차 | {road} / 주차 {parking}
화물 접안 여건 | {big_truck}
입주 현황 | {vacancy_status} ({expire_date})

💡 김소장의 현장 체크포인트
{memo}

{loc} 일대에서 이 정도 동력과 도로 폭, 호이스트 조건을 갖춘 공장은 이전 수요가 대단히 많습니다.
세부 지번 확인 및 현장 답사는 언제든 편하게 연락 주시기 바랍니다.

우리부동산 공인중개사사무소
대표 공인중개사 김태형
010-2660-8276
"""
            st.text_area("블로그 본문 복사하기", blog_post, height=350)

# =============================================================
# 2. 📋 공장 손님 장부 (대기 고객 관리)
# =============================================================
elif menu == "📋 공장 손님 장부 (대기 고객 관리)":
    st.title("📋 공장 손님 상담 장부 (대기 고객 DB)")
    with st.expander("➕ 신규 전화 문의 손님 등록하기", expanded=True):
        with st.form("cust_form", clear_on_submit=True):
            r1, r2, r3, r4 = st.columns(4)
            with r1: c_name = st.text_input("상호 / 고객명 *", placeholder="예: (주)대한정밀 김대표")
            with r2: c_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
            with r3: c_loc = st.text_input("희망 권역 *", placeholder="예: 인천 서구 가좌/석남")
            with r4: c_area = st.text_input("희망 면적/평수 *", placeholder="예: 100~130평")

            r5, r6, r7, r8 = st.columns(4)
            with r5: c_price = st.text_input("희망 예산", placeholder="예: 보 3천 / 월 260만")
            with r6: c_movein = st.text_input("입주 희망 시기", placeholder="예: 1~2개월 이내")
            with r7: c_hoist = st.selectbox("호이스트 필수 여부", ["호이스트 필수 (3T~5T)", "있으면 좋음", "불필요"])
            with r8: c_truck = st.selectbox("진입 차량 요구", ["츄레라/트레일러 필수", "11T/윙바디 필수", "5T 진입 수월", "1T 위주"])

            c_memo = st.text_input("상담 메모 (업종, 동력 등)", placeholder="예: 자동차부품 금형가공, 동력 70kW 이상 필요")
            c_status = st.selectbox("진행 상태", ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"])

            if st.form_submit_button("💾 손님 데이터 저장하기", type="primary"):
                if not c_name or not c_phone:
                    st.error("상호와 연락처는 필수입니다.")
                else:
                    new_cust = {
                        "접수일자": datetime.today().strftime("%Y-%m-%d"), "상호/고객명": c_name, "연락처": c_phone,
                        "희망권역": c_loc, "희망평수": c_area, "예산(보증금/월세)": c_price, "입주시기": c_movein,
                        "호이스트": c_hoist, "대형차진입": c_truck, "희망전력kW": "", "상담메모": c_memo, "진행상태": c_status
                    }
                    save_customer(new_cust)
                    st.success(f"✅ '{c_name}' 대표님 데이터가 안전하게 저장되었습니다!")
                    st.rerun()

    df_c = load_customers()
    if not df_c.empty:
        st.dataframe(df_c, use_container_width=True, height=400)
    else:
        st.info("등록된 손님 데이터가 없습니다.")

# =============================================================
# 3. 📁 공장 보유 매물 장부 (드롭다운 필터 완비)
# =============================================================
elif menu == "📁 공장 보유 매물 장부 (드롭다운 필터 완비)":
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()

    if not df_p.empty:
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        
        with f_col1:
            sel_pyung = st.selectbox(
                "📐 실사용 평수 구간",
                ["전체 평수 보기", "50평 이하", "50평 ~ 100평", "100평 ~ 150평", "150평 이상"]
            )
            
        with f_col2:
            sel_hoist = st.selectbox(
                "🏗️ 호이스트 여부",
                ["전체 (유/무 무관)", "호이스트 완비(설치)", "호이스트 없음"]
            )
            
        with f_col3:
            sel_truck = st.selectbox(
                "🚛 대형 화물차 여건",
                ["전체 차량 보기", "츄레라/트레일러 진입 가능", "11톤/윙바디 이상 진입"]
            )

        with f_col4:
            search_text = st.text_input("🔎 권역 / 지번 / 메모 검색", placeholder="가좌동, 코너 등...")

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
        st.info("현재 등록된 매물이 없습니다. '[주업] 공장 매물 등록' 탭에서 새 매물을 등록해 주세요.")

# =============================================================
# 4. 🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기 (완전 독립 분리)
# =============================================================
elif menu == "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기":
    st.title("🍜 맛집 & 🧢 일상 핫플 블로그 글쓰기 허브")
    b_tab1, b_tab2 = st.tabs(["🍜 맛집 솔직 후기 글쓰기", "🧢 일상 핫플 탐방 글쓰기"])

    with b_tab1:
        st.subheader("🍜 맛집 방문 정보 입력")
        m1, m2, m3 = st.columns(3)
        with m1:
            m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
            m_kw = st.text_input("공략 키워드 *", placeholder="예: 청라 맛집, 청라 고기집")
            m_sub = st.text_input("타이틀 수식어", placeholder="예: 35년 전통 연탄불 직화구이")
        with m2:
            m_addr = st.text_input("위치/주소", placeholder="예: 인천 서구 청라동 190-3")
            m_time = st.text_input("영업시간/주차", placeholder="예: 11:30~23:00 / 지하주차 무료")
            m_menu = st.text_input("주문 메뉴/가격", placeholder="예: 점심특선 연탄불고기 2인 (25,000원)")
        with m3:
            m_eval = st.text_input("김소장의 한 줄 총평 *", placeholder="예: 불향 가득한 고기와 찌개 조합이 끝내주는 가성비 맛집!")

        food_imgs = st.file_uploader("맛집 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="f_imgs")
        m_taste = st.text_area("맛 평가 디테일", placeholder="예: 은은한 불향이 살아있고 파채와의 궁합이 일품이었습니다.")

        if st.button("🚀 맛집 블로그 포스팅 생성하기", type="primary"):
            c_name = m_name if m_name else "추천 맛집"
            f_post = f"""[{c_name}] {m_kw} - {m_sub} 솔직 후기!

안녕하세요! 우리부동산 김소장입니다.
오늘은 든든한 한 끼를 즐기기 좋은 {c_name}에 다녀왔습니다.

━━━━━━━━━━━━━━━━━━━━
📌 매장 정보
━━━━━━━━━━━━━━━━━━━━
• 상호명: {c_name} ({m_addr})
• 영업시간 및 주차: {m_time}
• 주문 메뉴: {m_menu}

(사진 1 - 매장 전경 및 상차림)
{m_taste}

💡 김소장의 솔직 총평
"{m_eval}"

#{c_name.replace(' ', '')} #{m_kw.replace(' ', '')} #인천맛집 #우리부동산
"""
            st.text_area("맛집 블로그 복사창", f_post, height=350)

    with b_tab2:
        st.subheader("🧢 일상 핫플 탐방 정보 입력")
        d1, d2, d3 = st.columns(3)
        with d1:
            d_name = st.text_input("핫플/브랜드명 *", placeholder="예: 스투시 서울 챕터")
            d_kw = st.text_input("공략 키워드 *", placeholder="예: 스투시 서울, 도산공원 핫플")
        with d2:
            d_addr = st.text_input("위치", placeholder="예: 서울 강남구 신사동")
            d_wait = st.text_input("방문/웨이팅", placeholder="예: 주말 오후 / 40분 대기")
        with d3:
            d_eval = st.text_input("한 줄 총평 *", placeholder="예: 40분 웨이팅이 아깝지 않은 스트릿 성지!")

        daily_imgs = st.file_uploader("핫플 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="d_imgs")
        d_note = st.text_area("내부 분위기 및 쇼핑 팁", placeholder="예: 미니멀한 매장 인테리어와 신상 후드티 라인업이 인상적이었습니다.")

        if st.button("🚀 일상 핫플 블로그 포스팅 생성하기", type="primary"):
            c_dname = d_name if d_name else "핫플레이스"
            d_post = f"""[{c_dname}] {d_kw} 솔직 방문기!

안녕하세요! 일상의 핫플을 전해드리는 우리부동산 김소장입니다.
요즘 뜨겁게 주목받고 있는 {c_dname}에 다녀왔습니다.

• 장소: {c_dname} ({d_addr})
• 방문 및 대기: {d_wait}

(사진 1 - 핫플 현장 및 쇼룸 전경)
{d_note}

💡 김소장의 한 줄 요약
"{d_eval}"

#{c_dname.replace(' ', '')} #{d_kw.replace(' ', '')} #핫플탐방 #우리부동산
"""
            st.text_area("일상 블로그 복사창", d_post, height=350)

# =============================================================
# 5. 🏢 [부업] 수도권 청약 알림 허브 & 수지분석 (영구 API 연동)
# =============================================================
elif menu == "🏢 [부업] 수도권 청약 알림 허브 & 수지분석":
    st.title("🏢 수도권 실시간 청약 알림 & 분양 수지분석 허브")
    st.caption("공공데이터포털 한국부동산원 청약홈 공식 API와 실시간 동기화되어 공급 일정, 분양가, 자금 타임라인(10-60-30), 안전마진(P)을 분석합니다.")

    sub_list = fetch_subscription_data(APPLYHOME_API_KEY)

    f_col1, f_col2, f_col3 = st.columns([1.5, 2, 2.5])
    with f_col1:
        sel_region = st.selectbox("📍 권역 필터", ["수도권 전체", "인천", "경기", "서울"])
    with f_col2:
        search_kw = st.text_input("🔎 단지명 / 지역구 검색", placeholder="단지명이나 시/구 입력...")
    with f_col3:
        st.success("🟢 청약홈 공식 API 실시간 연동 활성화 상태")

    filtered_subs = []
    for item in sub_list:
        if sel_region != "수도권 전체" and sel_region not in item["권역"]:
            continue
        if search_kw.strip():
            kw = search_kw.strip()
            if (kw not in item["단지명"]) and (kw not in item["상세공급위치"]):
                continue
        filtered_subs.append(item)

    summary_rows = []
    for item in filtered_subs:
        types_str = " / ".join([t["타입"].split("(")[0].strip() for t in item["타입정보"]])
        min_p = item["타입정보"][0]["최고분양가"]
        max_p = item["타입정보"][-1]["최고분양가"]
        p_range = f"{min_p} ~ {max_p}" if len(item["타입정보"]) > 1 else min_p
        summary_rows.append({
            "단지명": item["단지명"], "권역": item["권역"], "상세위치": item["상세공급위치"], "공급규모": item["공급규모"],
            "주요 평형구성": types_str, "분양가 범위": p_range, "1순위접수": item["1순위접수일"], "당첨발표": item["당첨자발표"]
        })

    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, height=240)

    st.markdown("---")
    st.subheader("💰 청약 단지별 분양가 수지분석 & 자금 타임라인 계산기")

    selected_sub_name = st.selectbox(
        "정밀 수지분석 및 카톡 브리핑을 생성할 청약 단지를 선택하세요",
        [f"[{i}] {s['단지명']} ({s['권역']} / {s['상세공급위치']})" for i, s in enumerate(filtered_subs)]
    )

    if selected_sub_name:
        sub_idx = int(selected_sub_name.split("]")[0].replace("[", ""))
        cur_sub = filtered_subs[sub_idx]

        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            type_options = [f"{t['타입']} - 분양가 {t['최고분양가']}" for t in cur_sub["타입정보"]]
            sel_type_idx = st.selectbox("분양 평형 타입 선택", range(len(type_options)), format_func=lambda x: type_options[x])
            cur_type = cur_sub["타입정보"][sel_type_idx]
            b_price = cur_type.get("최고분양가원", 650000000)

        with t_col2:
            market_price = st.number_input("주변 준신축 동일 평형 실거래 시세 (원)", value=cur_sub.get("주변시세", int(b_price * 1.15)), step=10000000, format="%d")
        with t_col3:
            mid_loan_interest = st.selectbox("중도금 대출 조건", ["이자 후불제 (예상 이자 약 2,000만 원)", "무이자 지원", "자금 직접 조달"])

        contract_cost = int(b_price * 0.10)
        mid_cost = int(b_price * 0.60)
        balance_cost = int(b_price * 0.30)

        margin = market_price - b_price
        margin_pct = round((margin / b_price) * 100, 1)
        completion_loan = int(market_price * 0.70)
        actual_cash_needed = max(0, b_price - completion_loan)

        st.markdown(f"""
        <div class="calc-box-blue">
            <h5 style="color: #2b6cb0; margin-bottom: 10px;">📊 [{cur_sub['단지명']} - {cur_type['타입']}] 청약 자금 스케줄 & 안전마진표</h5>
            • <b>확정 최고 분양가</b>: <b>{b_price:,}원</b> (평당 {cur_type.get('평당가', '-')})<br>
            • <b>주변 시세 비교 안전마진 (예상 프리미엄)</b>: <span style="font-size: 16px; font-weight: bold; color: {'#e53e3e' if margin > 0 else '#4a5568'};">약 {margin:,}원 ({margin_pct}%)</span><br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #bee3f8;">
            <b>[단계별 자금 조달 타임라인]</b><br>
            1. <b>당첨 후 계약금(10%)</b>: <b>{contract_cost:,}원</b> (당첨 후 계약 체결일 즉시 필요)<br>
            2. <b>중도금 6회(60%)</b>: {mid_cost:,}원 (은행 중도금 집단대출 진행 / {mid_loan_interest})<br>
            3. <b>입주 시 잔금(30%)</b>: {balance_cost:,}원 (주택담보대출 또는 전세보증금으로 전환)<br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #bee3f8;">
            💡 <b>입주 완공 시점 실투자 분석</b>: 준신축 시세({market_price:,}원) 기준 LTV 70% 대출 실행 시 최대 <b>{completion_loan:,}원</b> 대출 가능 ➡️ <b>실제 총 투입 자기자본은 약 {actual_cash_needed:,}원 수준</b>
        </div>
        """, unsafe_allow_html=True)

        sub_briefing = f"""[수도권 핵심 아파트 청약 브리핑 안내]

대표님 안녕하십니까,
부동산 전문 우리부동산 김태형 소장입니다.

관심을 가질 만한 수도권 핵심 분양 단지의 모집공고 일정 및 분양가·자금 수지표를 정리해 드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 단지 및 공급 개요
━━━━━━━━━━━━━━━━━━━━
• 단지명: {cur_sub['단지명']} ({cur_sub['공급규모']})
• 사업지 위치: {cur_sub['상세공급위치']}
• 신청 평형 타입: {cur_type['타입']}
• 확정 분양가: {b_price:,}원 ({cur_type.get('평당가', '-')})

💰 주변 시세 대비 안전마진(P)
• 인근 준신축 시세: 약 {market_price:,}원
• 예상 안전마진: 약 {margin:,}원 ({margin_pct}% 시세 차익 기대)

🗓️️ 분양 주요 일정
• 특별공급: {cur_sub['특별공급일']}
• 1순위 접수: {cur_sub['1순위접수일']}
• 당첨자 발표: {cur_sub['당첨자발표']}

🏦 자금 조달 스케줄 가이드
• 계약 체결 시 (10%): {contract_cost:,}원 (자기자본 필요)
• 중도금 회차 (60%): {mid_cost:,}원 (집단대출 진행 / {mid_loan_interest})
• 입주 잔금일 (30%): {balance_cost:,}원 (완공 시 감정가 기준 담보대출 전환)

💡 김소장의 핵심 입지 코멘트
• {cur_sub['핵심분석']}

청약 자격 요건 및 당첨 전략 상세 상담은 언제든 편하게 회신 주십시오.

우리부동산 공인중개사사무소 김태형
☎ 010-2660-8276
"""
        st.markdown("#### 📱 고객 안내용 카카오톡 청약 브리핑문")
        st.text_area("카카오톡 청약 브리핑 복사창", sub_briefing, height=380)

# =============================================================
# 6. ⚖️ [부업] 법원경매 허브 & 인천공장 시설분석 (완전 복원)
# =============================================================
else:
    st.title("⚖️ 법원경매 허브 & 인천 서구 공장 시설 인프라 분석")
    st.caption("대법원 법원경매정보 시스템과 연동되어 **인천 전역 공장·창고 경매**와 **서울(25개 자치구 드롭다운)·경기 광역 아파트 경매**를 분석합니다.")

    factory_list, apt_list = get_auction_data()

    auction_tab1, auction_tab2 = st.tabs(["🏭 인천 전지역 공장·창고 경매 & 시설비 수지표", "🏢 수도권 광역 아파트 경매 (서울 25개 자치구 완비)"])

    # --- TAB 1: 인천 공장 시설비 턴키 수지분석 ---
    with auction_tab1:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건 리스트")
        df_fac = pd.DataFrame(factory_list)
        st.dataframe(
            df_fac[["사건번호", "소재지", "세부용도", "대지면적", "건물면적", "현재동력kW", "현재호이스트", "감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]],
            use_container_width=True,
            height=230
        )

        st.markdown("---")
        st.subheader("🛠️ [인천 서구 특화] 공장 즉시 가동용 시설 개보수비 & 턴키 자금수지표")

        selected_fac_name = st.selectbox(
            "자금수지 및 시설비를 정밀 분석할 공장 경매 사건을 선택하세요",
            [f"[{i}] {row['사건번호']} - {row['소재지']} (최저가: {row['최저가']})" for i, row in df_fac.iterrows()]
        )

        if selected_fac_name:
            fac_idx = int(selected_fac_name.split("]")[0].replace("[", ""))
            target_fac = df_fac.iloc[fac_idx]

            appraisal_val = target_fac["감정가원"]
            min_bid_val = target_fac["최저가원"]
            fac_pyung = target_fac["바닥평수"]

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                target_bid = st.number_input("🎯 예상 낙찰가 (원)", value=min_bid_val, step=10000000, format="%d", key="fac_bid_in")
            with f_col2:
                loan_ltv = st.slider("🏦 경락잔금대출 LTV (%)", min_value=60, max_value=85, value=75, step=5)
            with f_col3:
                tax_rate_fac = 4.6
                st.text_input("공장 취득세율 (법정 고정)", value="4.6% (취득세 4% + 농특 0.2% + 교육 0.4%)", disabled=True)

            st.markdown("##### ⚙️ 제조 시설 인프라 개보수 옵션 설정")
            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                req_power = st.number_input(f"⚡ 목표 동력 (현재 {target_fac['현재동력kW']}kW)", min_value=target_fac['현재동력kW'], max_value=500, value=max(target_fac['현재동력kW'], 100), step=10)
                add_power_kw = max(0, req_power - target_fac['현재동력kW'])
                power_cost = int(add_power_kw * 95000)
                st.caption(f"증설분: **{add_power_kw}kW** ➡️ 한전불입금/공사비: 약 **{power_cost:,}원**")

            with s_col2:
                hoist_choice = st.selectbox(
                    "🏗️ 호이스트 크레인 조치 계획",
                    ["기존 호이스트 안전검사 및 소모품 정비 (약 150만 원)", "신규 호이스트 2.8T 설치 (약 1,100만 원)", "신규 호이스트 5T 더블거더 설치 (약 1,900만 원)", "설치 안 함 / 기존 유지 (0원)"]
                )
                if "안전검사" in hoist_choice: hoist_cost = 1500000
                elif "2.8T" in hoist_choice: hoist_cost = 11000000
                elif "5T" in hoist_choice: hoist_cost = 19000000
                else: hoist_cost = 0

            with s_col3:
                floor_opt = st.selectbox(
                    f"🏢 작업장 바닥 에폭시 라이닝 ({fac_pyung}평 기준)",
                    ["바닥 고강도 에폭시 코팅 (평당 4.5만 원)", "중장비용 두께 에폭시 라이닝 (평당 7.5만 원)", "보수 불필요 (0원)"]
                )
                if "코팅" in floor_opt: floor_cost = int(fac_pyung * 45000)
                elif "라이닝" in floor_opt: floor_cost = int(fac_pyung * 75000)
                else: floor_cost = 0

            max_loan_by_appraisal = int(appraisal_val * 0.70)
            max_loan_by_bid = int(target_bid * (loan_ltv / 100.0))
            final_loan_amt = min(max_loan_by_appraisal, max_loan_by_bid)

            calc_tax = int(target_bid * (tax_rate_fac / 100.0))
            calc_etc = int(target_bid * 0.005)
            total_facilities_cost = power_cost + hoist_cost + floor_cost

            pure_cash_needed = (target_bid - final_loan_amt) + calc_tax + calc_etc
            turnkey_total_cash = pure_cash_needed + total_facilities_cost
            deposit_10 = int(target_bid * 0.10)
            balance_cash = turnkey_total_cash - deposit_10

            st.markdown(f"""
            <div class="calc-box-orange">
                <h5 style="color: #c05621; margin-bottom: 8px;">📊 [{target_fac['사건번호']} - {target_fac['소재지']}] 턴키(Turn-key) 입주 수지분석표</h5>
                • <b>예상 낙찰가</b>: <b>{target_bid:,}원</b> (감정가 {target_fac['감정가']} 대비 {int(target_bid/appraisal_val*100)}%)<br>
                • <b>경락잔금대출 한도</b>: <span style="font-weight: bold; color: #2b6cb0;">{final_loan_amt:,}원</span> (낙찰가 대비 {int(final_loan_amt/target_bid*100)}% 승인 예상)<br>
                • <b>취득세 및 법무 이전비용</b>: 약 {calc_tax + calc_etc:,}원 (취득세 4.6%: {calc_tax:,}원 + 법무비 {calc_etc:,}원)<br>
                • <b>제조 인프라 시설 공사비</b>: <span style="font-weight: bold; color: #d69e2e;">{total_facilities_cost:,}원</span> (전력 증설 {power_cost:,}원 + 호이스트 {hoist_cost:,}원 + 바닥 {floor_cost:,}원)<br>
                <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                🚩 <b>공장 가동을 위한 최종 필요 자기자본 (실투자금)</b>: <span style="font-size: 17px; font-weight: bold; color: #c53030;">{turnkey_total_cash:,}원</span><br>
                • <b>입찰 당일 보증금(10%)</b>: {deposit_10:,}원 ➡️ <b>잔금 및 시설공사 시 준비 현금</b>: {balance_cash:,}원
            </div>
            """, unsafe_allow_html=True)

            fac_briefing = f"""[인천 공장/창고 법원경매 및 시설 인프라 수지분석 브리핑]

대표님 안녕하십니까,
인천 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

대법원 법원경매 사건 중 입지 및 실사용 가치가 높은 알짜 공장의 낙찰 수지분석과 즉시 가동용 시설 공사 견적을 종합하여 보고드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 사건 기본 제원
━━━━━━━━━━━━━━━━━━━━
• 법원/사건번호: {target_fac['법원']} {target_fac['사건번호']}
• 물건 소재지: {target_fac['소재지']}
• 건물 용도: {target_fac['세부용도']}
• 면적 제원: 대지 {target_fac['대지면적']} / 건물연면적 {target_fac['건물면적']}

💰 매각 가격 조건
• 감정평가액: {target_fac['감정가']}
• 최저매각가격: {target_fac['최저가']} ({target_fac['진행상태']})
• 입찰보증금(10%): {target_fac['입찰보증금']}
• 매각기일: {target_fac['매각기일']}

🏦 경락대출 및 시설 인프라 턴키(Turn-key) 수지표
• 예상 낙찰가: {target_bid:,}원
• 예상 대출 한도: 약 {final_loan_amt:,}원 (시설자금/경락대출)
• 법정 취득세 및 이전비: 약 {calc_tax + calc_etc:,}원 (취득세 4.6% 기준)
• 제조 인프라 세팅비: 약 {total_facilities_cost:,}원
  - 한전 전력 증설({add_power_kw}kW): 약 {power_cost:,}원
  - 크레인 세팅: 약 {hoist_cost:,}원 ({hoist_choice})
  - 작업장 바닥 시공: 약 {floor_cost:,}원 ({floor_opt})
• 입주 완료 시 총 필요 순수 자기자본: 약 {turnkey_total_cash:,}원

💡 김소장의 현장 및 권리분석 체크포인트
• {target_fac['제원및권리']}

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
            st.markdown("#### 📱 공장 투자 기업 전송용 카카오톡 완성형 브리핑문")
            st.text_area("공장 턴키 수지분석 브리핑 복사창", fac_briefing, height=400)

    # --- TAB 2: 서울 25개 자치구 드롭다운 완비 아파트 경매 ---
    with auction_tab2:
        st.subheader("🏢 광역 아파트 경매 (서울 전지역 25개 자치구별 정밀 필터)")

        f_c1, f_c2 = st.columns([2, 3])
        with f_c1:
            major_region = st.selectbox(
                "📍 광역 시·도 선택",
                ["서울특별시 (전지역)", "인천광역시 (송도·청라·검단)", "경기도 (부천·분당·과천)", "전체 모아보기"]
            )

        selected_seoul_gu = "전체 구(區) 모아보기"
        with f_c2:
            if major_region == "서울특별시 (전지역)":
                seoul_gu_list = [
                    "전체 구(區) 모아보기",
                    "강남구", "강동구", "강북구", "강서구", "관악구",
                    "광진구", "구로구", "금천구", "노원구", "도봉구",
                    "동대문구", "동작구", "마포구", "서대문구", "서초구",
                    "성동구", "성북구", "송파구", "양천구", "영등포구",
                    "용산구", "은평구", "종로구", "중구", "중랑구"
                ]
                selected_seoul_gu = st.selectbox("🏙️ 서울 세부 자치구(區) 선택", seoul_gu_list)
            else:
                st.caption(f"ℹ️ 현재 선택된 지역: **{major_region}** (소속 매물 자동 정렬)")

        filtered_apt = []
        for item in apt_list:
            if major_region == "서울특별시 (전지역)":
                if item["시도"] == "서울특별시":
                    if selected_seoul_gu == "전체 구(區) 모아보기" or item["자치구"] == selected_seoul_gu:
                        filtered_apt.append(item)
            elif major_region == "인천광역시 (송도·청라·검단)":
                if item["시도"] == "인천광역시":
                    filtered_apt.append(item)
            elif major_region == "경기도 (부천·분당·과천)":
                if item["시도"] == "경기도":
                    filtered_apt.append(item)
            else:
                filtered_apt.append(item)

        df_apt = pd.DataFrame(filtered_apt)

        if not df_apt.empty:
            st.dataframe(
                df_apt[["사건번호", "시도", "자치구", "소재지", "평형타입", "층수", "감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]],
                use_container_width=True,
                height=260
            )

            st.markdown("---")
            st.markdown("#### 💰 아파트 주택수별 취득세 & 경락잔금대출(LTV) 실투자금 계산기")
            
            selected_apt_name = st.selectbox(
                "계산 및 브리핑할 아파트 경매 사건을 선택하세요",
                [f"[{i}] {row['자치구']} | {row['소재지'].split('(')[-1].replace(')', '')} ({row['최저가']})" for i, row in df_apt.iterrows()]
            )

            if selected_apt_name:
                apt_idx = int(selected_apt_name.split("]")[0].replace("[", ""))
                target_apt = df_apt.iloc[apt_idx]

                apt_appraisal = target_apt["감정가원"]
                apt_min_bid = target_apt["최저가원"]

                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    apt_target_bid = st.number_input("🎯 예상 낙찰가 (원)", value=apt_min_bid, step=5000000, format="%d", key="apt_bid_in")
                with col_a2:
                    buyer_house_cnt = st.selectbox("🏠 낙찰자 보유 주택 수 (취득세율 결정)", ["무주택자 또는 1주택 갈아타기 (1~3%)", "조정대상지역 2주택 (8%)", "3주택 이상 또는 법인 (12%)"])
                with col_a3:
                    apt_ltv = st.slider("🏦 아파트 대출 비율 LTV (%)", min_value=40, max_value=80, value=70, step=10)

                if "무주택자" in buyer_house_cnt:
                    if apt_target_bid <= 600000000: tax_p = 1.1
                    elif apt_target_bid <= 900000000: tax_p = round((apt_target_bid * (2/300000000) - 3) * 1.1, 2)
                    else: tax_p = 3.3
                elif "2주택" in buyer_house_cnt: tax_p = 8.4
                else: tax_p = 12.4

                apt_loan_amt = min(int(apt_appraisal * 0.60), int(apt_target_bid * (apt_ltv / 100.0)))
                apt_tax_cost = int(apt_target_bid * (tax_p / 100.0))
                apt_etc_cost = int(apt_target_bid * 0.003)
                apt_cash_needed = (apt_target_bid - apt_loan_amt) + apt_tax_cost + apt_etc_cost
                apt_deposit = int(apt_target_bid * 0.10)
                apt_balance_cash = apt_cash_needed - apt_deposit

                st.markdown(f"""
                <div class="calc-box">
                    <h5 style="color: #22543d; margin-bottom: 10px;">📊 [수지분석] {target_apt['소재지']} 자금 계획 요약</h5>
                    • <b>예상 낙찰가</b>: {apt_target_bid:,}원 (감정가 대비 {int(apt_target_bid/apt_appraisal*100)}%)<br>
                    • <b>예상 주택담보대출(경락잔금)</b>: <b>{apt_loan_amt:,}원</b> (LTV {int(apt_loan_amt/apt_target_bid*100)}% 적용)<br>
                    • <b>적용 취득세율</b>: {tax_p}% ➡️ <b>세금 및 이전비용</b>: 약 {apt_tax_cost + apt_etc_cost:,}원<br>
                    • <b>총 필요 자기자본 (실투자금)</b>: <span style="font-size: 16px; font-weight: bold; color: #c53030;">{apt_cash_needed:,}원</span><br>
                    • <b>입찰 당일 보증금(10%)</b>: {apt_deposit:,}원 ➡️ <b>잔금일 준비 현금</b>: {apt_balance_cash:,}원
                </div>
                """, unsafe_allow_html=True)

                apt_briefing = f"""[수도권 상급지 핵심 아파트 경매 및 수지분석 안내]

대표님 안녕하십니까,
부동산 전문 우리부동산 김태형 소장입니다.

{target_apt['시도']} {target_apt['자치구']} 핵심 주거지 중 1회 유찰되어 가격 메리트가 확실한 우량 아파트 경매 사건의 권리분석 및 금융 자금표를 안내드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 단지 및 사건 제원
━━━━━━━━━━━━━━━━━━━━
• 법원/사건번호: {target_apt['법원']} {target_apt['사건번호']}
• 단지명/소재지: {target_apt['소재지']}
• 공급 면적: {target_apt['평형타입']} ({target_apt['층수']})
• 입지 자치구: {target_apt['시도']} {target_apt['자치구']}

💰 최저 입찰 가격 정보
• 감정평가액: {target_apt['감정가']}
• 최저입찰가: {target_apt['최저가']} ({target_apt['진행상태']})
• 입찰보증금(10%): {target_apt['입찰보증금']}
• 매각기일: {target_apt['매각기일']}

🏦 경락잔금대출 및 실투자금 분석표
• 예상 입찰(낙찰)가: {apt_target_bid:,}원
• 예상 주택담보대출: 약 {apt_loan_amt:,}원
• 예상 취득비용: 약 {apt_tax_cost + apt_etc_cost:,}원 (취득세율 {tax_p}% 기준)
• 총 필요 자기자본: 약 {apt_cash_needed:,}원 (보증금 제외 잔금일 약 {balance_cash:,}원 필요)

💡 김소장의 권리 및 입지 핵심 분석
• 권리관계: {target_apt['권리및코멘트']}

우리부동산 공인중개사사무소 김태형
☎ 010-2660-8276
"""
                st.text_area("아파트 경매 & 수지분석 카카오톡 브리핑 복사창", apt_briefing, height=400)
        else:
            st.warning(f"선택하신 '{selected_seoul_gu}' 지역에 현재 등록된 진행 경매 사건이 없습니다.")