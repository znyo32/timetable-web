import io
import pandas as pd
from collections import defaultdict
import openpyxl
from openpyxl.styles import Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter
from ortools.sat.python import cp_model

def run_timetable_engine(uploaded_file, user_conditions):
    xls = pd.ExcelFile(uploaded_file)
    target_sheet = xls.sheet_names[0]
    for sheet in xls.sheet_names:
        if '국어' in str(sheet).replace(" ", ""):
            target_sheet = sheet
            break
            
    df_kor = pd.read_excel(xls, sheet_name=target_sheet, header=None)

    common_classes = []
    seen = set()
    for i in range(4, len(df_kor)):
        subj = df_kor.iloc[i, 0]
        teacher = df_kor.iloc[i, 1]
        if pd.notna(teacher) and str(teacher).strip() not in ['담당교사', '담당', '교사', 'nan', '']:
            t_name = str(teacher).strip()
            subj_name = str(subj).strip()
            for c_idx in range(2, 26):
                val = df_kor.iloc[i, c_idx]
                try:
                    if pd.notna(val) and float(val) > 0:
                        if 2 <= c_idx <= 9: g, b = 1, c_idx - 1
                        elif 10 <= c_idx <= 17: g, b = 2, c_idx - 9
                        elif 18 <= c_idx <= 25: g, b = 3, c_idx - 17
                        key = (t_name, subj_name, g, b)
                        if key not in seen:
                            seen.add(key)
                            common_classes.append({
                                "teacher": t_name, "subj": subj_name,
                                "grade": g, "cls": b, "hours": int(float(val))
                            })
                except: pass

    teachers = sorted(list(set(c["teacher"] for c in common_classes)))
    classes = sorted(list(set((c["grade"], c["cls"]) for c in common_classes)))

    teacher_hours = defaultdict(int)
    for c in common_classes: teacher_hours[c["teacher"]] += c["hours"]

    GRID = {"월":7, "화":6, "수":6, "목":7, "금":6}
    DAYS = list(GRID.keys())
    slots = [(d, p) for d in DAYS for p in range(1, GRID[d] + 1)]
    S = len(slots); sidx = {s: i for i, s in enumerate(slots)}

    def match_slots(day=None, days=None, period=None, periods=None):
        out = []
        for i, (d, p) in enumerate(slots):
            if day and d != day: continue
            if days and d not in days: continue
            if period and p != period: continue
            if periods and p not in periods: continue
            out.append(i)
        return out

    # ==== 1. 기본 금지 조건 ====
    reserved = set()
    for i in match_slots(day="월", period=7):
        for g, b in classes: reserved.add((g, b, i)) 

    ban = defaultdict(set)
    for i in match_slots(days=["월", "금"]): ban["김연지"].add(i)
    for i in match_slots(days=["화", "수", "목"], periods=[5,6,7]): ban["김연지"].add(i)
    for i in match_slots(day="월", period=1): ban["이기영"].add(i)
    for i in match_slots(day="목", period=1): ban["이기영"].add(i)
    for i in match_slots(day="금", period=5): ban["이기영"].add(i)
    for i in match_slots(period=1): ban["김효진"].add(i)
    for i in match_slots(day="화", period=6): ban["김온유"].add(i)

    bujang = ["이기영","김영순","이준희","박수경","서정수","김진호","이연경","임주헌","전정화","김나영","배미래","오은정"]
    for i in match_slots(day="금", period=6):
        for t in bujang: ban[t].add(i)

    # ==== 2. 스포츠 및 지원강사 압핀 고정 ====
    fixed_slots = []
    sports_pins = {
        ("화", 2): [("김진호", (3,1)), ("서정수", (3,1)), ("류지영", (3,2)), ("제현진", (3,3))],
        ("화", 3): [("황두환", (3,4)), ("김영순", (3,4)), ("김승미", (3,5)), ("이아정", (3,6))],
        ("화", 4): [("김재수", (3,7)), ("김진호", (3,7)), ("류지영", (3,8))],
        ("수", 2): [("김재수", (1,1)), ("김영순", (1,1)), ("김영혜", (1,2)), ("이아정", (1,3))],
        ("수", 3): [("김진호", (1,4)), ("임주헌", (1,4)), ("김승미", (1,5)), ("류지영", (1,6))],
        ("수", 4): [("서정수", (1,7)), ("김영순", (1,7)), ("제현진", (1,8))],
        ("목", 2): [("김재수", (2,1)), ("임주헌", (2,1)), ("김승미", (2,2)), ("김영혜", (2,3))],
        ("목", 3): [("김진호", (2,4)), ("김영순", (2,4)), ("류지영", (2,5)), ("이아정", (2,6))],
        ("목", 4): [("황두환", (2,7)), ("김승미", (2,7)), ("제현진", (2,8))]
    }
    sports_slot_indices = set()
    for (d, p), mappings in sports_pins.items():
        slot_idx = sidx[(d, p)]
        sports_slot_indices.add(slot_idx)
        for t_name, cls_tuple in mappings:
            ban[t_name].add(slot_idx)
            fixed_slots.append({"teacher": t_name, "cls": cls_tuple, "slot": slot_idx, "subj": "스포츠"})

    for d, p in [("화", 1), ("화", 2), ("화", 3), ("화", 4)]:
        slot_idx = sidx[(d, p)]
        ban["류명현"].add(slot_idx)
        fixed_slots.append({"teacher": "류명현", "cls": None, "slot": slot_idx, "subj": "지원"})
    for d, p in [("월", 2), ("월", 3), ("금", 2), ("금", 3)]:
        slot_idx = sidx[(d, p)]
        ban["영어지원"].add(slot_idx)
        fixed_slots.append({"teacher": "영어지원", "cls": None, "slot": slot_idx, "subj": "지원"})
    for d, p in [("금", 1), ("금", 3), ("금", 4)]:
        slot_idx = sidx[(d, p)]
        ban["이기영"].add(slot_idx)
        fixed_slots.append({"teacher": "이기영", "cls": None, "slot": slot_idx, "subj": "지원"})

    m = cp_model.CpModel()
    xc = {(ci, i): m.NewBoolVar(f"c{ci}_{i}") for ci in range(len(common_classes)) for i in range(S)}
    tocc = {}
    
    for t in teachers:
        cidx = [ci for ci, u in enumerate(common_classes) if u["teacher"] == t]
        for i in range(S):
            o = m.NewBoolVar("")
            m.Add(o == sum(xc[(ci, i)] for ci in cidx))
            tocc[(t, i)] = o
        for i in range(S): m.Add(tocc[(t, i)] <= 1)

    # ==== 3. 특별실 공유 (김연지-임주헌 엇갈리게 배정) ====
    if "김연지" in teachers and "임주헌" in teachers:
        for i in range(S):
            m.Add(tocc[("김연지", i)] + tocc[("임주헌", i)] <= 1)

    for ci, u in enumerate(common_classes):
        g, b = u["grade"], u["cls"]; t = u["teacher"]
        m.Add(sum(xc[(ci, i)] for i in range(S)) == u["hours"])
        for i in range(S):
            if (g, b, i) in reserved or i in ban[t]:
                m.Add(xc[(ci, i)] == 0)

    for g, b in classes:
        cidx = [ci for ci, u in enumerate(common_classes) if u["grade"] == g and u["cls"] == b]
        for i in range(S):
            sports_in_class_slot = any(f["cls"] == (g, b) and f["slot"] == i for f in fixed_slots)
            if sports_in_class_slot:
                m.Add(sum(xc[(ci, i)] for ci in cidx) == 0)
            else:
                m.Add(sum(xc[(ci, i)] for ci in cidx) <= 1)

    byc = defaultdict(list)
    for ci, u in enumerate(common_classes): byc[((u["grade"], u["cls"]), u["teacher"])].append(ci)
    for (cls, t), idxs in byc.items():
        if len(idxs) >= 2:
            for d in DAYS:
                m.Add(sum(xc[(ci, i)] for ci in idxs for i in match_slots(day=d)) <= 1)

    # ==== 4. 무용 및 체육 제약 ====
    for ci, u in enumerate(common_classes):
        if u["teacher"] == "이연경":
            if u["grade"] == 3:
                for i in match_slots(day="화"): m.Add(xc[(ci, i)] == 0)
            elif u["grade"] == 2:
                for i in match_slots(day="목"): m.Add(xc[(ci, i)] == 0)

    if user_conditions.get("apply_sports_rule", True):
        for i in sports_slot_indices:
            pe_in_slot = []
            for ci, u in enumerate(common_classes):
                if "체육" in u["subj"] and "지원" not in u["subj"]:
                    pe_in_slot.append(xc[(ci, i)])
            m.Add(sum(pe_in_slot) <= 2)

    # 3학년 미술 블록타임 및 일반과목 분산
    for ci, u in enumerate(common_classes):
        is_art_block = (u["subj"] == "미술" and u["grade"] == 3 and u["teacher"] in ["김진호", "이정빈"])
        if is_art_block and u["hours"] == 2:
            block_vars = []
            for d in DAYS:
                for p in range(1, GRID[d]):
                    if p == 4: continue
                    b_var = m.NewBoolVar(f"block_{ci}_{d}_{p}")
                    block_vars.append((b_var, sidx[(d, p)], sidx[(d, p+1)]))
            m.AddExactlyOne([bv[0] for bv in block_vars])
            for i in range(S):
                m.Add(xc[(ci, i)] == sum(bv[0] for bv in block_vars if bv[1] == i or bv[2] == i))
        else:
            if u["hours"] <= 5:
                for d in DAYS:
                    m.Add(sum(xc[(ci, i)] for i in match_slots(day=d)) <= 1)

    # ==== 5. 필수 배정 조건 ====
    pjh = [ci for ci, u in enumerate(common_classes) if u["teacher"] == "박주현"]
    if pjh:
        m.Add(sum(xc[(ci, i)] for ci in pjh for i in match_slots(day="월", periods=[2,3])) >= 1)
        m.Add(sum(xc[(ci, i)] for ci in pjh for i in match_slots(day="금", periods=[2,3])) >= 1)

    ljh = [ci for ci, u in enumerate(common_classes) if u["teacher"] == "이준희"]
    if ljh: m.Add(sum(xc[(ci, i)] for ci in ljh for i in match_slots(day="화", periods=[1,2,3,4])) >= 2)

    # ==== 6. 3연강 절대 금지 (지원강사 제외 모두 엄수) ====
    user_max_c = user_conditions.get("max_consecutive", 2)
    for t in teachers:
        if t in ["류명현", "체육지원", "영어지원"]: 
            continue # 고정표 상 연속 배정된 지원강사만 예외
        for d in DAYS:
            for p in range(1, GRID[d] + 1):
                if all((d, p + k) in sidx for k in range(user_max_c + 1)):
                    slot_vars = []
                    for k in range(user_max_c + 1):
                        s_idx = sidx[(d, p + k)]
                        is_fixed = any(f["teacher"] == t and f["slot"] == s_idx for f in fixed_slots)
                        slot_vars.append(1 if is_fixed else tocc[(t, s_idx)])
                    m.Add(sum(slot_vars) <= user_max_c)

    # ==== 7. 균등 배정 로직 (Soft Constraint) ====
    pen = []
    target_1st_free = user_conditions.get("target_1st_free", 2)
    target_1st_work = 5 - target_1st_free
    for t in teachers:
        s_1 = sum(tocc[(t, i)] for i in match_slots(period=1))
        fixed_p1 = sum(1 for f in fixed_slots if f["teacher"] == t and slots[f["slot"]][1] == 1)
        diff = m.NewIntVar(-5, 5, "")
        m.Add(diff == (s_1 + fixed_p1) - target_1st_work)
        abs_diff = m.NewIntVar(0, 5, "")
        m.AddAbsEquality(abs_diff, diff)
        pen.append((2, abs_diff))

    for t in teachers:
        day_sums = []
        for d in DAYS:
            s_d = sum(tocc[(t, i)] for i in match_slots(day=d))
            fixed_d = sum(1 for f in fixed_slots if f["teacher"] == t and slots[f["slot"]][0] == d)
            day_sums.append(s_d + fixed_d)
        d_max = m.NewIntVar(0, 7, ""); d_min = m.NewIntVar(0, 7, "")
        m.AddMaxEquality(d_max, day_sums); m.AddMinEquality(d_min, day_sums)
        pen.append((10, d_max - d_min))

    hr_1 = ["이아정","김홍섭","김나영","김온유","류지영","박주현","임희우","최나경"]
    hr_2 = ["우가윤","이상수","배미래","박은영","오성환","박은경","오혜빈","강수정"]
    hr_3 = ["우지연","김명규","오은정","서예슬","김영혜","이정빈","김승미","허수정"]
    hr_all = set(hr_1 + hr_2 + hr_3)
    hr_others = [t for t in teachers if t not in hr_all]

    def balance_group(group_teachers, weight):
        valid_t = [t for t in group_teachers if t in teachers]
        if not valid_t: return
        p3_sums = []
        for t in valid_t:
            s_3 = sum(tocc[(t, i)] for i in match_slots(period=3))
            fixed_p3 = sum(1 for f in fixed_slots if f["teacher"] == t and slots[f["slot"]][1] == 3)
            p3_sums.append(s_3 + fixed_p3)
        g_max = m.NewIntVar(0, 5, ""); g_min = m.NewIntVar(0, 5, "")
        m.AddMaxEquality(g_max, p3_sums); m.AddMinEquality(g_min, p3_sums)
        pen.append((weight, g_max - g_min))

    balance_group(hr_1, 5); balance_group(hr_2, 5); balance_group(hr_3, 5); balance_group(hr_others, 2)

    for t in ["김진호", "이정빈"]:
        cidx_3 = [ci for ci, u in enumerate(common_classes) if u["teacher"] == t and u["subj"] == "미술" and u["grade"] == 3]
        if cidx_3:
            am = sum(xc[(ci, i)] for ci in cidx_3 for i in match_slots(periods=[1,2,3,4]))
            pm = sum(xc[(ci, i)] for ci in cidx_3 for i in match_slots(periods=[5,6,7]))
            diff = m.NewIntVar(-10, 10, "")
            m.Add(diff == am - pm)
            abs_diff = m.NewIntVar(0, 10, "")
            m.AddAbsEquality(abs_diff, diff)
            pen.append((20, abs_diff))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180
    solver.parameters.num_search_workers = 8
    m.Minimize(sum(w * v for w, v in pen))
    st = solver.Solve(m)

    # ==== 8. 교사 순서 정렬 및 굵은 테두리 엑셀 인쇄 설정 ====
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out = {}
        for f in fixed_slots:
            t_name = f["teacher"]
            if t_name not in out: out[t_name] = []
            cls_str = f"{f['cls'][0]}-{f['cls'][1]}" if f["cls"] else ""
            out[t_name].append({"subj": f["subj"], "cls": cls_str, "slot": f["slot"]})
            if t_name not in teachers: teachers.append(t_name)
        
        for ci, u in enumerate(common_classes):
            for i in range(S):
                if solver.Value(xc[(ci, i)]):
                    t_name = u["teacher"]
                    if t_name not in out: out[t_name] = []
                    out[t_name].append({"subj": u["subj"], "cls": f"{u['grade']}-{u['cls']}", "slot": i})
        
        # 선생님이 요청하신 과목별 나열 순서
        custom_order = [
            "김영순", "임희우", "김홍섭", "김승미", "오혜빈", "박은영", # 국어
            "강수정", "김영혜", "김나영", # 역사, 사회
            "황두환", "김효진", "정현미", "박수경", # 사회, 도덕
            "서예슬", "박은경", "이상수", "김온유", "제현진", # 수학
            "김재수", "전정화", "최나경", "허수정", "우가윤", # 과학
            "오은정", "황현숙", "강영미", # 기가, 정보
            "이연경", "오성환", "이준희", "김명규", # 체육
            "류지영", "우지연", # 음악
            "김진호", "이정빈", # 미술
            "서정수", "이기영", "배미래", "박주현", "김미수", # 영어
            "이아정", "임주헌", "김연지", "체육지원", "영어지원", "류명현"
        ]
        # 과목 경계선 (굵은 밑줄 그을 선생님)
        group_ends = ["박은영", "김영혜", "김효진", "박수경", "제현진", "우가윤", "강영미", "김명규", "우지연", "이정빈"]
        
        sorted_teachers = sorted(out.keys(), key=lambda x: custom_order.index(x) if x in custom_order else 999)
                    
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "교사별 시간표"
        days_periods = [("월", 7), ("화", 6), ("수", 6), ("목", 7), ("금", 6)]

        # 프린트(인쇄) 최적화 설정 추가
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.print_options.horizontalCentered = True

        font_title1 = Font(name="바탕체", size=14, bold=True)
        font_title2 = Font(name="바탕체", size=11, bold=True)
        font_base = Font(name="바탕체", size=8)
        font_bold = Font(name="바탕체", size=9, bold=True)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        thin = Side(style="thin", color="000000")
        thick = Side(style="medium", color="000000") # 굵은 테두리
        bd_normal = Border(left=thin, right=thin, top=thin, bottom=thin)
        bd_thick_bottom = Border(left=thin, right=thin, top=thin, bottom=thick)

        ws.cell(1, 1, "2026-2학기 전체교사 시간표 초안").font = font_title1
        ws.cell(2, 1, "교사별 시간표").font = font_title2

        ws.cell(3, 1, "교사").font = font_bold
        ws.cell(3, 1).alignment = center; ws.cell(3, 1).border = bd_normal; ws.cell(4, 1, "").border = bd_normal
        ws.merge_cells("A3:A4")

        col = 2
        for day, periods in days_periods:
            ws.cell(3, col, day).font = font_bold
            ws.cell(3, col).alignment = center; ws.cell(3, col).border = bd_normal
            ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col+periods-1)
            for p in range(1, periods + 1):
                c = ws.cell(4, col, str(p))
                c.font = font_bold; c.alignment = center; c.border = bd_normal
                ws.cell(3, col).border = bd_normal
                col += 1

        ws.cell(3, col, "교사").font = font_bold
        ws.cell(3, col).alignment = center; ws.cell(3, col).border = bd_normal; ws.cell(4, col, "").border = bd_normal
        ws.merge_cells(start_row=3, start_column=col, end_row=4, end_column=col)

        ws.cell(3, col+1, "계").font = font_bold
        ws.cell(3, col+1).alignment = center; ws.cell(3, col+1).border = bd_normal; ws.cell(4, col+1, "").border = bd_normal
        ws.merge_cells(start_row=3, start_column=col+1, end_row=4, end_column=col+1)
        total_cols = col + 1

        r = 5
        for t_name in sorted_teachers:
            items = out[t_name]
            slot_map = {item["slot"]: item for item in items}
            
            is_group_end = t_name in group_ends
            bottom_bd = bd_thick_bottom if is_group_end else bd_normal
            
            ws.cell(r, 1, t_name).font = font_base
            ws.cell(r, 1).alignment = center; ws.cell(r, 1).border = bd_normal; ws.cell(r+1, 1).border = bottom_bd
            ws.merge_cells(start_row=r, start_column=1, end_row=r+1, end_column=1)
            
            col = 2
            count = 0
            for i in range(sum([p for _, p in days_periods])):
                if i in slot_map:
                    cls_str = slot_map[i]["cls"]
                    subj_str = slot_map[i]["subj"]
                    count += 1
                else:
                    cls_str = ""
                    subj_str = ""
                    
                c1 = ws.cell(r, col, cls_str); c2 = ws.cell(r+1, col, subj_str)
                c1.font = font_base; c1.alignment = center; c1.border = bd_normal
                c2.font = font_base; c2.alignment = center; c2.border = bottom_bd
                col += 1
                
            ws.cell(r, col, t_name).font = font_base
            ws.cell(r, col).alignment = center; ws.cell(r, col).border = bd_normal; ws.cell(r+1, col).border = bottom_bd
            ws.merge_cells(start_row=r, start_column=col, end_row=r+1, end_column=col)
            
            ws.cell(r, col+1, count).font = font_base
            ws.cell(r, col+1).alignment = center; ws.cell(r, col+1).border = bd_normal; ws.cell(r+1, col+1).border = bottom_bd
            ws.merge_cells(start_row=r, start_column=col+1, end_row=r+1, end_column=col+1)
            r += 2

        ws.column_dimensions["A"].width = 5.0
        for i in range(2, total_cols - 1):
            ws.column_dimensions[get_column_letter(i)].width = 3.6
        ws.column_dimensions[get_column_letter(total_cols-1)].width = 5.0
        ws.column_dimensions[get_column_letter(total_cols)].width = 5.0

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output, "성공"
    else:
        return None, "실패"