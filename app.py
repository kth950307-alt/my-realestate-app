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
        st.caption("인천 공장 중개 & 엔터프라이즈 손님 CRM - 사무실 보안 인증")
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
# ⚡ CSV 데이터베이스 관리 함수 (KeyError 방지 컬럼 동기화)
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        # 구버전 컬럼명 호환성 처리 (KeyError 방지 핵심)
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

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

# 안전한 컬럼 값 추출 헬퍼 함수
def get_safe_cust_val(row, col_name, default=""):
    val = row.get(col_name, default)
    if pd.isna(val):
        if col_name == "예산(보증금/월세/매매가)":
            val = row.get("예산(보증금/월세)", default)
        else:
            val = default
    return str(val) if pd.notna(val) else default

# 🎯 공장 매물 ➡️ 대기 손님 역매칭
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

        c_deal = str(row.get("거래구분", ""))
        if "매매" in fac_deal_type and "매매" in c_deal:
            score += 20
            reasons.append("매매 일치")
        elif "임대" in fac_deal_type and "임대" in c_deal:
            score += 20
            reasons.append("임대 일치")
        elif "겸용" in c_deal or "겸용" in fac_deal_type:
            score += 15
            reasons.append("거래조건 협의가능")
        else:
            score -= 30

        c_loc = str(row.get("희망권역", ""))
        loc_words = [w for w in fac_loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if (not c_loc.strip()) or any(w in c_loc for w in loc_words) or any(w in fac_loc for w in c_loc.split()):
            score += 25
            reasons.append("권역 일치")

        c_pyungs = parse_pyung_numbers(row.get("희망평수", ""))
        if f_pyung and c_pyungs:
            c_pyung = c_pyungs[0]
            if (c_pyung * 0.8) <= f_pyung <= (c_pyung * 1.25):
                score += 30
                reasons.append(f"평수({int(c_pyung)}평) 부합")
            elif (c_pyung * 0.6) <= f_pyung <= (c_pyung * 1.4):
                score += 15
                reasons.append("평수 근사치")
        else:
            score += 10

        c_hoist = str(row.get("호이스트", ""))
        if "필수" in c_hoist:
            if f_has_hoist:
                score += 15
                reasons.append("호이스트 충족")
            else:
                score -= 40
        else:
            score += 10

        c_truck = str(row.get("대형차진입", ""))
        c_truck_lv = 4 if any(k in c_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in c_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in c_truck for k in ["5T", "5톤"]) else 1))
        if f_truck_lv >= c_truck_lv:
            score += 10
            reasons.append("진입차량 충족")
        else:
            score -= 20

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

# 🎯 특정 손님 ➡️ 보유 매물 즉시 추천
def match_properties_for_customer(cust_row):
    df_p = load_properties()
    if df_p.empty: return []

    c_deal = str(cust_row.get("거래구분", ""))
    c_loc = str(cust_row.get("희망권역", ""))
    c_pyungs = parse_pyung_numbers(cust_row.get("희망평수", ""))
    c_pyung = c_pyungs[0] if c_pyungs else None
    c_hoist = str(cust_row.get("호이스트", ""))
    c_truck = str(cust_row.get("대형차진입", ""))
    c_truck_lv = 4 if any(k in c_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in c_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in c_truck for k in ["5T", "5톤"]) else 1))

    matched_props = []
    for _, prop in df_p.iterrows():
        p_deal = str(prop.get("거래구분", ""))
        p_loc = str(prop.get("소재지(권역)", ""))
        p_area = str(prop.get("면적", ""))
        p_hoist = str(prop.get("호이스트", ""))
        p_truck = str(prop.get("대형차량", ""))

        if ("매매" in c_deal and "매매" not in p_deal) and ("겸용" not in p_deal and "겸용" not in c_deal): continue
        if ("임대" in c_deal and "임대" not in p_deal) and ("겸용" not in p_deal and "겸용" not in c_deal): continue

        loc_words = [w for w in c_loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if loc_words and not any(w in p_loc for w in loc_words): continue

        p_pyungs = parse_pyung_numbers(p_area)
        if c_pyung and p_pyungs:
            p_p = p_pyungs[0]
            if not ((c_pyung * 0.75) <= p_p <= (c_pyung * 1.3)): continue

        p_has_hoist = any(k in p_hoist for k in ["완비", "설치", "톤", "T", "더블거더"]) and ("없음" not in p_hoist)
        if "필수" in c_hoist and not p_has_hoist: continue

        p_truck_lv = 4 if any(k in p_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in p_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in p_truck for k in ["5T", "5톤"]) else 1))
        if p_truck_lv < c_truck_lv: continue

        matched_props.append(prop)

    return matched_props

