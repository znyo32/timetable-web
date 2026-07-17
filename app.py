import streamlit as st
from engine import run_timetable_engine

st.set_page_config(page_title="학교 시간표 생성기", layout="wide")

st.title("📅 스마트 시간표 자동 생성 시스템")
st.markdown("모든 조건을 직접 제어할 수 있습니다. 오류가 날 경우 [필수] 규칙을 [차순위]로 낮춰가며 최적의 해를 찾아보세요.")

# ----------------------------------------
# 1. 자동 분배 규칙 (우선순위 설정)
# ----------------------------------------
st.header("🎛️ 1. 자동 배정 규칙 (우선순위 설정)")
st.info("각 규칙을 **[필수(무조건 지킴)]**, **[차순위(최대한 지킴)]**, **[미적용]** 중 하나로 선택하세요.")

col1, col2 = st.columns(2)
with col1:
    rule_3consec = st.radio("🚫 교과 3연강 금지", ["필수", "차순위", "미적용"], index=0, help="정규 교과는 예외 없이 3연강을 금지합니다.")
    rule_daily = st.radio("⚖️ 1일 수업 시수 균등 배정", ["필수", "차순위", "미적용"], index=1, help="하루에 수업이 몰리지 않고 고르게 퍼지게 합니다.")
    rule_1st = st.radio("🌅 1교시 공강 균등 배정", ["필수", "차순위", "미적용"], index=1)
    target_1st_free = st.slider("↪️ 1교시 공강 목표치 (주당)", min_value=0, max_value=5, value=2)

with col2:
    rule_4th = st.radio("🍱 4교시(점심) 공강 담임 그룹별 균등", ["필수", "차순위", "미적용"], index=1, help="점심시간 전인 4교시 공강을 담임들끼리 공평하게 나눕니다.")
    rule_pe = st.radio("🏃 운동장 체육 2학급 이하 제한", ["필수", "차순위", "미적용"], index=0)
    rule_art = st.radio("🎨 미술 블록타임 오전/오후 균등", ["필수", "차순위", "미적용"], index=1)


# ----------------------------------------
# 2. 교사별 특수 조건 입력 (무조건 필수 적용)
# ----------------------------------------
st.header("🚫 2. 교사별 필수/금지 조건 입력 (하드 제약)")
col3, col4 = st.columns(2)
with col3:
    default_banned = """김연지: 월, 금, 화5, 화6, 화7, 수5, 수6, 수7, 목5, 목6, 목7
이기영: 월1, 목1, 금5
김효진: 월1, 화1, 수1, 목1, 금1
김온유: 화6"""
    banned_text = st.text_area("❌ 특정 교시 금지 (이름: 요일교시, 요일교시...)", value=default_banned, height=120)

    default_grade_day = "이연경: 2-목, 3-화"
    grade_day_text = st.text_area("🚫 특정 학년-요일 금지 (예: 무용)", value=default_grade_day, height=68)

    default_special = "김연지, 임주헌"
    special_room_text = st.text_area("🏢 특별실 동시간대 금지 (2명 입력)", value=default_special, height=68)

with col4:
    default_mandatory = """이준희: 화1, 화2, 화3, 화4 >= 2
박주현: 월2, 월3 >= 1
박주현: 금2, 금3 >= 1"""
    mandatory_text = st.text_area("✅ 필수 배정 (이름: 요일교시... >= 횟수)", value=default_mandatory, height=120)

    default_pins = """3-1(화2): 김진호, 서정수 / 3-2(화2): 류지영, 제현진
3-4(화3): 황두환, 김영순 / 3-5(화3): 김승미 / 3-6(화3): 이아정
3-7(화4): 김재수, 김진호 / 3-8(화4): 류지영
1-1(수2): 김재수, 김영순 / 1-2(수2): 김영혜 / 1-3(수2): 이아정
1-4(수3): 김진호, 임주헌 / 1-5(수3): 김승미 / 1-6(수3): 류지영
1-7(수4): 서정수, 김영순 / 1-8(수4): 제현진
2-1(목2): 김재수, 임주헌 / 2-2(목2): 김승미 / 2-3(목2): 김영혜
2-4(목3): 김진호, 김영순 / 2-5(목3): 류지영 / 2-6(목3): 이아정
2-7(목4): 황두환, 김승미 / 2-8(목4): 제현진
지원(화1): 류명현 / 지원(화2): 류명현 / 지원(화3): 류명현 / 지원(화4): 류명현
지원(월2): 영어지원 / 지원(월3): 영어지원 / 지원(금2): 영어지원 / 지원(금3): 영어지원
지원(금1): 이기영 / 지원(금3): 이기영 / 지원(금4): 이기영"""
    pins_text = st.text_area("📌 스포츠 및 지원 강사 (하드 고정)", value=default_pins, height=160)


