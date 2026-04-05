"""
Holmes Place Israel - Auto Class Registration Bot
=================================================
Automatically registers to a gym class exactly when registration opens.

Setup:
    pip install requests beautifulsoup4

Usage:
    python holmes_register.py
"""

import requests
import time
import datetime
import json
import sys
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  CONFIG - Edit these values
# ─────────────────────────────────────────────
PHONE       = "0504014640"
PASSWORD    = "romi2008"
CLUB_URL    = "https://www.holmesplace.co.il/club-page-modiin/"  # סניף מודיעין

# השיעור שרוצים להירשם אליו:
TARGET_LESSON_NAME = "חדר כושר"   # חלק משם השיעור (חלקי)
TARGET_LESSON_DATE = "2026/4/6"   # תאריך השיעור: YYYY/M/D
TARGET_LESSON_TIME = "140000"     # שעת השיעור: HHMMSS  (14:00 = "140000")

# מתי ההרשמה נפתחת (היום, שעה 14:00):
REGISTRATION_OPENS = datetime.datetime(2026, 4, 5, 14, 0, 0)

# כמה שניות לפני פתיחת ההרשמה להתחיל לנסות
EARLY_START_SECONDS = 4

# ─────────────────────────────────────────────
BASE_URL = "https://www.holmesplace.co.il"
SESSION  = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": CLUB_URL,
})


def login():
    resp = SESSION.post(
        f"{BASE_URL}/api.php?action=login",
        data={"phone": PHONE, "password": PASSWORD},
        timeout=10
    )
    try:
        data = json.loads(resp.text)
    except Exception:
        print(f"[!] שגיאת Login: {resp.text[:200]}")
        return False
    if data.get("success"):
        print("[+] התחברות הצליחה!")
        return True
    else:
        print(f"[!] התחברות נכשלה: {data.get('error', data)}")
        return False


