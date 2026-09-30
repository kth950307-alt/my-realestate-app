import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

st.set_page_config(page_title="우리부동산 통합 업무 시스템", page_icon="🏢", layout="wide")

# 번역 방지 및 스타일
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
# CSV 파일 관리 함수 (손님 DB & 매물 DB)
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        return pd.read_csv(CUSTOMERS_CSV)
    else:
        columns = [
            "접수일자", "상호/고객명", "연락처", "희망권역", "희망평수", 
            "예산(보증금/월세)", "입주시기", "호이스트", "대형차진입", "상담메모", "진행상태"
        ]
        return pd.DataFrame(columns=columns)

def save_customer(new_data):
    df = load_customers()
    new_df = pd.DataFrame([new_data])
    updated_df = pd.concat([new_df, df], ignore_index=True)
    updated_df.to_csv(CUSTOMERS_CSV, index=False, encoding="utf-8-sig")
    return updated_df

def load_properties():
    if os.path.exists(PROPERTIES_CSV):
        df = pd.read_csv(PROPERTIES_CSV)
        if "입주/공실상태" not in df.columns:
            df["입주/공실상태"] = "현재 공실(즉시입주)"
        if "계약만료일" not in df.columns:
            df["계약만료일"] = "즉시 협의"
        return df
    else:
        columns = [
            "등록일자", "입주/공실상태", "계약만료일", "거래구분", "소재지(권역)", "상세주소(지번)", "임대인(건물주)", "임대인연락처",
            "가격(보/월)", "면적", "층고", "동력", "호이스트", "도로/주차", "대형차량", "특징메모"
        ]
        return pd.DataFrame(columns=columns)

def save_property(new_data):
    df = load_properties()
    new_df = pd.DataFrame([new_data])
    updated_df = pd.concat([new_df, df], ignore_index=True)
    updated_df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")
    return updated_df

def update_entire_properties(df):
    df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")

def parse_pyung_numbers(text):
    if not text or pd.isna(text):
        return []
    nums = re.findall(r'\d+', str(text))
    valid_nums = [float(n) for n in nums if 5 <= float(n) <= 5000]
    return valid_nums

def find_matching_customers(loc, hoist_spec, truck_spec, factory_area_text=""):
    df = load_customers()
    if df.empty:
        return pd.DataFrame()
    
    active_df = df[~df["진행상태"].isin(["계약 완료", "보류/마감"])].copy()
    if active_df.empty:
        return pd.DataFrame()

    matched_indices = []

    if any(k in truck_spec for k in ["츄레라", "트레일러"]):
        factory_truck_level = 4
    elif any(k in truck_spec for k in ["11T", "11톤", "윙바디"]):
        factory_truck_level = 3
    elif any(k in truck_spec for k in ["5T", "5톤"]):
        factory_truck_level = 2
    else:
        factory_truck_level = 1

    factory_has_hoist = any(k in hoist_spec for k in ["완비", "설치", "톤", "T", "더블거더"]) and ("없음" not in hoist_spec)
    factory_pyungs = parse_pyung_numbers(factory_area_text)
    f_pyung = factory_pyungs[0] if factory_pyungs else None

    for idx, row in active_df.iterrows():
        c_loc = str(row["희망권역"]) if pd.notna(row["희망권역"]) else ""
        c_hoist = str(row["호이스트"]) if pd.notna(row["호이스트"]) else ""
        c_truck = str(row["대형차진입"]) if pd.notna(row["대형차진입"]) else ""
        c_area = str(row["희망평수"]) if pd.notna(row["희망평수"]) else ""

        loc_words = [w for w in loc.replace("(", " ").replace(")", " ").split() if len(w) >= 2]
        loc_match = (not c_loc.strip()) or any(w in c_loc for w in loc_words) or (c_loc in loc)
        if not loc_match:
            continue

        if any(k in c_truck for k in ["츄레라", "트레일러"]):
            cust_truck_level = 4
        elif any(k in c_truck for k in ["11T", "11톤", "윙바디"]):
            cust_truck_level = 3
        elif any(k in c_truck for k in ["5T", "5톤"]):
            cust_truck_level = 2
        else:
            cust_truck_level = 1

        if factory_truck_level < cust_truck_level:
            continue

        if ("필수" in c_hoist) and (not factory_has_hoist):
            continue

        cust_pyungs = parse_pyung_numbers(c_area)
        if f_pyung and cust_pyungs:
            c_min = min(cust_pyungs) - 60
            c_max = max(cust_pyungs) + 60
            if not (c_min <= f_pyung <= c_max):
                continue

        matched_indices.append(idx)

    return active_df.loc[matched_indices]

