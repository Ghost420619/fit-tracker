# FitTracker (Python + Flet)

Food checklist + calorie counter, calendar, and custom workouts. Data is stored locally in SQLite.

## Run on PC (fastest)
```
pip install "flet>=1.0.4"
python main.py
```

## Build a real app
Run these inside this folder.

**Android APK** (installs on your phone):
```
flet build apk
```
Output: `build/apk/`. Copy the .apk to your phone and install it (allow "install unknown apps").
First build downloads Flutter and Android tools automatically, so it is slow and large.

**Windows app (.exe):**
```
flet build windows
```
Needs Visual Studio 2022 with the "Desktop development with C++" workload installed.
Output: `build/windows/`.

If a build fails, copy the error message and send it to me.

## Files
- `main.py`: the UI (4 tabs: Calendar, Foods, Workouts, More)
- `data.py`: database code (SQLite, no extra packages)
- `pyproject.toml`: app name and build settings

## Notes
- Calendar: tap a day, tick the foods you ate and workouts you did.
  Green = all foods eaten, yellow = some, blue dot = workout done.
- Backups: More tab -> Export backup saves a .json file next to the database.
  Import by typing that file's path.
- Phone and PC data are separate (no cloud sync, so it stays 100% free).