def get_lessons():
    """Scrape club page, return (branch_id, lessons_list)."""
    resp = SESSION.get(CLUB_URL, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    club_id_input = soup.find("input", {"id": "club_id"})
    if not club_id_input:
        print("[!] לא נמצא club_id בדף")
        sys.exit(1)
    branch_id = club_id_input["value"]

    lessons = []
    for el in soup.find_all(attrs={"data-lessonid": True}):
        lessons.append({
            "lessonid":    el.get("data-lessonid"),
            "date":        el.get("data-date"),
            "time":        el.get("data-time"),
            "instruction": el.get("data-instruction", "0"),
            "lessonname":  el.get("data-lessonname", ""),
            "location":    el.get("data-location", ""),
            "teacher":     el.get("data-teacher", ""),
        })
    return branch_id, lessons


def find_lesson(lessons):
    return [
        l for l in lessons
        if TARGET_LESSON_NAME in l["lessonname"]
        and l["date"] == TARGET_LESSON_DATE
        and l["time"] == TARGET_LESSON_TIME
    ]


def register(branch_id, lesson):
    print(f"[*] שולח בקשת הרשמה: {lesson['lessonname']} | {lesson['date']} {lesson['time'][:2]}:{lesson['time'][2:4]}")
    resp = SESSION.post(
        f"{BASE_URL}/api.php?action=registerToLesson",
        data={
            "branchID":    branch_id,
            "lessonID":    lesson["lessonid"],
            "date":        lesson["date"],
            "time":        lesson["time"],
            "instructorID": lesson["instruction"],
        },
        timeout=10
    )
    try:
        return json.loads(resp.text)
    except Exception:
        return {"raw": resp.text}


def register_waitlist(branch_id, lesson):
    resp = SESSION.post(
        f"{BASE_URL}/api.php?action=registerToWaitList",
        data={
            "branchID":    branch_id,
            "lessonID":    lesson["lessonid"],
            "date":        lesson["date"],
            "time":        lesson["time"],
            "instructorID": lesson["instruction"],
        },
        timeout=10
    )
    try:
        return json.loads(resp.text)
    except Exception:
        return {"raw": resp.text}


def wait_until(target_dt):
    """Sleep until target_dt, printing countdowns."""
    while True:
        remaining = (target_dt - datetime.datetime.now()).total_seconds()
        if remaining <= 0:
            return
        if remaining > 3600:
            time.sleep(300)
            r2 = (target_dt - datetime.datetime.now()).total_seconds()
            print(f"    נשארו: {r2/3600:.1f} שעות")
        elif remaining > 60:
            time.sleep(20)
            r2 = (target_dt - datetime.datetime.now()).total_seconds()
            print(f"    נשארו: {r2:.0f} שניות ({r2/60:.1f} דקות)")
        else:
            time.sleep(0.5)


def main():
    print("=" * 55)
    print("  Holmes Place - Auto Registration Bot")
    print("=" * 55)
    print(f"  שיעור:     {TARGET_LESSON_NAME} | {TARGET_LESSON_DATE} {TARGET_LESSON_TIME[:2]}:{TARGET_LESSON_TIME[2:4]}")
    print(f"  הרשמה ב:   {REGISTRATION_OPENS.strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)

    # 1. Wait until just before registration opens
    start_at = REGISTRATION_OPENS - datetime.timedelta(seconds=EARLY_START_SECONDS)
    now = datetime.datetime.now()
    if (start_at - now).total_seconds() > 0:
        print(f"\n[*] ממתין עד {start_at.strftime('%H:%M:%S')}...")
        wait_until(start_at)

    # 2. Login
    print("\n[*] מתחבר...")
    if not login():
        sys.exit(1)

    # 3. Fetch page and find lesson - retry until found (max 60 seconds)
    print(f"[*] מחפש את השיעור בדף הסניף...")
    branch_id = None
    lesson = None
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=60)

    while datetime.datetime.now() < deadline:
        branch_id, lessons = get_lessons()
        matches = find_lesson(lessons)
        if matches:
            lesson = matches[0]
            print(f"[+] שיעור נמצא: {lesson['lessonname']} | {lesson['location']}")
            break
        else:
            # Show what IS available for the target date
            date_lessons = [l for l in lessons if l["date"] == TARGET_LESSON_DATE]
            if date_lessons:
                names = [f"{l['time'][:2]}:{l['time'][2:4]} {l['lessonname']}" for l in date_lessons]
                print(f"    שיעורים שנמצאו ל-{TARGET_LESSON_DATE}: {', '.join(names)}")
            else:
                print(f"    אין שיעורים ל-{TARGET_LESSON_DATE} עדיין...")
            time.sleep(1)

    if not lesson:
        print(f"\n[!] לא נמצא '{TARGET_LESSON_NAME}' ב-{TARGET_LESSON_DATE} בשעה {TARGET_LESSON_TIME[:2]}:{TARGET_LESSON_TIME[2:4]} תוך 60 שניות.")
        print("    ייתכן שהשם שגוי או שהשיעור לא קיים. הנה כל השיעורים הזמינים:")
        _, all_lessons = get_lessons()
        for l in sorted(all_lessons, key=lambda x: (x["date"], x["time"])):
            t = l["time"].zfill(6)
            print(f"    {l['date']}  {t[:2]}:{t[2:4]}  |  {l['lessonname']}")
        sys.exit(1)

    # 4. Register - retry up to 15 times
    for attempt in range(1, 16):
        result = register(branch_id, lesson)
        print(f"    ניסיון {attempt}: {result}")

        if result.get("success"):
            print("\n[+] ✓ נרשמת בהצלחה!")
            sys.exit(0)

        err = str(result.get("error", ""))
        if "מלא" in err or "full" in err.lower():
            print("[!] השיעור מלא - מנסה להירשם לרשימת המתנה...")
            r2 = register_waitlist(branch_id, lesson)
            if r2.get("success"):
                print("[+] נרשמת לרשימת המתנה!")
            else:
                print(f"    רשימת המתנה: {r2}")
            sys.exit(0)
        elif "לא פתוחה" in err or "not open" in err.lower():
            print("    ההרשמה עדיין לא פתוחה, מנסה שוב...")
            time.sleep(0.3)
        else:
            print(f"[!] שגיאה לא צפויה: {err}")
            time.sleep(0.5)

    print("[!] לא הצלחנו להירשם אחרי 15 ניסיונות.")


if __name__ == "__main__":
    main()