# ----------------------------------------
# 3. 명단 및 출력 설정
# ----------------------------------------
st.header("🧑‍🏫 3. 교사 명단 및 인쇄 설정")
st.info("해가 바뀌면 이 명단만 최신화하세요. 아래 적히지 않은 분들은 '비담임'으로 자동 분류됩니다.")

col5, col6 = st.columns(2)
with col5:
    hr1_text = st.text_input("1학년 담임", value="이아정, 김홍섭, 김나영, 김온유, 류지영, 박주현, 임희우, 최나경")
    hr2_text = st.text_input("2학년 담임", value="우가윤, 이상수, 배미래, 박은영, 오성환, 박은경, 오혜빈, 강수정")
    hr3_text = st.text_input("3학년 담임", value="우지연, 김명규, 오은정, 서예슬, 김영혜, 이정빈, 김승미, 허수정")
    bujang_text = st.text_input("부장 교사 명단 (금6 공강)", value="이기영, 김영순, 이준희, 박수경, 서정수, 김진호, 이연경, 임주헌, 전정화, 김나영, 배미래, 오은정")
    opt_bujang_free = st.checkbox("부장교사 금요일 6교시 공강 필수 적용", value=True)

with col6:
    block_text = st.text_input("블록타임(2연강) 강제 교사", value="김진호, 이정빈")
    support_text = st.text_input("지원 강사 (3연강 제한 완전 예외)", value="류명현, 체육지원, 영어지원")
    border_text = st.text_input("엑셀 과목 경계선 (아래에 굵은 선)", value="박은영, 김영혜, 김효진, 박수경, 제현진, 우가윤, 강영미, 김명규, 우지연, 이정빈, 임주헌")
    
sort_text = st.text_area("엑셀 출력 나열 순서 (콤마 구분)", value="김영순, 임희우, 김홍섭, 김승미, 오혜빈, 박은영, 강수정, 김영혜, 김나영, 황두환, 김효진, 정현미, 박수경, 서예슬, 박은경, 이상수, 김온유, 제현진, 김재수, 전정화, 최나경, 허수정, 우가윤, 오은정, 황현숙, 강영미, 이연경, 오성환, 이준희, 김명규, 류지영, 우지연, 김진호, 이정빈, 서정수, 이기영, 배미래, 박주현, 김미수, 이아정, 임주헌, 김연지, 체육지원, 영어지원, 류명현")


# ----------------------------------------
# 4. 실행 버튼
# ----------------------------------------
st.markdown("---")
st.header("🚀 4. 시수표 업로드 및 생성")
uploaded_excel = st.file_uploader("전체 시수 취합 엑셀 (.xlsx)", type=["xlsx"])

if uploaded_excel is not None:
    if st.button("✨ 시간표 생성 시작", use_container_width=True):
        with st.spinner("수백만 개의 경우의 수를 탐색 중입니다... (약 1~3분 소요)"):
            user_conditions = {
                "rule_3consec": rule_3consec, "rule_daily": rule_daily, "rule_1st": rule_1st,
                "rule_4th": rule_4th, "rule_pe": rule_pe, "rule_art": rule_art,
                "target_1st_free": target_1st_free,
                "banned_text": banned_text, "grade_day_text": grade_day_text, "special_room_text": special_room_text,
                "mandatory_text": mandatory_text, "pins_text": pins_text,
                "opt_bujang_free": opt_bujang_free,
                "hr1_text": hr1_text, "hr2_text": hr2_text, "hr3_text": hr3_text, "bujang_text": bujang_text,
                "block_text": block_text, "support_text": support_text,
                "sort_text": sort_text, "border_text": border_text
            }
            
            excel_buffer, status = run_timetable_engine(uploaded_excel, user_conditions)
            
            if status == "성공" and excel_buffer is not None:
                st.success("🎉 최적의 시간표가 완성되었습니다!")
                st.balloons()
                st.download_button(
                    label="📥 인쇄 최적화 엑셀 시간표 다운로드 (Ctrl+P A4 맞춤)",
                    data=excel_buffer,
                    file_name="최종시간표_스마트.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("⚠️ 조건 충돌: 해를 찾을 수 없습니다. 1번 설정에서 [필수] 규칙들을 [차순위]로 하나씩 완화해 보세요.")