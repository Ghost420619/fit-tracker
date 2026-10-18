"""FitTracker data layer: plain sqlite3, no dependencies. Used by main.py."""
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta

PATH = None

# Default foods (name, kcal). Calories are estimates; edit them in the Foods tab.
DEFAULT_FOODS = [
    ("Egg (2)", 155),
    ("Yogurt", 100),
    ("Chola (50 gm)", 180),
    ("Almond (2)", 14),
    ("Cashew Nuts (2)", 18),
    ("Chicken", 280),
    ("Honey nuts", 100),
]
# The 4-day plan. Day numbers are fixed; each workout belongs to one day.
PLAN_DAYS = {
    1: "Push (Chest + Biceps + Shoulders)",
    2: "Pull (Back + Forearms + Triceps)",
    3: "Legs + Forearm",
    4: "Push (Shoulder + Back)",
}

PLAN_V1 = {
    1: [("Push-ups", "3 sets x 10"),
        ("Chest press", "3 x 10 (30kg)"),
        ("Butterfly", "3 sets x 10"),
        ("Barbell curl", "3 sets x 10 (10 kg)"),
        ("Dumbbell curl", "3 x 10"),
        ("Hammer Curl", "3 sets x 10"),
        ("Wide shoulder", "3 x 10")],
    2: [("Pull-ups", "3 sets x 10 (or assisted if needed)"),
        ("Reverse Weight curl", "3 x 10"),
        ("Wrist Curls", "3 sets x 15"),
        ("Reverse wrist curl (forearm)", "3 sets x 12"),
        ("Reverse weight wrist curl", "3 x 15"),
        ("Triceps", "3 sets x 10"),
        ("Literal rise", "3 x 10")],
    3: [("Squats", "40"),
        ("Sit ups", "40"),
        ("Legs", "4 sets x 10 each leg (15kg)"),
        ("Wrist Curl (forearm)", "3 sets x 15"),
        ("Reverse Wrist Curl (forearm)", "3 sets x 12"),
        ("Reverse weight wrist curl", "3 x 10"),
        ("Dumbbell spin", "70-70")],
    4: [("Shoulder Press", "3 sets x 10"),
        ("Lat pulldown", "3 sets x 10"),
        ("Biceps weight 10 kg", "3 sets x 10"),
        ("Sitted Wide shoulder", "3 x 10"),
        ("Reverse Weight curl", "3 x 10"),
        ("Dumbbell bench press", "3 x 10"),
        ("Assisted dips", "3 x 10")],
}


def _default_path():
    base = os.getenv("FLET_APP_STORAGE_DATA") or os.path.join(os.path.expanduser("~"), ".fittracker")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "fittracker.db")


def _conn():
    c = sqlite3.connect(PATH)
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    return c


