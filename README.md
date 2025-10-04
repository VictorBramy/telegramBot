# Telegram Bot Project

בוט טלגרם חכם ומתקדם שנבנה בפייתון עם ספריית `python-telegram-bot`.

## תכונות

- 🤖 פקודות בסיסיות (`/start`, `/help`, `/menu`)
- 📍 **איתור מיקום IP מתקדם** (`/locate`) - חיפוש מיקום גאוגרפי מפורט של IP או דומיין
- 💬 תגובה אוטומטית חכמה להודעות טקסט
- ⌨️ תפריט אינטראקטיבי עם כפתורים
- 🔧 ניהול שגיאות מתקדם
- 📝 לוגים מפורטים
- 🌍 תמיכה מלאה בעברית
- 🗺️ מידע גאוגרפי מקיף
- 🏥 Health check server לניטור
- 🚀 אופטימיזציה לפריסה בענן Project

בוט טלגרם פשוט וחכם שנבנה בפייתון עם ספריית `python-telegram-bot`.

## תכונות

- 🤖 פקודות בסיסיות (`/start`, `/help`, `/menu`)
- � **איתור מיקום IP** (`/locate`) - חיפוש מיקום גאוגרפי של IP או דומיין
- �💬 תגובה אוטומטית להודעות טקסט
- ⌨️ תפריט אינטראקטיבי עם כפתורים
- 🔧 ניהול שגיאות
- 📝 לוגים מפורטים
- 🌍 תמיכה בעברית
- 🗺️ קישורים ישירים למפות Google

## אפשרויות הרצה

### 🏠 הרצה מקומית (פיתוח)

#### 1. שכפול הפרויקט

```bash
git clone <repository-url>
cd telegram-bot
```

#### 2. יצירת סביבת פיתוח וירטואלית

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
```

#### 3. התקנת תלותיות

```bash
pip install -r requirements.txt
```

#### 4. הגדרת משתני סביבה

1. העתק את קובץ `.env.example` ל-`.env`
2. מלא את הפרטים הנדרשים:

```env
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
```

### ☁️ פריסה בענן

#### 🚂 Railway (ללא כרטיס אשראי!) ⭐ מומלץ

```bash
# העלה לGitHub ופרוס בקליק אחד
# $5 credit חודשי חינם
```

**📖 מדריך:** [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)

#### 🏢 Oracle Cloud (חינמי אבל דורש כרטיס אשראי)

```bash
# העלה את כל הקבצים ל-VM
scp -r . ubuntu@YOUR_ORACLE_IP:/home/ubuntu/telegram-bot/

# התחבר ל-VM והרץ:
ssh ubuntu@YOUR_ORACLE_IP
cd telegram-bot
chmod +x deploy-oracle-cloud.sh
sudo ./deploy-oracle-cloud.sh
```

**📖 מדריך:** [ORACLE_DEPLOYMENT.md](ORACLE_DEPLOYMENT.md)

### 🐳 הרצה עם Docker (מומלץ!)

```bash
# בניית האימג'
docker-compose build

# הרצה
docker-compose up -d

# בדיקת סטטוס
docker-compose ps