# =============================================================
# 사이드바 메뉴 (순서 변경: 글쓰기 -> 손님 -> 매물장부)
# =============================================================
menu = st.sidebar.radio(
    "📌 업무 메뉴 선택",
    [
        "✍️ 공장물건 글쓰기 (블로그/카톡)",
        "📋 손님 상담 및 매칭 관리",
        "🏭 공장 매물 관리 장부"
    ],
    index=0  # 접속 시 첫 화면을 공장물건 글쓰기로 고정
)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 사진 분석 엔진")
api_key = st.sidebar.text_input("Gemini API Key (선택)", type="password", help="API 키를 넣으면 AI가 사진을 직접 분석하여 글을 작성합니다.")

# =============================================================
# [1순위 메뉴] 공장물건 글쓰기 (블로그 & 카카오톡 생성)
# =============================================================
if menu == "✍️ 공장물건 글쓰기 (블로그/카톡)":
    st.title("✍️ 공장물건 글쓰기 및 원스톱 생성기")
    category = st.radio("작성할 카테고리를 선택하세요", ["🏭 공장 매물 브리핑", "🍜 맛집 솔직 후기", "🧢 일상 핫플 탐방"], horizontal=True)

    if category == "🏭 공장 매물 브리핑":
        st.subheader("🏭 공장 매물 정보 입력")

        with st.expander("🔒 [중개사 비밀 관리용] 상세 지번 및 건물주 연락처 (블로그 글 미포함)", expanded=True):
            sec1, sec2, sec3 = st.columns(3)
            with sec1:
                secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 123-4번지 1층")
            with sec2:
                owner_name = st.text_input("👤 건물주(임대인) 성함 (비공개)", placeholder="예: 홍길동 회장님")
            with sec3:
                owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-9999-8888")

        st.markdown("##### 📌 기본 거래 조건 및 입주 상태")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            loc = st.text_input("소재지 / 동 (블로그 노출용)", placeholder="예: 인천 제물포구 송현동 (구 동구)")
        with b2:
            deal_type = st.selectbox("거래 구분 *", ["임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)", "직접 입력"])
            if deal_type == "직접 입력":
                deal_type = st.text_input("거래 구분 직접 기입", placeholder="예: 1층 100평 중 40평 분할 전대차")
        with b3:
            vacancy_status = st.selectbox("입주 / 공실 상태 *", ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "건물주 사용중(협의)", "신축 첫입주"])
        with b4:
            expire_date = st.text_input("계약만료일 / 입주협의일", value="즉시 입주 가능 (상호 협의)", placeholder="예: 2026-12-31 만기 / 즉시입주 협의")

        c1, c2, c3 = st.columns(3)
        with c1:
            price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 1,000만 원 / 월세 100만 원 (또는 매매 15억)")
            area = st.text_input("면적 (대지/건물/실사용) *", placeholder="예: 바닥 150평 (작업장 140평 + 사무실 10평)")
        with c2:
            ceiling = st.text_input("층고 (처마/유효)", placeholder="예: 처마 7m / 유효 8m 하이 층고")
            power = st.text_input("동력 (전기 용량 kW)", placeholder="예: 제조 동력 30kW (단독 분전반 완비)")
            hoist = st.selectbox("호이스트 유 / 무", [
                "호이스트 크레인 완비 (3T)",
                "호이스트 크레인 완비 (5T)",
                "호이스트 크레인 완비 (2.8T)",
                "호이스트 크레인 완비 (10T)",
                "더블거더 크레인 완비",
                "호이스트 없음",
                "직접 입력"
            ])
            if hoist == "직접 입력":
                hoist = st.text_input("호이스트 스펙 직접 기입", placeholder="예: 2.8톤 2기 설치")
        with c3:
            road = st.text_input("진입 도로 여건 (직접 입력)", placeholder="예: 8m 도로 접 / 코너 각지 도로 / 12m 대도로변")
            parking = st.selectbox("주차 대수", ["1대", "2대", "3대", "4대", "5대 이상 가능", "단독 마당 10대 이상", "공용 주차 협의"])
            big_truck = st.selectbox("대형차량 작업 여부 *", [
                "츄레라 / 트레일러 진출입 및 상하차 원활",
                "11T / 대형 윙바디 접안 원활",
                "5T 화물차 문 앞 상하차 수월",
                "1T / 소형 화물차 최적화",
                "직접 입력"
            ])
            if big_truck == "직접 입력":
                big_truck = st.text_input("대형차량 여건 직접 기입")

        c4, c5 = st.columns(2)
        with c4:
            sub = st.text_input("출입문 및 부속시설", placeholder="예: 대형 반출입 도어, 약 5평 사무실, 건물 위생시설")
            industry = st.text_input("추천 업종", placeholder="예: 정밀 금속 가공, 기계 조립 및 수리, 물류 유통 거점")
        with c5:
            memo = st.text_area("특징 및 입지 메모", placeholder="예: 인천산업유통센터 인접, 빠른 외주 가공망 연계, 바닥 에폭시 신규 시공")

        st.markdown("##### 📸 공장 현장 사진 첨부 (다중 선택 가능)")
        factory_images = st.file_uploader("공장 사진을 올려주세요", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="factory_img")
        
        if factory_images:
            cols = st.columns(min(len(factory_images), 4))
            for idx, img_file in enumerate(factory_images):
                with cols[idx % 4]:
                    st.image(img_file, caption=f"사진 {idx+1}: {img_file.name}", use_container_width=True)

        if st.button("🚀 공장 매물 생성하기 (매물저장 + 블로그글 + 카톡브리핑문)", type="primary"):
            clean_loc = loc if loc else "인천 제물포구 송현동"
            road_clean = road if road else "도로망 양호"
            road_parking_summary = f"{road_clean}, 주차 {parking}, {big_truck}"

            new_prop_entry = {
                "등록일자": datetime.today().strftime("%Y-%m-%d"),
                "입주/공실상태": vacancy_status,
                "계약만료일": expire_date,
                "거래구분": deal_type,
                "소재지(권역)": clean_loc,
                "상세주소(지번)": secret_address,
                "임대인(건물주)": owner_name,
                "임대인연락처": owner_phone,
                "가격(보/월)": price,
                "면적": area,
                "층고": ceiling,
                "동력": power,
                "호이스트": hoist,
                "도로/주차": f"{road_clean} / {parking}",
                "대형차량": big_truck,
                "특징메모": memo
            }
            save_property(new_prop_entry)
            st.success(f"✅ 매물이 '공장 매물 관리 장부'에 성공적으로 누적 저장되었습니다! (상태: {vacancy_status})")

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
            else:
                st.markdown("---")
                st.caption("ℹ️ 현재 등록된 손님 중 위 조건과 일치하는 대기 손님은 없습니다.")

            kakao_briefing = f"""[신규 공장 매물 브리핑 안내]

대표님 안녕하십니까, 
인천 산업단지 공장·창고 전문 우리부동산 김태형 소장입니다.

찾으시던 조건에 부합하는 알짜 신규 공장 매물이 접수되어 먼저 브리핑 안내드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 매물 핵심 제원 요약
━━━━━━━━━━━━━━━━━━━━
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
• 부대시설: {sub}

💡 현장 핵심 포인트 & 추천
• {memo}
• 추천 업종: {industry}

시세 대비 경쟁력 있는 조건으로 신규 공급된 사업장으로, 빠른 계약 진행이 예상되는 물건입니다.
현장 답사나 세부 도면 검토가 필요하시면 편하게 회신 주십시오. 현장 안내 바로 도와드리겠습니다.

우리부동산 공인중개사사무소
대표 공인중개사 김태형
☎ 010-2660-8276
"""
            st.markdown("---")
            st.subheader("📱 손님 카카오톡 / 문자 원클릭 전송문 (원클릭 복사)")
            st.text_area("카톡 브리핑 복사창", kakao_briefing, height=370)

            st.markdown("---")
            st.subheader("📝 네이버 블로그 포스팅용 본문")
            
            if api_key and GENAI_AVAILABLE and factory_images:
                with st.spinner("AI가 현장 사진과 조건을 분석하여 맞춤 글을 작성 중입니다..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        pil_images = [Image.open(img) for img in factory_images]
                        ai_prompt = f"""
너는 인천 공장·창고 전문 '우리부동산'의 대표 공인중개사 김태형(김소장)이야.
아래 제공된 [공장 매물 조건]과 [첨부된 실제 현장 사진들]을 직접 눈으로 정밀하게 분석해서 네이버 블로그 상위 노출 규격으로 작성해줘.
소재지: {clean_loc}, 거래: {deal_type}, 가격: {price}, 입주: {vacancy_status}({expire_date}), 면적: {area}, 층고: {ceiling}, 동력: {power}, 호이스트: {hoist}, 도로/주차: {road_parking_summary}, 부속시설: {sub}, 추천업종: {industry}, 메모: {memo}
주의: 상세 지번이나 건물주 개인정보는 절대 언급하지 말고 대표 공인중개사 김태형 연락처(010-2660-8276)로 마무리할 것.
"""
                        contents = [ai_prompt] + pil_images
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
                        st.success("✨ AI가 사진을 직접 분석하여 맞춤 브리핑 글을 완성했습니다!")
                        st.text_area("블로그 본문 복사하기", response.text, height=600)
                    except Exception as e:
                        st.error(f"AI 호출 에러: {e}")
            else:
                post = f"""[{clean_loc} 공장 {deal_type.split('(')[0]}] {hoist} & 입주협의! {deal_type} ({price}, {area}, {road_parking_summary})
안녕하십니까. 인천 산업단지 공장·창고 전문 우리부동산입니다.

{clean_loc} 공업지역 내에서 {hoist} 설비를 완비한 1층 사업장을 {price} 조건으로 확보하는 것은 대단히 드문 기회입니다.

{memo} 배후 권역에서 소형 면적 제조 작업장을 물색해 보시면, 소형 면적 특성상 평당 단가가 높아 월 차임이 150만 원을 상회하거나 마땅한 물건 자체가 드물어 사옥 이전에 고심하시는 대표님들이 많습니다. 오늘 소개해 드리는 사업장은 {clean_loc} 소재 {deal_type} 건으로, {price}이라는 주변 시세 대비 매우 합리적인 조건으로 공급됩니다.

무엇보다 {vacancy_status} 상태로 {expire_date} 조건에 맞춰 안정적으로 조업 일정을 잡으실 수 있습니다. 도로 및 진출입 여건 또한 양호하여 {road_clean} 여건과 주차 {parking}, {big_truck} 조건을 갖추어 원자재 및 완제품의 상하차 작업성이 우수합니다.   

실사용 공간은 {area} 구조로 효율적으로 구성되어 있습니다. 공장 상부에는 중량물 인양과 하역에 필수적인 {hoist} 설비가 견고하게 설치되어 있으며, 충분한 제조 전력 인입과 더불어 {power} 인프라가 갖추어져 있어 전기 요금의 투명하고 명확한 실비 정산이 가능합니다. {industry} 등으로 초기 고정 투자 비용을 최소화하고자 하시는 대표님들께 적극 추천해 드립니다.   

먼저 본 매물의 상세 제원을 표로 안내해 드립니다.

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
관리비 정산 | 실비 정산 (개별 계량기 기준)

📌 매물 핵심 특징
✅ {clean_loc} 공장
• 실사용 면적: {area}
• 층고: {ceiling}
• 동력: {power}
• 도로 및 주차: {road_clean} / 주차 {parking}
• 대형차량 여건: {big_truck}
• 계약 형태: {deal_type}
• 인양 설비: {hoist}
• 부속 시설: {sub}
• 입주 현황: {vacancy_status} ({expire_date})

✅ {clean_loc} 사업장을 {price} 조건으로 운용하는 탁월한 경제성
✅ {vacancy_status} 상태로 일정 조율 용이
✅ {hoist} 기본 구비로 철골 구조물 보강 및 크레인 신설 비용 대폭 절감
✅ {power} 구축으로 전력 사용량 분쟁 없는 투명한 계량 정산 실현
✅ 사무 공간을 확보하여 행정 및 전산 업무 원활
✅ {memo} 입지로 신속한 원자재 수급 및 외주 가공망 연계
✅ {industry} 적극 추천

(사진 1 - 메인 조업 공간 내부 전경 및 호이스트 크레인 설비)
1층 메인 조업 공간 내부 전경입니다.
상부 철골 트러스 골조를 따라 {hoist} 설비가 견고하게 설치되어 있습니다. 공실 공장에 신규로 H빔을 보강하고 크레인을 가설할 경우 수천만 원 상당의 막대한 초기 자본이 소요되는 점을 감안할 때, 본 시설을 그대로 활용함으로써 초기 설비 투자 비용을 대폭 절감할 수 있는 뚜렷한 강점을 지닙니다.   

(사진 2 - 상부 층고 체적 및 주행 레일 구간)
천장 골조 및 여유로운 층고 체적입니다.
{ceiling} 구조로 유효 층고가 높아 부피가 큰 공작 기계의 안착은 물론, 중량 랙을 설치하여 자재를 다단 적재하기에 쾌적한 공간 활용성을 갖추고 있습니다.   

(사진 3 - 내부 중앙 작업 통로 및 적재 설비 구간)
작업장 내부 메인 물류 통로입니다.
중앙 통로 폭이 반듯하게 구획되어 있어 이동식 대차를 활용한 중량물 운반 시 작업 동선의 간섭이 발생하지 않으며, 전용 제조 구역으로 집중 활용하기에 최적화되어 있습니다.   

(사진 4 - 전력 설비 및 가공 작업대 라인)
벽면 라인 및 전력 인입 구역입니다.
{power} 환경이 완비되어 있어, 타 구역과의 전력 요금 갈등 없이 실사용량에 대한 정확하고 합리적인 정산이 가능합니다.   

(사진 5 - 물류 하역 라인 및 자재 출입문 연계 구역)
출입구 방향에서 바라본 물류 하역 구역입니다.
{road_clean} 여건과 주차 {parking}, {big_truck} 조건을 갖추어 화물 트럭이 문 앞까지 안정적으로 접근할 수 있으며, 출입구 인근에서 곧바로 중량물을 인양해 내부로 이송할 수 있어 상하차 효율이 매우 뛰어납니다.   

(사진 6 - 사무실 내부 및 부속시설 전경)
현장 한편에 별도로 마련된 사무 공간입니다.
{sub} 여건을 갖추어 현장 소음 및 분진과 분리되어 도면 검토, 수주 및 발주 관리, 세금계산서 발행 및 내방객 응대 업무를 안정적으로 수행하실 수 있습니다.   

{clean_loc} 공업지역 중심부에서 뛰어난 인프라와 {hoist}, {power} 조건을 갖추고 {price} 조건으로 확보할 수 있는 매물은 매우 희소합니다.
고정 임대료 지출을 최소화하고 즉시 조업에 착수하고자 하시는 대표님들께서는 유선 문의 후 현장을 직접 확인해 보시기 바랍니다.

우리부동산 공인중개사사무소
대표 공인중개사 김태형
010-2660-8276

기업의 성공적인 도약을 돕는 든든한 부동산 파트너가 되겠습니다.
정직과 전문성을 바탕으로 책임 중개하겠습니다.

#인천공장임대 #소형공장임대 #{clean_loc.replace(' ', '')}공장임대 #인천호이스트공장 #인천산업단지공장 #우리부동산 #책임중개

💡 사진 하단에 활용 가능한 전문 코멘트집
- [입주 상태 관점] {vacancy_status} 상태로, {expire_date} 일정에 맞추어 설비 반입 및 라인 배치를 여유 있게 조율하실 수 있습니다.
- [고정비 절감 관점] 주변 시세 대비 {price} 조건으로 운용할 수 있어 고정 운영비 부담을 실질적으로 낮출 수 있습니다.
- [호이스트 설비 관점] 상단 골조에 {hoist} 설비가 기본 장착되어 있어 중량물 인양·적재 작업을 인력 소모 없이 안전하게 수행할 수 있습니다.
- [단독 분전반 전력 계량 관점] {power} 환경이 구축되어 있어 타 사업장과의 전력 분쟁 없이 투명하게 실비 정산할 수 있습니다.
- [사무실 인프라 관점] 전용 작업장 외에 사무 공간을 확보하여 현장 작업과 분리된 환경에서 도면 분석, 수주 행정, 전산 업무를 원활히 처리하실 수 있습니다.
"""
                st.text_area("블로그 본문 복사하기", post, height=550)

    elif category == "🍜 맛집 솔직 후기":
        st.subheader("🍜 맛집 방문 정보 입력")
        m1, m2, m3 = st.columns(3)
        with m1:
            m_name = st.text_input("식당 상호명", placeholder="예: 메탄집 청라본점")
            m_keyword = st.text_input("타이틀 수식어", placeholder="예: 35년 전통의 깊은 내공! 연탄불향 불고기")
            m_addr = st.text_input("매장 주소", placeholder="예: 인천 서구 청라동 190-3")
        with m2:
            m_time = st.text_input("영업시간 / 휴무", placeholder="예: 매일 11:30 ~ 24:00 (월요일 휴무)")
            m_parking = st.text_input("주차 정보", placeholder="예: 매장 앞 전면 주차 가능")
            m_feature = st.text_input("매장 특징", placeholder="예: 35년 전통 직영점, 연탄 직화구이")
        with m3:
            m_vibe = st.text_input("외관 및 분위기", placeholder="예: 노란 간판, 옛 포차 감성")
            m_order = st.text_input("주문 메뉴 및 가격", placeholder="예: 점심 2인 특선 25,000원")
            m_summary = st.text_input("김소장의 솔직 총평", placeholder="예: 가성비 극강 맛집")
        m_dish = st.text_area("메인 요리 맛 평가 (고기 등)", placeholder="맛 평가 메모...")
        m_noodle = st.text_area("식사/면류 맛 평가", placeholder="식사류 평가 메모...")
        if st.button("🚀 맛집 후기 생성하기"):
            clean_name = m_name if m_name else "추천 맛집"
            food_post = f"[{clean_name}] {m_keyword} 솔직후기\n\n위치: {m_addr}\n메뉴: {m_order}\n\n{m_dish}\n\n{m_noodle}\n\n총평: {m_summary}"
            st.text_area("결과 복사", food_post, height=500)

    else:
        st.subheader("🧢 일상 핫플 탐방 정보 입력")
        d1, d2, d3 = st.columns(3)
        with d1:
            d_place = st.text_input("핫플 장소/브랜드명", placeholder="예: 스투시 서울 챕터")
            d_title = st.text_input("제목 키워드", placeholder="예: 첫 방문기! 일요일 웨이팅 40분 솔직 후기")
            d_addr = st.text_input("위치/주소", placeholder="예: 서울 강남구 신사동 (도산공원 인근)")
        with d2:
            d_time = st.text_input("방문일시 / 영업시간", placeholder="예: 일요일 오후 2시 방문")
            d_wait = st.text_input("웨이팅 현황", placeholder="예: 현장 스탠딩 약 40분 대기")
            d_compare = st.text_input("인기 체감 비교", placeholder="예: 슈프림 대비 대기 줄 길고 외국인 관람객 많음")
        with d3:
            d_summary = st.text_input("김소장의 한 줄 요약", placeholder="예: 40분 웨이팅이 아깝지 않은 스트릿 패션의 성지!")
        d_items = st.text_area("내부 인테리어 및 아이템", placeholder="아이템 메모...")
        d_staff = st.text_area("직원 분위기 체감", placeholder="직원 평가 메모...")
        if st.button("🚀 일상 후기 생성하기"):
            clean_place = d_place if d_place else "핫플레이스"
            daily_post = f"[{clean_place}] {d_title}\n\n위치: {d_addr}\n대기: {d_wait}\n\n{d_items}\n\n{d_staff}\n\n한 줄 요약: {d_summary}"
            st.text_area("결과 복사", daily_post, height=500)

# =============================================================
# [2순위 메뉴] 손님 상담 및 매칭 관리
# =============================================================
elif menu == "📋 손님 상담 및 매칭 관리":
    st.title("📋 공장 손님 상담 및 조건 매칭 시스템")
    st.markdown("전화 상담 시 조건(평수, 월세, 호이스트, 대형차 진입 등)을 즉시 기록하고 보관하세요.")

    with st.expander("➕ 신규 전화 상담 손님 등록하기 (클릭)", expanded=False):
        with st.form("customer_form", clear_on_submit=True):
            r1_1, r1_2, r1_3, r1_4 = st.columns(4)
            with r1_1:
                c_date = st.date_input("접수 일자", value=datetime.today())
            with r1_2:
                c_name = st.text_input("상호 / 고객명 *", placeholder="예: (주)대한정밀 / 김대표")
            with r1_3:
                c_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
            with r1_4:
                c_status = st.selectbox("진행 상태", ["상담 접수", "매물 브리핑 중", "현장 답사 예정", "계약 완료", "보류/마감"])

            r2_1, r2_2, r2_3, r2_4 = st.columns(4)
            with r2_1:
                c_loc = st.text_input("희망 권역 / 동", placeholder="예: 인천 서구 가좌/석남/송현")
            with r2_2:
                c_area = st.text_input("희망 면적/평수 (숫자 기입 권장)", placeholder="예: 100평 또는 100~150평")
            with r2_3:
                c_price = st.text_input("희망 예산 (보증금/월세)", placeholder="예: 보 3천 / 월 250만 이하")
            with r2_4:
                c_movein = st.text_input("입주 희망 시기", placeholder="예: 1~2개월 이내 협의 / 즉시")

            r3_1, r3_2, r3_3 = st.columns([1, 1, 2])
            with r3_1:
                c_hoist = st.selectbox("호이스트 필요 여부 *", ["호이스트 필수 (2.8T)", "호이스트 필수 (3T)", "호이스트 필수 (5T 이상)", "있으면 좋음", "불필요"])
            with r3_2:
                c_truck = st.selectbox("대형차 작업 여부 *", ["츄레라/트레일러 필수", "11T/대형 윙바디 필수", "5T 화물 진입", "1T/소형 위주"])
            with r3_3:
                c_memo = st.text_input("상담 메모 (업종, 동력 kW, 층고 등)", placeholder="예: 금속 절단 가공, 동력 50kW 이상, 처마 층고 7m 이상 희망")

            submitted = st.form_submit_button("💾 손님 상담 데이터 저장하기", type="primary")
            if submitted:
                if not c_name or not c_phone:
                    st.error("상호(고객명)와 연락처는 필수 입력 항목입니다.")
                else:
                    new_entry = {
                        "접수일자": c_date.strftime("%Y-%m-%d"),
                        "상호/고객명": c_name,
                        "연락처": c_phone,
                        "희망권역": c_loc,
                        "희망평수": c_area,
                        "예산(보증금/월세)": c_price,
                        "입주시기": c_movein,
                        "호이스트": c_hoist,
                        "대형차진입": c_truck,
                        "상담메모": c_memo,
                        "진행상태": c_status
                    }
                    save_customer(new_entry)
                    st.success(f"✅ '{c_name}' 대표님 상담 내역이 저장되었습니다!")

    st.markdown("---")
    st.subheader("🏭 보유 매물 조건으로 적합 손님 즉석 찾기")
    st.caption("공장 물건이 나왔을 때, 조건을 넣으면 ±60평 오차범위 및 호이스트·차량 상위호환에 맞는 손님을 즉시 찾아줍니다.")
    
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        q_loc = st.text_input("매물 위치 (동)", value="인천", placeholder="예: 송현동 / 가좌동 / 인천")
    with qc2:
        q_area = st.text_input("매물 평수 (평)", value="100", placeholder="예: 100")
    with qc3:
        q_hoist = st.selectbox("매물 호이스트", ["호이스트 크레인 완비 (3T)", "호이스트 크레인 완비 (5T)", "호이스트 크레인 완비 (2.8T)", "호이스트 없음"], index=0)
    with qc4:
        q_truck = st.selectbox("매물 진출입 여건", ["츄레라 / 트레일러 진출입 및 상하차 원활", "11T / 대형 윙바디 접안 원활", "5T 화물차 문 앞 상하차 수월", "1T / 소형 화물차"], index=0)

    if st.button("🔎 이 매물에 맞는 손님 실시간 검색", type="primary"):
        quick_matches = find_matching_customers(q_loc, q_hoist, q_truck, q_area)
        if not quick_matches.empty:
            st.success(f"🎯 총 {len(quick_matches)}명의 추천 손님을 찾았습니다! (평수 ±60평 적용)")
            for _, cust in quick_matches.iterrows():
                st.markdown(f"""
                <div class="compact-match-card">
                    <div class="compact-match-title">👤 {cust['상호/고객명']} ({cust['연락처']}) <span class="badge-status">{cust['진행상태']}</span></div>
                    • <b>희망지역</b>: {cust['희망권역']} | 📐 <b>희망평수</b>: {cust['희망평수']} | 💰 <b>예산</b>: {cust['예산(보증금/월세)']} | 🗓️ <b>입주</b>: {cust['입주시기']}<br>
                    • <b>호이스트</b>: {cust['호이스트']} | 🚛 <b>차량작업</b>: {cust['대형차진입']} | 📝 <b>메모</b>: {cust['상담메모']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("현재 입력하신 매물 조건과 일치하는 대기 손님이 없습니다.")

    st.markdown("---")
    st.subheader("📋 등록된 손님 목록 및 맞춤 조건 검색")

    df_customers = load_customers()
    if df_customers.empty:
        st.info("등록된 손님 데이터가 없습니다.")
    else:
        f1, f2, f3 = st.columns(3)
        with f1:
            search_keyword = st.text_input("🔎 고객명 / 연락처 / 메모 / 동 검색", placeholder="검색어 입력...")
        with f2:
            filter_hoist = st.selectbox("호이스트 조건 필터", ["전체 보기", "호이스트 필수 (2.8T)", "호이스트 필수 (3T)", "호이스트 필수 (5T 이상)", "불필요"])
        with f3:
            filter_truck = st.selectbox("대형차 작업 조건 필터", ["전체 보기", "츄레라/트레일러 필수", "11T/대형 윙바디 필수", "5T 화물 진입"])

        filtered_df = df_customers.copy()
        if search_keyword:
            filtered_df = filtered_df[
                filtered_df["상호/고객명"].str.contains(search_keyword, na=False) |
                filtered_df["연락처"].str.contains(search_keyword, na=False) |
                filtered_df["상담메모"].str.contains(search_keyword, na=False) |
                filtered_df["희망권역"].str.contains(search_keyword, na=False)
            ]
        if filter_hoist != "전체 보기":
            filtered_df = filtered_df[filtered_df["호이스트"] == filter_hoist]
        if filter_truck != "전체 보기":
            filtered_df = filtered_df[filtered_df["대형차진입"] == filter_truck]

        st.caption(f"총 {len(filtered_df)}명의 손님이 검색되었습니다.")
        st.dataframe(filtered_df, use_container_width=True, height=320)

        csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 현재 손님 목록 엑셀(CSV) 다운로드",
            data=csv_data,
            file_name=f"공장손님리스트_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# =============================================================
# [3순위 메뉴] 공장 매물 관리 장부 (수정/삭제 완비)
# =============================================================
else:
    st.title("🏭 공장 매물 관리 장부 (중개사 전용 보안 DB)")
    st.markdown("매물 정보(지번, 임대인 전화번호, 가격, 상태)를 **자유롭게 수정하거나 삭제**할 수 있습니다.")

    df_props = load_properties()
    if df_props.empty:
        st.info("아직 저장된 공장 매물이 없습니다. '✍️ 공장물건 글쓰기'에서 매물을 등록하고 생성 버튼을 누르면 자동으로 여기에 저장됩니다.")
    else:
        sf1, sf2, sf3 = st.columns(3)
        with sf1:
            p_search = st.text_input("🔎 매물 통합 검색 (소재지, 지번, 임대인 등)", placeholder="검색어를 입력하세요...")
        with sf2:
            status_filter = st.selectbox("입주/공실 상태 필터", ["전체 보기", "현재 공실(즉시입주)", "현재 임대중(만기 전)", "계약 완료", "보류/마감"])
        with sf3:
            deal_filter = st.selectbox("거래구분 필터", ["전체 보기", "임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)"])

        filtered_props = df_props.copy()
        if p_search:
            filtered_props = filtered_props[
                filtered_props["소재지(권역)"].str.contains(p_search, na=False) |
                filtered_props["상세주소(지번)"].str.contains(p_search, na=False) |
                filtered_props["임대인(건물주)"].str.contains(p_search, na=False) |
                filtered_props["특징메모"].str.contains(p_search, na=False)
            ]
        if status_filter != "전체 보기":
            filtered_props = filtered_props[filtered_props["입주/공실상태"] == status_filter]
        if deal_filter != "전체 보기":
            filtered_props = filtered_props[filtered_props["거래구분"].str.contains(deal_filter, na=False)]

        st.caption(f"총 {len(filtered_props)}건의 매물이 표시 중입니다.")
        st.dataframe(filtered_props, use_container_width=True, height=300)

        st.markdown("---")
        st.subheader("🛠️ 매물 상세정보 수정 및 삭제")
        
        prop_options = [f"[{i}] {row['소재지(권역)']} ({row['상세주소(지번)']}) - {row['면적']} - 임대인: {row['임대인(건물주)']} ({row['임대인연락처']})" for i, row in df_props.iterrows()]
        selected_prop_str = st.selectbox("관리할 매물을 선택하세요", prop_options)
        
        if selected_prop_str:
            selected_idx = int(selected_prop_str.split("]")[0].replace("[", ""))
            curr = df_props.loc[selected_idx]

            tab_edit, tab_del = st.tabs(["✏️ 매물 정보 수정 (전화번호/가격/지번 등)", "🗑️ 매물 영구 삭제"])

            with tab_edit:
                with st.form("edit_property_form"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        new_owner_name = st.text_input("임대인(건물주) 성함", value=str(curr.get("임대인(건물주)", "")))
                        new_owner_phone = st.text_input("임대인(건물주) 연락처", value=str(curr.get("임대인연락처)", "")))
                    with e2:
                        new_sec_addr = st.text_input("상세 지번 / 호수", value=str(curr.get("상세주소(지번)", "")))
                        new_loc = st.text_input("소재지 / 권역", value=str(curr.get("소재지(권역)", "")))
                    with e3:
                        new_status = st.selectbox(
                            "입주/공실 상태",
                            ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "계약 완료", "보류/마감", "건물주 직영중"],
                            index=["현재 공실(즉시입주)", "현재 임대중(만기 전)", "계약 완료", "보류/마감", "건물주 직영중"].index(curr["입주/공실상태"]) if curr["입주/공실상태"] in ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "계약 완료", "보류/마감", "건물주 직영중"] else 0
                        )
                        new_expire = st.text_input("계약만료일 (입주협의일)", value=str(curr.get("계약만료일", "즉시 협의")))

                    e4, e5, e6 = st.columns(3)
                    with e4:
                        new_deal = st.text_input("거래 구분", value=str(curr.get("거래구분", "임대차(월세)")))
                        new_price = st.text_input("가격 (보증금/월세 또는 매매가)", value=str(curr.get("가격(보/월)", "")))
                    with e5:
                        new_area = st.text_input("면적 제원", value=str(curr.get("면적", "")))
                        new_hoist = st.text_input("호이스트 스펙", value=str(curr.get("호이스트", "")))
                    with e6:
                        new_truck = st.text_input("대형차량 여건", value=str(curr.get("대형차량", "")))
                        new_road = st.text_input("도로 / 주차", value=str(curr.get("도로/주차", "")))

                    new_memo = st.text_area("특징 메모", value=str(curr.get("특징메모", "")))

                    btn_save_edit = st.form_submit_button("💾 수정 내용 장부에 저장하기", type="primary")
                    if btn_save_edit:
                        df_props.at[selected_idx, "임대인(건물주)"] = new_owner_name
                        df_props.at[selected_idx, "임대인연락처"] = new_owner_phone
                        df_props.at[selected_idx, "상세주소(지번)"] = new_sec_addr
                        df_props.at[selected_idx, "소재지(권역)"] = new_loc
                        df_props.at[selected_idx, "입주/공실상태"] = new_status
                        df_props.at[selected_idx, "계약만료일"] = new_expire
                        df_props.at[selected_idx, "거래구분"] = new_deal
                        df_props.at[selected_idx, "가격(보/월)"] = new_price
                        df_props.at[selected_idx, "면적"] = new_area
                        df_props.at[selected_idx, "호이스트"] = new_hoist
                        df_props.at[selected_idx, "대형차량"] = new_truck
                        df_props.at[selected_idx, "도로/주차"] = new_road
                        df_props.at[selected_idx, "특징메모"] = new_memo

                        update_entire_properties(df_props)
                        st.success("✅ 매물 정보(임대인 번호, 가격 등)가 성공적으로 수정되었습니다!")
                        st.rerun()

            with tab_del:
                st.warning(f"선택하신 매물: [{curr['소재지(권역)']}] {curr['상세주소(지번)']} ({curr['면적']})")
                confirm_del = st.checkbox("위 매물을 장부에서 완전히 삭제하는 것에 동의합니다.")
                if st.button("🗑️ 매물 영구 삭제하기", type="secondary"):
                    if confirm_del:
                        df_props = df_props.drop(index=selected_idx).reset_index(drop=True)
                        update_entire_properties(df_props)
                        st.success("✅ 매물이 장부에서 안전하게 삭제되었습니다.")
                        st.rerun()
                    else:
                        st.error("삭제하시려면 위의 동의 체크박스에 먼저 체크해 주세요.")

        prop_csv = filtered_props.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 매물 관리 장부 엑셀(CSV) 다운로드",
            data=prop_csv,
            file_name=f"공장매물관리대장_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )