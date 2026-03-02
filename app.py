import streamlit as st
from main import get_canvas_data, list_active_courses
from datetime import time, datetime, timedelta
import re
import random

DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

DISPLAY_START = 7 * 60
DISPLAY_END = 20 * 60

STUDY_WINDOW_START = 8 * 60
STUDY_WINDOW_END = 20 * 60

CORE_START = 10 * 60
CORE_END = 16 * 60

MIN_GAP_MINUTES = 30
SLOT_MINUTES = 30

CANVAS_BASE = "https://canvas.instructure.com"

st.set_page_config(layout="wide", page_title="AI Weekly Study Planner")

if "confirmed_busy" not in st.session_state:
    st.session_state.confirmed_busy = []

st.title("Canvas Schedule Generator")

colA, colB = st.columns([1, 2])
with colA:
    include_weekends = st.checkbox("Include weekends", value=True)
with colB:
    time_preference = st.selectbox("Preferred study time", ["No preference", "Morning", "Afternoon", "Night"], index=0)

courses = list_active_courses()
if not courses:
    st.error("No active courses found in Canvas.")
    st.stop()

name_to_id = {c["name"]: c["id"] for c in courses}
selected_names = st.multiselect("Choose course(s)", options=list(name_to_id.keys()), default=[])
selected_course_ids = [name_to_id[n] for n in selected_names]

with st.form("add_block_form", clear_on_submit=True):
    dcol1, dcol2, dcol3, dcol4 = st.columns([1.2, 1, 1, 2])
    day = dcol1.selectbox("Day", DAY_ORDER)
    start_t = dcol2.time_input("Start", time(8, 0))
    end_t = dcol3.time_input("End", time(9, 0))
    label = dcol4.text_input("Label", "")
    if st.form_submit_button("Add Block"):
        if start_t >= end_t:
            st.error("End time must be later than start time.")
        else:
            st.session_state.confirmed_busy.append({
                "day": day,
                "start": start_t.strftime("%I:%M %p"),
                "end": end_t.strftime("%I:%M %p"),
                "title": label
            })
            st.success(f"Added {label} on {day}.")

if st.session_state.confirmed_busy:
    with st.expander("Protected Time", expanded=False):
        for b in st.session_state.confirmed_busy:
            st.write(f"**{b['day']}**: {b['start']} – {b['end']} | {b['title']}")
        if st.button("Clear Blocks"):
            st.session_state.confirmed_busy = []
            st.rerun()

def parse_ampm_to_minutes(tstr):
    try:
        dt = datetime.strptime(tstr.strip(), "%I:%M %p")
        return dt.hour * 60 + dt.minute
    except Exception:
        return None

def minutes_to_ampm(minutes):
    minutes = max(0, min(23 * 60 + 59, minutes))
    h = minutes // 60
    m = minutes % 60
    return datetime.strptime(f"{h:02d}:{m:02d}", "%H:%M").strftime("%I:%M %p")

def parse_due_date(val):
    if not val:
        return None
    if isinstance(val, datetime):
        dt = val
        if dt.tzinfo is None:
            return dt
        return dt.astimezone()
    s = str(val).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt
        return dt.astimezone()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def fmt_due(dt):
    if not dt:
        return ""
    return dt.strftime("%a %m/%d %I:%M %p")