# צפייה בלוגים
docker-compose logs -f
```

### 5. קבלת Token לבוט

1. פתח שיחה עם [@BotFather](https://t.me/BotFather) בטלגרם
2. שלח `/newbot` ועקב אחר ההוראות
3. קבל את ה-token והכנס אותו לקובץ `.env`

## הרצה

```bash
python bot.py
```

## מבנה הפרויקט

```
telegram-bot/
├── bot.py              # קובץ הבוט הראשי
├── locate_ip.py        # מודול איתור IP (מתקדם)
├── requirements.txt    # תלותיות Python
├── .env.example       # דוגמה למשתני סביבה
├── .env              # משתני סביבה (לא נכלל ב-git)
├── .gitignore        # קבצים להתעלמות
└── README.md         # תיעוד הפרויקט
```

## פקודות זמינות

### 🔧 פקודות בסיס
- `/start` - התחלת השיחה עם הבוט
- `/help` - הצגת עזרה
- `/menu` - תפריט אינטראקטיבי
- `/status` - סטטוס מודולים

### 🌐 כלי רשת ואבטחה  
- `/locate <IP או דומיין>` - איתור מיקום גאוגרפי
- `/ping <host>` - בדיקת זמינות
- `/scan <target> [type]` - סריקת פורטים
- `/rangescan <range> <port>` - סריקת טווח IP

### 💥 ניתוח אבטחה מתקדם
- `/exploitscan <target>` - **חדש!** ניתוח exploits מקיף עם תוכנית ניצול
- `/vulnscan <target>` - סריקת פגיעויות בסיסית
- `/vulninfo <type>` - מידע מפורט על סוגי פגיעויות
- `/exploitinfo <service>` - מידע על exploits לשירות ספציפי

### 📊 ניתוח מניות (אם זמין)
- `/stock <symbol>` - ניתוח מניה מתקדם

### דוגמאות שימוש:

#### בדיקות רשת בסיסיות:
```
/locate 8.8.8.8
/ping google.com
/scan github.com quick
/rangescan 192.168.1.0/24 22
```

#### ניתוח אבטחה מתקדם:
```
/exploitscan example.com     # ניתוח מקיף
/vulnscan target.com         # בדיקת פגיעויות
/vulninfo ssl               # מידע על SSL issues  
/exploitinfo apache         # Apache exploits
```

## התאמה אישית

ניתן להוסיף פקודות חדשות על ידי:

1. הוספת handler חדש ב-`setup_handlers()`
2. יצירת פונקצית handler חדשה
3. רישום הפונקציה באפליקציה

## פיתוח נוסף

הבוט בנוי בצורה מודולרית ומאפשר הוספת תכונות נוספות בקלות:

- 📊 מסדי נתונים
- 🎯 API חיצוניים
- 📁 ניהול קבצים
- 👥 ניהול משתמשים
- 📈 אנליטיקה

## תכונת איתור IP

הבוט כולל מערכת מתקדמת לאיתור מיקום IP המשתמשת במספר מקורות:

### מקורות המידע:

- **ip-api.com** - מסד נתונים גאוגרפי מקיף
- **ipinfo.io** - שירות מיקום מקצועי
- **מסדי נתונים נוספים** - לדיוק מקסימלי

### יכולות:

- ✅ איתור IP addresses
- ✅ פתרון domain names לIP
- ✅ מיצוע מיקום ממספר מקורות
- ✅ קישור ישיר למפות Google
- ✅ מידע על ספק האינטרנט
- ✅ הערות על דיוק ומגבלות

## 🛠️ ניהול הבוט

### עבור Oracle Cloud:

```bash
# כלי ניהול אינטראקטיבי
./bot-manager.sh

# פקודות מהירות
bot-status     # סטטוס הבוט
bot-logs       # צפייה בלוגים
bot-restart    # הפעלה מחדש
bot-stop       # עצירה
bot-start      # הפעלה
```

### עדכון מהיר:

```bash
# העלה קבצים חדשים ואז:
./quick-update.sh
```

## 📊 ניטור ובקרה

### Health Check:

- **URL:** `http://YOUR_IP:8000/health`
- **Docker:** מובנה עם health checks
- **Systemd:** שירות אוטומטי עם restart

### לוגים:

```bash
# לוגי הבוט
docker-compose logs -f

# לוגי המערכת
journalctl -u telegram-bot -f

# ניטור משאבים
htop
docker stats
```

## 💰 עלויות Oracle Cloud

- **Always Free Tier:** 0₪ לתמיד
- **משאבים:** 1 Core, 1GB RAM, 200GB
- **רשת:** Bandwidth ללא הגבלה
- **זמינות:** 24/7

## 📞 תמיכה

אם יש בעיות:

1. בדוק לוגים: `bot-logs`
2. נסה restart: `bot-restart`
3. בדוק health: `curl localhost:8000/health`
4. ראה [ORACLE_DEPLOYMENT.md](ORACLE_DEPLOYMENT.md)

## 📄 רישיון

MIT License
