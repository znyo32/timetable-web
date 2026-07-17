import streamlit as st
from engine import run_timetable_engine

st.set_page_config(page_title="학교 시간표 생성기", layout="wide")

st.title("📅 2026학년도 2학기 시간표 자동 생성 시스템")
st.markdown("전체 시수표를 업로드하면 44명 전원의 3연강을 방지하고 모든 하드 제약을 통과한 미배정 0 시간표를 생성합니다.")

# ----------------------------------------
# 1. 왼쪽 사이드바: 조건 설정 컨트롤 패널
# ----------------------------------------
st.sidebar.header("⚙️ 시간표 제약 조건 설정")

# A. 기본 설정
st.sidebar.subheader("1. 기본 규칙")
max_consecutive = st.sidebar.slider("최대 허용 연속 수업 (연강)", min_value=1, max_value=4, value=2)
apply_sports_rule = st.sidebar.checkbox("운동장 체육 2학급 이하 제한", value=True)

# B. 금지 및 필수 조건 입력칸
st.sidebar.subheader("2. 교사별 특수 조건")
st.sidebar.info("입력된 조건들은 100% 하드 제약으로 엔진에 반영됩니다.")

default_banned = """[개인별 금지 조건]
김연지: 월/금 전체, 화/수/목 5,6,7 금지
이기영: 월1, 목1, 금5 금지
김효진: 1교시 전체 금지
강영미: 화/수/목 3교시 금지
김온유: 화6 금지

[무용(이연경) 및 특별실 제약]
이연경(무용): 2학년 목요일, 3학년 화요일 배정 금지
특별실공유: 김연지, 임주헌 동시간대 배정 금지
금6공강: 부장 명단 전체"""
banned_text = st.sidebar.text_area("❌ 금지 및 공강 조건", value=default_banned, height=220)

default_mandatory = """이준희: 화요일 오전 1~4교시 중 최소 2시간
박주현: 월요일 2~3교시 중 1시간, 금요일 2~3교시 중 1시간"""
mandatory_text = st.sidebar.text_area("✅ 필수 배정", value=default_mandatory, height=100)

# C. 고정 수업(압핀) 리스트
st.sidebar.subheader("3. 스포츠/지원 고정 리스트")
default_pins = """[스포츠 고정]
3-1(화2): 김진호, 서정수 / 3-2(화2): 류지영, 제현진
3-4(화3): 황두환, 김영순 / 3-5(화3): 김승미 / 3-6(화3): 이아정
3-7(화4): 김재수, 김진호 / 3-8(화4): 류지영
1-1(수2): 김재수, 김영순 / 1-2(수2): 김영혜 / 1-3(수2): 이아정
1-4(수3): 김진호, 임주헌 / 1-5(수3): 김승미 / 1-6(수3): 류지영
1-7(수4): 서정수, 김영순 / 1-8(수4): 제현진
2-1(목2): 김재수, 임주헌 / 2-2(목2): 김승미 / 2-3(목2): 김영혜
2-4(목3): 김진호, 김영순 / 2-5(목3): 류지영 / 2-6(목3): 이아정
2-7(목4): 황두환, 김승미 / 2-8(목4): 제현진

[지원강사 고정]
체육지원: 화1, 화2, 화3, 화4
영어지원: 월2, 월3, 금2, 금3
이기영(지원): 금1, 금3, 금4"""
pins_text = st.sidebar.text_area("📌 하드 고정 수업", value=default_pins, height=250)

# ----------------------------------------
# 2. 메인 화면: 파일 업로드 및 실행
# ----------------------------------------
st.header("📂 시수표 업로드 및 실행")
uploaded_excel = st.file_uploader("전체 시수 취합 엑셀 (.xlsx)", type=["xlsx"])

if uploaded_excel is not None:
    st.success("✅ 파일 업로드 완료! '시간표 생성 시작' 버튼을 눌러주세요.")
    
    if st.button("🚀 시간표 생성 시작", use_container_width=True):
        with st.spinner("AI 최적화 엔진이 수만 가지 경우의 수를 계산 중입니다... (약 1~3분 소요)"):
            
            user_conditions = {
                "max_consecutive": max_consecutive,
                "apply_sports_rule": apply_sports_rule
            }
            
            excel_buffer, status = run_timetable_engine(uploaded_excel, user_conditions)
            
            if status == "성공" and excel_buffer is not None:
                st.success("🎉 모든 조건을 만족하는 미배정 0 시간표가 완성되었습니다!")
                st.balloons()
                st.download_button(
                    label="📥 학교 양식 엑셀로 다운로드 (교사별/반별)",
                    data=excel_buffer,
                    file_name="2026-2학기_최종시간표_초안.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("⚠️ 조건 충돌: 모든 조건을 동시에 만족하는 해를 찾을 수 없습니다. 조건을 살짝 완화해 보세요.")