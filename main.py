"""FitTracker: food checklist + calorie counter + custom workouts. Python + Flet."""
import calendar as pycal
from datetime import date, timedelta

import flet as ft

import data as db

# ---- palette: ink-navy base, mint = food, electric blue = training ----
BG = "#0A0E1A"
SURFACE = "#121829"
SURFACE_2 = "#1A2238"
LINE = "#273049"
TEXT = "#E8ECF6"
MUTED = "#8A94B0"
MINT = "#2EE59D"
BLUE = "#4F7CFF"
VIOLET = "#8B5CF6"
AMBER = "#FFB547"
DARK = "#06110C"  # text on top of mint

W = ft.FontWeight
EASE = ft.Animation(220, ft.AnimationCurve.EASE_OUT)
POP = ft.Animation(260, ft.AnimationCurve.EASE_OUT_BACK)
STRETCH = ft.CrossAxisAlignment.STRETCH


def tint(color, alpha):
    return ft.Colors.with_opacity(alpha, color)


def main(page: ft.Page):
    db.init()
    page.title = "FitTracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=BLUE)
    page.dark_theme = ft.Theme(color_scheme_seed=BLUE)
    page.bgcolor = BG
    page.padding = 0

    today = date.today()
    plan_day = db.suggest_day(today)
    st = {"tab": 0, "sel": today, "year": today.year, "month": today.month,
          "edit_food": None, "draft": None, "plan_day": plan_day, "wk_day": plan_day}

    # ---------- building blocks ----------
    def toast(msg):
        page.show_dialog(ft.SnackBar(ft.Text(msg, color=TEXT), bgcolor=SURFACE_2,
                                     behavior=ft.SnackBarBehavior.FLOATING))

    def panel(*controls, gradient=None, border=LINE, padding=16, spacing=10):
        return ft.Container(
            content=ft.Column(list(controls), spacing=spacing, horizontal_alignment=STRETCH),
            padding=padding, border_radius=22, gradient=gradient,
            bgcolor=None if gradient else SURFACE, border=ft.Border.all(1, border))

    def title(text, sub=None):
        items = [ft.Text(text, size=30, weight=W.W_800, color=TEXT)]
        if sub:
            items.append(ft.Text(sub, size=14, color=MUTED))
        return ft.Column(items, spacing=0)

    def label(text, color=MUTED):
        return ft.Text(text, size=13, weight=W.W_600, color=color)

    def chip(text, color=MUTED, bg=SURFACE_2):
        return ft.Container(content=ft.Text(text, size=12, weight=W.W_600, color=color),
                            padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                            border_radius=10, bgcolor=bg)

    def field(text, accent=BLUE, **kw):
        return ft.TextField(label=text, filled=True, bgcolor=SURFACE_2, border_radius=14,
                            border_color=LINE, focused_border_color=accent, color=TEXT,
                            cursor_color=accent, label_style=ft.TextStyle(color=MUTED), **kw)

    def big_button(text, icon, on_click, c1, c2, fg):
        return ft.Container(
            content=ft.Row([ft.Icon(icon, size=20, color=fg),
                            ft.Text(text, size=15, weight=W.W_700, color=fg)],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            height=50, border_radius=16, alignment=ft.Alignment.CENTER, ink=True,
            gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,
                                       end=ft.Alignment.CENTER_RIGHT, colors=[c1, c2]),
            on_click=on_click)

    def soft_button(text, on_click, accent=BLUE):
        return ft.Container(
            content=ft.Text(text, size=14, weight=W.W_600, color=accent),
            padding=ft.Padding.symmetric(horizontal=18, vertical=11), border_radius=14,
            bgcolor=tint(accent, 0.14), ink=True, on_click=on_click)

    def meta_chips(w):
        out = []
        if w["sets"] and w["reps"]:
            out.append(chip(f"{w['sets']}×{w['reps']}", BLUE, tint(BLUE, 0.16)))
        elif w["sets"]:
            out.append(chip(f"{w['sets']} sets", BLUE, tint(BLUE, 0.16)))
        elif w["reps"]:
            out.append(chip(f"{w['reps']} reps", BLUE, tint(BLUE, 0.16)))
        wt = (w.get("weight") or "").strip()
        if wt:
            out.append(chip(wt if not wt[-1].isdigit() else wt + " kg", VIOLET, tint(VIOLET, 0.18)))
        if not out and w.get("detail"):
            out.append(chip(w["detail"]))
        return out

    def tick_row(name, accent, checked, on_toggle, trailing=(), sub="", on_edit=None):
        """A tappable row whose check circle pops in and whose tint fades in place."""
        state = {"on": checked}
        icon = ft.Icon(ft.Icons.CHECK, size=16, color=DARK, scale=1 if checked else 0,
                       animate_scale=POP)
        box = ft.Container(content=icon, width=26, height=26, border_radius=13,
                           alignment=ft.Alignment.CENTER, animate=EASE)
        text_col = [ft.Text(name, size=15, weight=W.W_500, color=TEXT)]
        if sub:
            text_col.append(ft.Text(sub, size=12, color=MUTED))
        right = list(trailing)
        if on_edit:
            right.append(ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color=MUTED,
                                       tooltip="Edit", on_click=lambda e: on_edit()))
        row = ft.Container(
            content=ft.Row([box, ft.Column(text_col, spacing=1, expand=True), *right],
                           spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=14,
            animate=EASE, ink=True)

        def paint():
            on = state["on"]
            box.bgcolor = accent if on else None
            box.border = ft.Border.all(2, accent if on else LINE)
            icon.scale = 1 if on else 0
            row.bgcolor = tint(accent, 0.10) if on else None

        def tap(e):
            state["on"] = not state["on"]
            paint()
            on_toggle(state["on"])

        row.on_click = tap
        paint()
        return row

    def day_pills(selected, on_pick, accent):
        pills = {}

        def paint(sel):
            for k, p in pills.items():
                on = k == sel
                p.bgcolor = accent if on else SURFACE_2
                p.content.color = "#FFFFFF" if on else MUTED

        for k in db.PLAN_DAYS:
            pills[k] = ft.Container(
                content=ft.Text(f"Day {k}", size=13, weight=W.W_700, text_align=ft.TextAlign.CENTER),
                expand=1, alignment=ft.Alignment.CENTER, border_radius=12, animate=EASE,
                padding=ft.Padding.symmetric(vertical=10), on_click=lambda e, k=k: on_pick(k))
        paint(selected)
        return ft.Row(list(pills.values()), spacing=6), paint

    def confirm(heading, text, on_yes):
        def yes(e):
            page.pop_dialog()
            on_yes()
        page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=SURFACE, title=ft.Text(heading, color=TEXT),
            content=ft.Text(text, color=MUTED),
            actions=[ft.TextButton(content="Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.TextButton(content="Delete", on_click=yes,
                                   style=ft.ButtonStyle(color=ft.Colors.RED_300))]))

    def edit_workout_dialog(w):
        """Pop-up editor for one exercise: name, sets, reps, weight, notes and day."""
        name = field("Exercise name", value=w["name"])
        sets = field("Sets", value=str(w["sets"] or ""), expand=1,
                     keyboard_type=ft.KeyboardType.NUMBER)
        reps = field("Reps", value=str(w["reps"] or ""), expand=1,
                     keyboard_type=ft.KeyboardType.NUMBER)
        weight = field("Weight (kg)", value=w.get("weight") or "", expand=1)
        notes = field("Notes (optional)", value=w.get("notes") or "")
        day_dd = ft.Dropdown(
            label="Day", value=str(w["day"]), border_radius=14, border_color=LINE,
            options=[ft.DropdownOption(key=str(k), text=f"Day {k} – {t}")
                     for k, t in db.PLAN_DAYS.items()])

        def save(e):
            n = name.value.strip()
            if not n:
                toast("Enter an exercise name")
                return
            for val in (sets.value, reps.value):
                if (val or "").strip() and not (val or "").strip().isdigit():
                    toast("Sets and reps must be numbers")
                    return
            db.update_workout(w["id"], n, sets.value, reps.value, weight.value, notes.value,
                              int(day_dd.value or w["day"]))
            page.pop_dialog()
            render()

        page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=SURFACE, title=ft.Text("Edit exercise", color=TEXT),
            content=ft.Column([name, ft.Row([sets, reps, weight], spacing=8), notes, day_dd],
                              tight=True, spacing=10, width=420),
            actions=[ft.TextButton(content="Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.TextButton(content="Save", on_click=save)]))

    # Ticks on the Today tab are a draft: nothing is written to the calendar until Save.
    def ensure_draft():
        if st["draft"] is None:
            f, w = db.day_log(today.isoformat())
            st["draft"] = {"f": set(f), "w": set(w)}
        return st["draft"]

    # ---------- TODAY tab ----------
    def week_strip(total_foods):
        summary = db.range_summary(today - timedelta(days=6), today)
        cells = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            eaten, worked = summary.get(d.isoformat(), (0, 0))
            if total_foods and eaten >= total_foods:
                food_dot = MINT
            elif eaten:
                food_dot = AMBER
            else:
                food_dot = None
            is_today = d == today
            cells.append(ft.Container(
                content=ft.Column([
                    ft.Text("MTWTFSS"[d.weekday()], size=12, color=BLUE if is_today else MUTED,
                            weight=W.W_600),
                    ft.Text(str(d.day), size=16, weight=W.W_700, color=TEXT),
                    ft.Row([ft.Container(width=6, height=6, border_radius=3, bgcolor=food_dot),
                            ft.Container(width=6, height=6, border_radius=3,
                                         bgcolor=BLUE if worked else None)],
                           spacing=4, alignment=ft.MainAxisAlignment.CENTER)],
                    spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=1, padding=ft.Padding.symmetric(vertical=8), border_radius=14,
                bgcolor=tint(BLUE, 0.16) if is_today else SURFACE,
                border=ft.Border.all(1.5, BLUE) if is_today else ft.Border.all(1, LINE),
                on_click=lambda e, d=d: pick(d)))
        return ft.Row(cells, spacing=6)

    def today_tab():
        dr = ensure_draft()
        foods = db.foods()
        cur = {"works": db.workouts(st["plan_day"])}
        plan_cal = sum(f["cal"] for f in foods)
        streak = db.streak()

        ring = ft.ProgressRing(value=0, width=116, height=116, stroke_width=11, color=MINT,
                               bgcolor=tint(MINT, 0.14), stroke_cap=ft.StrokeCap.ROUND)
        pct = ft.Text("0%", size=26, weight=W.W_800, color=TEXT)
        kcal = ft.Text("", size=18, weight=W.W_700, color=TEXT)
        meals = ft.Text("", size=13, color=MUTED)
        f_hint = ft.Container(content=ft.Text("Not saved yet.", size=12, color=AMBER),
                              opacity=0, animate_opacity=EASE, alignment=ft.Alignment.CENTER)
        w_bar = ft.ProgressBar(value=0, color=BLUE, bgcolor=tint(BLUE, 0.16), height=6,
                               border_radius=3)
        w_count = ft.Text("", size=13, color=MUTED)
        w_hint = ft.Container(content=ft.Text("Not saved yet.", size=12, color=AMBER),
                              opacity=0, animate_opacity=EASE, alignment=ft.Alignment.CENTER)

        def refresh():
            eaten = [f for f in foods if f["id"] in dr["f"]]
            cal = sum(f["cal"] for f in eaten)
            frac = cal / plan_cal if plan_cal else 0
            ring.value = min(frac, 1)
            pct.value = f"{round(frac * 100)}%"
            kcal.value = f"{cal} / {plan_cal} kcal"
            meals.value = f"{len(eaten)} of {len(foods)} foods eaten"
            works = cur["works"]
            done = len(dr["w"] & {w["id"] for w in works})
            w_count.value = f"{done} of {len(works)} done"
            w_bar.value = done / len(works) if works else 0
            saved_f, saved_w = db.day_log(today.isoformat())
            f_hint.opacity = 1 if saved_f != dr["f"] else 0
            w_hint.opacity = 1 if saved_w != dr["w"] else 0

        def on_food(fid):
            def h(on):
                dr["f"].add(fid) if on else dr["f"].discard(fid)
                refresh()
                page.update()
            return h

        def on_work(wid):
            def h(on):
                dr["w"].add(wid) if on else dr["w"].discard(wid)
                refresh()
                page.update()
            return h

        def save_foods(e):
            db.set_foods(today.isoformat(), sorted(dr["f"]))
            refresh()
            page.update()
            toast("Foods saved to calendar")

        def save_workouts(e):
            db.set_workouts(today.isoformat(), sorted(dr["w"]))
            refresh()
            page.update()
            toast("Workout saved to calendar" if dr["w"] else "Rest day saved (no workout)")

        food_rows = [tick_row(f["name"], MINT, f["id"] in dr["f"], on_food(f["id"]),
                              trailing=[chip(f"{f['cal']} kcal", MINT, tint(MINT, 0.14))])
                     for f in foods] or [
            ft.Text("No foods yet. Add your first one in the Foods tab.", color=MUTED)]

        def work_list():
            k = st["plan_day"]
            rows = [tick_row(w["name"], BLUE, w["id"] in dr["w"], on_work(w["id"]),
                             trailing=meta_chips(w), sub=(w.get("notes") or "").strip(),
                             on_edit=lambda w=w: edit_workout_dialog(w))
                    for w in cur["works"]] or [
                ft.Text(f"Nothing planned for Day {k}. Add exercises in the Workouts tab.",
                        color=MUTED)]
            return ft.Container(content=ft.Column(rows, spacing=4), key=f"day{k}")

        holder = ft.AnimatedSwitcher(content=work_list(), duration=220,
                                     transition=ft.AnimatedSwitcherTransition.FADE)
        pills_row, paint_pills = day_pills(st["plan_day"], lambda k: select_day(k), BLUE)
        day_name = ft.Text(f"Day {st['plan_day']} – {db.PLAN_DAYS[st['plan_day']]}",
                           size=15, weight=W.W_700, color=BLUE)

        def select_day(k):
            st["plan_day"] = k
            dr["w"] = set()
            cur["works"] = db.workouts(k)
            paint_pills(k)
            day_name.value = f"Day {k} – {db.PLAN_DAYS[k]}"
            holder.content = work_list()
            refresh()
            page.update()

        streak_chip = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=18, color=AMBER),
                            ft.Text(f"{streak}-day streak", size=13, weight=W.W_700, color=AMBER)],
                           spacing=4),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7), border_radius=16,
            bgcolor=tint(AMBER, 0.14)) if streak else ft.Container()

        refresh()
        hero = panel(
            ft.Row([
                ft.Stack([ring, ft.Container(content=pct, width=116, height=116,
                                             alignment=ft.Alignment.CENTER)], width=116, height=116),
                ft.Column([label("Today's fuel", MINT), kcal, meals], spacing=3, expand=True)],
                spacing=18, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column(food_rows, spacing=4),
            big_button("Save foods", ft.Icons.SAVE, save_foods, MINT, "#19B97A", DARK),
            f_hint,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[tint(MINT, 0.20), tint(MINT, 0.03)]),
            border=tint(MINT, 0.35), spacing=12)
        train = panel(
            ft.Row([label("Training"), w_count], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            pills_row, day_name, w_bar, holder,
            big_button("Save workout", ft.Icons.SAVE, save_workouts, BLUE, VIOLET, "#FFFFFF"),
            w_hint, spacing=12)
        return [
            ft.Row([title(today.strftime("%A"), today.strftime("%d %B %Y")), streak_chip],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            week_strip(len(foods)), hero, train]

    # ---------- HISTORY tab (calendar) ----------
    def shift_month(n):
        m = st["month"] + n
        y = st["year"]
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        st["month"], st["year"] = m, y
        render()

    def show_day(d):
        foods, works = db.foods(), db.workouts()
        eaten_ids, done_ids = db.day_log(d.isoformat())
        eaten = [f for f in foods if f["id"] in eaten_ids]
        done = [w for w in works if w["id"] in done_ids]
        kcal_total = sum(f["cal"] for f in eaten)

        def line(color, left, right=""):
            return ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=color, size=20),
                           ft.Text(left, expand=True, color=TEXT),
                           ft.Text(right, color=MUTED)])

        food_lines = [line(MINT, f["name"], f"{f['cal']} kcal") for f in eaten] or [
            ft.Text("No foods ticked", color=MUTED)]
        work_lines = []
        for k in sorted({w["day"] for w in done}):
            work_lines.append(ft.Text(f"Day {k} – {db.PLAN_DAYS.get(k, '')}", size=12, color=MUTED))
            work_lines += [line(BLUE, w["name"], db.describe(w)) for w in done if w["day"] == k]
        if not work_lines:
            work_lines = [ft.Text("No workouts done", color=MUTED)]
        page.show_dialog(ft.BottomSheet(ft.Container(
            padding=20, bgcolor=SURFACE,
            content=ft.Column([
                ft.Text(d.strftime("%A, %d %B %Y"), size=20, weight=W.W_800, color=TEXT),
                label("Foods eaten", MINT), *food_lines,
                ft.Text(f"Total: {kcal_total} kcal", weight=W.W_700, color=TEXT),
                ft.Divider(color=LINE),
                label("Workouts done", BLUE), *work_lines,
                ft.Row([ft.TextButton(content="Close", on_click=lambda e: page.pop_dialog())],
                       alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=8, scroll=ft.ScrollMode.AUTO))))

    def pick(d):
        st["sel"] = d
        render()
        show_day(d)

    def day_cell(d, summary, total_foods):
        if d == 0:
            return ft.Container(expand=1, height=58)
        this = date(st["year"], st["month"], d)
        future = this > today
        eaten, worked = summary.get(d, (0, 0))
        if total_foods and eaten >= total_foods:
            bg = tint(MINT, 0.28)
        elif eaten:
            bg = tint(AMBER, 0.24)
        else:
            bg = None if future else SURFACE
        if this == today:
            border = ft.Border.all(1.5, BLUE)
        elif this == st["sel"]:
            border = ft.Border.all(1.5, MUTED)
        else:
            border = None
        num_color = tint(TEXT, 0.3) if future else TEXT
        return ft.Container(
            content=ft.Column([
                ft.Text(str(d), size=16, weight=W.W_700 if this == today else W.W_500,
                        color=num_color),
                ft.Container(width=16, height=4, border_radius=2,
                             bgcolor=BLUE if worked else None)],
                spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=1, height=58, margin=2, border_radius=14, bgcolor=bg, border=border,
            on_click=None if future else (lambda e, this=this: pick(this)))

    def history_tab():
        foods = db.foods()
        total = len(foods)
        summary = db.month_summary(st["year"], st["month"])
        full_days = sum(1 for e, _ in summary.values() if total and e >= total)
        work_days = sum(1 for _, w in summary.values() if w)

        def stat(value, text, color):
            return ft.Column([ft.Text(str(value), size=24, weight=W.W_800, color=color),
                              ft.Text(text, size=12, color=MUTED)], spacing=0, expand=1,
                             horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        month_row = ft.Row([
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_color=MUTED,
                          on_click=lambda e: shift_month(-1)),
            ft.Text(date(st["year"], st["month"], 1).strftime("%B %Y"), size=20,
                    weight=W.W_700, color=TEXT, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=MUTED,
                          on_click=lambda e: shift_month(1))])
        weekdays = ft.Row([ft.Text(w, expand=1, text_align=ft.TextAlign.CENTER, size=13,
                                   weight=W.W_600, color=MUTED)
                           for w in ["S", "M", "T", "W", "T", "F", "S"]])
        weeks = [ft.Row([day_cell(d, summary, total) for d in wk], spacing=0)
                 for wk in pycal.Calendar(firstweekday=6).monthdayscalendar(st["year"], st["month"])]

        def key(color, text, bar=False):
            swatch = ft.Container(width=16 if bar else 12, height=4 if bar else 12,
                                  border_radius=2 if bar else 4, bgcolor=color)
            return ft.Row([swatch, ft.Text(text, size=12, color=MUTED)], spacing=6)

        legend = ft.Row([key(tint(MINT, 0.6), "All foods"), key(tint(AMBER, 0.6), "Some foods"),
                         key(BLUE, "Workout", bar=True)],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=16, wrap=True)
        return [
            title("History", "Tap a day to see what you ate and did"),
            panel(ft.Row([stat(work_days, "workout days", BLUE), stat(full_days, "full food days", MINT),
                          stat(len(summary), "days logged", TEXT)]), padding=12),
            panel(month_row, weekdays, *weeks, legend, padding=10, spacing=6),
        ]

    # ---------- FOODS tab ----------
    def foods_tab():
        editing = next((f for f in db.foods() if f["id"] == st["edit_food"]), None)
        name = field("Food name", MINT, value=editing["name"] if editing else "")
        cal = field("Calories", MINT, keyboard_type=ft.KeyboardType.NUMBER,
                    value=str(editing["cal"]) if editing else "")

        def save(e):
            n, c = name.value.strip(), (cal.value or "").strip()
            if not n or not c.isdigit():
                toast("Enter a name and calories (number)")
                return
            if editing:
                db.update_food(editing["id"], n, int(c))
                st["edit_food"] = None
            else:
                db.add_food(n, int(c))
            render()

        def cancel(e):
            st["edit_food"] = None
            render()

        def edit(fid):
            st["edit_food"] = fid
            render()

        def remove(f):
            confirm("Delete food?", f"Delete '{f['name']}' and its history?",
                    lambda: (db.delete_food(f["id"]), render()))

        foods = db.foods()
        top = max((f["cal"] for f in foods), default=1) or 1
        rows = [ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f["name"], size=15, weight=W.W_500, color=TEXT, expand=True),
                    chip(f"{f['cal']} kcal", MINT, tint(MINT, 0.14)),
                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color=MINT,
                                  on_click=lambda e, fid=f["id"]: edit(fid)),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=MUTED,
                                  on_click=lambda e, f=f: remove(f))]),
                ft.ProgressBar(value=f["cal"] / top, color=MINT, bgcolor=tint(MINT, 0.12),
                               height=4, border_radius=2)], spacing=2),
            padding=ft.Padding.symmetric(horizontal=6, vertical=4)) for f in foods] or [
            ft.Text("Nothing yet. Add your first food above.", color=MUTED)]
        buttons = [big_button("Save changes" if editing else "Add food",
                              ft.Icons.CHECK if editing else ft.Icons.ADD, save, MINT, "#19B97A", DARK)]
        if editing:
            buttons.append(soft_button("Cancel", cancel, MINT))
        return [
            title("Foods", f"Daily plan: {sum(f['cal'] for f in foods)} kcal"),
            panel(label("Edit food" if editing else "Add food", MINT), name, cal, *buttons,
                  border=tint(MINT, 0.35)),
            panel(label("Your foods", MINT), *rows, border=tint(MINT, 0.35)),
        ]

    # ---------- WORKOUTS tab ----------
    def workouts_tab():
        k = st["wk_day"]

        def pick_day(n):
            st["wk_day"] = n
            render()

        pills_row, _ = day_pills(k, pick_day, BLUE)
        name = field("Workout name (e.g. Squats)")
        sets = field("Sets", expand=1, keyboard_type=ft.KeyboardType.NUMBER)
        reps = field("Reps", expand=1, keyboard_type=ft.KeyboardType.NUMBER)
        weight = field("Weight (kg)", expand=1)
        notes = field("Notes (optional)")

        def add(e):
            n = name.value.strip()
            if not n:
                toast("Enter a workout name")
                return
            for val in (sets.value, reps.value):
                if (val or "").strip() and not (val or "").strip().isdigit():
                    toast("Sets and reps must be numbers")
                    return
            db.add_workout(n, sets.value, reps.value, weight.value, notes.value, k)
            render()

        def remove(w):
            confirm("Delete workout?", f"Delete '{w['name']}' and its history?",
                    lambda: (db.delete_workout(w["id"]), render()))

        rows = [ft.Container(
            content=ft.Row([
                ft.Column([ft.Text(w["name"], size=15, weight=W.W_500, color=TEXT),
                           ft.Text((w.get("notes") or "").strip(), size=12, color=MUTED)],
                          spacing=1, expand=True),
                *meta_chips(w),
                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color=BLUE,
                              tooltip="Edit", on_click=lambda e, w=w: edit_workout_dialog(w)),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=MUTED,
                              on_click=lambda e, w=w: remove(w))],
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2))
            for w in db.workouts(k)] or [ft.Text("Nothing here yet. Add the first exercise below.",
                                                 color=MUTED)]
        return [
            title("Workouts", "Your 4-day plan"),
            pills_row,
            panel(ft.Text(f"Day {k} – {db.PLAN_DAYS[k]}", size=16, weight=W.W_700, color=BLUE), *rows),
            panel(label(f"Add to Day {k}", BLUE), name, ft.Row([sets, reps, weight], spacing=8),
                  notes, big_button("Add workout", ft.Icons.ADD, add, BLUE, VIOLET, "#FFFFFF")),
        ]

    # ---------- MORE tab ----------
    def more_tab():
        path_field = field("Backup file path to import", hint_text=db.backup_path())

        def do_export(e):
            p = db.backup_path()
            db.export_json(p)
            toast(f"Saved: {p}")

        def do_import(e):
            p = (path_field.value or "").strip()
            if not p:
                toast("Type the path of a backup file")
                return
            try:
                db.import_json(p)
            except Exception as ex:
                toast(f"Import failed: {ex}")
                return
            st["draft"] = None
            render()
            toast("Imported")

        def do_reset():
            db.reset_all()
            st["draft"] = None
            render()

        return [
            title("More"),
            panel(label("Backup"),
                  ft.Text("Your data is stored on this device only.", size=13, color=MUTED),
                  soft_button("Export backup", do_export),
                  path_field, soft_button("Import backup", do_import)),
            panel(label("Reset", ft.Colors.RED_300),
                  soft_button("Delete all data",
                              lambda e: confirm("Delete everything?", "This cannot be undone.",
                                                do_reset), ft.Colors.RED_300),
                  border=tint(ft.Colors.RED_300, 0.3)),
        ]

    # ---------- shell ----------
    tabs = [today_tab, history_tab, foods_tab, workouts_tab, more_tab]
    holder = ft.AnimatedSwitcher(content=ft.Container(), duration=240, expand=True,
                                 transition=ft.AnimatedSwitcherTransition.FADE)

    def render():
        col = ft.Column(tabs[st["tab"]](), scroll=ft.ScrollMode.AUTO, expand=True, spacing=14,
                        horizontal_alignment=STRETCH)
        holder.content = ft.Container(content=col, key=f"tab{st['tab']}", expand=True,
                                      padding=ft.Padding.symmetric(horizontal=14, vertical=10))
        page.navigation_bar.selected_index = st["tab"]
        page.update()

    def set_tab(i):
        st["tab"] = i
        render()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0, bgcolor=SURFACE, indicator_color=tint(BLUE, 0.28),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.TODAY, label="Today"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="History"),
            ft.NavigationBarDestination(icon=ft.Icons.RESTAURANT, label="Foods"),
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER, label="Workouts"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="More"),
        ],
        on_change=lambda e: set_tab(e.control.selected_index),
    )
    page.add(ft.SafeArea(expand=True, content=holder))
    render()


if __name__ == "__main__":
    ft.run(main)
