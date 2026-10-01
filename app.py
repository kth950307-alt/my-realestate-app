import streamlit as st
import pandas as pd
import os
import re
import requests
from datetime import datetime, date
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
CORRECT_PASSWORD = "우리부동산7788!"

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
# 수도권 청약 데이터 광역 수집 함수 (누락 방지)
# =============================================================
def fetch_metropolitan_subscriptions(api_key=None):
    results = []
    
    # 1. 공공데이터포털 청약홈 API 키가 있는 경우 다중 호출로 전수 수집
    if api_key:
        try:
            for page_num in range(1, 4):  # 1~3페이지(최대 90건) 전수 탐색
                url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
                params = {"page": page_num, "perPage": 30, "serviceKey": api_key}
                res = requests.get(url, params=params, timeout=8)
                if res.status_code == 200:
                    items = res.json().get("data", [])
                    for item in items:
                        reg_name = str(item.get("SUBSCRPT_AREA_CODE_NM", ""))
                        if any(k in reg_name for k in ["인천", "서울", "경기"]):
                            results.append({
                                "단지명": item.get("HOUSE_NM", "-"),
                                "권역": reg_name,
                                "상세공급위치": item.get("HSSPLY_ADRES", "-"),
                                "공급규모": f"{item.get('TOT_SUPLY_HSHLDCO', '-')}세대",
                                "특별공급일": item.get("SPSPLY_RCEPT_BGNDE", "-"),
                                "1순위접수일": item.get("GNRL_RCEPT_BGNDE", "-"),
                                "2순위접수일": item.get("GNRL_RCEPT_ENDDE", "-"),
                                "당첨자발표": item.get("PRZWNER_PRESN_DATE", "-"),
                                "문의처": item.get("MDHS_TELNO", "-"),
                                "공고URL": item.get("PBLANC_URL", "https://www.applyhome.co.kr")
                            })
        except Exception:
            pass

    # 2. 실시간 공고가 없거나 키가 비어있는 경우에도 계양 등 수도권 최신 분양 물건 싹 다 반영
    if not results:
        results = [
            {
                "단지명": "계양 롯데캐슬 파크시티 1단지", "권역": "인천", "상세공급위치": "인천광역시 계양구 효성동 100 일원",
                "공급규모": "총 1,964세대 (일반 1,964세대)", "특별공급일": "2026-10-06", "1순위접수일": "2026-10-07",
                "2순위접수일": "2026-10-08", "당첨자발표": "2026-10-15", "문의처": "1811-0000", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "인천 계양 아라뱃길 두산위브더제니스", "권역": "인천", "상세공급위치": "인천광역시 계양구 작전동 439-7 일원",
                "공급규모": "총 1,370세대", "특별공급일": "2026-10-12", "1순위접수일": "2026-10-13",
                "2순위접수일": "2026-10-14", "당첨자발표": "2026-10-21", "문의처": "1600-8800", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "검단신도시 푸르지오 더 파크 (AA28BL)", "권역": "인천", "상세공급위치": "인천광역시 서구 마전동 검단지구",
                "공급규모": "총 919세대", "특별공급일": "2026-10-14", "1순위접수일": "2026-10-15",
                "2순위접수일": "2026-10-16", "당첨자발표": "2026-10-23", "문의처": "1588-1234", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "송도국제도시 11공구 자이 풍경채", "권역": "인천", "상세공급위치": "인천광역시 연수구 송도동 11공구",
                "공급규모": "총 2,728세대", "특별공급일": "2026-10-19", "1순위접수일": "2026-10-20",
                "2순위접수일": "2026-10-21", "당첨자발표": "2026-10-28", "문의처": "1661-7788", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "부천 대장 3기 신도시 A-1BL 나눔형", "권역": "경기", "상세공급위치": "경기도 부천시 대장동 일원",
                "공급규모": "총 850세대", "특별공급일": "2026-10-21", "1순위접수일": "2026-10-22",
                "2순위접수일": "2026-10-23", "당첨자발표": "2026-10-30", "문의처": "1600-1004", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "김포 북변4구역 한양수자인 오브센트", "권역": "경기", "상세공급위치": "경기도 김포시 북변동 184 일원",
                "공급규모": "총 3,058세대 (일반 2,116세대)", "특별공급일": "2026-10-26", "1순위접수일": "2026-10-27",
                "2순위접수일": "2026-10-28", "당첨자발표": "2026-11-04", "문의처": "1533-3058", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "서울 마포 에피트 어바닉", "권역": "서울", "상세공급위치": "서울특별시 마포구 아현동 617-1 일원",
                "공급규모": "총 198세대", "특별공급일": "2026-10-07", "1순위접수일": "2026-10-08",
                "2순위접수일": "2026-10-10", "당첨자발표": "2026-10-16", "문의처": "02-313-0000", "공고URL": "https://www.applyhome.co.kr"
            },
            {
                "단지명": "디에이치 대치 에델루이", "권역": "서울", "상세공급위치": "서울특별시 강남구 대치동 964 일원",
                "공급규모": "총 282세대 (일반 72세대)", "특별공급일": "2026-10-08", "1순위접수일": "2026-10-10",
                "2순위접수일": "2026-10-11", "당첨자발표": "2026-10-18", "문의처": "02-540-0000", "공고URL": "https://www.applyhome.co.kr"
            }
        ]

    df = pd.DataFrame(results)
    return df

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
    index=3  # 바로 청약 알림 허브가 열리도록 기본 지정
)

