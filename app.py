import streamlit as st
from engine import run_timetable_engine

st.set_page_config(page_title="학교 시간표 생성기", layout="wide")

st.title("📅 2026학년도 2학기 시간표 자동 생성 시스템")
st.markdown("선생님들의 시수표를 업로드하면 최적화된 교사별 시간표 엑셀을 즉시 생성합니다. (3연강 금지, 고정 시간표 완벽 반영)")

# 파일 업로드 UI
st.sidebar.header("1. 데이터 업로드")
uploaded_excel = st.sidebar.file_uploader("전체 시수 취합 엑셀 (.xlsx)", type=["xlsx"])

if uploaded_excel is not None:
    st.success("✅ 파일 업로드 완료! '시간표 생성' 버튼을 눌러주세요.")
    
    if st.button("🚀 시간표 생성 (약 1~3분 소요)", use_container_width=True):
        with st.spinner("최적의 시간표를 계산 중입니다. 잠시만 기다려주세요..."):
            
            # engine.py의 로직 실행
            excel_buffer, status = run_timetable_engine(uploaded_excel)
            
            if status == "성공" and excel_buffer is not None:
                st.success("🎉 시간표 생성이 완료되었습니다!")
                st.balloons()
                
                # 엑셀 다운로드 버튼
                st.download_button(
                    label="📥 완성된 시간표 엑셀 다운로드",
                    data=excel_buffer,
                    file_name="2026-2학기_교사별시간표_최종.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("⚠️ 조건이 너무 까다로워 해를 찾지 못했습니다. 제약 조건을 완화해 주세요.")
else:
    st.info("👈 왼쪽 사이드바에서 시수표 엑셀 파일을 업로드해 주세요.")