# Multibill Client - גרסה ראשונית

קליינט חדש להחלפת רכיב ה-Delphi 4 / Paradox הקיים.
משיכת קבצים מ-SFTP → פענוח הצפנה (PGP) → פירוק EDI → תצוגת נתונים ללקוח.

## הרצה מקומית

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # ולמלא פרטי חיבור אמיתיים
export MULTIBILL_GPG_PASSPHRASE="..."   # אם רלוונטי
uvicorn main:app --reload
```

לאחר ההרצה: פתח http://localhost:8000

## מבנה הפרויקט

| קובץ | תפקיד |
|---|---|
| `sftp_client.py` | חיבור ומשיכת קבצים חדשים מ-SFTP |
| `decryption.py` | פענוח PGP (stub ראשוני - יש להתאים לשיטת ההצפנה בפועל) |
| `edi_parser.py` | פירוק גנרי של קובץ EDI לסגמנטים/אלמנטים |
| `models.py` | טבלת מעקב קבצים (SQLite כברירת מחדל) |
| `main.py` | FastAPI + Scheduler שמריץ את מחזור המשיכה |
| `static/index.html` | עמוד תצוגה בסיסי ללקוח |

## מה עוד חסר לפני production (בכוונה לא נכלל בגרסה ראשונית)

- **פורמט EDI אמיתי** - ה-parser כרגע גנרי (segment/element separators בלבד).
  צריך לבדוק מול הבנק/ERP את המבנה המדויק (קודי סוג הודעה, מיפוי שדות)
  ואולי לעבור לספרייה ייעודית עם תמיכה ב-schema validation.
- **אימות SSH host key** מול known_hosts במקום AutoAddPolicy - קריטי לאבטחה.
- **טיפול בשגיאות ו-retry** במשיכת SFTP (timeout, קובץ חלקי, ניתוק).
- **Authentication/Authorization** ל-API עצמו - כרגע פתוח לחלוטין.
- **מעבר ל-PostgreSQL** במקום SQLite לסביבת production.
- **הרצה כ-container** (Dockerfile) + פריסה (K8s CronJob לpuller, Deployment ל-API).
- **ניטור ולוגים מרכזיים** (לא רק stdout).
- **בדיקות QA** - unit tests ל-parser, integration tests ל-SFTP (עם sftp server מדומה).

## התאמה לתוכנית הקיימת (המצגת)

הרכיבים כאן ממפים ישירות למשימות שכבר הוגדרו בסלייד 2 של "חלופה 1":

- "התאמת רכיב התקשורת" → `sftp_client.py`
- "פיתוח ממשק משתמש UI להצגת נתוני חשבונות" → `main.py` + `static/index.html`
- "קליטת הנתונים למבנה החדש" → `models.py` + `edi_parser.py`

זו נקודת פתיחה לעבודה מעמיקה יותר ב-Claude Code, כולל בדיקות, Docker,
והתאמת ה-parser לפורמט EDI האמיתי מול קבצי דוגמה מהבנק.