def init(path=None):
    """Create tables, migrate older databases, and load starter data once."""
    global PATH
    PATH = path or _default_path()
    with closing(_conn()) as c, c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS foods(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, cal INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS workouts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                sets INTEGER NOT NULL DEFAULT 0, reps INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                day INTEGER NOT NULL DEFAULT 1, detail TEXT NOT NULL DEFAULT '',
                weight TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS food_log(
                day TEXT NOT NULL, food_id INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
                PRIMARY KEY(day, food_id));
            CREATE TABLE IF NOT EXISTS workout_log(
                day TEXT NOT NULL, workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
                PRIMARY KEY(day, workout_id));
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
            """
        )
        # migrate databases created by the first version (no day/detail columns)
        cols = {r[1] for r in c.execute("PRAGMA table_info(workouts)")}
        if "day" not in cols:
            c.execute("ALTER TABLE workouts ADD COLUMN day INTEGER NOT NULL DEFAULT 1")
        if "detail" not in cols:
            c.execute("ALTER TABLE workouts ADD COLUMN detail TEXT NOT NULL DEFAULT ''")
        if "weight" not in cols:
            c.execute("ALTER TABLE workouts ADD COLUMN weight TEXT NOT NULL DEFAULT ''")

        # Foods: the app's only default foods are DEFAULT_FOODS. Any database that has not
        # been through this step yet (new, old, or from an earlier version of this code)
        # has all its foods removed and replaced once.
        if not c.execute("SELECT 1 FROM meta WHERE k='foods_v3'").fetchone():
            c.execute("DELETE FROM foods")
            c.executemany("INSERT INTO foods(name, cal) VALUES(?,?)", DEFAULT_FOODS)
            c.execute("INSERT OR REPLACE INTO meta VALUES('seeded','1')")
            c.execute("INSERT OR REPLACE INTO meta VALUES('foods_v3','1')")

        if not c.execute("SELECT 1 FROM meta WHERE k='plan_v1'").fetchone():
            # the old starter "Push-ups 3x15" becomes Day 1's Push-ups (keeps its history)
            old = c.execute("SELECT id FROM workouts WHERE name='Push-ups' AND sets=3 AND reps=15 "
                            "AND COALESCE(notes,'')='' AND detail='' LIMIT 1").fetchone()
            for day, items in PLAN_V1.items():
                for i, (name, detail) in enumerate(items):
                    if day == 1 and i == 0 and old:
                        c.execute("UPDATE workouts SET sets=0, reps=0, day=1, detail=? WHERE id=?",
                                  (detail, old["id"]))
                    else:
                        c.execute("INSERT INTO workouts(name, sets, reps, notes, day, detail) "
                                  "VALUES(?,0,0,'',?,?)", (name, day, detail))
            c.execute("INSERT INTO meta VALUES('plan_v1','1')")

        if not c.execute("SELECT 1 FROM meta WHERE k='plan_split'").fetchone():
            for r in c.execute("SELECT id, detail, notes FROM workouts WHERE detail<>'' "
                               "AND sets=0 AND reps=0 AND weight=''").fetchall():
                sets, reps, weight, note = _split_detail(r["detail"])
                note = " · ".join(x for x in ((r["notes"] or "").strip(), note) if x)
                c.execute("UPDATE workouts SET sets=?, reps=?, weight=?, notes=?, detail='' WHERE id=?",
                          (sets, reps, weight, note, r["id"]))
            c.execute("INSERT INTO meta VALUES('plan_split','1')")


def _num(v):
    v = str(v if v is not None else "").strip()
    return int(v) if v.isdigit() else 0


def _split_detail(detail):
    """'3 sets x 10 (30kg)' -> (3, 10, '30', ''). Anything unrecognised goes to notes."""
    d = (detail or "").strip()
    m = re.match(r"^(\d+)\s*(?:sets?)?\s*x\s*(\d+)\s*(.*)$", d, re.I)
    if m:
        sets, reps, rest = int(m.group(1)), int(m.group(2)), m.group(3)
        weight = ""
        w = re.search(r"(\d+(?:\.\d+)?)\s*kg", rest, re.I)
        if w:
            weight = w.group(1)
            rest = rest[:w.start()] + rest[w.end():]
        note = re.sub(r"[()]", " ", rest)
        return sets, reps, weight, " ".join(note.split())
    if d.isdigit():
        return 0, int(d), "", ""
    return 0, 0, "", d


def describe(w):
    """Short text shown next to a workout (sets x reps, weight, notes)."""
    sets, reps = w.get("sets") or 0, w.get("reps") or 0
    weight = (w.get("weight") or "").strip()
    parts = []
    if sets and reps:
        parts.append(f"{sets} x {reps}")
    elif sets:
        parts.append(f"{sets} sets")
    elif reps:
        parts.append(f"{reps} reps")
    if weight:
        parts.append(weight if not weight[-1].isdigit() else weight + " kg")
    text = " · ".join(parts)
    if (w.get("notes") or "").strip():
        text = (text + " · " if text else "") + w["notes"].strip()
    return text or (w.get("detail") or "")


# ---------- foods ----------
def foods():
    with closing(_conn()) as c:
        return [dict(r) for r in c.execute("SELECT * FROM foods ORDER BY id")]


def add_food(name, cal):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO foods(name, cal) VALUES(?,?)", (name.strip(), int(cal)))


def update_food(fid, name, cal):
    with closing(_conn()) as c, c:
        c.execute("UPDATE foods SET name=?, cal=? WHERE id=?", (name.strip(), int(cal), fid))


def delete_food(fid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM foods WHERE id=?", (fid,))


# ---------- workouts ----------
def workouts(day=None):
    """All workouts ordered by plan day, or only one day's."""
    with closing(_conn()) as c:
        if day is None:
            rows = c.execute("SELECT * FROM workouts ORDER BY day, id")
        else:
            rows = c.execute("SELECT * FROM workouts WHERE day=? ORDER BY id", (int(day),))
        return [dict(r) for r in rows]


def add_workout(name, sets, reps, weight, notes, day):
    if int(day) not in PLAN_DAYS:
        raise ValueError("day must be 1-4")
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO workouts(name, sets, reps, weight, notes, day, detail) "
                  "VALUES(?,?,?,?,?,?,'')",
                  (name.strip(), _num(sets), _num(reps), str(weight or "").strip(),
                   str(notes or "").strip(), int(day)))


