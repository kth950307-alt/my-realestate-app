import streamlit as st
import pandas as pd
import os
import re
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="우리부동산 통합 업무 시스템", page_icon="🏢", layout="wide")

# 크롬/사파리 번역 방지 및 공통 스타일 (기울임체 전면 금지)
st.markdown("""
<script>
    document.documentElement.lang = 'ko';
    document.documentElement.classList.add('notranslate');
    document.documentElement.setAttribute('translate', 'no');
</script>
<meta name="google" content="notranslate">
<div translate="no" class="notranslate">
<style>
    html, body, [data-testid="stAppViewContainer"], .notranslate { translate: no !important; font-style: normal !important; }
    .hunt-item-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #3182ce; border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; }
    .hunt-item-done { background-color: #f0fff4; border: 1px solid #c6f6d5; border-left: 5px solid #38a169; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; }
    .customer-card-pro { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid #3182ce; border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.04); }
    .customer-card-pro-vip { background-color: #fffdf7; border: 1px solid #feebc8; border-left: 6px solid #dd6b20; border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 2px 6px rgba(221,107,32,0.1); }
    .tag-blue { background-color: #ebf8ff; color: #2b6cb0; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-orange { background-color: #fffaf0; color: #c05621; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-green { background-color: #f0fff4; color: #276749; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-gray { background-color: #edf2f7; color: #4a5568; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 600; margin-right: 5px; display: inline-block; }
    .remind-card-red { background-color: #fff5f5; border-left: 5px solid #e53e3e; border: 1px solid #fed7d7; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-weight: 600; }
    .calc-box-orange { background-color: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 16px; margin: 10px 0; line-height: 1.7; }
    .calc-box-blue { background-color: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 16px; margin: 10px 0; line-height: 1.7; }
    .check-list-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #4a5568; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; font-size: 13.5px; line-height: 1.7; }
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"], .stButton, header, footer { display: none !important; }
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 보안 잠금 (950307)
# =============================================================
CORRECT_PASSWORD = "950307"
if not st.session_state.get("authenticated", False):
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>### 🏢 우리부동산 통합 업무 시스템", unsafe_allow_html=True)
        st.caption("인천 서구 공장 전문 중개 & 실시간 청약·법원경매 통합 허브")
        pwd_input = st.text_input("사무실 전용 비밀번호", type="password", key="pwd_box")
        if st.button("🔓 시스템 접속하기", type="primary", use_container_width=True):
            if pwd_input == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
    st.stop()

# =============================================================
# ⚡ 4대 CSV 데이터베이스 관리 함수
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"
NEW_DEV_CSV = "new_developments.csv"
HUNTING_CSV = "hunting_properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        for col, d_val in [
            ("예산(보증금/월세/매매가)", ""), ("거래구분", "임대차(월세)"), ("중요도", "⭐⭐ A급(유력)"),
            ("최근연락일", datetime.today().strftime("%Y-%m-%d")), ("업종인허가", "일반제조(소음·진동)"),
            ("입주시기", "협의 입주"), ("호이스트", "호이스트 무관"), ("대형차진입", "11T 윙바디 수월"),
            ("희망전력kW", "일반전력(30kW 내외)"), ("상담히스토리", "")
        ]:
            if col not in df.columns: df[col] = d_val
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

def load_hunting_properties():
    if os.path.exists(HUNTING_CSV):
        return pd.read_csv(HUNTING_CSV)
    init_data = [
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-822", "건물유형": "집합공장", "소재지전체": "인천 서구 석남동 223-822", "소유자/법인명": "관리사무소/집합", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "집합공장. 관리사무소 방문하여 임대/매매 호실 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-932", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-932", "소유자/법인명": "홍정미", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "개인소유. 현장 방문하여 건물주 연락처 탐문"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-651", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-651", "소유자/법인명": "소유자 확인중", "상호": "", "연락처": "", "진행상태": "📞 전화 확인", "현장메모": "대장 열람 후 유선 컨택"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-360", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-360", "소유자/법인명": "이해영, 최완규", "상호": "신창코팅", "연락처": "032-577-0104", "진행상태": "📞 전화 확인", "현장메모": "신창코팅 유선 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-559", "건물유형": "운수/차고지", "소재지전체": "인천 서구 석남동 223-559", "소유자/법인명": "한미교통주식회사", "상호": "한미교통", "연락처": "032-571-1032", "진행상태": "📞 전화 확인", "현장메모": "법인 총무팀 유선 컨택"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-557", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-557", "소유자/법인명": "김용주", "상호": "명인기공", "연락처": "032-579-3171", "진행상태": "🚗 방문 필요", "현장메모": "명인기공 방문 및 유선 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-835", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-835", "소유자/법인명": "박용욱", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "개인소유 방문 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-786", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-786", "소유자/법인명": "진우조명", "상호": "진우조명", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "진우조명 현장 방문"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-886", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-886", "소유자/법인명": "안민영", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "현장 방문 조사 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-881", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-881", "소유자/법인명": "권진주", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "현장 방문 조사 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-855", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-855", "소유자/법인명": "성용욱", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "현장 방문 조사 필요"}
    ]
    df = pd.DataFrame(init_data)
    df.to_csv(HUNTING_CSV, index=False, encoding="utf-8-sig")
    return df

def save_all_hunting(df): df.to_csv(HUNTING_CSV, index=False, encoding="utf-8-sig")

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

def get_safe_cust_val(row, col_name, default=""):
    val = row.get(col_name, default)
    if pd.isna(val) or str(val).strip() in ["", "nan"]:
        if col_name == "예산(보증금/월세/매매가)": val = row.get("예산(보증금/월세)", default)
        else: val = default
    return str(val) if pd.notna(val) else default

# 양방향 매칭 엔진 (손님 -> 매물, 매물 -> 손님)
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
        loc_words = [w for w in c_loc.replace("(", " ").replace(")", " ").replace("/", " ").split() if len(w) >= 2]
        if loc_words and not any(w in p_loc for w in loc_words): continue
        p_pyungs = parse_pyung_numbers(p_area)
        if c_pyung and p_pyungs:
            if not ((c_pyung * 0.70) <= p_pyungs[0] <= (c_pyung * 1.35)): continue
        matched_props.append(prop)
    return matched_props

def match_customers_for_property(loc_str, area_str):
    df_c = load_customers()
    if df_c.empty: return []
    p_pyungs = parse_pyung_numbers(area_str)
    p_pyung = p_pyungs[0] if p_pyungs else None

    matched_custs = []
    for _, cust in df_c.iterrows():
        if str(cust.get("진행상태", "")) in ["계약 완료", "보류/마감"]: continue
        c_loc = str(cust.get("희망권역", ""))
        loc_words = [w for w in loc_str.replace("인천", "").replace("서구", "").split() if len(w) >= 2]
        if loc_words and not any(w in c_loc for w in loc_words): continue
        c_pyungs = parse_pyung_numbers(cust.get("희망평수", ""))
        if p_pyung and c_pyungs:
            if not ((c_pyungs[0] * 0.70) <= p_pyung <= (c_pyungs[0] * 1.35)): continue
        matched_custs.append(cust)
    return matched_custs

# =============================================================
# ⚖ 대법원 법원경매 정밀 데이터베이스 (수도권 아파트 + 인천 공장 전수)
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
            "사건번호": "2026타경10550", "법원": "서울중앙지방법원 (경매4계)", "시도": "서울특별시",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크 104동)", "주택유형": "아파트", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층 (로열층 한강뷰)",
            "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회", "실거래시세원": 4500000000, "최근실거래가": "45억 원 선",
            "권리분석": {"말소기준권리": "2019-12-10 근저당권 (신한은행)", "임차인분석": "소유자 세대 점유 (대항력 있는 임차인 없음)", "인수보증금": 0, "토허제특례": "경매 취득 시 토지거래허가구역 실거주의무 면제 (전세 갭투자 가능)", "명도난이도": "보통 (소유자 거주, 협의 수월)"},
            "미납관리비": 1800000, "추천입찰가밴드": "36억 5,000만 ~ 37억 8,000만 원", "예상시세차익": "약 7억 ~ 8.5억 원",
            "배당정보": {"경매비용": 18000000, "당해세": 15000000, "최우선변제": 0, "선순위근저당": 2800000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경07819", "법원": "인천지방법원 부천지원 (경매2계)", "시도": "경기도",
            "소재지": "경기도 부천시 원미구 중동 1162 (중동 센트럴파크 푸르지오 102동)", "주택유형": "주상복합 아파트", "평형타입": "전용 84.99㎡ (35평형)", "층수": "28층 / 49층 (고층 공원뷰)",
            "감정가원": 1180000000, "감정가": "11억 8,000만 원", "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "입찰보증금": "8,260만 원 (10%)",
            "매각기일": "2026-10-26", "진행상태": "유찰 1회", "실거래시세원": 1200000000, "최근실거래가": "12억 원 선",
            "권리분석": {"말소기준권리": "2020-09-03 근저당권 (농협은행)", "임차인분석": "소유자 세대 점유 (선순위 임차인 없음)", "인수보증금": 0, "토허제특례": "비규제지역 (대출 수월)", "명도난이도": "수월 (인도명령 인용)"},
            "미납관리비": 1100000, "추천입찰가밴드": "9억 1,000만 ~ 9억 4,000만 원", "예상시세차익": "약 2.6억 ~ 2.9억 원",
            "배당정보": {"경매비용": 8500000, "당해세": 3200000, "최우선변제": 0, "선순위근저당": 650000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2026타경11430", "법원": "인천지방법원 본원 (경매6계)", "시도": "인천광역시",
            "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴 302동)", "주택유형": "아파트", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층",
            "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)",
            "매각기일": "2026-10-22", "진행상태": "유찰 1회", "실거래시세원": 810000000, "최근실거래가": "8억 1,000만 원 선",
            "권리분석": {"말소기준권리": "2021-02-18 근저당권 (신한은행)", "임차인분석": "후순위 임차인 (보증금 1억 원 전액 배당 소멸)", "인수보증금": 0, "토허제특례": "비규제지역 (경락대출 70~80% 가능)", "명도난이도": "보통 (이사비 협의 권장)"},
            "미납관리비": 450000, "추천입찰가밴드": "6억 2,000만 ~ 6억 4,500만 원", "예상시세차익": "약 1.7억 ~ 1.9억 원",
            "배당정보": {"경매비용": 6500000, "당해세": 2400000, "최우선변제": 0, "선순위근저당": 420000000, "임차인배당": 100000000},
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 📌 업무 메뉴 네비게이션 (9개 핵심 파이프라인)
# =============================================================
MENU_DICT = {
    "FACTORY_HUNT": "🏃 [임장/작업] 현장 공장 물건따기 파이프라인",
    "FACTORY_REG": "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
    "NEW_DEV": "🏗️ [주업] 신축공장 맞춤 분양 설계 & 제안서",
    "CUSTOMER_CRM": "📋 [주업] 공장 손님 장부 (CRM & 리마인드)",
    "FACTORY_BOOK": "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)",
    "PRICE_AI": "🔍 [주업] 공장·창고 AI 시세 추정기",
    "BLOG_TOOL": "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
    "APPLY_HOME": "🏢 [부업] 실시간 청약·줍줍 & LH 공공임대 허브",
    "AUCTION_HUB": "⚖️ [부업] 법원경매 허브 & 수도권 주택·공장 정밀분석"
}

menu_choice = st.sidebar.radio("📌 업무 시스템 메뉴", list(MENU_DICT.values()), index=0)
st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()
st.sidebar.caption("🏢 **우리부동산 대표 공인중개사 김태형 전용 시스템**")

# =============================================================
# 0. 🏃 [임장/작업] 현장 공장 물건따기 파이프라인 (확보완료창 분리 & 원클릭 이관)
# =============================================================
if menu_choice == MENU_DICT["FACTORY_HUNT"]:
    st.title("🏃 현장 공장 물건따기 파이프라인 (임장 장부)")
    st.caption("작업 중 지번 ➡️ 확보 성공 ➡️ '🎉 확보완료 매물함'으로 즉시 분리 이관 및 1번 탭 정식 매물 원클릭 등록 지원!")

    df_h = load_hunting_properties()

    cnt_total = len(df_h)
    cnt_visit = len(df_h[df_h["진행상태"].str.contains("방문", na=False)])
    cnt_call = len(df_h[df_h["진행상태"].str.contains("전화", na=False)])
    cnt_done = len(df_h[df_h["진행상태"].str.contains("완료", na=False)])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📌 전체 작업 지번", f"{cnt_total}건")
    m2.metric("🚗 현장 방문 대상", f"{cnt_visit}건")
    m3.metric("📞 전화 확인 대상", f"{cnt_call}건")
    m4.metric("🎉 물건 확보 성공", f"{cnt_done}건")

    st.markdown("---")
    h_tab1, h_tab_done, h_tab2 = st.tabs([
        "🚗 [작업 중] 현장 임장·컨택 리스트",
        "🎉 [수주 성공] 확보 완료 매물함 (정식 매물 이관)",
        "📥 [텍스트 일괄 붙여넣기] 지번 자동 등록"
    ])

    with h_tab1:
        f1, f2, f3, f4 = st.columns([1.3, 1.3, 1.8, 1.2])
        all_dongs = ["전체 동 모아보기"] + sorted(list(df_h["동"].dropna().unique()))
        with f1: sel_dong = st.selectbox("📍 법정동 필터", all_dongs, key="hunt_d_f")
        with f2: sel_stat = st.selectbox("🚦 진행상태 필터", ["전체 상태", "🚗 방문 필요", "📞 전화 확인", "🔄 재트라이", "보류/거절"], key="hunt_s_f")
        with f3: kw_hunt = st.text_input("🔎 지번 / 상호 / 소유자 검색", placeholder="예: 223-360, 신창코팅...", key="hunt_k_f")
        with f4:
            st.write("")
            st.link_button("📄 정부24 건축물대장 열람", "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098", use_container_width=True)

        active_df = df_h[~df_h["진행상태"].str.contains("완료", na=False)].copy()
        if sel_dong != "전체 동 모아보기": active_df = active_df[active_df["동"] == sel_dong]
        if sel_stat != "전체 상태": active_df = active_df[active_df["진행상태"].str.contains(sel_stat.replace("🚗 ","").replace("📞 ","").replace("🔄 ",""), na=False)]
        if kw_hunt.strip():
            kw = kw_hunt.strip()
            active_df = active_df[active_df["지번"].astype(str).str.contains(kw, na=False) | active_df["소유자/법인명"].astype(str).str.contains(kw, na=False) | active_df["상호"].astype(str).str.contains(kw, na=False)]

        if active_df.empty:
            st.info("현재 작업 중인 지번이 없습니다. (확보 완료된 물건은 상단 '🎉 확보 완료 매물함'에서 확인하세요)")
        else:
            status_opts = ["🚗 방문 필요", "📞 전화 확인", "🔄 재트라이", "보류/거절"]
            for idx, r in active_df.iterrows():
                full_addr = f"인천 서구 {r['동']} {r['지번']}"
                map_url = f"https://map.naver.com/p/search/{full_addr.replace(' ', '%20')}"

                owner_info = f"👤 {r['소유자/법인명']}"
                if str(r.get("상호", "")).strip(): owner_info += f" ({r['상호']})"
                if str(r.get("연락처", "")).strip(): owner_info += f" 📞 {r['연락처']}"

                curr_st = str(r["진행상태"])
                st_idx = 0
                for s_i, s_name in enumerate(status_opts):
                    if s_name.split()[-1] in curr_st:
                        st_idx = s_i
                        break

                c_info, c_map, c_status, c_done_btn = st.columns([3.8, 0.9, 1.3, 1.2])
                with c_info:
                    st.markdown(f"**📍 {r['동']} {r['지번']}** <span class='tag-blue'>{r['건물유형']}</span> <span style='font-size:13px; color:#4a5568;'>{owner_info}</span><br><span style='font-size:12px; color:#718096;'>💡 {r.get('현장메모','')}</span>", unsafe_allow_html=True)
                with c_map:
                    st.link_button("🗺️ 로드뷰", map_url, use_container_width=True)
                with c_status:
                    new_st = st.selectbox("상태", status_opts, index=st_idx, key=f"hst_{idx}", label_visibility="collapsed")
                    if new_st != r["진행상태"]:
                        df_h.at[idx, "진행상태"] = new_st
                        save_all_hunting(df_h)
                        st.rerun()
                with c_done_btn:
                    if st.button("🎉 확보 완료!", key=f"h_done_{idx}", type="primary", use_container_width=True):
                        df_h.at[idx, "진행상태"] = "🎉 확보 완료"
                        save_all_hunting(df_h)
                        st.success(f"🎉 {r['동']} {r['지번']} 확보 성공! 확보완료함으로 이관되었습니다.")
                        st.rerun()

                st.markdown("<hr style='margin:3px 0 6px 0; border:0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)

        with st.expander("💬 건물주/대표님 부재 시 문자·카톡 발송 표준 문구 복사"):
            sms_tpl = """안녕하십니까 대표님! 인천 서구 공장·창고 전문 우리부동산 김태형 대표공인중개사입니다.
소유하고 계신 공장과 관련하여 우량 제조기업 임차(매수) 대기 수요가 있어 귀한 인연 맺고자 연락드렸습니다.
혹시 향후 임대차 만기나 매각 계획이 있으시다면 편하게 말씀 남겨주십시오. 신속하고 정확하게 브리핑 진행해 드리겠습니다!
- 우리부동산 대표 김태형 올림 (010-2660-8276)"""
            st.text_area("문자 복사용", sms_tpl, height=110)

    with h_tab_done:
        st.subheader("🎉 [수주 성공] 확보 완료 매물함")
        st.caption("건물주·관리인 컨택에 성공해 중개를 수락받은 매물들입니다. 금액/평수를 기재한 후 [1번 탭 정식 매물로 이관]을 누르면 정식 장부로 즉시 등록됩니다.")

        done_df = df_h[df_h["진행상태"].str.contains("완료", na=False)].copy()

        if done_df.empty:
            st.info("아직 확보 완료된 매물이 없습니다. 현장 작업 리스트에서 '🎉 확보 완료!'를 눌러보세요.")
        else:
            for d_idx, d_row in done_df.iterrows():
                st.markdown(f"""
                <div class="hunt-item-done">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:16px; font-weight:bold; color:#1a365d;">📍 {d_row['동']} {d_row['지번']} ({d_row['소유자/법인명']}{f" / {d_row['상호']}" if str(d_row.get('상호','')).strip() else ""})</span>
                        <span style="font-size:13px; color:#276749; font-weight:bold;">📞 {d_row.get('연락처','연락처 미등록')}</span>
                    </div>
                    <div style="font-size:12.5px; color:#4a5568; margin-top:4px;">
                        💡 <b>임장 히스토리</b>: {d_row.get('현장메모','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_pr, col_ar, col_to_reg, col_del = st.columns([1.5, 1.2, 1.5, 0.8])
                with col_pr:
                    tr_price = st.text_input("보증금 / 월세 *", placeholder="예: 보 3,000 / 월 250", key=f"tr_p_{d_idx}")
                with col_ar:
                    tr_area = st.text_input("전용 평수 *", placeholder="예: 75평", key=f"tr_a_{d_idx}")
                with col_to_reg:
                    st.write("")
                    if st.button("🚀 1번 탭 정식매물로 이관", key=f"btn_tr_{d_idx}", type="primary", use_container_width=True):
                        if not tr_price or not tr_area:
                            st.error("보증금/월세와 평수를 입력해 주세요.")
                        else:
                            save_property({
                                "등록일자": datetime.today().strftime("%Y-%m-%d"),
                                "입주/공실상태": "현재 공실(즉시입주)",
                                "계약만료일": "즉시 협의",
                                "거래구분": "임대차(월세)",
                                "소재지(권역)": f"인천 서구 {d_row['동']}",
                                "상세주소(지번)": f"인천 서구 {d_row['동']} {d_row['지번']}",
                                "임대인(건물주)": d_row['소유자/법인명'],
                                "임대인연락처": d_row['연락처'],
                                "가격(보/월)": tr_price,
                                "면적": tr_area,
                                "층고": "처마 7.5m",
                                "동력": "30kW",
                                "호이스트": "호이스트 무관",
                                "도로/주차": "화물차 접안 편리",
                                "대형차량": "11T 윙바디 수월",
                                "특징메모": f"[현장확보매물] {d_row.get('현장메모','')}"
                            })
                            st.success(f"✅ {d_row['지번']} 매물이 1번 탭 정식 매물 장부로 성공적으로 이관 등록되었습니다!")
                with col_del:
                    st.write("")
                    if st.button("목록 제거", key=f"btn_d_del_{d_idx}", use_container_width=True):
                        df_h = df_h.drop(df_h.index[d_idx]).reset_index(drop=True)
                        save_all_hunting(df_h)
                        st.rerun()

                st.markdown("<hr style='margin:4px 0 10px 0; border:0; border-top:1px dashed #cbd5e0;'>", unsafe_allow_html=True)

    with h_tab2:
        st.subheader("📥 텍스트 복사·붙여넣기로 지번 일괄 자동 파싱")
        st.caption("메모장이나 카톡에 적어둔 내용을 있는 그대로 복사해서 붙여넣으세요. 기계가 동, 지번, 소유자, 전화번호를 자동 분리합니다.")

        sample_guide = """석남동 223-822 > 집합공장
석남동 223-932 > 홍정미 (방문 필요)
석남동 223-360 > 이해영 , 최완규 (신창코팅) 032-577-0104
석남동 223-559 > 한미교통주식회사 032-571-1032
가좌동 556-12 > 박대표 (가좌정밀) 010-1234-5678"""

        raw_text_batch = st.text_area("작업 메모 텍스트 붙여넣기:", height=160, placeholder=sample_guide)

        if st.button("⚡ 1초 만에 자동 분석하여 장부에 등록하기", type="primary", use_container_width=True):
            if raw_text_batch.strip():
                lines = raw_text_batch.strip().split("\n")
                new_entries = []
                for line in lines:
                    line = line.strip()
                    if not line: continue

                    dong_match = re.search(r'(석남동|가좌동|원창동|경서동|도화동|송림동|오류동|청라동|효성동)', line)
                    dong = dong_match.group(1) if dong_match else "석남동"

                    jibun_match = re.search(r'\b(\d+-\d+|\d+)\b', line)
                    jibun = jibun_match.group(1) if jibun_match else ""
                    if not jibun: continue

                    phone_match = re.search(r'(0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})', line)
                    phone = phone_match.group(1).replace(" ", "-") if phone_match else ""

                    biz_match = re.search(r'\((.*?)\)', line)
                    biz = biz_match.group(1) if biz_match else ""

                    rem_text = line
                    if dong_match: rem_text = rem_text.replace(dong, "")
                    if jibun_match: rem_text = rem_text.replace(jibun, "")
                    if phone_match: rem_text = rem_text.replace(phone_match.group(1), "")
                    if biz_match: rem_text = rem_text.replace(f"({biz})", "")
                    rem_text = rem_text.replace(">", "").strip()

                    owner = rem_text.split(",")[0].strip() if rem_text else "소유자 확인중"
                    if len(owner) > 15: owner = owner[:15]

                    bldg_type = "집합공장" if "집합" in line else ("제조공장" if ("제조" in line or "공장" in line) else "일반공장")
                    status_auto = "📞 전화 확인" if phone else "🚗 방문 필요"

                    new_entries.append({
                        "등록일": datetime.today().strftime("%Y-%m-%d"),
                        "동": dong,
                        "지번": jibun,
                        "건물유형": bldg_type,
                        "소재지전체": f"인천 서구 {dong} {jibun}",
                        "소유자/법인명": owner,
                        "상호": biz,
                        "연락처": phone,
                        "진행상태": status_auto,
                        "현장메모": line
                    })

                if new_entries:
                    new_df = pd.DataFrame(new_entries)
                    df_h = pd.concat([new_df, df_h], ignore_index=True)
                    df_h = df_h.drop_duplicates(subset=["동", "지번"], keep="first")
                    save_all_hunting(df_h)
                    st.success(f"✅ 총 {len(new_entries)}개 지번이 장부에 파싱되어 등록되었습니다!")
                    st.rerun()

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 확인설명서 & 대기손님 자동 역매칭
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_REG"]:
    st.title("🏭 공장 매물 등록 & 확인·설명서 & 대기손님 자동 역매칭")
    st.caption("매물 등록 시 [중개대상물 확인·설명서 표준 텍스트], [공장 전문 블로그 원고], 그리고 [CRM 대기손님 자동 역매칭]이 한 번에 실행됩니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처", expanded=False):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 556-12 1층")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 박회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")

    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 *", value="인천 서구 가좌동")
    with b2: deal_type = st.selectbox("거래 형태 *", ["임대차(월세)", "매매", "임대/매매 겸용"])
    with b3: vacancy_status = st.selectbox("입주 상태 *", ["현재 공실(즉시입주)", "협의 입주", "만기 후 입주"])
    with b4: expire_date = st.text_input("입주 가능일", value="즉시 협의 가능")

    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 250만 원")
        area = st.text_input("실사용 면적/평수 *", placeholder="예: 1층 80평 + 가설 20평 (총 100평)")
    with c2:
        ceiling = st.text_input("처마 층고", value="처마 7.5m (하이 층고)")
        power = st.text_input("인입 동력 (kW) *", value="50kW")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음"])
    with c3:
        road = st.text_input("접면 도로 폭(m)", value="10m 도로 접")
        parking_count = st.text_input("주차장 현황", value="전면 단독마당 주차 4대 이상")
        big_truck = st.selectbox("화물차 진입 여건 *", ["11T 윙바디 접안 원활", "츄레라 / 트레일러 진출입 원활", "5톤 화물차 수월", "1톤 화물차 문 앞 접안 최적"])

    st.markdown("---")
    leg1, leg2, leg3 = st.columns(3)
    with leg1:
        violation_status = st.selectbox("위반건축물 여부", ["위반건축물 아님 (적법)", "위반건축물 등재", "확인 요망"])
        building_structure = st.text_input("주구조 / 지붕", value="일반철골구조 / 판넬지붕")
    with leg2:
        bldg_use = st.text_input("대장상 주용도", value="공장 (제조업소)")
        approval_date = st.text_input("사용승인일자", placeholder="예: 2015.05.20")
    with leg3:
        sewage_type = st.selectbox("오수/정화조 처리방식", ["하수종말처리시설 연결 (직결)", "단독정화조", "기타"])
        elevator_lift = st.selectbox("승강기 / 화물리프트", ["승강기 없음", "화물용 리프트 1대", "승객용 승강기 구비"])

    zoning_choice = st.selectbox("용도지역 분류 (인허가 기준)", ["일반공업지역 (인천지방산단/일반산단)", "전용공업지역 (중화학/공해공장 밀집)", "준공업지역 (주거 혼재 구역)"])
    memo = st.text_area("매물 핵심 강점 메모", placeholder="예: 가좌IC 3분 거리 물류 이동 최상. 호이스트 및 동력 완비로 초기 시설 투자비 수천만 원 절감.")

    if st.button("🚀 매물 저장 + 확인·설명서 + 블로그 원고 + 대기손님 역매칭 동시 실행", type="primary", use_container_width=True):
        if not price or not area:
            st.error("가격과 면적은 필수 입력 항목입니다.")
        else:
            save_property({
                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
                "거래구분": deal_type, "소재지(권역)": loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
                "임대인연락처": owner_phone, "가격(보/월)": price, "면적": area, "층고": ceiling, "동력": power,
                "호이스트": hoist, "도로/주차": f"{road} / {parking_count}", "대형차량": big_truck, "특징메모": f"[{zoning_choice}] {memo}"
            })
            st.success("✅ 매물이 보유 장부에 안전하게 등록되었습니다!")

            # 🔥 디벨롭 기능: CRM 대기 손님 자동 역매칭
            matched_custs = match_customers_for_property(loc, area)
            if matched_custs:
                st.markdown(f"##### 🎯 [자동 역매칭 알림] 이 매물 조건({loc} / {area})을 기다리는 손님이 **{len(matched_custs)}명** 있습니다!")
                for mc in matched_custs:
                    st.markdown(f"""
                    <div class="calc-box-orange" style="padding:10px 14px; margin:4px 0;">
                        👤 <b>{mc.get('상호/고객명','')}</b> ({mc.get('중요도','')}) | 📞 <b>{mc.get('연락처','')}</b> | 희망: {mc.get('희망권역','')} ({mc.get('희망평수','')}) | 예산: {mc.get('예산(보증금/월세/매매가)','')}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("현재 CRM 장부에 해당 평수/권역과 일치하는 대기 손님이 없습니다.")

            out_t1, out_t2 = st.tabs(["📋 중개대상물 확인·설명서 [Ⅱ] (비주거용) 표준 텍스트", "📝 네이버 블로그 공장 전문 브리핑 원고"])
            with out_t1:
                legal_report_text = f"""[중개대상물 확인·설명서 (비주거용 건축물) 필수 기재 사항 요약표]
1. 대상물건의 표시
• 소재지: {secret_address if secret_address else loc}
• 전용면적: {area} | 대장상 주용도: {bldg_use} | 주구조: {building_structure}
• 사용승인일: {approval_date if approval_date else '공적장부 확인'} | 위반건축물 여부: {violation_status}

2. 입지 및 제조 인프라 설비 현황
• 용도지역: {zoning_choice}
• 접면도로 및 차량진입: {road} ({big_truck}) | 주차시설: {parking_count}
• 인입전력(동력): {power} | 유효층고: {ceiling} | 크레인(호이스트): {hoist}
• 승강기시설: {elevator_lift} | 오수처리시설: {sewage_type}

3. 거래예정금액 및 입주조건
• 거래구분: {deal_type} | 거래예정금액: {price} | 입주가능시기: {vacancy_status} ({expire_date})
• 중개사 세부 의견: {memo}
- 우리부동산 공인중개사사무소 대표 김태형 (010-2660-8276) -"""
                st.text_area("확인·설명서 복사용 텍스트", legal_report_text, height=280)

            with out_t2:
                fac_blog = f"""안녕하세요! 인천 서구 및 주요 산업단지 공장·창고 전문 파트너, 우리부동산 대표 공인중개사 김태형입니다. 🙋‍♂️

오늘 소개해 드릴 현장은 {loc}에 위치한 알짜배기 {bldg_use} {deal_type} 매물입니다.
{big_truck}이 가능하고 {hoist} 및 동력 {power}가 구축되어 있어 초기 설비 투자 비용을 획기적으로 아낄 수 있는 즉시 조업 가능한 현장입니다!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 1. 매물 핵심 제원 및 임대/매매 조건
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 소재지: {loc} (상세 지번은 보안상 유선 문의 시 즉시 안내)
- 거래 형태: {deal_type}
- 금액 조건: {price}
- 실사용 면적: {area}
- 입주 가능일: {vacancy_status} ({expire_date})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 2. 제조 설비 및 물류 인프라 스펙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 용도지역: {zoning_choice}
- 처마 층고: {ceiling}
- 인입 동력: {power}
- 호이스트: {hoist}
- 도로 및 차량 접안: {road} / {big_truck} ({parking_count})
- 건축물 구조 및 적법성: {building_structure} / {violation_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 3. 김소장의 현장 실사 총평
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ {memo if memo else '차량 진출입 동선이 쾌적하고 내부 바닥 컨디션이 우수하여 기계 가공, 조립, 물류 창고 등 다양한 업종에 강력 추천합니다.'}
✅ 공장 계약은 단순 면적 확인을 넘어 업종별 인허가(폐수·대기·소음), 한전 수전용량 승압 여부, 대형 차량 회전 반경까지 전문가의 사전 점검이 필수입니다.

현장 실물 확인 및 상세 도면 브리핑이 필요하신 대표님께서는 언제든 편하게 연락 주십시오!

인천 공장·창고 전문 우리부동산 공인중개사사무소
대표 공인중개사 김태형 ☎ 010-2660-8276

#{loc.replace(' ','')}공장 #인천서구공장 #인천공장임대 #인천공장매매 #호이스트공장 #가좌동공장 #석남동공장 #우리부동산 #공인중개사김소장"""
                st.text_area("블로그 포스팅 복사용", fac_blog, height=380)

# =============================================================
# 2. 🏗️ [주업] 신축공장 맞춤 분양 설계 & 총사업비(턴키) 제안서
# =============================================================
elif menu_choice == MENU_DICT["NEW_DEV"]:
    st.title("🏗️ 신축공장 맞춤 분양 설계 & 턴키(Turn-Key) 고객 제안서")
    st.caption("대지·층별 평수 설계, 2D 캐드형 배치도, 그리고 한전 전기분담금·호이스트·취득세까지 포함한 총사업비 제안서를 A4로 즉시 인쇄합니다.")

    dev_tab1, dev_tab2 = st.tabs(["📐 맞춤 분양 설계 & 2D 평면도 & 총사업비", "🏢 신축공장 분양 전용 매물장부"])

    with dev_tab1:
        p1, p2, p3 = st.columns(3)
        with p1:
            site_name = st.text_input("프로젝트/단지명 *", value="인천 서구 가좌 첨단제조단지")
            site_addr = st.text_input("사업지 상세 주소 *", value="인천 서구 가좌동 일원")
        with p2:
            custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=150, step=10)
            road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
        with p3:
            cust_company = st.text_input("제안 대상 기업명/대표님", placeholder="예: (주)대한정밀 대표님")
            cust_usage = st.text_input("권장 조업 업종/용도", value="정밀기계제조 / 금형가공")

        st.markdown("---")
        fl1, fl2, fl3, fl4, fl5 = st.columns(5)
        with fl1: f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=90, step=5)
        with fl2: f2_pyung = st.number_input("2층 사무/제조 (평)", min_value=0, max_value=5000, value=30, step=5)
        with fl3: f3_pyung = st.number_input("3층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl4: req_kw = st.number_input("⚡ 희망 인입전력 (kW)", min_value=10, max_value=1000, value=75, step=5)
        with fl5: add_hoist_cnt = st.number_input("🏗️ 호이스트 신설 (대)", min_value=0, max_value=10, value=1, step=1)

        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원) *", value=1200, step=50)
        with pr2: add_unit_price = st.number_input("상층부 증축단가 (건축 평당 만 원) *", value=380, step=10)
        with pr3: loan_ratio = st.slider("시설자금 대출 비율 (%)", 50, 85, 80, 5)
        with pr4: interest_rate = st.number_input("예상 대출금리 (연 %)", value=4.2, step=0.1)

        actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
        yard_pyung = max(0, custom_land - f1_pyung)

        if st.button("🚀 신축공장 맞춤 분양 견적 & 2D 평면도 산출하기", type="primary", use_container_width=True):
            floor_list = [f1_pyung, f2_pyung, f3_pyung]
            active_floors = [p for p in floor_list if p > 0]
            max_floor_cnt = len(active_floors)
            total_bldg_area = sum(floor_list)

            base_cost = int(custom_land * base_unit_price * 10000)
            extra_cost = int(sum(floor_list[1:]) * add_unit_price * 10000)
            total_dev_price = base_cost + extra_cost

            # 🔥 디벨롭: 부대설비 및 세금 정밀 연산
            loan_amt = int(total_dev_price * (loan_ratio / 100.0))
            pure_down_payment = total_dev_price - loan_amt
            acq_tax = int(total_dev_price * 0.046)
            kepco_cost = int(req_kw * 110000) # 한전 시설분담금 및 내선공사 추정
            hoist_cost = int(add_hoist_cnt * 15000000) # 호이스트 1기당 약 1,500만 추정
            monthly_interest = int((loan_amt * (interest_rate / 100.0)) / 12)
            total_turnkey_cash = pure_down_payment + acq_tax + kepco_cost + hoist_cost

            company_display = cust_company if cust_company.strip() else "귀사"

            out_c1, out_c2 = st.columns([1.25, 1.25])
            with out_c1:
                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{company_display}] 신축공장 턴키(Turn-Key) 분양 수지분석표</h4>
                    • <b>사업지</b>: {site_name} ({site_addr})<br>
                    • <b>대지면적</b>: <b>{custom_land}평</b> | <b>건폐율</b>: <b>{actual_bcr}%</b> (단독 마당 <b>약 {yard_pyung}평</b>)<br>
                    • <b>건축규모</b>: <b>지상 {max_floor_cnt}층 (연면적 {total_bldg_area}평)</b><br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    1. <b>총 분양 공급가액</b>: <span style="font-size: 18px; font-weight: bold; color: #c53030;">{total_dev_price:,}원</span><br>
                    2. <b>시설자금 대출 ({loan_ratio}%)</b>: 약 <b>{loan_amt:,}원</b> (월 이자 약 {monthly_interest:,}원 수준)<br>
                    3. <b>분양 자부담금 ({100-loan_ratio}%)</b>: <b>{pure_down_payment:,}원</b><br>
                    4. <b>취등록세 (4.6%) 및 부대설비 예산</b>:<br>
                    &nbsp;&nbsp;&nbsp;- 취득세 등: 약 {acq_tax:,}원<br>
                    &nbsp;&nbsp;&nbsp;- 전기 승압/인입비({req_kw}kW): 약 {kepco_cost:,}원 | 호이스트({add_hoist_cnt}대): 약 {hoist_cost:,}원<br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px solid #dd6b20;">
                    🚩 <b>입주 시까지 필요 총 자기자본(턴키 현금)</b>: <span style="font-size: 20px; color: #2b6cb0; font-weight: bold;">약 {total_turnkey_cash:,}원</span>
                </div>
                """, unsafe_allow_html=True)

            with out_c2:
                bldg_w_svg = int(max(25, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
                yard_w_svg = 100 - bldg_w_svg
                truck_text = "40ft 트레일러 회전 및 접안 최적" if road_width >= 10 else "11T 윙바디 전면 접안"

                svg_2d = f"""
                <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 14px;">
                    <div style="background-color: #2d3748; color: white; text-align: center; padding: 8px; font-weight: bold; font-size: 13px; margin-bottom: 10px;">
                        ▲ 전면 {road_width}m 광폭 도로 접 ({truck_text}) ▲
                    </div>
                    <div style="border: 2px dashed #3182ce; padding: 12px; background-color: #ebf8ff; border-radius: 6px;">
                        <div style="display: flex; gap: 10px; height: 180px;">
                            <div style="flex: {bldg_w_svg}; background-color: #bee3f8; border: 2px solid #1a365d; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 16px; color: #1a365d;">🏭 신축 공장동</span>
                                <span style="font-size: 13px; color: #2c5282; font-weight: bold;">지상 {max_floor_cnt}층 (1F {f1_pyung}평)</span>
                                <span style="font-size: 12px; color: #2b6cb0; margin-top:4px;">⚡ {req_kw}kW / 호이스트 {add_hoist_cnt}기</span>
                            </div>
                            <div style="flex: {yard_w_svg}; background-color: #edf2f7; border: 2px dashed #718096; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 14px; color: #4a5568;">🚛 단독 마당/주차</span>
                                <span style="font-size: 13px; color: #718096; font-weight: bold;">약 {yard_pyung}평</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(svg_2d, unsafe_allow_html=True)

            print_html = f"""<html><body style='font-family:sans-serif; padding:30px;'><h2>[{company_display}] {site_name} 신축공장 분양 제안서</h2><hr><p><b>1. 사업지</b>: {site_addr} (전면 {road_width}m 도로 접)</p><p><b>2. 분양면적</b>: 대지 {custom_land}평 / 건축 총 연면적 {total_bldg_area}평 (1층 {f1_pyung}평, 마당 {yard_pyung}평)</p><p><b>3. 총 분양공급가</b>: {total_dev_price:,}원 (대출 {loan_ratio}% 실행 시 약 {loan_amt:,}원 / 월 이자 약 {monthly_interest:,}원)</p><p><b>4. 취등록세 및 설비(전기 {req_kw}kW, 호이스트 {add_hoist_cnt}대) 포함 필요 순수 현금</b>: 약 {total_turnkey_cash:,}원</p><hr><p><b>우리부동산 공인중개사사무소 대표 김태형 (010-2660-8276)</b></p></body></html>"""
            st.components.v1.html(f"""<button onclick="var w=window.open('','_blank');w.document.write(`{print_html}`);w.print();" style="background:#2b6cb0; color:white; padding:12px 20px; border:none; border-radius:6px; font-weight:bold; cursor:pointer; width:100%; font-size:15px;">🖨️ 이 고객 맞춤형 분양제안서 A4 인쇄하기</button>""", height=55)

    with dev_tab2:
        st.subheader("🏢 신축공장 분양 전용 매물장부")
        df_devs = load_new_devs()
        if not df_devs.empty: st.dataframe(df_devs, use_container_width=True, height=350)
        else: st.info("저장된 신축공장 분양 매물이 없습니다.")

# =============================================================
# 3. 📋 [주업] 공장 손님 CRM (월별 필터 + VIP 서브탭 + 스마트 카드 완전 복구)
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
                            "고객명": row.get("상호/고객명", ""), "연락처": row.get("연락처", ""),
                            "중요도": row.get("중요도", ""), "경과일": passed_days
                        })
                except Exception: pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락 후 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | <span style="color:#d69e2e;">{rt['중요도']}</span> | 마지막 연락 후 <b>{rt['경과일']}일 경과</b> ➡️ 신규 매물 체크 및 안부 연락 권장
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    tab_list, tab_edit = st.tabs(["📊 손님 장부 목록 (스마트 카드 뷰)", "✍️ 손님 신규 등록 및 수정/삭제"])

    with tab_list:
        if not df_c.empty:
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
            with f_col4: search_kw = st.text_input("🔎 손님명 / 연락처 / 메모 검색", placeholder="예: 대한정밀, 가좌동...", key="crm_kw_search")

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

            subtab_vip, subtab_active, subtab_done, subtab_all = st.tabs(["🔥 집중 관리 (S/A급 VIP)", "🏃 진행중", "🤝 계약 완료", "📁 전체 보기"])

            def render_customer_cards_pro(target_df, tab_prefix="all"):
                if target_df.empty:
                    st.info("해당 조건의 손님이 없습니다.")
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
                            <span class="tag-gray">🗓️ {c_movein_val}</span>
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
                        if st.button("🎯 맞춤 보유매물 매칭", key=f"btn_m_{tab_prefix}_{orig_idx}"):
                            m_props = match_properties_for_customer(c_row)
                            if m_props:
                                for p in m_props:
                                    st.markdown(f"• **{p.get('소재지(권역)','')}** | {p.get('가격(보/월)','')} | {p.get('면적','')} | {p.get('호이스트','')}")
                            else: st.info("조건에 부합하는 보유 매물이 없습니다.")
                    with btn_c2:
                        if st.button("💬 안부/체크 카톡 생성", key=f"btn_k_{tab_prefix}_{orig_idx}"):
                            talk = f"[{c_name_val} 대표님, 우리부동산 매물 안내]\n\n대표님 안녕하십니까! 인천 공장 전문 우리부동산 김태형 대표입니다.\n문의해 주신 공장 조건({c_loc_val}, {c_area_val}, {c_deal_val}) 관련 신규 매물 체크차 연락드렸습니다.\n일정 조율해 주시면 현장 도면과 함께 상세히 브리핑해 드리겠습니다!\n\n- 우리부동산 김태형 대표 (010-2660-8276)"
                            st.text_area(f"카톡 복사창 ({c_name_val})", talk, height=160, key=f"tx_{tab_prefix}_{orig_idx}")
                    with btn_c3:
                        if st.button("📝 상담일지 기록", key=f"btn_h_{tab_prefix}_{orig_idx}"):
                            curr_h = str(c_row.get("상담히스토리", ""))
                            st.text_area("누적 상담 기록", curr_h, height=90, disabled=True, key=f"hv_{tab_prefix}_{orig_idx}")
                            new_l = st.text_input("오늘 통화 내용 입력", key=f"in_{tab_prefix}_{orig_idx}")
                            if st.button("일지 저장", key=f"sv_{tab_prefix}_{orig_idx}"):
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
            with r1: c_name = st.text_input("상호 / 고객명 *", value=str(target_row["상호/고객명"]) if target_row is not None else "", placeholder="예: (주)대한정밀 김대표")
            with r2: c_phone = st.text_input("연락처 *", value=str(target_row["연락처"]) if target_row is not None else "", placeholder="예: 010-1234-5678")
            with r3:
                star_opts = ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"]
                star_def = str(target_row["중요도"]) if target_row is not None else "⭐⭐ A급(유력)"
                c_star = st.selectbox("중요도 (VIP 등급)", star_opts, index=star_opts.index(star_def) if star_def in star_opts else 1)

            r4, r5, r6, r7 = st.columns(4)
            with r4:
                deal_opts = ["임대차(월세)", "매매", "매매/임대 겸용"]
                deal_def = str(target_row["거래구분"]) if target_row is not None else "임대차(월세)"
                c_deal = st.selectbox("거래 구분 *", deal_opts, index=deal_opts.index(deal_def) if deal_def in deal_opts else 0)
            with r5: c_loc = st.text_input("희망 권역 *", value=str(target_row["희망권역"]) if target_row is not None else "인천 서구 가좌/석남")
            with r6: c_area = st.text_input("희망 평수/면적 *", value=str(target_row["희망평수"]) if target_row is not None else "80~120평")
            with r7:
                permit_opts = ["일반제조(소음·진동)", "폐수·대기 배출(인허가 필수)", "식품가공(HACCP)", "단순물류·창고", "자원순환·고물상", "기타 특수업종"]
                permit_def = str(target_row.get("업종인허가", "일반제조(소음·진동)")) if target_row is not None else "일반제조(소음·진동)"
                c_permit = st.selectbox("🏭 업종 및 인허가 *", permit_opts, index=permit_opts.index(permit_def) if permit_def in permit_opts else 0)

            r8, r9, r10, r11 = st.columns(4)
            with r8: c_hoist = st.selectbox("🏗️ 호이스트 요구 *", ["호이스트 필수 (2.8T~5T)", "있으면 좋음", "불필요 (호이스트 무관)"])
            with r9: c_truck = st.selectbox("🚛 화물차량 작업 여건 *", ["11T 윙바디 필수", "츄레라/트레일러 필수", "5T 진입 수월", "1T 위주 진입"])
            with r10: c_pwr = st.selectbox("⚡ 필요 동력(kW) *", ["50kW 내외", "30kW 이하 (기본)", "75kW 이상 (중형)", "100kW~200kW 대용량"])
            with r11: c_movein = st.selectbox("🗓️ 입주 희망 시기 *", ["협의 입주", "즉시 입주", "1개월 이내", "2~3개월 이내"])

            r12, r13 = st.columns(2)
            with r12: c_budget = st.text_input("희망 예산 (보증금/월세 또는 매매가)", value=get_safe_cust_val(target_row, "예산(보증금/월세/매매가)") if target_row is not None else "", placeholder="예: 보 3천 / 월 250만")
            with r13: c_stat = st.selectbox("진행 상태", ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"])

            c_memo = st.text_area("상세 상담 메모", value=str(target_row["상담메모"]) if target_row is not None else "", placeholder="예: CNC 선반 4대 보유, 바닥 에폭시 상태 중요")

            sub_b1, sub_b2 = st.columns([4, 1])
            with sub_b1: submit_save = st.form_submit_button("💾 손님 정보 저장하기", type="primary", use_container_width=True)
            with sub_b2: submit_del = st.form_submit_button("🗑️ 손님 삭제", type="secondary", use_container_width=True) if edit_mode else False

            if submit_save:
                if not c_name or not c_phone:
                    st.error("상호/고객명과 연락처는 필수입니다.")
                else:
                    new_entry = {
                        "접수일자": target_row["접수일자"] if target_row is not None else today.strftime("%Y-%m-%d"),
                        "최근연락일": today.strftime("%Y-%m-%d"), "중요도": c_star, "거래구분": c_deal,
                        "업종인허가": c_permit, "상호/고객명": c_name, "연락처": c_phone, "희망권역": c_loc,
                        "희망평수": c_area, "예산(보증금/월세/매매가)": c_budget, "입주시기": c_movein,
                        "호이스트": c_hoist, "대형차진입": c_truck, "희망전력kW": c_pwr, "상담메모": c_memo,
                        "상담히스토리": target_row.get("상담히스토리", "") if target_row is not None else f"[{today.strftime('%Y-%m-%d %H:%M')}] 최초 접수 완료\n",
                        "진행상태": c_stat
                    }
                    if edit_mode and selected_cust_idx is not None:
                        df_c.iloc[selected_cust_idx] = new_entry
                        save_all_customers(df_c)
                    else:
                        save_customer(new_entry)
                    st.success("✅ 저장되었습니다!")
                    st.rerun()

            if submit_del and edit_mode and selected_cust_idx is not None:
                df_c = df_c.drop(df_c.index[selected_cust_idx]).reset_index(drop=True)
                save_all_customers(df_c)
                st.warning("🗑️ 삭제되었습니다.")
                st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부 (4중 필터 + 브리핑 문자 생성기)
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부 & 손님 전송용 브리핑 생성기")
    st.caption("평수 구간, 호이스트, 화물차 진입 여건으로 즉시 필터링하고, 보안 정보(상세지번/건물주 번호)를 제외한 손님용 브리핑 카톡을 1초 만에 뽑아냅니다.")

    df_p = load_properties()
    if not df_p.empty:
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: sel_pyung = st.selectbox("📐 실사용 평수 구간", ["전체 평수 보기", "60평 이하", "60평 ~ 120평", "120평 ~ 200평", "200평 이상"])
        with f_col2: sel_hoist = st.selectbox("🏗️ 호이스트 유무", ["전체 (유/무 무관)", "호이스트 완비(설치)", "호이스트 없음"])
        with f_col3: sel_truck = st.selectbox("🚛 화물차 여건", ["전체 차량 보기", "츄레라/트레일러 가능", "11톤/윙바디 이상"])
        with f_col4: search_text = st.text_input("🔎 권역/지번/메모 검색", placeholder="예: 가좌동, 석남동...")

        filtered_df = df_p.copy()
        if sel_pyung != "전체 평수 보기":
            def check_pyung_range(area_val, mode):
                nums = parse_pyung_numbers(area_val)
                if not nums: return True
                p = nums[0]
                if mode == "60평 이하": return p <= 60
                if mode == "60평 ~ 120평": return 60 <= p <= 120
                if mode == "120평 ~ 200평": return 120 <= p <= 200
                if mode == "200평 이상": return p >= 200
                return True
            filtered_df = filtered_df[filtered_df["면적"].apply(lambda x: check_pyung_range(x, sel_pyung))]

        if sel_hoist == "호이스트 완비(설치)": filtered_df = filtered_df[filtered_df["호이스트"].astype(str).str.contains("완비|설치|톤|T", na=False)]
        elif sel_hoist == "호이스트 없음": filtered_df = filtered_df[filtered_df["호이스트"].astype(str).str.contains("없음", na=False)]
        if sel_truck == "츄레라/트레일러 가능": filtered_df = filtered_df[filtered_df["대형차량"].astype(str).str.contains("츄레라|트레일러", na=False)]
        elif sel_truck == "11톤/윙바디 이상": filtered_df = filtered_df[filtered_df["대형차량"].astype(str).str.contains("11|윙바디|츄레라", na=False)]
        if search_text.strip():
            kw = search_text.strip()
            filtered_df = filtered_df[filtered_df["소재지(권역)"].astype(str).str.contains(kw, na=False) | filtered_df["상세주소(지번)"].astype(str).str.contains(kw, na=False) | filtered_df["특징메모"].astype(str).str.contains(kw, na=False)]

        st.dataframe(filtered_df, use_container_width=True, height=320)

        # 🔥 디벨롭: 손님 카톡 전송용 브리핑 카드 자동 생성기 (보안 지번 자동 블라인드)
        if not filtered_df.empty:
            st.markdown("---")
            st.subheader("📲 손님 전송용 매물 브리핑 카톡 생성기 (상세지번·임대인 정보 자동 블라인드)")
            prop_records = filtered_df.to_dict("records")
            chosen_p_idx = st.selectbox(
                "손님에게 브리핑할 매물을 선택하세요:",
                range(len(prop_records)),
                format_func=lambda i: f"[{prop_records[i].get('거래구분','')}] {prop_records[i].get('소재지(권역)','')} | {prop_records[i].get('면적','')} | {prop_records[i].get('가격(보/월)','')}"
            )
            cp = prop_records[chosen_p_idx]
            brief_msg = f"""[🏢 우리부동산 맞춤 공장/창고 추천 브리핑]

대표님 안녕하십니까! 요청하신 조건에 부합하는 우량 공장 매물 브리핑해 드립니다.

■ 소재지: {cp.get('소재지(권역)','')} 일원 (상세 지번은 현장 미팅 시 안내)
■ 거래조건: {cp.get('거래구분','')} / {cp.get('가격(보/월)','')}
■ 실사용면적: {cp.get('면적','')}
■ 층고 / 동력: {cp.get('층고','')} / 인입전력 {cp.get('동력','')}
■ 호이스트: {cp.get('호이스트','')}
■ 차량진입 / 주차: {cp.get('대형차량','')} ({cp.get('도로/주차','')})
■ 입주가능일: {cp.get('입주/공실상태','')} ({cp.get('계약만료일','')})
■ 매물특징: {cp.get('특징메모','')}

현장 내부 실사 및 도면 확인을 원하시면 편하신 시간 말씀해 주십시오.
- 인천 공장 전문 우리부동산 대표 김태형 (010-2660-8276) -"""
            st.text_area("카카오톡/문자 복사용 브리핑 카드", brief_msg, height=260)
    else:
        st.info("등록된 보유 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 정밀 시세 & 적정 임대료 추정기 (전면 디벨롭)
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 정밀 시세 & 적정 임대료 추정기")
    st.caption("인천 서구 권역별 실거래 토지 단가 + 건물 구조/연식 감가상각 + 호이스트/대용량 전력 프리미엄 + 기대 수익률 기반 적정 임대료(보증금/월세)를 동시 산출합니다.")

    v1, v2, v3 = st.columns(3)
    with v1:
        zone_sel = st.selectbox("📍 인천 주요 산업권역 선택", [
            "서구 가좌동 (주안국가산단/일반공업)",
            "서구 석남동 (일반공업/기계가공 밀집)",
            "서구 원창동/청라 (북항배후단지/물류최적)",
            "서구 오류동/검단 (검단일반산단/신축밀집)",
            "서구 경서동/기타 (녹지/소규모제조)"
        ])
        land_p = st.number_input("📐 대지면적 (평) *", min_value=10, max_value=10000, value=200, step=10)
    with v2:
        bldg_p = st.number_input("🏢 건물 연면적 (평) *", min_value=10, max_value=10000, value=140, step=10)
        bldg_age = st.slider("🗓️ 건물 경과 연수 (준공 후 년수)", 0, 35, 10, 1)
    with v3:
        road_cond = st.selectbox("🚛 접면 도로 및 차량 여건", ["10m 이상 광폭 (츄레라 원활 +8%)", "6~8m 도로 (11톤 윙바디 원활 기준)", "4m 내외 협소도로 (-10%)"])
        infra_spec = st.selectbox("⚙️ 호이스트 및 동력 설비", ["호이스트 5T 이상 + 동력 100kW 이상 (+5,000만)", "호이스트 2.8T~3T + 동력 50kW (+2,500만)", "기본 설비 (추가 가산 없음)"])

    base_land_map = {
        "서구 가좌동 (주안국가산단/일반공업)": 1150,
        "서구 석남동 (일반공업/기계가공 밀집)": 1080,
        "서구 원창동/청라 (북항배후단지/물류최적)": 1280,
        "서구 오류동/검단 (검단일반산단/신축밀집)": 1020,
        "서구 경서동/기타 (녹지/소규모제조)": 890
    }
    road_mult_map = {
        "10m 이상 광폭 (츄레라 원활 +8%)": 1.08,
        "6~8m 도로 (11톤 윙바디 원활 기준)": 1.00,
        "4m 내외 협소도로 (-10%)": 0.90
    }
    infra_add_map = {
        "호이스트 5T 이상 + 동력 100kW 이상 (+5,000만)": 50000000,
        "호이스트 2.8T~3T + 동력 50kW (+2,500만)": 25000000,
        "기본 설비 (추가 가산 없음)": 0
    }

    unit_land = int(base_land_map[zone_sel] * road_mult_map[road_cond])
    est_land_val = land_p * unit_land * 10000

    # 건물 신축단가 평당 380만 원 기준 연 2.5% 감가 (최소 잔존가치 25%)
    depreciation_factor = max(0.25, 1.0 - (bldg_age * 0.025))
    unit_bldg = int(380 * depreciation_factor)
    est_bldg_val = bldg_p * unit_bldg * 10000

    infra_val = infra_add_map[infra_spec]
    total_est_sale = est_land_val + est_bldg_val + infra_val
    pyung_avg_sale = int((total_est_sale / land_p) / 10000)

    # 적정 임대료 역산 (공장 평당 월세 3.2~3.8만 원 및 연 수익률 6.0% 연동)
    est_monthly_rent = int(bldg_p * 3.5) * 10000
    est_deposit = est_monthly_rent * 10

    st.markdown("---")
    r_c1, r_c2 = st.columns(2)
    with r_c1:
        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="color:#c05621; margin:0 0 8px 0;">💰 1. AI 매매 시세 추정 결과 ({zone_sel.split()[1]})</h4>
            • <b>토지 평가액</b>: 약 <b>{est_land_val:,}원</b> (대지 평당 약 {unit_land:,}만 원)<br>
            • <b>건물 잔존가치</b>: 약 <b>{est_bldg_val:,}원</b> (경과 {bldg_age}년 감가 반영, 평당 {unit_bldg}만 원)<br>
            • <b>설비 프리미엄</b>: 약 <b>{infra_val:,}원</b><br>
            <hr style="margin:8px 0;">
            🚩 <b>추정 적정 매매가</b>: <span style="font-size:21px; font-weight:bold; color:#c53030;">약 {total_est_sale:,}원</span><br>
            &nbsp;&nbsp;&nbsp;(대지 평당 환산가: <b>약 {pyung_avg_sale:,}만 원/평</b>)
        </div>
        """, unsafe_allow_html=True)
    with r_c2:
        st.markdown(f"""
        <div class="calc-box-blue">
            <h4 style="color:#2b6cb0; margin:0 0 8px 0;">📊 2. 적정 임대차(보증금/월세) 및 담보대출 한도</h4>
            • <b>권장 임대 보증금</b>: <b>약 {est_deposit:,}원</b><br>
            • <b>권장 적정 월세</b>: <span style="font-size:19px; font-weight:bold; color:#2b6cb0;">월 약 {est_monthly_rent:,}원</span> (건물 평당 약 3.5만 원 기준)<br>
            • <b>연간 임대수익률</b>: 매매가 대비 약 <b>{round(((est_monthly_rent*12)/(total_est_sale-est_deposit))*100, 2)}%</b><br>
            <hr style="margin:8px 0;">
            🏦 <b>매수 시 기업 시설자금 대출 가능액 (LTV 75% 기준)</b>:<br>
            &nbsp;&nbsp;&nbsp;➡ 최대 <b>약 {int(total_est_sale * 0.75):,}원</b> (실제 필요 자부담 약 {int(total_est_sale * 0.25):,}원)
        </div>
        """, unsafe_allow_html=True)

# =============================================================
# 6. 🍜 [고도화] 맛집 & 일상 블로그 (400자 영수증 리뷰 & 숏폼 대본 완전 복구)
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
            m_wait = st.text_input("방문/웨이팅", placeholder="예: 주말 저녁 6시 30분 방문 / 캐치테이블 20분 대기")
        with c3:
            m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 은은한 연탄 불향과 팡 터지는 육즙 조화가 끝내주는 가성비 삼겹살 찐맛집")
            m_point = st.text_input("킬링 포인트 (숏폼용)", placeholder="예: 첫 점 씹자마자 터지는 연탄 불향 육즙과 구운 묵은지 궁합")

        m_taste = st.text_area("맛 평가 디테일", placeholder="예: 연탄불 직화구이로 첫 점부터 육즙 폭발. 파채와 묵은지 구이의 조합이 일품이며, 칼칼한 된장찌개가 밥도둑임.")

        if st.button("🚀 맛집 마케팅 패키지 (포스팅 + 400자 영수증 + 숏폼) 생성", type="primary"):
            if not m_name or not m_eval:
                st.error("상호명과 솔직 한 줄 총평은 필수입니다.")
            else:
                b_col1, b_col2 = st.columns([1.3, 1.0])
                with b_col1:
                    st.markdown("##### 📝 네이버 블로그 최상위 포스팅 본문")
                    post_text = f"""안녕하세요. 인천 맛집·일상 탐방 전문 김소장입니다.
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
#{m_name.replace(' ','')} #{m_loc.replace(' ','')}맛집 #{m_kw.replace(', ',' #').replace(' ','')} #인천맛집 #우리부동산"""
                    st.text_area("블로그 본문 복사", post_text, height=350)

                with b_col2:
                    st.markdown("##### 🧾 네이버 영수증 리뷰 (400자 이내 찐후기)")
                    review_text = f"""⭐⭐⭐⭐⭐
{m_loc} 찐맛집 인정합니다! 평소 소문 듣고 찾아왔는데 기대 이상이었어요.
{m_menu} 주문해서 먹어봤는데, {m_point if m_point else m_eval}. {m_taste}
고기 질도 정말 신선하고 불향과 육즙 밸런스가 예술이라 마지막 한 점까지 물리지 않고 맛있게 먹었습니다.
주차도 편하고 직원분들이 바쁜 시간대에도 친절하게 응대해 주셔서 기분 좋게 식사했네요. 가족 외식이나 모임 장소로 강력 추천드리고 조만간 무조건 재방문할 생각입니다! 번창하세요 사장님 👍"""
                    st.caption(f"📝 현재 글자 수: **{len(review_text)}자** / 최대 400자")
                    st.text_area("영수증 리뷰 복사", review_text, height=180)

                    st.markdown("##### 🎬 30초 숏폼(릴스·클립) 촬영 대본")
                    short_script = f"""[0~3초 훅 오프닝]
"인천 {m_loc}에서 고기 좀 먹어봤다면 모를 수가 없는 이곳!" (지글지글 연탄불 ASMR 컷)

[4~22초 본론 킬링포인트]
"바로 {m_name}인데요. {m_menu} 시키면 나오는 비주얼 좀 보세요. {m_point}!" (육즙 클로즈업 컷)

[23~30초 클로징]
"이번 주말 외식 장소 고민 끝! 위치는 {m_addr}입니다." """
                    st.text_area("숏폼 대본 복사", short_script, height=180)

    with b_tab2:
        d1, d2 = st.columns(2)
        with d1:
            d_name = st.text_input("핫플명 *", placeholder="예: 스투시 서울 챕터 도산")
            d_loc = st.text_input("위치 *", placeholder="예: 서울 강남구 신사동 도산공원 일대")
            d_item = st.text_input("신상 품목 *", placeholder="예: 2026 신상 후드티, 로고 티셔츠")
        with d2:
            d_eval = st.text_input("한 줄 총평 *", placeholder="예: 감각적인 쇼룸 인테리어와 힙한 무드가 공존하는 스트릿 패션의 성지")
            d_wait = st.text_input("대기 시간", placeholder="예: 주말 오후 2시 방문 / 현장 태블릿 40분 대기")
        d_note = st.text_area("내부 무드 및 쇼핑 팁", placeholder="예: 미니멀한 노출 콘크리트 인테리어에 힙한 사운드가 가득함. 피팅룸 대기 전 미리 사이즈 체크 필수.")

        if st.button("🚀 핫플 블로그 포스팅 & 릴스 대본 생성", type="primary"):
            if not d_name or not d_eval:
                st.error("핫플명과 한 줄 총평은 필수입니다.")
            else:
                st.text_area("핫플 블로그 본문", f"안녕하세요! 김소장입니다. 오늘은 {d_loc} {d_name} 다녀왔습니다.\n\n• 핵심 아이템: {d_item}\n• 웨이팅: {d_wait}\n• 총평: {d_eval}\n• 쇼핑 팁: {d_note}", height=200)
                st.text_area("핫플 릴스 대본", f"[오프닝] {d_loc} 가면 무조건 들러야 할 {d_name}!\n[본론] 신상 {d_item} 라인업 실물 깡패네요.\n[클로징] 주말엔 웨이팅({d_wait}) 있으니 서두르세요!", height=150)

# =============================================================
# 7. 🏢 [실시간 API 완전 자동화] 청약홈 분양·줍줍 & LH 공공임대 허브
# =============================================================
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 실시간 청약·줍줍 & LH 공공임대 자동 업데이트 허브")
    st.caption("공공데이터포털 정식 인증키 내장 완료! 한국부동산원 청약Home 및 LH 실시간 공고 자동 수집 ➡️ 단지 선택 즉시 블로그 원고 1초 자동 완성!")

    DEFAULT_API_KEY = "d1a0585bef6ed7240317271c754ad4be4f9ba74cdf342e6b714bbb85d3196f69"
    API_KEY_FILE = "data_go_kr_key.txt"

    def get_active_api_key():
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k: return k
        return DEFAULT_API_KEY

    active_key = get_active_api_key()

    @st.cache_data(ttl=1800)
    def fetch_realtime_applyhome(api_key, sido_filter="전체"):
        results = []
        today_dt = datetime.today().date()
        start_date_cond = (datetime.today() - timedelta(days=60)).strftime("%Y-%m-%d")

        endpoints = [
            ("🏢 APT 일반/공공분양", "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"),
            ("🔥 무순위/취소 (줍줍)", "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getRemndrLttotPblancDetail"),
            ("🏙️ 오피스텔/도시형/생숙", "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getUrbtyOfctlLttotPblancDetail")
        ]

        api_error_msg = None
        for label_type, url in endpoints:
            params = {
                "serviceKey": api_key, "page": 1, "perPage": 80,
                "returnType": "JSON", "cond[RCRIT_PBLANC_DE::GTE]": start_date_cond
            }
            if sido_filter != "전체":
                params["cond[SUBSCRPT_AREA_CODE_NM::EQ]"] = sido_filter

            try:
                res = requests.get(url, params=params, timeout=8)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    for row in data:
                        r_bgnde = str(row.get("RCEPT_BGNDE") or row.get("SUBSCRPT_RCEPT_BGNDE") or "")
                        r_endde = str(row.get("RCEPT_ENDDE") or row.get("SUBSCRPT_RCEPT_ENDDE") or "")
                        status_badge = "📌 공고중"
                        try:
                            if r_bgnde and r_endde:
                                s_d = datetime.strptime(r_bgnde[:10], "%Y-%m-%d").date()
                                e_d = datetime.strptime(r_endde[:10], "%Y-%m-%d").date()
                                if s_d <= today_dt <= e_d: status_badge = "🔴 오늘 접수중!"
                                elif today_dt < s_d: status_badge = f"⏳ 접수예정 (D-{(s_d - today_dt).days})"
                                else: status_badge = "🏁 접수마감"
                        except Exception: pass

                        results.append({
                            "주택관리번호": str(row.get("HOUSE_MANAGE_NO") or ""),
                            "공고번호": str(row.get("PBLANC_NO") or ""),
                            "진행상태": status_badge, "구분": label_type,
                            "지역": str(row.get("SUBSCRPT_AREA_CODE_NM") or "전국"),
                            "단지명": str(row.get("HOUSE_NM") or ""),
                            "공급위치": str(row.get("HSSPLY_ADRES") or ""),
                            "공급세대수": f"{row.get('TOT_SUPLY_HSHLDCO', 0)}세대",
                            "모집공고일": str(row.get("RCRIT_PBLANC_DE") or ""),
                            "청약접수기간": f"{r_bgnde} ~ {r_endde}" if r_bgnde else "공고문 확인",
                            "특별공급일": f"{row.get('SPSPLY_RCEPT_BGNDE', '')} ~ {row.get('SPSPLY_RCEPT_ENDDE', '')}".strip(" ~") or "해당없음",
                            "1순위접수일": f"{row.get('GNRL_RNK1_CRSPAREA_RCPTDE', '')}".strip() or r_bgnde,
                            "당첨자발표일": str(row.get("PRZWNER_PRESNATN_DE") or ""),
                            "계약기간": f"{row.get('CNTRCT_CNCLS_BGNDE', '')} ~ {row.get('CNTRCT_CNCLS_ENDDE', '')}".strip(" ~"),
                            "입주예정월": str(row.get("MVN_PREARNGE_YM") or "공고문 참조"),
                            "시공사": str(row.get("BSNS_MBY_NM") or row.get("CNSTRCT_ENTRPS_NM") or "시공사 확인"),
                            "문의처": str(row.get("MDHS_TELNO") or ""),
                            "공고URL": str(row.get("PBLANC_URL") or "https://www.applyhome.co.kr")
                        })
                else:
                    api_error_msg = f"API 응답 코드: {res.status_code}"
            except Exception as e:
                api_error_msg = str(e)
                continue
        return results, api_error_msg

    @st.cache_data(ttl=1800)
    def fetch_apt_price_detail(api_key, house_manage_no, pblanc_no, is_remndr=False):
        if not house_manage_no or not pblanc_no: return []
        url = (
            "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getRemndrLttotPblancMdl"
            if is_remndr else
            "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl"
        )
        params = {
            "serviceKey": api_key, "page": 1, "perPage": 30, "returnType": "JSON",
            "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no, "cond[PBLANC_NO::EQ]": pblanc_no
        }
        models = []
        try:
            res = requests.get(url, params=params, timeout=6)
            if res.status_code == 200:
                for m in res.json().get("data", []):
                    h_ty = str(m.get("HOUSE_TY") or m.get("MODEL_NO") or "")
                    top_amt = str(m.get("LTTOT_TOP_AMOUNT") or m.get("SUPLY_AMOUNT") or "")
                    sup_cnt = str(m.get("SUPLY_HSHLDCO") or "")
                    if top_amt and top_amt != "0":
                        models.append(f"• {h_ty}타입 ({sup_cnt}세대): 최고가 {top_amt}만 원")
        except Exception: pass
        return models

    @st.cache_data(ttl=1800)
    def fetch_realtime_lh(api_key):
        url = "https://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"
        params = {"serviceKey": api_key, "PG_SZ": 60, "PAGE": 1}
        lh_results = []
        try:
            res = requests.get(url, params=params, timeout=8)
            if res.status_code == 200:
                js = res.json()
                if isinstance(js, list) and len(js) > 1 and "dsList" in js[1]:
                    for item in js[1]["dsList"]:
                        pan_ss = str(item.get("PAN_SS") or "")
                        lh_results.append({
                            "진행상태": f"🟢 {pan_ss}" if ("접수" in pan_ss or "공고" in pan_ss) else f"⚪ {pan_ss}",
                            "구분": f"🏠 LH {item.get('AIS_TP_CD_NM', '공공임대')}",
                            "지역": str(item.get("CNP_CD_NM") or "전국"),
                            "단지명": str(item.get("PAN_NM") or ""),
                            "공고게시일": str(item.get("PAN_NT_ST_DT") or ""),
                            "접수마감일": str(item.get("CLSG_DT") or ""),
                            "공고URL": str(item.get("DTL_URL") or "https://apply.lh.or.kr")
                        })
        except Exception: pass
        return lh_results

    sub_tab1, sub_tab2 = st.tabs([
        "🏢 [청약Home 실시간 자동수집] 아파트 분양 & 무순위 줍줍",
        "🏠 [LH 실시간 자동수집] 공공임대·행복주택·청년주택"
    ])

    with sub_tab1:
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.3, 1.6, 1.8, 1.0])
        with f_col1: sel_sido = st.selectbox("📍 지역 선택", ["전체", "서울", "인천", "경기", "부산", "대구", "대전", "광주", "세종"], index=0)
        with f_col2: sel_status_filter = st.selectbox("🚦 상태 필터", ["접수중/예정만 보기 (마감 제외)", "전체 보기 (마감 포함)", "🔥 무순위/줍줍만 보기"])
        with f_col3: kw_search = st.text_input("🔎 단지명/지역 검색", placeholder="예: 계양, 당산, 반포, 자이...")
        with f_col4:
            st.write("")
            if st.button("🔄 실시간 새로고침", type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        with st.spinner("한국부동산원 청약홈 서버에서 실시간 공고 데이터를 불러오는 중입니다..."):
            live_list, err_msg = fetch_realtime_applyhome(active_key, sel_sido)

        if not live_list:
            st.warning(f"⚠️ 현재 청약홈 API 서버 응답 대기 중입니다. ({err_msg if err_msg else '활용신청 직후라면 서버 동기화에 약 30분 소요될 수 있습니다.'})")
        else:
            df_live = pd.DataFrame(live_list)
            if sel_status_filter == "접수중/예정만 보기 (마감 제외)":
                df_live = df_live[~df_live["진행상태"].str.contains("마감", na=False)]
            elif sel_status_filter == "🔥 무순위/줍줍만 보기":
                df_live = df_live[df_live["구분"].str.contains("줍줍", na=False)]
            if kw_search.strip():
                k = kw_search.strip()
                df_live = df_live[df_live["단지명"].str.contains(k, na=False) | df_live["공급위치"].str.contains(k, na=False)]

            st.caption(f"✅ 한국부동산원 실시간 조회 결과: **총 {len(df_live)}건**")
            st.dataframe(df_live[["진행상태", "구분", "지역", "단지명", "공급세대수", "청약접수기간", "당첨자발표일", "시공사"]], use_container_width=True, height=250)

            if not df_live.empty:
                st.markdown("---")
                st.subheader("✍️ 목록에서 단지 선택 ➡️ 평형별 분양가 & 블로그 원고 1초 자동 완성")
                records = df_live.to_dict("records")
                sel_idx = st.selectbox(
                    "📌 블로그 글을 작성할 단지를 선택하세요:",
                    range(len(records)),
                    format_func=lambda i: f"[{records[i]['진행상태']}] [{records[i]['지역']}] {records[i]['단지명']} ({records[i]['구분']} / {records[i]['공급세대수']})"
                )
                target = records[sel_idx]

                is_jupjup = "줍줍" in target["구분"]
                model_prices = fetch_apt_price_detail(active_key, target.get("주택관리번호", ""), target.get("공고번호", ""), is_remndr=is_jupjup)
                auto_price_text = "\n".join(model_prices) if model_prices else "• 상세 평형별 공급금액은 아래 공식 모집공고문 원문 표 참조"

                st.markdown(f"""
                <div class="calc-box-orange">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0; color:#c05621;">🏢 [{target['지역']}] {target['단지명']} ({target['구분']})</h4>
                        <span class="tag-blue">{target['진행상태']}</span>
                    </div>
                    • <b>공급위치</b>: {target['공급위치']} | <b>공급규모</b>: {target['공급세대수']} | <b>시공사</b>: {target['시공사']}<br>
                    • <b>청약접수</b>: <b style="color:#c53030;">{target['청약접수기간']}</b> (특공: {target['특별공급일']} / 1순위: {target['1순위접수일']})<br>
                    • <b>당첨자발표</b>: <b>{target['당첨자발표일']}</b> | <b>계약기간</b>: {target['계약기간']} | <b>입주예정</b>: {target['입주예정월']}
                </div>
                """, unsafe_allow_html=True)

                st.link_button(f"📄 [{target['단지명']}] 청약홈 원본 모집공고문 새 창으로 열기", target["공고URL"], use_container_width=True)

                add_c1, add_c2 = st.columns(2)
                with add_c1: opt_real = st.text_input("📊 주변 실거래 시세 코멘트 (선택 입력)", placeholder="예: 인근 신축 84㎡ 실거래 8억 5,000만 원 선", key=f"or_{sel_idx}")
                with add_c2: opt_margin = st.text_input("📈 핵심 입지/안전마진 한 줄 평 (선택)", placeholder="예: 안전마진 약 1.5억 원 예상, 초역세권 대단지", key=f"om_{sel_idx}")

                real_line = opt_real.strip() if opt_real.strip() else "국토교통부 실거래가 공개시스템 기준 인근 동일 생활권 신축 시세 대조 권장"
                margin_line = opt_margin.strip() if opt_margin.strip() else "주변 시세 대비 합리적인 분양가로 실거주 및 중장기 가치 우수"
                qual_guide = (
                    "무순위/취소후재공급 물량으로 청약통장 가입 여부와 무관하게 신청 가능하며, 모집공고문상 거주지 요건 및 무주택 세대주/세대원 요건을 충족해야 합니다."
                    if is_jupjup else
                    f"입주자모집공고일({target['모집공고일']}) 현재 {target['지역']} 및 수도권 거주 만 19세 이상 세대주/세대원 중 청약통장 가입기간 및 예치금을 충족하신 분"
                )
                clean_tag = re.sub(r'[^가-힣a-zA-Z0-9]', '', target["단지명"].split()[0]) if target["단지명"] else "청약정보"

                auto_blog_text = f"""안녕하세요! 정확한 부동산 팩트체크와 핵심 청약 정보를 전해드리는 공인중개사 김태형입니다. 🙋‍♂️

한국부동산원 청약홈에 공식 공고된 '{target['단지명']}'의 분양 일정과 타입별 분양가, 신청 자격 팩트체크를 정리해 드립니다.
이번 공급은 {target['공급위치']} 일원에 총 {target['공급세대수']} 규모로 공급되는 {target['구분'].split()[-1]} 물량입니다.

📄 공식 입주자모집공고문 원문 및 인터넷 청약 접수처:
{target['공고URL']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 청약 일정 팩트체크 (날짜 필수 확인!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 입주자 모집공고일: {target['모집공고일']}
- 전체 청약 접수기간: {target['청약접수기간']}
- 특별공급 접수일: {target['특별공급일']}
- 1순위/일반 접수일: {target['1순위접수일']}
- 당첨자 발표일: {target['당첨자발표일']}
- 정당 계약기간: {target['계약기간']}
- 인터넷 접수처: 한국부동산원 청약Home (09:00 ~ 17:30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {target['단지명']}
- 공급 위치: {target['공급위치']} ({target['지역']})
- 공급 규모: 총 {target['공급세대수']} (입주예정: {target['입주예정월']})
- 시공사 / 시행사: {target['시공사']}
- 분양 문의처: {target['문의처'] if target['문의처'] else '공고문 내 견본주택 문의처 참조'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 주택형별 확정 공급금액 및 시세 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[주택형별 최고 공급금액 (공식 API 기준)]
{auto_price_text}

- 주변 실거래 시세 기준: {real_line}
- 입지 및 안전마진 평가: {margin_line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 신청 자격 및 부적격 예방 체크리스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 자격 핵심: {qual_guide}
- 주의사항: 모집공고일({target['모집공고일']})을 기준으로 무주택 여부, 거주지역 우선공급 요건, 재당첨 제한 여부를 판정하므로 접수 전 공고문 원문을 반드시 확인하시기 바랍니다.

내 집 마련과 주거 안정을 준비하시는 모든 분들의 당첨을 진심으로 응원합니다! 😊

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276

#{clean_tag} #{target['지역']}청약 #청약정보 #아파트청약 #{'무순위청약 #줍줍' if is_jupjup else '일반분양 #내집마련'} #청약홈 #공인중개사김소장 #우리부동산"""
                st.text_area("📋 네이버 블로그 자동 완성 원고 (전체 복사하여 바로 발행하세요)", auto_blog_text, height=450)

    with sub_tab2:
        lh_list = fetch_realtime_lh(active_key)
        if not lh_list:
            st.info("⏳ 현재 LH API 서버 동기화 대기 중입니다.")
        else:
            df_lh = pd.DataFrame(lh_list)
            lh_c1, lh_c2 = st.columns([1.5, 2.5])
            with lh_c1: lh_region = st.selectbox("📍 LH 지역 필터", ["전체", "서울", "인천", "경기", "전국"], key="lh_reg_sel")
            with lh_c2: lh_kw = st.text_input("🔎 LH 공고명 검색", placeholder="예: 행복주택, 매입임대, 신혼, 계양, 검단...", key="lh_kw_sel")

            if lh_region != "전체": df_lh = df_lh[df_lh["지역"].str.contains(lh_region, na=False)]
            if lh_kw.strip(): df_lh = df_lh[df_lh["단지명"].str.contains(lh_kw.strip(), na=False)]

            st.dataframe(df_lh, use_container_width=True, height=240)
            if not df_lh.empty:
                lh_records = df_lh.to_dict("records")
                sel_lh_idx = st.selectbox(
                    "📌 블로그 글을 생성할 LH 공고를 선택하세요:",
                    range(len(lh_records)),
                    format_func=lambda i: f"[{lh_records[i]['진행상태']}] [{lh_records[i]['지역']}] {lh_records[i]['단지명']}"
                )
                t_lh = lh_records[sel_lh_idx]
                st.link_button(f"🌐 [{t_lh['단지명']}] LH청약플러스 공식 공고문 열기", t_lh["공고URL"], use_container_width=True)

                lh_blog = f"""안녕하세요! 청년·신혼부부 및 무주택 서민의 주거 안정을 돕는 공인중개사 김태형입니다. 🙋‍♂️

한국토지주택공사(LH) 청약플러스에 공식 게시된 '{t_lh['단지명']}' 모집공고 소식을 전해드립니다.

🌐 LH청약플러스 공식 공고문 확인 및 인터넷 접수 링크:
{t_lh['공고URL']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 공고 개요 및 핵심 일정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 공고명: {t_lh['단지명']}
- 공급 유형: {t_lh['구분']}
- 관할 지역: {t_lh['지역']}
- 공고 게시일: {t_lh['공고게시일']}
- 접수 마감일: {t_lh['접수마감일']} (현재 상태: {t_lh['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 2. 공공임대·행복주택 핵심 혜택 및 체크포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 주변 시세 대비 30~80% 수준의 저렴한 임대보증금과 월 임대료로 안정적인 장기 거주 가능
- 보증금-월세 상호전환 제도를 활용하면 버팀목 전세대출 등을 통해 월 고정 주거비를 대폭 낮출 수 있습니다.
- 행복주택·청년매입임대 등 공공임대주택은 당첨되어 입주하더라도 기존 청약통장의 효력이 그대로 100% 유지됩니다!

우리부동산 공인중개사사무소 대표 김태형 ☎ 010-2660-8276
#LH청약플러스 #공공임대 #행복주택 #청년매입임대 #{t_lh['지역'].replace(' ','')}임대주택 #공인중개사김소장"""
                st.text_area("📋 LH 공공임대 블로그 자동 완성 원고", lh_blog, height=380)

# =============================================================
# 8. ⚖️ [완전 복구 & 디벨롭] 법원경매 허브 (5단계 배당표 + 턴키 자금표 + 전문 블로그)
# =============================================================
elif menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 & 수도권 주택·인천 공장 심층 수지분석")
    st.caption("대법원 법원경매정보 연동 기반: 수도권 주택(아파트)·인천공장 5단계 실시간 배당표, 기계기구 분리평가, 턴키 자금표 및 경매 전문 블로그 원클릭 완성!")

    factory_list, apt_list = get_auction_data()

    with st.expander("📌 [필독] 경매 입찰 전 물건 유형별 필수 확인 체크리스트 (실무 가이드)", expanded=False):
        c_tab1, c_tab2 = st.tabs(["🏭 공장·창고 경매 필수 확인 사항", "🏢 주택·아파트 경매 필수 확인 사항"])
        with c_tab1:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 산업단지 입주자격 (산집법 제38조)</b>: 국가산단/일반산단 경매는 입주 부적격자 낙찰 시 6개월 내 처분명령 대상. 입주업종 코드 사전 확인 필수.<br>
                <b>2. 기계기구 감정가 분리</b>: 공장 총 감정가 중 기계(CNC, 프레스, 크레인) 가치와 실제 현장 존치·가동 여부 분리 필수.<br>
                <b>3. 한전 단전 및 산업용 전기 체납</b>: 기본요금 연체로 단전된 경우 새로 인입 시 수천만 원 분담금 발생 가능 (한전 123 확인).
            </div>
            """, unsafe_allow_html=True)
        with c_tab2:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 대항력 있는 선순위 임차인</b>: 전입일자가 말소기준권리보다 빠르고 미배당 보증금 존재 시 낙찰자가 전액 인수.<br>
                <b>2. 토지거래허가구역 경매 특례</b>: 경매 취득 시 토지거래허가 면제되어 2년 실거주의무 없이 즉시 전세 세팅 가능.<br>
                <b>3. 공용부분 미납관리비 승계</b>: 대법원 판례상 최근 3년 치 공용 관리비는 낙찰자 인수 대상.
            </div>
            """, unsafe_allow_html=True)

    auction_tab1, auction_tab2 = st.tabs(["🏢 수도권 주택(아파트) 경매 & 5단계 배당표·블로그", "🏭 인천 전지역 공장·창고 경매 & 턴키 수지표·블로그"])

    with auction_tab1:
        f_c1, f_c2 = st.columns([2.0, 2.5])
        with f_c1: major_region = st.selectbox("📍 광역 시·도 필터", ["전체 모아보기 (수도권 전지역)", "서울특별시", "경기도", "인천광역시"], index=0)
        with f_c2: kw_val = st.text_input("🔎 단지명 / 사건번호 검색", placeholder="예: 아크로, 푸르지오, 청라, 10550...")

        filtered_apt = [a for a in apt_list if (major_region == "전체 모아보기 (수도권 전지역)" or a["시도"] == major_region) and (not kw_val.strip() or kw_val.strip() in a["소재지"] or kw_val.strip() in a["사건번호"])]

        if filtered_apt:
            st.dataframe(pd.DataFrame([{
                "사건번호": a["사건번호"], "법원": a["법원"], "시도": a["시도"], "소재지": a["소재지"],
                "평형": a["평형타입"], "감정가": a["감정가"], "최저가": a["최저가"], "추천입찰가": a["추천입찰가밴드"], "매각기일": a["매각기일"]
            } for a in filtered_apt]), use_container_width=True, height=180)

            chosen_apt_idx = st.selectbox("📌 정밀 분석 및 블로그 포스팅을 생성할 주택 사건 선택:", range(len(filtered_apt)), format_func=lambda i: f"[{filtered_apt[i]['사건번호']}] {filtered_apt[i]['소재지']} (최저가: {filtered_apt[i]['최저가']})")
            cur_apt = filtered_apt[chosen_apt_idx]
            qa_apt = cur_apt["권리분석"]
            case_key = cur_apt['사건번호'].replace("타경", "_")

            col_l, col_r = st.columns([1.2, 1.3])
            with col_l:
                st.markdown("##### 📊 실시간 5단계 배당표 시뮬레이터")
                sim_bid = st.number_input("가상 낙찰가 입력 (원)", value=int(cur_apt['최저가원']), step=10000000, key=f"sim_b_{case_key}")
                bd = cur_apt["배당정보"]
                rem = sim_bid
                pay_exp = min(rem, bd["경매비용"]); rem -= pay_exp
                pay_tax = min(rem, bd["당해세"]); rem -= pay_tax
                pay_pri = min(rem, bd["최우선변제"]); rem -= pay_pri
                pay_mort = min(rem, bd["선순위근저당"]); rem -= pay_mort
                pay_rent = min(rem, bd["임차인배당"]); rem -= pay_rent

                st.markdown(f"""
                <div style="background:#f7fafc; border:1px solid #cbd5e0; border-radius:6px; padding:12px; font-size:13px; line-height:1.8;">
                    1순위 경매집행비용 배당: <b>{pay_exp:,}원</b><br>
                    2순위 당해세(재산세/종부세) 배당: <b>{pay_tax:,}원</b><br>
                    3순위 소액임차인 최우선변제: <b>{pay_pri:,}원</b><br>
                    4순위 선순위 근저당권 배당: <b>{pay_mort:,}원</b><br>
                    5순위 일반 임차인 배당금: <b>{pay_rent:,}원</b><br>
                    🚩 <b>낙찰자 추가 인수 보증금</b>: <span style="color:#276749; font-weight:bold;">{qa_apt['인수보증금']:,}원 (소멸주의 안전물건)</span>
                </div>
                """, unsafe_allow_html=True)

            with col_r:
                st.markdown("##### 💰 주택 경락잔금대출 & 실투자금 계산기")
                u_ltv = st.slider("경락잔금대출 LTV (%)", 40, 80, 70, 5, key=f"al_{case_key}")
                tax = int(sim_bid * (0.011 if sim_bid <= 600000000 else 0.035))
                loan = min(int(cur_apt['감정가원'] * 0.7), int(sim_bid * (u_ltv / 100.0)))
                cash = (sim_bid - loan) + tax + cur_apt['미납관리비'] + 2000000
                st.markdown(f"""
                <div class="calc-box-orange">
                    • 예상 낙찰가: <b>{sim_bid:,}원</b> | 경락대출({u_ltv}%): 약 <b>{loan:,}원</b><br>
                    • 취득세 등: 약 {tax:,}원 | 공용 미납관리비: 약 {cur_apt['미납관리비']:,}원<br>
                    • 명도 협의 이사비 예산: 약 2,000,000원<br>
                    <hr style="margin:6px 0;">
                    🚩 <b>필요 순수 자기자본(현금)</b>: <span style="font-size:20px; color:#c53030; font-weight:bold;">약 {cash:,}원</span>
                </div>
                """, unsafe_allow_html=True)

            clean_apt_name = cur_apt['소재지'].split('(')[-1].replace(')', '').split()[0] if '(' in cur_apt['소재지'] else "아파트경매"
            apt_blog_post = f"""안녕하세요! 수도권 법원경매 권리분석 및 실전 입찰 전문 공인중개사 김태형입니다. 🙋‍♂️

시세 대비 확실한 안전마진을 확보할 수 있는 우량 아파트 경매 사건을 브리핑해 드립니다.
오늘 분석할 물건은 {cur_apt['법원']}에서 진행되는 사건번호 {cur_apt['사건번호']} 매각 사건입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 매각 일정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_apt['사건번호']} ({cur_apt['법원']})
- 소재지: {cur_apt['소재지']}
- 주택유형 및 면적: {cur_apt['주택유형']} {cur_apt['평형타입']} ({cur_apt['층수']})
- 매각기일: {cur_apt['매각기일']} ({cur_apt['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정가 vs 실거래 시세 안전마진 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 최초 감정가: {cur_apt['감정가']}
- 현재 최저매각가격: {cur_apt['최저가']} (입찰보증금 10%: {cur_apt['입찰보증금']})
- 최근 실거래 시세: {cur_apt['최근실거래가']}
- 추천 입찰가 밴드: {cur_apt['추천입찰가밴드']} (예상 시세차익: {cur_apt['예상시세차익']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ 3. 김소장의 정밀 권리분석 체크포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 말소기준권리: {qa_apt['말소기준권리']} (이후 모든 권리 소멸)
✅ 임차인 대항력 분석: {qa_apt['임차인분석']} (낙찰자 인수 보증금 {qa_apt['인수보증금']}원)
✅ 규제 특례 사항: {qa_apt['토허제특례']}
✅ 명도 난이도: {qa_apt['명도난이도']}

현장 임장 및 입찰 대리, 경락잔금대출 상담은 언제든 편하게 문의해 주십시오.
우리부동산 공인중개사사무소 대표 김태형 ☎ 010-2660-8276
#{clean_apt_name} #아파트경매 #법원경매 #권리분석 #경락잔금대출 #우리부동산 #공인중개사김소장"""
            st.text_area("📋 아파트 경매 네이버 블로그 완성본", apt_blog_post, height=340)

    with auction_tab2:
        st.dataframe(pd.DataFrame([{
            "사건번호": f["사건번호"], "법원": f["법원"], "소재지": f["소재지"],
            "용도": f["세부용도"], "바닥평수": f"{f['바닥평수']}평", "감정가": f["총감정가"],
            "최저가": f["최저가"], "보증금": f["입찰보증금"], "매각기일": f["매각기일"]
        } for f in factory_list]), use_container_width=True, height=160)

        chosen_fac_idx = st.selectbox("📌 정밀 분석 및 블로그 포스팅할 공장 경매 사건 선택:", range(len(factory_list)), format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']} (최저가: {factory_list[i]['최저가']})")
        cur_fac = factory_list[chosen_fac_idx]
        case_fac_key = cur_fac['사건번호'].replace("타경", "_")
        pure_real_estate = cur_fac['토지감정가원'] + cur_fac['건물감정가원']

        fc1, fc2 = st.columns([1.2, 1.3])
        with fc1:
            st.markdown("##### ⚖️ 공장 권리분석 & 기계기구 분리평가")
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #cbd5e0; border-radius:6px; padding:12px; font-size:13px; line-height:1.8;">
                • <b>말소기준권리</b>: {cur_fac['권리분석']['말소기준']}<br>
                • <b>임차인/유치권</b>: {cur_fac['권리분석']['임차인']} / {cur_fac['권리분석']['유치권']}<br>
                • <b>순수 부동산(토지+건물) 감정가</b>: <b style="color:#2b6cb0;">{pure_real_estate:,}원</b><br>
                • <b>기계기구 분리 감정액</b>: <b>{cur_fac['기계기구감정가원']:,}원</b> ({cur_fac['기계감정내역']})<br>
                • <b>산단 입주자격</b>: {cur_fac['산단입주자격']}
            </div>
            """, unsafe_allow_html=True)

        with fc2:
            st.markdown("##### 💰 공장 턴키 정상가동 실시간 자금조달표")
            f_bid = st.number_input("예상 낙찰가 (원)", value=int(cur_fac['최저가원']), step=10000000, key=f"fb_{case_fac_key}")
            f_ltv = st.slider("기업 시설자금대출 LTV (%)", 50, 85, 75, 5, key=f"fl_{case_fac_key}")
            f_tax = int(f_bid * 0.046)
            f_loan = min(int(cur_fac['총감정가원'] * 0.75), int(f_bid * (f_ltv / 100.0)))
            f_cash = (f_bid - f_loan) + f_tax + cur_fac['연체관리비추정'] + 15000000
            st.markdown(f"""
            <div class="calc-box-orange">
                • 예상 낙찰가: <b>{f_bid:,}원</b> | 시설대출({f_ltv}%): 약 <b>{f_loan:,}원</b><br>
                • 취득세(4.6%): {f_tax:,}원 | 연체전기료/관리비 추정: {cur_fac['연체관리비추정']:,}원<br>
                • 수전설비/호이스트 점검 예비비: 약 15,000,000원<br>
                <hr style="margin:6px 0;">
                🚩 <b>턴키 정상가동 필요 현금</b>: <span style="font-size:20px; color:#c53030; font-weight:bold;">약 {f_cash:,}원</span>
            </div>
            """, unsafe_allow_html=True)

        clean_fac_loc = cur_fac['소재지'].split()[1] + " " + cur_fac['소재지'].split()[2]
        fac_blog_post = f"""안녕하세요! 인천 서구 및 주요 산업단지 공장·창고 전문 공인중개사 김태형입니다. 🙋‍♂️

제조업 대표님들의 자가 공장 마련 비용을 획기적으로 낮출 수 있는 알짜배기 공장 경매 사건을 브리핑해 드립니다.
오늘 소개해 드리는 물건은 {cur_fac['법원']} 사건번호 {cur_fac['사건번호']} 공장입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 입찰 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_fac['사건번호']} ({cur_fac['법원']})
- 소재지: {cur_fac['소재지']}
- 대지면적 / 건물면적: 대지 {cur_fac['대지면적']} / 건물 {cur_fac['건물면적']} (1층 바닥 {cur_fac['바닥평수']}평)
- 매각기일: {cur_fac['매각기일']} ({cur_fac['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정평가 분석 (기계기구 분리평가 필수!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 감정가액: {cur_fac['총감정가']}
- 현재 최저가: {cur_fac['최저가']} (보증금 10%: {cur_fac['입찰보증금']})
- 순수 부동산(토지+건물) 가치: 약 {pure_real_estate:,}원
- 기계기구 감정액: 약 {cur_fac['기계기구감정가원']:,}원 ({cur_fac['기계감정내역']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 3. 제조 설비 스펙 및 권리분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 현장 제원: {cur_fac['제원및코멘트']}
- 권리분석: 말소기준권리({cur_fac['권리분석']['말소기준']}) 이후 전액 소멸, {cur_fac['권리분석']['유치권']}
- 산단 입주 적격성: {cur_fac['산단입주자격']}

공장 경매는 낙찰 후 업종 인허가와 한전 단전 해제, 경락잔금대출(최대 75~80%)까지 원스톱으로 점검해야 실패가 없습니다. 현장 임장 동행 및 입찰 대리 상담은 편하게 연락 주십시오!

인천 공장·창고 중개 및 법원경매 전문
우리부동산 공인중개사사무소 대표 김태형 ☎ 010-2660-8276
#{clean_fac_loc.replace(' ','')}공장 #인천공장경매 #창고경매 #법원경매 #호이스트공장 #우리부동산 #공인중개사김소장"""
        st.text_area("📋 공장 경매 네이버 블로그 완성본", fac_blog_post, height=340)