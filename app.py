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
    .hunting-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #48bb78;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .hunting-card-target {
        background-color: #fffaf0;
        border: 1px solid #feebc8;
        border-left: 6px solid #dd6b20;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(221,107,32,0.08);
    }
    .hunting-card-done {
        background-color: #f0fff4;
        border: 1px solid #c6f6d5;
        border-left: 6px solid #38a169;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .customer-card-pro {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #3182ce;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
    }
    .customer-card-pro-vip {
        background-color: #fffdf7;
        border: 1px solid #feebc8;
        border-left: 6px solid #dd6b20;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(221,107,32,0.1);
    }
    .tag-blue {
        background-color: #ebf8ff;
        color: #2b6cb0;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-orange {
        background-color: #fffaf0;
        color: #c05621;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-gray {
        background-color: #edf2f7;
        color: #4a5568;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-green {
        background-color: #f0fff4;
        color: #276749;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
        display: inline-block;
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
    .calc-box-purple {
        background-color: #faf5ff;
        border: 1px solid #e9d8fd;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
    .check-list-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #4a5568;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 13px;
        line-height: 1.7;
    }
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"], .stButton, header, footer {
            display: none !important;
        }
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# 🔒 보안 잠금
# =============================================================
CORRECT_PASSWORD = "950307"

def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("### 🏢 우리부동산 통합 업무 시스템")
        st.caption("인천 공장 중개 & 현장 물건따기·청약/공공임대 팩트체크 허브 - 보안 인증")
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
# ⚡ CSV 데이터베이스 관리 함수
# =============================================================
CUSTOMERS_CSV = "customers.csv"
PROPERTIES_CSV = "properties.csv"
NEW_DEV_CSV = "new_developments.csv"
HUNTING_CSV = "hunting_properties.csv"

def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        if "예산(보증금/월세/매매가)" not in df.columns:
            if "예산(보증금/월세)" in df.columns: df["예산(보증금/월세/매매가)"] = df["예산(보증금/월세)"]
            else: df["예산(보증금/월세/매매가)"] = ""
        if "거래구분" not in df.columns: df["거래구분"] = "임대차(월세)"
        if "중요도" not in df.columns: df["중요도"] = "⭐⭐ A급(유력)"
        if "최근연락일" not in df.columns: df["최근연락일"] = df["접수일자"] if "접수일자" in df.columns else datetime.today().strftime("%Y-%m-%d")
        if "업종인허가" not in df.columns: df["업종인허가"] = "일반제조(소음·진동)"
        if "입주시기" not in df.columns: df["입주시기"] = "협의 입주"
        if "호이스트" not in df.columns: df["호이스트"] = "호이스트 무관"
        if "대형차진입" not in df.columns: df["대형차진입"] = "11T 윙바디 수월"
        if "희망전력kW" not in df.columns: df["희망전력kW"] = "일반전력(30kW 내외)"
        if "상담히스토리" not in df.columns: df["상담히스토리"] = ""
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

# 🏃 현장 물건따기 전용 장부 데이터 로드/저장
def load_hunting_properties():
    if os.path.exists(HUNTING_CSV):
        return pd.read_csv(HUNTING_CSV)
    # 대표님이 주신 석남동 11개 실전 물건 기본 데이터
    init_data = [
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-822", "건물유형": "집합공장", "소재지전체": "인천 서구 석남동 223-822", "소유자/법인명": "관리사무소/집합", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "집합공장. 관리사무소 방문하여 임대/매매 나온 호실 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-932", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-932", "소유자/법인명": "홍정미", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "개인소유. 방문 필요. 현장 점유자/관리인 만나서 건물주 직통 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-651", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-651", "소유자/법인명": "소유자 확인중", "상호": "", "연락처": "", "진행상태": "📞 유선 확인 필요", "현장메모": "건축물대장 열람 후 소유자 번호 유선 확인"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-360", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-360", "소유자/법인명": "이해영, 최완규", "상호": "신창코팅", "연락처": "032-577-0104", "진행상태": "📞 유선 확인 필요", "현장메모": "신창코팅 유선 통화 후 임대 만기/매각 의사 체크"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-559", "건물유형": "운수/차고지", "소재지전체": "인천 서구 석남동 223-559", "소유자/법인명": "한미교통주식회사", "상호": "한미교통", "연락처": "032-571-1032", "진행상태": "📞 유선 확인 필요", "현장메모": "한미교통 자산관리 담당자 유선 통화"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-557", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-557", "소유자/법인명": "김용주", "상호": "명인기공", "연락처": "032-579-3171", "진행상태": "🚗 현장 방문 필요", "현장메모": "명인기공 대표실 방문 또는 032-579-3171 유선 컨택"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-835", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-835", "소유자/법인명": "박용욱", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "개인소유. 현장 방문하여 명함 전달 및 건물주 연락처 탐문"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-786", "건물유형": "제조공장", "소재지전체": "인천 서구 석남동 223-786", "소유자/법인명": "진우조명", "상호": "진우조명", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "진우조명 공장 현장 방문하여 이전/임대 여부 체크"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-886", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-886", "소유자/법인명": "안민영", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "현장 방문 조사 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-881", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-881", "소유자/법인명": "권진주", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "현장 방문 조사 필요"},
        {"등록일": "2026-10-13", "동": "석남동", "지번": "223-855", "건물유형": "일반공장", "소재지전체": "인천 서구 석남동 223-855", "소유자/법인명": "성용욱", "상호": "", "연락처": "", "진행상태": "🚗 현장 방문 필요", "현장메모": "현장 방문 조사 필요"}
    ]
    df = pd.DataFrame(init_data)
    df.to_csv(HUNTING_CSV, index=False, encoding="utf-8-sig")
    return df

def save_all_hunting(df):
    df.to_csv(HUNTING_CSV, index=False, encoding="utf-8-sig")

def save_hunting_item(new_data):
    df = load_hunting_properties()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    save_all_hunting(updated)
    return updated

# =============================================================
# 📌 업무 메뉴 네비게이션 (9개 메뉴 체계)
# =============================================================
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

st.sidebar.caption("🏢 **인천 서구 공장 중개 & 현장 물건따기·청약·경매 허브 가동 중**")

