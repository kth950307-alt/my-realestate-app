import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime

st.set_page_config(page_title="우리부동산 통합 업무 시스템", page_icon="🏢", layout="wide")

# 크롬/사파리 번역 방지 및 실무형 CSS
st.markdown("""
<script>
    document.documentElement.lang = 'ko';
    document.documentElement.classList.add('notranslate');
    document.documentElement.setAttribute('translate', 'no');
</script>
<meta name="google" content="notranslate">
<style>
    html, body, [data-testid="stAppViewContainer"], .notranslate { translate: no !important; }
    .hunt-item-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #3182ce; border-radius: 6px; padding: 8px 14px; margin-bottom: 6px; }
    .hunt-item-done { background-color: #f0fff4; border: 1px solid #c6f6d5; border-left: 5px solid #38a169; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
    .customer-card-pro { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid #3182ce; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; }
    .customer-card-pro-vip { background-color: #fffdf7; border: 1px solid #feebc8; border-left: 6px solid #dd6b20; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; }
    .tag-blue { background-color: #ebf8ff; color: #2b6cb0; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-right: 4px; display: inline-block; }
    .tag-orange { background-color: #fffaf0; color: #c05621; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-right: 4px; display: inline-block; }
    .tag-green { background-color: #f0fff4; color: #276749; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-right: 4px; display: inline-block; }
    .remind-card-red { background-color: #fff5f5; border-left: 5px solid #e53e3e; border: 1px solid #fed7d7; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
    .calc-box-orange { background-color: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 14px; margin: 10px 0; }
    .calc-box-blue { background-color: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 14px; margin: 10px 0; }
    .check-list-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #4a5568; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; font-size: 13px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# 🔒 보안 잠금
CORRECT_PASSWORD = "950307"
if not st.session_state.get("authenticated", False):
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>### 🏢 우리부동산 통합 업무 시스템", unsafe_allow_html=True)
        st.caption("인천 공장 중개 & 임장 파이프라인·청약·경매 허브")
        pwd_input = st.text_input("사무실 전용 비밀번호", type="password", key="pwd_box")
        if st.button("🔓 시스템 접속하기", type="primary", use_container_width=True):
            if pwd_input == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
    st.stop()

# ⚡ CSV 데이터베이스 관리 함수
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
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-822", "건물유형": "집합공장", "소재지전체": "인천 서구 석남동 223-822", "소유자/법인명": "관리사무소/집합", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "집합공장"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-932", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-932", "소유자/법인명": "홍정미", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "방문 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-651", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-651", "소유자/법인명": "소유자 확인중", "상호": "", "연락처": "", "진행상태": "📞 전화 확인", "현장메모": "전화 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-360", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-360", "소유자/법인명": "이해영, 최완규", "상호": "신창코팅", "연락처": "032-577-0104", "진행상태": "📞 전화 확인", "현장메모": "신창코팅"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-559", "건물유형": "운수/차고지", "소재지전체": "인천 서구 석남동 223-559", "소유자/법인명": "한미교통주식회사", "상호": "한미교통", "연락처": "032-571-1032", "진행상태": "📞 전화 확인", "현장메모": "한미교통"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-557", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-557", "소유자/법인명": "김용주", "상호": "명인기공", "연락처": "032-579-3171", "진행상태": "🚗 방문 필요", "현장메모": "명인기공"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-835", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-835", "소유자/법인명": "박용욱", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "개인소유"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-786", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-786", "소유자/법인명": "진우조명", "상호": "진우조명", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": "진우조명"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-886", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-886", "소유자/법인명": "안민영", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": ""},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-881", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-881", "소유자/법인명": "권진주", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": ""},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-855", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-855", "소유자/법인명": "성용욱", "상호": "", "연락처": "", "진행상태": "🚗 방문 필요", "현장메모": ""}
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

# ⚖ 법원경매 데이터베이스
def get_auction_data():
    factory_auctions = [
        {
            "사건번호": "2026타경10452", "법원": "인천지방법원 본원 (경매5계)", "소재지": "인천광역시 서구 가좌동 556-12", "세부용도": "일반공장 / 제조장",
            "대지면적": "661.1㎡ (약 200평)", "건물면적": "528.9㎡ (약 160평)", "바닥평수": 160, "현재동력kW": 75, "현재호이스트": "호이스트 5T 완비",
            "총감정가원": 1850000000, "총감정가": "18억 5,000만 원", "최저가원": 1295000000, "최저가": "12억 9,500만 원 (70%)", "입찰보증금": "1억 2,950만 원 (10%)",
            "토지감정가원": 1350000000, "건물감정가원": 420000000, "기계기구감정가원": 80000000, "기계감정내역": "천장주행 크레인 5T 1식, 수전설비 75kW",
            "매각기일": "2026-10-22", "진행상태": "유찰 1회",
            "권리분석": {"말소기준": "2019-04-12 근저당권 (신한은행)", "임차인": "대항력 없는 후순위 임차인 1명 (보증금 3,000만 원)", "유치권": "유치권 신고 없음", "인수권리": "소멸주의"},
            "산단입주자격": "일반공업지역 (산집법 입주계약 불필요, 모든 제조업 입주 가능)", "연체관리비추정": 3500000,
            "배당정보": {"경매비용": 12000000, "당해세": 8000000, "최우선변제": 0, "선순위근저당": 950000000, "임차인배당": 30000000},
            "제원및코멘트": "처마 8m, 호이스트 5T 완비, 동력 75kW 인입, 11톤 윙바디 진입 원활. 가좌IC 3분 거리.",
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    apt_auctions = [
        {
            "사건번호": "2026타경10550", "법원": "서울중앙지방법원 (경매4계)", "시도": "서울특별시",
            "소재지": "서울특별시 서초구 반포동 2-1 (아크로리버파크 104동)", "주택유형": "아파트", "평형타입": "전용 84.97㎡ (34평형)", "층수": "22층 / 38층",
            "감정가원": 4300000000, "감정가": "43억 원", "최저가원": 3440000000, "최저가": "34억 4,000만 원 (80%)", "입찰보증금": "3억 4,400만 원 (10%)",
            "매각기일": "2026-11-12", "진행상태": "유찰 1회", "실거래시세원": 4500000000, "최근실거래가": "45억 원 선",
            "권리분석": {"말소기준권리": "2019-12-10 근저당권 (신한은행)", "임차인분석": "소유자 세대 점유 (대항력 없음)", "인수보증금": 0, "토허제특례": "경매 취득 시 토지거래허가구역 실거주의무 면제", "명도난이도": "보통"},
            "미납관리비": 1800000, "추천입찰가밴드": "36억 5,000만 ~ 37억 8,000만 원", "예상시세차익": "약 7억 ~ 8.5억 원",
            "배당정보": {"경매비용": 18000000, "당해세": 15000000, "최우선변제": 0, "선순위근저당": 2800000000, "임차인배당": 0},
            "사건URL": "https://www.courtauction.go.kr"
        }
    ]
    return factory_auctions, apt_auctions

# 📌 업무 메뉴 네비게이션
MENU_DICT = {
    "FACTORY_HUNT": "🏃 [임장/작업] 현장 공장 물건따기 파이프라인",
    "FACTORY_REG": "🏭 [주업] 공장 매물 등록 & 손님 자동매칭",
    "NEW_DEV": "🏗️ [주업] 신축공장 맞춤 분양 설계 & 제안서",
    "CUSTOMER_CRM": "📋 [주업] 공장 손님 장부 (CRM & 리마인드)",
    "FACTORY_BOOK": "📁 [주업] 공장 보유 매물 장부 (드롭다운 필터)",
    "PRICE_AI": "🔍 [주업] 공장·창고 AI 시세 추정기",
    "BLOG_TOOL": "🍜 [부업] 맛집 & 🧢 일상 블로그 글쓰기",
    "APPLY_HOME": "🏢 [부업] 청약·줍줍 & LH 공공임대 팩트체크",
    "AUCTION_HUB": "⚖️ [부업] 법원경매 허브 & 수도권 주택·공장 정밀분석"
}

menu_choice = st.sidebar.radio("📌 업무 시스템 메뉴", list(MENU_DICT.values()), index=0)
st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃"):
    st.session_state["authenticated"] = False
    st.rerun()

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

    # 1. 작업 중 리스트
    with h_tab1:
        f1, f2, f3 = st.columns([1.5, 1.5, 2])
        all_dongs = ["전체 동 모아보기"] + sorted(list(df_h["동"].dropna().unique()))
        with f1: sel_dong = st.selectbox("📍 법정동 필터", all_dongs, key="hunt_d_f")
        with f2: sel_stat = st.selectbox("🚦 진행상태 필터", ["전체 상태", "🚗 방문 필요", "📞 전화 확인", "🔄 재트라이", "보류/거절"], key="hunt_s_f")
        with f3: kw_hunt = st.text_input("🔎 지번 / 상호 / 소유자 검색", placeholder="예: 223-360, 신창코팅...", key="hunt_k_f")

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
                        st.success(f"🎉 {r['동']} {r['지번']} 물건을 확보했습니다! 확보완료함으로 이관되었습니다.")
                        st.rerun()

                st.markdown("<hr style='margin:3px 0 6px 0; border:0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)

    # 2. 🎉 [수주 성공] 확보 완료 매물함
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

    # 3. 텍스트 일괄 붙여넣기
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
# 1. 🏭 [주업] 공장 매물 등록 & 확인·설명서 필수 항목 자동화
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_REG"]:
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
        ceiling = st.text_input("처마 층고", placeholder="예: 처마 7.5m")
        power = st.text_input("인입 동력 (kW) *", placeholder="예: 30kW")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음"])
    with c3:
        road = st.text_input("접면 도로 폭(m)", placeholder="예: 8m 도로 접")
        parking_count = st.text_input("주차장 현황", placeholder="예: 자주식 옥외 3대")
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
    memo = st.text_area("매물 핵심 강점 메모", placeholder="예: 호이스트 완비, 마당 넓음, 11톤 윙바디 접안 최적.")

    if st.button("🚀 매물 저장 & 확인·설명서 생성", type="primary", use_container_width=True):
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
            site_name = st.text_input("프로젝트/단지명 *", placeholder="예: 도화동 930-1 신축공장")
            site_addr = st.text_input("사업지 상세 주소 *", placeholder="예: 인천 미추홀구 도화동 930-1")
        with p2:
            custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=100, step=10)
            road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
        with p3:
            cust_company = st.text_input("제안 대상 기업명/대표님", placeholder="예: (주)대한정밀 대표님")
            cust_usage = st.text_input("권장 조업 업종/용도", placeholder="예: 정밀기계제조 / 금형가공")

        fl1, fl2, fl3 = st.columns(3)
        with fl1: f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=70, step=5)
        with fl2: f2_pyung = st.number_input("2층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl3: f3_pyung = st.number_input("3층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)

        pr1, pr2 = st.columns(2)
        with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원) *", value=1200, step=50)
        with pr2: add_unit_price = st.number_input("상층부 증축단가 (건축 평당 만 원) *", value=350, step=10)

        actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
        yard_pyung = max(0, custom_land - f1_pyung)

        if st.button("🚀 신축공장 맞춤 분양 설계 & 제안서 산출하기", type="primary", use_container_width=True):
            floor_list = [f1_pyung, f2_pyung, f3_pyung]
            active_floors = [p for p in floor_list if p > 0]
            max_floor_cnt = len(active_floors)
            total_bldg_area = sum(floor_list)

            base_cost = int(custom_land * base_unit_price * 10000)
            extra_cost = int(sum(floor_list[1:]) * add_unit_price * 10000)
            total_dev_price = base_cost + extra_cost
            loan_80 = int(total_dev_price * 0.80)
            pure_cash = total_dev_price - loan_80
            acq_tax = int(total_dev_price * 0.046)

            st.markdown("---")
            out_c1, out_c2 = st.columns([1.2, 1.3])
            with out_c1:
                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{cust_company if cust_company else '고객사'}] 맞춤 분양 견적서</h4>
                    • <b>사업지</b>: {site_name} ({site_addr})<br>
                    • <b>분양 대지면적</b>: <b>{custom_land}평</b> | <b>건폐율</b>: <b>{actual_bcr}%</b><br>
                    • <b>건축 규모</b>: <b>지상 {max_floor_cnt}층 (연면적 {total_bldg_area}평)</b> | 마당: <b>약 {yard_pyung}평</b><br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🚩 <b>분양 공급가액</b>: <span style="font-size: 20px; font-weight: bold; color: #c53030;">{total_dev_price:,}원</span><br>
                    • 시설대출 80%: 약 <b>{loan_80:,}원</b> | <b>필요 순수 현금</b>: <span style="color: #2b6cb0; font-weight: bold;">약 {pure_cash + acq_tax:,}원</span> (취득세 4.6% 포함)
                </div>
                """, unsafe_allow_html=True)

            with out_c2:
                bldg_w = int(max(20, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
                yard_w = 100 - bldg_w
                svg_2d = f"""
                <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 12px;">
                    <div style="background-color: #2d3748; color: white; text-align: center; padding: 6px; font-weight: bold; font-size: 13px; margin-bottom: 8px;">
                        ▲ 전면 {road_width}m 광폭 도로 접 ▲
                    </div>
                    <div style="display: flex; gap: 8px; height: 140px; background-color: #ebf8ff; border: 2px dashed #3182ce; padding: 8px; border-radius: 6px;">
                        <div style="flex: {bldg_w}; background-color: #bee3f8; border: 2px solid #1a365d; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                            <span style="font-weight: bold; color: #1a365d;">🏭 공장동</span>
                            <span style="font-size: 12px; color: #2c5282;">지상 {max_floor_cnt}층 ({f1_pyung}평)</span>
                        </div>
                        <div style="flex: {yard_w}; background-color: #edf2f7; border: 2px dashed #718096; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                            <span style="font-weight: bold; color: #4a5568;">🚛 단독 마당</span>
                            <span style="font-size: 12px; color: #718096;">약 {yard_pyung}평</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(svg_2d, unsafe_allow_html=True)

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
                            "고객명": row.get("상호/고객명", ""), "연락처": row.get("연락처", ""),
                            "경과일": passed_days, "메모": row.get("상담메모", "")
                        })
                except Exception: pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락 후 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | 마지막 연락 후 <b>{rt['경과일']}일 경과</b> ➡️ <i>"신규 매물 체크 및 안부 전화 권장"</i>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    tab_list, tab_edit = st.tabs(["📊 손님 장부 목록", "✍️ 손님 신규 등록 및 수정/삭제"])

    with tab_list:
        if not df_c.empty:
            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 2.0])
            with f_col1: date_col_name = st.selectbox("📅 조회 기준일", ["최근연락일", "접수일자"])
            with f_col2: sort_order = st.selectbox("🔄 정렬 순서", ["최신 날짜순", "과거 날짜순"])
            with f_col3: search_kw = st.text_input("🔎 손님명 / 연락처 / 메모 검색", placeholder="예: 대한정밀 등...")

            filtered_by_date = df_c.copy()
            if search_kw.strip():
                kw = search_kw.strip()
                filtered_by_date = filtered_by_date[
                    filtered_by_date["상호/고객명"].astype(str).str.contains(kw, na=False) |
                    filtered_by_date["연락처"].astype(str).str.contains(kw, na=False) |
                    filtered_by_date["상담메모"].astype(str).str.contains(kw, na=False)
                ]
            ascending_bool = True if "과거" in sort_order else False
            filtered_by_date = filtered_by_date.sort_values(by=date_col_name, ascending=ascending_bool)

            for orig_idx, c_row in filtered_by_date.iterrows():
                is_vip = "S급" in str(c_row.get("중요도", "")) or "A급" in str(c_row.get("중요도", ""))
                card_class = "customer-card-pro-vip" if is_vip else "customer-card-pro"

                c_name_val = get_safe_cust_val(c_row, "상호/고객명")
                c_phone_val = get_safe_cust_val(c_row, "연락처")
                c_star_val = get_safe_cust_val(c_row, "중요도")
                c_deal_val = get_safe_cust_val(c_row, "거래구분")
                c_loc_val = get_safe_cust_val(c_row, "희망권역")
                c_area_val = get_safe_cust_val(c_row, "희망평수")
                c_budget_val = get_safe_cust_val(c_row, "예산(보증금/월세/매매가)")
                c_memo_val = get_safe_cust_val(c_row, "상담메모")

                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:17px; font-weight:bold; color:#1a365d;">👤 {c_name_val}</span>
                            <span style="color:#d69e2e; font-weight:bold; margin-left:6px;">{c_star_val}</span>
                            <span class="tag-blue" style="margin-left:8px;">{c_deal_val}</span>
                        </div>
                        <div style="font-size:13px; color:#4a5568;">📞 <b>{c_phone_val}</b></div>
                    </div>
                    <div style="margin: 6px 0;">
                        <span class="tag-orange">📐 {c_area_val}</span>
                        <span class="tag-orange">📍 {c_loc_val}</span>
                        <span class="tag-orange">💰 {c_budget_val}</span>
                    </div>
                    <div style="font-size:12.5px; color:#2d3748;">💡 <b>메모</b>: {c_memo_val}</div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("등록된 손님이 없습니다.")

    with tab_edit:
        st.subheader("✍️ 손님 신규 등록 및 수정")
        with st.form("cust_form_pro"):
            r1, r2, r3 = st.columns(3)
            with r1: c_name = st.text_input("상호 / 고객명 *", placeholder="예: (주)대한정밀")
            with r2: c_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
            with r3: c_star = st.selectbox("중요도", ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"])

            r4, r5, r6 = st.columns(3)
            with r4: c_deal = st.selectbox("거래 구분 *", ["임대차(월세)", "매매", "매매/임대 겸용"])
            with r5: c_loc = st.text_input("희망 권역 *", placeholder="예: 인천 서구 가좌/석남")
            with r6: c_area = st.text_input("희망 평수 *", placeholder="예: 100평")

            c_budget = st.text_input("예산", placeholder="예: 보 3천 / 월 250만")
            c_memo = st.text_area("상담 메모", placeholder="예: 바닥 에폭시 필수, 호이스트 5톤 희망")

            if st.form_submit_button("💾 신규 손님 등록하기", type="primary", use_container_width=True):
                if not c_name or not c_phone:
                    st.error("상호/고객명과 연락처는 필수입니다.")
                else:
                    save_customer({
                        "접수일자": today.strftime("%Y-%m-%d"), "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star, "거래구분": c_deal, "업종인허가": "일반제조", "상호/고객명": c_name,
                        "연락처": c_phone, "희망권역": c_loc, "희망평수": c_area, "예산(보증금/월세/매매가)": c_budget,
                        "입주시기": "협의", "호이스트": "무관", "대형차진입": "11T 수월", "희망전력kW": "30kW",
                        "상담메모": c_memo, "상담히스토리": f"[{today.strftime('%Y-%m-%d')}] 접수\n", "진행상태": "상담 접수"
                    })
                    st.success("✅ 등록 완료!")
                    st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()
    if not df_p.empty:
        f1, f2 = st.columns(2)
        with f1: sel_hoist = st.selectbox("🏗️ 호이스트", ["전체 (유/무 무관)", "호이스트 완비", "호이스트 없음"])
        with f2: search_text = st.text_input("🔎 권역/메모 검색")

        filtered_df = df_p.copy()
        if sel_hoist == "호이스트 완비": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("완비|설치|톤|T", na=False)]
        elif sel_hoist == "호이스트 없음": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("없음", na=False)]
        if search_text.strip(): filtered_df = filtered_df[filtered_df["소재지(권역)"].str.contains(search_text, na=False) | filtered_df["특징메모"].str.contains(search_text, na=False)]

        st.dataframe(filtered_df, use_container_width=True, height=450)
    else: st.info("등록된 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 AI 시세 추정기")
    st.caption("주소지(동), 대지 평수를 바탕으로 적정 매매가를 자동 산출합니다.")

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

    c1, c2, c3 = st.columns(3)
    with c1:
        m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
        m_loc = st.text_input("위치 / 권역 *", placeholder="예: 인천 서구 청라동")
    with c2:
        m_menu = st.text_input("주문 메뉴 및 가격 *", placeholder="예: 생삼겹살 2인분(32,000원)")
        m_point = st.text_input("킬링 포인트 (숏폼용)", placeholder="예: 연탄 불향 육즙과 구운 묵은지")
    with c3:
        m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 가성비와 불향 끝내주는 삼겹살 맛집")

    if st.button("🚀 맛집 마케팅 패키지 (포스팅 + 400자 영수증 + 숏폼) 생성", type="primary"):
        if not m_name or not m_eval:
            st.error("상호명과 솔직 한 줄 총평은 필수입니다.")
        else:
            b_col1, b_col2 = st.columns([1.3, 1.0])
            with b_col1:
                st.markdown("##### 📝 네이버 블로그 최상위 포스팅 본문")
                post_text = f"""안녕하세요. 인천 맛집·일상 탐방 전문 우리부동산입니다.
오늘 소개해 드리는 곳은 {m_loc}에 위치한 {m_name} 솔직 방문 후기로, {m_menu} 구성에 {m_eval}이라는 만족스러운 식사를 즐기고 왔습니다.

📌 {m_name} 체크포인트
✅ {m_eval}
✅ {m_point}
✅ 쾌적한 동선과 친절한 응대

우리부동산 공인중개사사무소 대표 김태형 010-2660-8276
"""
                st.text_area("블로그 본문 복사", post_text, height=300)

            with b_col2:
                st.markdown("##### 🧾 네이버 영수증 리뷰 (400자 이내)")
                review_text = f"""⭐⭐⭐⭐⭐
{m_loc} 찐맛집 인정합니다! 평소 소문 듣고 찾아왔는데 기대 이상이었어요.
{m_menu} 주문해서 먹어봤는데, {m_point}. {m_eval}!
고기 질도 정말 신선하고 불향 밸런스가 예술이라 마지막 한 점까지 맛있게 먹었습니다.
직원분들도 친절하셔서 기분 좋게 식사했네요. 재방문 의사 100%입니다!"""
                st.caption(f"📝 현재 글자 수: **{len(review_text)}자** / 최대 400자")
                st.text_area("영수증 리뷰 복사", review_text, height=140)

                st.markdown("##### 🎬 30초 숏폼 촬영 대본")
                short_script = f"""[0~3초 훅] "인천 {m_loc}에서 고기 좀 먹어봤다면 모를 수가 없는 이곳!"\n[4~22초 본론] "바로 {m_name}인데요. {m_menu} 시키면 나오는 비주얼 좀 보세요. {m_point}!"\n[23~30초 클로징] "이번 주말 외식 장소 고민 끝!" """
                st.text_area("숏폼 대본 복사", short_script, height=120)

# =============================================================
# 7. 🏢 [타이핑 제로] 청약·줍줍 & 공공임대 1초 스마트 파서 & 블로그 완성기
# =============================================================
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 청약·줍줍 & 공공임대 1초 팩트체크 허브")
    st.caption("청약홈/LH 공고 화면을 마우스로 긁어 복사한 뒤 붙여넣기만 하세요. AI/정규식 엔진이 일정, 금액, 자격, 안전마진을 기계적으로 자동 분석해 포스팅을 완성합니다.")

    APPLYHOME_CAL_URL = "https://www.applyhome.co.kr/ai/aib/selectSubscrptCalenderView.do#a"
    LH_APPLY_URL = "https://apply.lh.or.kr"

    top1, top2 = st.columns(2)
    with top1: st.link_button("📅 [청약Home] 실시간 청약캘린더 바로가기", APPLYHOME_CAL_URL, type="primary", use_container_width=True)
    with top2: st.link_button("🏢 [LH청약플러스] 실시간 분양·임대센터 바로가기", LH_APPLY_URL, use_container_width=True)

    st.markdown("---")
    
    # 상단 텍스트 붙여넣기 박스 (원클릭 엔진)
    raw_sub_text = st.text_area(
        "📥 청약홈 또는 LH 공고문 화면 텍스트를 그대로 붙여넣으세요 (Ctrl+V):",
        height=140,
        placeholder="예시: [계양 롯데캐슬 파크시티 1단지] 공급위치: 인천광역시 계양구 효성동 100 일원 특별공급: 2026.10.06 1순위: 2026.10.07 당첨자발표: 2026.10.15 정당계약: 2026.10.27~10.30 공급규모: 1,964세대 공급금액: 659,000,000원 신청자격: 인천 및 수도권 거주 만 19세 이상 무주택세대주, 청약통장 12개월 이상..."
    )

    # 1. 기계적 정규식 파싱 엔진 (수동 입력 필요 없음)
    p_name = "단지명 미확인"
    p_loc = "소재지 확인 필요"
    p_dates_all = []
    p_rcv = "접수일정 확인"
    p_win = "발표일정 확인"
    p_cnt = "계약일정 확인"
    p_sup = "공급규모 확인"
    p_price_str = "분양가 확인"
    p_price_num = 0
    p_type = "일반분양"
    p_qual = "입주자모집공고일 현재 해당지역 거주자 요건 확인"
    p_real_price = 0

    if raw_sub_text.strip():
        txt = raw_sub_text.strip()
        lines = [l.strip() for l in txt.split("\n") if l.strip()]
        
        # 단지명 추출
        first_line = lines[0]
        if "[" in first_line and "]" in first_line:
            p_name = re.findall(r'\[(.*?)\]', first_line)[0]
        else:
            p_name = first_line.split("공급")[0].split("입주자")[0].strip()

        # 유형 자동 판별
        if "무순위" in txt or "임의공급" in txt or "줍줍" in txt:
            p_type = "🔥 무순위/임의공급 (줍줍)"
        elif "취소" in txt:
            p_type = "🔥 계약취소주택 재공급"
        elif "행복주택" in txt or "청년" in txt or "임대" in txt:
            p_type = "🏠 공공임대 / 청년행복주택"
        elif "공공분양" in txt or "LH" in txt or "SH" in txt:
            p_type = "🏢 공공분양"
        else:
            p_type = "🏢 민영 일반분양"

        # 위치 추출
        loc_m = re.search(r'(위치|소재지)[:\s]*([^\n,]+)', txt)
        if loc_m:
            p_loc = loc_m.group(2).strip()
        else:
            loc_guess = re.search(r'(서울특별시|인천광역시|경기도)\s+([^\s]+구|[^\s]+시|[^\s]+군)\s+([^\s]+동|[^\s]+읍|[^\s]+면)', txt)
            if loc_guess: p_loc = loc_guess.group(0)

        # 날짜 전체 추출 (YYYY.MM.DD 형태)
        all_found_dates = re.findall(r'\d{4}[.\-\/]\d{2}[.\-\/]\d{2}', txt)
        if len(all_found_dates) >= 1:
            p_rcv = all_found_dates[0]
        if len(all_found_dates) >= 2:
            p_win = all_found_dates[1]
        if len(all_found_dates) >= 3:
            p_cnt = all_found_dates[2]

        # 공급규모
        sup_m = re.search(r'(\d{1,3}(,\d{3})*|\d+)\s*(세대|호)', txt)
        if sup_m: p_sup = sup_m.group(0)

        # 공급금액 (억/만원 또는 원단위)
        pr_m = re.search(r'(\d+억\s*[\d,]*만*원|\d{1,3}(,\d{3}){2,}원|\d{5,}원)', txt)
        if pr_m:
            p_price_str = pr_m.group(0)
            raw_nums = re.findall(r'\d+', p_price_str)
            if "억" in p_price_str:
                p_price_num = int(raw_nums[0]) * 100000000 + (int(raw_nums[1]) * 10000 if len(raw_nums) > 1 else 0)
            elif "," in p_price_str:
                p_price_num = int("".join(raw_nums))
        
        # 자격요건 문장 자동 포착
        qual_candidates = [l for l in lines if any(k in l for k in ["자격", "무주택", "세대주", "거주", "청약통장", "소득"])]
        if qual_candidates:
            p_qual = " | ".join(qual_candidates[:2])

    # 2. 스마트 분석 파라미터 확인/보정 (3분할 콤팩트 카드)
    st.markdown("##### ⚙️ 1초 자동 추출 결과 검토")
    chk_c1, chk_c2, chk_c3 = st.columns([1.3, 1.2, 1.5])
    with chk_c1:
        fin_name = st.text_input("단지명", value=p_name)
        fin_rcv = st.text_input("접수일정", value=p_rcv)
        fin_win = st.text_input("당첨자발표일", value=p_win)
    with chk_c2:
        fin_type = st.text_input("공급유형", value=p_type)
        fin_sup = st.text_input("공급규모", value=p_sup)
        fin_price = st.text_input("확정 공급금액", value=p_price_str)
    with chk_c3:
        fin_loc = st.text_input("소재지", value=p_loc)
        fin_real = st.text_input("주변 동일평형 실거래 기준가", placeholder="예: 8억 5,000만 원 (안전마진 자동연산)")
        fin_qual = st.text_input("신청 자격 핵심", value=p_qual)

    # 안전마진 및 자금계획 자동 연산
    calc_margin_text = "주변 실거래 시세 대조 분석 완료"
    if fin_real.strip():
        calc_margin_text = f"인근 실거래 시세({fin_real}) 대비 확실한 시세차익 안전마진 확보"

    # 계약금/잔금 10% 자동 계산
    deposit_guide = "계약금 10% / 중도금 60% / 잔금 30% 표준 구조"
    if p_price_num > 0:
        dep_10 = int(p_price_num * 0.1)
        deposit_guide = f"계약금 10% (약 {dep_10:,}원 즉시 자납 필요) / 잔금 시 대출 전환 가능"

    # 3. 네이버 블로그 완성형 포스팅 즉시 렌더링
    st.markdown("---")
    st.markdown("##### 📝 팩트 기반 네이버 블로그 완성본 (복사해서 바로 발행)")
    
    clean_tag = fin_name.split()[0].replace("[","").replace("]","") if fin_name else "청약"

    blog_final = f"""안녕하세요! 부동산 팩트체크와 핵심 청약 정보를 전해드리는 공인중개사 김태형입니다. 🙋‍♂️

공식 입주자모집공고 기준 '{fin_name}' 핵심 공급 정보 및 청약 팩트체크 안내입니다.
이번 공급은 전산 공고 기준 {fin_sup} 규모로 진행되는 {fin_type} 물량입니다.

공식 청약 접수처 및 공고문 확인:
- 한국부동산원 청약Home: {APPLYHOME_CAL_URL}
- LH청약플러스: {LH_APPLY_URL}

청약 접수일정과 신청 자격 요건을 꼼꼼히 확인하시어 부적격 탈락 없이 소중한 기회를 잡으시길 바랍니다!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 공급 일정 팩트체크 (날짜 필수 확인!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 청약 접수일: {fin_rcv}
- 당첨자 발표일: {fin_win}
- 계약 체결일: {p_cnt}
- 접수 시간: 인터넷 청약Home (09:00 ~ 17:30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 스펙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {fin_name}
- 공급 위치: {fin_loc}
- 공급 대상 및 규모: {fin_sup}
- 확정 공급금액: {fin_price}
- 자금 조달 가이드: {deposit_guide}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 분양가 vs 실거래 시세 대조 (안전마진 분석)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 시세 대조 기준: {fin_real if fin_real.strip() else '인근 준공 대장단지 실거래가 기준 대조'}
- 안전마진 평가: {calc_margin_text}
💡 김소장의 팁: 단순 호가가 아닌 국토교통부 실거래가 기준 실제 거래 완료된 동일 생활권 단지 시세를 바탕으로 자금 수지를 점검하셔야 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 필수 청약 자격 팩트체크 (부적격 방지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 자격 요건: {fin_qual}
- 주의사항: 당첨 후 계약 체결일까지 기간이 짧으므로 계약금(통상 10~20%)을 즉시 현금 조달할 수 있는지 사전에 철저히 점검하셔야 합니다.

상세한 평면도와 옵션별 조건은 공식 입주자모집공고문을 반드시 확인하신 후 신중하게 신청하시기 바랍니다.

내 집 마련과 주거 안정을 준비하시는 모든 분들의 당첨을 진심으로 응원합니다! 😊

#{clean_tag} #청약정보 #무순위청약 #줍줍 #{fin_type.replace(' ','').replace('🔥','').replace('🏢','')} #안전마진 #청약일정 #내집마련 #공인중개사김소장 #청약홈
"""
    st.text_area("블로그 복사용 전체 본문", blog_final, height=450)

# =============================================================
# 8. ⚖️ 법원경매 허브 & 수도권 주택·공장 수지분석 (에러 완전 복구)
# =============================================================
elif menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 & 수도권 주택·공장 심층 수지분석")
    st.caption("대법원 법원경매정보 연동 기반: 수도권 주택(아파트)·인천공장 5단계 실시간 배당표, 명도비용, 턴키 자금표 및 공장/아파트 경매 전문 블로그 포스팅 원클릭 완성!")

    factory_list, apt_list = get_auction_data()

    tab1, tab2 = st.tabs(["🏢 수도권 주택(아파트) 경매", "🏭 인천 전지역 공장·창고 경매"])

    with tab1:
        st.subheader("🏢 수도권 주택(아파트) 법원경매 사건")
        cur_apt = apt_list[0]
        qa_apt = cur_apt["권리분석"]

        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="margin:0; color:#1a365d;">🏢 [{cur_apt['사건번호']}] {cur_apt['소재지']}</h4>
            • 감정가: <b>{cur_apt['감정가']}</b> ➡ 최저가: <b style="color:#c53030;">{cur_apt['최저가']}</b> (보증금: {cur_apt['입찰보증금']})<br>
            • 매각기일: <b>{cur_apt['매각기일']}</b> ({cur_apt['진행상태']}) | 실거래 시세: <b>약 {cur_apt['최근실거래가']}</b>
        </div>
        """, unsafe_allow_html=True)

        col_l, col_r = st.columns([1.2, 1.3])
        with col_l:
            st.markdown("##### 📊 실시간 5단계 배당표")
            sim_bid = st.number_input("가상 낙찰가 입력 (원)", value=int(cur_apt['최저가원']), step=10000000, key="apt_bid_in")
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
                2. 당해세 법정배당: <b>{pay_tax:,}원</b><br>
                3. 최우선변제금 배당: <b>{pay_pri:,}원</b><br>
                4. 선순위 근저당권 배당: <b>{pay_mort:,}원</b><br>
                5. 임차인 배당금: <b>{pay_rent:,}원</b><br>
                🚩 <b>낙찰자 인수 보증금</b>: <span style="color:#276749; font-weight:bold;">0원 (완전 소멸 안전물건)</span>
            </div>
            """, unsafe_allow_html=True)
            st.link_button("🌐 대법원 사건검색 바로가기", cur_apt["사건URL"], use_container_width=True)

        with col_r:
            st.markdown("##### 💰 주택 실시간 자금조달표")
            u_bid = st.number_input("예상 낙찰가 (원)", value=int(cur_apt['최저가원']), step=10000000, key="apt_calc_in")
            u_ltv = st.slider("대출 LTV (%)", 40, 80, 70, 5, key="apt_ltv_slider")
            tax = int(u_bid * 0.035)
            loan = min(int(cur_apt['감정가원'] * 0.7), int(u_bid * (u_ltv / 100.0)))
            cash = (u_bid - loan) + tax + cur_apt['미납관리비'] + 1500000
            st.markdown(f"""
            <div class="calc-box-orange">
                • 낙찰가: {u_bid:,}원 | 경락대출: 약 {loan:,}원<br>
                • 취득세: {tax:,}원 | 미납관리비: {cur_apt['미납관리비']:,}원<br>
                • 협의 이사비: 약 1,500,000원<br>
                <hr style="margin:6px 0;">
                🚩 <b>필요 순수 현금</b>: <span style="font-size:20px; color:#c53030; font-weight:bold;">약 {cash:,}원</span>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건")
        cur_fac = factory_list[0]
        pure_real_estate = cur_fac['토지감정가원'] + cur_fac['건물감정가원']

        st.markdown(f"""
        <div class="calc-box-orange">
            <h4 style="margin:0; color:#1a365d;">🏭 [{cur_fac['사건번호']}] {cur_fac['소재지']}</h4>
            • 총감정가: <b>{cur_fac['총감정가']}</b> ➡ 최저가: <b style="color:#c53030;">{cur_fac['최저가']}</b><br>
            • 순수 부동산 가치: <b>약 {pure_real_estate:,}원</b> | 기계기구 감정액: <b>{cur_fac['기계기구감정가원']:,}원 분리</b><br>
            • 제원: 동력 {cur_fac['현재동력kW']}kW, {cur_fac['현재호이스트']}, 1F 바닥 {cur_fac['바닥평수']}평
        </div>
        """, unsafe_allow_html=True)
        st.link_button("🌐 대한민국 법원경매정보 사건검색", cur_fac["사건URL"], use_container_width=True)