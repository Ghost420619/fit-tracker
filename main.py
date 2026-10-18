"""FitTracker: food checklist + calorie counter + custom workouts. Python + Flet."""
import calendar as pycal
from datetime import date

import flet as ft

import data as db

BLUE = ft.Colors.BLUE_ACCENT_700
GREEN = ft.Colors.GREEN_600
FOOD_BG = "#000000"
FOOD_CARD = "#141414"
FOOD_GREEN = "#22C55E"
FOOD_TEXT = "#FFFFFF"
FOOD_MUTED = "#9CA3AF"


def main(page: ft.Page):
    db.init()
    page.title = "FitTracker"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
    page.padding = 0

    today = date.today()
    st = {"tab": 0, "sel": today, "year": today.year, "month": today.month,
          "edit_food": None, "edit_work": None, "draft": None,
          "plan_day": db.suggest_day(today), "add_day": 1}
    body = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=12,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # ---------- helpers ----------
    def toast(msg):
        page.show_dialog(ft.SnackBar(ft.Text(msg)))

    def card(*controls):
        return ft.Container(
            content=ft.Column(list(controls), spacing=6,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=14, border_radius=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        )

    def heading(text):
        return ft.Text(text, size=16, weight=ft.FontWeight.BOLD)

    def food_card(*controls):
        return ft.Container(
            content=ft.Column(list(controls), spacing=6,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=14, border_radius=16, bgcolor=FOOD_CARD,
            border=ft.Border.all(1, FOOD_GREEN),
        )

    def food_heading(text):
        return ft.Text(text, size=16, weight=ft.FontWeight.BOLD, color=FOOD_GREEN)

    def food_field(label, **kw):
        return ft.TextField(
            label=label, color=FOOD_TEXT, cursor_color=FOOD_GREEN,
            label_style=ft.TextStyle(color=FOOD_GREEN),
            border_color=FOOD_GREEN, focused_border_color=FOOD_GREEN, **kw)

    def confirm(title, text, on_yes):
        def yes(e):
            page.pop_dialog()
            on_yes()
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text(title), content=ft.Text(text),
            actions=[ft.TextButton(content="Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.TextButton(content="Delete", on_click=yes)],
        )
        page.show_dialog(dlg)

    def edit_workout_dialog(w):
        """Pop-up editor for one exercise: name, sets, reps, weight, notes and day."""
        name = ft.TextField(label="Exercise name", value=w["name"])
        sets = ft.TextField(label="Sets", value=str(w["sets"] or ""), expand=1,
                            keyboard_type=ft.KeyboardType.NUMBER)
        reps = ft.TextField(label="Reps", value=str(w["reps"] or ""), expand=1,
                            keyboard_type=ft.KeyboardType.NUMBER)
        weight = ft.TextField(label="Weight (kg)", value=w.get("weight") or "", expand=1)
        notes = ft.TextField(label="Notes (optional)", value=w.get("notes") or "")
        day_dd = ft.Dropdown(
            label="Day", value=str(w["day"]),
            options=[ft.DropdownOption(key=str(k), text=f"Day {k} – {t}") for k, t in db.PLAN_DAYS.items()])

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
            modal=True, title=ft.Text("Edit exercise"),
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

    def toggle_food(day, fid):
        dr = ensure_draft()
        dr["f"].symmetric_difference_update({fid})
        render()

    def toggle_work(day, wid):
        dr = ensure_draft()
        dr["w"].symmetric_difference_update({wid})
        render()

    def select_plan_day(k):
        st["plan_day"] = k
        ensure_draft()["w"] = set()
        render()

    # Foods and workouts are saved separately, so a rest day can save just the foods.
    def save_foods(e):
        dr = ensure_draft()
        db.set_foods(today.isoformat(), sorted(dr["f"]))
        render()
        toast("Foods saved to calendar")

    def save_workouts(e):
        dr = ensure_draft()
        db.set_workouts(today.isoformat(), sorted(dr["w"]))
        render()
        toast("Workout saved to calendar" if dr["w"] else "Rest day saved (no workout)")

    # ---------- shared: one day's food + workout checklist ----------
    def day_panel(day, title):
        foods, works = db.foods(), db.workouts(st["plan_day"])
        dr = ensure_draft()
        eaten_ids, done_ids = dr["f"], dr["w"]
        saved_f, saved_w = db.day_log(day.isoformat())
        unsaved_f = saved_f != dr["f"]
        unsaved_w = saved_w != dr["w"]
        eaten_cal = sum(f["cal"] for f in foods if f["id"] in eaten_ids)
        plan_cal = sum(f["cal"] for f in foods)

        food_rows = [ft.Row([
            ft.Checkbox(label=f["name"], value=f["id"] in eaten_ids, expand=True,
                        active_color=FOOD_GREEN, check_color="#000000",
                        label_style=ft.TextStyle(color=FOOD_TEXT),
                        on_change=lambda e, fid=f["id"]: toggle_food(day, fid)),
            ft.Text(f"{f['cal']} kcal", color=FOOD_GREEN)])
            for f in foods] or [ft.Text("No foods yet. Add them in the Foods tab.", color=FOOD_MUTED)]
        work_rows = [ft.Row([
            ft.Checkbox(
                label=ft.Text(w["name"] + (f"   ({db.describe(w)})" if db.describe(w) else "")),
                value=w["id"] in done_ids, expand=True,
                on_change=lambda e, wid=w["id"]: toggle_work(day, wid)),
            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, tooltip="Edit sets / reps / weight",
                          on_click=lambda e, w=w: edit_workout_dialog(w))])
            for w in works] or [ft.Text("No workouts on this day. Add some in the Workouts tab.")]
        day_buttons = ft.Row([
            ft.Button(content=f"Day {k}", on_click=lambda e, k=k: select_plan_day(k),
                      bgcolor=BLUE if k == st["plan_day"] else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                      color=ft.Colors.WHITE if k == st["plan_day"] else ft.Colors.ON_SURFACE,
                      expand=1)
            for k in db.PLAN_DAYS], spacing=6)

        def status(unsaved):
            # only warn when there are unsaved changes; nothing is shown once saved
            if not unsaved:
                return ft.Container(height=0)
            return ft.Text("Not saved yet.", size=12, color=ft.Colors.AMBER,
                           text_align=ft.TextAlign.CENTER)

        return [
            food_card(food_heading(title), *food_rows,
                      ft.Row([ft.Text("Eaten", weight=ft.FontWeight.BOLD, color=FOOD_TEXT),
                              ft.Text(f"{eaten_cal} / {plan_cal} kcal", weight=ft.FontWeight.BOLD,
                                      color=FOOD_GREEN)],
                             alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
            ft.Button(content="Save foods", icon=ft.Icons.SAVE, on_click=save_foods,
                      bgcolor=FOOD_GREEN, color="#000000", height=48),
            status(unsaved_f),
            card(heading("Workout day"), day_buttons,
                 ft.Text(f"Day {st['plan_day']} – {db.PLAN_DAYS[st['plan_day']]}",
                         weight=ft.FontWeight.BOLD, color=BLUE),
                 *work_rows),
            ft.Button(content="Save workout", icon=ft.Icons.SAVE, on_click=save_workouts,
                      bgcolor=BLUE, color=ft.Colors.WHITE, height=48),
            status(unsaved_w),
        ]

    # ---------- TODAY tab ----------
    def today_tab():
        streak = db.streak()
        return [
            ft.Text("Today", size=26, weight=ft.FontWeight.BOLD),
            ft.Text(today.strftime("%A, %d %B %Y") + (f"   🔥 {streak}-day streak" if streak else ""),
                    color=ft.Colors.ON_SURFACE_VARIANT),
            *day_panel(today, "Meals"),
        ]

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
        kcal = sum(f["cal"] for f in eaten)

        def line(icon_color, left, right=""):
            return ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=icon_color, size=20),
                           ft.Text(left, expand=True),
                           ft.Text(right, color=ft.Colors.ON_SURFACE_VARIANT)])

        food_lines = [line(FOOD_GREEN, f["name"], f"{f['cal']} kcal") for f in eaten] or [
            ft.Text("No foods ticked", color=ft.Colors.ON_SURFACE_VARIANT)]
        work_lines = []
        for k in sorted({w["day"] for w in done}):
            work_lines.append(ft.Text(f"Day {k} – {db.PLAN_DAYS.get(k, '')}", size=12,
                                      color=ft.Colors.ON_SURFACE_VARIANT))
            work_lines += [line(BLUE, w["name"], db.describe(w)) for w in done if w["day"] == k]
        if not work_lines:
            work_lines = [ft.Text("No workouts done", color=ft.Colors.ON_SURFACE_VARIANT)]
        sheet = ft.BottomSheet(ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text(d.strftime("%A, %d %B %Y"), size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Foods eaten", weight=ft.FontWeight.BOLD, color=FOOD_GREEN),
                *food_lines,
                ft.Text(f"Total: {kcal} kcal", weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Workouts done", weight=ft.FontWeight.BOLD, color=BLUE),
                *work_lines,
                ft.Row([ft.TextButton(content="Close", on_click=lambda e: page.pop_dialog())],
                       alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=8, scroll=ft.ScrollMode.AUTO)))
        page.show_dialog(sheet)

    def pick(d):
        st["sel"] = d
        render()
        show_day(d)

    def dot(color):
        return ft.Container(width=5, height=5, border_radius=3, bgcolor=color)

    def day_cell(d, summary, total_foods):
        if d == 0:
            return ft.Container(expand=1, height=54)
        this = date(st["year"], st["month"], d)
        future = this > today
        selected = this == st["sel"]
        eaten, worked = summary.get(d, (0, 0))

        if selected:
            txt = ft.Text(str(d), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        elif future:
            txt = ft.Text(str(d), size=16, color=ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE))
        else:
            txt = ft.Text(str(d), size=16)
        circle = ft.Container(
            content=txt, width=38, height=38, border_radius=19,
            bgcolor=BLUE if selected else None,
            border=ft.Border.all(1.5, BLUE) if (this == today and not selected) else None,
            alignment=ft.Alignment.CENTER,
        )
        food_color = None
        if total_foods and eaten >= total_foods:
            food_color = GREEN
        elif eaten > 0:
            food_color = ft.Colors.AMBER
        dots = ft.Row([dot(food_color), dot(ft.Colors.BLUE_300 if worked else None)],
                      spacing=3, alignment=ft.MainAxisAlignment.CENTER)
        return ft.Container(
            content=ft.Column([circle, dots], spacing=2,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=1, height=54,
            on_click=None if future else (lambda e, this=this: pick(this)),
        )

    def history_tab():
        foods = db.foods()
        summary = db.month_summary(st["year"], st["month"])

        top = ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: set_tab(0)),
            ft.Text("History", size=22, weight=ft.FontWeight.BOLD)])
        month_row = ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_LEFT, icon_color=ft.Colors.ON_SURFACE_VARIANT,
                          on_click=lambda e: shift_month(-1)),
            ft.Text(f"{st['year']}/{st['month']:02d}", size=18, weight=ft.FontWeight.BOLD,
                    expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.ARROW_RIGHT, icon_color=ft.Colors.ON_SURFACE_VARIANT,
                          on_click=lambda e: shift_month(1)),
        ])
        weekdays = ft.Row([ft.Text(w, expand=1, text_align=ft.TextAlign.CENTER, size=14,
                                   weight=ft.FontWeight.W_500)
                           for w in ["S", "M", "T", "W", "T", "F", "S"]])
        weeks = [ft.Row([day_cell(d, summary, len(foods)) for d in wk], spacing=0)
                 for wk in pycal.Calendar(firstweekday=6).monthdayscalendar(st["year"], st["month"])]
        legend = ft.Text("Tap a date to see what you ate and did. Green dot = all foods · Yellow = some · Blue = workout",
                         size=12, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER)

        return [top, month_row, weekdays, *weeks, legend]

    # ---------- FOODS tab (black + green) ----------
    def foods_tab():
        editing = next((f for f in db.foods() if f["id"] == st["edit_food"]), None)
        name = food_field("Food name", value=editing["name"] if editing else "")
        cal = food_field("Calories", keyboard_type=ft.KeyboardType.NUMBER,
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

        buttons = [ft.Button(content="Save" if editing else "Add food", on_click=save,
                             bgcolor=FOOD_GREEN, color="#000000")]
        if editing:
            buttons.append(ft.TextButton(content="Cancel", on_click=cancel,
                                         style=ft.ButtonStyle(color=FOOD_GREEN)))

        def edit(fid):
            st["edit_food"] = fid
            render()

        def remove(f):
            confirm("Delete food?", f"Delete '{f['name']}' and its history?",
                    lambda: (db.delete_food(f["id"]), render()))

        foods = db.foods()
        rows = [ft.Row([
            ft.Column([ft.Text(f["name"], color=FOOD_TEXT),
                       ft.Text(f"{f['cal']} kcal", size=12, color=FOOD_GREEN)],
                      spacing=0, expand=True),
            ft.IconButton(icon=ft.Icons.EDIT, icon_color=FOOD_GREEN,
                          on_click=lambda e, fid=f["id"]: edit(fid)),
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=FOOD_MUTED,
                          on_click=lambda e, f=f: remove(f))])
            for f in foods] or [ft.Text("Nothing yet.", color=FOOD_MUTED)]
        panel = ft.Container(
            content=ft.Column([
                ft.Text("Foods", size=26, weight=ft.FontWeight.BOLD, color=FOOD_TEXT),
                food_card(food_heading("Edit food" if editing else "Add food"), name, cal,
                          ft.Row(buttons)),
                food_card(food_heading("Your foods"), *rows,
                          ft.Row([ft.Text("Daily total", weight=ft.FontWeight.BOLD, color=FOOD_TEXT),
                                  ft.Text(f"{sum(f['cal'] for f in foods)} kcal",
                                          weight=ft.FontWeight.BOLD, color=FOOD_GREEN)],
                                 alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            bgcolor=FOOD_BG, padding=14, border_radius=20,
        )
        return [panel]

    # ---------- WORKOUTS tab ----------
    def workouts_tab():
        name = ft.TextField(label="Workout name (e.g. Squats)")
        sets = ft.TextField(label="Sets", keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        reps = ft.TextField(label="Reps", keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        weight = ft.TextField(label="Weight (kg)", expand=1)
        notes = ft.TextField(label="Notes (optional)")
        day_dd = ft.Dropdown(
            label="Add to day", value=str(st["add_day"]),
            options=[ft.DropdownOption(key=str(k), text=f"Day {k} – {t}") for k, t in db.PLAN_DAYS.items()])

        def add(e):
            n = name.value.strip()
            if not n:
                toast("Enter a workout name")
                return
            for val in (sets.value, reps.value):
                if (val or "").strip() and not (val or "").strip().isdigit():
                    toast("Sets and reps must be numbers")
                    return
            day = int(day_dd.value or st["add_day"])
            db.add_workout(n, sets.value, reps.value, weight.value, notes.value, day)
            st["add_day"] = day
            render()

        def remove(w):
            confirm("Delete workout?", f"Delete '{w['name']}' and its history?",
                    lambda: (db.delete_workout(w["id"]), render()))

        everything = db.workouts()
        day_cards = []
        for k, title in db.PLAN_DAYS.items():
            rows = [ft.Row([
                ft.Column([ft.Text(w["name"]),
                           ft.Text(db.describe(w), size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                          spacing=0, expand=True),
                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit",
                              on_click=lambda e, w=w: edit_workout_dialog(w)),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e, w=w: remove(w))])
                for w in everything if w["day"] == k] or [ft.Text("Nothing yet.")]
            day_cards.append(card(heading(f"Day {k} – {title}"), *rows))
        return [
            card(heading("Add custom workout"), name, ft.Row([sets, reps, weight], spacing=8),
                 notes, day_dd, ft.Row([ft.Button(content="Add workout", on_click=add)])),
            *day_cards,
        ]

    # ---------- MORE tab ----------
    def more_tab():
        path_field = ft.TextField(label="Backup file path to import", hint_text=db.backup_path())

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
            render()
            toast("Imported")

        def do_reset():
            db.reset_all()
            render()

        return [
            card(heading("Backup"),
                 ft.Text("Your data is stored on this device only.", size=12,
                         color=ft.Colors.ON_SURFACE_VARIANT),
                 ft.Button(content="Export backup", on_click=do_export),
                 path_field, ft.Button(content="Import backup", on_click=do_import)),
            card(heading("Reset"),
                 ft.TextButton(content="Delete all data",
                               on_click=lambda e: confirm("Delete everything?",
                                                          "This cannot be undone.", do_reset))),
        ]

    # ---------- shell ----------
    tabs = [today_tab, history_tab, foods_tab, workouts_tab, more_tab]

    def render():
        body.controls = tabs[st["tab"]]()
        page.navigation_bar.selected_index = st["tab"]
        page.update()

    def set_tab(i):
        st["tab"] = i
        render()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.TODAY, label="Today"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="History"),
            ft.NavigationBarDestination(icon=ft.Icons.RESTAURANT, label="Foods"),
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER, label="Workouts"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="More"),
        ],
        on_change=lambda e: set_tab(e.control.selected_index),
    )
    page.add(ft.SafeArea(
        expand=True,
        content=ft.Container(content=body, padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                             expand=True)))
    render()


if __name__ == "__main__":
    ft.run(main)