def update_workout(wid, name, sets, reps, weight, notes, day):
    if int(day) not in PLAN_DAYS:
        raise ValueError("day must be 1-4")
    with closing(_conn()) as c, c:
        c.execute("UPDATE workouts SET name=?, sets=?, reps=?, weight=?, notes=?, day=?, detail='' "
                  "WHERE id=?",
                  (name.strip(), _num(sets), _num(reps), str(weight or "").strip(),
                   str(notes or "").strip(), int(day), wid))


def delete_workout(wid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM workouts WHERE id=?", (wid,))


# ---------- daily log ----------
def day_log(day):
    """Return (set of eaten food ids, set of done workout ids) for an ISO date string."""
    with closing(_conn()) as c:
        f = {r[0] for r in c.execute("SELECT food_id FROM food_log WHERE day=?", (day,))}
        w = {r[0] for r in c.execute("SELECT workout_id FROM workout_log WHERE day=?", (day,))}
    return f, w


def set_day(day, food_ids, workout_ids):
    """Replace everything logged for a day with exactly these foods/workouts (used by Save)."""
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM food_log WHERE day=?", (day,))
        c.execute("DELETE FROM workout_log WHERE day=?", (day,))
        c.executemany("INSERT INTO food_log(day, food_id) VALUES(?,?)", [(day, i) for i in food_ids])
        c.executemany("INSERT INTO workout_log(day, workout_id) VALUES(?,?)", [(day, i) for i in workout_ids])


def set_foods(day, food_ids):
    """Replace only the foods logged for a day (workouts for that day are left alone)."""
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM food_log WHERE day=?", (day,))
        c.executemany("INSERT INTO food_log(day, food_id) VALUES(?,?)", [(day, i) for i in food_ids])


def set_workouts(day, workout_ids):
    """Replace only the workouts logged for a day (foods for that day are left alone).
    An empty list = rest day, no workout recorded."""
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM workout_log WHERE day=?", (day,))
        c.executemany("INSERT INTO workout_log(day, workout_id) VALUES(?,?)",
                      [(day, i) for i in workout_ids])


def suggest_day(today=None):
    """Which plan day to show: today's saved day, else the day after the last one you trained, else Day 1."""
    today = (today or date.today()).isoformat()
    with closing(_conn()) as c:
        r = c.execute("SELECT w.day FROM workout_log l JOIN workouts w ON w.id=l.workout_id "
                      "WHERE l.day=? GROUP BY w.day ORDER BY COUNT(*) DESC LIMIT 1", (today,)).fetchone()
        if r:
            return r["day"]
        r = c.execute("SELECT l.day d FROM workout_log l WHERE l.day<? ORDER BY l.day DESC LIMIT 1",
                      (today,)).fetchone()
        if r:
            r2 = c.execute("SELECT w.day FROM workout_log l JOIN workouts w ON w.id=l.workout_id "
                           "WHERE l.day=? GROUP BY w.day ORDER BY COUNT(*) DESC LIMIT 1", (r["d"],)).fetchone()
            if r2:
                return r2["day"] % len(PLAN_DAYS) + 1
    return 1


def month_summary(year, month):
    """{day_number: (foods_eaten, workouts_done)} for days that have any activity."""
    prefix = f"{year:04d}-{month:02d}-"
    out = {}
    with closing(_conn()) as c:
        for r in c.execute("SELECT day, COUNT(*) n FROM food_log WHERE day LIKE ? GROUP BY day", (prefix + "%",)):
            out[int(r["day"][8:])] = [r["n"], 0]
        for r in c.execute("SELECT day, COUNT(*) n FROM workout_log WHERE day LIKE ? GROUP BY day", (prefix + "%",)):
            out.setdefault(int(r["day"][8:]), [0, 0])[1] = r["n"]
    return {k: tuple(v) for k, v in out.items()}


def streak(today=None):
    """Consecutive days (ending today, or yesterday if today isn't done yet) with every food eaten."""
    today = today or date.today()
    with closing(_conn()) as c:
        total = c.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
        if total == 0:
            return 0
        full = {r[0] for r in c.execute(
            "SELECT day FROM food_log GROUP BY day HAVING COUNT(*) = ?", (total,))}
    d = today if today.isoformat() in full else today - timedelta(days=1)
    n = 0
    while d.isoformat() in full:
        n += 1
        d -= timedelta(days=1)
    return n


# ---------- backup ----------
def export_json(path):
    with closing(_conn()) as c:
        payload = {
            "foods": [dict(r) for r in c.execute("SELECT * FROM foods")],
            "workouts": [dict(r) for r in c.execute("SELECT * FROM workouts")],
            "food_log": [dict(r) for r in c.execute("SELECT * FROM food_log")],
            "workout_log": [dict(r) for r in c.execute("SELECT * FROM workout_log")],
        }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def import_json(path):
    with open(path, encoding="utf-8") as fh:
        p = json.load(fh)
    for k in ("foods", "workouts", "food_log", "workout_log"):
        if not isinstance(p.get(k), list):
            raise ValueError("Not a FitTracker backup file")
    works = []
    for w in p["workouts"]:
        sets, reps = _num(w.get("sets", 0)), _num(w.get("reps", 0))
        weight, notes = str(w.get("weight", "") or ""), w.get("notes", "") or ""
        detail = w.get("detail", "") or ""
        if detail and not (sets or reps or weight):
            sets, reps, weight, note = _split_detail(detail)
            notes = " · ".join(x for x in (notes.strip(), note) if x)
            detail = ""
        works.append({"id": w["id"], "name": w["name"], "sets": sets, "reps": reps, "weight": weight,
                      "notes": notes, "day": w.get("day", 1), "detail": detail})
    with closing(_conn()) as c, c:
        for t in ("food_log", "workout_log", "foods", "workouts"):
            c.execute(f"DELETE FROM {t}")
        c.executemany("INSERT INTO foods(id,name,cal) VALUES(:id,:name,:cal)", p["foods"])
        c.executemany("INSERT INTO workouts(id,name,sets,reps,weight,notes,day,detail) "
                      "VALUES(:id,:name,:sets,:reps,:weight,:notes,:day,:detail)", works)
        c.executemany("INSERT INTO food_log(day,food_id) VALUES(:day,:food_id)", p["food_log"])
        c.executemany("INSERT INTO workout_log(day,workout_id) VALUES(:day,:workout_id)", p["workout_log"])


def reset_all():
    with closing(_conn()) as c, c:
        for t in ("food_log", "workout_log", "foods", "workouts"):
            c.execute(f"DELETE FROM {t}")


def backup_path():
    return os.path.join(os.path.dirname(PATH), f"fittracker-backup-{date.today().isoformat()}.json")
