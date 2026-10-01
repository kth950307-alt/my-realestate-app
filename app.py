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
        st.caption("공장 전문 중개 관리 시스템 - 사무실 보안 인증")
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
# ⚡ 경량화 캐시 및 DB 관리 함수
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        return pd.read_csv(CUSTOMERS_CSV)
    cols = ["접수일자", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세)", "입주시기", "호이스트", "대형차진입", "희망전력kW", "상담메모", "진행상태"]
    return pd.DataFrame(columns=cols)

def save_customer(new_data):
    df = load_customers()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated.to_csv(CUSTOMERS_CSV, index=False, encoding="utf-8-sig")
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
# ⚡ 캐시 데이터 함수 (경매 / 청약)
# =============================================================
@st.cache_data(ttl=3600)
def get_cached_auctions():
    factory_auctions = [
        {"사건번호": "2026타경10452", "법원": "인천지법 본원", "소재지": "인천 서구 가좌동 556-12", "용도": "제조공장", "바닥평수": 160, "현재동력kW": 75, "호이스트": "5T 완비", "감정가원": 1850000000, "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)", "기일": "2026-10-22", "진행": "유찰 1회"},
        {"사건번호": "2026타경11208", "법원": "인천지법 본원", "소재지": "인천 서구 오류동 검단산단 42-5", "용도": "신축공장", "바닥평수": 240, "현재동력kW": 150, "호이스트": "레일구비", "감정가원": 2680000000, "최저가원": 1876000000, "최저가": "18억 7,600만 원 (70%)", "기일": "2026-10-27", "진행": "유찰 1회"},
        {"사건번호": "2026타경09874", "법원": "인천지법 본원", "소재지": "인천 남동구 고잔동 남동산단", "용도": "공장/사무동", "바닥평수": 350, "현재동력kW": 200, "호이스트": "3T/5T 복수", "감정가원": 3820000000, "최저가원": 2674000000, "최저가": "26억 7,400만 원 (70%)", "기일": "2026-11-03", "진행": "유찰 1회"},
        {"사건번호": "2026타경12541", "법원": "인천지법 본원", "소재지": "인천 서구 원창동 북항배후단지", "용도": "물류창고", "바닥평수": 400, "현재동력kW": 50, "호이스트": "없음(도크완비)", "감정가원": 4500000000, "최저가원": 3150000000, "최저가": "31억 5,000만 원 (70%)", "기일": "2026-11-10", "진행": "유찰 1회"}
    ]
    apt_auctions = [
        {"사건번호": "2026타경10892", "시도": "인천", "자치구": "연수구", "소재지": "인천 송도센트럴파크푸르지오", "타입": "전용 84㎡ (35평)", "감정가원": 950000000, "최저가원": 665000000, "최저가": "6억 6,500만 원 (70%)", "기일": "2026-10-20"},
        {"사건번호": "2026타경11430", "시도": "인천", "자치구": "서구", "소재지": "인천 청라호수공원 한신더휴", "타입": "전용 84㎡ (34평)", "감정가원": 820000000, "최저가원": 574000000, "최저가": "5억 7,400만 원 (70%)", "기일": "2026-10-22"},
        {"사건번호": "2026타경07819", "시도": "경기", "자치구": "부천시", "소재지": "경기 부천 중동 센트럴파크 푸르지오", "타입": "전용 84㎡ (35평)", "감정가원": 1180000000, "최저가원": 826000000, "최저가": "8억 2,600만 원 (70%)", "기일": "2026-10-26"},
        {"사건번호": "2026타경10550", "시도": "서울", "자치구": "서초구", "소재지": "서울 서초 반포 아크로리버파크", "타입": "전용 84㎡ (34평)", "감정가원": 4300000000, "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "기일": "2026-11-12"},
        {"사건번호": "2026타경14210", "시도": "서울", "자치구": "강남구", "소재지": "서울 강남 대치 은마아파트", "타입": "전용 76㎡ (30평)", "감정가원": 2600000000, "최저가원": 2080000000, "최저가": "20억 8,000만 원 (80%)", "기일": "2026-11-16"},
        {"사건번호": "2026타경08712", "시도": "서울", "자치구": "마포구", "소재지": "서울 마포 마포프레스티지자이", "타입": "전용 59㎡ (25평)", "감정가원": 1750000000, "최저가원": 1400000000, "최저가": "14억 원 (80%)", "기일": "2026-10-28"}
    ]
    return factory_auctions, apt_auctions

@st.cache_data(ttl=3600)
def get_cached_subscriptions():
    return [
        {"단지명": "계양 롯데캐슬 파크시티 1단지", "권역": "인천", "위치": "인천 계양구 효성동 100", "규모": "1,964세대", "1순위": "2026-10-07", "당첨": "2026-10-15", "분양가": "6억 5,900만 원 (84㎡)", "분양가원": 659000000, "주변시세": 750000000},
        {"단지명": "검단신도시 푸르지오 더 파크", "권역": "인천", "위치": "인천 서구 마전동 AA28BL", "규모": "919세대", "1순위": "2026-10-15", "당첨": "2026-10-23", "분양가": "5억 8,200만 원 (84㎡)", "분양가원": 582000000, "주변시세": 720000000},
        {"단지명": "송도국제도시 11공구 자이 풍경채", "권역": "인천", "위치": "인천 연수구 송도동 11공구", "규모": "2,728세대", "1순위": "2026-10-20", "당첨": "2026-10-28", "분양가": "8억 6,500만 원 (84㎡)", "분양가원": 865000000, "주변시세": 1050000000}
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
        "🏢 [부업] 수도권 청약 알림 & 자금분석",
        "⚖️ [부업] 인천 공장 & 광역 경매 허브"
    ],
    index=2
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.caption("⚡ **공장 중개 실무 모드 가동 중**")

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

현장 답사나 세부 도면 확인을 원하시면 편하게 회신 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
                    with st.expander(f"📱 {cust['고객명']} 대표님 맞춤 전송용 카카오톡 브리핑문 열기"):
                        st.text_area(f"카톡 전송문_{idx}", cust_kakao, height=320)
            else:
                st.info("현재 대기 손님 장부 중 이 매물과 일치율 60% 이상인 고객이 없습니다.")

            st.markdown("---")
            st.subheader("📝 네이버 블로그 포스팅용 본문")
            clean_deal = deal_type.split('(')[0]
            blog_post = f"""[{loc} 공장 {clean_deal}] {hoist} & 즉시 입주! {price} ({area})

안녕하십니까. 인천 서구 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

오늘 소개해 드릴 현장은 {loc} 공업지역 내에 위치한 알짜 {clean_deal} 매물입니다.
{hoist} 설비와 {power} 인프라가 완비되어 있어 즉시 조업 투입 가능한 특급 사업장입니다.

매물 항목 | 상세 제원
---|---
소재지 / 입지 | {loc} ({memo})
거래 구분 | {deal_type}
가격 조건 | {price}
실사용 면적 | {area}
층고 제원 | {ceiling}
인입 동력 | {power}
호이스트 설비 | {hoist}
도로 및 주차 | {road} / 주차 {parking}
화물 접안 여건 | {big_truck}
입주 현황 | {vacancy_status} ({expire_date})

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
# 3. 📁 공장 보유 매물 장부 (드롭다운 3대 조건 정밀 필터 완비)
# =============================================================
elif menu == "📁 공장 보유 매물 장부 (드롭다운 필터 완비)":
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()

    if not df_p.empty:
        # 상단 3대 핵심 조건 드롭다운 바
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

        # 필터링 로직 수행
        filtered_df = df_p.copy()

        # 1. 평수 필터링
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

        # 2. 호이스트 필터링
        if sel_hoist == "호이스트 완비(설치)":
            filtered_df = filtered_df[filtered_df["호이스트"].str.contains("완비|설치|톤|T|더블거더", na=False) & ~filtered_df["호이스트"].str.contains("없음", na=False)]
        elif sel_hoist == "호이스트 없음":
            filtered_df = filtered_df[filtered_df["호이스트"].str.contains("없음", na=False)]

        # 3. 화물차 필터링
        if sel_truck == "츄레라/트레일러 진입 가능":
            filtered_df = filtered_df[filtered_df["대형차량"].str.contains("츄레라|트레일러", na=False)]
        elif sel_truck == "11톤/윙바디 이상 진입":
            filtered_df = filtered_df[filtered_df["대형차량"].str.contains("츄레라|트레일러|11T|11톤|윙바디", na=False)]

        # 4. 텍스트 검색 필터링
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
# 5. 🏢 [부업] 수도권 청약 알림 & 자금분석
# =============================================================
elif menu == "🏢 [부업] 수도권 청약 알림 & 자금분석":
    st.title("🏢 수도권 실시간 청약 알림 & 분양 수지분석")
    subs = get_cached_subscriptions()
    st.dataframe(pd.DataFrame(subs)[["단지명", "권역", "위치", "규모", "1순위", "당첨", "분양가"]], use_container_width=True, height=180)

    st.markdown("---")
    st.subheader("💰 청약 자금 타임라인(10-60-30) & 안전마진 계산기")
    sel_sub = st.selectbox("분석할 청약 단지 선택", [s["단지명"] for s in subs])
    sub_data = next(s for s in subs if s["단지명"] == sel_sub)

    c_p = sub_data["분양가원"]
    m_p = st.number_input("주변 준신축 동일 평형 시세 (원)", value=sub_data["주변시세"], step=10000000)

    margin = m_p - c_p
    c10 = int(c_p * 0.10)
    m60 = int(c_p * 0.60)
    balance30 = int(c_p * 0.30)

    st.markdown(f"""
    <div class="calc-box-blue">
        <b>확정 분양가</b>: {c_p:,}원 | <b>예상 안전마진(P)</b>: <span style="color: {'#e53e3e' if margin > 0 else '#4a5568'}; font-weight: bold;">약 {margin:,}원</span><br>
        • <b>계약금(10%)</b>: {c10:,}원 (당첨 즉시 필요 현금)<br>
        • <b>중도금(60%)</b>: {m60:,}원 (집단 중도금 대출)<br>
        • <b>잔금(30%)</b>: {balance30:,}원 (입주 시 주담대 전환)
    </div>
    """, unsafe_allow_html=True)

# =============================================================
# 6. ⚖️ [부업] 인천 공장 & 광역 경매 허브
# =============================================================
else:
    st.title("⚖️ 법원경매 허브 & 인천 서구 공장 시설비 분석")
    fac_auc, apt_auc = get_cached_auctions()
    tab_a1, tab_a2 = st.tabs(["🏭 인천 공장·창고 경매 & 시설비 수지표", "🏢 수도권 광역 아파트 경매"])

    with tab_a1:
        st.dataframe(pd.DataFrame(fac_auc)[["사건번호", "소재지", "용도", "바닥평수", "현재동력kW", "호이스트", "최저가", "기일", "진행"]], use_container_width=True, height=180)
        sel_fac_num = st.selectbox("시설비 분석 공장 사건 선택", [f"{a['사건번호']} - {a['소재지']}" for a in fac_auc])
        fac_obj = next(a for a in fac_auc if a["사건번호"] == sel_fac_num.split(" - ")[0])

        target_bid = st.number_input("예상 낙찰가 (원)", value=fac_obj["최저가원"], step=10000000)
        req_p = st.number_input(f"목표 동력 (현재 {fac_obj['현재동력kW']}kW)", min_value=fac_obj['현재동력kW'], max_value=500, value=max(fac_obj['현재동력kW'], 100), step=10)
        add_p = max(0, req_p - fac_obj['현재동력kW'])
        p_cost = add_p * 95000

        loan_75 = int(target_bid * 0.75)
        tax_46 = int(target_bid * 0.046)
        total_cash = (target_bid - loan_75) + tax_46 + p_cost

        st.markdown(f"""
        <div class="calc-box-orange">
            <b>[{fac_obj['사건번호']}] 턴키 입주 수지분석</b><br>
            • 예상 낙찰가: {target_bid:,}원 (경락잔금대출 75%: 약 {loan_75:,}원)<br>
            • 취득세(4.6%): {tax_46:,}원 | 전력 증설비({add_p}kW): {p_cost:,}원<br>
            • <b>실제 총 필요 자기자본 (실투자금)</b>: <span style="font-size: 16px; font-weight: bold; color: #c53030;">{total_cash:,}원</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_a2:
        st.dataframe(pd.DataFrame(apt_auc)[["사건번호", "시도", "자치구", "소재지", "타입", "최저가", "기일"]], use_container_width=True, height=220)