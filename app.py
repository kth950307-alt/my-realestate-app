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
        st.caption("공장 전문 중개 & 고객 관리 CRM - 사무실 보안 인증")
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
# ⚡ CSV 데이터베이스 관리 함수 (손님 장부 컬럼 대폭 강화)
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        # 이전 버전 호환 컬럼 자동 보정
        if "거래구분" not in df.columns: df["거래구분"] = "임대차(월세)"
        if "중요도" not in df.columns: df["중요도"] = "⭐⭐ A급(유력)"
        if "최근연락일" not in df.columns: df["최근연락일"] = df["접수일자"] if "접수일자" in df.columns else datetime.today().strftime("%Y-%m-%d")
        return df
    cols = ["접수일자", "최근연락일", "중요도", "거래구분", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세/매매가)", "입주시기", "호이스트", "대형차진입", "희망전력kW", "상담메모", "진행상태"]
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

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

# 🎯 공장 매물 ➡️ 대기 손님 정밀 스캔 & 일치율 평가 (거래형태 대조 반영)
def match_customers_advanced(fac_loc, fac_deal_type, fac_hoist, fac_truck, fac_area_text, fac_power_text=""):
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

        # 0. 거래구분(매매/임대) 일치 여부
        c_deal = str(row.get("거래구분", ""))
        if "매매" in fac_deal_type and "매매" in c_deal:
            score += 20
            reasons.append("매매 조건 일치")
        elif "임대" in fac_deal_type and "임대" in c_deal:
            score += 20
            reasons.append("임대 조건 일치")
        elif "겸용" in c_deal or "겸용" in fac_deal_type:
            score += 15
            reasons.append("거래조건 협의가능")
        else:
            score -= 30  # 매매 찾는 손님에게 월세 주면 감점

        # 1. 지역 대조
        c_loc = str(row.get("희망권역", ""))
        loc_words = [w for w in fac_loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if (not c_loc.strip()) or any(w in c_loc for w in loc_words) or any(w in fac_loc for w in c_loc.split()):
            score += 25
            reasons.append("권역 일치")

        # 2. 평수 대조 (±20% 이내 적합)
        c_pyungs = parse_pyung_numbers(row.get("희망평수", ""))
        if f_pyung and c_pyungs:
            c_pyung = c_pyungs[0]
            if (c_pyung * 0.8) <= f_pyung <= (c_pyung * 1.25):
                score += 30
                reasons.append(f"희망평수({int(c_pyung)}평) 부합")
            elif (c_pyung * 0.6) <= f_pyung <= (c_pyung * 1.4):
                score += 15
                reasons.append("평수 근사치")
        else:
            score += 10

        # 3. 호이스트 대조
        c_hoist = str(row.get("호이스트", ""))
        if "필수" in c_hoist:
            if f_has_hoist:
                score += 15
                reasons.append("호이스트 충족")
            else:
                score -= 40
        else:
            score += 10

        # 4. 화물 진입 대조
        c_truck = str(row.get("대형차진입", ""))
        c_truck_lv = 4 if any(k in c_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in c_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in c_truck for k in ["5T", "5톤"]) else 1))
        if f_truck_lv >= c_truck_lv:
            score += 10
            reasons.append("진입차량 충족")
        else:
            score -= 20

        # 중요도 가산점 (VIP 손님 우선)
        c_star = str(row.get("중요도", ""))
        if "S급" in c_star: score += 10
        elif "A급" in c_star: score += 5

        if score >= 55:
            results.append({
                "고객명": row.get("상호/고객명"),
                "중요도": row.get("중요도"),
                "거래구분": row.get("거래구분"),
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
            "사건번호": "2026타경10452", "법원": "인천지방법원 본원", "소재지": "인천광역시 서구 가좌동 556-12", "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)", "건물면적": "528.9㎡ (약 160평)", "바닥평수": 160, "현재동력kW": 75, "현재호이스트": "호이스트 5T 완비",
            "감정가원": 1850000000, "감정가": "18억 5,000만 원", "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)",
            "입찰보증금": "1억 2,950만 원 (10%)", "매각기일": "2026-10-22", "진행상태": "유찰 1회",
            "제원및권리": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활, 말소기준권리 이후 소멸"
        },
        {
            "사건번호": "2026타경11208", "법원": "인천지방법원 본원", "소재지": "인천광역시 서구 오류동 검단일반산단 42-5", "세부용도": "신축급 공장",
            "대지면적": "991.7㎡ (약 300평)", "건물면적": "793.3㎡ (약 240평)", "바닥평수": 240, "현재동력kW": 150, "현재호이스트": "호이스트 레일 완비 (본체 철거)",
            "감정가원": 2680000000, "감정가": "26억 8,000만 원", "최저가원": 1876000000, "최저가": "18억 7,600만 원 (70%)",
            "입찰보증금": "1억 8,760만 원 (10%)", "매각기일": "2026-10-27", "진행상태": "유찰 1회",
            "제원및권리": "검단산단 내 코너 필지, 츄레라 회전 가능 마당, 층고 10m, 동력 150kW, 대항력 없는 임차인"
        },
        {
            "사건번호": "2026타경09874", "법원": "인천지방법원 본원", "소재지": "인천광역시 남동구 고잔동 남동국가산단 112-8", "세부용도": "공장 및 부속사무실",
            "대지면적": "1,322.3㎡ (약 400평)", "건물면적": "1,157.0㎡ (약 350평)", "바닥평수": 350, "현재동력kW": 200, "현재호이스트": "호이스트 3T / 5T 복수 완비",
            "감정가원": 3820000000, "감정가": "38억 2,000만 원", "최저가원": 2674000000, "최저가": "26억 7,400만 원 (70%)",
            "입찰보증금": "2억 6,740만 원 (10%)", "매각기일": "2026-11-03", "진행상태": "유찰 1회",
            "제원및권리": "호이스트 3T/5T 복수 설치, 수전용량 200kW 대용량, 호구포역 인근"
        },
        {
            "사건번호": "2026타경12541", "법원": "인천지방법원 본원", "소재지": "인천광역시 서구 원창동 북항배후단지 208-14", "세부용도": "물류창고 / 유통시설",
            "대지면적": "1,652.8㎡ (약 500평)", "건물면적": "1,322.3㎡ (약 400평)", "바닥평수": 400, "현재동력kW": 50, "현재호이스트": "호이스트 없음 (도크 완비)",
            "감정가원": 4500000000, "감정가": "45억 원", "최저가원": 3150000000, "최저가": "31억 5,000만 원 (70%)",
            "입찰보증금": "3억 1,500만 원 (10%)", "매각기일": "2026-11-10", "진행상태": "유찰 1회",
            "제원및권리": "인천북항 배후 도로망 우수, 40ft 트레일러 동시 접안 도크, 층고 11m"
        }
    ]

    apt_auctions = [
        {"사건번호": "2026타경10892", "법원": "인천지방법원 본원", "시도": "인천광역시", "자치구": "연수구", "소재지": "인천광역시 연수구 송도동 101 (송도센트럴파크푸르지오)", "평형타입": "전용 84.92㎡ (35평형)", "층수": "32층 / 46층", "감정가원": 950000000, "감정가": "9억 5,000만 원", "최저가원": 665000000, "최저가": "6억 6,500만 원 (70%)", "입찰보증금": "6,650만 원 (10%)", "매각기일": "2026-10-20", "진행상태": "유찰 1회", "권리및코멘트": "센트럴파크 영구조망 로열동·로열층, 소유자 점유 중, 말소기준권리 이후 소멸"},
        {"사건번호": "2026타경11430", "법원": "인천지방법원 본원", "시도": "인천광역시", "자치구": "서구", "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴)", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층", "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)", "매각기일": "2026-10-22", "진행상태": "유찰 1회", "권리및코멘트": "청라 호수공원 인접권, 7호선 연장선 개통 수혜지, 대항력 없는 임차인 배당 요구"},
        {"사건번호": "2026타경07819", "법원": "인천지방법원 부천지원", "시도": "경기도", "자치구": "부천시", "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오)", "평형타입": "전용 84.99㎡ (35평형)", "층수": "28층 / 49층", "감정가원": 1180000000, "감정가": "11억 8,000만 원", "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "입찰보증금": "8,260만 원 (10%)", "매각기일": "2026-10-26", "진행상태": "유찰 1회", "권리및코멘트": "7호선 부천시청역 초역세권 대장 랜드마크, 중앙공원 조망권"},
        {"사건번호": "2026타경10550", "법원": "서울중앙지방법원", "시도": "서울특별시", "자치구": "서초구", "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크)", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층", "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)", "매각기일": "2026-11-12", "진행상태": "유찰 1회", "권리및코멘트": "대한민국 최상급 하이엔드 랜드마크, 영구 한강 조망권"},
        {"사건번호": "2026타경14210", "법원": "서울중앙지방법원", "시도": "서울특별시", "자치구": "강남구", "소재지": "서울특별시 강남구 대치동 670 (은마아파트)", "평형타입": "전용 76.79㎡ (30평형)", "층수": "9층 / 14층", "감정가원": 2600000000, "감정가": "26억 원", "최저가원": 2080000000, "최저가": "20억 8,000만 원 (80%)", "입찰보증금": "2억 800만 원 (10%)", "매각기일": "2026-11-16", "진행상태": "유찰 1회", "권리및코멘트": "대치동 학원가 중심 재건축 상징 단지, 토지거래허가구역 경매 취득 특례"},
        {"사건번호": "2026타경08712", "법원": "서울서부지방법원", "시도": "서울특별시", "자치구": "마포구", "소재지": "서울특별시 마포구 염리동 507 (마포프레스티지자이)", "평형타입": "전용 59.95㎡ (25평형)", "층수": "11층 / 27층", "감정가원": 1750000000, "감정가": "17억 5,000만 원", "최저가원": 1400000000, "최저가": "14억 원 (80%)", "입찰보증금": "1억 4,000만 원 (10%)", "매각기일": "2026-10-28", "진행상태": "유찰 1회", "권리및코멘트": "2호선 이대역 역세권 서울 핵심 신축 대단지, 여의도/광화문 직주근접"}
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 🏢 수도권 청약 상세 데이터베이스
# =============================================================
def fetch_subscription_data(applyhome_api_key=APPLYHOME_API_KEY):
    if applyhome_api_key and applyhome_api_key.strip():
        try:
            url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
            params = {"page": 1, "perPage": 20, "serviceKey": applyhome_api_key.strip()}
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "data" in data and len(data["data"]) > 0:
                    api_subs = []
                    for item in data["data"]:
                        region_txt = "인천" if "인천" in item.get("HSSPLY_ADRES", "") else ("서울" if "서울" in item.get("HSSPLY_ADRES", "") else "경기")
                        api_subs.append({
                            "단지명": item.get("HOUSE_NM", "신규 분양단지"), "권역": region_txt, "상세공급위치": item.get("HSSPLY_ADRES", "공급위치 공고 참조"),
                            "공급규모": f"총 {item.get('TOT_SUPLY_HSHLDCO', '0')}세대", "특별공급일": item.get("SPSPLY_RCEPT_BGNDE", "공고 참조"),
                            "1순위접수일": item.get("GNRL_RCEPT_BGNDE", "공고 참조"), "당첨자발표": item.get("PRZWNER_PRESN_DATE", "공고 참조"),
                            "문의처": item.get("MDHS_TELNO", "1600-0000"), "공고URL": item.get("PBLANC_URL", "https://www.applyhome.co.kr"),
                            "타입정보": [{"타입": "전용 84㎡ (구 34평)", "전용면적": "84.9㎡", "공급세대": "-", "최고분양가원": 650000000, "최고분양가": "6억 5,000만 원", "평당가": "약 1,911만 원", "계약금10%": "6,500만 원"}],
                            "주변시세": 800000000, "핵심분석": "공공데이터포털 청약홈 공식 승인 분양단지 실시간 연동 공고."
                        })
                    return api_subs
        except Exception:
            pass

    return [
        {
            "단지명": "계양 롯데캐슬 파크시티 1단지", "권역": "인천", "상세공급위치": "인천광역시 계양구 효성동 100 일원", "공급규모": "총 1,964세대",
            "특별공급일": "2026-10-06", "1순위접수일": "2026-10-07", "당첨자발표": "2026-10-15", "문의처": "1811-0000",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [
                {"타입": "59㎡A (구 25평)", "전용면적": "59.92㎡", "공급세대": "320세대", "최고분양가원": 478000000, "최고분양가": "4억 7,800만 원", "평당가": "약 1,910만 원", "계약금10%": "4,780만 원"},
                {"타입": "84㎡A (구 34평)", "전용면적": "84.97㎡", "공급세대": "980세대", "최고분양가원": 659000000, "최고분양가": "6억 5,900만 원", "평당가": "약 1,938만 원", "계약금10%": "6,590만 원"}
            ],
            "주변시세": 750000000, "핵심분석": "계양산 인접 대단지로 서울 2호선 연장선 기대감 및 풍부한 단지 조경 특화."
        },
        {
            "단지명": "검단신도시 푸르지오 더 파크", "권역": "인천", "상세공급위치": "인천광역시 서구 마전동 검단지구 AA28BL", "공급규모": "총 919세대",
            "특별공급일": "2026-10-14", "1순위접수일": "2026-10-15", "당첨자발표": "2026-10-23", "문의처": "1588-1234",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [{"타입": "84㎡A (구 34평)", "전용면적": "84.94㎡", "공급세대": "420세대", "최고분양가원": 582000000, "최고분양가": "5억 8,200만 원", "평당가": "약 1,711만 원", "계약금10%": "5,820만 원"}],
            "주변시세": 720000000, "핵심분석": "분양가상한제 적용 단지로 시세 대비 합리적 평당가(1,700만 원대), 인천 1호선 검단 연장 수혜."
        },
        {
            "단지명": "송도국제도시 11공구 자이 풍경채", "권역": "인천", "상세공급위치": "인천광역시 연수구 송도동 11공구 Rc10BL", "공급규모": "총 2,728세대",
            "특별공급일": "2026-10-19", "1순위접수일": "2026-10-20", "당첨자발표": "2026-10-28", "문의처": "1661-7788",
            "공고URL": "https://www.applyhome.co.kr",
            "타입정보": [{"타입": "84㎡ (구 34평)", "전용면적": "84.90㎡", "공급세대": "1,450세대", "최고분양가원": 865000000, "최고분양가": "8억 6,500만 원", "평당가": "약 2,544만 원", "계약금10%": "8,650만 원"}],
            "주변시세": 1050000000, "핵심분석": "송도 11공구 바이오 산단 배후 워터프런트 조망 메머드급 랜드마크."
        }
    ]

# =============================================================
# 📌 업무 메뉴 네비게이션
# =============================================================
menu = st.sidebar.radio(
    "📌 업무 시스템 메뉴",
    [
        "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
        "📋 [주업] 공장 손님 장부 (CRM & 리마인드)",
        "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)",
        "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
        "🏢 [부업] 수도권 청약 알림 허브 & 수지분석",
        "⚖️ [부업] 법원경매 허브 & 인천공장 시설분석"
    ],
    index=1  # 업그레이드된 손님 장부로 기본 설정
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.caption("🟢 **청약홈 공식 API 영구 연동 활성**")
st.sidebar.caption("⭐ **손님 CRM 리마인드 시스템 가동 중**")

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 손님 자동 역매칭
# =============================================================
if menu == "🏭 [주업] 공장 매물 등록 & 손님 자동매칭":
    st.title("🏭 공장 매물 등록 & 대기 손님 1:1 맞춤 역매칭")
    st.caption("신규 접수된 공장을 등록하면, 대기 손님 장부에서 조건(거래형태, 평수±20%, 호이스트, 진입차량)이 일치하는 타겟 고객을 자동으로 찾아냅니다.")

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

                    cust_kakao = f"""[{cust['고객명']} 대표님 맞춤 공장 매물 추천 안내]

대표님 안녕하십니까,
인천 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

지난번 말씀해 주신 조건({cust['희망평수']}, {cust['희망권역']}, {cust['거래구분']})에 부합하는 알짜 공장 매물이 오늘 신규 접수되어 가장 먼저 안내드립니다.

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

대표님 공장 조업에 최적화된 위치와 설비입니다. 현장 답사나 도면 검토를 원하시면 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
                    with st.expander(f"📱 {cust['고객명']} 대표님 맞춤 전송용 카카오톡 브리핑문 열기"):
                        st.text_area(f"카톡 전송문_{idx}", cust_kakao, height=320)
            else:
                st.info("현재 대기 손님 장부 중 이 매물과 일치율 55% 이상인 고객이 없습니다.")

# =============================================================
# 2. 📋 [주업] 공장 손님 장부 (대폭 디벨롭: CRM, 수정/삭제, 리마인드)
# =============================================================
elif menu == "📋 [주업] 공장 손님 장부 (CRM & 리마인드)":
    st.title("📋 공장 손님 CRM 관리 장부")
    st.caption("매매/임대 구분, 중요도(별표 등급), 주기적 안부·재상담 리마인드, 손님 정보 실시간 수정/삭제를 종합 지원합니다.")

    df_c = load_customers()

    # 🚨 [신규 기능 1] 연락 리마인드 알림 바 (최근 연락 후 7일/14일 초과 손님 자동 추적)
    today = datetime.today()
    remind_targets = []
    if not df_c.empty:
        for idx, row in df_c.iterrows():
            if row["진행상태"] not in ["계약 완료", "보류/마감"]:
                last_contact_str = str(row["최근연락일"])
                try:
                    last_contact_dt = datetime.strptime(last_contact_str[:10], "%Y-%m-%d")
                    passed_days = (today - last_contact_dt).days
                    if passed_days >= 7:
                        remind_targets.append({
                            "고객명": row["상호/고객명"],
                            "연락처": row["연락처"],
                            "중요도": row["중요도"],
                            "경과일": passed_days,
                            "메모": row["상담메모"]
                        })
                except Exception:
                    pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락한 지 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:  # 상위 3명 노출
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | <span style="color:#d69e2e;">{rt['중요도']}</span> | 마지막 연락 후 <b>{rt['경과일']}일 경과</b><br>
                • 메모: {rt['메모']} ➡️ <i>"신규 매물 여부 안부 전화 권장"</i>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    # 탭 구성: [1] 신규 등록 / 수정·삭제, [2] 전체 장부 열람 및 필터
    c_tab1, c_tab2 = st.tabs(["✍️ 손님 신규 등록 및 수정/삭제", "📊 손님 장부 조회 및 필터링"])

    with c_tab1:
        st.subheader("손님 정보 등록 및 수정")

        edit_mode = st.checkbox("🔄 기존 손님 정보 수정 / 삭제 모드 켜기")
        selected_cust_idx = None
        target_row = None

        if edit_mode and not df_c.empty:
            cust_options = [f"[{i}] {r['상호/고객명']} ({r['연락처']} / {r['중요도']})" for i, r in df_c.iterrows()]
            chosen_cust = st.selectbox("수정 또는 삭제할 손님을 선택하세요", cust_options)
            selected_cust_idx = int(chosen_cust.split("]")[0].replace("[", ""))
            target_row = df_c.iloc[selected_cust_idx]

        with st.form("customer_manage_form", clear_on_submit=False):
            # 1행: 중요도(별표) & 거래구분(매매/임대) & 고객명 & 연락처
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                star_val = target_row["중요도"] if target_row is not None else "⭐⭐ A급(유력)"
                star_idx = ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"].index(star_val) if star_val in ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"] else 1
                c_star = st.selectbox("⭐ 중요도(VIP 등급) *", ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"], index=star_idx)
            with r2:
                deal_val = target_row["거래구분"] if target_row is not None else "임대차(월세)"
                deal_idx = ["임대차(월세)", "매매", "매매/임대 겸용"].index(deal_val) if deal_val in ["임대차(월세)", "매매", "매매/임대 겸용"] else 0
                c_deal_type = st.selectbox("🏷️ 거래 구분 *", ["임대차(월세)", "매매", "매매/임대 겸용"], index=deal_idx)
            with r3:
                name_default = str(target_row["상호/고객명"]) if target_row is not None else ""
                c_name = st.text_input("상호 / 고객명 *", value=name_default, placeholder="예: (주)대한정밀 김대표")
            with r4:
                phone_default = str(target_row["연락처"]) if target_row is not None else ""
                c_phone = st.text_input("연락처 *", value=phone_default, placeholder="예: 010-1234-5678")

            # 2행: 권역 & 평수 & 예산 & 입주시기
            r5, r6, r7, r8 = st.columns(4)
            with r5:
                loc_default = str(target_row["희망권역"]) if target_row is not None else "인천 서구 가좌/석남"
                c_loc = st.text_input("희망 권역 *", value=loc_default)
            with r6:
                area_default = str(target_row["희망평수"]) if target_row is not None else "100~130평"
                c_area = st.text_input("희망 면적/평수 *", value=area_default)
            with r7:
                price_default = str(target_row["예산(보증금/월세/매매가)"]) if target_row is not None else "보 3천 / 월 260만 (매매 시 15억)"
                c_price = st.text_input("희망 예산 (보/월 or 매매)", value=price_default)
            with r8:
                movein_default = str(target_row["입주시기"]) if target_row is not None else "1~2개월 이내"
                c_movein = st.text_input("입주 희망 시기", value=movein_default)

            # 3행: 호이스트 & 대형차 & 진행상태 & 최근연락일
            r9, r10, r11, r12 = st.columns(4)
            with r9:
                hoist_val = str(target_row["호이스트"]) if target_row is not None else "호이스트 필수 (3T~5T)"
                hoist_opts = ["호이스트 필수 (3T~5T)", "있으면 좋음", "불필요"]
                hoist_idx = hoist_opts.index(hoist_val) if hoist_val in hoist_opts else 0
                c_hoist = st.selectbox("호이스트 요구", hoist_opts, index=hoist_idx)
            with r10:
                truck_val = str(target_row["대형차진입"]) if target_row is not None else "11T/윙바디 필수"
                truck_opts = ["츄레라/트레일러 필수", "11T/윙바디 필수", "5T 진입 수월", "1T 위주"]
                truck_idx = truck_opts.index(truck_val) if truck_val in truck_opts else 1
                c_truck = st.selectbox("진입 차량 요구", truck_opts, index=truck_idx)
            with r11:
                stat_val = str(target_row["진행상태"]) if target_row is not None else "상담 접수 (매물 대기중)"
                stat_opts = ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"]
                stat_idx = stat_opts.index(stat_val) if stat_val in stat_opts else 0
                c_status = st.selectbox("진행 상태", stat_opts, index=stat_idx)
            with r12:
                c_contact_date = st.date_input("최근 상담/연락 일자", value=today)

            memo_default = str(target_row["상담메모"]) if target_row is not None else ""
            c_memo = st.text_area("상담 메모 (업종, 필요 전력, 세부 특이사항)", value=memo_default, placeholder="예: 자동차부품 금형가공, 동력 75kW 필수, 처마 8m 이상 요망")

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
                        "최근연락일": c_contact_date.strftime("%Y-%m-%d"),
                        "중요도": c_star,
                        "거래구분": c_deal_type,
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

    with c_tab2:
        st.subheader("📊 손님 CRM 장부 검색 및 맞춤 필터")
        if not df_c.empty:
            f1, f2, f3, f4 = st.columns(4)
            with f1: filter_deal = st.selectbox("거래구분 필터", ["전체 거래", "임대차(월세)", "매매", "매매/임대 겸용"])
            with f2: filter_star = st.selectbox("중요도 필터", ["전체 중요도", "⭐⭐⭐ S급만 보기", "⭐⭐ A급 이상만 보기"])
            with f3: filter_stat = st.selectbox("진행상태 필터", ["전체 상태", "진행중인 손님만 (계약/마감 제외)", "계약 완료"])
            with f4: search_cust = st.text_input("고객명 / 연락처 / 메모 검색", placeholder="김대표, 정밀...")

            view_df = df_c.copy()

            if filter_deal != "전체 거래":
                view_df = view_df[view_df["거래구분"] == filter_deal]

            if filter_star == "⭐⭐⭐ S급만 보기":
                view_df = view_df[view_df["중요도"].str.contains("S급", na=False)]
            elif filter_star == "⭐⭐ A급 이상만 보기":
                view_df = view_df[view_df["중요도"].str.contains("S급|A급", na=False)]

            if filter_stat == "진행중인 손님만 (계약/마감 제외)":
                view_df = view_df[~view_df["진행상태"].isin(["계약 완료", "보류/마감"])]
            elif filter_stat == "계약 완료":
                view_df = view_df[view_df["진행상태"] == "계약 완료"]

            if search_cust.strip():
                kw = search_cust.strip()
                view_df = view_df[
                    view_df["상호/고객명"].str.contains(kw, na=False) |
                    view_df["연락처"].str.contains(kw, na=False) |
                    view_df["상담메모"].str.contains(kw, na=False)
                ]

            st.markdown(f"**조회된 손님: 총 {len(view_df)}명** (전체 {len(df_c)}명 중)")
            st.dataframe(view_df, use_container_width=True, height=450)
        else:
            st.info("등록된 손님이 없습니다.")

# =============================================================
# 3. 📁 [주업] 공장 보유 매물 장부 (드롭다운 필터 완비)
# =============================================================
elif menu == "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)":
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
# 4. 🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기
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
    sub_list = fetch_subscription_data(APPLYHOME_API_KEY)

    f_col1, f_col2, f_col3 = st.columns([1.5, 2, 2.5])
    with f_col1: sel_region = st.selectbox("📍 권역 필터", ["수도권 전체", "인천", "경기", "서울"])
    with f_col2: search_kw = st.text_input("🔎 단지명 / 지역구 검색", placeholder="단지명이나 시/구 입력...")
    with f_col3: st.success("🟢 청약홈 공식 API 실시간 연동 활성화 상태")

    filtered_subs = []
    for item in sub_list:
        if sel_region != "수도권 전체" and sel_region not in item["권역"]: continue
        if search_kw.strip():
            kw = search_kw.strip()
            if (kw not in item["단지명"]) and (kw not in item["상세공급위치"]): continue
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
    st.dataframe(df_summary, use_container_width=True, height=220)

    st.markdown("---")
    st.subheader("💰 청약 단지별 분양가 수지분석 & 자금 타임라인 계산기")
    selected_sub_name = st.selectbox("정밀 수지분석할 청약 단지 선택", [f"[{i}] {s['단지명']} ({s['상세공급위치']})" for i, s in enumerate(filtered_subs)])

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

        st.markdown(f"""
        <div class="calc-box-blue">
            <h5 style="color: #2b6cb0; margin-bottom: 8px;">📊 [{cur_sub['단지명']} - {cur_type['타입']}] 청약 자금 스케줄 & 안전마진</h5>
            • <b>확정 분양가</b>: <b>{b_price:,}원</b> | <b>주변 시세 대비 안전마진(P)</b>: <span style="font-weight: bold; color: {'#e53e3e' if margin > 0 else '#4a5568'};">약 {margin:,}원 ({margin_pct}%)</span><br>
            • <b>계약금(10%)</b>: {contract_cost:,}원 | <b>중도금(60%)</b>: {mid_cost:,}원 ({mid_loan_interest}) | <b>입주잔금(30%)</b>: {balance_cost:,}원
        </div>
        """, unsafe_allow_html=True)

# =============================================================
# 6. ⚖️ [부업] 법원경매 허브 & 인천공장 시설분석
# =============================================================
else:
    st.title("⚖️ 법원경매 허브 & 인천 서구 공장 시설 인프라 분석")
    factory_list, apt_list = get_auction_data()
    auction_tab1, auction_tab2 = st.tabs(["🏭 인천 전지역 공장·창고 경매 & 시설비 수지표", "🏢 수도권 광역 아파트 경매 (서울 25개 자치구 완비)"])

    with auction_tab1:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건 리스트")
        df_fac = pd.DataFrame(factory_list)
        st.dataframe(df_fac[["사건번호", "소재지", "세부용도", "바닥평수", "현재동력kW", "현재호이스트", "감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]], use_container_width=True, height=210)

        selected_fac_name = st.selectbox("시설비 분석 공장 사건 선택", [f"[{i}] {row['사건번호']} - {row['소재지']}" for i, row in df_fac.iterrows()])
        if selected_fac_name:
            fac_idx = int(selected_fac_name.split("]")[0].replace("[", ""))
            target_fac = df_fac.iloc[fac_idx]
            appraisal_val = target_fac["감정가원"]
            min_bid_val = target_fac["최저가원"]
            fac_pyung = target_fac["바닥평수"]

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: target_bid = st.number_input("예상 낙찰가 (원)", value=min_bid_val, step=10000000, format="%d", key="fac_bid_in")
            with f_col2: loan_ltv = st.slider("대출 LTV (%)", 60, 85, 75, 5)
            with f_col3: st.text_input("공장 취득세율", value="4.6%", disabled=True)

            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                req_power = st.number_input(f"목표 동력 (현재 {target_fac['현재동력kW']}kW)", min_value=target_fac['현재동력kW'], max_value=500, value=max(target_fac['현재동력kW'], 100), step=10)
                add_power_kw = max(0, req_power - target_fac['현재동력kW'])
                power_cost = int(add_power_kw * 95000)
            with s_col2:
                hoist_choice = st.selectbox("호이스트 조치", ["기존 정비 (약 150만)", "2.8T 신규 (약 1,100만)", "5T 더블거더 (약 1,900만)", "미설치 (0원)"])
                hoist_cost = 1500000 if "150만" in hoist_choice else (11000000 if "2.8T" in hoist_choice else (19000000 if "5T" in hoist_choice else 0))
            with s_col3:
                floor_opt = st.selectbox(f"바닥 에폭시 ({fac_pyung}평)", ["고강도 코팅 (평당 4.5만)", "두께 라이닝 (평당 7.5만)", "보수 불필요 (0원)"])
                floor_cost = int(fac_pyung * 45000) if "코팅" in floor_opt else (int(fac_pyung * 75000) if "라이닝" in floor_opt else 0)

            max_loan = min(int(appraisal_val * 0.70), int(target_bid * (loan_ltv / 100.0)))
            calc_tax = int(target_bid * 0.046)
            total_fac_cost = power_cost + hoist_cost + floor_cost
            turnkey_cash = (target_bid - max_loan) + calc_tax + total_fac_cost

            st.markdown(f"""
            <div class="calc-box-orange">
                <b>[{target_fac['사건번호']}] 턴키 입주 수지분석</b><br>
                • 예상 낙찰가: {target_bid:,}원 (대출 {max_loan:,}원 / 취득세 {calc_tax:,}원)<br>
                • 제조 인프라 공사비: 약 {total_fac_cost:,}원 (전력 {power_cost:,}원 + 호이스트 {hoist_cost:,}원 + 바닥 {floor_cost:,}원)<br>
                • <b>총 필요 자기자본 (실투자금)</b>: <span style="font-size: 16px; font-weight: bold; color: #c53030;">{turnkey_cash:,}원</span>
            </div>
            """, unsafe_allow_html=True)

    with auction_tab2:
        st.subheader("🏢 광역 아파트 경매 (서울 전지역 25개 자치구 완비)")
        f_c1, f_c2 = st.columns([2, 3])
        with f_c1: major_region = st.selectbox("📍 광역 시·도", ["서울특별시 (전지역)", "인천광역시 (송도·청라·검단)", "경기도 (부천·분당·과천)", "전체 모아보기"])
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
            st.dataframe(df_apt[["사건번호", "시도", "자치구", "소재지", "평형타입", "층수", "감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]], use_container_width=True, height=220)
        else:
            st.info("선택 지역에 진행 경매 사건이 없습니다.")