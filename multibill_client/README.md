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

## התקנה אצל הלקוח (Docker)

זו הדרך המיועדת להתקנה בשרת פנימי אצל הלקוח - חבילה עצמאית שלא דורשת
התקנת Python בשרת, ומריצה את כל התלויות (כולל gnupg) בתוך container.

```bash
cp config.example.yaml config.yaml   # הלקוח ממלא כאן את פרטי ה-SFTP וה-PGP שלו
cp .env.example .env                 # וממלא כאן את MULTIBILL_GPG_PASSPHRASE
mkdir -p keys                        # ומכניס לכאן את מפתח ה-PGP הפרטי שלו

docker compose up -d --build
```

לאחר ההרצה: פתח http://<שם-השרת-הפנימי>:8000

- `config.yaml`, `.env` ו-`keys/` **לא** נכנסים ל-image (ראה `.dockerignore`) - נטענים
  כ-volumes בזמן ריצה, כך שפרטי ההתחברות והמפתחות של הלקוח נשארים רק אצלו.
- הנתונים (SQLite DB, קבצים שהורדו/פוענחו) נשמרים תחת `./data/` בשרת המארח,
  כך שהם שורדים עדכון/הפעלה מחדש של ה-container.
- **הערה לגבי כיוון החיבור:** ה-container רק **יוצא** לשרת ה-SFTP (outbound) -
  אין צורך לפתוח פורט נכנס בפיירוול של הלקוח בשביל המשיכה עצמה. פורט 8000
  (ה-UI) הוא היחיד שנחשף, ורק לרשת הפנימית (לא לאינטרנט) אלא אם הוחלט אחרת.

## שלב הבא: חיבור למערכות ה-ERP של הלקוח

**עדיין לא ממומש.** לאחר שהנתונים מפורקים (`edi_parser.py`) הם נשמרים היום רק
ב-DB המקומי ומוצגים ב-UI. השלב הבא הוא לקבוע:
- האם דוחפים את הנתונים המפורקים ל-ERP של הלקוח (API/קובץ ייצוא), או שה-ERP
  שולף מהקליינט הזה.
- מיפוי שדות מדויק בין הסגמנטים ב-EDI לשדות ב-ERP (תלוי במבנה ה-EDI האמיתי,
  ראה גם הסעיף הבא).

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
- **חיבור בפועל למערכות ה-ERP** של הלקוח (ראה סעיף למעלה).
- **Dockerfile** קיים לגרסה בסיסית, אבל עדיין חסר: משתמש non-root בתוך ה-container,
  health check, ופריסה מסודרת יותר (K8s CronJob לpuller, Deployment ל-API) אם רלוונטי.
- **ניטור ולוגים מרכזיים** (לא רק stdout).
- **בדיקות QA** - unit tests ל-parser, integration tests ל-SFTP (עם sftp server מדומה).

## התאמה לתוכנית הקיימת (המצגת)

הרכיבים כאן ממפים ישירות למשימות שכבר הוגדרו בסלייד 2 של "חלופה 1":

- "התאמת רכיב התקשורת" → `sftp_client.py`
- "פיתוח ממשק משתמש UI להצגת נתוני חשבונות" → `main.py` + `static/index.html`
- "קליטת הנתונים למבנה החדש" → `models.py` + `edi_parser.py`

זו נקודת פתיחה לעבודה מעמיקה יותר ב-Claude Code, כולל בדיקות, Docker,
והתאמת ה-parser לפורמט EDI האמיתי מול קבצי דוגמה מהבנק.
