import streamlit as st
from engine import run_timetable_engine

st.set_page_config(page_title="학교 시간표 생성기", layout="wide")

st.title("📅 스마트 시간표 자동 생성 시스템")
st.markdown("모든 조건은 아래 탭에서 선생님이 직접 수정하실 수 있습니다. 해가 바뀌어도 교사 이름만 바꾸어 계속 사용할 수 있습니다.")

# ----------------------------------------
# 1. 왼쪽 탭: 조건 설정 컨트롤 패널
# ----------------------------------------
tab1, tab2, tab3 = st.tabs(["🔴 1. 필수 제약 조건", "🟡 2. 차순위 (선택) 조건", "🟢 3. 명단 및 출력 설정"])

with tab1:
    st.info("이곳의 조건들은 타협할 수 없는 하드 제약으로 100% 반영됩니다. (형식에 맞춰 이름과 요일을 자유롭게 수정하세요)")
    
    col1, col2 = st.columns(2)
    with col1:
        default_banned = """김연지: 월, 금, 화5, 화6, 화7, 수5, 수6, 수7, 목5, 목6, 목7
이기영: 월1, 목1, 금5
김효진: 월1, 화1, 수1, 목1, 금1
김온유: 화6"""
        banned_text = st.text_area("❌ 특정 교시 금지 (형식: 이름: 요일교시, 요일교시...)", value=default_banned, height=130)

        default_grade_day = "이연경: 2-목, 3-화"
        grade_day_text = st.text_area("🚫 특정 학년-요일 금지 (예: 무용 등)", value=default_grade_day, height=68)

        default_special = "김연지, 임주헌"
        special_room_text = st.text_area("🏢 특별실 동시간대 금지 (2명 입력)", value=default_special, height=68)

    with col2:
        default_mandatory = """이준희: 화1, 화2, 화3, 화4 >= 2
박주현: 월2, 월3 >= 1
박주현: 금2, 금3 >= 1"""
        mandatory_text = st.text_area("✅ 필수 배정 (형식: 이름: 요일교시, 요일교시... >= 시간수)", value=default_mandatory, height=130)

        default_pins = """3-1(화2): 김진호, 서정수
3-2(화2): 류지영, 제현진
3-4(화3): 황두환, 김영순
3-5(화3): 김승미
3-6(화3): 이아정
3-7(화4): 김재수, 김진호
3-8(화4): 류지영
1-1(수2): 김재수, 김영순
1-2(수2): 김영혜
1-3(수2): 이아정
1-4(수3): 김진호, 임주헌
1-5(수3): 김승미
1-6(수3): 류지영
1-7(수4): 서정수, 김영순
1-8(수4): 제현진
2-1(목2): 김재수, 임주헌
2-2(목2): 김승미
2-3(목2): 김영혜
2-4(목3): 김진호, 김영순
2-5(목3): 류지영
2-6(목3): 이아정
2-7(목4): 황두환, 김승미
2-8(목4): 제현진
지원(화1): 류명현
지원(화2): 류명현
지원(화3): 류명현
지원(화4): 류명현
지원(월2): 영어지원
지원(월3): 영어지원
지원(금2): 영어지원
지원(금3): 영어지원
지원(금1): 이기영
지원(금3): 이기영
지원(금4): 이기영"""
        pins_text = st.text_area("📌 스포츠 및 지원 강사 (하드 고정)", value=default_pins, height=200)

with tab2:
    st.info("오류 발생 시 아래 체크박스를 하나씩 해제하여 조건을 완화해 보세요.")
    
    col3, col4 = st.columns(2)
    with col3:
        opt_consecutive = st.checkbox("🔥 정규교과 3연강 절대 금지 (해제 시 최대 3연강 허용)", value=True)
        max_consecutive = st.slider("기본 연속 수업 허용치", min_value=1, max_value=4, value=2) if opt_consecutive else 3
        
        opt_sports_limit = st.checkbox("🏃 운동장 체육 2학급 이하 제한", value=True)
        opt_bujang_free = st.checkbox("👑 부장교사 금요일 6교시 공강", value=True)
        opt_mandatory_check = st.checkbox("✅ 필수 배정(tab1) 조건 강제 적용", value=True)

    with col4:
        opt_1st_class = st.checkbox("🌅 1교시 공강 균등 배정", value=True)
        target_1st_free = st.slider("주당 1교시 공강 목표치", min_value=0, max_value=5, value=2) if opt_1st_class else 2
        
        opt_day_balance = st.checkbox("⚖️ 요일별 일일 평균 수업 시수 균등 배정", value=True)
        opt_hr_balance = st.checkbox("🧑‍🏫 담임/비담임 그룹별 3교시 공강 균등 배정", value=True)
        opt_block_balance = st.checkbox("🎨 블록타임(미술) 교사 오전/오후 균등 배정", value=True)

