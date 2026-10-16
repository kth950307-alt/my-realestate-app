import streamlit as st
import pandas as pd
import os
import re
import base64
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="우리공장부동산 | 인천 공장·창고·신축분양 전문", page_icon="🏭", layout="wide")

# 이미지 저장용 폴더 자동 생성
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_image(uploaded_file, prefix="prop"):
    if uploaded_file is None:
        return ""
    ext = os.path.splitext(uploaded_file.name)[-1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return fpath

def get_image_base64_html(img_path, height_px=190, badge_text="추천매물"):
    if img_path and pd.notna(img_path) and str(img_path).strip() and os.path.exists(str(img_path).strip()):
        try:
            with open(str(img_path).strip(), "rb") as img_f:
                b64 = base64.b64encode(img_f.read()).decode()
            return f"""
            <div style="position:relative; height:{height_px}px; width:100%; overflow:hidden; border-radius:10px 10px 0 0; background:#1a202c;">
                <img src="data:image/jpeg;base64,{b64}" style="width:100%; height:100%; object-fit:cover;">
                <span style="position:absolute; top:10px; left:10px; background:#dd6b20; color:white; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:700;">{badge_text}</span>
            </div>
            """
        except Exception:
            pass
    return f"""
    <div style="position:relative; height:{height_px}px; width:100%; border-radius:10px 10px 0 0; background:linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); display:flex; flex-direction:column; align-items:center; justify-content:center; color:white;">
        <span style="position:absolute; top:10px; left:10px; background:#dd6b20; color:white; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:700;">{badge_text}</span>
        <div style="font-size:38px;">🏭</div>
        <div style="font-size:14px; font-weight:700; margin-top:4px;">우리공장부동산 현장실사 매물</div>
        <div style="font-size:11px; opacity:0.85;">☎ 032-582-6200 / 010-2660-8276</div>
    </div>
    """

# 크롬 번역 방지 & 반응형 홈페이지(토미부동산 스타일) + 업무 시스템 통합 CSS
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
    .hero-banner {
        background: linear-gradient(120deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
        color: white;
        padding: 28px 32px;
        border-radius: 14px;
        margin-bottom: 18px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
    }
    .prop-web-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        margin-bottom: 18px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        overflow: hidden;
    }
    .prop-web-body { padding: 16px; }
    .floating-cta-bar {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: #0f172a;
        color: white;
        padding: 10px 20px;
        z-index: 9999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 -3px 12px rgba(0,0,0,0.2);
    }
    .hunt-item-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #3182ce; border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; }
    .hunt-item-done { background-color: #f0fff4; border: 1px solid #c6f6d5; border-left: 5px solid #38a169; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; }
    .customer-card-pro { background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid #3182ce; border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; }
    .customer-card-pro-vip { background-color: #fffdf7; border: 1px solid #feebc8; border-left: 6px solid #dd6b20; border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; }
    .tag-blue { background-color: #ebf8ff; color: #2b6cb0; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-orange { background-color: #fffaf0; color: #c05621; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-green { background-color: #f0fff4; color: #276749; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-right: 5px; display: inline-block; }
    .tag-gray { background-color: #edf2f7; color: #4a5568; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: 600; margin-right: 5px; display: inline-block; }
    .remind-card-red { background-color: #fff5f5; border-left: 5px solid #e53e3e; border: 1px solid #fed7d7; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-weight: 600; }
    .calc-box-orange { background-color: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 16px; margin: 10px 0; line-height: 1.7; }
    .calc-box-blue { background-color: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 16px; margin: 10px 0; line-height: 1.7; }
    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"], .stButton, .floating-cta-bar, header, footer { display: none !important; }
    }
</style>
</div>
""", unsafe_allow_html=True)

# =============================================================
# ⚡ 데이터베이스 파일 및 로드/세이브 함수
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
        for col, d_val in [("입주/공실상태", "현재 공실(즉시입주)"), ("계약만료일", "즉시 협의"), ("사진경로", ""), ("추천매물여부", "일반")]:
            if col not in df.columns: df[col] = d_val
        return df
    # 초기 샘플 매물 (홈페이지에 즉시 보이도록 구성)
    init_props = [
        {
            "등록일자": "2026-10-15", "입주/공실상태": "현재 공실(즉시입주)", "계약만료일": "즉시 입주", "거래구분": "임대차(월세)",
            "소재지(권역)": "인천 서구 가좌동", "상세주소(지번)": "인천 서구 가좌동 556-12", "임대인(건물주)": "박회장", "임대인연락처": "010-0000-0000",
            "가격(보/월)": "보증금 3,500만 원 / 월세 280만 원", "면적": "1층 90평", "층고": "처마 8m", "동력": "75kW",
            "호이스트": "호이스트 5톤 완비", "도로/주차": "10m 도로 접 / 마당 주차 5대", "대형차량": "11T 윙바디 접안 원활",
            "특징메모": "[일반공업지역] 가좌IC 3분 거리, 호이스트 5톤 및 동력 75kW 완비된 단독형 A급 공장", "사진경로": "", "추천매물여부": "🌟프리미엄추천"
        },
        {
            "등록일자": "2026-10-15", "입주/공실상태": "협의 입주", "계약만료일": "2026년 11월 말", "거래구분": "임대차(월세)",
            "소재지(권역)": "인천 서구 석남동", "상세주소(지번)": "인천 서구 석남동 223-360", "임대인(건물주)": "김대표", "임대인연락처": "010-1111-2222",
            "가격(보/월)": "보증금 2,500만 원 / 월세 210만 원", "면적": "1층 70평", "층고": "처마 7m", "동력": "50kW",
            "호이스트": "호이스트 2.8톤 완비", "도로/주차": "8m 도로 접 / 주차 3대", "대형차량": "5톤 화물차 수월",
            "특징메모": "[일반공업지역] 석남동 공구상가 초인접, 정밀가공 및 사출·조립 최적", "사진경로": "", "추천매물여부": "🌟프리미엄추천"
        },
        {
            "등록일자": "2026-10-15", "입주/공실상태": "현재 공실(즉시입주)", "계약만료일": "즉시 입주", "거래구분": "매매",
            "소재지(권역)": "인천 서구 원창동", "상세주소(지번)": "인천 서구 원창동 380-1", "임대인(건물주)": "이소유", "임대인연락처": "010-3333-4444",
            "가격(보/월)": "매매가 24억 5,000만 원", "면적": "대지 250평 / 건물 180평", "층고": "처마 9m", "동력": "100kW",
            "호이스트": "호이스트 5톤 완비", "도로/주차": "12m 광폭도로 / 대형마당", "대형차량": "츄레라 / 트레일러 진출입 원활",
            "특징메모": "[일반공업지역] 북항배후단지 인접, 40ft 컨테이너 트레일러 회전 가능한 대형 단독공장 급매", "사진경로": "", "추천매물여부": "🌟프리미엄추천"
        }
    ]
    df = pd.DataFrame(init_props)
    df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")
    return df

def save_all_properties(df): df.to_csv(PROPERTIES_CSV, index=False, encoding="utf-8-sig")
def save_property(new_data):
    df = load_properties()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    save_all_properties(updated)
    return updated

def load_new_devs():
    if os.path.exists(NEW_DEV_CSV):
        df = pd.read_csv(NEW_DEV_CSV)
        if "사진경로" not in df.columns: df["사진경로"] = ""
        return df
    init_devs = [
        {
            "등록일자": "2026-10-15", "사업지명": "가좌 첨단제조단지 신축분양", "소재지": "인천 서구 가좌동 일원",
            "분양대지평수": "150평 (분할 가능)", "건폐율": "60%", "1층바닥평수": "90평", "건물층수": "지상 2층",
            "총연면적": "120평", "분양공급가": "19억 1,400만 원 (대출 80% 가능)", "도로여건": "12m 광폭도로 접 (츄레라 진입)",
            "층고제원": "처마 8.5m", "인입동력": "75kW 기본인입", "특징메모": "취득세 감면 혜택 및 시설자금 80% 저리 대출 지원, 맞춤 설계 가능", "사진경로": ""
        },
        {
            "등록일자": "2026-10-15", "사업지명": "검단일반산단 코너필지 신축분양", "소재지": "인천 서구 오류동 검단산단 내",
            "분양대지평수": "220평", "건폐율": "70%", "1층바닥평수": "150평", "건물층수": "지상 1층 (단독마당 70평)",
            "총연면적": "150평", "분양공급가": "24억 2,000만 원 (시설대출 80%)", "도로여건": "15m 산단 대로변 코너",
            "층고제원": "처마 10m (호이스트 10T 가능)", "인입동력": "150kW", "특징메모": "검단신도시 및 고속도로 IC 인접, 대형 제조 및 물류거점 최적 입지", "사진경로": ""
        }
    ]
    df = pd.DataFrame(init_devs)
    df.to_csv(NEW_DEV_CSV, index=False, encoding="utf-8-sig")
    return df

def save_new_dev(new_data):
    df = load_new_devs()
    updated = pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
    updated.to_csv(NEW_DEV_CSV, index=False, encoding="utf-8-sig")
    return updated

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
# 🔑 사이드바: 고객용 홈페이지 모드 vs 대표님(관리자) 업무 모드 스위치
# =============================================================
CORRECT_PASSWORD = "950307"
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

st.sidebar.markdown("### 🏭 우리공장부동산")
st.sidebar.caption("인천 서구 공장·창고·신축분양 전문\n대표 김태형 | ☎ 032-582-6200")

if not st.session_state["is_admin"]:
    st.sidebar.info("🌐 현재 **[고객용 반응형 홈페이지]** 화면입니다.")
    with st.sidebar.expander("🔒 관리자(김소장) 전용 로그인", expanded=False):
        pwd_in = st.text_input("관리자 비밀번호", type="password", key="admin_pwd_input")
        if st.button("🔓 업무 시스템 열기", type="primary", use_container_width=True):
            if pwd_in == CORRECT_PASSWORD:
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 일치하지 않습니다.")
    menu_choice = "PUBLIC_HOMEPAGE"
else:
    st.sidebar.success("✅ **관리자(김태형 대표님) 모드 가동 중**")
    MENU_DICT = {
        "PUBLIC_HOMEPAGE": "🌐 [실시간 미리보기] 고객용 반응형 홈페이지",
        "FACTORY_HUNT": "🏃 [임장/작업] 현장 공장 물건따기 파이프라인",
        "FACTORY_REG": "🏭 [주업] 공장 매물 등록 (홈페이지 자동연동)",
        "NEW_DEV": "🏗️ [주업] 신축공장 분양 등록 & 설계 제안서",
        "CUSTOMER_CRM": "📋 [주업] 공장 손님 장부 (홈페이지 접수 연동)",
        "FACTORY_BOOK": "📁 [주업] 공장 보유 매물 장부 (멀티장바구니)",
        "PRICE_AI": "🔍 [주업] 공장·창고 AI 시세 & 건물주 리포트",
        "BLOG_FOOD": "🍜 [부업] 맛집 탐방 블로그 (SEO·영수증·숏폼)",
        "BLOG_LIFE": "🧢 [부업] 일상·핫플·운동 블로그 (주제별 맞춤)",
        "APPLY_HOME": "🏢 [부업] 실시간 청약·줍줍 & LH 공공임대 허브",
        "AUCTION_HUB": "⚖️ [부업] 법원경매 목록 허브 (인천공장 & 아파트)"
    }
    menu_choice = st.sidebar.radio("📌 통합 업무 메뉴", list(MENU_DICT.values()), index=0)
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 관리자 로그아웃 (손님 화면으로 전환)", use_container_width=True):
        st.session_state["is_admin"] = False
        st.rerun()

# =============================================================
# 🌐 [고객용 반응형 홈페이지] 토미부동산 스타일 초고속 매물 검색 & 신축분양관
# =============================================================
if menu_choice == "PUBLIC_HOMEPAGE" or (st.session_state["is_admin"] and menu_choice == MENU_DICT["PUBLIC_HOMEPAGE"]):
    df_p = load_properties()
    df_dev = load_new_devs()

    # 상단 프리미엄 히어로 배너
    st.markdown("""
    <div class="hero-banner">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <span style="background:#f59e0b; color:#0f172a; padding:4px 12px; border-radius:20px; font-size:12.5px; font-weight:800;">인천 서구·산단 공장/창고 NO.1 파트너</span>
                <h1 style="color:white; margin:10px 0 6px 0; font-size:30px; font-weight:800;">🏭 우리공장부동산 공인중개사사무소</h1>
                <p style="color:#dbeafe; margin:0; font-size:15px;">가좌·석남·원창·오류·검단산단 | 대형공장·호이스트·신축부지 분양부터 인허가까지 원스톱 책임 중개</p>
            </div>
            <div style="background:rgba(255,255,255,0.12); padding:14px 20px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); text-align:right;">
                <div style="font-size:13px; color:#bfdbfe;">대표 공인중개사 김태형 직통 상담</div>
                <div style="font-size:24px; font-weight:800; color:#fde047;">📞 032-582-6200</div>
                <div style="font-size:15px; font-weight:700; color:#ffffff;">📱 010-2660-8276</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    web_tab1, web_tab2, web_tab3 = st.tabs([
        "🔍 [실시간 공장·창고 매물 검색] 원터치 퀵필터",
        "🏗️ [신축공장 & 산업용지 특별분양관] 사진·분양가 안내",
        "📝 [공장 구해요 / 내놓아요] 1:1 맞춤 중개 의뢰"
    ])

    # ---------------------------------------------------------
    # 홈페이지 탭 1: 토미부동산 스타일 초고속 공장·창고 검색
    # ---------------------------------------------------------
    with web_tab1:
        st.markdown("##### ⚡ 찾으시는 공장 조건을 선택하시면 0.1초 만에 매물이 필터링됩니다")
        wf1, wf2, wf3, wf4, wf5 = st.columns([1.2, 1.3, 1.3, 1.3, 1.8])
        with wf1:
            w_deal = st.selectbox("거래 형태", ["전체 (임대+매매)", "임대차(월세)", "매매"], key="w_deal")
        with wf2:
            w_region = st.selectbox("희망 지역(동)", ["인천 전체", "가좌동", "석남동", "원창동", "오류동/검단", "경서동/기타"], key="w_reg")
        with wf3:
            w_pyung = st.selectbox("실사용 평수대", ["전체 평수", "60평 이하", "60평 ~ 120평", "120평 ~ 200평", "200평 이상"], key="w_py")
        with wf4:
            w_spec = st.selectbox("핵심 설비 조건", ["전체 설비", "🏗️ 호이스트 완비", "🚛 츄레라/대형차 진입", "⚡ 동력 50kW 이상"], key="w_sp")
        with wf5:
            w_kw = st.text_input("키워드 빠른 검색", placeholder="예: 가좌IC, 단독마당, 공실, 급매...", key="w_kw")

        show_df = df_p.copy()
        if w_deal != "전체 (임대+매매)":
            show_df = show_df[show_df["거래구분"].astype(str).str.contains(w_deal[:2], na=False)]
        if w_region != "인천 전체":
            r_token = w_region.split("/")[0]
            show_df = show_df[show_df["소재지(권역)"].astype(str).str.contains(r_token, na=False)]
        if w_pyung != "전체 평수":
            def filter_web_pyung(a_txt, mode):
                nums = parse_pyung_numbers(a_txt)
                if not nums: return True
                p = nums[0]
                if mode == "60평 이하": return p <= 60
                if mode == "60평 ~ 120평": return 60 <= p <= 120
                if mode == "120평 ~ 200평": return 120 <= p <= 200
                if mode == "200평 이상": return p >= 200
                return True
            show_df = show_df[show_df["면적"].apply(lambda x: filter_web_pyung(x, w_pyung))]
        if w_spec == "🏗️ 호이스트 완비":
            show_df = show_df[show_df["호이스트"].astype(str).str.contains("완비|톤|T", na=False)]
        elif w_spec == "🚛 츄레라/대형차 진입":
            show_df = show_df[show_df["대형차량"].astype(str).str.contains("츄레라|트레일러|11", na=False)]
        elif w_spec == "⚡ 동력 50kW 이상":
            show_df = show_df[show_df["동력"].astype(str).str.contains("50|75|100|150|200", na=False)]
        if w_kw.strip():
            k = w_kw.strip()
            show_df = show_df[show_df["소재지(권역)"].astype(str).str.contains(k, na=False) | show_df["특징메모"].astype(str).str.contains(k, na=False)]

        st.caption(f"📢 현재 조건에 부합하는 공장·창고 실매물: **총 {len(show_df)}건** (보안상 상세 번지수는 전화 문의 시 즉시 안내해 드립니다)")

        if show_df.empty:
            st.info("해당 조건의 매물이 홈페이지에 아직 업로드되지 않았습니다. [공장 구해요] 탭에 남겨주시면 비공개 보유 매물을 즉시 찾아드립니다!")
        else:
            # 3열 반응형 그리드 카드 렌더링
            prop_list_web = show_df.to_dict("records")
            cols_per_row = 3
            for i in range(0, len(prop_list_web), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(prop_list_web):
                        item = prop_list_web[i + j]
                        with row_cols[j]:
                            badge_str = f"{item.get('거래구분','')} | {item.get('입주/공실상태','즉시협의')}"
                            img_html = get_image_base64_html(item.get("사진경로", ""), height_px=185, badge_text=badge_str)
                            st.markdown(f"""
                            <div class="prop-web-card">
                                {img_html}
                                <div class="prop-web-body">
                                    <div style="font-size:13px; color:#2563eb; font-weight:700;">📍 {item.get('소재지(권역)','')} (지번 비공개)</div>
                                    <div style="font-size:18px; font-weight:800; color:#0f172a; margin:4px 0 8px 0;">{item.get('가격(보/월)','')}</div>
                                    <div style="margin-bottom:8px; line-height:1.8;">
                                        <span class="tag-orange">📐 {item.get('면적','')}</span>
                                        <span class="tag-blue">🏗️ {item.get('호이스트','')}</span>
                                        <span class="tag-green">⚡ 동력 {item.get('동력','')}</span>
                                        <span class="tag-gray">🏢 {item.get('층고','')}</span>
                                        <span class="tag-gray">🚛 {item.get('대형차량','')}</span>
                                    </div>
                                    <div style="font-size:13px; color:#475569; background:#f8fafc; padding:8px 10px; border-radius:6px; min-height:48px;">
                                        {item.get('특징메모','')}
                                    </div>
                                    <div style="margin-top:10px; display:flex; gap:6px;">
                                        <a href="tel:010-2660-8276" style="flex:1; text-align:center; background:#1e3a8a; color:white; padding:8px 0; border-radius:6px; text-decoration:none; font-weight:700; font-size:13px;">📞 전화 상담</a>
                                        <a href="sms:010-2660-8276" style="flex:1; text-align:center; background:#f59e0b; color:#0f172a; padding:8px 0; border-radius:6px; text-decoration:none; font-weight:700; font-size:13px;">💬 문자 문의</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 홈페이지 탭 2: 신축공장 & 토지 특별분양관 (사진 + 분양가)
    # ---------------------------------------------------------
    with web_tab2:
        st.subheader("🏗️ 인천 서구·산업단지 신축공장 및 산업용지 특별분양관")
        st.caption("시설자금 대출 최대 80% 지원! 현재 지불하시는 월세 수준으로 내 공장을 분양받으실 수 있는 검증된 현장입니다.")

        if df_dev.empty:
            st.info("현재 등록된 신축분양 현장이 없습니다.")
        else:
            dev_records = df_dev.to_dict("records")
            d_cols_cnt = 2
            for i in range(0, len(dev_records), d_cols_cnt):
                d_cols = st.columns(d_cols_cnt)
                for j in range(d_cols_cnt):
                    if i + j < len(dev_records):
                        dv = dev_records[i + j]
                        with d_cols[j]:
                            d_img_html = get_image_base64_html(dv.get("사진경로", ""), height_px=220, badge_text="🏗️ 신축분양 / 토지분양")
                            st.markdown(f"""
                            <div class="prop-web-card">
                                {d_img_html}
                                <div class="prop-web-body">
                                    <h4 style="margin:0 0 4px 0; color:#1e3a8a; font-size:19px;">🏢 {dv.get('사업지명','')}</h4>
                                    <div style="font-size:13.5px; color:#64748b; margin-bottom:8px;">📍 소재지: {dv.get('소재지','')}</div>
                                    <div style="font-size:20px; font-weight:800; color:#c53030; margin-bottom:10px;">💰 분양가: {dv.get('분양공급가','')}</div>
                                    <div style="background:#fffaf0; border:1px solid #feebc8; border-radius:8px; padding:10px 12px; font-size:13.5px; line-height:1.7;">
                                        • <b>분양 대지면적</b>: {dv.get('분양대지평수','')} (건폐율 {dv.get('건폐율','')})<br>
                                        • <b>건축 연면적</b>: {dv.get('총연면적','')} (1층 바닥 {dv.get('1층바닥평수','')} / {dv.get('건물층수','')})<br>
                                        • <b>도로 및 설비</b>: {dv.get('도로여건','')} | 층고 {dv.get('층고제원','')} | 동력 {dv.get('인입동력','')}<br>
                                        • <b>현장 특징</b>: {dv.get('특징메모','')}
                                    </div>
                                    <div style="margin-top:12px;">
                                        <a href="tel:010-2660-8276" style="display:block; text-align:center; background:#c53030; color:white; padding:10px 0; border-radius:6px; text-decoration:none; font-weight:800; font-size:14px;">📞 분양홍보관 & 현장투어 예약 (010-2660-8276)</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 홈페이지 탭 3: 고객 매물 구해요/내놓아요 접수 -> 3번 CRM 자동 저장
    # ---------------------------------------------------------
    with web_tab3:
        st.subheader("📝 공장·창고 구해요 / 내놓아요 (김태형 대표 1:1 직통 접수)")
        st.caption("남겨주신 정보는 외부에 절대 공개되지 않으며, 대표 공인중개사가 확인 후 직접 연락드립니다.")

        with st.form("web_customer_inquiry_form"):
            wq1, wq2, wq3 = st.columns(3)
            with wq1:
                req_type = st.selectbox("의뢰 구분 *", ["🔍 공장/창고 구합니다 (임차·매수)", "🏢 공장/창고 내놓습니다 (임대·매도)", "🏗️ 신축분양 상담 원합니다"])
                req_name = st.text_input("기업명 또는 성함 *", placeholder="예: (주)대한정밀 김대표")
            with wq2:
                req_phone = st.text_input("연락처 *", placeholder="예: 010-1234-5678")
                req_loc = st.text_input("희망 지역 (또는 물건 소재지) *", placeholder="예: 인천 서구 가좌동, 석남동 일대")
            with wq3:
                req_area = st.text_input("희망 평수 (또는 물건 면적) *", placeholder="예: 바닥 80~120평")
                req_budget = st.text_input("희망 예산 / 보증금·월세", placeholder="예: 보 3,000 / 월 250 선")

            req_memo = st.text_area("상세 요청사항 (업종, 호이스트 유무, 필요 전력kW, 입주 희망일 등)", placeholder="예: 금속가공 업종이며 호이스트 5톤과 동력 50kW 이상 필요합니다.")

            if st.form_submit_button("🚀 우리공장부동산에 중개 의뢰 접수하기", type="primary", use_container_width=True):
                if not req_name or not req_phone:
                    st.error("성함과 연락처는 필수 입력 항목입니다.")
                else:
                    save_customer({
                        "접수일자": datetime.today().strftime("%Y-%m-%d"),
                        "최근연락일": datetime.today().strftime("%Y-%m-%d"),
                        "중요도": "⭐⭐⭐ S급(홈페이지직접접수)",
                        "거래구분": req_type[:10],
                        "업종인허가": "홈페이지접수건",
                        "상호/고객명": f"[웹접수] {req_name}",
                        "연락처": req_phone,
                        "희망권역": req_loc,
                        "희망평수": req_area,
                        "예산(보증금/월세/매매가)": req_budget,
                        "입주시기": "협의",
                        "호이스트": "상담확인",
                        "대형차진입": "상담확인",
                        "희망전력kW": "상담확인",
                        "상담메모": f"[{req_type}] {req_memo}",
                        "상담히스토리": f"[{datetime.today().strftime('%Y-%m-%d %H:%M')}] 공식 홈페이지를 통해 고객이 직접 접수함\n",
                        "진행상태": "상담 접수 (매물 대기중)"
                    })
                    st.success("✅ 접수가 완료되었습니다! 우리공장부동산 김태형 대표가 빠르게 확인 후 연락드리겠습니다.")

    # 하단 고정 플로팅 바 (모바일/PC 공통)
    st.markdown("""
    <div class="floating-cta-bar">
        <div style="font-size:14px; font-weight:700;">🏭 <b>우리공장부동산</b> | 인천 서구 공장·창고·신축분양 전문 (대표 김태형)</div>
        <div style="display:flex; gap:10px;">
            <a href="tel:032-582-6200" style="background:#2563eb; color:white; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:700; font-size:13px;">☎ 사무실 032-582-6200</a>
            <a href="tel:010-2660-8276" style="background:#f59e0b; color:#0f172a; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:800; font-size:13px;">📱 직통 010-2660-8276</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================
# 0. 🏃 [임장/작업] 현장 공장 물건따기 파이프라인 (관리자 전용)
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["FACTORY_HUNT"]:
    st.title("🏃 현장 공장 물건따기 파이프라인 (임장 장부)")
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
        for d_nm, jb, ow, ph, ex_d, r_d in exp_alerts:
            st.markdown(f"<div class='remind-card-red'>🚨 [만기도래] <b>{d_nm} {jb}</b> ({ow} / {ph}) | 만기예정일: <b>{ex_d} (D-{r_d})</b></div>", unsafe_allow_html=True)

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
        with f3: kw_hunt = st.text_input("🔎 지번 / 상호 / 소유자 검색", key="hunt_k_f")
        with f4:
            st.write("")
            st.link_button("📄 정부24 건축물대장 열람", "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098", use_container_width=True)

        active_df = df_h[~df_h["진행상태"].str.contains("완료", na=False)].copy()
        if sel_dong != "전체 동 모아보기": active_df = active_df[active_df["동"] == sel_dong]
        if sel_stat != "전체 상태": active_df = active_df[active_df["진행상태"].str.contains(sel_stat.replace("🚗 ","").replace("📞 ","").replace("🔄 ",""), na=False)]
        if kw_hunt.strip():
            kw = kw_hunt.strip()
            active_df = active_df[active_df["지번"].astype(str).str.contains(kw, na=False) | active_df["소유자/법인명"].astype(str).str.contains(kw, na=False) | active_df["상호"].astype(str).str.contains(kw, na=False)]

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
                new_lg = st.selectbox("대장", ledger_opts, index=lg_idx, key=f"hlg_{idx}", label_visibility="collapsed")
                if new_lg != curr_lg:
                    df_h.at[idx, "대장체크"] = new_lg; save_all_hunting(df_h); st.rerun()
            with c_exp:
                cur_exp_val = str(r.get("임대만기예정일", "")) if pd.notna(r.get("임대만기예정일", "")) else ""
                new_exp = st.text_input("만기일", value=cur_exp_val, placeholder="만기:2027-03-01", key=f"hexp_{idx}", label_visibility="collapsed")
                if new_exp != cur_exp_val:
                    df_h.at[idx, "임대만기예정일"] = new_exp; save_all_hunting(df_h); st.rerun()
            with c_map: st.link_button("🗺️ 지도", map_url, use_container_width=True)
            with c_status:
                new_st = st.selectbox("상태", status_opts, index=st_idx, key=f"hst_{idx}", label_visibility="collapsed")
                if new_st != r["진행상태"]:
                    df_h.at[idx, "진행상태"] = new_st; save_all_hunting(df_h); st.rerun()
            with c_done_btn:
                if st.button("🎉 확보!", key=f"h_done_{idx}", type="primary", use_container_width=True):
                    df_h.at[idx, "진행상태"] = "🎉 확보 완료"; save_all_hunting(df_h); st.rerun()
            st.markdown("<hr style='margin:3px 0 6px 0; border:0; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)

    with h_tab_done:
        done_df = df_h[df_h["진행상태"].str.contains("완료", na=False)].copy()
        for d_idx, d_row in done_df.iterrows():
            st.markdown(f"<div class='hunt-item-done'><b>📍 {d_row['동']} {d_row['지번']}</b> ({d_row['소유자/법인명']}) | 📞 {d_row.get('연락처','')} | 💡 {d_row.get('현장메모','')}</div>", unsafe_allow_html=True)
            col_pr, col_ar, col_to_reg, col_del = st.columns([1.5, 1.2, 1.5, 0.8])
            with col_pr: tr_price = st.text_input("보증금 / 월세 *", placeholder="예: 보 3,000 / 월 250", key=f"tr_p_{d_idx}")
            with col_ar: tr_area = st.text_input("전용 평수 *", placeholder="예: 75평", key=f"tr_a_{d_idx}")
            with col_to_reg:
                st.write("")
                if st.button("🚀 홈페이지 & 정식장부 이관", key=f"btn_tr_{d_idx}", type="primary", use_container_width=True):
                    if tr_price and tr_area:
                        save_property({
                            "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": "현재 공실(즉시입주)", "계약만료일": "즉시 협의",
                            "거래구분": "임대차(월세)", "소재지(권역)": f"인천 서구 {d_row['동']}", "상세주소(지번)": f"인천 서구 {d_row['동']} {d_row['지번']}",
                            "임대인(건물주)": d_row['소유자/법인명'], "임대인연락처": d_row['연락처'], "가격(보/월)": tr_price, "면적": tr_area,
                            "층고": "처마 7.5m", "동력": "30kW", "호이스트": "호이스트 무관", "도로/주차": "화물차 접안 편리",
                            "대형차량": "11T 윙바디 수월", "특징메모": f"[현장확보] {d_row.get('현장메모','')}", "사진경로": "", "추천매물여부": "🌟프리미엄추천"
                        })
                        st.success("✅ 정식 매물 장부 및 고객용 홈페이지에 동시 업로드되었습니다!")
            with col_del:
                st.write("")
                if st.button("제거", key=f"btn_d_del_{d_idx}", use_container_width=True):
                    df_h = df_h.drop(df_h.index[d_idx]).reset_index(drop=True); save_all_hunting(df_h); st.rerun()

    with h_tab2:
        raw_text_batch = st.text_area("작업 메모 텍스트 붙여넣기:", height=150, placeholder="석남동 223-360 > 이해영 , 최완규 (신창코팅) 032-577-0104")
        if st.button("⚡ 1초 자동 분석 등록", type="primary", use_container_width=True):
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
                    save_all_hunting(df_h); st.rerun()

# =============================================================
# 1. 🏭 [주업] 공장 매물 등록 (현장 사진 업로드 -> 홈페이지 실시간 자동 연동!)
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["FACTORY_REG"]:
    st.title("🏭 공장 매물 등록 (홈페이지 실시간 업로드 + 확인설명서 + 손님 역매칭)")
    st.caption("여기서 매물과 사진을 등록하면 [고객용 반응형 홈페이지]에 0.1초 만에 자동 게시되며, 상세 지번과 건물주 연락처는 철저히 비밀로 보호됩니다.")

    with st.expander("🔒 [중개사 비밀 보관용] 상세 지번 및 건물주 직통 연락처 (홈페이지 비노출)", expanded=True):
        s1, s2, s3 = st.columns(3)
        with s1: secret_address = st.text_input("📌 상세 지번/호수 (비공개)", placeholder="예: 인천 서구 가좌동 556-12")
        with s2: owner_name = st.text_input("👤 건물주 성함 (비공개)", placeholder="예: 박회장님")
        with s3: owner_phone = st.text_input("📞 건물주 연락처 (비공개)", placeholder="예: 010-8888-9999")

    img_col1, img_col2 = st.columns([2.5, 1.5])
    with img_col1:
        prop_img_file = st.file_uploader("📸 공장 외관/내부 대표 사진 업로드 (첨부 시 홈페이지 카드에 즉시 표시)", type=["jpg", "jpeg", "png", "webp"])
    with img_col2:
        is_featured = st.selectbox("🌟 홈페이지 상단 노출 설정", ["🌟프리미엄추천", "일반매물"])

    b1, b2, b3, b4 = st.columns(4)
    with b1: loc = st.text_input("소재지 / 권역 (홈페이지 표시용) *", value="인천 서구 가좌동")
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
            "일반공업지역 (비산단 자유입주)", "일반공업지역 (국가/일반산단 - 입주계약 필수)", "전용공업지역 (중화학/공해업종 가능)", "준공업지역 (주거혼재)"
        ])

    memo = st.text_area("매물 핵심 강점 메모 (홈페이지 및 블로그 설명문에 반영)", placeholder="예: 가좌IC 3분 거리. 호이스트 및 동력 완비로 초기 시설 투자비 절감.")

    price_str = f"보증금 {dep_man:,}만 원 / 월세 {rent_man:,}만 원" if rent_man > 0 else f"매매가 {dep_man:,}만 원"
    conv_deposit_man = dep_man + (rent_man * 100) if rent_man > 0 else dep_man
    comm_base_won = (dep_man + (rent_man * 100)) * 10000 if rent_man > 0 else dep_man * 10000
    max_comm_won = int(comm_base_won * 0.009)

    if st.button("🚀 홈페이지 실시간 게시 + 장부 저장 + 확인설명서 + 블로그 원고 생성", type="primary", use_container_width=True):
        saved_img_path = save_uploaded_image(prop_img_file, prefix="factory")
        save_property({
            "등록일자": datetime.today().strftime("%Y-%m-%d"), "입주/공실상태": vacancy_status, "계약만료일": expire_date,
            "거래구분": deal_type, "소재지(권역)": loc, "상세주소(지번)": secret_address, "임대인(건물주)": owner_name,
            "임대인연락처": owner_phone, "가격(보/월)": price_str, "면적": area, "층고": ceiling, "동력": power,
            "호이스트": hoist, "도로/주차": f"{road} / {parking_count}", "대형차량": big_truck,
            "특징메모": f"[{zoning_choice.split()[0]}] {memo}", "사진경로": saved_img_path, "추천매물여부": is_featured
        })
        st.success("✅ 매물과 사진이 [고객용 반응형 홈페이지] 및 보유 장부에 실시간 등록되었습니다!")

        matched_custs = match_customers_for_property(loc, area)
        if matched_custs:
            st.markdown(f"##### 🎯 [자동 역매칭] 이 매물({loc} / {area})을 기다리는 손님이 **{len(matched_custs)}명** 있습니다!")
            for mc in matched_custs:
                st.markdown(f"<div class='calc-box-orange' style='padding:8px 14px;'>👤 <b>{mc.get('상호/고객명','')}</b> ({mc.get('중요도','')}) | 📞 <b>{mc.get('연락처','')}</b></div>", unsafe_allow_html=True)

        legal_report_text = f"""[중개대상물 확인·설명서 (비주거용 건축물) 필수 기재 사항 요약표]
• 소재지: {secret_address if secret_address else loc} | 전용면적: {area} | 주용도: {bldg_use} | 구조: {building_structure}
• 사용승인일: {approval_date if approval_date else '공적장부 확인'} | 위반건축물 여부: {violation_status}
• 도로/차량진입: {road} ({big_truck}) | 주차: {parking_count} | 인입전력: {power} | 층고: {ceiling} | 호이스트: {hoist}
• 거래예정금액: {price_str} (환산보증금 {conv_deposit_man:,}만 원) | 법정중개보수(0.9%): {max_comm_won:,}원(부가세별도)
- 우리부동산 공인중개사사무소 대표 김태형 (032-582-6200 / 010-2660-8276) -"""
        st.text_area("📋 확인·설명서 표준 텍스트", legal_report_text, height=200)

# =============================================================
# 2. 🏗️ [주업] 신축공장 분양 등록 (토지/현장 사진 업로드 -> 홈페이지 실시간 연동!)
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["NEW_DEV"]:
    st.title("🏗️ 신축공장·토지 분양 등록 (홈페이지 자동 게시) & 맞춤 설계 제안서")
    st.caption("토지나 조감도 사진을 올리고 분양가를 저장하면 [홈페이지 신축분양 전용관]에 즉시 게시되며, [월세 vs 분양 비교 설득표]도 함께 산출됩니다.")

    dev_img_file = st.file_uploader("📸 신축 현장 / 토지 사진 업로드 (홈페이지 신축분양관에 즉시 노출됩니다)", type=["jpg", "jpeg", "png", "webp"])

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        site_name = st.text_input("분양 현장명 *", value="가좌 첨단제조단지 신축분양")
        site_addr = st.text_input("사업지 소재지 *", value="인천 서구 가좌동 일원")
    with p2:
        custom_land = st.number_input("분양 대지면적 (평) *", min_value=10, max_value=5000, value=150, step=10)
        road_width = st.number_input("접면 도로 폭 (m) *", min_value=4, max_value=50, value=12, step=1)
    with p3:
        f1_pyung = st.number_input("1층 바닥평수 (평) *", min_value=5, max_value=5000, value=90, step=5)
        f2_pyung = st.number_input("2층 사무/제조 (평)", min_value=0, max_value=5000, value=30, step=5)
    with p4:
        cust_company = st.text_input("제안 대상 기업명", value="(주)대한정밀")
        curr_paying_rent = st.number_input("🔥 고객의 현재 월세 (만 원)", min_value=100, max_value=5000, value=450, step=50)

    pr1, pr2, pr3, pr4 = st.columns(4)
    with pr1: base_unit_price = st.number_input("1층 분양단가 (대지 평당 만 원)", value=1200, step=50)
    with pr2: add_unit_price = st.number_input("2층 증축단가 (건축 평당 만 원)", value=380, step=10)
    with pr3: loan_ratio = st.slider("시설자금 대출 비율 (%)", 50, 85, 80, 5)
    with pr4: interest_rate = st.number_input("예상 대출금리 (연 %)", value=4.1, step=0.1)

    dev_memo = st.text_input("신축분양 핵심 홍보 문구 (홈페이지 표시용)", value="시설자금 80% 저리 대출 가능, 대형 트레일러 진입 및 맞춤 설계 지원")

    actual_bcr = round((f1_pyung / custom_land) * 100, 1) if custom_land > 0 else 0
    yard_pyung = max(0, custom_land - f1_pyung)
    total_bldg_area = f1_pyung + f2_pyung
    total_dev_price = int((custom_land * base_unit_price + f2_pyung * add_unit_price) * 10000)
    loan_amt = int(total_dev_price * (loan_ratio / 100.0))
    pure_down = total_dev_price - loan_amt
    acq_tax = int(total_dev_price * 0.046)
    monthly_interest = int((loan_amt * (interest_rate / 100.0)) / 12)
    curr_rent_won = curr_paying_rent * 10000

    if st.button("🚀 홈페이지 [신축분양관]에 사진·분양가 실시간 게시하기", type="primary", use_container_width=True):
        saved_dev_img = save_uploaded_image(dev_img_file, prefix="newdev")
        save_new_dev({
            "등록일자": datetime.today().strftime("%Y-%m-%d"),
            "사업지명": site_name, "소재지": site_addr,
            "분양대지평수": f"{custom_land}평", "건폐율": f"{actual_bcr}%",
            "1층바닥평수": f"{f1_pyung}평", "건물층수": f"지상 {2 if f2_pyung > 0 else 1}층",
            "총연면적": f"{total_bldg_area}평",
            "분양공급가": f"{total_dev_price:,}원 (대출 {loan_ratio}% 가능)",
            "도로여건": f"전면 {road_width}m 광폭도로 접",
            "층고제원": "처마 8m 이상", "인입동력": "50~100kW 맞춤인입",
            "특징메모": dev_memo, "사진경로": saved_dev_img
        })
        st.success("✅ 신축공장 사진과 분양가가 [고객용 홈페이지 신축분양관]에 실시간 업로드되었습니다!")

    st.markdown(f"""
    <div class="calc-box-orange">
        <h4 style="color: #c05621; margin: 0 0 8px 0;">📊 [{cust_company}] 신축 분양 견적 & [월세 vs 내 공장 취득] 비교표</h4>
        • <b>분양 제원</b>: 대지 <b>{custom_land}평</b> / 건물 연면적 <b>{total_bldg_area}평</b> (1F {f1_pyung}평, 단독마당 {yard_pyung}평)<br>
        • <b>총 분양 공급가</b>: <b style="color:#c53030; font-size:18px;">{total_dev_price:,}원</b> | 대출({loan_ratio}%): <b>{loan_amt:,}원</b> | 필요 현금(취득세 포함): <b>약 {pure_down+acq_tax:,}원</b><br>
        • <b>비교 설득</b>: 현재 소멸성 월세(<b>월 {curr_rent_won:,}원</b>) vs 분양 대출이자(<b>월 약 {monthly_interest:,}원</b>) ➡️ 월 지출 차액 <b>{abs(curr_rent_won-monthly_interest):,}원</b>!
    </div>
    """, unsafe_allow_html=True)

# =============================================================
# 3. 📋 [주업] 공장 손님 CRM (홈페이지 의뢰 실시간 수신 & 투어 스케줄러)
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["CUSTOMER_CRM"]:
    st.title("📋 공장 손님 CRM 장부 (홈페이지 접수 실시간 연동)")
    df_c = load_customers()
    df_p = load_properties()
    today = datetime.today()

    tab_list, tab_tour, tab_edit = st.tabs(["📊 손님 장부 목록 (홈페이지 접수 포함)", "🚗 임장 투어 코스 & 유인물 생성기", "✍️ 손님 수동 등록"])

    with tab_list:
        if not df_c.empty:
            for orig_idx, c_row in df_c.iterrows():
                is_vip = "S급" in str(c_row.get("중요도", "")) or "A급" in str(c_row.get("중요도", ""))
                card_class = "customer-card-pro-vip" if is_vip else "customer-card-pro"
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between;">
                        <div><b>👤 {get_safe_cust_val(c_row, '상호/고객명')}</b> <span style="color:#d69e2e;">{get_safe_cust_val(c_row, '중요도')}</span> <span class="tag-blue">{get_safe_cust_val(c_row, '거래구분')}</span></div>
                        <div>📞 <b>{get_safe_cust_val(c_row, '연락처')}</b> | 접수일: {get_safe_cust_val(c_row, '접수일자')}</div>
                    </div>
                    <div style="margin-top:6px;">
                        <span class="tag-orange">📐 {get_safe_cust_val(c_row, '희망평수')}</span>
                        <span class="tag-orange">📍 {get_safe_cust_val(c_row, '희망권역')}</span>
                        <span class="tag-orange">💰 {get_safe_cust_val(c_row, '예산(보증금/월세/매매가)')}</span>
                    </div>
                    <div style="font-size:13px; color:#4a5568; margin-top:6px;">💡 {get_safe_cust_val(c_row, '상담메모')}</div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("등록된 손님이 없습니다.")

    with tab_tour:
        if not df_p.empty:
            p_list = df_p.to_dict("records")
            selected_tour_indices = st.multiselect("투어할 매물 선택:", range(len(p_list)), format_func=lambda i: f"{p_list[i].get('소재지(권역)','')} ({p_list[i].get('면적','')}) - {p_list[i].get('가격(보/월)','')}")
            if selected_tour_indices:
                handout_lines = [f"[우리공장부동산 현장 투어 브리핑 시트 - {today.strftime('%Y-%m-%d')}]"]
                for seq_i, p_i in enumerate(selected_tour_indices):
                    tp = p_list[p_i]
                    handout_lines.append(f"■ [{chr(65+seq_i)}안] {tp.get('소재지(권역)','')} | {tp.get('면적','')} | {tp.get('가격(보/월)','')} | {tp.get('호이스트','')} | {tp.get('특징메모','')}")
                st.text_area("손님 배포용 시트", "\n\n".join(handout_lines), height=220)

    with tab_edit:
        with st.form("cust_quick_form"):
            c1, c2, c3 = st.columns(3)
            with c1: c_name = st.text_input("상호 / 고객명 *"); c_phone = st.text_input("연락처 *")
            with c2: c_loc = st.text_input("희망 권역 *", value="인천 서구 가좌/석남"); c_area = st.text_input("희망 평수 *", value="80~120평")
            with c3: c_star = st.selectbox("VIP 등급", ["⭐⭐⭐ S급(최우선)", "⭐⭐ A급(유력)"]); c_budget = st.text_input("희망 예산", value="보 3,000 / 월 250")
            c_memo = st.text_area("상담 메모")
            if st.form_submit_button("💾 신규 손님 저장", type="primary", use_container_width=True):
                if c_name and c_phone:
                    save_customer({
                        "접수일자": today.strftime("%Y-%m-%d"), "최근연락일": today.strftime("%Y-%m-%d"),
                        "중요도": c_star, "거래구분": "임대차(월세)", "업종인허가": "일반제조", "상호/고객명": c_name,
                        "연락처": c_phone, "희망권역": c_loc, "희망평수": c_area, "예산(보증금/월세/매매가)": c_budget,
                        "입주시기": "협의", "호이스트": "무관", "대형차진입": "11T 수월", "희망전력kW": "50kW",
                        "상담메모": c_memo, "상담히스토리": "", "진행상태": "상담 접수"
                    })
                    st.rerun()

# =============================================================
# 4. 📁 [주업] 공장 보유 매물 장부 & 멀티 브리핑 장바구니
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["FACTORY_BOOK"]:
    st.title("📁 공장 보유 매물 장부 & 멀티 브리핑 / 네이버 광고 생성기")
    df_p = load_properties()
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True, height=260)
        prop_records = df_p.to_dict("records")
        multi_indices = st.multiselect("손님에게 묶어서 비교 브리핑할 매물 선택:", range(len(prop_records)), default=[0], format_func=lambda i: f"[{prop_records[i].get('소재지(권역)','')}] {prop_records[i].get('면적','')} | {prop_records[i].get('가격(보/월)','')}")
        if multi_indices:
            cart_blocks = ["[🏢 우리공장부동산 맞춤 공장 비교 추천 브리핑]"]
            for idx_order, m_i in enumerate(multi_indices):
                mp = prop_records[m_i]
                cart_blocks.append(f"▶ [{chr(65 + idx_order)}안] {mp.get('소재지(권역)','')} ({mp.get('면적','')})\n• 조건: {mp.get('가격(보/월)','')}\n• 제원: {mp.get('층고','')} / 동력 {mp.get('동력','')} / {mp.get('호이스트','')}\n• 특징: {mp.get('특징메모','')}")
            cart_blocks.append("- 우리공장부동산 대표 김태형 (032-582-6200 / 010-2660-8276) -")
            st.text_area("📲 멀티 비교 브리핑 카톡 복사창", "\n\n".join(cart_blocks), height=250)

# =============================================================
# 5. 🔍 [주업] 공장·창고 AI 시세 추정기 & 건물주 설득 리포트
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["PRICE_AI"]:
    st.title("🔍 인천 공장·창고 AI 시세 추정기 & 건물주 설득 리포트")
    v1, v2, v3 = st.columns(3)
    with v1:
        zone_sel = st.selectbox("📍 권역 선택", ["서구 가좌동 (일반공업)", "서구 석남동 (일반공업)", "서구 원창동/청라 (북항배후)", "서구 오류동/검단 (검단산단)"])
        land_p = st.number_input("📐 대지면적 (평)", value=200, step=10)
    with v2:
        bldg_p = st.number_input("🏢 건물 연면적 (평)", value=140, step=10)
        bldg_age = st.slider("🗓️ 건물 경과 연수", 0, 35, 10, 1)
    with v3:
        infra_spec = st.selectbox("⚙️ 설비", ["호이스트 5T 이상 + 동력 100kW (+5,000만)", "호이스트 2.8T + 동력 50kW (+2,500만)", "기본 설비"])

    base_map = {"서구 가좌동 (일반공업)": 1150, "서구 석남동 (일반공업)": 1080, "서구 원창동/청라 (북항배후)": 1280, "서구 오류동/검단 (검단산단)": 1020}
    est_land = land_p * base_map[zone_sel] * 10000
    est_bldg = int(bldg_p * 380 * max(0.25, 1.0 - bldg_age * 0.025) * 10000)
    infra_add = 50000000 if "5T" in infra_spec else (25000000 if "2.8T" in infra_spec else 0)
    tot_sale = est_land + est_bldg + infra_add
    est_rent = int(bldg_p * 3.5) * 10000

    st.markdown(f"<div class='calc-box-orange'>• <b>추정 적정 매매가</b>: <b style='color:#c53030; font-size:20px;'>약 {tot_sale:,}원</b> | <b>권장 적정 임대료</b>: 보증금 {est_rent*10:,}원 / 월세 {est_rent:,}원</div>", unsafe_allow_html=True)

# =============================================================
# 6. 🍜 [부업] 맛집 탐방 전용 블로그
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["BLOG_FOOD"]:
    st.title("🍜 맛집 탐방 전문 블로그 엔진 (SEO 제목 5선 + 영수증 리뷰 + 숏폼)")
    c1, c2, c3 = st.columns(3)
    with c1:
        m_name = st.text_input("식당 상호명 *", placeholder="예: 메탄집 청라본점")
        m_loc = st.text_input("지역명 *", placeholder="예: 인천 청라")
        m_tone = st.selectbox("🎨 문체 선택", ["1. 미식가 분석형", "2. 데이트 감성형", "3. 가성비·회식형", "4. 동네 단골 찐후기형"])
    with c2:
        m_menu = st.text_input("주문 메뉴 및 가격 *", placeholder="예: 생삼겹살 2인분(32,000원)")
        m_addr = st.text_input("위치 및 주차 *", placeholder="예: 청라커낼로 123 (지하주차 무료)")
        m_wait = st.text_input("웨이팅 팁", placeholder="예: 주말 저녁 20분 대기")
    with c3:
        m_eval = st.text_input("한 줄 총평 *", placeholder="예: 연탄 불향과 육즙이 끝내주는 삼겹살 맛집")
        m_point = st.text_input("킬링 포인트", placeholder="예: 구운 묵은지와 첫 점의 육즙")
    m_taste = st.text_area("상세 맛 메모")

    if st.button("🚀 맛집 블로그 + 400자 영수증 리뷰 + 숏폼 생성", type="primary", use_container_width=True):
        if m_name and m_eval:
            post_body = f"""[추천 제목] {m_loc} 맛집 {m_name} 솔직후기 주차 웨이팅 총정리\n\n안녕하세요! 김소장입니다. 오늘은 {m_loc} '{m_name}' 방문 후기입니다.\n• 위치/주차: {m_addr}\n• 주문메뉴: {m_menu}\n• 총평: {m_eval} ({m_point})\n• 상세후기: {m_taste}\n#{m_loc.replace(' ','')}맛집 #{m_name.replace(' ','')} #내돈내산"""
            review_text = f"⭐⭐⭐⭐⭐\n{m_loc} 찐맛집 인정합니다! {m_menu} 먹어봤는데 {m_eval}. {m_taste} 주차({m_addr})도 편해서 재방문 의사 100%입니다!"
            st.text_area("📝 블로그 본문", post_body, height=240)
            st.text_area(f"🧾 영수증 리뷰 ({len(review_text)}자)", review_text, height=130)

# =============================================================
# 7. 🧢 [부업] 일상·핫플·운동 블로그
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["BLOG_LIFE"]:
    st.title("🧢 일상·핫플·운동·취미 블로그 엔진")
    l1, l2, l3 = st.columns(3)
    with l1: d_title_kw = st.text_input("핵심 키워드 *", placeholder="예: 코비6 프로트로 농구화 / 태안 해루질"); d_loc = st.text_input("장소/브랜드 *", placeholder="예: 부천 체육관 / 태안 안면도")
    with l2: d_item = st.text_input("핵심 내용 *", placeholder="예: 2시간 풀타임 접지력 테스트"); d_wait_cost = st.text_input("준비물/팁", placeholder="예: 반업 추천 / 물때표 확인")
    with l3: d_eval = st.text_input("한 줄 총평 *", placeholder="예: 가드 포지션 최강의 접지력!"); d_point = st.text_input("하이라이트", placeholder="예: 급정지 스텝백 시 밀림 제로")
    d_note = st.text_area("상세 경험담 메모")
    if st.button("🚀 일상 블로그 + 릴스 대본 생성", type="primary", use_container_width=True):
        if d_title_kw and d_eval:
            st.text_area("📝 일상 블로그 원고", f"[추천 제목] {d_title_kw} 솔직후기 {d_item} 실전 팁\n\n안녕하세요 김소장입니다! 오늘은 {d_title_kw} 후기입니다.\n• 장소/대상: {d_loc}\n• 핵심포인트: {d_point}\n• 총평: {d_eval}\n• 상세내용: {d_note}\n• 꿀팁: {d_wait_cost}", height=260)

# =============================================================
# 8. 🏢 [부업] 실시간 청약·줍줍 & LH 공공임대 허브
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["APPLY_HOME"]:
    st.title("🏢 실시간 청약·줍줍 & LH 공공임대 (오류 0% 팩트 검증 시스템)")
    DEFAULT_API_KEY = "d1a0585bef6ed7240317271c754ad4be4f9ba74cdf342e6b714bbb85d3196f69"

    @st.cache_data(ttl=1800)
    def fetch_realtime_applyhome(api_key, sido_filter="전체"):
        results = []
        today_dt = datetime.today().date()
        start_date_cond = (datetime.today() - timedelta(days=60)).strftime("%Y-%m-%d")
        endpoints = [
            ("🏢 APT 일반/공공분양", "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"),
            ("🔥 무순위/취소 (줍줍)", "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getRemndrLttotPblancDetail")
        ]
        for label_type, url in endpoints:
            params = {"serviceKey": api_key, "page": 1, "perPage": 60, "returnType": "JSON", "cond[RCRIT_PBLANC_DE::GTE]": start_date_cond}
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
                            "진행상태": status_badge, "구분": label_type, "지역": str(row.get("SUBSCRPT_AREA_CODE_NM") or "전국"),
                            "단지명": str(row.get("HOUSE_NM") or ""), "공급위치": str(row.get("HSSPLY_ADRES") or ""),
                            "공급세대수": f"{row.get('TOT_SUPLY_HSHLDCO', 0)}세대", "모집공고일": str(row.get("RCRIT_PBLANC_DE") or ""),
                            "청약접수기간": f"{r_bgnde} ~ {r_endde}", "당첨자발표일": str(row.get("PRZWNER_PRESNATN_DE") or ""),
                            "시공사": str(row.get("BSNS_MBY_NM") or "시공사 확인"), "공고URL": str(row.get("PBLANC_URL") or "https://www.applyhome.co.kr")
                        })
            except Exception: continue
        return results

    sel_sido = st.selectbox("📍 지역 선택", ["전체", "서울", "인천", "경기"])
    live_list = fetch_realtime_applyhome(DEFAULT_API_KEY, sel_sido)
    if live_list:
        df_live = pd.DataFrame(live_list)
        st.dataframe(df_live, use_container_width=True, height=220)
        records = df_live.to_dict("records")
        sel_idx = st.selectbox("📌 단지 선택:", range(len(records)), format_func=lambda i: f"[{records[i]['진행상태']}] {records[i]['단지명']}")
        target = records[sel_idx]
        st.link_button(f"📄 [{target['단지명']}] 공식 모집공고문 열기", target["공고URL"], type="primary")
        lk1, lk2 = st.columns(2)
        with lk1: fact_qual = st.selectbox("신청 자격 확인", ["해당지역 거주 무주택세대주", "수도권 무주택세대구성원", "전국 만 19세 이상 (통장무관)"])
        with lk2: fact_resale = st.selectbox("전매제한 확인", ["당첨자 발표일로부터 1년", "당첨자 발표일로부터 3년", "전매제한 없음"])
        st.text_area("📋 청약 블로그 원고", f"안녕하세요! 공인중개사 김태형입니다.\n'{target['단지명']}' ({target['공급위치']}, 총 {target['공급세대수']}) 청약 안내입니다.\n- 접수기간: {target['청약접수기간']}\n- 당첨자발표: {target['당첨자발표일']}\n- 자격요건: {fact_qual} / 전매제한: {fact_resale}\n- 공고문 원문: {target['공고URL']}\n[면책공지] 신청 전 반드시 공식 모집공고문 원문을 재확인하시기 바랍니다.", height=240)

# =============================================================
# 9. ⚖️ [부업] 법원경매 목록 허브 (인천 공장 목록 & 수도권 아파트 목록)
# =============================================================
elif st.session_state["is_admin"] and menu_choice == MENU_DICT["AUCTION_HUB"]:
    st.title("⚖️ 법원경매 허브 (인천 공장 경매 목록 & 수도권 아파트 경매 목록)")
    factory_list, apt_list = get_auction_data()
    auction_tab1, auction_tab2 = st.tabs(["🏭 인천/산단 공장 경매 목록", "🏢 수도권 아파트 경매 목록"])

    with auction_tab1:
        st.dataframe(pd.DataFrame(factory_list)[["사건번호", "법원", "소재지", "세부용도", "대지면적", "총감정가", "최저가", "매각기일"]], use_container_width=True, height=180)
        chosen_fac_idx = st.selectbox("📌 공장 경매 사건 선택:", range(len(factory_list)), format_func=lambda i: f"[{factory_list[i]['사건번호']}] {factory_list[i]['소재지']}")
        cur_fac = factory_list[chosen_fac_idx]
        pure_re = cur_fac['토지감정가원'] + cur_fac['건물감정가원']
        st.markdown(f"<div class='calc-box-orange'>• <b>{cur_fac['사건번호']}</b> ({cur_fac['소재지']}) | 최저가: <b>{cur_fac['최저가']}</b> | 순수 부동산감정가: {pure_re:,}원 (기계기구 {cur_fac['기계기구감정가원']:,}원 분리)</div>", unsafe_allow_html=True)
        st.text_area("📋 공장 경매 블로그 원고", f"안녕하세요! 인천 공장 전문 공인중개사 김태형입니다.\n{cur_fac['법원']} [{cur_fac['사건번호']}] 공장 경매 브리핑입니다.\n- 소재지: {cur_fac['소재지']}\n- 면적: 대지 {cur_fac['대지면적']} / 건물 {cur_fac['건물면적']}\n- 감정가: {cur_fac['총감정가']} ➡️ 최저가: {cur_fac['최저가']} (매각기일: {cur_fac['매각기일']})\n- 핵심제원: {cur_fac['제원및코멘트']}\n- 산단자격: {cur_fac['산단입주자격']}\n☎ 입찰 및 경락대출 문의: 우리공장부동산 김태형 대표 (010-2660-8276)", height=240)

    with auction_tab2:
        st.dataframe(pd.DataFrame(apt_list)[["사건번호", "법원", "시도", "소재지", "평형타입", "감정가", "최저가", "매각기일"]], use_container_width=True, height=180)
        chosen_apt_idx = st.selectbox("📌 아파트 경매 사건 선택:", range(len(apt_list)), format_func=lambda i: f"[{apt_list[i]['사건번호']}] {apt_list[i]['소재지']}")
        cur_apt = apt_list[chosen_apt_idx]
        st.markdown(f"<div class='calc-box-orange'>• <b>{cur_apt['사건번호']}</b> ({cur_apt['소재지']}) | 감정가: {cur_apt['감정가']} ➡️ 최저가: <b>{cur_apt['최저가']}</b> | 실거래시세: {cur_apt['최근실거래가']}</div>", unsafe_allow_html=True)
        st.text_area("📋 아파트 경매 블로그 원고", f"안녕하세요! 공인중개사 김태형입니다.\n{cur_apt['법원']} [{cur_apt['사건번호']}] 아파트 경매 분석입니다.\n- 소재지: {cur_apt['소재지']} ({cur_apt['평형타입']}, {cur_apt['층수']})\n- 감정가: {cur_apt['감정가']} ➡️ 최저가: {cur_apt['최저가']} (매각기일: {cur_apt['매각기일']})\n- 권리분석: 말소기준({cur_apt['권리분석']['말소기준권리']}) 이후 소멸, {cur_apt['권리분석']['임차인분석']}\n☎ 상담문의: 우리공장부동산 김태형 대표 (010-2660-8276)", height=240)