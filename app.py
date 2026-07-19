import streamlit as st
from engine import run_timetable_engine

st.set_page_config(page_title="학교 시간표 생성기", layout="wide")

st.title("스마트 시간표 자동 생성 시스템")
st.markdown("모든 조건을 껐다 켰다 할 수 있습니다. 깐깐한 조건부터 점차 완화해가며 최적의 시간표를 뽑아보세요.")

if "custom_rules" not in st.session_state:
    st.session_state.custom_rules = []

tab1, tab2 = st.tabs(["1. 조건 및 규칙 설정 (메인)", "2. 교사 명단 및 인쇄 설정"])

with tab1:
    st.header("1. 우선순위 자동 배정 규칙 (클릭하여 이동)")
    st.info("팁: 아래 칸에 직접 글씨를 쓰고 [엔터]를 치면 새 항목이 추가됩니다. 항목의 'X'를 누르면 빠지고, 빈칸을 눌러 다시 넣을 수 있습니다.")
    
    new_rule = st.text_input("➕ 여기에 새로운 규칙을 입력하고 [엔터]를 누르세요.")
    if new_rule and new_rule not in st.session_state.custom_rules:
        st.session_state.custom_rules.append(new_rule)
    
    base_rules = [
        "교과 3연강 절대 금지", "운동장 체육 2학급 이하 제한", 
        "1일 수업 시수 균등 배정", "1교시 공강 균등 배정", 
        "4교시(점심) 공강 담임별 균등", "미술 블록 오전/오후 균등"
    ]
    all_rules = base_rules + st.session_state.custom_rules
    
    hard_rules = st.multiselect("필수 조건 (하드 제약 - 1순위. 예외 없음)", all_rules, default=["교과 3연강 절대 금지", "운동장 체육 2학급 이하 제한"] + st.session_state.custom_rules)
    
    rem_rules = [r for r in all_rules if r not in hard_rules]
    soft_rules = st.multiselect("차순위 조건 (소프트 제약 - 2순위. 최대한 지킴)", rem_rules, default=rem_rules)
    
    target_1st_free = st.slider("[참고] 1교시 공강 목표 횟수 (주당)", min_value=0, max_value=5, value=2)

    st.markdown("---")
    st.header("2. 교사별 세부 조건 (자유 추가 및 삭제)")
    st.info("여기에 텍스트로 적힌 조건들은 '최우선 하드 제약'으로 작동합니다. 항목을 직접 지우거나 새롭게 타이핑하여 추가하실 수 있습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        default_banned = """김연지: 월, 금, 화5, 화6, 화7, 수5, 수6, 수7, 목5, 목6, 목7
이기영: 월1, 목1, 금2, 금5, 금6
김효진: 월1, 화1, 수1, 목1, 금1
김온유: 화6"""
        banned_text = st.text_area("특정 교시 금지 (이름: 요일교시...)", value=default_banned, height=130)

        default_grade_day = "이연경: 2-목, 3-화"
        grade_day_text = st.text_area("특정 학년-요일 금지 (무용 등)", value=default_grade_day, height=68)

        default_special = "김연지, 임주헌"
        special_room_text = st.text_area("특별실 동시간대 금지 (2명)", value=default_special, height=68)

    with col2:
        default_mandatory = """이준희: 화1, 화2, 화3, 화4 >= 2
박주현: 월2, 월3 >= 1
박주현: 금2, 금3 >= 1"""
        mandatory_text = st.text_area("필수 배정 (이름: 요일교시... >= 횟수)", value=default_mandatory, height=130)

        default_pins = """3-1(화2): 김진호, 서정수 / 3-2(화2): 류지영, 제현진
3-4(화3): 황두환, 김영순 / 3-5(화3): 김승미 / 3-6(화3): 이아정
3-7(화4): 김재수, 김진호 / 3-8(화4): 류지영
1-1(수2): 김재수, 김영순 / 1-2(수2): 김영혜 / 1-3(수2): 이아정
1-4(수3): 김진호, 임주헌 / 1-5(수3): 김승미 / 1-6(수3): 류지영
1-7(수4): 서정수, 김영순 / 1-8(수4): 제현진
2-1(목2): 김재수, 임주헌 / 2-2(목2): 김승미 / 2-3(목2): 김영혜
2-4(목3): 김진호, 김영순 / 2-5(목3): 류지영 / 2-6(목3): 이아정
2-7(목4): 황두환, 김승미 / 2-8(목4): 제현진
지원(화1): 체육지원 / 지원(화2): 체육지원 / 지원(화3): 체육지원 / 지원(화4): 체육지원
지원(월2): 영어지원 / 지원(월3): 영어지원 / 지원(금2): 영어지원 / 지원(금3): 영어지원"""
        pins_text = st.text_area("고정 리스트 (압핀)", value=default_pins, height=160)

with tab2:
    st.header("명단 및 출력 설정")
    st.info("해가 바뀌면 이 명단만 최신화하세요. 아래 명단에 없는 선생님은 '비담임'으로 자동 적용됩니다.")
    
    col3, col4 = st.columns(2)
    with col3:
        hr1_text = st.text_area("1학년 담임", value="이아정, 김홍섭, 김나영, 김온유, 류지영, 박주현, 임희우, 최나경", height=68)
        hr2_text = st.text_area("2학년 담임", value="우가윤, 이상수, 배미래, 박은영, 오성환, 박은경, 오혜빈, 강수정", height=68)
        hr3_text = st.text_area("3학년 담임", value="우지연, 김명규, 오은정, 서예슬, 김영혜, 이정빈, 김승미, 허수정", height=68)
        bujang_text = st.text_area("부장 교사 (금6 공강)", value="이기영, 김영순, 이준희, 박수경, 서정수, 김진호, 이연경, 임주헌, 전정화, 김나영, 배미래, 오은정", height=68)
        opt_bujang_free = st.checkbox("부장교사 금요일 6교시 공강 강제 적용", value=True)

    with col4:
        block_text = st.text_area("블록타임(2연강) 강제 교사", value="김진호, 이정빈", height=68)
        support_text = st.text_area("지원 강사 (3연강 예외 교사)", value="체육지원, 영어지원", height=68)
        sort_text = st.text_area("엑셀 출력 나열 순서", value="김영순, 임희우, 김홍섭, 김승미, 오혜빈, 박은영, 강수정, 김영혜, 김나영, 황두환, 김효진, 정현미, 박수경, 서예슬, 박은경, 이상수, 김온유, 제현진, 김재수, 전정화, 최나경, 허수정, 우가윤, 오은정, 황현숙, 강영미, 이연경, 오성환, 이준희, 김명규, 류지영, 우지연, 김진호, 이정빈, 서정수, 이기영, 배미래, 박주현, 김미수, 이아정, 임주헌, 김연지, 체육지원, 영어지원", height=100)
        border_text = st.text_area("굵은 밑줄(과목 경계선) 교사", value="박은영, 김영혜, 김효진, 박수경, 제현진, 우가윤, 강영미, 김명규, 우지연, 이정빈, 임주헌", height=68)

st.markdown("---")
st.header("실행 결과")
uploaded_excel = st.file_uploader("전체 시수 취합 엑셀 (.xlsx)", type=["xlsx"])

if uploaded_excel is not None:
    if st.button("시간표 생성 시작", use_container_width=True):
        with st.spinner("AI가 수백만 개의 경우의 수를 탐색 중입니다. (진행률 표기는 어렵지만 1~3분 내로 완료됩니다)"):
            
            user_conditions = {
                "hard_rules": hard_rules, "soft_rules": soft_rules,
                "target_1st_free": target_1st_free,
                "banned_text": banned_text, "grade_day_text": grade_day_text, "special_room_text": special_room_text,
                "mandatory_text": mandatory_text, "pins_text": pins_text,
                "opt_bujang_free": opt_bujang_free,
                "hr1_text": hr1_text, "hr2_text": hr2_text, "hr3_text": hr3_text, "bujang_text": bujang_text,
                "block_text": block_text, "support_text": support_text,
                "sort_text": sort_text, "border_text": border_text
            }
            
            excel_buffer, status, feedback = run_timetable_engine(uploaded_excel, user_conditions)
            
            if status == "성공" and excel_buffer is not None:
                st.success("모든 조건을 만족하는 미배정 0 시간표가 완성되었습니다!")
                st.info("다운로드 후 엑셀에서 인쇄(Ctrl+P)를 누르시면 A4 한 장에 꽉 차게 맞춰집니다.")
                st.balloons()
                st.download_button(
                    label="인쇄 최적화 엑셀 시간표 다운로드",
                    data=excel_buffer,
                    file_name="최종시간표_스마트.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("조건 충돌: 현재 조건들이 너무 빡빡하여 해를 찾지 못했습니다.")
                st.warning(feedback)