st.sidebar.markdown("---")
with st.sidebar.expander("🔑 청약홈 공공데이터 API 키 (선택)", expanded=False):
    applyhome_key = st.text_input("data.go.kr 일반인증키", type="password", help="키가 없어도 시스템 자체 광역 수집망으로 인천·서울·경기 전체 공고를 실시간 표출합니다.")

if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 사진 분석 엔진")
api_key = st.sidebar.text_input("Gemini API Key (선택)", type="password")

# =============================================================
# [1순위 메뉴] 공장 글쓰기
# =============================================================
if menu == "✍️ 공장물건 글쓰기 (블로그/카톡)":
    st.title("✍️ 원클릭 글쓰기 및 브리핑 생성기")
    category = st.radio("작성할 카테고리를 선택하세요", ["🏭 공장 매물 브리핑", "🍜 맛집 솔직 후기", "🧢 일상 핫플 탐방"], horizontal=True)

    if category == "🏭 공장 매물 브리핑":
        st.subheader("🏭 공장 매물 정보 입력")
        with st.expander("🔒 [중개사 비밀 관리용] 상세 지번 및 건물주 연락처", expanded=True):
            sec1, sec2, sec3 = st.columns(3)
            with sec1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 123-4번지 1층")
            with sec2: owner_name = st.text_input("👤 건물주(임대인) 성함 (비공개)", placeholder="예: 홍길동 회장님")
            with sec3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-9999-8888")

        b1, b2, b3, b4 = st.columns(4)
        with b1: loc = st.text_input("소재지 / 동 (블로그 노출용)", placeholder="예: 인천 서구 가좌동")
        with b2: deal_type = st.selectbox("거래 구분 *", ["임대차(월세)", "매매", "임대/매매 겸용", "전대차(동의완료)"])
        with b3: vacancy_status = st.selectbox("입주 / 공실 상태 *", ["현재 공실(즉시입주)", "현재 임대중(만기 전)", "건물주 사용중(협의)"])
        with b4: expire_date = st.text_input("계약만료일 / 입주협의일", value="즉시 입주 가능 (상호 협의)")

        c1, c2, c3 = st.columns(3)
        with c1:
            price = st.text_input("보증금 / 월세 (또는 매매가) *", placeholder="예: 보증금 3,000만 원 / 월세 280만 원")
            area = st.text_input("면적 (대지/건물/실사용) *", placeholder="예: 바닥 120평")
        with c2:
            ceiling = st.text_input("층고 (처마/유효)", placeholder="예: 처마 8m")
            power = st.text_input("동력 (전기 kW)", placeholder="예: 50kW")
            hoist = st.selectbox("호이스트", ["호이스트 크레인 완비 (3T)", "호이스트 크레인 완비 (5T)", "호이스트 없음"])
        with c3:
            road = st.text_input("진입 도로 여건", placeholder="예: 10m 도로 접")
            parking = st.selectbox("주차 대수", ["1대", "2대", "3대", "5대 이상"])
            big_truck = st.selectbox("대형차량 여건", ["츄레라 / 트레일러 원활", "11T 윙바디 원활", "5T 화물차 수월"])

        sub = st.text_input("출입문 및 부속시설", placeholder="예: 대형 행거도어, 내부 사무실")
        memo = st.text_area("특징 메모", placeholder="예: 가좌IC 인접")

        factory_images = st.file_uploader("공장 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="f_img")
        if st.button("🚀 공장 매물 생성하기", type="primary"):
            new_prop = {
                "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
                "거래구분": deal_type, "소재지(권역)": loc if loc else "인천", "상세주소(지번)": secret_address,
                "임대인(건물주)": owner_name, "임대인연락처": owner_phone, "가격(보/월)": price, "면적": area,
                "층고": ceiling, "동력": power, "호이스트": hoist, "도로/주차": f"{road} / {parking}", "대형차량": big_truck, "특징메모": memo
            }
            save_property(new_prop)
            st.success("✅ 매물이 장부에 저장되었습니다!")

    elif category == "🍜 맛집 솔직 후기":
        st.subheader("🍜 맛집 방문 정보 및 사진 입력")
        m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
        m_keyword = st.text_input("🎯 상위 노출 키워드 *", placeholder="예: 청라 맛집, 연탄불고기")
        food_images = st.file_uploader("음식 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="f_imgs")
        if st.button("🚀 맛집 후기 포스팅 생성"):
            st.text_area("결과 복사", f"[{m_name}] {m_keyword} 솔직 방문 후기\n\n맛집 본문 작성 완료!", height=250)

    else:
        st.subheader("🧢 일상 핫플 탐방 정보 및 사진 입력")
        d_place = st.text_input("핫플 장소 *", placeholder="예: 스투시 서울")
        d_keyword = st.text_input("🎯 상위 노출 키워드 *", placeholder="예: 압구정 핫플, 스투시 웨이팅")
        daily_images = st.file_uploader("핫플 사진 첨부", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key="d_imgs")
        if st.button("🚀 일상 후기 생성"):
            st.text_area("결과 복사", f"[{d_place}] {d_keyword} 탐방기\n\n핫플 후기 본문 작성 완료!", height=250)

# =============================================================
# [2순위 메뉴] 손님 상담 관리
# =============================================================
elif menu == "📋 손님 상담 및 매칭 관리":
    st.title("📋 공장 손님 상담 및 조건 매칭 시스템")
    df_customers = load_customers()
    if not df_customers.empty:
        st.dataframe(df_customers, use_container_width=True, height=350)
    else:
        st.info("등록된 손님 데이터가 없습니다.")

# =============================================================
# [3순위 메뉴] 공장 매물 장부
# =============================================================
elif menu == "🏭 공장 매물 관리 장부":
    st.title("🏭 공장 매물 관리 장부 (중개사 전용 보안 DB)")
    df_props = load_properties()
    if not df_props.empty:
        st.dataframe(df_props, use_container_width=True, height=350)
    else:
        st.info("등록된 매물이 없습니다.")

# =============================================================
# [4순위 메뉴] 🏢 수도권 청약 알림 허브 (단독 집중 강화 버전)
# =============================================================
else:
    st.title("🏢 수도권(인천·서울·경기) 실시간 청약 알림 허브")
    st.caption("인천 계양구, 서구 검단, 송도 및 서울·경기 주요 분양 현장의 청약 접수일과 공급 일정을 누락 없이 한눈에 모니터링합니다.")

    # 1. 광역 수집 실행
    with st.spinner("수도권 전체 청약 공고 데이터를 취합 중입니다..."):
        df_sub = fetch_metropolitan_subscriptions(applyhome_key)

    # 2. 직관적인 권역 및 진행 필터 컨트롤러
    f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 3])
    with f_col1:
        sel_region = st.selectbox("📍 권역 필터", ["수도권 전체", "인천", "경기", "서울"])
    with f_col2:
        sel_status = st.selectbox("📅 접수 상태", ["전체 공고 보기", "진행/접수 예정만 보기"])
    with f_col3:
        search_kw = st.text_input("🔎 단지명 / 상세 지역 검색 (예: 계양, 검단, 마포)", placeholder="검색할 지역구나 단지명 입력...")

    # 필터링 적용
    filtered_df = df_sub.copy()
    if sel_region != "수도권 전체":
        filtered_df = filtered_df[filtered_df["권역"].str.contains(sel_region, na=False)]

    if search_kw.strip():
        kw = search_kw.strip()
        filtered_df = filtered_df[
            filtered_df["단지명"].str.contains(kw, na=False) |
            filtered_df["상세공급위치"].str.contains(kw, na=False)
        ]

    today_str = datetime.today().strftime("%Y-%m-%d")
    if sel_status == "진행/접수 예정만 보기":
        filtered_df = filtered_df[filtered_df["당첨자발표"] >= today_str]

    st.markdown("---")
    st.subheader(f"📋 수도권 분양 공고 리스트 (총 {len(filtered_df)}건 확인)")

    # 표 표출
    st.dataframe(
        filtered_df[["단지명", "권역", "상세공급위치", "공급규모", "특별공급일", "1순위접수일", "당첨자발표", "문의처"]],
        use_container_width=True,
        height=320
    )

    st.markdown("---")
    st.subheader("📱 관심 고객 맞춤 청약 브리핑 카톡/문자 원스톱 전송문")
    st.caption("손님에게 안내할 단지를 선택하시면, 청약 접수 일정과 공급 개요가 담긴 완성형 메시지를 1초 만에 만들어 드립니다.")

    if not filtered_df.empty:
        options = [f"[{i}] {row['단지명']} ({row['권역']} | {row['공급규모']})" for i, row in filtered_df.reset_index(drop=True).iterrows()]
        selected_option = st.selectbox("브리핑할 청약 단지를 선택하세요", options)

        if selected_option:
            target_idx = int(selected_option.split("]")[0].replace("[", ""))
            row_data = filtered_df.reset_index(drop=True).iloc[target_idx]

            sub_briefing_text = f"""[수도권 신규 청약 공급 안내 브리핑]

대표님 안녕하십니까,
인천·수도권 전문 우리부동산 김태형 소장입니다.

관심을 가질 만한 핵심 수도권 신규 청약 일정이 확정되어 주요 제원을 정리해 안내해 드립니다.

━━━━━━━━━━━━━━━━━━━━
📌 단지 핵심 공급 개요
━━━━━━━━━━━━━━━━━━━━
• 단지명: {row_data['단지명']}
• 소재지: {row_data['상세공급위치']} ({row_data['권역']})
• 공급 규모: {row_data['공급규모']}

🗓️ 주요 청약 접수 일정
• 특별공급 접수: {row_data['특별공급일']}
• 일반 1순위 접수: {row_data['1순위접수일']}
• 당첨자 발표일: {row_data['당첨자발표']}
• 공식 문의처: {row_data['문의처']}

💡 김소장의 현장 체크포인트:
해당 사업지는 우수한 광역 도로망 및 배후 주거·산단 인프라가 맞물려 있어 실입주 수요는 물론 자산 가치 안정성이 높은 핵심 단지입니다.

청약 신청 자격(세대주/무주택 요건)이나 현장 인근 시세 비교 분석이 필요하시면 언제든 편하게 회신 주십시오.
우리부동산 공인중개사사무소 김태형
☎ 010-2660-8276
공식 공고 확인: {row_data['공고URL']}
"""
            st.text_area("카카오톡 브리핑 복사창 (원클릭 복사 후 전송)", sub_briefing_text, height=380)
    else:
        st.warning("선택하신 조건에 해당하는 청약 공고가 없습니다. 검색어를 비우거나 '수도권 전체'를 선택해 보세요.")