def normalize_material_url(u):
    if not u:
        return None
    m = re.search(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", str(u))
    if m:
        u = m.group(2)
    u = str(u).strip()
    if u.startswith(CANVAS_BASE + "/api/v1/"):
        u = u.replace("/api/v1", "")
    return u

def merge_intervals(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ps, pe = merged[-1]
        if s <= pe:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged

def subtract_intervals(window, busy):
    ws, we = window
    free = []
    cur = ws
    for bs, be in busy:
        if be <= cur:
            continue
        if bs >= we:
            break
        if bs > cur:
            free.append((cur, min(bs, we)))
        cur = max(cur, be)
        if cur >= we:
            break
    if cur < we:
        free.append((cur, we))
    return free

def intersect_intervals(a, b):
    out = []
    i = 0
    j = 0
    a = sorted(a, key=lambda x: x[0])
    b = sorted(b, key=lambda x: x[0])
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if e > s:
            out.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out

def total_minutes(intervals):
    return sum(e - s for s, e in intervals)

def preference_window(pref):
    if pref == "Morning":
        return [(8 * 60, 12 * 60)]
    if pref == "Afternoon":
        return [(12 * 60, 17 * 60)]
    if pref == "Night":
        return [(17 * 60, 20 * 60)]
    return [(STUDY_WINDOW_START, STUDY_WINDOW_END)]

def compute_free_slots(busy_blocks, include_weekends, time_preference):
    busy_by_day = {d: [] for d in DAY_ORDER}
    for b in busy_blocks:
        s = parse_ampm_to_minutes(b["start"])
        e = parse_ampm_to_minutes(b["end"])
        if s is None or e is None:
            continue
        busy_by_day[b["day"]].append((s, e))

    slots = {d: [] for d in DAY_ORDER}
    for d in DAY_ORDER:
        if not include_weekends and d in ("Saturday", "Sunday"):
            continue
        merged_busy = merge_intervals(busy_by_day[d])
        free = subtract_intervals((STUDY_WINDOW_START, STUDY_WINDOW_END), merged_busy)
        free = [(s, e) for s, e in free if (e - s) >= MIN_GAP_MINUTES]

        if time_preference == "No preference":
            core = intersect_intervals(free, [(CORE_START, CORE_END)])
            core = [(s, e) for s, e in core if (e - s) >= MIN_GAP_MINUTES]
            use = core if total_minutes(core) >= 60 else free
        else:
            pref = intersect_intervals(free, preference_window(time_preference))
            pref = [(s, e) for s, e in pref if (e - s) >= MIN_GAP_MINUTES]
            use = pref if total_minutes(pref) >= 60 else free

        slots[d] = merge_intervals(use)
    return slots

def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or a_start >= b_end)

def blocks_to_minutes(schedule, day):
    out = []
    for b in schedule.get(day, []):
        sm = parse_ampm_to_minutes(b.get("start",""))
        em = parse_ampm_to_minutes(b.get("end",""))
        if sm is None or em is None:
            continue
        out.append((sm, em, b))
    out.sort(key=lambda x: x[0])
    return out

def find_slot(day, duration, free_slots, schedule, bias="core_center", min_start=None):
    existing = blocks_to_minutes(schedule, day)
    candidates = []
    for ss, se in free_slots.get(day, []):
        if min_start is not None:
            ss = max(ss, min_start)
        if se - ss < duration:
            continue
        if bias == "latest":
            start = se - duration
            candidates.extend(range(start, ss - 1, -SLOT_MINUTES))
        elif bias == "earliest":
            candidates.extend(range(ss, se - duration + 1, SLOT_MINUTES))
        else:
            center = (ss + se) // 2
            start0 = max(ss, min(se - duration, center - duration // 2))
            jitter = random.choice([-30, -15, 0, 15, 30])
            start0 = max(ss, min(se - duration, start0 + jitter))
            around = [start0, start0 - 30, start0 + 30, start0 - 60, start0 + 60, ss, se - duration]
            for x in around:
                if ss <= x <= se - duration:
                    candidates.append(x)
    seen = set()
    ordered = []
    for c in candidates:
        c = (c // SLOT_MINUTES) * SLOT_MINUTES
        if c in seen:
            continue
        seen.add(c)
        ordered.append(c)
    for cand_start in ordered:
        cand_end = cand_start + duration
        conflict = any(overlaps(cand_start, cand_end, bs, be) for bs, be, _ in existing)
        if not conflict:
            return cand_start, cand_end
    return None

def day_index():
    return {d: i for i, d in enumerate(DAY_ORDER)}

def is_quizlike(name):
    n = (name or "").lower()
    return any(k in n for k in ["quiz", "exam", "test"])

def is_big_assignment(name):
    n = (name or "").lower()
    return any(k in n for k in ["report", "essay", "paper", "project", "research", "notebook", "lab"])

def week_bounds_local_with_grace():
    now = datetime.now()
    start = now - timedelta(days=now.weekday())
    start = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_sun = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    grace = end_sun + timedelta(hours=8)
    return start, end_sun, grace

def build_assignment_list(canvas_data):
    items = []
    for course in canvas_data.get("courses", []):
        cname = course.get("course_name","Course")
        for a in course.get("assignments", []):
            nm = a.get("name") or ""
            due_dt = parse_due_date(a.get("due"))
            url = normalize_material_url(a.get("url"))
            if nm and due_dt:
                items.append({
                    "course": cname,
                    "name": nm,
                    "name_l": nm.lower(),
                    "due_dt": due_dt,
                    "due_day": due_dt.strftime("%A"),
                    "due_display": fmt_due(due_dt),
                    "url": url
                })
    items.sort(key=lambda x: x["due_dt"])
    return items

def build_module_materials(canvas_data):
    mats = []
    for course in canvas_data.get("courses", []):
        cname = course.get("course_name","Course")
        for it in (course.get("module_items") or []):
            title = (it.get("title") or "").strip()
            url = normalize_material_url(it.get("url") or it.get("html_url") or "")
            module = (it.get("module") or it.get("module_name") or "").strip()
            if title and url:
                mats.append({
                    "course": cname,
                    "title": title,
                    "module": module,
                    "url": url
                })
    return mats

def add_block(schedule, day, start_min, end_min, course, task, url, due_display, notes):
    schedule[day].append({
        "start": minutes_to_ampm(start_min),
        "end": minutes_to_ampm(end_min),
        "course": course,
        "task": task,
        "materials": [u for u in [url] if u],
        "due_display": due_display,
        "notes": notes or ""
    })

def schedule_rule_based(assignments, materials, free_slots, include_weekends, time_preference, max_hours_daily):
    schedule = {d: [] for d in DAY_ORDER}
    di = day_index()
    wk_start, wk_end_sun, wk_grace = week_bounds_local_with_grace()

    week_items = [x for x in assignments if wk_start <= x["due_dt"] <= wk_grace]
    quizzes = [x for x in week_items if is_quizlike(x["name"])]
    assigns = [x for x in week_items if not is_quizlike(x["name"])]

    required_minutes = 0
    for q in quizzes:
        required_minutes += 150
    for a in assigns:
        required_minutes += (180 if is_big_assignment(a["name"]) else 120) + 20

    daily_minutes = {d: 0 for d in DAY_ORDER}

    def can_use_day(d):
        if not include_weekends and d in ("Saturday","Sunday"):
            return False
        return True

    available_days = [d for d in DAY_ORDER if can_use_day(d)]
    base_capacity = len(available_days) * max_hours_daily * 60
    effective_max = max_hours_daily
    if required_minutes > base_capacity:
        effective_max = min(10, max_hours_daily + 3)

    def bias_for():
        if time_preference == "Morning":
            return "earliest"
        if time_preference == "Night":
            return "latest"
        return "core_center"

    def place(d, duration, min_start=None, bias=None):
        if daily_minutes[d] + duration > effective_max * 60:
            return None
        return find_slot(d, duration, free_slots, schedule, bias=bias or bias_for(), min_start=min_start)

    daily_quiz_focus = {d: None for d in DAY_ORDER}

    def reserve_quiz_prep(q, d, duration=60):
        if not can_use_day(d):
            return False
        focus = daily_quiz_focus[d]
        if focus is not None and focus != q["name_l"]:
            return False
        p = place(d, duration)
        if not p:
            return False
        s, e = p
        add_block(schedule, d, s, e, q["course"], f"Prep: {q['name']}", q["url"], q["due_display"], "Review notes + do practice problems.")
        daily_minutes[d] += duration
        daily_quiz_focus[d] = q["name_l"]
        return True

    for q in quizzes:
        due_day = q["due_day"]
        due_idx = di.get(due_day, 6)
        for off in [2, 1]:
            idx = due_idx - off
            if idx >= 0:
                reserve_quiz_prep(q, DAY_ORDER[idx], 60)
        if can_use_day(due_day):
            p = place(due_day, 30)
            if p:
                s, e = p
                add_block(schedule, due_day, s, e, q["course"], f"TAKE: {q['name']}", q["url"], q["due_display"], f"Complete before {q['due_dt'].strftime('%I:%M %p')}.")
                daily_minutes[due_day] += 30
                daily_quiz_focus[due_day] = q["name_l"]

    for a in assigns:
        due_day = a["due_day"]
        due_idx = di.get(due_day, 6)
        total = 180 if is_big_assignment(a["name"]) else 120

        if total <= 120:
            stages = [("Draft", 60), ("Revise/Finalize", 60)]
        else:
            stages = [("Plan/Outline", 60), ("Draft", 60), ("Revise/Finalize", 60)]

        stage_notes = {
            "Plan/Outline": "Choose approach + outline sections + list requirements.",
            "Draft": "Write/build the main content. Aim for completion.",
            "Revise/Finalize": "Polish, verify rubric, checklist."
        }

        candidate_days = []
        for i in range(max(0, due_idx - 5), min(6, due_idx) + 1):
            d = DAY_ORDER[i]
            if can_use_day(d):
                candidate_days.append(d)
        if not candidate_days:
            continue

        last_pos = None
        for stage_name, dur in stages:
            placed = False
            min_day_idx = last_pos[0] if last_pos else di[candidate_days[0]]
            min_start = last_pos[1] if last_pos and last_pos[0] == min_day_idx else None
            for d in candidate_days:
                if di[d] < min_day_idx:
                    continue
                ms = min_start if di[d] == min_day_idx else None
                p = place(d, dur, min_start=ms)
                if p:
                    s, e = p
                    add_block(schedule, d, s, e, a["course"], f"{stage_name}: {a['name']}", a["url"], a["due_display"], stage_notes.get(stage_name, ""))
                    daily_minutes[d] += dur
                    last_pos = (di[d], e)
                    placed = True
                    break
            if not placed:
                break

        submit_day = due_day
        if due_day == "Monday" and a["due_dt"] <= wk_grace and a["due_dt"] > wk_end_sun:
            submit_day = "Sunday"

        submit_min_start = None
        if last_pos is not None and last_pos[0] == di.get(submit_day, 6):
            submit_min_start = last_pos[1]

        p = place(submit_day, 20, min_start=submit_min_start, bias="latest")
        if not p:
            for idx in range(di.get(submit_day, 6), -1, -1):
                d = DAY_ORDER[idx]
                if not can_use_day(d):
                    continue
                ms = None
                if last_pos is not None and last_pos[0] == idx:
                    ms = last_pos[1]
                p2 = place(d, 20, min_start=ms, bias="latest")
                if p2:
                    submit_day = d
                    p = p2
                    break

        if p:
            s, e = p
            add_block(schedule, submit_day, s, e, a["course"], f"SUBMIT: {a['name']}", a["url"], a["due_display"], f"Final check + submit before {a['due_dt'].strftime('%I:%M %p')}.")

    course_deadlines = {}
    for it in week_items:
        course_deadlines.setdefault(it["course"], []).append(it["due_dt"])
    for c in course_deadlines:
        course_deadlines[c].sort()

    mats_by_course = {}
    for m in materials:
        mats_by_course.setdefault(m["course"], []).append(m)

    selected_courses_set = set([c["name"] for c in list_active_courses() if c["id"] in selected_course_ids])
    for c in selected_courses_set:
        mats_by_course.setdefault(c, [])

    for course, mats in mats_by_course.items():
        deadline_list = course_deadlines.get(course, [])
        target_due = deadline_list[0] if deadline_list else wk_end_sun
        target_day = target_due.strftime("%A")
        target_idx = di.get(target_day, 6)

        review_days = []
        for off in [3, 2, 1]:
            idx = target_idx - off
            if idx >= 0:
                d = DAY_ORDER[idx]
                if can_use_day(d):
                    review_days.append(d)
        if not review_days:
            for d in DAY_ORDER:
                if can_use_day(d):
                    review_days.append(d)
                    break

        mats = mats[:8]
        day_ptr = 0
        for m in mats:
            label = m["title"]
            if m.get("module"):
                label = f"{m['module']}: {m['title']}"
            d = review_days[min(day_ptr, len(review_days)-1)]
            p = place(d, 30)
            if not p:
                placed = False
                for dd in review_days:
                    p2 = place(dd, 30)
                    if p2:
                        d = dd
                        p = p2
                        placed = True
                        break
                if not placed:
                    continue
            s, e = p
            add_block(schedule, d, s, e, course, f"REVIEW MATERIALS: {label}", m["url"], "", "Skim, take notes, pull 3 key points + 2 questions.")
            daily_minutes[d] += 30
            day_ptr += 1

    for d in DAY_ORDER:
        schedule[d].sort(key=lambda b: parse_ampm_to_minutes(b.get("start","")) or 10**9)

    return schedule

def safe_html(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_events(schedule, busy_blocks):
    events = {d: [] for d in DAY_ORDER}
    for b in busy_blocks:
        sm = parse_ampm_to_minutes(b["start"])
        em = parse_ampm_to_minutes(b["end"])
        if sm is None or em is None:
            continue
        events[b["day"]].append({"start": sm, "end": em, "title": b["title"], "kind": "busy", "course": "", "materials": [], "notes": "", "due_display": ""})

    for d in DAY_ORDER:
        for b in schedule.get(d, []):
            sm = parse_ampm_to_minutes(b.get("start", ""))
            em = parse_ampm_to_minutes(b.get("end", ""))
            if sm is None or em is None:
                continue
            mats = []
            for u in (b.get("materials", []) or []):
                nu = normalize_material_url(u)
                if nu:
                    mats.append(nu)
            events[d].append({"start": sm, "end": em, "title": b.get("task",""), "kind": "study", "course": b.get("course",""), "materials": mats, "notes": b.get("notes","") or "", "due_display": b.get("due_display","") or ""})
        events[d] = sorted(events[d], key=lambda x: (x["start"], x["end"]))
    return events

def render_calendar(schedule, busy_blocks):
    events = build_events(schedule, busy_blocks)
    times = list(range(DISPLAY_START, DISPLAY_END, SLOT_MINUTES))

    day_cells = {d: {} for d in DAY_ORDER}
    for d in DAY_ORDER:
        for ev in events[d]:
            s = max(DISPLAY_START, ev["start"])
            e = min(DISPLAY_END, ev["end"])
            if e <= s:
                continue
            s_idx = (s - DISPLAY_START) // SLOT_MINUTES
            e_idx = (e - DISPLAY_START + SLOT_MINUTES - 1) // SLOT_MINUTES
            rowspan = max(1, e_idx - s_idx)
            day_cells[d][s_idx] = (rowspan, ev)
            for k in range(s_idx + 1, s_idx + rowspan):
                day_cells[d][k] = None

    css = """
    <style>
    .cal-wrap{overflow-x:auto;}
    table.cal{border-collapse:collapse; width:100%; table-layout:fixed; font-family:Segoe UI, Arial, sans-serif;}
    table.cal th{position:sticky; top:0; background:#f3f4f6; z-index:2; border:1px solid #e5e7eb; padding:8px; font-size:14px;}
    table.cal td{border:1px solid #e5e7eb; vertical-align:top; padding:6px; font-size:12px; height:34px; word-wrap:break-word;}
    td.time{background:#fafafa; width:90px; font-weight:600; color:#374151;}
    td.empty{background:#ffffff;}
    td.busy{background:#ffe4e6; color:#7f1d1d;}
    td.study{background:#dcfce7; color:#14532d;}
    .ev-title{font-weight:700; margin-bottom:4px; line-height:1.2;}
    .ev-sub{opacity:0.9; font-size:11px; margin-top:2px; line-height:1.2;}
    .ev-links{margin-top:4px; font-size:11px; line-height:1.2;}
    .ev-links a{color:#2563eb; text-decoration:underline;}
    .ev-notes{margin-top:4px; font-size:11px; opacity:0.9; line-height:1.2;}
    </style>
    """
    html = [css, '<div class="cal-wrap"><table class="cal">']
    html.append("<tr><th></th>" + "".join([f"<th>{d}</th>" for d in DAY_ORDER]) + "</tr>")

    for i, t in enumerate(times):
        row = [f'<tr><td class="time">{minutes_to_ampm(t)}</td>']
        for d in DAY_ORDER:
            cell = day_cells[d].get(i, "empty")
            if cell is None:
                continue
            if cell == "empty":
                row.append('<td class="empty"></td>')
            else:
                rowspan, ev = cell
                cls = "busy" if ev["kind"] == "busy" else "study"
                title_html = safe_html(ev.get("title",""))

                course_line = (ev.get("course","") or "").strip()
                due_line = (ev.get("due_display","") or "").strip()
                if course_line and due_line:
                    course_line = f"{course_line} • Due: {due_line}"
                elif due_line:
                    course_line = f"Due: {due_line}"

                links = []
                mats = ev.get("materials") or []
                for u in mats[:2]:
                    if u:
                        safe_u = u.replace('"', "%22")
                        links.append(f'<a href="{safe_u}" target="_blank" rel="noopener noreferrer">Open</a>')
                links_html = ('<div class="ev-links">' + " • ".join(links) + '</div>') if links else ""

                notes = (ev.get("notes","") or "").strip()
                notes_html = f'<div class="ev-notes">{safe_html(notes)}</div>' if notes else ""

                body = f'<div class="ev-title">{title_html}</div>'
                if course_line:
                    body += f'<div class="ev-sub">{safe_html(course_line)}</div>'
                body += links_html + notes_html

                row.append(f'<td class="{cls}" rowspan="{rowspan}">{body}</td>')
        row.append("</tr>")
        html.append("".join(row))

    html.append("</table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

max_hours_daily = st.slider("Max study hours per day", min_value=1, max_value=10, value=4, step=1)

if st.button("Create Schedule", type="primary"):
    if not selected_course_ids:
        st.warning("Please select at least one course.")
    elif not st.session_state.confirmed_busy:
        st.warning("Please add at least one block first duhhhhhhhhh error 3")
    else:
        canvas_data = get_canvas_data(selected_course_ids)
        assignments = build_assignment_list(canvas_data)
        materials = build_module_materials(canvas_data)
        free_slots = compute_free_slots(st.session_state.confirmed_busy, include_weekends, time_preference)
        schedule = schedule_rule_based(assignments, materials, free_slots, include_weekends, time_preference, max_hours_daily)
        render_calendar(schedule, st.session_state.confirmed_busy)