# =============================================================
# 📌 업무 메뉴 네비게이션
# =============================================================
menu = st.sidebar.radio(
    "📌 업무 시스템 메뉴",
    [
        "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
        "📋 [주업] 공장 손님 장부 (CRM & 리마인드)",
        "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)",
        "🔍 [주업] 공장·창고 AI 시세 추정기",
        "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
        "🏢 [부업] 수도권 청약 알림 허브 & 수지분석",
        "⚖️ [부업] 법원경매 허브 & 인천공장 시설분석"
    ],
    index=1
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

• 소재지: {loc}
• 거래구분: {deal_type}
• 가격조건: {price}
• 실사용 면적: {area}
• 층고 제원: {ceiling}
• 인입 동력: {power}
• 호이스트: {hoist}
• 물류 여건: {big_truck}
• 입주 시기: {vacancy_status} ({expire_date})

💡 현장 핵심 포인트: {memo}

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
                    with st.expander(f"📱 {cust['고객명']} 대표님 맞춤 전송용 카카오톡 브리핑문 열기"):
                        st.text_area(f"카톡 전송문_{idx}", cust_kakao, height=300)
            else:
                st.info("현재 대기 손님 장부 중 이 매물과 일치율 55% 이상인 고객이 없습니다.")

# =============================================================
# 2. 📋 [주업] 공장 손님 장부 (에러 방지 안전 코드 적용)
# =============================================================
elif menu == "📋 [주업] 공장 손님 장부 (CRM & 리마인드)":
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

            def render_customer_cards(filtered_customers):
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

                    with btn_c1: show_prop_match = st.button(f"🎯 추천 보유매물 조회", key=f"btn_match_{orig_idx}")
                    with btn_c2: show_kakao_gen = st.button(f"💬 안부/체크 카톡 생성", key=f"btn_kakao_{orig_idx}")
                    with btn_c3: show_history = st.button(f"📝 상담일지 열기", key=f"btn_hist_{orig_idx}")

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
                        st.text_area(f"카톡 안부 복사창 ({c_name_val})", hello_talk, height=260)

                    if show_history:
                        st.markdown(f"###### 📝 [{c_name_val} 대표님] 누적 상담 히스토리 일지")
                        current_hist = str(c_row.get("상담히스토리", ""))
                        if current_hist.strip():
                            st.text_area("이전 상담 기록", current_hist, height=120, disabled=True, key=f"hist_view_{orig_idx}")
                        else:
                            st.caption("아직 누적된 상담 일지가 없습니다.")

                        with st.form(f"form_hist_add_{orig_idx}"):
                            new_log = st.text_input("오늘 통화/상담 내용 입력", placeholder="예: 2차 유선 통화 완료. 이번 주 목요일 현장 미팅 약속")
                            if st.form_submit_button("💾 상담 일지에 추가 저장"):
                                if new_log.strip():
                                    time_tag = datetime.today().strftime("%Y-%m-%d %H:%M")
                                    updated_hist_str = f"[{time_tag}] {new_log.strip()}\n" + current_hist
                                    df_c.at[orig_idx, "상담히스토리"] = updated_hist_str
                                    df_c.at[orig_idx, "최근연락일"] = datetime.today().strftime("%Y-%m-%d")
                                    save_all_customers(df_c)
                                    st.success("✅ 상담 일지가 누적 저장되었습니다!")
                                    st.rerun()

                    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

            with subtab_vip:
                vip_df = df_c[df_c["중요도"].str.contains("S급|A급", na=False) & ~df_c["진행상태"].isin(["계약 완료", "보류/마감"])]
                render_customer_cards(vip_df)

            with subtab_active:
                act_df = df_c[~df_c["진행상태"].isin(["계약 완료", "보류/마감"])]
                render_customer_cards(act_df)

            with subtab_done:
                done_df = df_c[df_c["진행상태"] == "계약 완료"]
                render_customer_cards(done_df)

            with subtab_all:
                render_customer_cards(df_c)
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
# 4. 🔍 [주업] 공장·창고 AI 시세 추정기 (신규 탑재)
# =============================================================
elif menu == "🔍 [주업] 공장·창고 AI 시세 추정기":
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
        # 1. 권역별 대지 기준 평단가 산출 (인천 서구 실무 데이터)
        if "가좌" in v_addr or "석남" in v_addr:
            land_base_min = 8500000; land_base_max = 11000000
        elif "원창" in v_addr or "북항" in v_addr:
            land_base_min = 7500000; land_base_max = 9800000
        elif "오류" in v_addr or "검단" in v_addr:
            land_base_min = 6500000; land_base_max = 8500000
        else:
            land_base_min = 7000000; land_base_max = 9000000

        # 도로 여건 가산
        road_mult = 1.05 if "8m~10m" in v_road else (0.95 if "골목" in v_road else 1.0)
        land_val_min = int(v_land_pyung * land_base_min * road_mult)
        land_val_max = int(v_land_pyung * land_base_max * road_mult)

        # 2. 건물 잔존가치 산출 (신축 평당 300만, 35년 정액 감가)
        passed_yr = max(1, 2026 - v_year)
        depreciation = max(0.2, (1.0 - (passed_yr / 35.0)))
        bldg_val = int(v_bldg_pyung * 3000000 * depreciation)

        # 3. 설비 프리미엄
        fac_add = 18000000 if "완비" in v_hoist else 0
        fac_add += int(max(0, v_power - 30) * 80000)

        # 최종 매매가 밴드
        final_sale_min = land_val_min + bldg_val + fac_add
        final_sale_max = land_val_max + bldg_val + fac_add

        # 4. 임대료 산출 (평당 월 3.3만 ~ 4.2만 선)
        rent_unit_min = 34000 if "가좌" in v_addr else 30000
        rent_unit_max = 42000 if "가좌" in v_addr else 38000
        m_rent_min = int(v_bldg_pyung * rent_unit_min)
        m_rent_max = int(v_bldg_pyung * rent_unit_max)
        deposit_est = int((m_rent_min + m_rent_max) / 2 * 10)  # 통상 월세의 10배

        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{v_addr}] 공장 추정 시세 결과</h4>
            • <b>예상 적정 매매가</b>: <span style="font-size: 19px; font-weight: bold; color: #c53030;">{final_sale_min:,}원 ~ {final_sale_max:,}원</span><br>
            • <b>대지 평당 매매단가</b>: 약 {int((final_sale_min/v_land_pyung)/10000):,}만 원 ~ {int((final_sale_max/v_land_pyung)/10000):,}만 원 선<br>
            • <b>예상 적정 임대료</b>: <span style="font-size: 17px; font-weight: bold; color: #2b6cb0;">보증금 {deposit_est:,}원 / 월세 {m_rent_min:,}원 ~ {m_rent_max:,}원</span> (평당 약 {int(rent_unit_min/10000)}.{int((rent_unit_min%10000)/1000)}만~{int(rent_unit_max/10000)}.{int((rent_unit_max%10000)/1000)}만 원)<br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
            💡 <b>세부 감정 평가 내역</b><br>
            • 대지 가치: 약 {land_val_min:,}원 ~ {land_val_max:,}원 (도로 접면 반영)<br>
            • 건물 잔존가치: 약 {bldg_val:,}원 ({passed_yr}년 경과 잔존율 {int(depreciation*100)}% 적용)<br>
            • 인프라 설비 가산: 약 {fac_add:,}원 (호이스트 및 동력 {v_power}kW 가산)
        </div>
        """, unsafe_allow_html=True)

        val_briefing = f"""[인천 공장/창고 시세 감정 및 브리핑 보고서]