with tab3:
    st.info("해가 바뀌면 이 명단만 수정하시면 프로그램이 알아서 새로운 선생님들을 인식합니다.")
    
    default_hr1 = "이아정, 김홍섭, 김나영, 김온유, 류지영, 박주현, 임희우, 최나경"
    hr1_text = st.text_area("1학년 담임", value=default_hr1)
    
    default_hr2 = "우가윤, 이상수, 배미래, 박은영, 오성환, 박은경, 오혜빈, 강수정"
    hr2_text = st.text_area("2학년 담임", value=default_hr2)
    
    default_hr3 = "우지연, 김명규, 오은정, 서예슬, 김영혜, 이정빈, 김승미, 허수정"
    hr3_text = st.text_area("3학년 담임", value=default_hr3)
    
    default_bujang = "이기영, 김영순, 이준희, 박수경, 서정수, 김진호, 이연경, 임주헌, 전정화, 김나영, 배미래, 오은정"
    bujang_text = st.text_area("부장 교사 명단", value=default_bujang)

    default_block = "김진호, 이정빈"
    block_text = st.text_input("블록타임 (2시간 연강) 적용 교사", value=default_block)

    default_support = "류명현, 체육지원, 영어지원"
    support_text = st.text_input("지원 강사 (연강 제한 완전 예외)", value=default_support)

    st.markdown("---")
    default_sort = "김영순, 임희우, 김홍섭, 김승미, 오혜빈, 박은영, 강수정, 김영혜, 김나영, 황두환, 김효진, 정현미, 박수경, 서예슬, 박은경, 이상수, 김온유, 제현진, 김재수, 전정화, 최나경, 허수정, 우가윤, 오은정, 황현숙, 강영미, 이연경, 오성환, 이준희, 김명규, 류지영, 우지연, 김진호, 이정빈, 서정수, 이기영, 배미래, 박주현, 김미수, 이아정, 임주헌, 김연지, 체육지원, 영어지원, 류명현"
    sort_text = st.text_area("엑셀 출력 나열 순서 (콤마 구분)", value=default_sort)

    default_border = "박은영, 김영혜, 김효진, 박수경, 제현진, 우가윤, 강영미, 김명규, 우지연, 이정빈, 임주헌"
    border_text = st.text_input("굵은 밑줄(과목 경계) 기준 교사 (해당 교사 아래에 줄이 그어짐)", value=default_border)


# ----------------------------------------
# 2. 메인 화면: 파일 업로드 및 실행
# ----------------------------------------
st.header("📂 시수표 업로드 및 실행")
uploaded_excel = st.file_uploader("전체 시수 취합 엑셀 (.xlsx)", type=["xlsx"])

if uploaded_excel is not None:
    st.success("✅ 파일 업로드 완료!")
    
    if st.button("🚀 시간표 생성 시작", use_container_width=True):
        with st.spinner("AI가 수백만 개의 경우의 수를 탐색 중입니다. 진행률 표기는 불가하나 열심히 계산하고 있습니다! (약 1~3분 소요)"):
            
            # 모든 텍스트 조건을 하나의 딕셔너리로 패킹하여 엔진으로 전달
            user_conditions = {
                "banned_text": banned_text, "grade_day_text": grade_day_text, "special_room_text": special_room_text,
                "mandatory_text": mandatory_text, "pins_text": pins_text,
                "opt_consecutive": opt_consecutive, "max_consecutive": max_consecutive,
                "opt_sports_limit": opt_sports_limit, "opt_bujang_free": opt_bujang_free, "opt_mandatory_check": opt_mandatory_check,
                "opt_1st_class": opt_1st_class, "target_1st_free": target_1st_free,
                "opt_day_balance": opt_day_balance, "opt_hr_balance": opt_hr_balance, "opt_block_balance": opt_block_balance,
                "hr1_text": hr1_text, "hr2_text": hr2_text, "hr3_text": hr3_text, "bujang_text": bujang_text,
                "block_text": block_text, "support_text": support_text,
                "sort_text": sort_text, "border_text": border_text
            }
            
            excel_buffer, status = run_timetable_engine(uploaded_excel, user_conditions)
            
            if status == "성공" and excel_buffer is not None:
                st.success("🎉 모든 조건을 만족하는 미배정 0 시간표가 완성되었습니다!")
                st.info("🖨️ 다운로드 후 엑셀에서 인쇄(Ctrl+P)를 누르시면 A4 가로 한 장에 꽉 차게 맞춰져 나옵니다.")
                st.balloons()
                st.download_button(
                    label="📥 인쇄 최적화 엑셀 시간표 다운로드",
                    data=excel_buffer,
                    file_name="최종시간표_초안.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("⚠️ 조건 충돌: 현재 조합으로는 해를 찾을 수 없습니다. [차순위 (선택) 조건] 탭에서 체크박스를 끄거나, [필수 제약 조건]의 시간을 수정하여 조건을 완화해 보세요.")