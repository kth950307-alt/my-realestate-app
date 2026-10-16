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
    html, body, [data-testid="stAppViewContainer"], .notranslate, em, i { translate: no !important; font-style: normal !important; }
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
# ⚡ CSV 데이터베이스 관리 함수
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

def load_hunting_properties():
    if os.path.exists(HUNTING_CSV):
        df = pd.read_csv(HUNTING_CSV)
        for col, d_val in [("대장체크", "정상(적법)"), ("임대만기예정일", "")]:
            if col not in df.columns: df[col] = d_val
        return df
    init_data = [
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-822", "건물유형": "집합공장", "소재지전체": "인천 서구 석남동 223-822", "소유자/법인명": "관리사무소/집합", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": "집합공장. 관리사무소 방문하여 임대/매매 호실 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-932", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-932", "소유자/법인명": "홍정미", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": "개인소유. 현장 방문하여 건물주 연락처 탐문"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-651", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-651", "소유자/법인명": "소유자 확인중", "상호": "", "연락처": "", "진행상태": "📞 전화 확인", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": "대장 열람 후 유선 컨택"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-360", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-360", "소유자/법인명": "이해영, 최완규", "상호": "신창코팅", "연락처": "032-577-0104", "진행상태": "📞 전화 확인", "대장체크": "정상(적법)", "임대만기예정일": "2026-11-30", "현장메모": "신창코팅 유선 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-559", "건물유형": "운수/차고지", "소재지전체": "인천 서구 석남동 223-559", "소유자/법인명": "한미교통주식회사", "상호": "한미교통", "연락처": "032-571-1032", "진행상태": "📞 전화 확인", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": "법인 총무팀 유선 컨택"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-557", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-557", "소유자/법인명": "김용주", "상호": "명인기공", "연락처": "032-579-3171", "진행상태": "🚗 방문 필요", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": "명인기공 방문 및 유선 확인"}
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

def get_auction_data():
    factory_auctions = [
        {
            "사건번호": "2025타경10452", "법원": "인천지방법원 본원 (경매5계)", "소재지": "인천광역시 서구 가좌동 556-12", "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)", "건물면적": "528.9㎡ (약 160평)", "바닥평수": 160, "현재동력kW": 75, "현재호이스트": "호이스트 5T 완비",
            "총감정가원": 1850000000, "총감정가": "18억 5,000만 원", "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)", "입찰보증금": "1억 2,950만 원 (10%)",
            "토지감정가원": 1350000000, "건물감정가원": 420000000, "기계기구감정가원": 80000000, "기계감정내역": "천장주행 크레인 5T 1식, 수전설비 75kW",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회 (70%)",
            "권리분석": {"말소기준": "2019-04-12 근저당권 (신한은행)", "임차인": "대항력 없는 후순위 임차인 (보증금 3,000만 원)", "유치권": "유치권 신고 없음 (깨끗)", "인수권리": "인수 권리 없음 (소멸주의)"},
            "산단입주자격": "일반공업지역 (산집법 입주계약 불필요, 모든 제조업 입주 가능)", "연체관리비추정": 3500000,
            "배당정보": {"경매비용": 12000000, "당해세": 8000000, "최우선변제": 0, "선순위근저당": 950000000, "임차인배당": 30000000},
            "제원및코멘트": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활. 가좌IC 3분 거리.",
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2025타경11208", "법원": "인천지방법원 본원 (경매3계)", "소재지": "인천광역시 서구 오류동 검단일반산단 42-5", "세부용도": "신축급 산단공장",
            "대지면적": "991.7㎡ (약 300평)", "건물면적": "793.3㎡ (약 240평)", "바닥평수": 240, "현재동력kW": 150, "현재호이스트": "호이스트 5T 2기 완비",
            "총감정가원": 2680000000, "총감정가": "26억 8,000만 원", "최저가원": 1876000000, "최저가": "18억 7,600만 원 (70%)", "입찰보증금": "1억 8,760만 원 (10%)",
            "토지감정가원": 1900000000, "건물감정가원": 750000000, "기계기구감정가원": 30000000, "기계감정내역": "수전설비 150kW 및 크레인",
            "매각기일": "2026-11-19", "진행상태": "유찰 1회 (70%)",
            "권리분석": {"말소기준": "2021-08-19 근저당권 (기업은행)", "임차인": "소유자 직접 점유 (대항력 없음)", "유치권": "유치권 신고 없음", "인수권리": "소멸주의"},
            "산단입주자격": "검단일반산단 관리구역 (산집법상 제조업 입주적격업체 사전 확인 필수)", "연체관리비추정": 6000000,
            "배당정보": {"경매비용": 16000000, "당해세": 12000000, "최우선변제": 0, "선순위근저당": 1400000000, "임차인배당": 0},
            "제원및코멘트": "산단 코너 필지, 40ft 츄레라 회전 가능 마당, 층고 10m, 동력 150kW 대용량.",
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    apt_auctions = [
        {
            "사건번호": "2025타경10550", "법원": "서울중앙지방법원 (경매4계)", "시도": "서울특별시",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크 104동)", "주택유형": "아파트", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층 (로열층 한강뷰)",
            "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회 (80%)", "실거래시세원": 4500000000, "최근실거래가": "45억 원 선",
            "권리분석": {"말소기준권리": "2019-12-10 근저당권 (신한은행)", "임차인분석": "소유자 세대 점유 (대항력 있는 임차인 없음)", "인수보증금": 0, "토허제특례": "경매 취득 시 토지거래허가구역 실거주의무 면제 (전세 갭투자 가능)", "명도난이도": "보통 (소유자 거주, 협의 수월)"},
            "미납관리비": 1800000, "추천입찰가밴드": "36억 5,000만 ~ 37억 8,000만 원", "예상시세차익": "약 7억 ~ 8.5억 원",
            "배당정보": {"경매비용": 18000000, "당해세": 15000000, "최우선변제": 0, "선순위근저당": 2800000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        },
        {
            "사건번호": "2025타경11430", "법원": "인천지방법원 본원 (경매6계)", "시도": "인천광역시",
            "소재지": "인천광역시 서구 청라동 155-2 (청라호수공원 한신더휴 302동)", "주택유형": "아파트", "평형타입": "전용 84.88㎡ (34평형)", "층수": "18층 / 30층",
            "감정가원": 820000000, "감정가": "8억 2,000만 원", "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "입찰보증금": "5,740만 원 (10%)",
            "매각기일": "2026-11-18", "진행상태": "유찰 1회 (70%)", "실거래시세원": 810000000, "최근실거래가": "8억 1,000만 원 선",
            "권리분석": {"말소기준권리": "2021-02-18 근저당권 (신한은행)", "임차인분석": "후순위 임차인 (보증금 1억 원 전액 배당 소멸)", "인수보증금": 0, "토허제특례": "비규제지역 (경락대출 70~80% 가능)", "명도난이도": "보통 (이사비 협의 권장)"},
            "미납관리비": 450000, "추천입찰가밴드": "6억 3,000만 ~ 6억 6,000만 원", "예상시세차익": "약 1.5억 ~ 1.8억 원",
            "배당정보": {"경매비용": 6500000, "당해세": 2400000, "최우선변제": 0, "선순위근저당": 420000000, "임차인배당": 100000000},
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    return factory_auctions, apt_auctions

# =============================================================
# 📌 업무 메뉴 네비게이션 (우리부동산 전용 10개 핵심 업무 탭)
# =============================================================
MENU_DICT = {
    "FACTORY_HUNT": "🏃 [임장/작업] 현장 공장 물건따기 파이프라인",
    "FACTORY_REG": "🏭 [주업] 공장 매물 등록 & 인허가·손님 역매칭",
    "NEW_DEV": "🏗️ [주업] 신축공장 맞춤 분양 설계 & 제안서",
    "CUSTOMER_CRM": "📋 [주업] 공장 손님 장부 (CRM & 투어스케줄러)",
    "FACTORY_BOOK": "📁 [주업] 공장 보유 매물 장부 (멀티장바구니)",
    "PRICE_AI": "🔍 [주업] 공장·창고 AI 시세 & 건물주 설득 리포트",
    "BLOG_FOOD": "🍜 [부업] 맛집 탐방 블로그 (SEO·영수증·숏폼)",
    "BLOG_LIFE": "🧢 [부업] 일상·핫플·운동 블로그 (주제별 맞춤)",
    "APPLY_HOME": "🏢 [부업] 실시간 청약·줍줍 & LH 공공임대 허브",
    "AUCTION_HUB": "⚖️ [부업] 법원경매 목록 허브 (인천공장 & 아파트)"
}

menu_choice = st.sidebar.radio("📌 업무 시스템 메뉴", list(MENU_DICT.values()), index=0)
st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()
st.sidebar.caption("🏢 **우리부동산 대표 공인중개사 김태형 전용 시스템**")

# =============================================================
# 0. 🏃 [임장/작업] 현장 공장 물건따기 파이프라인
# =============================================================
if menu_choice == MENU_DICT["FACTORY_HUNT"]:
    st.title("🏃 현장 공장 물건따기 파이프라인 (임장 장부)")
    st.caption("작업 중 지번 ➡️ 임대만기 도래 재공략 알람 ➡️ 확보 성공 시 '🎉 확보완료 매물함' 분리 이관 및 1번 탭 정식 매물 원클릭 등록!")

    df_h = load_hunting_properties()
    today_d = datetime.today().date()

    exp_alerts = []
    for _, hr in df_h.iterrows():
        exp_str = str(hr.get("임대만기예정일", "")).strip()
        if exp_str and exp_str != "nan" and "완료" not in str(hr.get("진행상태", "")):
            try:
                e_dt = datetime.strptime(exp_str[:10], "%Y-%m-%d").date()
                rem_days = (e_dt - today_d).days
                if -30 <= rem_days <= 60:
                    exp_alerts.append((hr["동"], hr["지번"], hr["소유자/법인명"], hr.get("연락처", ""), exp_str, rem_days))
            except Exception: pass

    if exp_alerts:
        st.markdown("##### 🔔 [만기 도래 타깃 재공략 경보] 임대차 만기가 60일 이내로 다가온 현장입니다!")
        for d_nm, jb, ow, ph, ex_d, r_d in exp_alerts:
            st.markdown(f"<div class='remind-card-red'>🚨 <b>{d_nm} {jb}</b> ({ow} / {ph}) | 만기예정일: <b>{ex_d} (D-{r_d})</b> ➡️ 지금 바로 전화/방문하여 차기 공실 물건을 선점하세요!</div>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📌 전체 작업 지번", f"{len(df_h)}건")
    m2.metric("🚗 현장 방문 대상", f"{len(df_h[df_h['진행상태'].str.contains('방문', na=False)])}건")
    m3.metric("📞 전화 확인 대상", f"{len(df_h[df_h['진행상태'].str.contains('전화', na=False)])}건")
    m4.metric("🎉 물건 확보 성공", f"{len(df_h[df_h['진행상태'].str.contains('완료', na=False)])}건")

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
            st.info("현재 작업 중인 지번이 없습니다.")
        else:
            status_opts = ["🚗 방문 필요", "📞 전화 확인", "🔄 재트라이", "보류/거절"]
            ledger_opts = ["정상(적법)", "위반건축물있음", "근저당과다", "미확인"]
            for idx, r in active_df.iterrows():
                full_addr = f"인천 서구 {r['동']} {r['지번']}"
                map_url = f"https://map.naver.com/p/search/{full_addr.replace(' ', '%20')}"

                owner_info = f"👤 {r['소유자/법인명']}"
                if str(r.get("상호", "")).strip() and str(r.get("상호", "")) != "nan": owner_info += f" ({r['상호']})"
                if str(r.get("연락처", "")).strip() and str(r.get("연락처", "")) != "nan": owner_info += f" 📞 {r['연락처']}"

                curr_st = str(r["진행상태"])
                st_idx = next((s_i for s_i, s_name in enumerate(status_opts) if s_name.split()[-1] in curr_st), 0)
                curr_lg = str(r.get("대장체크", "정상(적법)"))
                lg_idx = ledger_opts.index(curr_lg) if curr_lg in ledger_opts else 0

                c_info, c_lg, c_exp, c_map, c_status, c_done_btn = st.columns([3.0, 1.1, 1.1, 0.8, 1.2, 1.0])
                with c_info:
                    st.markdown(f"**📍 {r['동']} {r['지번']}** <span class='tag-blue'>{r['건물유형']}</span> <span style='font-size:13px; color:#4a5568;'>{owner_info}</span><br><span style='font-size:12px; color:#718096;'>💡 {r.get('현장메모','')}</span>", unsafe_allow_html=True)
                with c_lg:
                    new_lg = st.selectbox("대장/등기", ledger_opts, index=lg_idx, key=f"hlg_{idx}", label_visibility="collapsed")
                    if new_lg != curr_lg:
                        df_h.at[idx, "대장체크"] = new_lg
                        save_all_hunting(df_h)
                        st.rerun()
                with c_exp:
                    cur_exp_val = str(r.get("임대만기예정일", "")) if pd.notna(r.get("임대만기예정일", "")) else ""
                    new_exp = st.text_input("만기일", value=cur_exp_val, placeholder="만기:2027-03-01", key=f"hexp_{idx}", label_visibility="collapsed")
                    if new_exp != cur_exp_val:
                        df_h.at[idx, "임대만기예정일"] = new_exp
                        save_all_hunting(df_h)
                        st.rerun()
                with c_map:
                    st.link_button("🗺️ 지도", map_url, use_container_width=True)
                with c_status:
                    new_st = st.selectbox("상태", status_opts, index=st_idx, key=f"hst_{idx}", label_visibility="collapsed")
                    if new_st != r["진행상태"]:
                        df_h.at[idx, "진행상태"] = new_st
                        save_all_hunting(df_h)
                        st.rerun()
                with c_done_btn:
                    if st.button("🎉 확보!", key=f"h_done_{idx}", type="primary", use_container_width=True):
                        df_h.at[idx, "진행상태"] = "🎉 확보 완료"
                        save_all_hunting(df_h)
                        st.success(f"🎉 {r['동']} {r['지번']} 확보 성공!")
                        st.rerun()
                st.markdown("<hr style='margin:3px 0 6px 0; border:0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)

        with st.expander("💬 건물주/대표님 부재 시 문자·카톡 발송 표준 문구 복사"):
            sms_tpl = """안녕하십니까 대표님! 인천 서구 공장·창고 전문 우리부동산 김태형 대표공인중개사입니다.
소유하고 계신 공장과 관련하여 우량 제조기업 임차(매수) 대기 수요가 있어 귀한 인연 맺고자 연락드렸습니다.
혹시 향후 임대차 만기나 매각 계획이 있으시다면 편하게 말씀 남겨주십시오. 신속하고 정확하게 브리핑 진행해 드리겠습니다!
- 우리부동산 대표 김태형 올림 (010-2660-8276)"""
            st.text_area("문자 복사용", sms_tpl, height=100)

    with h_tab_done:
        st.subheader("🎉 [수주 성공] 확보 완료 매물함")
        done_df = df_h[df_h["진행상태"].str.contains("완료", na=False)].copy()
        if done_df.empty:
            st.info("아직 확보 완료된 매물이 없습니다.")
        else:
            for d_idx, d_row in done_df.iterrows():
                st.markdown(f"""
                <div class="hunt-item-done">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:16px; font-weight:bold; color:#1a365d;">📍 {d_row['동']} {d_row['지번']} ({d_row['소유자/법인명']}) [{d_row.get('대장체크','정상')}]</span>
                        <span style="font-size:13px; color:#276749; font-weight:bold;">📞 {d_row.get('연락처','연락처 미등록')}</span>
                    </div>
                    <div style="font-size:12.5px; color:#4a5568; margin-top:4px;">💡 <b>임장 히스토리</b>: {d_row.get('현장메모','')}</div>
                </div>
                """, unsafe_allow_html=True)
                col_pr, col_ar, col_to_reg, col_del = st.columns([1.5, 1.2, 1.5, 0.8])
                with col_pr: tr_price = st.text_input("보증금 / 월세 *", placeholder="예: 보 3,000 / 월 250", key=f"tr_p_{d_idx}")
                with col_ar: tr_area = st.text_input("전용 평수 *", placeholder="예: 75평", key=f"tr_a_{d_idx}")
                with col_to_reg:
                    st.write("")
                    if st.button("🚀 1번 탭 정식매물로 이관", key=f"btn_tr_{d_idx}", type="primary", use_container_width=True):
                        if tr_price and tr_area:
                            save_property({
                                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": "현재 공실(즉시입주)", "계약만료일": "즉시 협의",
                                "거래구분": "임대차(월세)", "소재지(권역)": f"인천 서구 {d_row['동']}", "상세주소(지번)": f"인천 서구 {d_row['동']} {d_row['지번']}",
                                "임대인(건물주)": d_row['소유자/법인명'], "임대인연락처": d_row['연락처'], "가격(보/월)": tr_price, "면적": tr_area,
                                "층고": "처마 7.5m", "동력": "30kW", "호이스트": "호이스트 무관", "도로/주차": "화물차 접안 편리",
                                "대형차량": "11T 윙바디 수월", "특징메모": f"[현장확보/{d_row.get('대장체크','적법')}] {d_row.get('현장메모','')}"
                            })
                            st.success("✅ 정식 매물 장부로 이관 완료!")
                with col_del:
                    st.write("")
                    if st.button("목록 제거", key=f"btn_d_del_{d_idx}", use_container_width=True):
                        df_h = df_h.drop(df_h.index[d_idx]).reset_index(drop=True)
                        save_all_hunting(df_h)
                        st.rerun()

    with h_tab2:
        st.subheader("📥 텍스트 복사·붙여넣기로 지번 일괄 자동 파싱")
        raw_text_batch = st.text_area("작업 메모 텍스트 붙여넣기:", height=150, placeholder="석남동 223-360 > 이해영 , 최완규 (신창코팅) 032-577-0104")
        if st.button("⚡ 1초 만에 자동 분석하여 장부에 등록하기", type="primary", use_container_width=True):
            if raw_text_batch.strip():
                new_entries = []
                for line in raw_text_batch.strip().split("\n"):
                    line = line.strip()
                    if not line: continue
                    dong_m = re.search(r'(석남동|가좌동|원창동|경서동|도화동|송림동|오류동|청라동|효성동)', line)
                    dong = dong_m.group(1) if dong_m else "석남동"
                    jibun_m = re.search(r'\b(\d+-\d+|\d+)\b', line)
                    if not jibun_m: continue
                    jibun = jibun_m.group(1)
                    phone_m = re.search(r'(0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})', line)
                    phone = phone_m.group(1).replace(" ", "-") if phone_m else ""
                    biz_m = re.search(r'\((.*?)\)', line)
                    biz = biz_m.group(1) if biz_m else ""
                    rem_text = line.replace(dong, "").replace(jibun, "").replace(phone_m.group(1) if phone_m else "", "").replace(f"({biz})", "").replace(">", "").strip()
                    owner = rem_text.split(",")[0].strip()[:15] if rem_text else "소유자 확인중"
                    new_entries.append({
                        "등록일": datetime.today().strftime("%Y-%m-%d"), "동": dong, "지번": jibun,
                        "건물유형": "집합공장" if "집합" in line else "일반공장", "소재지전체": f"인천 서구 {dong} {jibun}",
                        "소유자/법인명": owner, "상호": biz, "연락처": phone,
                        "진행상태": "📞 전화 확인" if phone else "🚗 방문 필요", "대장체크": "정상(적법)", "임대만기예정일": "", "현장메모": line
                    })
                if new_entries:
                    df_h = pd.concat([pd.DataFrame(new_entries), df_h], ignore_index=True).drop_duplicates(subset=["동", "지번"], keep="first")
                    save_all_hunting(df_h)
                    st.success(f"✅ 총 {len(new_entries)}건 등록 완료!")
                    st.rerun()

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 & 인허가 판독 & 복비 계산 & 역매칭
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_REG"]:
    st.title("🏭 공장 매물 등록 & 인허가 판독 & 대기손님 자동 역매칭")
    st.caption("매물 저장 시 [용도지역별 인허가 가이드], [비주거용 확인·설명서 표준 텍스트], [환산보증금/복비], [대기손님 역매칭]이 동시 실행됩니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처", expanded=False):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 556-12")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 박회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")

    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 *", value="인천 서구 가좌동")
    with b2: deal_type = st.selectbox("거래 형태 *", ["임대차(월세)", "매매", "임대/매매 겸용"])
    with b3: vacancy_status = st.selectbox("입주 상태 *", ["현재 공실(즉시입주)", "협의 입주", "만기 후 입주"])
    with b4: expire_date = st.text_input("입주 가능일", value="즉시 협의 가능")

    c1, c2, c3 = st.columns(3)
    with c1:
        dep_man = st.number_input("보증금 또는 매매가 (만 원) *", min_value=0, value=3000, step=500)
        rent_man = st.number_input("월세 (만 원, 매매 시 0) *", min_value=0, value=250, step=10)
        area = st.text_input("실사용 면적/평수 *", value="1층 80평")
    with c2:
        ceiling = st.text_input("처마 층고", value="처마 7.5m")
        power = st.text_input("인입 동력 (kW) *", value="50kW")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음"])
    with c3:
        road = st.text_input("접면 도로 폭(m)", value="10m 도로 접")
        parking_count = st.text_input("주차장 현황", value="마당 주차 4대")
        big_truck = st.selectbox("화물차 진입 여건 *", ["11T 윙바디 접안 원활", "츄레라 / 트레일러 진출입 원활", "5톤 화물차 수월", "1톤 화물차 접안"])

    leg1, leg2, leg3 = st.columns(3)
    with leg1:
        violation_status = st.selectbox("위반건축물 여부", ["위반건축물 아님 (적법)", "위반건축물 등재", "확인 요망"])
        building_structure = st.text_input("주구조 / 지붕", value="일반철골구조 / 판넬지붕")
    with leg2:
        bldg_use = st.text_input("대장상 주용도", value="공장 (제조업소)")
        approval_date = st.text_input("사용승인일자", placeholder="예: 2015.05.20")
    with leg3:
        sewage_type = st.selectbox("오수/정화조 처리방식", ["하수종말처리시설 연결 (직결)", "단독정화조"])
        zoning_choice = st.selectbox("용도지역 및 산단 구분", [
            "일반공업지역 (비산단 자유입주)",
            "일반공업지역 (국가/일반산단 - 입주계약 필수)",
            "전용공업지역 (중화학/공해업종 가능)",
            "준공업지역 (주거혼재 - 소음·악취 민원 주의)"
        ])

    memo = st.text_area("매물 핵심 강점 메모", placeholder="예: 가좌IC 3분 거리. 호이스트 및 동력 완비로 초기 시설 투자비 절감.")

    zoning_guide_map = {
        "일반공업지역 (비산단 자유입주)": "✅ 산단 외 일반공업지역으로 산집법상 입주계약 절차 없이 일반 제조·물류 전 업종 즉시 공장등록 가능",
        "일반공업지역 (국가/일반산단 - 입주계약 필수)": "⚠️ 산업단지 관리구역으로 계약 전 한국산업단지공단 입주적격 업종코드(C코드) 사전 확인 필수",
        "전용공업지역 (중화학/공해업종 가능)": "✅ 대기·폐수 배출시설 및 중량물·화학·표면처리 등 특수 제조업 인허가 최우선 적합 구역",
        "준공업지역 (주거혼재 - 소음·악취 민원 주의)": "⚠️ 인근 주거단지와 인접할 수 있어 야간 소음·분진·도장 악취 유발 업종은 구청 환경과 사전 협의 권장"
    }
    permit_auto_comment = zoning_guide_map[zoning_choice]

    price_str = f"보증금 {dep_man:,}만 원 / 월세 {rent_man:,}만 원" if rent_man > 0 else f"매매가 {dep_man:,}만 원"
    conv_deposit_man = dep_man + (rent_man * 100) if rent_man > 0 else dep_man
    comm_base_won = (dep_man + (rent_man * 100)) * 10000 if rent_man > 0 else dep_man * 10000
    max_comm_won = int(comm_base_won * 0.009)
    vat_won = int(max_comm_won * 0.1)

    st.markdown(f"""
    <div class="calc-box-blue" style="padding:10px 16px;">
        🏭 <b>인허가 판독</b>: {permit_auto_comment}<br>
        💰 <b>금액/복비 브리핑</b>: <b>{price_str}</b> (환산보증금 {conv_deposit_man:,}만 원) | 🧾 <b>법정 중개보수(0.9%)</b>: <b>{max_comm_won:,}원</b> (부가세 포함 {max_comm_won+vat_won:,}원)
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 매물 저장 + 확인·설명서 + 블로그 원고 + 대기손님 역매칭 실행", type="primary", use_container_width=True):
        save_property({
            "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
            "거래구분": deal_type, "소재지(권역)": loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
            "임대인연락처": owner_phone, "가격(보/월)": price_str, "면적": area, "층고": ceiling, "동력": power,
            "호이스트": hoist, "도로/주차": f"{road} / {parking_count}", "대형차량": big_truck, "특징메모": f"[{zoning_choice}] {memo}"
        })
        st.success("✅ 매물이 보유 장부에 안전하게 등록되었습니다!")

        matched_custs = match_customers_for_property(loc, area)
        if matched_custs:
            st.markdown(f"##### 🎯 [자동 역매칭 알림] 이 매물 조건({loc} / {area})을 기다리는 손님이 **{len(matched_custs)}명** 있습니다!")
            for mc in matched_custs:
                st.markdown(f"<div class='calc-box-orange' style='padding:8px 14px;'>👤 <b>{mc.get('상호/고객명','')}</b> ({mc.get('중요도','')}) | 📞 <b>{mc.get('연락처','')}</b> | 희망: {mc.get('희망권역','')} ({mc.get('희망평수','')})</div>", unsafe_allow_html=True)

        out_t1, out_t2 = st.tabs(["📋 중개대상물 확인·설명서 [Ⅱ] 표준 텍스트", "📝 네이버 블로그 공장 전문 브리핑 원고"])
        with out_t1:
            legal_report_text = f"""[중개대상물 확인·설명서 (비주거용 건축물) 필수 기재 사항 요약표]
• 소재지: {secret_address if secret_address else loc} | 전용면적: {area} | 주용도: {bldg_use} | 구조: {building_structure}
• 사용승인일: {approval_date if approval_date else '공적장부 확인'} | 위반건축물 여부: {violation_status}
• 용도지역 및 인허가: {zoning_choice} ({permit_auto_comment})
• 도로/차량진입: {road} ({big_truck}) | 주차: {parking_count} | 인입전력: {power} | 층고: {ceiling} | 호이스트: {hoist} | 오수처리: {sewage_type}
• 거래예정금액: {price_str} (환산보증금 {conv_deposit_man:,}만 원) | 중개보수 산출내역: {max_comm_won:,}원 (상한요율 0.9% 적용, 부가세 별도)
- 우리부동산 공인중개사사무소 대표 김태형 (010-2660-8276) -"""
            st.text_area("확인·설명서 복사용 텍스트", legal_report_text, height=230)
        with out_t2:
            fac_blog = f"""안녕하세요! 인천 서구 공장·창고 전문 파트너, 우리부동산 대표 공인중개사 김태형입니다. 🙋‍♂️

오늘 소개해 드릴 현장은 {loc}에 위치한 알짜배기 {bldg_use} {deal_type} 매물입니다.
{big_truck}이 가능하고 {hoist} 및 동력 {power}가 구축되어 있어 초기 설비 투자 비용을 아낄 수 있는 즉시 조업 가능한 현장입니다!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 1. 매물 핵심 제원 및 거래 조건
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 소재지: {loc} (상세 지번은 보안상 유선 문의 시 안내)
- 거래 조건: {deal_type} / {price_str}
- 실사용 면적: {area}
- 입주 가능일: {vacancy_status} ({expire_date})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 2. 제조 설비 및 인허가 스펙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 용도지역 및 인허가: {zoning_choice}
  ({permit_auto_comment})
- 처마 층고 / 동력: {ceiling} / {power}
- 호이스트: {hoist}
- 도로 및 차량 접안: {road} / {big_truck} ({parking_count})
- 건축물 적법성: {building_structure} / {violation_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 3. 김소장의 현장 실사 총평
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ {memo if memo else '차량 진출입 동선이 쾌적하고 내부 바닥 컨디션이 우수하여 기계 가공, 조립, 물류 창고 등 다양한 업종에 강력 추천합니다.'}

현장 실물 확인 및 상세 도면 브리핑이 필요하신 대표님께서는 언제든 편하게 연락 주십시오!
인천 공장·창고 전문 우리부동산 대표 김태형 ☎ 010-2660-8276
#{loc.replace(' ','')}공장 #인천서구공장 #인천공장임대 #인천공장매매 #호이스트공장 #우리부동산 #공인중개사김소장"""
            st.text_area("블로그 포스팅 복사용", fac_blog, height=340)

# =============================================================
# 2. 🏗️ [주업] 신축공장 맞춤 분양 설계 & [월세 vs 분양 비교 설득 카드]
# =============================================================
elif menu_choice == MENU_DICT["NEW_DEV"]:
    st.title("🏗️ 신축공장 맞춤 분양 설계 & [월세 vs 자가취득] 비교 제안서")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        site_name = st.text_input("프로젝트/단지명 *", value="가좌 첨단제조단지")
        site_addr = st.text_input("사업지 주소 *", value="인천 서구 가좌동 일원")
    with p2:
        custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=150, step=10)
        road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
    with p3:
        f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=90, step=5)
        f2_pyung = st.number_input("2층 사무/제조 (평)", min_value=0, max_value=5000, value=30, step=5)
    with p4:
        cust_company = st.text_input("제안 기업명", value="(주)대한정밀")
        curr_paying_rent = st.number_input("🔥 고객의 현재 월세 (만 원)", min_value=100, max_value=5000, value=450, step=50)

    pr1, pr2, pr3, pr4 = st.columns(4)
    with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원)", value=1200, step=50)
    with pr2: add_unit_price = st.number_input("2층 증축단가 (건축 평당 만 원)", value=380, step=10)
    with pr3: loan_ratio = st.slider("시설자금 대출 비율 (%)", 50, 85, 80, 5)
    with pr4: interest_rate = st.number_input("예상 대출금리 (연 %)", value=4.1, step=0.1)

    actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
    yard_pyung = max(0, custom_land - f1_pyung)
    total_bldg_area = f1_pyung + f2_pyung
    total_dev_price = int((custom_land * base_unit_price + f2_pyung * add_unit_price) * 10000)
    loan_amt = int(total_dev_price * (loan_ratio / 100.0))
    pure_down = total_dev_price - loan_amt
    acq_tax = int(total_dev_price * 0.046)
    monthly_interest = int((loan_amt * (interest_rate / 100.0)) / 12)
    curr_rent_won = curr_paying_rent * 10000
    diff_monthly = curr_rent_won - monthly_interest

    out_c1, out_c2 = st.columns([1.3, 1.2])
    with out_c1:
        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="color: #c05621; margin: 0 0 8px 0;">📊 [{cust_company}] 신축 분양 견적 & [월세 vs 내 공장 취득] 비교표</h4>
            • <b>분양 제원</b>: 대지 <b>{custom_land}평</b> / 건물 연면적 <b>{total_bldg_area}평</b> (1F {f1_pyung}평, 단독마당 {yard_pyung}평)<br>
            • <b>총 분양 공급가</b>: <b style="color:#c53030; font-size:18px;">{total_dev_price:,}원</b> | 대출({loan_ratio}%): <b>{loan_amt:,}원</b><br>
            • <b>필요 자기자본</b>: 분양자부담 {pure_down:,}원 + 취득세 {acq_tax:,}원 = <b>약 {pure_down+acq_tax:,}원</b><br>
            <hr style="margin:8px 0;">
            💡 <b>[핵심 설득 포인트: 남의 건물 월세 vs 내 공장 대출이자 비교]</b><br>
            1. 현재 지출하시는 소멸성 월세: <b>월 {curr_rent_won:,}원</b> (연간 {curr_rent_won*12:,}원 비용 소멸)<br>
            2. 신축 분양 시 은행 월 이자({interest_rate}%): <b style="color:#2b6cb0; font-size:17px;">월 약 {monthly_interest:,}원</b><br>
            🚩 <b>결론</b>: 현재 월세와 비교해 매월 <b>{abs(diff_monthly):,}원 {'절감하면서' if diff_monthly >= 0 else '소폭 추가만으로'} 평생 가치가 오르는 자가 신축 공장을 소유</b>하실 수 있습니다!
        </div>
        """, unsafe_allow_html=True)
    with out_c2:
        bldg_w_svg = int(max(25, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
        yard_w_svg = 100 - bldg_w_svg
        st.markdown(f"""
        <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 14px; margin-top:10px;">
            <div style="background-color: #2d3748; color: white; text-align: center; padding: 8px; font-weight: bold; font-size: 13px; margin-bottom: 10px;">
                ▲ 전면 {road_width}m 광폭 도로 접 (대형 화물차 진출입 최적) ▲
            </div>
            <div style="display: flex; gap: 10px; height: 170px; border: 2px dashed #3182ce; padding: 10px; background-color: #ebf8ff; border-radius: 6px;">
                <div style="flex: {bldg_w_svg}; background-color: #bee3f8; border: 2px solid #1a365d; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <span style="font-weight: bold; font-size: 16px; color: #1a365d;">🏭 신축 공장동</span>
                    <span style="font-size: 13px; color: #2c5282; font-weight: bold;">1F {f1_pyung}평 / 총 {total_bldg_area}평</span>
                </div>
                <div style="flex: {yard_w_svg}; background-color: #edf2f7; border: 2px dashed #718096; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <span style="font-weight: bold; font-size: 14px; color: #4a5568;">🚛 단독 마당</span>
                    <span style="font-size: 13px; color: #718096; font-weight: bold;">약 {yard_pyung}평</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =============================================================
# 3. 📋 [주업] 공장 손님 CRM & [임장 투어 코스 스케줄러]
# =============================================================
elif menu_choice == MENU_DICT["CUSTOMER_CRM"]:
    st.title("📋 공장 손님 CRM 장부 & 현장 투어(임장) 스케줄러")
    df_c = load_customers()
    df_p = load_properties()
    today = datetime.today()

    tab_list, tab_tour, tab_edit = st.tabs(["📊 손님 장부 목록", "🚗 [미팅 당일용] 임장 투어 코스 & 유인물 생성기", "✍️ 손님 신규 등록 및 수정"])

    with tab_list:
        if not df_c.empty:
            search_kw = st.text_input("🔎 손님명 / 연락처 / 희망권역 검색", placeholder="예: 대한정밀, 가좌동...")
            f_df_c = df_c.copy()
            if search_kw.strip():
                kw = search_kw.strip()
                f_df_c = f_df_c[f_df_c["상호/고객명"].astype(str).str.contains(kw, na=False) | f_df_c["희망권역"].astype(str).str.contains(kw, na=False)]

            for orig_idx, c_row in f_df_c.iterrows():
                is_vip = "S급" in str(c_row.get("중요도", "")) or "A급" in str(c_row.get("중요도", ""))
                card_class = "customer-card-pro-vip" if is_vip else "customer-card-pro"
                c_name_val = get_safe_cust_val(c_row, "상호/고객명")
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between;">
                        <div><b>👤 {c_name_val}</b> <span style="color:#d69e2e;">{get_safe_cust_val(c_row, '중요도')}</span> <span class="tag-blue">{get_safe_cust_val(c_row, '거래구분')}</span></div>
                        <div>📞 <b>{get_safe_cust_val(c_row, '연락처')}</b> | 최근연락: {get_safe_cust_val(c_row, '최근연락일')}</div>
                    </div>
                    <div style="margin-top:6px;">
                        <span class="tag-orange">📐 {get_safe_cust_val(c_row, '희망평수')}</span>
                        <span class="tag-orange">📍 {get_safe_cust_val(c_row, '희망권역')}</span>
                        <span class="tag-orange">💰 {get_safe_cust_val(c_row, '예산(보증금/월세/매매가)')}</span>
                        <span class="tag-gray">🏗️ {get_safe_cust_val(c_row, '호이스트')}</span>
                        <span class="tag-gray">⚡ {get_safe_cust_val(c_row, '희망전력kW')}</span>
                    </div>
                    <div style="font-size:13px; color:#4a5568; margin-top:6px;">💡 {get_safe_cust_val(c_row, '상담메모')}</div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("등록된 손님이 없습니다.")

    with tab_tour:
        st.subheader("🚗 미팅 당일 임장 투어 스케줄러 & 손님 배포용 유인물")
        if df_p.empty:
            st.info("보유 매물 장부에 매물을 먼저 등록해 주세요.")
        else:
            tour_cust_name = st.text_input("투어 진행 고객사명", value="(주)대한정밀 대표님")
            p_list = df_p.to_dict("records")
            selected_tour_indices = st.multiselect(
                "오늘 투어할 매물을 순서대로 선택하세요 (2~5개 권장):",
                range(len(p_list)),
                format_func=lambda i: f"[{i+1}번 후보] {p_list[i].get('소재지(권역)','')} ({p_list[i].get('상세주소(지번)','지번미기재')}) | {p_list[i].get('면적','')} | {p_list[i].get('가격(보/월)','')}"
            )
            if selected_tour_indices:
                st.markdown("##### 📍 1. 중개사 전용 동선표 (상세 지번 & 건물주 연락처 포함)")
                for seq_i, p_i in enumerate(selected_tour_indices):
                    tp = p_list[p_i]
                    addr_q = tp.get("상세주소(지번)") if str(tp.get("상세주소(지번)","")).strip() else tp.get("소재지(권역)","")
                    st.markdown(f"**[{seq_i+1}코스]** 📍 **{addr_q}** | 건물주: {tp.get('임대인(건물주)','')} ({tp.get('임대인연락처','')}) | {tp.get('면적','')} | {tp.get('가격(보/월)','')}")

                st.markdown("##### 📄 2. 손님 배포용 투어 브리핑 시트 (상세지번·건물주 번호 자동 블라인드)")
                handout_lines = [f"[{tour_cust_name} 맞춤 공장 현장 투어 브리핑 시트]\n- 일시: {today.strftime('%Y-%m-%d')} | 담당: 우리부동산 대표 김태형 (010-2660-8276)\n" + "="*50]
                for seq_i, p_i in enumerate(selected_tour_indices):
                    tp = p_list[p_i]
                    handout_lines.append(f"""■ [현장 {chr(65+seq_i)}안] {tp.get('소재지(권역)','')} ({tp.get('거래구분','')})
• 금액조건: {tp.get('가격(보/월)','')}
• 실사용면적: {tp.get('면적','')}
• 설비제원: 층고 {tp.get('층고','')} / 동력 {tp.get('동력','')} / {tp.get('호이스트','')}
• 차량/도로: {tp.get('대형차량','')} ({tp.get('도로/주차','')})
• 핵심특징: {tp.get('특징메모','')}
• 현장메모: [                                                  ]
--------------------------------------------------""")
                st.text_area("손님 전달용 시트 (복사 또는 인쇄)", "\n".join(handout_lines), height=320)

    with tab_edit:
        with st.form("cust_quick_form"):
            c1, c2, c3 = st.columns(3)
            with c1: c_name = st.text_input("상호 / 고객명 *"); c_phone = st.text_input("연락처 *")
            with c2: c_loc = st.text_input("희망 권역 *", value="인천 서구 가좌/석남"); c_area = st.text_input("희망 평수 *", value="80~120평")
            with c3: c_star = st.selectbox("VIP 등급", ["⭐⭐⭐ S급(최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반)"]); c_budget = st.text_input("희망 예산", value="보 3,000 / 월 250")
            c_memo = st.text_area("상담 메모")
            if st.form_submit_button("💾 신규 손님 저장", type="primary", use_container_width=True):
                if c_name and c_phone:
                    save_customer({
                        "접수일자": today.strftime("%Y-%m-%d"), "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star, "거래구분": "임대차(월세)", "업종인허가": "일반제조", "상호/고객명": c_name,
                        "연락처": c_phone, "희망권역": c_loc, "희망평수": c_area, "예산(보증금/월세/매매가)": c_budget,
                        "입주시기": "협의", "호이스트": "있으면 좋음", "대형차진입": "11T 수월", "희망전력kW": "50kW",
                        "상담메모": c_memo, "상담히스토리": "", "진행상태": "상담 접수"
                    })
                    st.success("저장 완료!")
                    st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부 & [멀티 비교 장바구니 + 네이버 광고 텍스트]
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부 & 멀티 브리핑 / 네이버 광고 생성기")
    st.caption("매물 여러 개를 동시에 체크하면 [A안 / B안 / C안 비교 추천 브리핑 카톡 문구]와 [네이버 부동산 광고 등록용 타이틀·설명문]을 동시에 생성합니다.")

    df_p = load_properties()
    if not df_p.empty:
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1: sel_pyung = st.selectbox("📐 평수 필터", ["전체 평수 보기", "60평 이하", "60평 ~ 120평", "120평 이상"])
        with f_col2: sel_hoist = st.selectbox("🏗️ 호이스트 유무", ["전체", "호이스트 완비", "호이스트 없음"])
        with f_col3: search_text = st.text_input("🔎 권역/메모 검색")

        filtered_df = df_p.copy()
        if sel_hoist == "호이스트 완비": filtered_df = filtered_df[filtered_df["호이스트"].astype(str).str.contains("완비|톤|T", na=False)]
        elif sel_hoist == "호이스트 없음": filtered_df = filtered_df[filtered_df["호이스트"].astype(str).str.contains("없음", na=False)]
        if search_text.strip(): filtered_df = filtered_df[filtered_df["소재지(권역)"].astype(str).str.contains(search_text.strip(), na=False) | filtered_df["특징메모"].astype(str).str.contains(search_text.strip(), na=False)]

        st.dataframe(filtered_df, use_container_width=True, height=280)

        st.markdown("---")
        b_tab1, b_tab2 = st.tabs(["🛒 카카오톡 멀티 비교 브리핑 장바구니", "📢 네이버 부동산 매물 광고 등록용 텍스트"])
        prop_records = filtered_df.to_dict("records")

        with b_tab1:
            multi_indices = st.multiselect(
                "손님에게 묶어서 비교 브리핑할 매물들을 선택하세요 (복수 선택 가능):",
                range(len(prop_records)),
                default=[0] if len(prop_records) > 0 else [],
                format_func=lambda i: f"[{prop_records[i].get('소재지(권역)','')}] {prop_records[i].get('면적','')} | {prop_records[i].get('가격(보/월)','')} | {prop_records[i].get('호이스트','')}"
            )
            if multi_indices:
                cart_blocks = ["[🏢 우리부동산 대표님 맞춤 공장 비교 추천 브리핑]\n\n대표님 안녕하십니까! 요청하신 조건에 가장 부합하는 핵심 매물들을 비교하실 수 있도록 정리해 드립니다.\n"]
                for idx_order, m_i in enumerate(multi_indices):
                    mp = prop_records[m_i]
                    cart_blocks.append(f"""▶ [{chr(65 + idx_order)}안] {mp.get('소재지(권역)','')} ({mp.get('면적','')})
• 금액조건: {mp.get('거래구분','')} / {mp.get('가격(보/월)','')}
• 설비제원: 층고 {mp.get('층고','')} | 동력 {mp.get('동력','')} | {mp.get('호이스트','')}
• 차량진입: {mp.get('대형차량','')} ({mp.get('도로/주차','')})
• 매물특징: {mp.get('특징메모','')}""")
                cart_blocks.append("\n위 후보군 중 마음에 드시는 현장을 말씀해 주시면 일정 조율하여 내부 실사 안내해 드리겠습니다!\n- 인천 공장 전문 우리부동산 대표 김태형 (032-582-6200 / 010-2660-8276) -")
                st.text_area("📲 멀티 비교 브리핑 카카오톡 복사창", "\n\n".join(cart_blocks), height=280)

        with b_tab2:
            if prop_records:
                ad_idx = st.selectbox("네이버 부동산에 올릴 매물 선택:", range(len(prop_records)), format_func=lambda i: f"{prop_records[i].get('소재지(권역)','')} ({prop_records[i].get('면적','')})")
                ap = prop_records[ad_idx]
                naver_ad_text = f"""[네이버 부동산 매물 특징 광고 타이틀 (40자 이내)]
★{ap.get('소재지(권역)','').split()[-1]} 알짜공장★ {ap.get('면적','')} / {ap.get('호이스트','')} / {ap.get('대형차량','')} / 즉시조업

[네이버 부동산 상세 설명문 복사용]
■ 매물 핵심 제원 안내 ■
- 소재지: {ap.get('소재지(권역)','')}
- 실사용 면적: {ap.get('면적','')}
- 층고 및 동력: {ap.get('층고','')} / 인입전력 {ap.get('동력','')}
- 크레인(호이스트): {ap.get('호이스트','')}
- 진입도로 및 주차: {ap.get('대형차량','')} ({ap.get('도로/주차','')})
- 입주 가능일: {ap.get('입주/공실상태','')} ({ap.get('계약만료일','')})

■ 우리부동산 김태형 대표의 추천 포인트 ■
✔ {ap.get('특징메모','내부 바닥 컨디션 최상이며 대형 화물차 진출입이 매우 원활한 공장입니다.')}
✔ 인천 서구 전지역(가좌·석남·원창·오류·검단) 공장·창고 최다 보유!
✔ 업종별 인허가 검토부터 수전용량 확인까지 원스톱으로 책임 중개합니다.
☎ 대표 직통 문의: 우리부동산 김태형 대표공인중개사 (032-582-6200 / 010-2660-8276)"""
                st.text_area("네이버 부동산 광고 복사용", naver_ad_text, height=280)
    else:
        st.info("등록된 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기 & [건물주 설득 리포트]
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 정밀 시세 & 적정 임대료 추정기")
    v1, v2, v3 = st.columns(3)
    with v1:
        zone_sel = st.selectbox("📍 인천 주요 산업권역 선택", ["서구 가좌동 (일반공업)", "서구 석남동 (일반공업)", "서구 원창동/청라 (북항배후)", "서구 오류동/검단 (검단산단)"])
        land_p = st.number_input("📐 대지면적 (평) *", value=200, step=10)
    with v2:
        bldg_p = st.number_input("🏢 건물 연면적 (평) *", value=140, step=10)
        bldg_age = st.slider("🗓️ 건물 경과 연수", 0, 35, 10, 1)
    with v3:
        infra_spec = st.selectbox("⚙️ 설비", ["호이스트 5T 이상 + 동력 100kW (+5,000만)", "호이스트 2.8T + 동력 50kW (+2,500만)", "기본 설비"])

    base_map = {"서구 가좌동 (일반공업)": 1150, "서구 석남동 (일반공업)": 1080, "서구 원창동/청라 (북항배후)": 1280, "서구 오류동/검단 (검단산단)": 1020}
    est_land = land_p * base_map[zone_sel] * 10000
    est_bldg = int(bldg_p * 380 * max(0.25, 1.0 - bldg_age * 0.025) * 10000)
    infra_add = 50000000 if "5T" in infra_spec else (25000000 if "2.8T" in infra_spec else 0)
    tot_sale = est_land + est_bldg + infra_add
    est_rent = int(bldg_p * 3.5) * 10000

    st.markdown(f"""
    <div class="calc-box-orange">
        • <b>추정 적정 매매가</b>: <b style="color:#c53030; font-size:20px;">약 {tot_sale:,}원</b> (대지 평당 환산 약 {int((tot_sale/land_p)/10000):,}만 원)<br>
        &nbsp;&nbsp;- 토지 평가액: {est_land:,}원 + 건물 잔존가치(경과 {bldg_age}년): {est_bldg:,}원 + 설비 가치: {infra_add:,}원<br>
        • <b>권장 적정 임대료</b>: <b>보증금 {est_rent*10:,}원 / 월세 {est_rent:,}원</b> | 🏦 <b>매수자 대출 한도(75%)</b>: 약 <b>{int(tot_sale*0.75):,}원</b>
    </div>
    """, unsafe_allow_html=True)

    owner_report = f"""[🏢 우리부동산 공장 자산가치 및 적정 시세 분석 브리핑]

대표님 안녕하십니까, 인천 공장 전문 우리부동산 김태형 대표공인중개사입니다.
문의하신 {zone_sel.split()[1]} 소재 공장(대지 {land_p}평 / 건물 {bldg_p}평)의 인근 실거래 데이터 및 설비 감가상각 기반 적정 시세 분석 결과입니다.

1. 매매 적정 가치 산출
• 토지 가치: 약 {est_land:,}원 ({zone_sel.split()[1]} 실거래 평균 반영)
• 건물 및 설비 가치: 약 {est_bldg + infra_add:,}원 (준공 후 {bldg_age}년 감가 및 설비 반영)
▶ 추천 급매/적정 매도가 밴드: 약 {tot_sale:,}원 선 (대지 평당 약 {int((tot_sale/land_p)/10000):,}만 원)

2. 임대차(월세) 진행 시 적정 조건
• 권장 임대 조건: 보증금 {est_rent*10:,}원 / 월세 {est_rent:,}원 (연 환산 수익률 약 6%대)

현재 당사에 해당 평수대를 찾는 진성 제조업체 대표님들이 대기 중입니다. 위 적정 시세 범주로 조건을 맞춰주시면 1~2개월 내 신속한 계약 체결이 가능하도록 최우선 브리핑하겠습니다!
- 우리부동산 대표 김태형 올림 (032-582-6200 / 010-2660-8276) -"""
    st.text_area("📲 건물주 전송용 적정 시세 설득 카톡 리포트", owner_report, height=260)

# =============================================================
# 6. 🍜 [부업] 맛집 탐방 전용 블로그 (단독 분리 & SEO 4종 문체)
# =============================================================
elif menu_choice == MENU_DICT["BLOG_FOOD"]:
    st.title("🍜 맛집 탐방 전문 블로그 엔진 (SEO 제목 5선 + 영수증 리뷰 + 숏폼)")
    st.caption("맛집 포스팅에 최적화된 단독 탭입니다! [4가지 문체 로테이션], [스마트블록 제목 5선], [Q&A 요약박스], [400자 영수증 리뷰]를 한 번에 생성합니다.")

    c1, c2, c3 = st.columns(3)
    with c1:
        m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
        m_loc = st.text_input("지역명 (핵심키워드) *", placeholder="예: 인천 청라 / 부천 역곡")
        m_tone = st.selectbox("🎨 글 문체 선택 (유사문서 방지)", ["1. 미식가 꼼꼼 분석형", "2. 주말 데이트 감성형", "3. 가성비·회식 추천형", "4. 동네 주민 단골 찐후기형"])
    with c2:
        m_menu = st.text_input("주문 메뉴 및 가격 *", placeholder="예: 연탄 생삼겹살 2인분(32,000원)")
        m_addr = st.text_input("상세 위치 및 주차 팩트 *", placeholder="예: 청라커낼로 123 (지하주차 2시간 무료)")
        m_wait = st.text_input("영업시간 및 웨이팅 팁", placeholder="예: 주말 저녁 20분 대기, 캐치테이블 가능")
    with c3:
        m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 은은한 연탄 불향과 육즙 조화가 끝내주는 삼겹살 맛집")
        m_point = st.text_input("킬링 포인트 (숏폼/리뷰용)", placeholder="예: 구운 묵은지와 파채를 곁들인 첫 점의 육즙")

    m_taste = st.text_area("상세 맛 표현 및 반찬/분위기 메모", placeholder="예: 고기 두께가 두툼하고 직원분이 그릴링을 도와주셔서 편함. 된장찌개가 칼칼해서 공깃밥 필수.")

    if st.button("🚀 맛집 상위노출 패키지 (제목5선 + 본문 + Q&A + 400자 영수증 + 숏폼) 생성", type="primary", use_container_width=True):
        if not m_name or not m_eval:
            st.error("상호명과 한 줄 총평은 필수입니다.")
        else:
            intros = {
                "1. 미식가 꼼꼼 분석형": f"제대로 된 식재료와 조리 밸런스를 갖춘 식당을 만나는 건 언제나 즐거운 일입니다. 오늘은 {m_loc} 일대에서 입소문이 자자한 '{m_name}'에 직접 다녀와 고기 원육 상태부터 밑반찬 구성까지 꼼꼼하게 경험해 본 솔직 후기를 정리해 드립니다.",
                "2. 주말 데이트 감성형": f"기분 좋은 주말, 소중한 사람과 함께 맛있는 한 끼를 즐기기 위해 {m_loc} 맛집 나들이를 다녀왔습니다. 분위기와 맛 두 마리 토끼를 모두 잡은 '{m_name}' 방문 기록을 공유해 볼게요.",
                "3. 가성비·회식 추천형": f"단체 모임이나 외식 장소를 고를 때 가장 중요한 건 단연 호불호 없는 맛과 쾌적한 주차·좌석 동선입니다. {m_loc}에서 가격 대비 훌륭한 퀄리티로 만족도를 높여준 '{m_name}' 후기입니다.",
                "4. 동네 주민 단골 찐후기형": f"평소 {m_loc} 근처를 지날 때마다 늘 손님들로 북적이던 곳이라 궁금했던 '{m_name}'에 드디어 다녀왔습니다. 왜 동네 주민들이 단골로 찾는지 단번에 납득이 갔던 식사였습니다."
            }

            seo_titles = f"""[🎯 네이버 스마트블록·뷰탭 상위노출 추천 제목 5선]
1. {m_loc} 맛집 {m_name} 솔직후기 주차 웨이팅 가격 총정리
2. {m_loc} 모임 회식장소 추천 {m_name} {m_menu.split('(')[0]} 내돈내산 찐후기
3. 실패 없는 {m_loc} 데이트 맛집 {m_name} 대표메뉴 및 방문 팁
4. [{m_loc}] {m_eval} {m_name} 재방문 솔직리뷰
5. {m_loc} 현지인 단골 맛집 {m_name} 주차장 및 웨이팅 정보"""

            post_body = f"""{seo_titles}

==================================================
[본문 시작]

안녕하세요! 인천·부천 지역의 숨은 미식 명소를 기록하는 김소장입니다. 🙋‍♂️
{intros[m_tone]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. {m_name} 방문 전 필수 정보 요약
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 상호명: {m_name}
• 위치 및 주차: {m_addr}
• 주문 내역: {m_menu}
• 영업 및 대기 팁: {m_wait}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🍽️ 2. 메뉴 디테일 및 솔직 맛 평가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
오늘 주문한 메인 구성은 {m_menu}입니다.
첫인상부터 재료의 신선함이 한눈에 느껴졌는데요. {m_eval}!

특히 가장 인상 깊었던 킬링 포인트는 '{m_point}'이었습니다.
{m_taste}
마지막 한 입까지 물리지 않고 깔끔하게 즐길 수 있어 함께 간 일행 모두 만족도가 상당히 높았습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❓ 3. 방문 전 자주 묻는 질문 (Q&A 핵심 요약)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q1. 주차 공간은 여유로운가요?
A1. {m_addr} 기준으로 이용 가능하여 자차 방문 시에도 편리합니다.

Q2. 피크타임 웨이팅은 어느 정도인가요?
A2. {m_wait if m_wait else '식사 피크 시간대에는 대기가 발생할 수 있으니 조금 일찍 방문하시는 것을 권장합니다.'}

Q3. 어떤 메뉴 조합을 가장 추천하나요?
A3. 대표 메뉴인 {m_menu} 조합을 가장 추천해 드립니다.

#{m_loc.replace(' ','')}맛집 #{m_name.replace(' ','')} #내돈내산 #솔직후기 #김소장"""

            col_b1, col_b2 = st.columns([1.3, 1.0])
            with col_b1:
                st.text_area("📝 네이버 블로그 본문 (제목 5선 + 본문 + Q&A 포함)", post_body, height=450)
            with col_b2:
                review_text = f"""⭐⭐⭐⭐⭐
{m_loc} 찐맛집 인정합니다! {m_menu} 주문해서 먹어봤는데, {m_point if m_point else m_eval}. {m_taste} 재료도 신선하고 직원분들도 친절하셔서 기분 좋게 식사했습니다. 주차({m_addr})도 편해서 다음 모임 때 무조건 재방문할 생각입니다! 👍"""
                st.caption(f"🧾 네이버 영수증 리뷰 (현재 {len(review_text)}자 / 400자 이내)")
                st.text_area("영수증 리뷰 복사", review_text, height=180)

                short_script = f"""[0~3초 훅] "{m_loc}에서 여기 안 가봤으면 간첩입니다!" (조리 클로즈업 컷)
[4~20초 본론] "바로 {m_name}인데요. {m_menu} 비주얼 좀 보세요. {m_point}!"
[21~30초 클로징] "주차는 {m_addr}! 이번 주말 외식 코스로 저장해 두세요!" """
                st.text_area("🎬 30초 릴스·클립 촬영 대본", short_script, height=180)

# =============================================================
# 7. 🧢 [부업] 일상·핫플·운동 블로그 (단독 분리 신설!)
# =============================================================
elif menu_choice == MENU_DICT["BLOG_LIFE"]:
    st.title("🧢 일상·핫플·운동·취미 블로그 엔진 (주제별 맞춤형 SEO)")
    st.caption("맛집과 완전히 분리된 일상/라이프스타일 전용 탭입니다! 핫플/카페/쇼핑 후기, 농구/러닝 운동 기록, 해루질/나들이 등 주제에 맞춰 진정성 있는 일상 포스팅과 릴스 대본을 생성합니다.")

    life_cat = st.radio(
        "📌 일상 포스팅 카테고리 선택",
        ["🛍️ 핫플·팝업·쇼핑·카페 나들이", "🏀 농구·러닝·웨이트 운동 & 장비 리뷰", "🌊 해루질·캠핑·주말 여행·반려견 일상"],
        horizontal=True
    )

    l1, l2, l3 = st.columns(3)
    with l1:
        d_title_kw = st.text_input("핵심 키워드 (장소/장비/주제) *", placeholder="예: 성수동 팝업스토어 / 코비6 프로트로 농구화 / 태안 해루질")
        d_loc = st.text_input("장소 또는 브랜드/코스 *", placeholder="예: 도산공원 스투시 / 부천 체육관 / 태안 안면도")
    with l2:
        d_item = st.text_input("핵심 대상 (구매품목/운동내용/수확물) *", placeholder="예: 신상 후드티 / 포인트가드 2시간 풀타임 & 농구화 접지력 / 꽃게·소라")
        d_wait_cost = st.text_input("소요 시간 / 비용 / 준비물 팁", placeholder="예: 주말 웨이팅 30분 / 정사이즈 반업 추천 / 물때표 간조 시간 체크 필수")
    with l3:
        d_eval = st.text_input("오늘의 한 줄 총평 *", placeholder="예: 최상의 코트 접지력과 쿠셔닝, 가드 포지션 인생 농구화 등극!")
        d_point = st.text_input("가장 좋았던 하이라이트 순간", placeholder="예: 급정지 스텝백 할 때 밀림 없는 쫀쫀한 접지력")

    d_note = st.text_area("상세 경험담 및 꿀팁 메모", placeholder="예: 직접 겪어본 사이즈 팁이나 현장 분위기, 주차 정보, 다음번 방문/사용 시 참고할 점을 자유롭게 적어주세요.")

    if st.button("🚀 일상·취미 맞춤형 블로그 본문 + 릴스 대본 생성", type="primary", use_container_width=True):
        if not d_title_kw or not d_eval:
            st.error("핵심 키워드와 한 줄 총평은 필수입니다.")
        else:
            life_titles = f"""[🎯 네이버 검색 유입 추천 제목 4선]
1. {d_title_kw} 솔직후기 {d_item} 직접 경험해본 찐리뷰 및 꿀팁
2. [{d_loc}] {d_title_kw} 현장 분위기 및 {d_wait_cost.split('/')[0]} 총정리
3. {d_eval}! {d_title_kw} 상세 기록
4. 실패 없는 {d_title_kw} 준비부터 실전 팁까지 한눈에 보기"""

            life_body = f"""{life_titles}

==================================================
[본문 시작]

안녕하세요! 바쁜 본업 속에서도 건강한 일상과 취미를 기록하는 김소장입니다. 🙋‍♂️
오늘은 많은 분들이 궁금해하시는 '{d_title_kw}' 관련해서 직접 다녀오고 경험해 본 생생한 후기와 실전 팁을 정리해 보려고 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 오늘의 핵심 요약 ({d_title_kw})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 장소 / 대상: {d_loc}
• 주요 내용 / 아이템: {d_item}
• 체크 포인트: {d_wait_cost}
• 한 줄 총평: {d_eval}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 2. 생생 경험담 및 디테일 후기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이번에 '{d_title_kw}'을(를) 직접 경험하면서 가장 만족스러웠던 부분은 바로 '{d_point}'이었습니다.

{d_note}

직접 부딪혀보고 경험해 보니 왜 많은 분들이 찾고 추천하는지 확실히 알 수 있었던 알찬 시간이었습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 3. 김소장의 실전 꿀팁 정리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 사전 체크사항: {d_wait_cost if d_wait_cost else '방문 및 시작 전 일정과 현장 컨디션을 미리 체크하시면 훨씬 수월합니다.'}
✅ 추천 포인트: {d_eval}

오늘 정리해 드린 {d_title_kw} 후기가 도움이 되셨기를 바랍니다! 이웃님들도 활기차고 즐거운 한 주 보내시길 응원합니다. 😊

#{d_title_kw.replace(' ','')} #{d_loc.replace(' ','')} #일상기록 #솔직리뷰 #내돈내산 #취미생활 #김소장"""

            lc1, lc2 = st.columns([1.3, 1.0])
            with lc1:
                st.text_area("📝 일상·취미 네이버 블로그 완성본", life_body, height=420)
            with lc2:
                life_short = f"""[0~3초 오프닝 훅]
"{d_title_kw} 고민 중이시라면 이 영상 무조건 끝까지 보세요!"

[4~20초 하이라이트]
"직접 {d_loc}에서 {d_item} 경험해 봤는데요. 특히 {d_point} 부분이 진짜 대박이었습니다. {d_eval}!"

[21~30초 꿀팁 클로징]
"참고로 {d_wait_cost} 이 점만 미리 챙기시면 실패 없습니다! 저장해 두고 참고하세요!" """
                st.text_area("🎬 30초 인스타 릴스 / 네이버 클립 대본", life_short, height=250)

# =============================================================
# 8. 🏢 [부업] 실시간 청약·줍줍 & LH 공공임대 (오류 0% 팩트 잠금장치 탑재)
# =============================================================
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 실시간 청약·줍줍 & LH 공공임대 (오류 0% 팩트 검증 시스템)")
    st.caption("공공데이터포털 API의 100% 공식 일정/분양가 데이터에 더해, [자격·전매·실거주 팩트 체크리스트 잠금장치]와 [공인중개사 면책 조항]으로 오류 가능성을 원천 차단합니다.")

    DEFAULT_API_KEY = "d1a0585bef6ed7240317271c754ad4be4f9ba74cdf342e6b714bbb85d3196f69"

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
        for label_type, url in endpoints:
            params = {"serviceKey": api_key, "page": 1, "perPage": 80, "returnType": "JSON", "cond[RCRIT_PBLANC_DE::GTE]": start_date_cond}
            if sido_filter != "전체": params["cond[SUBSCRPT_AREA_CODE_NM::EQ]"] = sido_filter
            try:
                res = requests.get(url, params=params, timeout=8)
                if res.status_code == 200:
                    for row in res.json().get("data", []):
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
                            "주택관리번호": str(row.get("HOUSE_MANAGE_NO") or ""), "공고번호": str(row.get("PBLANC_NO") or ""),
                            "진행상태": status_badge, "구분": label_type, "지역": str(row.get("SUBSCRPT_AREA_CODE_NM") or "전국"),
                            "단지명": str(row.get("HOUSE_NM") or ""), "공급위치": str(row.get("HSSPLY_ADRES") or ""),
                            "공급세대수": f"{row.get('TOT_SUPLY_HSHLDCO', 0)}세대", "모집공고일": str(row.get("RCRIT_PBLANC_DE") or ""),
                            "청약접수기간": f"{r_bgnde} ~ {r_endde}" if r_bgnde else "공고문 확인",
                            "특별공급일": f"{row.get('SPSPLY_RCEPT_BGNDE', '')} ~ {row.get('SPSPLY_RCEPT_ENDDE', '')}".strip(" ~") or "해당없음",
                            "1순위접수일": f"{row.get('GNRL_RNK1_CRSPAREA_RCPTDE', '')}".strip() or r_bgnde,
                            "당첨자발표일": str(row.get("PRZWNER_PRESNATN_DE") or ""),
                            "계약기간": f"{row.get('CNTRCT_CNCLS_BGNDE', '')} ~ {row.get('CNTRCT_CNCLS_ENDDE', '')}".strip(" ~"),
                            "입주예정월": str(row.get("MVN_PREARNGE_YM") or "공고문 참조"),
                            "시공사": str(row.get("BSNS_MBY_NM") or row.get("CNSTRCT_ENTRPS_NM") or "시공사 확인"),
                            "문의처": str(row.get("MDHS_TELNO") or ""), "공고URL": str(row.get("PBLANC_URL") or "https://www.applyhome.co.kr")
                        })
            except Exception: continue
        return results

    @st.cache_data(ttl=1800)
    def fetch_apt_price_detail(api_key, house_manage_no, pblanc_no, is_remndr=False):
        if not house_manage_no or not pblanc_no: return []
        url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getRemndrLttotPblancMdl" if is_remndr else "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl"
        params = {"serviceKey": api_key, "page": 1, "perPage": 30, "returnType": "JSON", "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no, "cond[PBLANC_NO::EQ]": pblanc_no}
        models = []
        try:
            res = requests.get(url, params=params, timeout=6)
            if res.status_code == 200:
                for m in res.json().get("data", []):
                    h_ty = str(m.get("HOUSE_TY") or m.get("MODEL_NO") or "")
                    top_amt = str(m.get("LTTOT_TOP_AMOUNT") or m.get("SUPLY_AMOUNT") or "")
                    sup_cnt = str(m.get("SUPLY_HSHLDCO") or "")
                    if top_amt and top_amt != "0": models.append(f"• {h_ty}타입 ({sup_cnt}세대): 최고가 {top_amt}만 원")
        except Exception: pass
        return models

    f_col1, f_col2, f_col3, f_col4 = st.columns([1.3, 1.6, 1.8, 1.0])
    with f_col1: sel_sido = st.selectbox("📍 지역 선택", ["전체", "서울", "인천", "경기", "부산", "대구", "대전", "광주", "세종"])
    with f_col2: sel_status_filter = st.selectbox("🚦 상태 필터", ["접수중/예정만 보기 (마감 제외)", "전체 보기", "🔥 무순위/줍줍만 보기"])
    with f_col3: kw_search = st.text_input("🔎 단지명 검색")
    with f_col4:
        st.write("")
        if st.button("🔄 실시간 새로고침", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    live_list = fetch_realtime_applyhome(DEFAULT_API_KEY, sel_sido)
    if not live_list:
        st.warning("⚠️ 현재 API 데이터를 불러오는 중이거나 공공데이터포털 키 동기화 대기 중입니다.")
    else:
        df_live = pd.DataFrame(live_list)
        if sel_status_filter == "접수중/예정만 보기 (마감 제외)": df_live = df_live[~df_live["진행상태"].str.contains("마감", na=False)]
        elif sel_status_filter == "🔥 무순위/줍줍만 보기": df_live = df_live[df_live["구분"].str.contains("줍줍", na=False)]
        if kw_search.strip(): df_live = df_live[df_live["단지명"].str.contains(kw_search.strip(), na=False)]

        st.dataframe(df_live[["진행상태", "구분", "지역", "단지명", "공급세대수", "청약접수기간", "당첨자발표일", "시공사"]], use_container_width=True, height=230)

        if not df_live.empty:
            records = df_live.to_dict("records")
            sel_idx = st.selectbox("📌 포스팅할 단지 선택:", range(len(records)), format_func=lambda i: f"[{records[i]['진행상태']}] [{records[i]['지역']}] {records[i]['단지명']} ({records[i]['공급세대수']})")
            target = records[sel_idx]
            is_jupjup = "줍줍" in target["구분"]
            model_prices = fetch_apt_price_detail(DEFAULT_API_KEY, target.get("주택관리번호", ""), target.get("공고번호", ""), is_remndr=is_jupjup)
            auto_price_text = "\n".join(model_prices) if model_prices else "• 상세 타입별 공급금액은 아래 공식 입주자모집공고문 표 참조"

            st.link_button(f"📄 1단계: [{target['단지명']}] 공식 모집공고문 원문 열기 (규제사항 눈으로 확인)", target["공고URL"], type="primary", use_container_width=True)

            st.markdown("##### 🔒 2단계: 오류 0% 팩트 체크 잠금장치 (공고문 원문 확인 후 선택하세요)")
            lk1, lk2, lk3, lk4 = st.columns(4)
            with lk1: fact_qual = st.selectbox("① 신청 자격 요건", ["공고문 원문 기준 확인 필수", "해당지역 거주 무주택세대주만", "수도권 거주 무주택세대구성원", "전국 만 19세 이상 (유주택 가능/통장무관)"])
            with lk2: fact_reside = st.selectbox("② 실거주 의무 기간", ["실거주 의무 없음", "실거주 의무 있음 (입주 후 2~5년)", "공고문 원문 확인"])
            with lk3: fact_resale = st.selectbox("③ 전매제한 기간", ["당첨자 발표일로부터 1년", "당첨자 발표일로부터 3년", "소유권이전등기 시까지", "전매제한 없음 (즉시 전매 가능)"])
            with lk4: fact_loan = st.text_input("④ 계약금 비율 & 실거래 비교", placeholder="예: 계약금 10%, 인근시세 대비 1억 저렴")

            clean_tag = re.sub(r'[^가-힣a-zA-Z0-9]', '', target["단지명"].split()[0]) if target["단지명"] else "청약정보"
            auto_blog_text = f"""안녕하세요! 정확한 부동산 공적장부와 모집공고문 팩트만을 전달하는 공인중개사 김태형입니다. 🙋‍♂️

한국부동산원 청약홈에 공식 등재된 '{target['단지명']}'의 청약 일정과 공급가액, 핵심 자격 요건을 정리해 드립니다.
이번 공고는 {target['공급위치']} 일원에 총 {target['공급세대수']} 규모로 공급되는 {target['구분'].split()[-1]} 물량입니다.

📄 한국부동산원 공식 입주자모집공고문 원문 보기:
{target['공고URL']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 공식 청약 일정 팩트체크 (한국부동산원 전산 기준)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 입주자 모집공고일: {target['모집공고일']}
- 전체 청약 접수기간: {target['청약접수기간']}
- 특별공급 접수일: {target['특별공급일']}
- 1순위/일반 접수일: {target['1순위접수일']}
- 당첨자 발표일: {target['당첨자발표일']}
- 정당 계약기간: {target['계약기간']}
- 접수 방법: 한국부동산원 청약Home 인터넷 접수 (09:00 ~ 17:30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {target['단지명']}
- 공급 위치: {target['공급위치']} ({target['지역']})
- 공급 규모: 총 {target['공급세대수']} (입주예정월: {target['입주예정월']})
- 시공사 / 시행사: {target['시공사']}
- 견본주택 문의처: {target['문의처'] if target['문의처'] else '공고문 내 문의처 참조'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 주택형별 확정 최고 공급금액 (공식 API 데이터)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{auto_price_text}
- 자금 및 시세 체크포인트: {fact_loan if fact_loan.strip() else '계약금(통상 10~20%) 자납 조건 및 인근 실거래가 대조 필수'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 핵심 규제 및 신청 자격 체크리스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 자격 기준: {fact_qual}
- 전매제한 기간: {fact_resale}
- 실거주 의무: {fact_reside}

[📌 공인중개사 팩트체크 안내 및 면책사항]
본 포스팅은 한국부동산원 청약홈 공식 Open API 데이터를 기반으로 작성되었으나, 신청자의 개별 가점·세대주 요건·특공 소득 기준에 따라 적격 여부가 달라질 수 있습니다. 청약 신청 전 반드시 상단에 링크된 공식 입주자모집공고문 원문을 직접 재확인하시기 바랍니다.

우리부동산 공인중개사사무소 대표 김태형 ☎ 032-582-6200 / 010-2660-8276
#{clean_tag} #{target['지역']}청약 #청약정보 #아파트청약 #청약홈 #공인중개사김소장 #우리부동산"""
            st.text_area("📋 무결점 네이버 블로그 원고 (전체 복사)", auto_blog_text, height=450)

# =============================================================
# 9. ⚖️ [부업] 법원경매 목록 허브 (인천 공장 목록 & 수도권 아파트 목록)
# =============================================================
elif menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 (인천 공장 경매 목록 & 수도권 아파트 경매 목록)")
    st.caption("목록에서 원하는 경매 물건을 클릭하면 [5단계 배당표], [턴키 자금조달표], [경매 전문 블로그 원고]가 즉시 생성되며, 실제 매각기일/최저가 1초 보정 기능으로 오류를 완벽 방지합니다.")

    factory_list, apt_list = get_auction_data()

    auction_tab1, auction_tab2 = st.tabs([
        "🏭 [인천/산단 공장 경매 목록] 기계기구 분리 & 턴키 수지분석·블로그",
        "🏢 [수도권 아파트 경매 목록] 5단계 배당표 & 실투자금 분석·블로그"
    ])

    with auction_tab1:
        st.subheader("🏭 인천·수도권 주요 공장 및 창고 법원경매 목록")
        st.dataframe(pd.DataFrame([{
            "사건번호": f["사건번호"], "법원": f["법원"], "소재지": f["소재지"],
            "용도": f["세부용도"], "대지/건물": f"{f['대지면적']} / {f['건물면적']}", "감정가": f["총감정가"],
            "최저가": f["최저가"], "보증금(10%)": f["입찰보증금"], "매각기일": f["매각기일"]
        } for f in factory_list]), use_container_width=True, height=190)

        chosen_fac_idx = st.selectbox(
            "📌 분석 및 블로그 글을 생성할 공장 경매 사건을 선택하세요:",
            range(len(factory_list)),
            format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']} (감정가: {factory_list[i]['총감정가']} ➡️ 최저가: {factory_list[i]['최저가']})"
        )
        cur_fac = factory_list[chosen_fac_idx]
        case_fac_key = cur_fac['사건번호'].replace("타경", "_")

        with st.expander("🔒 [오류 0% 안전장치] 대법원 당일 공고 기준 매각기일·최저가 1초 보정", expanded=False):
            e_fc1, e_fc2, e_fc3 = st.columns(3)
            with e_fc1: edit_f_date = st.text_input("매각기일 확인", value=cur_fac["매각기일"], key=f"efd_{case_fac_key}")
            with e_fc2: edit_f_min = st.number_input("최저매각가격(원)", value=int(cur_fac["최저가원"]), step=10000000, key=f"efm_{case_fac_key}")
            with e_fc3: edit_f_malso = st.text_input("말소기준권리 확인", value=cur_fac["권리분석"]["말소기준"], key=f"efms_{case_fac_key}")

        pure_real_estate = cur_fac['토지감정가원'] + cur_fac['건물감정가원']

        fc1, fc2 = st.columns([1.2, 1.3])
        with fc1:
            st.markdown("##### ⚖️ 공장 권리분석 & 기계기구 분리평가")
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #cbd5e0; border-radius:6px; padding:12px; font-size:13px; line-height:1.8;">
                • <b>말소기준권리</b>: {edit_f_malso}<br>
                • <b>임차인/유치권</b>: {cur_fac['권리분석']['임차인']} / {cur_fac['권리분석']['유치권']}<br>
                • <b>순수 부동산(토지+건물) 감정가</b>: <b style="color:#2b6cb0;">{pure_real_estate:,}원</b><br>
                • <b>기계기구 분리 감정액</b>: <b>{cur_fac['기계기구감정가원']:,}원</b> ({cur_fac['기계감정내역']})<br>
                • <b>산단 입주자격</b>: {cur_fac['산단입주자격']}
            </div>
            """, unsafe_allow_html=True)
            st.link_button("🌐 대법원 법원경매정보 원문 확인", cur_fac["사건URL"], use_container_width=True)

        with fc2:
            st.markdown("##### 💰 공장 턴키 정상가동 실시간 자금조달표")
            f_bid = st.number_input("예상 낙찰가 (원)", value=int(edit_f_min), step=10000000, key=f"fb_{case_fac_key}")
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
오늘 소개해 드리는 물건은 {cur_fac['법원']} 사건번호 [{cur_fac['사건번호']}] 공장입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 입찰 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_fac['사건번호']} ({cur_fac['법원']})
- 소재지: {cur_fac['소재지']}
- 대지면적 / 건물면적: 대지 {cur_fac['대지면적']} / 건물 {cur_fac['건물면적']} (1층 바닥 {cur_fac['바닥평수']}평)
- 매각기일: {edit_f_date} ({cur_fac['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정평가 분석 (기계기구 분리평가 필수!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 감정가액: {cur_fac['총감정가']}
- 현재 최저가: {edit_f_min:,}원 (입찰보증금 10%: {int(edit_f_min*0.1):,}원)
- 순수 부동산(토지+건물) 가치: 약 {pure_real_estate:,}원
- 기계기구 감정액: 약 {cur_fac['기계기구감정가원']:,}원 ({cur_fac['기계감정내역']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 3. 제조 설비 스펙 및 권리분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 현장 제원: {cur_fac['제원및코멘트']}
- 권리분석: 말소기준권리({edit_f_malso}) 이후 전액 소멸, {cur_fac['권리분석']['유치권']}
- 산단 입주 적격성: {cur_fac['산단입주자격']}

[📌 공인중개사 법률 면책 공지]
본 포스팅은 법원 매각물건명세서를 바탕으로 작성된 참고 자료입니다. 입찰 전 반드시 당일 기준 공고문 열람 및 현장 임장을 거치시기 바라며, 공장 경락잔금대출(최대 75~80%) 및 입찰 상담은 편하게 연락 주십시오!

인천 공장·창고 중개 및 법원경매 전문
우리부동산 공인중개사사무소 대표 김태형 ☎ 032-582-6200 / 010-2660-8276
#{clean_fac_loc.replace(' ','')}공장 #인천공장경매 #창고경매 #법원경매 #호이스트공장 #우리부동산 #공인중개사김소장"""
        st.text_area("📋 공장 경매 네이버 블로그 완성본", fac_blog_post, height=340)

    with auction_tab2:
        st.subheader("🏢 수도권(서울·인천·경기) 주요 아파트 법원경매 목록")
        f_c1, f_c2 = st.columns([2.0, 2.5])
        with f_c1: major_region = st.selectbox("📍 광역 시·도 필터", ["전체 모아보기 (수도권 전지역)", "서울특별시", "인천광역시", "경기도"], index=0)
        with f_c2: kw_val = st.text_input("🔎 단지명 / 사건번호 검색", placeholder="예: 아크로, 청라, 당산, 푸르지오...")

        filtered_apt = [a for a in apt_list if (major_region == "전체 모아보기 (수도권 전지역)" or a["시도"] == major_region) and (not kw_val.strip() or kw_val.strip() in a["소재지"] or kw_val.strip() in a["사건번호"])]

        if filtered_apt:
            st.dataframe(pd.DataFrame([{
                "사건번호": a["사건번호"], "법원": a["법원"], "시도": a["시도"], "소재지": a["소재지"],
                "평형": a["평형타입"], "감정가": a["감정가"], "최저가": a["최저가"], "추천입찰가": a["추천입찰가밴드"], "매각기일": a["매각기일"]
            } for a in filtered_apt]), use_container_width=True, height=190)

            chosen_apt_idx = st.selectbox("📌 분석 및 블로그 포스팅을 생성할 아파트 사건 선택:", range(len(filtered_apt)), format_func=lambda i: f"[{filtered_apt[i]['사건번호']}] {filtered_apt[i]['소재지']} (최저가: {filtered_apt[i]['최저가']})")
            cur_apt = filtered_apt[chosen_apt_idx]
            qa_apt = cur_apt["권리분석"]
            case_key = cur_apt['사건번호'].replace("타경", "_")

            with st.expander("🔒 [오류 0% 안전장치] 대법원 당일 공고 기준 매각기일·최저가 1초 보정", expanded=False):
                e_ac1, e_ac2 = st.columns(2)
                with e_ac1: edit_a_date = st.text_input("아파트 매각기일 확인", value=cur_apt["매각기일"], key=f"ead_{case_key}")
                with e_ac2: edit_a_min = st.number_input("아파트 최저가(원)", value=int(cur_apt["최저가원"]), step=10000000, key=f"eam_{case_key}")

            col_l, col_r = st.columns([1.2, 1.3])
            with col_l:
                st.markdown("##### 📊 실시간 5단계 배당표 시뮬레이터")
                sim_bid = st.number_input("가상 낙찰가 입력 (원)", value=int(edit_a_min), step=10000000, key=f"sim_b_{case_key}")
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
오늘 분석할 물건은 {cur_apt['법원']}에서 진행되는 사건번호 [{cur_apt['사건번호']}] 매각 사건입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 매각 일정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_apt['사건번호']} ({cur_apt['법원']})
- 소재지: {cur_apt['소재지']}
- 주택유형 및 면적: {cur_apt['주택유형']} {cur_apt['평형타입']} ({cur_apt['층수']})
- 매각기일: {edit_a_date} ({cur_apt['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정가 vs 실거래 시세 안전마진 안전 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 최초 감정가: {cur_apt['감정가']}
- 현재 최저매각가격: {edit_a_min:,}원 (입찰보증금 10%: {int(edit_a_min*0.1):,}원)
- 최근 실거래 시세: {cur_apt['최근실거래가']}
- 추천 입찰가 밴드: {cur_apt['추천입찰가밴드']} (예상 시세차익: {cur_apt['예상시세차익']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ 3. 김소장의 정밀 권리분석 체크포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 말소기준권리: {qa_apt['말소기준권리']} (이후 모든 권리 소멸)
✅ 임차인 대항력 분석: {qa_apt['임차인분석']} (낙찰자 인수 보증금 {qa_apt['인수보증금']}원)
✅ 규제 특례 사항: {qa_apt['토허제특례']}
✅ 명도 난이도: {qa_apt['명도난이도']}

[📌 공인중개사 법률 면책 공지]
본 포스팅은 법원 매각물건명세서를 바탕으로 작성된 참고 자료입니다. 입찰 전 반드시 당일 기준 공고문 및 현황조서를 재확인하시기 바라며, 현장 임장 및 입찰 대리 상담은 언제든 편하게 문의해 주십시오.

우리부동산 공인중개사사무소 대표 김태형 ☎ 032-582-6200 / 010-2660-8276
#{clean_apt_name} #아파트경매 #법원경매 #권리분석 #경락잔금대출 #우리부동산 #공인중개사김소장"""
            st.text_area("📋 아파트 경매 네이버 블로그 완성본", apt_blog_post, height=340)