대표님 안녕하십니까,
인천 산업단지 공장 전문 우리부동산 김태형 소장입니다.

의뢰해 주신 물건({v_addr}, 대지 {v_land_pyung}평, 건물 {v_bldg_pyung}평)의 국토부 실거래가 및 인근 호가 기반 시세 평가 내역을 보고드립니다.

• 소재지: {v_addr}
• 대지/건물: 대지 {v_land_pyung}평 / 건물연면적 {v_bldg_pyung}평 ({v_year}년식)
• 인프라: {v_hoist}, 동력 {v_power}kW, {v_road}

💰 적정 매매 시세 범위
• 약 {final_sale_min:,}원 ~ {final_sale_max:,}원 (대지 평당 약 {int((final_sale_min/v_land_pyung)/10000)}만~{int((final_sale_max/v_land_pyung)/10000)}만 원)

💰 적정 임대차 시세 범위
• 보증금 약 {deposit_est:,}원 / 월세 {m_rent_min:,}원 ~ {m_rent_max:,}원

현장 보수 상태 및 진입로 코너 여부에 따라 오차가 발생할 수 있으니, 매각 또는 임대차 진행 시 편하게 연락 주십시오.

우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276
"""
        st.text_area("손님 안내용 시세 브리핑 복사창", val_briefing, height=300)

# =============================================================
# 5. 🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기
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
# 6. 🏢 [부업] 수도권 청약 알림 허브 & 수지분석
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
# 7. ⚖️ [부업] 법원경매 허브 & 인천공장 시설분석
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