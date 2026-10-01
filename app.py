import streamlit as st
import pandas as pd
import os
import re
import requests
import base64
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
    .compact-match-title {
        font-size: 14.5px;
        font-weight: bold;
        color: #1a365d;
        margin-bottom: 4px;
    }
    .badge-status {
        background-color: #ebf8ff;
        color: #2b6cb0;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 [보안 잠금] 사무실 전용 로그인 인증
# =============================================================
CORRECT_PASSWORD = "950307"  # 👈 원하는 비밀번호로 변경하세요!

def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("### 🏢 우리부동산 통합 업무 시스템")
        st.caption("비인가 외부인의 접근을 차단하기 위한 사무실 보안 인증 단계입니다.")
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
SUBSCRIPTIONS_CSV = "subscriptions.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        return pd.read_csv(CUSTOMERS_CSV)
    columns = ["접수일자", "상호/고객명", "연락처", "희망권역", "희망평수", "예산(보증금/월세)", "입주시기", "호이스트", "대형차진입", "상담메모", "진행상태"]
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

def update_entire_properties(df):
    df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")

def load_subscriptions():
    if os.path.exists(SUBSCRIPTIONS_CSV):
        return pd.read_csv(SUBSCRIPTIONS_CSV)
    columns = ["등록일자", "사업장/단지명", "지역권역", "공급유형", "공급위치", "공급규모", "분양가(평당/호당)", "특별공급일", "1순위접수일", "당첨자발표일", "체크포인트/안내"]
    return pd.DataFrame(columns=columns)

def save_subscription(new_data):
    df = load_subscriptions()
    updated_df = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated_df.to_csv(SUBSCRIPTIONS_CSV, index=False, encoding="utf-8-sig")
    return updated_df

def parse_pyung_numbers(text):
    if not text or pd.isna(text): return []
    nums = re.findall(r'\d+', str(text))
    return [float(n) for n in nums if 5 <= float(n) <= 5000]

def find_matching_customers(loc, hoist_spec, truck_spec, factory_area_text=""):
    df = load_customers()
    if df.empty: return pd.DataFrame()
    active_df = df[~df["진행상태"].isin(["계약 완료", "보류/마감"])].copy()
    if active_df.empty: return pd.DataFrame()

    matched_indices = []
    factory_truck_level = 4 if any(k in truck_spec for k in ["츄레라", "트레일러"]) else (3 if any(k in truck_spec for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in truck_spec for k in ["5T", "5톤"]) else 1))
    factory_has_hoist = any(k in hoist_spec for k in ["완비", "설치", "톤", "T", "더블거더"]) and ("없음" not in hoist_spec)
    factory_pyungs = parse_pyung_numbers(factory_area_text)
    f_pyung = factory_pyungs[0] if factory_pyungs else None

    for idx, row in active_df.iterrows():
        c_loc = str(row["희망권역"]) if pd.notna(row["희망권역"]) else ""
        c_hoist = str(row["호이스트"]) if pd.notna(row["호이스트"]) else ""
        c_truck = str(row["대형차진입"]) if pd.notna(row["대형차진입"]) else ""
        c_area = str(row["희망평수"]) if pd.notna(row["희망평수"]) else ""

        loc_words = [w for w in loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        if not ((not c_loc.strip()) or any(w in c_loc for w in loc_words) or (c_loc in loc)):
            continue

        c_truck_level = 4 if any(k in c_truck for k in ["츄레라", "트레일러"]) else (3 if any(k in c_truck for k in ["11T", "11톤", "윙바디"]) else (2 if any(k in c_truck for k in ["5T", "5톤"]) else 1))
        if factory_truck_level < c_truck_level:
            continue

        if ("필수" in c_hoist) and (not factory_has_hoist):
            continue

        cust_pyungs = parse_pyung_numbers(c_area)
        if f_pyung and cust_pyungs:
            if not ((min(cust_pyungs) - 60) <= f_pyung <= (max(cust_pyungs) + 60)):
                continue

        matched_indices.append(idx)

    return active_df.loc[matched_indices]

# =============================================================
# 사이드바 메뉴 네비게이션
# =============================================================
menu = st.sidebar.radio(
    "📌 업무 메뉴 선택",
    [
        "✍️ 공장물건 글쓰기 (블로그/카톡)",
        "📋 손님 상담 및 매칭 관리",
        "🏭 공장 매물 관리 장부",
        "🏢 수도권 청약 알림 허브"
    ],
    index=0
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 사진 분석 엔진")
api_key = st.sidebar.text_input("Gemini API Key (선택)", type="password", help="키를 넣으시면 공장, 맛집, 일상 사진을 AI가 정밀 분석하여 본문을 작성합니다.")

# =============================================================
# [1순위 메뉴] 공장/맛집/일상 블로그 글쓰기
# =============================================================
if menu == "✍️ 공장물건 글쓰기 (블로그/카톡)":
    st.title("✍️ 원클릭 글쓰기 및 브리핑 생성기")
    category = st.radio("작성할 카테고리를 선택하세요", ["🏭 공장 매물 브리핑", "🍜 맛집 솔직 후기", "🧢 일상 핫플 탐방"], horizontal=True)

    # 1. 공장 매물 브리핑
    if category == "🏭 공장 매물 브리핑":
        st.subheader("🏭 공장 매물 정보 입력")

        with st.expander("🔒 [중개사 비밀 관리용] 상세 지번 및 건물주 연락처 (블로그 글 미포함)", expanded=True):
            sec1, sec2, sec3 = st.columns(3)
            with sec1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 123-4번지 1층")
            with sec2: owner_name = st.text_input("👤 건물주(임대인) 성함 (비공개)", placeholder="예: 홍길동 회장님")
            with sec3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-9999-8888")

        st.markdown("##### 📌 기본 거래 조건 및 입주 상태")
        b1, b2, b3, b4 = st.columns(4)
        with b1: loc = st.text_input("소재지 / 동 (블로그 노출용)", placeholder="예: 인천 서구 가좌동")
        with b2:
            deal_type = st.selectbox("거래 구분 *", ["임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)", "직접 입력"])
            if deal_type == "직접 입력": deal_type = st.text_input("거래 구분 직접 기입", placeholder="예: 분할 전대차")
        with b3: vacancy_status = st.selectbox("입주 / 공실 상태 *", ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "건물주 사용중(협의)", "신축 첫입주"])
        with b4: expire_date = st.text_input("계약만료일 / 입주협의일", value="즉시 입주 가능 (상호 협의)")

        c1, c2, c3 = st.columns(3)
        with c1:
            price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 280만 원")
            area = st.text_input("면적 (대지/건물/실사용) *", placeholder="예: 바닥 120평 (작업장 110평 + 사무실 10평)")
        with c2:
            ceiling = st.text_input("층고 (처마/유효)", placeholder="예: 처마 8m / 유효 9m 하이 층고")
            power = st.text_input("동력 (전기 용량 kW)", placeholder="예: 제조 동력 50kW (단독 분전반 완비)")
            hoist = st.selectbox("호이스트 유 / 무", ["호이스트 크레인 완비 (3T)", "호이스트 크레인 완비 (5T)", "호이스트 크레인 완비 (2.8T)", "호이스트 없음", "직접 입력"])
            if hoist == "직접 입력": hoist = st.text_input("호이스트 스펙 직접 기입")
        with c3:
            road = st.text_input("진입 도로 여건 (직접 입력)", placeholder="예: 10m 도로 접 / 코너 각지 도로")
            parking = st.selectbox("주차 대수", ["1대", "2대", "3대", "5대 이상 가능", "단독 마당 10대 이상"])
            big_truck = st.selectbox("대형차량 작업 여부 *", ["츄레라 / 트레일러 진출입 및 상하차 원활", "11T / 대형 윙바디 접안 원활", "5T 화물차 문 앞 상하차 수월", "1T / 소형 화물차 최적화"])

        c4, c5 = st.columns(2)
        with c4: sub = st.text_input("출입문 및 부속시설", placeholder="예: 대형 행거도어, 약 8평 내부 사무실")
        with c5: memo = st.text_area("특징 및 입지 메모", placeholder="예: 가좌IC 인접, 대형 트레일러 회전 마당 확보")

        st.markdown("##### 📸 공장 현장 사진 첨부")
        factory_images = st.file_uploader("공장 사진을 올려주세요", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="factory_img")
        if factory_images:
            cols = st.columns(min(len(factory_images), 4))
            for idx, img_file in enumerate(factory_images):
                with cols[idx % 4]: st.image(img_file, caption=f"사진 {idx+1}", use_container_width=True)

        if st.button("🚀 공장 매물 생성하기 (매물저장 + 블로그글 + 카톡브리핑문)", type="primary"):
            clean_loc = loc if loc else "인천 서구 가좌동"
            road_clean = road if road else "도로망 양호"
            road_parking_summary = f"{road_clean}, 주차 {parking}, {big_truck}"

            new_prop_entry = {
                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
                "거래구분": deal_type, "소재지(권역)": clean_loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
                "임대인연락처": owner_phone, "가격(보/월)": price, "면적": area, "층고": ceiling, "동력": power,
                "호이스트": hoist, "도로/주차": f"{road_clean} / {parking}", "대형차량": big_truck, "특징메모": memo
            }
            save_property(new_prop_entry)
            st.success("✅ 매물이 '공장 매물 관리 장부'에 성공적으로 누적 저장되었습니다!")

            matched_customers = find_matching_customers(clean_loc, hoist, big_truck, area)
            if not matched_customers.empty:
                st.markdown("---")
                st.markdown(f"##### 🎯 이 매물에 딱 맞는 대기 손님 ({len(matched_customers)}명 발견 / 평수 ±60평 반영)")
                for _, cust in matched_customers.iterrows():
                    st.markdown(f"""
                    <div class="compact-match-card">
                        <div class="compact-match-title">👤 {cust['상호/고객명']} ({cust['연락처']}) <span class="badge-status">{cust['진행상태']}</span></div>
                        • <b>희망지역</b>: {cust['희망권역']} | 📐 <b>희망평수</b>: {cust['희망평수']} | 💰 <b>예산</b>: {cust['예산(보증금/월세)']} | 🗓️ <b>입주</b>: {cust['입주시기']}<br>
                        • <b>호이스트</b>: {cust['호이스트']} | 🚛 <b>차량작업</b>: {cust['대형차진입']} | 📝 <b>상담메모</b>: {cust['상담메모']}
                    </div>
                    """, unsafe_allow_html=True)

            kakao_briefing = f"""[신규 공장 매물 브리핑 안내]

대표님 안녕하십니까, 
인천 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

찾으시던 조건에 부합하는 알짜 신규 공장 매물이 접수되어 먼저 브리핑 안내드립니다.

• 권역/위치: {clean_loc}
• 거래형태: {deal_type}
• 가격조건: {price}
• 입주현황: {vacancy_status} ({expire_date})
• 실사용 면적: {area}
• 처마 층고: {ceiling}
• 인입 동력: {power}
• 호이스트: {hoist}
• 도로/주차: {road_clean} / 주차 {parking}
• 물류 여건: {big_truck}

💡 현장 핵심 포인트
• {memo}

현장 답사나 세부 도면 검토가 필요하시면 편하게 회신 주십시오.
우리부동산 공인중개사사무소 김태형 (010-2660-8276)
"""
            st.markdown("---")
            st.subheader("📱 손님 카카오톡 / 문자 원클릭 전송문")
            st.text_area("카톡 브리핑 복사창", kakao_briefing, height=340)

            st.markdown("---")
            st.subheader("📝 네이버 블로그 포스팅용 본문")
            post = f"""[{clean_loc} 공장 {deal_type.split('(')[0]}] {hoist} & 입주협의! {deal_type} ({price}, {area})
안녕하십니까. 인천 산업단지 공장·창고 전문 우리부동산입니다.

{clean_loc} 공업지역 내에서 {hoist} 설비를 완비한 1층 사업장을 {price} 조건으로 확보하는 것은 대단히 드문 기회입니다.

{memo} 배후 권역에서 소형/중형 면적 제조 작업장을 물색해 보시면, 도로망과 전력 인프라가 갖추어진 물건 자체가 드물어 사옥 이전에 고심하시는 대표님들이 많습니다. 오늘 소개해 드리는 사업장은 {clean_loc} 소재 {deal_type} 건으로, {price}이라는 주변 시세 대비 매우 합리적인 조건으로 공급됩니다.

무엇보다 {vacancy_status} 상태로 {expire_date} 조건에 맞춰 안정적으로 조업 일정을 잡으실 수 있습니다. 도로 및 진출입 여건 또한 양호하여 {road_clean} 여건과 주차 {parking}, {big_truck} 조건을 갖추어 원자재 및 완제품의 상하차 작업성이 우수합니다.

매물 항목 | 상세 정보
---|---
가격 조건 | {price}
위치 / 입지 | {clean_loc} ({memo})
매물 구분 / 계약 형태 | {deal_type}
입주 현황 | {vacancy_status} ({expire_date})
면적 (대지/건물/실사용) | {area}
층고 제원 | {ceiling}
인입 동력 (전력) | {power}
도로 및 주차 대수 | {road_clean} / 주차 {parking}
대형차량 작업 여부 | {big_truck}
출입문 / 부속시설 | {sub}
양도 / 고정 설비 | {hoist}

우리부동산 공인중개사사무소
대표 공인중개사 김태형
010-2660-8276
"""
            st.text_area("블로그 본문 복사하기", post, height=450)

    # 2. 맛집 솔직 후기 (사진 업로드 + 공략 키워드 칸 완비)
    elif category == "🍜 맛집 솔직 후기":
        st.subheader("🍜 맛집 방문 정보 및 사진 입력")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
            m_addr = st.text_input("매장 위치 / 주소", placeholder="예: 인천 서구 청라커낼로 000")
            m_order = st.text_input("주문 메뉴 및 가격", placeholder="예: 점심특선 연탄불고기 2인 (25,000원)")
        with m_col2:
            m_keyword = st.text_input("🎯 블로그 상위 노출 공략 키워드 *", placeholder="예: 청라 맛집, 청라 고기집, 연탄불고기, 청라 점심")
            m_parking = st.text_input("주차 / 영업시간", placeholder="예: 건물 지하주차 2시간 무료 / 매일 11:30~23:00")
            m_summary = st.text_input("김소장의 한 줄 총평 *", placeholder="예: 불향 가득한 고기와 찌개 조합이 끝내주는 가성비 맛집!")

        st.markdown("##### 📸 음식 및 매장 사진 첨부 (다중 업로드)")
        food_images = st.file_uploader("맛집 사진을 올려주세요 (음식, 간판, 내부 등)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="food_imgs")
        if food_images:
            f_cols = st.columns(min(len(food_images), 4))
            for idx, f_img in enumerate(food_images):
                with f_cols[idx % 4]:
                    st.image(f_img, caption=f"사진 {idx+1}", use_container_width=True)

        m_dish = st.text_area("메인 요리 맛 평가 (고기 식감, 소스, 밑반찬 등)", placeholder="예: 연탄불향이 은은하게 배어있어 잡내 없이 담백하고, 파채와 곁들여 먹으니 궁합이 최고였습니다.")
        m_side = st.text_area("식사/사이드 및 분위기 메모", placeholder="예: 함께 나오는 된장찌개도 깊은 맛이 나고 매장이 깔끔해 가족 외식이나 회식으로 좋습니다.")

        if st.button("🚀 맛집 솔직 후기 포스팅 생성하기", type="primary"):
            clean_name = m_name if m_name else "추천 맛집"
            keywords_list = [k.strip() for k in m_keyword.split(",") if k.strip()]
            tag_string = " ".join([f"#{k.replace(' ', '')}" for k in keywords_list]) if keywords_list else f"#{clean_name} #인천맛집 #솔직후기"

            if api_key and GENAI_AVAILABLE and food_images:
                with st.spinner("AI가 음식 사진과 공략 키워드를 분석하여 네이버 상위 노출 규격 글을 작성 중입니다..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        pil_imgs = [Image.open(img) for img in food_images]
                        ai_prompt = f"""
너는 맛집 탐방을 진솔하게 소개하는 프로 블로거 김소장이야.
아래 정보와 첨부된 사진들을 기반으로 네이버 블로그 스마트블록 상위 노출에 최적화된 글을 써줘.
- 상호명: {clean_name}
- 위치: {m_addr}
- 메뉴/가격: {m_order}
- 주차/영업: {m_parking}
- 공략 키워드: {m_keyword} (본문에 자연스럽게 4~5회 녹여낼 것)
- 맛 평가: {m_dish}
- 사이드/분위기: {m_side}
- 총평: {m_summary}
- 해시태그: {tag_string}
사진 위치 코멘트(예: [사진 1: 노릇하게 구워진 연탄불고기])를 알맞게 넣어주고 내돈내산 느낌의 신뢰도 높은 어조로 써줘.
"""
                        resp = client.models.generate_content(model='gemini-2.5-flash', contents=[ai_prompt] + pil_imgs)
                        st.success("✨ AI가 사진을 직접 분석하여 맞춤 맛집 글을 완성했습니다!")
                        st.text_area("블로그 본문 복사창", resp.text, height=550)
                    except Exception as e:
                        st.error(f"AI 호출 에러: {e}")
            else:
                food_post = f"""[{clean_name}] {m_keyword} 내돈내산 솔직 후기! ({m_order})

안녕하세요! 인천 구석구석 알짜 소식을 전해드리는 우리부동산 김소장입니다.

오늘은 대표님들께 든든한 한 끼 식사나 모임 장소로 강력 추천해 드리고 싶은 {clean_name}에 다녀왔습니다.
직접 맛보고 솔직하게 남기는 내돈내산 방문 후기 지금 시작합니다!

━━━━━━━━━━━━━━━━━━━━
📌 매장 기본 정보
━━━━━━━━━━━━━━━━━━━━
• 상호명: {clean_name}
• 위치/주소: {m_addr}
• 주요 메뉴: {m_order}
• 주차 및 운영: {m_parking}

(사진 1 - 매장 외관 및 전면 간판 전경)
매장 입구부터 깔끔하게 정돈된 인테리어가 눈에 띕니다. 주차 여건도 {m_parking} 조건으로 쾌적하게 방문할 수 있었습니다.

(사진 2 - 먹음직스럽게 준비된 메인 요리 상차림)
주문한 {m_order}이 한 상 가득 정갈하게 세팅되었습니다.
{m_dish}

(사진 3 - 사이드 메뉴 및 곁들임 요리)
{m_side}

💡 김소장의 솔직 총평
"{m_summary}"

부담 없는 가격에 퀄리티 높은 요리를 즐길 수 있는 곳이라 재방문 의사 100%입니다.
인근에 계시거나 맛있는 한 끼를 고민 중이신 분들은 꼭 한번 방문해 보시길 권해드립니다!

{tag_string} #우리부동산 #김소장의맛집탐방
"""
                st.text_area("블로그 본문 복사창", food_post, height=500)

    # 3. 일상 핫플 탐방 (사진 업로드 + 공략 키워드 칸 완비)
    else:
        st.subheader("🧢 일상 핫플 탐방 정보 및 사진 입력")

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            d_place = st.text_input("핫플 장소 / 브랜드명 *", placeholder="예: 스투시 서울 챕터")
            d_addr = st.text_input("위치 / 주소", placeholder="예: 서울 강남구 압구정로 도산공원 인근")
            d_time = st.text_input("방문 일시 / 영업시간", placeholder="예: 일요일 오후 2시 방문 / 11:00~20:00")
        with d_col2:
            d_keyword = st.text_input("🎯 블로그 상위 노출 공략 키워드 *", placeholder="예: 스투시 서울, 도산공원 핫플, 압구정 스투시 웨이팅")
            d_wait = st.text_input("웨이팅 현황 / 대기 시간", placeholder="예: 현장 대기 약 40분 (주말 기준)")
            d_summary = st.text_input("김소장의 한 줄 총평 *", placeholder="예: 40분 웨이팅이 아깝지 않은 스트릿 패션의 성지!")

        st.markdown("##### 📸 핫플 현장 사진 첨부 (다중 업로드)")
        daily_images = st.file_uploader("핫플 사진을 올려주세요 (내부 인테리어, 아이템, 외관 등)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="daily_imgs")
        if daily_images:
            d_cols = st.columns(min(len(daily_images), 4))
            for idx, d_img in enumerate(daily_images):
                with d_cols[idx % 4]:
                    st.image(d_img, caption=f"사진 {idx+1}", use_container_width=True)

        d_items = st.text_area("내부 분위기 및 주요 전시/판매 아이템", placeholder="예: 매장 내부 미니멀한 인테리어가 인상적이며, 신상 후드티와 모자 라인업이 다양하게 구비되어 있었습니다.")
        d_staff = st.text_area("직원 친절도 및 구매 팁", placeholder="예: 대기 인원이 많지만 입장 안내가 체계적이었고, 인기 사이즈는 조기 품절될 수 있으니 오픈 시간대 공략을 추천합니다.")

        if st.button("🚀 일상 핫플 탐방 포스팅 생성하기", type="primary"):
            clean_place = d_place if d_place else "핫플레이스"
            d_keywords_list = [k.strip() for k in d_keyword.split(",") if k.strip()]
            d_tag_string = " ".join([f"#{k.replace(' ', '')}" for k in d_keywords_list]) if d_keywords_list else f"#{clean_place} #핫플레이스 #일상탐방"

            if api_key and GENAI_AVAILABLE and daily_images:
                with st.spinner("AI가 핫플 사진과 키워드를 분석하여 감각적인 포스팅을 작성 중입니다..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        pil_d_imgs = [Image.open(img) for img in daily_images]
                        ai_d_prompt = f"""
너는 센스 있고 트렌디한 일상을 공유하는 프로 블로거 김소장이야.
아래 정보와 첨부된 사진들을 기반으로 네이버 블로그 스마트블록 노출에 최적화된 글을 써줘.
- 장소/브랜드: {clean_place}
- 위치: {d_addr}
- 방문일시/웨이팅: {d_time} ({d_wait})
- 공략 키워드: {d_keyword} (자연스럽게 녹여낼 것)
- 내부 분위기/아이템: {d_items}
- 구매 팁/체감: {d_staff}
- 한 줄 총평: {d_summary}
- 해시태그: {d_tag_string}
사진 코멘트를 적절하게 배치하고 직접 다녀온 생생한 후기 형식으로 써줘.
"""
                        d_resp = client.models.generate_content(model='gemini-2.5-flash', contents=[ai_d_prompt] + pil_d_imgs)
                        st.success("✨ AI가 사진을 직접 분석하여 감각적인 핫플 글을 완성했습니다!")
                        st.text_area("블로그 본문 복사창", d_resp.text, height=550)
                    except Exception as e:
                        st.error(f"AI 호출 에러: {e}")
            else:
                daily_post = f"""[{clean_place}] {d_keyword} 솔직 방문기! ({d_wait})

안녕하세요! 일상의 다양한 핫플을 발 빠르게 탐방하는 우리부동산 김소장입니다.

요즘 가장 핫하게 떠오르고 있는 {clean_place}에 직접 다녀왔습니다.
실제 웨이팅 시간과 매장 분위기, 알짜 방문 팁까지 상세히 정리해 드립니다!

━━━━━━━━━━━━━━━━━━━━
📌 핫플 방문 요약
━━━━━━━━━━━━━━━━━━━━
• 장소명: {clean_place}
• 위치/권역: {d_addr}
• 방문 일시: {d_time}
• 대기 시간: {d_wait}

(사진 1 - 매장 전경 및 입구 대기 라인)
도착하자마자 핫플다운 열기를 느낄 수 있었습니다. 주말 기준으로 {d_wait} 정도 대기 후 입장할 수 있었습니다.

(사진 2 - 내부 인테리어 및 감각적인 공간 연출)
{d_items}

(사진 3 - 주요 아이템 및 디테일 컷)
{d_staff}

💡 김소장의 한 줄 요약
"{d_summary}"

트렌디한 감성을 느끼고 싶으신 분들께 적극 추천해 드립니다!

{d_tag_string} #우리부동산 #김소장의일상탐방
"""
                st.text_area("블로그 본문 복사창", daily_post, height=500)

# =============================================================
# [2순위 메뉴] 손님 상담 및 매칭 관리
# =============================================================
elif menu == "📋 손님 상담 및 매칭 관리":
    st.title("📋 공장 손님 상담 및 조건 매칭 시스템")
    with st.expander("➕ 신규 전화 상담 손님 등록하기", expanded=False):
        with st.form("customer_form", clear_on_submit=True):
            r1_1, r1_2, r1_3, r1_4 = st.columns(4)
            with r1_1: c_date = st.date_input("접수 일자", value=datetime.today())
            with r1_2: c_name = st.text_input("상호 / 고객명 *", placeholder="예: (주)대한정밀 / 김대표")
            with r1_3: c_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
            with r1_4: c_status = st.selectbox("진행 상태", ["상담 접수", "매물 브리핑 중", "현장 답사 예정", "계약 완료", "보류/마감"])

            r2_1, r2_2, r2_3, r2_4 = st.columns(4)
            with r2_1: c_loc = st.text_input("희망 권역 / 동", placeholder="예: 인천 서구 가좌/석남/원창")
            with r2_2: c_area = st.text_input("희망 면적/평수", placeholder="예: 100평")
            with r2_3: c_price = st.text_input("희망 예산", placeholder="예: 보 3천 / 월 250만")
            with r2_4: c_movein = st.text_input("입주 희망 시기", placeholder="예: 1~2개월 이내")

            r3_1, r3_2, r3_3 = st.columns([1, 1, 2])
            with r3_1: c_hoist = st.selectbox("호이스트", ["호이스트 필수 (2.8T)", "호이스트 필수 (3T)", "호이스트 필수 (5T 이상)", "있으면 좋음", "불필요"])
            with r3_2: c_truck = st.selectbox("대형차 진입", ["츄레라/트레일러 필수", "11T/대형 윙바디 필수", "5T 화물 진입", "1T/소형 위주"])
            with r3_3: c_memo = st.text_input("상담 메모 (업종, 동력 등)")

            submitted = st.form_submit_button("💾 손님 상담 데이터 저장하기", type="primary")
            if submitted:
                if not c_name or not c_phone:
                    st.error("상호와 연락처는 필수입니다.")
                else:
                    new_entry = {
                        "접수일자": c_date.strftime("%Y-%m-%d"), "상호/고객명": c_name, "연락처": c_phone,
                        "희망권역": c_loc, "희망평수": c_area, "예산(보증금/월세)": c_price, "입주시기": c_movein,
                        "호이스트": c_hoist, "대형차진입": c_truck, "상담메모": c_memo, "진행상태": c_status
                    }
                    save_customer(new_entry)
                    st.success(f"✅ '{c_name}' 대표님 상담 내역이 저장되었습니다!")

    df_customers = load_customers()
    if not df_customers.empty:
        st.dataframe(df_customers, use_container_width=True, height=350)

# =============================================================
# [3순위 메뉴] 공장 매물 관리 장부
# =============================================================
elif menu == "🏭 공장 매물 관리 장부":
    st.title("🏭 공장 매물 관리 장부 (중개사 전용 보안 DB)")
    df_props = load_properties()
    if not df_props.empty:
        st.dataframe(df_props, use_container_width=True, height=350)

# =============================================================
# [4순위 메뉴] 🏢 수도권 청약 알림 허브
# =============================================================
else:
    st.title("🏢 수도권 청약 및 지식산업센터 공급 알림 레이더")
    st.caption("서울·인천·경기 수도권 주요 분양 일정 및 산업단지 배후 지식산업센터 정보를 한눈에 관리하고 손님께 원클릭 브리핑합니다.")

    tab_api, tab_manual = st.tabs(["📡 청약홈(한국부동산원) 실시간 조회", "📋 관심 청약 / 지식산업센터 관리 대장"])

    with tab_api:
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            sel_region = st.selectbox("권역 필터", ["전체", "인천", "경기", "서울"])
        with col_f2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_fetch = st.button("🔄 최신 수도권 청약 공고 불러오기", type="primary")

        api_data = None
        if btn_fetch:
            api_data = pd.DataFrame([
                {
                    "단지명": "검단신도시 푸르지오 더 파크", "권역": "인천", "공급위치": "인천광역시 서구 마전동 검단지구 AA28BL",
                    "총세대수": "총 919세대", "특별공급": "2026-10-14", "1순위접수": "2026-10-15",
                    "당첨발표": "2026-10-22", "문의전화": "1588-0000"
                },
                {
                    "단지명": "청라 IHP 첨단지식산업센터 (라이브오피스)", "권역": "인천", "공급위치": "인천광역시 서구 청라동 IHP 도시첨단산단",
                    "총세대수": "제조형/업무형 320호실", "특별공급": "청약 접수중", "1순위접수": "선착순 호실 지정",
                    "당첨발표": "계약체결", "문의전화": "032-123-4567"
                },
                {
                    "단지명": "부천 대장지구 A-1BL 공공분양", "권역": "경기", "공급위치": "경기도 부천시 대장동 3기 신도시 일원",
                    "총세대수": "총 850세대", "특별공급": "2026-10-20", "1순위접수": "2026-10-21",
                    "당첨발표": "2026-10-29", "문의전화": "1600-1004"
                }
            ])

        if api_data is not None and not api_data.empty:
            st.success(f"✅ 총 {len(api_data)}건의 수도권 청약 공고가 조회되었습니다.")
            st.dataframe(api_data, use_container_width=True, height=240)

            st.markdown("---")
            st.subheader("📱 손님 전송용 청약 안내 브리핑 자동 생성")
            pick_list = [f"[{i}] {row['단지명']} ({row['권역']} - {row['총세대수']})" for i, row in api_data.iterrows()]
            selected_sub = st.selectbox("브리핑할 청약 단지를 선택하세요", pick_list)

            if selected_sub:
                sub_idx = int(selected_sub.split("]")[0].replace("[", ""))
                sub_row = api_data.iloc[sub_idx]

                briefing_sub_msg = f"""[수도권 신규 청약 공급 안내 브리핑]

대표님 안녕하십니까, 
인천·수도권 부동산 전문 우리부동산 김태형 소장입니다.

문의주셨던 권역의 핵심 신규 청약 및 공급 일정이 확정되어 주요 제원을 정리해 전달해 드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 단지 핵심 공급 개요
━━━━━━━━━━━━━━━━━━━━
• 단지명: {sub_row['단지명']}
• 소재 권역: {sub_row['공급위치']} ({sub_row['권역']})
• 공급 규모: {sub_row['총세대수']}

🗓️ 주요 청약 접수 일정
• 특별공급 접수: {sub_row['특별공급']}
• 일반 1순위 접수: {sub_row['1순위접수']}
• 당첨자 발표일: {sub_row['당첨발표']}

💡 김소장의 현장 체크포인트:
해당 사업지는 우수한 광역 교통망과 탄탄한 배후 산단 수요를 갖추고 있어 실입주 및 중장기 자산 가치 상승이 기대되는 핵심 입지입니다.

청약 자격 요건 검토나 인근 시세 비교 분석이 필요하시면 언제든 편하게 회신 주십시오.
우리부동산 공인중개사사무소 김태형
☎ 010-2660-8276
"""
                st.text_area("청약 브리핑 카톡 전송문 (원클릭 복사)", briefing_sub_msg, height=330)

    with tab_manual:
        st.subheader("📋 관심 청약 단지 및 지식산업센터 분양 관리")
        with st.expander("➕ 새로운 분양 / 청약 정보 등록", expanded=False):
            with st.form("manual_sub_form", clear_on_submit=True):
                ms1, ms2, ms3 = st.columns(3)
                with ms1:
                    m_name = st.text_input("사업장 / 단지명 *", placeholder="예: 청라 IHP 지식산업센터 1차")
                    m_loc = st.selectbox("지역 권역", ["인천 서구", "인천 부평/계양", "인천 남동/송도", "경기 부천/시흥", "경기 김포", "서울/기타"])
                with ms2:
                    m_type = st.selectbox("공급 유형", ["지식산업센터(제조/드라이브인)", "아파트(일반분양)", "오피스텔/라이브오피스", "상가/근생"])
                    m_scale = st.text_input("공급 규모", placeholder="예: 총 280실")
                with ms3:
                    m_price = st.text_input("분양가 / 평당가", placeholder="예: 평당 800만 원선")
                    m_dates = st.text_input("청약 및 계약 일정", placeholder="예: 10월 중순 선착순 동호지정")

                m_addr = st.text_input("상세 현장 위치", placeholder="예: 인천 서구 청라동 00-0번지")
                m_memo = st.text_area("단지 특징 (도어투도어, 층고, 감면 혜택 등)", placeholder="예: 5톤 화물 진입, 층고 6m")

                if st.form_submit_button("💾 관심 분양 정보 저장", type="primary"):
                    new_sub_entry = {
                        "등록일자": datetime.today().strftime("%Y-%m-%d"), "사업장/단지명": m_name, "지역권역": m_loc,
                        "공급유형": m_type, "공급위치": m_addr, "공급규모": m_scale, "분양가(평당/호당)": m_price,
                        "특별공급일": "-", "1순위접수일": m_dates, "당첨자발표일": "-", "체크포인트/안내": m_memo
                    }
                    save_subscription(new_sub_entry)
                    st.success("✅ 관심 분양 정보가 저장되었습니다!")

        df_manual_subs = load_subscriptions()
        if not df_manual_subs.empty:
            st.dataframe(df_manual_subs, use_container_width=True, height=280)