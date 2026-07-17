import io
import pandas as pd
from collections import defaultdict
import openpyxl
from openpyxl.styles import Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter
from ortools.sat.python import cp_model

def parse_slots(s_str):
    s_str = s_str.strip()
    if len(s_str) == 1 and s_str in ["월", "화", "수", "목", "금"]:
        return [(s_str, p) for p in range(1, 8)]
    elif len(s_str) >= 2:
        return [(s_str[0], int(s_str[1:]))]
    return []

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

    GRID = {"월":7, "화":6, "수":6, "목":7, "금":6}
    DAYS = list(GRID.keys())
    slots = [(d, p) for d in DAYS for p in range(1, GRID[d] + 1)]
    S = len(slots); sidx = {s: i for i, s in enumerate(slots)}

    ban = defaultdict(set)
    reserved = set()
    for i in [sidx[(d, p)] for d, p in slots if d=="월" and p==7]:
        for g, b in classes: reserved.add((g, b, i)) 

    # 1. 자유 추가 텍스트 파싱
    for line in user_conditions.get("banned_text", "").split("\n"):
        if ":" in line:
            t, slots_part = line.split(":", 1)
            t = t.strip()
            for s in slots_part.split(","):
                for d, p in parse_slots(s):
                    if (d, p) in sidx: ban[t].add(sidx[(d, p)])

    if user_conditions.get("opt_bujang_free", True):
        bujang = [x.strip() for x in user_conditions.get("bujang_text", "").split(",") if x.strip()]
        for t in bujang:
            if ("금", 6) in sidx: ban[t].add(sidx[("금", 6)])

    fixed_slots = []
    sports_slot_indices = set()
    for line in user_conditions.get("pins_text", "").split("\n"):
        line = line.strip()
        if not line or line.startswith("["): continue
        for part in line.split("/"):
            part = part.strip()
            if "(" in part and "):" in part:
                cls_part, rest = part.split("(", 1)
                slot_part, teachers_part = rest.split("):", 1)
                cls_part, slot_part = cls_part.strip(), slot_part.strip()
                if len(slot_part) >= 2 and (slot_part[0], int(slot_part[1:])) in sidx:
                    slot_i = sidx[(slot_part[0], int(slot_part[1:]))]
                    if "-" in cls_part:
                        sports_slot_indices.add(slot_i)
                        g, b = map(int, cls_part.split("-"))
                        cls_tuple = (g, b)
                        subj_name = "스포츠"
                    else:
                        cls_tuple = None
                        subj_name = "지원"
                    for t in teachers_part.split(","):
                        t = t.strip()
                        ban[t].add(slot_i)
                        fixed_slots.append({"teacher": t, "cls": cls_tuple, "slot": slot_i, "subj": subj_name})

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

    def is_active(t, d, p):
        if (d, p) not in sidx: return 0
        slot_i = sidx[(d, p)]
        is_fixed = 1 if any(f["teacher"] == t and f["slot"] == slot_i for f in fixed_slots) else 0
        return tocc[(t, slot_i)] + is_fixed

    # 특별실 공유 금지
    sp_teachers = [x.strip() for x in user_conditions.get("special_room_text", "").split(",") if x.strip()]
    if len(sp_teachers) >= 2:
        t1, t2 = sp_teachers[0], sp_teachers[1]
        if t1 in teachers and t2 in teachers:
            for i in range(S): m.Add(tocc[(t1, i)] + tocc[(t2, i)] <= 1)

    for ci, u in enumerate(common_classes):
        g, b = u["grade"], u["cls"]; t = u["teacher"]
        m.Add(sum(xc[(ci, i)] for i in range(S)) == u["hours"])
        for i in range(S):
            if (g, b, i) in reserved or i in ban[t]: m.Add(xc[(ci, i)] == 0)

    for g, b in classes:
        cidx = [ci for ci, u in enumerate(common_classes) if u["grade"] == g and u["cls"] == b]
        for i in range(S):
            sports_in_class_slot = any(f["cls"] == (g, b) and f["slot"] == i for f in fixed_slots)
            if sports_in_class_slot:
                m.Add(sum(xc[(ci, i)] for ci in cidx) == 0)
            else:
                m.Add(sum(xc[(ci, i)] for ci in cidx) <= 1)

    # 1일 1과목 원칙 (일반 교과)
    byc = defaultdict(list)
    for ci, u in enumerate(common_classes): byc[((u["grade"], u["cls"]), u["teacher"])].append(ci)
    for (cls, t), idxs in byc.items():
        if len(idxs) >= 2:
            for d in DAYS:
                target_slots = [sidx[(d, p)] for p in range(1, GRID[d] + 1)]
                m.Add(sum(xc[(ci, i)] for ci in idxs for i in target_slots) <= 1)

    # 특정 학년 요일 금지
    for line in user_conditions.get("grade_day_text", "").split("\n"):
        if ":" in line:
            t, rule_part = line.split(":", 1)
            t = t.strip()
            for rule in rule_part.split(","):
                if "-" in rule:
                    g_str, day_str = rule.split("-", 1)
                    try:
                        g_val, day_str = int(g_str.strip()), day_str.strip()
                        for ci, u in enumerate(common_classes):
                            if u["teacher"] == t and u["grade"] == g_val:
                                target_slots = [sidx[(day_str, p)] for p in range(1, GRID[day_str] + 1) if (day_str, p) in sidx]
                                for i in target_slots: m.Add(xc[(ci, i)] == 0)
                    except: pass

    # 필수 배정
    for line in user_conditions.get("mandatory_text", "").split("\n"):
        if ":" in line and ">=" in line:
            left, req = line.rsplit(">=", 1)
            t, slots_part = left.split(":", 1)
            t, req = t.strip(), int(req.strip())
            target_slots = []
            for s in slots_part.split(","):
                for d, p in parse_slots(s):
                    if (d, p) in sidx: target_slots.append(sidx[(d, p)])
            cidx_t = [ci for ci, u in enumerate(common_classes) if u["teacher"] == t]
            if cidx_t and target_slots:
                m.Add(sum(xc[(ci, i)] for ci in cidx_t for i in target_slots) >= req)

    # 블록타임 적용
    block_teachers = [x.strip() for x in user_conditions.get("block_text", "").split(",") if x.strip()]
    for ci, u in enumerate(common_classes):
        if u["teacher"] in block_teachers and u["hours"] == 2:
            block_vars = []
            for d in DAYS:
                for p in range(1, GRID[d]):
                    if p == 4: continue # 4교시 가로지르기 금지
                    b_var = m.NewBoolVar(f"block_{ci}_{d}_{p}")
                    block_vars.append((b_var, sidx[(d, p)], sidx[(d, p+1)]))
            m.AddExactlyOne([bv[0] for bv in block_vars])
            for i in range(S):
                m.Add(xc[(ci, i)] == sum(bv[0] for bv in block_vars if bv[1] == i or bv[2] == i))

    # ==== 동적 분배 규칙 (사용자 선택 우선순위) ====
    pen = []
    hard_rules = user_conditions.get("hard_rules", [])
    soft_rules = user_conditions.get("soft_rules", [])
    support_teachers = [x.strip() for x in user_conditions.get("support_text", "").split(",") if x.strip()]

    # 1. 3연강 금지
    if "교과 3연강 절대 금지" in hard_rules or "교과 3연강 절대 금지" in soft_rules:
        for t in teachers:
            if t in support_teachers: continue 
            for d in DAYS:
                for p in range(1, GRID[d] - 1):
                    if all((d, p+k) in sidx for k in range(3)):
                        expr = sum(is_active(t, d, p+k) for k in range(3))
                        if "교과 3연강 절대 금지" in hard_rules:
                            m.Add(expr <= 2)
                        else:
                            excess = m.NewIntVar(0, 3, "")
                            m.Add(excess >= expr - 2)
                            pen.append((50, excess))

    # 2. 1일 수업 시수 균등 배정
    if "1일 수업 시수 균등 배정" in hard_rules or "1일 수업 시수 균등 배정" in soft_rules:
        for t in teachers:
            day_sums = [sum(is_active(t, d, p) for p in range(1, GRID[d]+1) if (d, p) in sidx) for d in DAYS]
            d_max = m.NewIntVar(0, 7, ""); d_min = m.NewIntVar(0, 7, "")
            m.AddMaxEquality(d_max, day_sums); m.AddMinEquality(d_min, day_sums)
            if "1일 수업 시수 균등 배정" in hard_rules:
                m.Add(d_max - d_min <= 2)
            else:
                pen.append((10, d_max - d_min))

    # 3. 1교시 공강 균등 배정
    if "1교시 공강 균등 배정" in hard_rules or "1교시 공강 균등 배정" in soft_rules:
        target_1st_work = 5 - user_conditions.get("target_1st_free", 2)
        for t in teachers:
            s_1 = sum(is_active(t, d, 1) for d in DAYS if (d, 1) in sidx)
            diff = m.NewIntVar(-5, 5, "")
            m.Add(diff == s_1 - target_1st_work)
            abs_diff = m.NewIntVar(0, 5, "")
            m.AddAbsEquality(abs_diff, diff)
            if "1교시 공강 균등 배정" in hard_rules:
                m.Add(abs_diff <= 1)
            else:
                pen.append((5, abs_diff))

    # 4. 4교시(점심시간) 공강 담임별 균등 배정
    if "4교시(점심) 공강 담임별 균등" in hard_rules or "4교시(점심) 공강 담임별 균등" in soft_rules:
        hr_1 = [x.strip() for x in user_conditions.get("hr1_text", "").split(",") if x.strip()]
        hr_2 = [x.strip() for x in user_conditions.get("hr2_text", "").split(",") if x.strip()]
        hr_3 = [x.strip() for x in user_conditions.get("hr3_text", "").split(",") if x.strip()]
        hr_others = [t for t in teachers if t not in set(hr_1 + hr_2 + hr_3)]
        
        for g_list in [hr_1, hr_2, hr_3, hr_others]:
            valid_t = [t for t in g_list if t in teachers]
            if not valid_t: continue
            p4_sums = [sum(is_active(t, d, 4) for d in DAYS if (d, 4) in sidx) for t in valid_t]
            g_max = m.NewIntVar(0, 5, ""); g_min = m.NewIntVar(0, 5, "")
            m.AddMaxEquality(g_max, p4_sums); m.AddMinEquality(g_min, p4_sums)
            if "4교시(점심) 공강 담임별 균등" in hard_rules:
                m.Add(g_max - g_min <= 1)
            else:
                pen.append((5, g_max - g_min))

    # 5. 운동장 체육 2학급 제한
    if "운동장 체육 2학급 이하 제한" in hard_rules or "운동장 체육 2학급 이하 제한" in soft_rules:
        for i in sports_slot_indices:
            pe_in_slot = []
            for ci, u in enumerate(common_classes):
                if "체육" in u["subj"] and "지원" not in u["subj"]:
                    pe_in_slot.append(xc[(ci, i)])
            if "운동장 체육 2학급 이하 제한" in hard_rules:
                m.Add(sum(pe_in_slot) <= 2)
            else:
                excess = m.NewIntVar(0, 10, "")
                m.Add(excess >= sum(pe_in_slot) - 2)
                pen.append((50, excess))

    # 6. 미술 블록 오전/오후 균등
    if "미술 블록 오전/오후 균등" in hard_rules or "미술 블록 오전/오후 균등" in soft_rules:
        for t in block_teachers:
            cidx_3 = [ci for ci, u in enumerate(common_classes) if u["teacher"] == t and u["hours"] == 2]
            if cidx_3:
                am = sum(xc[(ci, sidx[(d, p)])] for ci in cidx_3 for d in DAYS for p in range(1, 5) if (d, p) in sidx)
                pm = sum(xc[(ci, sidx[(d, p)])] for ci in cidx_3 for d in DAYS for p in range(5, 8) if (d, p) in sidx)
                diff = m.NewIntVar(-10, 10, "")
                m.Add(diff == am - pm)
                abs_diff = m.NewIntVar(0, 10, "")
                m.AddAbsEquality(abs_diff, diff)
                if "미술 블록 오전/오후 균등" in hard_rules:
                    m.Add(abs_diff <= 1)
                else:
                    pen.append((20, abs_diff))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180
    solver.parameters.num_search_workers = 8
    m.Minimize(sum(w * v for w, v in pen))
    st = solver.Solve(m)

    # ==== 8. 결과 처리 및 피드백 ====
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
        
        custom_order = [x.strip() for x in user_conditions.get("sort_text", "").split(",") if x.strip()]
        group_ends = [x.strip() for x in user_conditions.get("border_text", "").split(",") if x.strip()]
        sorted_teachers = sorted(out.keys(), key=lambda x: custom_order.index(x) if x in custom_order else 999)
                    
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "교사별 시간표"
        days_periods = [("월", 7), ("화", 6), ("수", 6), ("목", 7), ("금", 6)]

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
        thick = Side(style="medium", color="000000")
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
        return output, "성공", ""
    else:
        fb = "[AI 시간표 해결 추천 피드백]\n\n"
        if "교과 3연강 절대 금지" in hard_rules:
            fb += "1. '교과 3연강 절대 금지'를 차순위 상자로 이동해 보세요. 주당 시수가 너무 많은 선생님은 물리적으로 3연강을 피하기 어렵습니다.\n"
        if "1일 수업 시수 균등 배정" in hard_rules:
            fb += "2. '1일 수업 시수 균등 배정'을 필수로 두면 5일 분배가 불가능한 교과가 생깁니다. 가급적 '차순위'로 사용하세요.\n"
        if "4교시(점심) 공강 담임별 균등" in hard_rules:
            fb += "3. '4교시 점심 공강 균등'을 차순위로 옮겨 엔진에 여유를 주세요.\n"
        fb += "4. '교사별 세부 조건'의 텍스트 입력칸에서 김연지, 이기영, 김효진 선생님 등 제약이 많은 분의 금지 시간을 하나씩 지워보시면 배정이 훨씬 수월해집니다."
        return None, "실패", fb