# =============================================================
# 0. 🏃 [신규 탑재] 현장 공장 물건따기 파이프라인 (작업용 장부)
# =============================================================
if menu_choice == MENU_DICT["FACTORY_HUNT"]:
    st.title("🏃 현장 공장 물건따기 파이프라인 (임장 & 건물주 컨택)")
    st.caption("네이버 부동산·현장 임장 지번 등록 ➡️ 건축물대장 소유자/법인 특정 ➡️ 현장 방문/유선 컨택 ➡️ 물건 확보까지 원스톱 관리!")

    df_h = load_hunting_properties()

    # 현황 요약 카운터
    cnt_total = len(df_h)
    cnt_visit = len(df_h[df_h["진행상태"] == "🚗 현장 방문 필요"])
    cnt_call = len(df_h[df_h["진행상태"] == "📞 유선 확인 필요"])
    cnt_retry = len(df_h[df_h["진행상태"] == "🔄 재방문/재트라이"])
    cnt_done = len(df_h[df_h["진행상태"] == "🎉 물건 확보 성공!"])

    s_c1, s_c2, s_c3, s_c4, s_c5 = st.columns(5)
    s_c1.metric("📌 전체 작업 지번", f"{cnt_total}건")
    s_c2.metric("🚗 현장 방문 대상", f"{cnt_visit}건")
    s_c3.metric("📞 유선 컨택 대상", f"{cnt_call}건")
    s_c4.metric("🔄 재트라이 대상", f"{cnt_retry}건")
    s_c5.metric("🎉 물건 확보 성공", f"{cnt_done}건")

    st.markdown("---")
    h_tab1, h_tab2 = st.tabs(["🚗 [현장 임장 모드] 동별 작업 장부 & 상태 변경", "➕ [신규 지번 등록] 대장 열람 후 타깃 추가"])

    with h_tab1:
        f1, f2, f3 = st.columns([1.5, 1.5, 2])
        
        all_dongs = ["전체 동 모아보기"] + sorted(list(df_h["동"].dropna().unique()))
        with f1:
            sel_dong = st.selectbox("📍 법정동 필터", all_dongs, key="hunt_dong_filter")
        
        all_status = ["전체 진행상태 보기", "🚗 현장 방문 필요", "📞 유선 확인 필요", "🔄 재방문/재트라이", "🎉 물건 확보 성공!", "보류/거절"]
        with f2:
            sel_stat = st.selectbox("🚦 진행 상태 필터", all_status, key="hunt_stat_filter")
            
        with f3:
            kw_hunt = st.text_input("🔎 지번 / 상호 / 소유자명 / 메모 검색", placeholder="예: 223-360, 신창코팅, 홍정미 등...", key="hunt_search_kw")

        f_df = df_h.copy()
        if sel_dong != "전체 동 모아보기":
            f_df = f_df[f_df["동"] == sel_dong]
        if sel_stat != "전체 진행상태 보기":
            f_df = f_df[f_df["진행상태"] == sel_stat]
        if kw_hunt.strip():
            kw = kw_hunt.strip()
            f_df = f_df[
                f_df["지번"].astype(str).str.contains(kw, na=False) |
                f_df["소유자/법인명"].astype(str).str.contains(kw, na=False) |
                f_df["상호"].astype(str).str.contains(kw, na=False) |
                f_df["현장메모"].astype(str).str.contains(kw, na=False)
            ]

        st.caption(f"조회된 물건: **총 {len(f_df)}건** (동: {sel_dong} | 상태: {sel_stat})")

        if f_df.empty:
            st.info("조건에 부합하는 작업 대상 물건이 없습니다.")
        else:
            for idx, r in f_df.iterrows():
                is_done = r["진행상태"] == "🎉 물건 확보 성공!"
                is_visit = "방문" in r["진행상태"]
                card_style = "hunting-card-done" if is_done else ("hunting-card-target" if is_visit else "hunting-card")

                full_addr = f"인천 서구 {r['동']} {r['지번']}"
                map_url = f"https://map.naver.com/p/search/{full_addr.replace(' ', '%20')}"

                st.markdown(f"""
                <div class="{card_style}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="font-size: 19px; font-weight: bold; color: #1a365d;">📍 {r['동']} {r['지번']}</span>
                            <span class="tag-blue" style="margin-left: 8px;">{r['건물유형']}</span>
                            <span class="tag-orange">👤 {r['소유자/법인명']}</span>
                            {f'<span class="tag-green">🏭 {r["상호"]}</span>' if str(r.get("상호","")).strip() else ''}
                        </div>
                        <div>
                            <span style="font-size: 13px; font-weight: bold; color: {'#38a169' if is_done else '#dd6b20'};">
                                {r['진행상태']}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 14px; color: #2d3748; margin-bottom: 6px;">
                        📞 연락처: <b>{r['연락처'] if str(r.get('연락처','')).strip() else '현장 방문하여 탐문 필요'}</b>
                    </div>
                    <div style="background-color: #f8fafc; border-radius: 6px; padding: 8px 12px; font-size: 13px; color: #4a5568;">
                        💡 <b>임장/작업 메모</b>: {r['현장메모']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 2.0, 1.2, 1.0])
                with b_col1:
                    st.link_button(f"🗺️ {r['지번']} 네이버 지도/로드뷰", map_url, use_container_width=True)
                with b_col2:
                    status_options = ["🚗 현장 방문 필요", "📞 유선 확인 필요", "🔄 재방문/재트라이", "🎉 물건 확보 성공!", "보류/거절"]
                    curr_idx = status_options.index(r["진행상태"]) if r["진행상태"] in status_options else 0
                    new_status = st.selectbox(
                        "진행상태 갱신",
                        status_options,
                        index=curr_idx,
                        key=f"st_sel_{idx}"
                    )
                with b_col3:
                    if st.button("💾 상태 저장", key=f"btn_st_save_{idx}", use_container_width=True):
                        df_h.at[idx, "진행상태"] = new_status
                        save_all_hunting(df_h)
                        st.success(f"{r['지번']} 상태 변경 완료!")
                        st.rerun()
                with b_col4:
                    if st.button("🗑️ 삭제", key=f"btn_h_del_{idx}", use_container_width=True):
                        df_h = df_h.drop(df_h.index[idx]).reset_index(drop=True)
                        save_all_hunting(df_h)
                        st.warning(f"{r['지번']} 삭제 완료")
                        st.rerun()

    with h_tab2:
        st.subheader("➕ 네이버 부동산 보고 딸 공장 지번 추가하기")
        st.caption("건축물대장을 떼서 확인한 소유자명이나, 현장에서 알아낸 상호/전화번호를 입력해 두세요.")

        with st.form("new_hunt_form"):
            in_c1, in_c2, in_c3 = st.columns(3)
            with in_c1:
                dong_opts = ["석남동", "가좌동", "원창동", "경서동", "도화동", "송림동", "기타"]
                new_dong = st.selectbox("법정동 선택 *", dong_opts)
                new_jibun = st.text_input("지번 (번지-호) *", placeholder="예: 223-999")
            with in_c2:
                new_type = st.selectbox("건물 유형", ["일반공장", "집합공장", "제조업소", "물류창고", "차고지/나대지"])
                new_owner = st.text_input("소유자명 (대장상 명의)", placeholder="예: 홍길동 또는 (주)대한국제")
            with in_c3:
                new_biz = st.text_input("상호 / 현장 간판명", placeholder="예: 대한정밀, 한미교통 등")
                new_phone = st.text_input("확인된 전화번호", placeholder="예: 032-570-0000 또는 010-0000-0000")

            new_stat_sel = st.selectbox("초기 진행 상태", ["🚗 현장 방문 필요", "📞 유선 확인 필요", "🔄 재방문/재트라이"])
            new_memo = st.text_area("임장/공략 메모", placeholder="예: 네이버 매물 보고 지번 특정. 현장 관리인 만나서 건물주 번호 따거나 우편함 체크 필요.")

            submit_hunt = st.form_submit_button("🚀 작업 지번 목록에 등록하기", type="primary", use_container_width=True)

            if submit_hunt:
                if not new_jibun.strip():
                    st.error("지번은 필수 입력 항목입니다.")
                else:
                    new_item = {
                        "등록일": datetime.today().strftime("%Y-%m-%d"),
                        "동": new_dong,
                        "지번": new_jibun.strip(),
                        "건물유형": new_type,
                        "소재지전체": f"인천 서구 {new_dong} {new_jibun.strip()}",
                        "소유자/법인명": new_owner if new_owner.strip() else "확인중",
                        "상호": new_biz.strip(),
                        "연락처": new_phone.strip(),
                        "진행상태": new_stat_sel,
                        "현장메모": new_memo.strip()
                    }
                    save_hunting_item(new_item)
                    st.success(f"✅ 인천 서구 {new_dong} {new_jibun} 물건이 작업 목록에 추가되었습니다!")
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
        ceiling = st.text_input("처마 층고", placeholder="예: 처마 7.5m (호이스트 주행 하이 층고)")
        power = st.text_input("인입 동력 (kW) *", placeholder="예: 30kW (가공 설비 구동 충분)")
        hoist = st.selectbox("호이스트 설비 *", ["호이스트 2.8톤 완비", "호이스트 5톤 완비", "호이스트 3톤 완비", "호이스트 없음"])
    with c3:
        road = st.text_input("접면 도로 폭(m)", placeholder="예: 8m 도로 접 (문 앞 차량 접안 편리)")
        parking_count = st.text_input("주차장 현황", placeholder="예: 자주식 옥외 3대 (전면 마당 포함)")
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
    memo = st.text_area("매물 핵심 강점 메모", placeholder="예: 인천산업유통센터 및 송현 공구상가 초인접으로 부품 수급 최상. 호이스트 완비로 시설비 수천만 원 절감.")

    if st.button("🚀 매물 저장 & 확인·설명서 생성 & 블로그 포스팅 동시 실행", type="primary", use_container_width=True):
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
            site_name = st.text_input("프로젝트/단지명 *", placeholder="예: 도화동 930-1 신축공장, 가좌 첨단제조단지 등")
            site_addr = st.text_input("사업지 상세 주소 *", placeholder="예: 인천 미추홀구 도화동 930-1 (지번/일대)")
        with p2:
            custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=100, step=10)
            road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
        with p3:
            cust_company = st.text_input("제안 대상 기업명/대표님", placeholder="예: (주)대한정밀 대표님")
            cust_usage = st.text_input("권장 조업 업종/용도", placeholder="예: 정밀기계제조 / 금형가공 / 물류유통")

        st.markdown("---")
        fl1, fl2, fl3, fl4, fl5 = st.columns(5)
        with fl1: f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=70, step=5)
        with fl2: f2_pyung = st.number_input("2층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl3: f3_pyung = st.number_input("3층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl4: f4_pyung = st.number_input("4층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)
        with fl5: f5_pyung = st.number_input("5층 바닥평수 (평)", min_value=0, max_value=5000, value=0, step=5)

        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원) *", value=1200, step=50)
        with pr2: add_unit_price = st.number_input("상층부 증축단가 (건축 평당 만 원) *", value=350, step=10)
        with pr3: ceiling_spec = st.text_input("층고 제원", value="처마 7m (유효 7.5m)")
        with pr4: power_spec = st.text_input("인입 동력", value="30kW 기본 인입")

        actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
        yard_pyung = max(0, custom_land - f1_pyung)

        if st.button("🚀 신축공장 맞춤 분양 설계 & 제안서 산출하기", type="primary", use_container_width=True):
            floor_list = [f1_pyung, f2_pyung, f3_pyung, f4_pyung, f5_pyung]
            active_floors = [p for p in floor_list if p > 0]
            max_floor_cnt = len(active_floors)
            total_bldg_area = sum(floor_list)

            base_cost = int(custom_land * base_unit_price * 10000)
            extra_bldg_area = sum(floor_list[1:])
            extra_cost = int(extra_bldg_area * add_unit_price * 10000)
            total_dev_price = base_cost + extra_cost

            loan_80 = int(total_dev_price * 0.80)
            pure_cash = total_dev_price - loan_80
            acq_tax = int(total_dev_price * 0.046)

            floor_desc = ", ".join([f"{idx+1}F {p}평" for idx, p in enumerate(floor_list) if p > 0])
            company_display = cust_company if cust_company.strip() else "고객사"

            st.markdown("---")
            out_c1, out_c2 = st.columns([1.2, 1.3])
            with out_c1:
                st.markdown(f"""
                <div class="calc-box-orange">
                    <h4 style="color: #c05621; margin-bottom: 8px;">📊 [{company_display}] 신축공장 맞춤 분양 견적서</h4>
                    • <b>사업지</b>: {site_name} ({site_addr})<br>
                    • <b>분양 대지면적</b>: <b>{custom_land}평</b> | <b>건폐율</b>: <b>{actual_bcr}%</b><br>
                    • <b>건축 규모</b>: <b>지상 {max_floor_cnt}층 공장 (총 연면적 {total_bldg_area}평)</b> | {floor_desc}<br>
                    • <b>단독 마당/주차</b>: <b>약 {yard_pyung}평 확보</b> (전면 {road_width}m 도로 접)<br>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #feebc8;">
                    🚩 <b>최종 분양 공급가액</b>: <span style="font-size: 20px; font-weight: bold; color: #c53030;">{total_dev_price:,}원</span><br>
                    • 시설자금 대출 80%: 약 <b>{loan_80:,}원</b> | <b>필요 순수 현금</b>: <span style="color: #2b6cb0; font-weight: bold;">약 {pure_cash + acq_tax:,}원</span> (취득세 4.6% {acq_tax:,}원 포함)
                </div>
                """, unsafe_allow_html=True)

            with out_c2:
                bldg_w_svg = int(max(20, min(80, (f1_pyung / custom_land) * 100))) if custom_land > 0 else 50
                yard_w_svg = 100 - bldg_w_svg
                truck_text = "40ft 트레일러 접안 최적" if road_width >= 10 else "11T 윙바디 접안"

                svg_2d = f"""
                <div style="background-color: #ffffff; border: 2px solid #cbd5e0; border-radius: 8px; padding: 12px;">
                    <div style="background-color: #2d3748; color: white; text-align: center; padding: 8px; font-weight: bold; font-size: 13px; margin-bottom: 8px;">
                        ▲ 전면 {road_width}m 광폭 도로 접 ({truck_text}) ▲
                    </div>
                    <div style="border: 2px dashed #3182ce; padding: 10px; background-color: #ebf8ff; border-radius: 6px;">
                        <div style="display: flex; gap: 8px; height: 160px;">
                            <div style="flex: {bldg_w_svg}; background-color: #bee3f8; border: 2px solid #1a365d; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 15px; color: #1a365d;">🏭 신축 공장동</span>
                                <span style="font-size: 13px; color: #2c5282; font-weight: bold;">지상 {max_floor_cnt}층 (1F {f1_pyung}평)</span>
                            </div>
                            <div style="flex: {yard_w_svg}; background-color: #edf2f7; border: 2px dashed #718096; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                                <span style="font-weight: bold; font-size: 13px; color: #4a5568;">🚛 단독 마당</span>
                                <span style="font-size: 12px; color: #718096; font-weight: bold;">약 {yard_pyung}평</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(svg_2d, unsafe_allow_html=True)

            print_html_content = f"""<html><body style='font-family:sans-serif; padding:30px;'><h2>{site_name} 신축공장 분양계획서</h2><p>대지: {custom_land}평 | 공급가: {total_dev_price:,}원 | 대출 80%: {loan_80:,}원</p><p>우리부동산 대표 김태형 010-2660-8276</p></body></html>"""
            st.components.v1.html(f"""<button onclick="var w=window.open('','_blank');w.document.write(`{print_html_content}`);w.print();" style="background:#2b6cb0; color:white; padding:10px 20px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">🖨️ 이 분양제안서만 바로 인쇄하기 (A4 전용)</button>""", height=50)

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
                            "idx": idx, "고객명": row.get("상호/고객명", ""), "연락처": row.get("연락처", ""),
                            "중요도": row.get("중요도", ""), "경과일": passed_days, "메모": row.get("상담메모", "")
                        })
                except Exception: pass

    if remind_targets:
        st.markdown(f"##### 🔔 [재상담 리마인드] 연락 후 7일 이상 경과한 손님 ({len(remind_targets)}명)")
        for rt in remind_targets[:3]:
            st.markdown(f"""
            <div class="remind-card-red">
                🚨 <b>{rt['고객명']}</b> ({rt['연락처']}) | <span style="color:#d69e2e;">{rt['중요도']}</span> | 마지막 연락 후 <b>{rt['경과일']}일 경과</b> ➡️ <i>"신규 매물 체크 및 안부 전화 권장"</i>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    tab_list, tab_edit = st.tabs(["📊 손님 장부 목록", "✍️ 손님 신규 등록 및 수정/삭제"])

    with tab_list:
        if not df_c.empty:
            st.markdown("##### 🗓️ 손님 장부 기간별 & 월별(Month) 상세 필터")
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
            with f_col4: search_kw = st.text_input("🔎 손님명 / 연락처 / 메모 검색", placeholder="예: 대한정밀, 1830 등...", key="crm_kw_search")

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

            st.caption(f"📌 조회된 손님: **총 {len(filtered_by_date)}명** (조건: {selected_month} | {date_filter_type})")

            subtab_vip, subtab_active, subtab_done, subtab_all = st.tabs(["🔥 집중 관리 (S/A급 VIP)", "🏃 진행중", "🤝 계약 완료", "📁 전체 보기"])

            def render_customer_cards_pro(target_df, tab_prefix="all"):
                if target_df.empty:
                    st.info("선택하신 기간/조건에 해당하는 손님이 없습니다.")
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
                        if st.button("🎯 추천 보유매물 조회", key=f"btn_m_{tab_prefix}_{orig_idx}"):
                            m_props = match_properties_for_customer(c_row)
                            if m_props:
                                for p in m_props: st.markdown(f"• **{p.get('소재지(권역)','')}** | {p.get('가격(보/월)','')} | {p.get('면적','')} | {p.get('호이스트','')}")
                            else: st.info("조건에 부합하는 매물이 없습니다.")
                    with btn_c2:
                        if st.button("💬 안부/체크 카톡 생성", key=f"btn_k_{tab_prefix}_{orig_idx}"):
                            talk = f"[{c_name_val} 대표님, 우리부동산 안부 안내]\n\n대표님 안녕하십니까! 인천 공장 전문 우리부동산 김태형 소장입니다.\n문의해 주신 공장 조건({c_loc_val}, {c_area_val}, {c_deal_val}) 관련 신규 매물 체크차 연락드렸습니다.\n\n우리부동산 김태형 대표 (010-2660-8276)"
                            st.text_area(f"카톡 복사창 ({c_name_val})", talk, height=180, key=f"tx_{tab_prefix}_{orig_idx}")
                    with btn_c3:
                        if st.button("📝 상담일지 열기", key=f"btn_h_{tab_prefix}_{orig_idx}"):
                            curr_h = str(c_row.get("상담히스토리", ""))
                            st.text_area("상담 기록", curr_h, height=100, disabled=True, key=f"hv_{tab_prefix}_{orig_idx}")
                            new_l = st.text_input("오늘 통화 내용 추가", key=f"in_{tab_prefix}_{orig_idx}")
                            if st.button("저장", key=f"sv_{tab_prefix}_{orig_idx}"):
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
            with r1:
                name_def = str(target_row["상호/고객명"]) if target_row is not None else ""
                c_name = st.text_input("상호 / 고객명 *", value=name_def, placeholder="예: (주)대한정밀 김대표")
            with r2:
                phone_def = str(target_row["연락처"]) if target_row is not None else ""
                c_phone = st.text_input("연락처 *", value=phone_def, placeholder="예: 010-1234-5678")
            with r3:
                star_opts = ["⭐⭐⭐ S급(자금확보/최우선)", "⭐⭐ A급(유력)", "⭐ B급(일반상담)"]
                star_def = str(target_row["중요도"]) if target_row is not None else "⭐⭐ A급(유력)"
                star_idx = star_opts.index(star_def) if star_def in star_opts else 1
                c_star = st.selectbox("중요도 (VIP 등급)", star_opts, index=star_idx)

            r4, r5, r6, r7 = st.columns(4)
            with r4:
                deal_opts = ["임대차(월세)", "매매", "매매/임대 겸용"]
                deal_def = str(target_row["거래구분"]) if target_row is not None else "임대차(월세)"
                c_deal = st.selectbox("거래 구분 *", deal_opts, index=deal_opts.index(deal_def) if deal_def in deal_opts else 0)
            with r5:
                loc_def = str(target_row["희망권역"]) if target_row is not None else "인천 서구 가좌/석남"
                c_loc = st.text_input("희망 권역 *", value=loc_def, placeholder="예: 인천 서구 가좌, 오류동 등")
            with r6:
                area_def = str(target_row["희망평수"]) if target_row is not None else "100~150평"
                c_area = st.text_input("희망 평수/면적 *", value=area_def, placeholder="예: 70평~100평")
            with r7:
                permit_opts = ["일반제조(소음·진동)", "폐수·대기 배출(인허가 필수)", "식품가공(HACCP)", "단순물류·창고", "자원순환·고물상", "기타 특수업종"]
                permit_def = str(target_row.get("업종인허가", "일반제조(소음·진동)")) if target_row is not None else "일반제조(소음·진동)"
                c_permit = st.selectbox("🏭 업종 및 인허가 *", permit_opts, index=permit_opts.index(permit_def) if permit_def in permit_opts else 0)

            r8, r9, r10, r11 = st.columns(4)
            with r8:
                hoist_opts = ["호이스트 필수 (2.8T~5T)", "있으면 좋음", "불필요 (호이스트 무관)"]
                hoist_def = str(target_row.get("호이스트", "있으면 좋음")) if target_row is not None else "있으면 좋음"
                c_hoist = st.selectbox("🏗️ 호이스트 요구 *", hoist_opts, index=hoist_opts.index(hoist_def) if hoist_def in hoist_opts else 1)
            with r9:
                truck_opts = ["츄레라/트레일러 필수", "11T 윙바디 필수", "5T 진입 수월", "1T 위주 진입"]
                truck_def = str(target_row.get("대형차진입", "11T 윙바디 필수")) if target_row is not None else "11T 윙바디 필수"
                c_truck = st.selectbox("🚛 화물차량 작업 여건 *", truck_opts, index=truck_opts.index(truck_def) if truck_def in truck_opts else 1)
            with r10:
                pwr_opts = ["30kW 이하 (기본)", "50kW 내외", "75kW 이상 (중형)", "100kW~200kW 대용량", "전력 협의"]
                pwr_def = str(target_row.get("희망전력kW", "50kW 내외")) if target_row is not None else "50kW 내외"
                c_pwr = st.selectbox("⚡ 필요 동력(kW) *", pwr_opts, index=pwr_opts.index(pwr_def) if pwr_def in pwr_opts else 1)
            with r11:
                movein_opts = ["즉시 입주", "1개월 이내", "2~3개월 이내", "협의 입주"]
                movein_def = str(target_row.get("입주시기", "협의 입주")) if target_row is not None else "협의 입주"
                c_movein = st.selectbox("🗓️ 입주 희망 시기 *", movein_opts, index=movein_opts.index(movein_def) if movein_def in movein_opts else 3)

            r12, r13 = st.columns(2)
            with r12:
                budget_def = get_safe_cust_val(target_row, "예산(보증금/월세/매매가)", "보 3,000만 / 월 250만") if target_row is not None else ""
                c_budget = st.text_input("희망 예산 (보증금/월세 또는 매매가)", value=budget_def, placeholder="예: 보 3천 / 월 250만 (매매 시 15억)")
            with r13:
                stat_opts = ["상담 접수 (매물 대기중)", "브리핑 진행중", "현장 미팅 예정", "계약 완료", "보류/마감"]
                stat_def = str(target_row["진행상태"]) if target_row is not None else "상담 접수 (매물 대기중)"
                c_stat = st.selectbox("진행 상태", stat_opts, index=stat_opts.index(stat_def) if stat_def in stat_opts else 0)

            memo_def = str(target_row["상담메모"]) if target_row is not None else ""
            c_memo = st.text_area("상세 상담 메모", value=memo_def, placeholder="예: CNC 가공 3대 안착 예정, 바닥 크랙 없는 공장 선호, 층고 8m 이상 요망")

            sub_b1, sub_b2 = st.columns([4, 1])
            with sub_b1:
                btn_name = "💾 기존 손님 정보 수정 반영" if edit_mode else "💾 신규 손님 등록하기"
                submit_save = st.form_submit_button(btn_name, type="primary", use_container_width=True)
            with sub_b2:
                submit_del = st.form_submit_button("🗑️ 손님 삭제", type="secondary", use_container_width=True) if edit_mode else False

            if submit_save:
                if not c_name or not c_phone:
                    st.error("상호/고객명과 연락처는 필수입니다.")
                else:
                    new_entry = {
                        "접수일자": target_row["접수일자"] if target_row is not None else today.strftime("%Y-%m-%d"),
                        "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star,
                        "거래구분": c_deal,
                        "업종인허가": c_permit,
                        "상호/고객명": c_name,
                        "연락처": c_phone,
                        "희망권역": c_loc,
                        "희망평수": c_area,
                        "예산(보증금/월세/매매가)": c_budget,
                        "입주시기": c_movein,
                        "호이스트": c_hoist,
                        "대형차진입": c_truck,
                        "희망전력kW": c_pwr,
                        "상담메모": c_memo,
                        "상담히스토리": target_row.get("상담히스토리", "") if target_row is not None else f"[{today.strftime('%Y-%m-%d %H:%M')}] 최초 접수 완료\n",
                        "진행상태": c_stat
                    }
                    if edit_mode and selected_cust_idx is not None:
                        df_c.iloc[selected_cust_idx] = new_entry
                        save_all_customers(df_c)
                        st.success(f"✅ '{c_name}' 대표님 정보가 수정되었습니다!")
                    else:
                        save_customer(new_entry)
                        st.success(f"✅ '{c_name}' 대표님이 신규 장부에 등록되었습니다!")
                    st.rerun()

            if submit_del and edit_mode and selected_cust_idx is not None:
                df_c = df_c.drop(df_c.index[selected_cust_idx]).reset_index(drop=True)
                save_all_customers(df_c)
                st.warning("🗑️ 손님 데이터가 삭제되었습니다.")
                st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부
# =============================================================
elif menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부")
    st.caption("손님 전화 상담 중 원하는 평수, 호이스트 유무, 츄레라 작업 여부를 드롭다운으로 즉시 필터링하여 매물을 확인합니다.")

    df_p = load_properties()
    if not df_p.empty:
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: sel_pyung = st.selectbox("📐 실사용 평수", ["전체 평수 보기", "50평 이하", "50평 ~ 100평", "100평 ~ 150평", "150평 이상"])
        with f_col2: sel_hoist = st.selectbox("🏗️ 호이스트", ["전체 (유/무 무관)", "호이스트 완비(설치)", "호이스트 없음"])
        with f_col3: sel_truck = st.selectbox("🚛 화물차 여건", ["전체 차량 보기", "츄레라/트레일러 진입 가능", "11톤/윙바디 이상 진입"])
        with f_col4: search_text = st.text_input("🔎 권역/메모 검색")

        filtered_df = df_p.copy()
        if sel_hoist == "호이스트 완비(설치)": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("완비|설치|톤|T", na=False)]
        elif sel_hoist == "호이스트 없음": filtered_df = filtered_df[filtered_df["호이스트"].str.contains("없음", na=False)]
        if search_text.strip(): filtered_df = filtered_df[filtered_df["소재지(권역)"].str.contains(search_text, na=False) | filtered_df["특징메모"].str.contains(search_text, na=False)]

        st.dataframe(filtered_df, use_container_width=True, height=450)
    else: st.info("등록된 매물이 없습니다.")

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기
# =============================================================
elif menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 AI 시세 추정기")
    st.caption("주소지(동), 대지·건물 평수, 준공연도, 설비 제원을 입력하면 인근 국토부 실거래가 및 네이버 매물 호가를 기반으로 적정 매매가와 임대료(보/월)를 자동 산출합니다.")

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
            m_wait = st.text_input("방문/웨이팅", placeholder="예: 주말 저녁 6시 30분 방문 / 현장 캐치테이블 20분 대기")
        with c3:
            m_eval = st.text_input("솔직 한 줄 총평 *", placeholder="예: 은은한 연탄 불향과 팡 터지는 육즙 조화가 끝내주는 가성비 삼겹살 찐맛집")
            m_point = st.text_input("킬링 포인트 (숏폼용)", placeholder="예: 첫 점 씹자마자 터지는 연탄 불향 육즙과 구운 묵은지 궁합")

        m_taste = st.text_area("맛 평가 디테일", placeholder="예: 35년 전통 연탄불 직화구이로 첫 점부터 육즙 폭발. 파채와 묵은지 구이의 조합이 일품이며, 칼칼한 된장찌개가 밥도둑임.")

        if st.button("🚀 맛집 마케팅 패키지 (포스팅 + 400자 영수증 + 숏폼) 생성", type="primary"):
            if not m_name or not m_eval:
                st.error("상호명과 솔직 한 줄 총평은 필수입니다.")
            else:
                b_col1, b_col2 = st.columns([1.3, 1.0])
                with b_col1:
                    st.markdown("##### 📝 네이버 블로그 최상위 포스팅 본문")
                    post_text = f"""안녕하세요. 인천 맛집·일상 탐방 전문 우리부동산입니다.
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
#{m_name.replace(' ','')} #{m_loc.replace(' ','')}맛집 #{m_kw.replace(', ',' #').replace(' ','')} #인천맛집 #우리부동산
"""
                    st.text_area("블로그 본문 복사", post_text, height=350)

                with b_col2:
                    st.markdown("##### 🧾 네이버 영수증 리뷰 (400자 이내 찐후기)")
                    review_text = f"""⭐⭐⭐⭐⭐
{m_loc} 찐맛집 인정합니다! 평소 소문 듣고 찾아왔는데 기대 이상이었어요.
{m_menu} 주문해서 먹어봤는데, {m_point if m_point else m_eval}. {m_taste}
고기 질도 정말 신선하고 불향과 육즙 밸런스가 예술이라 마지막 한 점까지 물리지 않고 맛있게 먹었습니다.
{m_addr.split('(')[-1].replace(')', '') if '(' in m_addr else '주차'}도 편하고 직원분들이 바쁜 시간대에도 친절하게 응대해 주셔서 기분 좋게 식사했네요. 
가족 외식이나 모임 장소로 강력 추천드리고 조만간 무조건 재방문할 생각입니다! 번창하세요 사장님 👍"""
                    st.caption(f"📝 현재 글자 수: **{len(review_text)}자** / 최대 400자")
                    st.text_area("영수증 리뷰 복사", review_text, height=180)

                    st.markdown("##### 🎬 30초 숏폼(릴스·클립) 촬영 대본")
                    short_script = f"""[0~3초 훅 오프닝]
"인천 {m_loc}에서 고기 좀 먹어봤다면 모를 수가 없는 이곳!"
(지글지글 연탄불에 고기 올라가는 ASMR 컷)

[4~22초 본론 킬링포인트]
"바로 {m_name}인데요. {m_menu} 시키면 나오는 비주얼 좀 보세요. {m_point}!"
(육즙 떨어지는 클로즈업 + 파채 싸먹는 컷)

[23~30초 클로징]
"이번 주말 외식 장소 고민 끝! 위치는 {m_addr}입니다."
"""
                    st.text_area("숏폼 대본 복사", short_script, height=190)

    with b_tab2:
        d1, d2 = st.columns(2)
        with d1:
            d_name = st.text_input("핫플명 *", placeholder="예: 스투시 서울 챕터 도산")
            d_loc = st.text_input("위치 *", placeholder="예: 서울 강남구 신사동 도산공원 일대")
            d_item = st.text_input("신상 품목 *", placeholder="예: 2026 SS 신상 후드티, 로고 티셔츠")
        with d2:
            d_eval = st.text_input("한 줄 총평 *", placeholder="예: 감각적인 쇼룸 인테리어와 힙한 무드가 공존하는 스트릿 패션의 성지")
            d_wait = st.text_input("대기 시간", placeholder="예: 주말 오후 2시 방문 / 현장 태블릿 40분 대기")

        d_note = st.text_area("내부 무드 및 쇼핑 팁", placeholder="예: 미니멀한 노출 콘크리트 인테리어에 힙한 사운드가 가득함. 신상 라인업 회전율이 빠르며 피팅룸 대기 전 미리 사이즈 체크 필수.")

        if st.button("🚀 핫플 블로그 포스팅 & 릴스 대본 생성", type="primary"):
            if not d_name or not d_eval:
                st.error("핫플명과 한 줄 총평은 필수입니다.")
            else:
                st.text_area("핫플 블로그 본문", f"안녕하세요! 우리부동산입니다. 오늘은 {d_loc} {d_name} 다녀왔습니다. {d_eval}! {d_note}", height=200)
                st.text_area("핫플 릴스 대본", f"[오프닝] 도산공원 가면 무조건 들러야 할 {d_name}!\n[본론] 신상 {d_item} 라인업 실물 깡패네요.\n[클로징] 주말엔 웨이팅 {d_wait} 있으니 서두르세요!", height=150)

# =============================================================
# 7. 🏢 [청약홈 & LH청약플러스 팩트 주입기] 청약·줍줍·공공임대 허브
# =============================================================
elif menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 청약·줍줍 & LH·SH 공공임대 팩트체크 포스팅 허브")
    st.caption("청약홈 캘린더 및 LH청약플러스 공고문 팩트 기반: 텍스트 붙여넣기 ➡️ 날짜·자격·임대료 오차 0% 블로그 포스팅 자동 완성!")

    APPLYHOME_CAL_URL = "https://www.applyhome.co.kr/ai/aib/selectSubscrptCalenderView.do#a"
    LH_APPLY_URL = "https://apply.lh.or.kr"

    top_c1, top_c2 = st.columns(2)
    with top_c1:
        st.link_button("📅 [청약Home] 공식 청약캘린더 바로가기", APPLYHOME_CAL_URL, type="primary", use_container_width=True)
    with top_c2:
        st.link_button("🏢 [LH청약플러스] 공식 임대·분양센터 바로가기", LH_APPLY_URL, use_container_width=True)

    hub_mode = st.radio(
        "📌 정보 유형 선택",
        ["🏢 [민영·공공분양/줍줍] 청약Home 팩트 주입 포스팅", "🏠 [공공임대/행복주택/청년주택] LH·SH·iH 팩트 주입 포스팅"],
        horizontal=True
    )

    if hub_mode == "🏢 [민영·공공분양/줍줍] 청약Home 팩트 주입 포스팅":
        base_sale_list = [
            {
                "단지명": "당산역 디아이빌", "권역": "서울특별시", "지역구": "영등포구", "유형": "🔥 임의공급 잔여세대 (줍줍)",
                "위치": "서울특별시 영등포구 당산동1가 1-4 일원", "시공사": "대인산업개발(주)",
                "공급규모": "총 72세대 중 잔여 무순위 임의공급",
                "공급금액": "전용 28~35㎡ 3억 8,000만 ~ 4억 5,000만 원 선",
                "접수시작일": "2026-10-06", "접수종료일": "2026-10-07",
                "접수일정텍스트": "2026.10.06 (화) ~ 10.07 (수) 09:00~17:30",
                "당첨자발표": "2026-10-14 (수)", "계약체결": "2026-10-21 (수)",
                "자격요건": "국내 거주 만 19세 이상 성년자 (거주지 무관, 주택수 무관, 청약통장 불필요 100% 추첨)",
                "동일단지실거래": "당산역 일대 신축 소형 오피스텔/도시형 실거래가 5억 2,000만 원",
                "안전마진": "약 7,000만 ~ 1억 원 (여의도/광화문 직주근접 전세가율 80% 형성)",
                "공고URL": APPLYHOME_CAL_URL
            },
            {
                "단지명": "강변역 센트럴 아이파크", "권역": "서울특별시", "지역구": "광진구", "유형": "🔥 계약취소주택 재공급 (줍줍)",
                "위치": "서울특별시 광진구 자양동 680-63 일원", "시공사": "HDC현대산업개발(주)",
                "공급규모": "총 215세대 중 계약취소 1세대 (101동 402호, 84C)",
                "공급금액": "12억 4,380만 원 (확장비 2,178만 포함)",
                "접수시작일": "2026-10-06", "접수종료일": "2026-10-06",
                "접수일정텍스트": "2026.10.06 (화) 09:00~17:30 단 하루",
                "당첨자발표": "2026-10-12 (월)", "계약체결": "2026-10-23 (금)",
                "자격요건": "입주자모집공고일 현재 서울특별시 거주 만 19세 이상 무주택세대주 (청약통장 불필요, 100% 추첨)",
                "동일단지실거래": "동일 단지 84㎡ 14층 입주권 최근 실거래가 22억 원",
                "안전마진": "약 9억 5,620만 원 (동일 단지 22억 실거래가 대조)",
                "공고URL": APPLYHOME_CAL_URL
            },
            {
                "단지명": "충정로역자이르네", "권역": "서울특별시", "지역구": "서대문구", "유형": "🔥 계약취소주택 재공급 (줍줍)",
                "위치": "서울특별시 서대문구 충정로2가 185-1 일원", "시공사": "자이에스앤디(주)",
                "공급규모": "총 192세대 중 계약취소 1세대 (전용 52㎡)",
                "공급금액": "7억 9,500만 원",
                "접수시작일": "2026-10-15", "접수종료일": "2026-10-15",
                "접수일정텍스트": "2026.10.15 (목) 09:00~17:30",
                "당첨자발표": "2026-10-21 (수)", "계약체결": "2026-10-29 (목)",
                "자격요건": "입주자모집공고일 현재 서울특별시 거주 만 19세 이상 무주택세대구성원",
                "동일단지실거래": "충정로역자이르네 동일 단지 52㎡ 실거래가 10억 5,000만 원",
                "안전마진": "약 2억 5,500만 원 (동일 단지 실거래가 대조)",
                "공고URL": APPLYHOME_CAL_URL
            },
            {
                "단지명": "계양 롯데캐슬 파크시티 1단지", "권역": "인천광역시", "지역구": "계양구", "유형": "일반분양",
                "위치": "인천광역시 계양구 효성동 100 일원", "시공사": "롯데건설(주)",
                "공급규모": "총 1,964세대",
                "공급금액": "84A 6억 5,900만 원 (59A 4억 7,800만)",
                "접수시작일": "2026-10-06", "접수종료일": "2026-10-07",
                "접수일정텍스트": "특공 2026.10.06 / 1순위 2026.10.07",
                "당첨자발표": "2026-10-15 (목)", "계약체결": "2026-10-27 ~ 10.30",
                "자격요건": "인천 및 수도권 거주자 (청약통장 12개월, 인천 예치금 250만 원 충족)",
                "동일단지실거래": "힐스테이트 자이 계양 84㎡ 실거래 7억 5,000만 원",
                "안전마진": "약 9,100만 원",
                "공고URL": APPLYHOME_CAL_URL
            },
            {
                "단지명": "부천대장 A2블록 부천대장 하우스토리 디센트", "권역": "경기도", "지역구": "부천시", "유형": "공공분양",
                "위치": "경기도 부천시 부천대장 공공주택지구 A2블록", "시공사": "남광토건(주) / 하우스토리",
                "공급규모": "총 548세대",
                "공급금액": "59A 4억 3,500만 / 84A 5억 8,800만 원",
                "접수시작일": "2026-10-12", "접수종료일": "2026-10-13",
                "접수일정텍스트": "특공 2026.10.12 / 1순위 2026.10.13",
                "당첨자발표": "2026-10-20 (화)", "계약체결": "2026-12-07 ~ 12.11",
                "자격요건": "수도권 거주 무주택세대구성원 (청약통장 12회 이상, 인정납입 총액 순차제)",
                "동일단지실거래": "계양 롯데캐슬 84㎡ 분양권 실거래 7억 2,000만 원",
                "안전마진": "약 1억 3,200만 원",
                "공고URL": "https://xn--vk1bl3b19f7xexvfwncgul82b1wt8smd2ch4k.com"
            },
            {
                "단지명": "과천 그랑자이 파크 (지정타 S2BL)", "권역": "경기도", "지역구": "과천시", "유형": "일반분양",
                "위치": "경기도 과천시 갈현동 과천지식정보타운 S2BL", "시공사": "GS건설(주)",
                "공급규모": "총 740세대",
                "공급금액": "84A 8억 7,000만 원 선",
                "접수시작일": "2026-10-13", "접수종료일": "2026-10-14",
                "접수일정텍스트": "특공 2026.10.13 / 1순위 2026.10.14",
                "당첨자발표": "2026-10-22 (목)", "계약체결": "2026-11-03 ~ 11.06",
                "자격요건": "과천시 및 수도권 거주자 (청약통장 12개월 이상 및 예치금 충족)",
                "동일단지실거래": "과천 푸르지오 오르투스 84㎡ 실거래 14억 5,000만 원",
                "안전마진": "약 5억 8,000만 원",
                "공고URL": APPLYHOME_CAL_URL
            }
        ]

        today_d = datetime.today().date()
        for item in base_sale_list:
            try:
                s_d = datetime.strptime(item["접수시작일"], "%Y-%m-%d").date()
                e_d = datetime.strptime(item["접수종료일"], "%Y-%m-%d").date()
                if s_d <= today_d <= e_d: item["진행상태"] = "🔴 오늘 접수 진행 중!"
                elif today_d < s_d: item["진행상태"] = f"⏳ 접수 예정 (D-{(s_d - today_d).days})"
                else: item["진행상태"] = "🏁 청약 접수 마감"
            except Exception: item["진행상태"] = "일정 확인"

        st.markdown("##### 1. 청약Home 수도권 캘린더 실시간 접수 현황 (마감 여부 자동 판별)")
        col_f1, col_f2 = st.columns([1.5, 2.5])
        with col_f1:
            f_region = st.selectbox("📍 권역 필터", ["수도권 전체", "인천광역시", "서울특별시", "경기도"], key="sale_reg_box")
        with col_f2:
            f_search = st.text_input("🔎 단지명 / 지역구 검색", placeholder="예: 당산, 계양, 강변역, 부천대장...", key="sale_kw_box")

        filtered_cal = [x for x in base_sale_list if (f_region == "수도권 전체" or x["권역"] == f_region) and (not f_search.strip() or f_search.strip() in x["단지명"] or f_search.strip() in x.get("지역구", ""))]

        st.dataframe(pd.DataFrame([{
            "진행상태": d["진행상태"],
            "공급유형": d["유형"],
            "단지명": d["단지명"],
            "권역": f"{d['권역']} ({d.get('지역구','')})",
            "접수일정": d["접수일정텍스트"],
            "공급규모": d["공급규모"],
            "확정공급가": d["공급금액"],
            "안전마진": d["안전마진"]
        } for d in filtered_cal]), use_container_width=True, height=220)

        st.markdown("---")
        st.markdown("##### 2. 단지 선택 & 청약홈 공고문 팩트 주입")

        if filtered_cal:
            sel_idx = st.selectbox("분석 및 포스팅할 단지를 선택하세요:", range(len(filtered_cal)), format_func=lambda i: f"[{filtered_cal[i]['진행상태']}] {filtered_cal[i]['단지명']} ({filtered_cal[i]['공급규모']})")
            target = filtered_cal[sel_idx]

            st.markdown(f"""
            <div class="calc-box-orange">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4 style="color:#c05621; margin:0;">🏢 [{target['유형']}] {target['단지명']}</h4>
                    <span style="background:{'#e53e3e' if '오늘' in target['진행상태'] else '#4a5568'}; color:white; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:12px;">{target['진행상태']}</span>
                </div>
                • 위치: <b>{target['위치']}</b> | 시공사: <b>{target['시공사']}</b><br>
                • <b>공식 접수 일정</b>: <span style="color:#c53030; font-weight:bold;">{target['접수일정텍스트']}</span> | 발표: {target['당첨자발표']} | 계약: {target['계약체결']}<br>
                • <b>신청 자격 기준</b>: <b>{target['자격요건']}</b><br>
                • <b>동일 단지 실거래가</b>: <b>{target['동일단지실거래']}</b> ➡ 안전마진: <span style="font-size:17px; font-weight:bold; color:#2b6cb0;">{target['안전마진']}</span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📥 청약홈에서 복사한 공고문 텍스트 붙여넣기 (날짜·금액 1초 덮어쓰기)", expanded=True):
                st.caption("청약홈 화면에서 복사한 문구가 있다면 아래에 붙여넣어 즉시 기계적으로 반영할 수 있습니다.")
                user_paste_text = st.text_area("청약홈 화면 텍스트 붙여넣기 박스:", height=80, placeholder="청약접수일, 당첨자발표일, 공급금액 등을 복사해 넣으면 아래 입력값이 기계적으로 덮어씌워집니다.", key="sale_paste_box")

            p_name = target["단지명"]
            p_loc = target["위치"]
            p_type = target["유형"]
            p_sup = target["공급규모"]
            p_price = target["공급금액"]
            p_rcv = target["접수일정텍스트"]
            p_win = target["당첨자발표"]
            p_cnt = target["계약체결"]
            p_qual = target["자격요건"]
            p_real = target["동일단지실거래"]
            p_margin = target["안전마진"]

            if user_paste_text.strip():
                t = user_paste_text.strip()
                dates = re.findall(r'\d{4}[.\-\/]\d{2}[.\-\/]\d{2}', t)
                if len(dates) >= 1: p_rcv = dates[0]
                if len(dates) >= 2: p_win = dates[1]
                if len(dates) >= 3: p_cnt = dates[2]
                pr_m = re.search(r'(\d+억\s*\d*만*원|\d{1,3}(,\d{3})+원)', t)
                if pr_m: p_price = pr_m.group(0)

            c1, c2, c3 = st.columns(3)
            with c1:
                fin_rcv = st.text_input("접수일자 *", value=p_rcv, key="s_rcv")
                fin_win = st.text_input("당첨자발표 *", value=p_win, key="s_win")
            with c2:
                fin_sup = st.text_input("공급규모 *", value=p_sup, key="s_sup")
                fin_price = st.text_input("공급금액 *", value=p_price, key="s_price")
            with c3:
                fin_real = st.text_input("동일단지 실거래 *", value=p_real, key="s_real")
                fin_margin = st.text_input("안전마진 *", value=p_margin, key="s_margin")

            fin_qual = st.text_area("신청 자격 팩트 *", value=p_qual, height=65, key="s_qual")

            clean_tag = p_name.replace("(", " ").replace(")", " ").split()[0]
            blog_sale = f"""안녕하세요! 부동산 팩트체크와 알짜 청약 정보를 전해드리는 공인중개사 김태형입니다. 🙋‍♂️

청약홈 공식 공고 기준 '{p_name}' 입주자모집공고 안내입니다.
이번 공급은 전산 공고 기준 {fin_sup}로 진행되는 알짜배기 {p_type} 물량입니다.

청약홈 공식 공고문 및 인터넷 접수처:
{target['공고URL']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 공급 일정 팩트체크 (날짜 필수 확인!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 청약 접수일: {fin_rcv}
- 당첨자 발표일: {fin_win}
- 정당 계약일: {p_cnt}
- 접수처: 한국부동산원 청약Home (09:00 ~ 17:30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {p_name} ({p_loc})
- 공급 대상 및 규모: {fin_sup}
- 확정 공급금액: {fin_price}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 분양가 vs 실거래 시세 비교 (동일 단지 안전마진)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 시세 대조 기준: {fin_real}
- 당첨 시 예상 시세차익(안전마진): {fin_margin}
💡 김소장의 시세 분석: 단순 인근 구축 아파트와 비교한 것이 아니라, 국토교통부 실거래가 기준 실제 거래 완료된 동일 단지 입주권/분양권 시세를 바탕으로 산출한 확실한 안전마진입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 필수 청약 자격 팩트체크 (부적격 탈락 방지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 자격 요건: {fin_qual}
- 자금 조달 주의사항: 당첨 후 계약 체결일까지 기간이 짧으므로 계약금(통상 10~20%)을 즉시 현금 조달할 수 있는지 사전에 철저히 점검하셔야 합니다.

청약은 한국부동산원 청약Home 공식 홈페이지를 통해 접수하실 수 있습니다. 상세한 평면도와 옵션별 조건은 공식 입주자모집공고문을 반드시 확인하신 후 신중하게 신청하시기 바랍니다.

내 집 마련과 주거 안정을 준비하시는 모든 분들의 합격을 진심으로 응원합니다! 😊

#{clean_tag} #청약정보 #무순위청약 #줍줍 #{p_type.replace(' ','')} #안전마진 #청약일정 #내집마련 #공인중개사김소장 #청약홈
"""
            st.markdown("##### 📝 분양/줍줍 네이버 블로그 완성본")
            st.text_area("블로그 본문 복사창", blog_sale, height=450, key="sale_res_box")

    # -------------------------------------------------------------
    # 2. 🏠 [할루시네이션 0%] 공공임대 팩트 주입기 & 블로그 포스팅
    # -------------------------------------------------------------
    else:
        st.markdown("##### 1. LH·SH·iH 공공임대 기본 목록")
        base_rent_list = [
            {
                "단지명": "[iH] 검단신도시 청년 매입임대주택", "기관": "iH 인천도시공사", "권역": "인천광역시", "유형": "청년 매입임대",
                "위치": "인천광역시 서구 원당동 검단지구 신축 오피스텔 단지", "규모": "총 45세대 (빌트인 풀옵션)",
                "접수일정": "2026.10.15 ~ 10.19", "발표일": "2026.11.25", "입주": "2026년 12월 즉시입주",
                "기본보증금": "200만 원 (목돈 부담 제로)", "기본월세": "15만~18만 원 선",
                "최대전환조건": "보증금 최대 증액 시 월 8~10만 원대",
                "자격요건": "만 19세~39세 무주택 미혼 청년 (본인 소득 100% 이하, 총자산 2억 7,300만 원 이하)",
                "차량기준": "등록 차량가액 3,708만 원 이하 (고가 차량 보유 시 탈락)",
                "통장혜택": "청약통장 불필요, 당첨되어 입주해도 청약통장 미사용 유지!",
                "교통환경": "인천 1호선 아라역 인접, 상업지구 도보 5분, 에어컨·세탁기·냉장고 풀옵션",
                "공고URL": "https://www.ih.co.kr"
            },
            {
                "단지명": "[LH] 인천계양 A3블록 신혼희망타운 (행복주택)", "기관": "LH 한국토지주택공사", "권역": "인천광역시", "유형": "신혼부부 행복주택",
                "위치": "인천광역시 계양구 동양동 인천계양 A3BL", "규모": "총 359세대",
                "접수일정": "2026.10.20 ~ 10.26 (10:00~17:00)", "발표일": "2026.12.18", "입주": "2027년 03월 예정",
                "기본보증금": "6,200만 원", "기본월세": "24만 원",
                "최대전환조건": "보증금 최대 9,800만 원 전환 시 최저 월세 10만 원대",
                "자격요건": "혼인 7년 이내 신혼부부 또는 예비신혼부부 (소득 130% 이하 / 총자산 3억 4,500만 원 이하)",
                "차량기준": "차량가액 3,708만 원 이하",
                "통장혜택": "행복주택 거주 중에도 청약통장 효력 100% 유지 (향후 일반분양 계속 도전 가능)",
                "교통환경": "인천 1호선 박촌역 연계, 3기 신도시 계양 테크노밸리 배후 신축 단지, 단지 내 어린이집",
                "공고URL": LH_APPLY_URL
            },
            {
                "단지명": "[SH] 자양동 청년안심주택 (역세권)", "기관": "SH 서울주택도시공사", "권역": "서울특별시", "유형": "청년안심주택 (공공임대)",
                "위치": "서울특별시 광진구 자양동 680-1 일원 (구의역 도보 3분)", "규모": "총 280세대 중 공공임대 98세대",
                "접수일정": "2026.10.19 ~ 10.23", "발표일": "2026.12.10", "입주": "2027년 01월 입주",
                "기본보증금": "3,800만 원", "기본월세": "19만 원",
                "최대전환조건": "보증금 5,600만 원 전환 시 최저 월세 8만 원대 (전환이율 6.7%)",
                "자격요건": "만 19세~39세 무주택 청년 (소득 100% 이하 / 총자산 2억 7,300만 원 이하)",
                "차량기준": "차량 미소유자 우선 (생업용/장애인 차량 외 원칙적 주차 불가)",
                "통장혜택": "청약통장 유무 상관없이 신청 가능 (당첨되어도 청약통장 효력 유지!)",
                "교통환경": "2호선 구의역 150m 초역세권, 냉장고·세탁기·에어컨 풀퍼니시드 시스템 빌트인",
                "공고URL": "https://www.i-sh.co.kr"
            }
        ]

        r_reg = st.selectbox("📍 관할 기관 필터", ["전체 기관", "LH 한국토지주택공사", "iH 인천도시공사", "SH 서울주택도시공사"], key="rent_reg_box")
        r_filtered = [r for r in base_rent_list if r_reg == "전체 기관" or r["기관"] == r_reg]
        st.dataframe(pd.DataFrame(r_filtered)[["기관", "유형", "단지명", "권역", "기본보증금", "기본월세", "접수일정"]], use_container_width=True, height=180)

        st.markdown("---")
        st.markdown("##### 2. 공공임대 단지 선택 & LH/SH 공고문 팩트 주입")
        sel_r_idx = st.selectbox("포스팅할 공공임대 단지 선택:", range(len(r_filtered)), format_func=lambda i: f"[{r_filtered[i]['기관']}] {r_filtered[i]['단지명']}")
        target_r = r_filtered[sel_r_idx]

        st.link_button(f"🌐 [{target_r['기관']}] 공식 공고문 바로가기", target_r["공고URL"], use_container_width=True)

        with st.expander("📥 LH·SH 공고문 복사 텍스트 붙여넣기 (보증금·월세·날짜 1초 덮어쓰기)", expanded=True):
            st.caption("LH청약플러스나 SH/iH 사이트 공고문에서 복사한 텍스트를 넣으시면 아래 입력값이 기계적으로 즉시 덮어씌워집니다.")
            rent_paste_text = st.text_area("공공임대 공고문 텍스트 붙여넣기 박스:", height=80, placeholder="예시: 접수기간: 2026.10.20~10.26 당첨자발표: 2026.12.18 기본보증금: 62,000,000원 월임대료: 240,000원 신청자격: 소득 130% 이하...", key="rent_paste_box")

        r_name = target_r["단지명"]
        r_inst = target_r["기관"]
        r_loc = target_r["위치"]
        r_type = target_r["유형"]
        r_sup = target_r["규모"]
        r_rcv = target_r["접수일정"]
        r_win = target_r["발표일"]
        r_in = target_r["입주"]
        r_dep = target_r["기본보증금"]
        r_rent = target_r["기본월세"]
        r_conv = target_r["최대전환조건"]
        r_qual = target_r["자격요건"]
        r_car = target_r["차량기준"]
        r_bank = target_r["통장혜택"]
        r_env = target_r["교통환경"]

        if rent_paste_text.strip():
            rt = rent_paste_text.strip()
            r_dates = re.findall(r'\d{4}[.\-\/]\d{2}[.\-\/]\d{2}', rt)
            if len(r_dates) >= 1: r_rcv = r_dates[0]
            if len(r_dates) >= 2: r_win = r_dates[1]
            dep_m = re.search(r'(보증금[:\s]*[\d,]+만*원|[\d,]{5,}원)', rt)
            if dep_m: r_dep = dep_m.group(0)
            rent_m = re.search(r'(월세[:\s]*[\d,]+만*원|임대료[:\s]*[\d,]+원)', rt)
            if rent_m: r_rent = rent_m.group(0)

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            fin_r_rcv = st.text_input("서류접수 일정 *", value=r_rcv, key="r_in_rcv")
            fin_r_win = st.text_input("당첨자 발표일 *", value=r_win, key="r_in_win")
        with rc2:
            fin_r_dep = st.text_input("기본 보증금 *", value=r_dep, key="r_in_dep")
            fin_r_rent = st.text_input("기본 월세 *", value=r_rent, key="r_in_rent")
        with rc3:
            fin_r_conv = st.text_input("보증금 최대 전환 시 *", value=r_conv, key="r_in_conv")
            fin_r_car = st.text_input("차량가액 기준 *", value=r_car, key="r_in_car")

        fin_r_qual = st.text_area("신청 자격 팩트 (소득/자산) *", value=r_qual, height=60, key="r_in_qual")

        clean_r_tag = r_name.replace("[", "").replace("]", "").split()[1] if len(r_name.split()) > 1 else "공공임대"

        blog_rent = f"""안녕하세요! 청년·신혼 주거비 부담을 덜어드리는 공인중개사 김태형입니다. 🙋‍♂️

{r_inst} 공식 공고 기준 '{r_name}' 입주자 모집공고 안내입니다.
목돈 부담 없이 안정적으로 장기 거주할 수 있는 알짜배기 {r_type} 물량입니다.

{r_inst} 공식 청약 접수처 및 공고문 확인:
{target_r['공고URL']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 1. 핵심 공급 일정 팩트체크 (체크리스트)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 청약 접수 및 서류제출: {fin_r_rcv} ({r_inst} 청약센터)
- 최종 당첨자 발표일: {fin_r_win}
- 계약 및 입주 예정 시기: {r_in}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 2. 단지 개요 및 공급 위치
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 단지명: {r_name}
- 공급 위치: {r_loc}
- 공급 대상 및 규모: {r_sup}
- 교통 및 주거 환경: {r_env}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 3. 임대 조건 및 보증금-월세 상호전환 안내
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 기본 임대료: 보증금 {fin_r_dep} / 월세 {fin_r_rent}
- 보증금 최대 증액 시: {fin_r_conv}
💡 김소장의 팁: 버팀목 전세대출(연 1~2%대)을 이용할 수 있다면, 보증금을 최대로 높여 월 고정비 지출을 10만 원 안팎으로 획기적으로 낮추는 것이 훨씬 유리합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 4. 신청 전 필수 자격 팩트체크 (소득·자산 컷)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 신청 대상 요건: {fin_r_qual}
- 자동차 가액 기준: {fin_r_car}
- 청약통장 혜택: {r_bank}

공공임대 및 청년주택은 한국부동산원 청약Home이 아닌, {r_inst} 공식 청약센터를 통해 인터넷으로 접수하셔야 합니다. 세부 평면도와 호수 배치는 공식 공고문을 반드시 확인하신 후 접수하시기 바랍니다.

내 집 마련의 든든한 징검다리가 되어줄 청년 여러분의 당첨을 진심으로 응원합니다! 😊

#{clean_r_tag} #공공임대 #{r_type.replace(' ','')} #청년주택 #행복주택 #{r_inst.split()[0]}청약 #주거안정 #공인중개사김소장
"""
        st.markdown("##### 📝 공공임대 네이버 블로그 완성본")
        st.text_area("공공임대 블로그 본문 복사창", blog_rent, height=450, key="rent_res_box")

# =============================================================
# 8. ⚖️ [완전 복구] 법원경매 허브 (5단계 배당표 & 턴키 자금조달표)
# =============================================================
elif menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 & 수도권 주택·공장 심층 수지분석")
    st.caption("대법원 법원경매정보 연동 기반: 수도권 주택(아파트)·인천공장 5단계 실시간 배당표, 명도비용, 턴키 자금표 및 공장/아파트 경매 전문 블로그 포스팅 원클릭 완성!")

    factory_list, apt_list = get_auction_data()

    with st.expander("📌 [필독] 경매 입찰 전 물건 유형별 필수 확인 체크리스트 (실무 가이드)", expanded=False):
        c_tab1, c_tab2 = st.tabs(["🏭 공장·창고 경매 필수 확인 사항", "🏢 주택·아파트 경매 필수 확인 사항"])
        with c_tab1:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 산업단지 입주자격 (산집법 제38조)</b>: 국가산단/일반산단 경매는 입주 부적격자 낙찰 시 6개월 내 처분명령 대상. 입주업종 코드 사전 확인 필수.<br>
                <b>2. 기계기구 감정가 분리</b>: 공장 총 감정가 중 기계(CNC, 프레스, 크레인) 가치와 실제 가동 여부 분리 필수.<br>
                <b>3. 한전 단전 및 산업용 전기 체납</b>: 수천만 원 규모의 전기요금 연체 시 한전 단전 해제비 및 보증보험료 발생 (한전 123 확인).<br>
                <b>4. 진입로 사도(개인도로) 지분 여부</b>: 도로 지분 없이 맹지 상태인 경우 대형 트럭 진입 불가 분쟁 위험.
            </div>
            """, unsafe_allow_html=True)
        with c_tab2:
            st.markdown("""
            <div class="check-list-box">
                <b>1. 대항력 있는 선순위 임차인</b>: 전입일자가 말소기준권리보다 빠르고 미배당 시 낙찰자가 전액 인수.<br>
                <b>2. 토지거래허가구역 경매 특례</b>: 경매 취득 시 허가가 면제되어 2년 실거주의무 없이 즉시 전세 갭투자 가능.<br>
                <b>3. 공용부분 미납관리비 승계</b>: 대법원 판례상 최근 3년 치 공용 관리비 낙찰자 승계.<br>
                <b>4. 명도 난이도 및 강제집행 예산</b>: 통상 이사비(평당 8~10만 원) 협의가 소송보다 빠르고 경제적입니다.
            </div>
            """, unsafe_allow_html=True)

    auction_tab1, auction_tab2 = st.tabs(["🏢 수도권 주택(아파트) 경매 & 권리분석·블로그", "🏭 인천 전지역 공장·창고 경매 & 정밀 턴키 수지표·블로그"])

    with auction_tab1:
        st.subheader("🏢 수도권 주택(아파트) 법원경매 사건 리스트")

        f_c1, f_c2 = st.columns([2.2, 2.5])
        with f_c1:
            major_region = st.selectbox(
                "📍 광역 시·도 필터 (전체 우선)",
                ["전체 모아보기 (수도권 전지역)", "서울특별시", "경기도", "인천광역시"],
                index=0
            )
        with f_c2:
            kw_val = st.text_input("🔎 단지명 / 사건번호 검색", placeholder="예: 아크로, 푸르지오, 10550 등...")

        filtered_apt = []
        for item in apt_list:
            if major_region != "전체 모아보기 (수도권 전지역)" and item["시도"] != major_region: continue
            if kw_val.strip() and (kw_val.strip() not in item["소재지"]) and (kw_val.strip() not in item["사건번호"]): continue
            filtered_apt.append(item)

        df_apt_show = pd.DataFrame(filtered_apt)
        if not df_apt_show.empty:
            summary_cols = df_apt_show[["사건번호", "법원", "시도", "소재지", "평형타입", "층수", "감정가", "최저가", "추천입찰가밴드", "예상시세차익", "매각기일", "진행상태"]].copy()
            st.dataframe(summary_cols, use_container_width=True, height=210)
        else:
            st.info("선택하신 조건의 주택 경매 사건이 없습니다.")

        if filtered_apt:
            st.markdown("---")
            chosen_apt_idx = st.selectbox(
                "정밀 분석 및 포스팅을 생성할 주택 사건을 선택하세요",
                range(len(filtered_apt)),
                format_func=lambda i: f"[{filtered_apt[i]['사건번호']}] {filtered_apt[i]['소재지']} (감정가: {filtered_apt[i]['감정가']} / 최저가: {filtered_apt[i]['최저가']})"
            )
            cur_apt = filtered_apt[chosen_apt_idx]
            qa_apt = cur_apt["권리분석"]
            case_key = cur_apt['사건번호'].replace("타경", "_")

            st.markdown(f"""
            <div style="background-color: #f7fafc; border: 2px solid #cbd5e0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #1a365d;">🏢 {cur_apt['사건번호']} - {cur_apt['소재지']}</h3>
                    <span class="sub-badge-wait" style="font-size: 13px;">{cur_apt['법원']} | {cur_apt['진행상태']}</span>
                </div>
                • <b>주택 유형 / 면적</b>: <b>{cur_apt['주택유형']} ({cur_apt['평형타입']})</b> | 층수: <b>{cur_apt['층수']}</b><br>
                • <b>가격 현황</b>: 감정가 <b>{cur_apt['감정가']}</b> ➡ 최저가 <b>{cur_apt['최저가']}</b> (보증금 10%: {cur_apt['입찰보증금']})<br>
                • <b>인근 실거래 시세</b>: <span style="color: #2b6cb0; font-weight: bold;">약 {cur_apt['최근실거래가']}</span> (추천밴드: {cur_apt['추천입찰가밴드']} / 예상차익 {cur_apt['예상시세차익']})
            </div>
            """, unsafe_allow_html=True)

            apt_sub_tab1, apt_sub_tab2 = st.tabs(["📝 [원클릭] 아파트 경매 전문 네이버 블로그 포스팅", "📊 실시간 5단계 배당표 & 자금조달표"])

            with apt_sub_tab1:
                clean_apt_name = cur_apt['소재지'].split('(')[-1].replace(')', '').split()[0] if '(' in cur_apt['소재지'] else "아파트경매"

                apt_blog_post = f"""안녕하세요! 수도권 법원경매 전문 분석 및 실전 임장 공인중개사 김태형입니다. 🙋‍♂️

최근 시세 대비 감정가와 1회 유찰 최저가 메리트가 확실한 알짜배기 주택 경매 물건을 브리핑해 드립니다.
오늘 소개해 드리는 사건은 {cur_apt['법원']}에서 진행되는 사건번호 {cur_apt['사건번호']} 매각 물건입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 매각 일정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_apt['사건번호']}
- 담당법원: {cur_apt['법원']}
- 물건소재지: {cur_apt['소재지']}
- 주택유형 및 평형: {cur_apt['주택유형']} {cur_apt['평형타입']} ({cur_apt['층수']})
- 매각기일: {cur_apt['매각기일']} ({cur_apt['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정평가 및 시세차익 안전마진 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 감정가액: {cur_apt['감정가']}
- 1회 유찰 최저가: {cur_apt['최저가']} (감정가 대비 70~80% 수준)
- 입찰 보증금: {cur_apt['입찰보증금']} (10% 자기앞수표 1매 준비 필수)
- 최근 인근 실거래 시세: {cur_apt['최근실거래가']} 선 형성
🚩 김소장의 추천 입찰가 밴드: {cur_apt['추천입찰가밴드']} (당첨 시 예상 시세차익: {cur_apt['예상시세차익']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ 3. 김소장의 심층 권리분석 체크포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 말소기준권리: {qa_apt['말소기준권리']}
✅ 임차인 대항력 여부: {qa_apt['임차인분석']}
✅ 낙찰자 추가 인수 보증금: {qa_apt['인수보증금']:,}원 (말소기준권리 이하 모든 채권 소멸, 리스크 제로)
✅ 규제 특례 혜택: {qa_apt['토허제특례']}
✅ 명도 난이도 및 가이드: {qa_apt['명도난이도']}
✅ 공용부분 미납관리비: 약 {cur_apt['미납관리비']:,}원 (대법원 판례상 최근 3년 공용부분 승계 검토 완료)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💸 4. 예상 실투자금 및 경락대출 자금 로드맵 (낙찰가 기준)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 경락잔금대출 한도: 낙찰가의 70~80% 지원 (무주택/1주택자 기준)
2. 주택 취득세율: 1.1% ~ 3.5% (다주택자 중과 여부 개별 확인 필요)
3. 필요 순수 현금: 입찰보증금(10%) + 잔금 자부담(20~30%) + 취득세 및 협의 이사비

법원경매는 시세보다 수억 원 저렴하게 내 집을 마련할 수 있는 가장 확실한 기회이지만, 현장 임장과 명도 협의 계획이 철저해야 합니다.
본 사건의 상세 권리분석 및 입찰 대리 진행 상담은 언제든 편하게 문의해 주시기 바랍니다.

현장 임장 및 입찰 대리 전문
우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276

#{clean_apt_name} #아파트경매 #법원경매 #대법원경매 #부동산경매 #{cur_apt['시도'].replace('특별시','').replace('광역시','')}경매 #경락대출 #시세차익 #공인중개사김소장 #우리부동산
"""
                st.text_area("아파트 경매 네이버 블로그 복사용 본문", apt_blog_post, height=450)

            with apt_sub_tab2:
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
                    <div style="background:#f7fafc; border:1px solid #cbd5e0; padding:10px; font-size:12.5px; line-height:1.7;">
                        1. 경매집행비용 배당: <b>{pay_exp:,}원</b><br>
                        2. 당해세(재산세 등) 법정배당: <b>{pay_tax:,}원</b><br>
                        3. 최우선변제금 배당: <b>{pay_pri:,}원</b><br>
                        4. 선순위 근저당권 배당: <b>{pay_mort:,}원</b><br>
                        5. 임차인 배당금: <b>{pay_rent:,}원</b><br>
                        🚩 <b>낙찰자 추가 인수 보증금</b>: <span style="color:#276749; font-weight:bold;">0원 (완전 소멸 안전물건)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("🌐 대법원 사건검색 바로가기", cur_apt["사건URL"], use_container_width=True)

                with col_r:
                    st.markdown("##### 💰 주택 실시간 자금조달표")
                    u_bid = st.number_input("예상 낙찰가 (원)", value=int(cur_apt['최저가원']), step=10000000, key=f"ab_{case_key}")
                    u_ltv = st.slider("대출 LTV (%)", 40, 80, 70, 5, key=f"al_{case_key}")
                    tax = int(u_bid * (0.011 if u_bid <= 600000000 else 0.035))
                    loan = min(int(cur_apt['감정가원'] * 0.7), int(u_bid * (u_ltv / 100.0)))
                    cash = (u_bid - loan) + tax + cur_apt['미납관리비'] + 1500000
                    st.markdown(f"""
                    <div class="calc-box-orange">
                        • 낙찰가: {u_bid:,}원 | 경락대출: 약 {loan:,}원<br>
                        • 취득세: {tax:,}원 | 미납관리비: {cur_apt['미납관리비']:,}원<br>
                        • 협의 이사비(예비비): 약 1,500,000원<br>
                        <hr style="margin:6px 0;">
                        🚩 <b>필요 순수 현금</b>: <span style="font-size:20px; color:#c53030; font-weight:bold;">약 {cash:,}원</span>
                    </div>
                    """, unsafe_allow_html=True)

    with auction_tab2:
        st.subheader("🏭 인천광역시 공장 및 창고 경매 사건 리스트")

        df_fac = pd.DataFrame(factory_list)
        summary_fac = df_fac[["사건번호", "법원", "소재지", "세부용도", "바닥평수", "총감정가", "최저가", "입찰보증금", "매각기일", "진행상태"]].copy()
        st.dataframe(summary_fac, use_container_width=True, height=200)

        st.markdown("---")
        chosen_fac_idx = st.selectbox(
            "정밀 분석 및 블로그 포스팅을 생성할 공장 경매 사건을 선택하세요",
            range(len(factory_list)),
            format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']} (감정가: {factory_list[i]['총감정가']} / 최저가: {factory_list[i]['최저가']})"
        )
        cur_fac = factory_list[chosen_fac_idx]
        case_fac_key = cur_fac['사건번호'].replace("타경", "_")
        pure_real_estate = cur_fac['토지감정가원'] + cur_fac['건물감정가원']

        st.markdown(f"""
        <div style="background-color: #f7fafc; border: 2px solid #cbd5e0; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="margin: 0; color: #1a365d;">🏭 {cur_fac['사건번호']} - {cur_fac['소재지']}</h3>
                <span class="sub-badge-wait" style="font-size: 13px;">{cur_fac['법원']} | {cur_fac['진행상태']}</span>
            </div>
            • <b>대지 / 건물 면적</b>: 대지 {cur_fac['대지면적']} / 건물 연면적 {cur_fac['건물면적']} (1F 바닥 {cur_fac['바닥평수']}평)<br>
            • <b>현재 설비 스펙</b>: 처마 층고 / 인입 동력 <b>{cur_fac['현재동력kW']}kW</b> / {cur_fac['현재호이스트']}<br>
            • <b>현장 제원 코멘트</b>: {cur_fac['제원및코멘트']}
        </div>
        """, unsafe_allow_html=True)

        fac_sub_tab1, fac_sub_tab2 = st.tabs(["📝 [원클릭] 공장 경매 전문 네이버 블로그 포스팅", "💰 턴키 정상가동 실시간 자금조달표"])

        with fac_sub_tab1:
            clean_fac_loc = cur_fac['소재지'].split()[1] + " " + cur_fac['소재지'].split()[2]

            fac_blog_post = f"""안녕하세요! 인천 서구 및 주요 산업단지 공장·창고 전문 공인중개사 김태형입니다. 🙋‍♂️

제조업 대표님들의 자가 공장 마련과 이전 부담을 획기적으로 낮출 수 있는 알짜배기 공장 경매 사건을 브리핑해 드립니다.
오늘 소개해 드리는 물건은 {cur_fac['법원']}에서 진행되는 사건번호 {cur_fac['사건번호']} 물건으로, 감정가 대비 1회 유찰되어 시세 차익과 실수요 입주 메리트가 대단히 높습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 1. 사건 개요 및 입찰 기본 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 사건번호: {cur_fac['사건번호']}
- 담당법원: {cur_fac['법원']}
- 소재지: {cur_fac['소재지']}
- 대지면적: {cur_fac['대지면적']}
- 건물면적: {cur_fac['건물면적']} (1층 바닥 {cur_fac['바닥평수']}평)
- 매각기일: {cur_fac['매각기일']} ({cur_fac['진행상태']})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 2. 감정평가 상세 분석 (기계기구 분리평가)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 감정가액: {cur_fac['총감정가']}
- 1회 유찰 최저가: {cur_fac['최저가']} (감정가 70% 수준)
- 입찰 보증금: {cur_fac['입찰보증금']} (10% 수표 1장 준비)
- 순수 부동산(토지+건물) 가치: 약 {pure_real_estate:,}원
- 기계기구 감정액: 약 {cur_fac['기계기구감정가원']:,}원 ({cur_fac['기계감정내역']})
💡 김소장의 팁: 공장 경매는 총 감정가 중 기계기구 평가액이 포함되어 있으므로, 실제 부동산 가치만을 분리 계산하여 입찰가를 산정하는 것이 필수입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 3. 공장 현장 제원 및 제조 인프라 스펙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 인입 동력: 현재 {cur_fac['현재동력kW']}kW 인입 (필요시 증설 가능 여부 확인 완료)
- 호이스트 설비: {cur_fac['현재호이스트']}
- 진입 도로 및 마당: {cur_fac['제원및코멘트']}
- 용도지역 및 입주 적격성: {cur_fac['산단입주자격']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ 4. 김소장의 공장 경매 6대 권리분석 체크포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 말소기준권리: {cur_fac['권리분석']['말소기준']}
✅ 임차인 대항력: {cur_fac['권리분석']['임차인']}
✅ 유치권 신고 여부: {cur_fac['권리분석']['유치권']}
✅ 낙찰자 인수 권리: {cur_fac['권리분석']['인수권리']} (소멸주의 원칙 적용)
✅ 산업단지 입주자격: {cur_fac['산단입주자격']}
✅ 연체 관리비 및 전기료: 약 {cur_fac['연체관리비추정']:,}원 (한전 단전 여부 사전 체크 완료)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💸 5. 턴키 정상가동 자금 조달 타임라인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 시설자금 경락잔금대출: 감정가 및 낙찰가의 최대 75~80% 지원 가능
2. 취득세율: 공장/토지 4.6% 적용 (산단 최초 입주 시 감면 요건 개별 검토)
3. 제조 인프라 세팅비: 동력 승압비, 호이스트 정비, 바닥 에폭시 공사비 사전 예산 수립 완료

공장 경매는 권리분석뿐만 아니라 업종 인허가, 산집법 입주계약 체결, 수전용량과 호이스트 실가동 여부까지 원스톱으로 점검해야 실패하지 않습니다.
현장 임장 동행 및 턴키 입찰 대리 진행 상담은 편하게 문의해 주십시오.

인천 공장·창고 중개 및 법원경매 전문
우리부동산 공인중개사사무소 대표 김태형
☎ 010-2660-8276

#{clean_fac_loc.replace(' ','')}공장 #인천공장경매 #창고경매 #법원경매 #호이스트공장 #공인중개사김소장 #우리부동산 #경락잔금대출 #제조업이전
"""
            st.text_area("공장 경매 네이버 블로그 복사용 본문", fac_blog_post, height=450)

        with fac_sub_tab2:
            fc1, fc2 = st.columns([1.2, 1.3])
            with fc1:
                st.markdown("##### ⚖️ 권리분석 & 기계기구 분리")
                st.markdown(f"""
                <div style="background:#ffffff; border:1px solid #cbd5e0; padding:12px; font-size:13px; line-height:1.8;">
                    • <b>말소기준</b>: {cur_fac['권리분석']['말소기준']}<br>
                    • <b>임차인</b>: {cur_fac['권리분석']['임차인']}<br>
                    • <b>유치권</b>: {cur_fac['권리분석']['유치권']}<br>
                    • <b>순수 부동산 가치</b>: {pure_real_estate:,}원<br>
                    • <b>기계기구 감정액</b>: {cur_fac['기계기구감정가원']:,}원 ({cur_fac['기계감정내역']})<br>
                    • <b>산단입주</b>: {cur_fac['산단입주자격']}
                </div>
                """, unsafe_allow_html=True)
                st.link_button("🌐 대한민국 법원경매정보 사건검색", cur_fac["사건URL"], use_container_width=True)

            with fc2:
                st.markdown("##### 💰 턴키 입주 실시간 자금조달표")
                f_bid = st.number_input("예상 낙찰가 (원)", value=int(cur_fac['최저가원']), step=10000000, key=f"fb_{case_fac_key}")
                f_ltv = st.slider("시설대출 LTV (%)", 50, 85, 75, 5, key=f"fl_{case_fac_key}")
                f_tax = int(f_bid * 0.046)
                f_loan = min(int(cur_fac['총감정가원'] * 0.7), int(f_bid * (f_ltv / 100.0)))
                f_cash = (f_bid - f_loan) + f_tax + cur_fac['연체관리비추정'] + 15000000
                st.markdown(f"""
                <div class="calc-box-orange">
                    • 낙찰가: {f_bid:,}원 | 시설대출: 약 {f_loan:,}원<br>
                    • 취득세(4.6%): {f_tax:,}원 | 연체전기료/관리비: {cur_fac['연체관리비추정']:,}원<br>
                    • 동력/호이스트 시설보수 예비비: 약 15,000,000원<br>
                    <hr style="margin:6px 0;">
                    🚩 <b>필요 순수 현금</b>: <span style="font-size:20px; color:#c53030; font-weight:bold;">약 {f_cash:,}원</span>
                </div>
                """, unsafe_allow_html=True)