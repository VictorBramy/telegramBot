# 🚀 Oracle Cloud Deployment Guide

מדריך מפורט להעלאת הבוט לענן Oracle Cloud בחינם.

## 📋 דרישות מוקדמות

1. **חשבון Oracle Cloud (חינמי):**
   - הירשם ב-[Oracle Cloud](https://cloud.oracle.com)
   - קבל Always Free Tier (VM + 200GB storage)

2. **Telegram Bot Token:**
   - צור בוט ב-[@BotFather](https://t.me/BotFather)
   - שמור את ה-Token

## 🖥️ שלב 1: יצירת VM ב-Oracle Cloud

### 1.1 יצירת Instance
1. התחבר ל-Oracle Cloud Console
2. לך ל-**Compute → Instances**
3. לחץ **Create Instance**

### 1.2 הגדרות Instance
- **Name:** `telegram-bot-server`
- **Image:** Ubuntu 22.04 LTS (Always Free Eligible)
- **Shape:** VM.Standard.E2.1.Micro (Always Free)
- **Network:** השאר default
- **SSH Keys:** העלה את ה-public key שלך או צור חדש

### 1.3 הגדרות רשת (חשוב!)
1. לחץ **Show advanced options**
2. ב-**Networking** וודא:
   - Public IP assigned: ✅ Yes
   - השאר את הגדרות ה-subnet ברירת מחדל

## 🔑 שלב 2: התחברות ל-VM

```bash
# החלף YOUR_PUBLIC_IP עם ה-IP שקיבלת
ssh -i ~/.ssh/your_private_key ubuntu@YOUR_PUBLIC_IP

# אם לא עובד, נסה:
ssh -i ~/.ssh/your_private_key opc@YOUR_PUBLIC_IP
```

## 📦 שלב 3: העלאת הקבצים

### 3.1 העתק קבצים מהמחשב המקומי
```bash
# מהמחשב המקומי (Windows PowerShell/CMD):
scp -i ~/.ssh/your_private_key bot.py ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
scp -i ~/.ssh/your_private_key locate_ip.py ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
scp -i ~/.ssh/your_private_key requirements.txt ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
scp -i ~/.ssh/your_private_key Dockerfile ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
scp -i ~/.ssh/your_private_key docker-compose.yml ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
scp -i ~/.ssh/your_private_key deploy-oracle-cloud.sh ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
```

### 3.2 יצירת קובץ .env
```bash
# על ה-VM:
nano .env
```

הכנס את התוכן הבא:
```env
TELEGRAM_BOT_TOKEN=8228187620:AAGovEMQeCHAfE1BJHVuASE1l_W-d1PaNa8
BOT_NAME=VB_International_BOT
DEBUG=False
```

שמור וצא: `Ctrl+X → Y → Enter`

## 🚀 שלב 4: הרצת הסקריפט

```bash
# הרץ את סקריפט ההתקנה
chmod +x deploy-oracle-cloud.sh
sudo ./deploy-oracle-cloud.sh
```

הסקריפט יתקין:
- Docker & Docker Compose
- יבנה את האימג'
- יריץ את הבוט
- יגדיר שירות systemd
- יגדיר firewall
- יגדיר monitoring

## 🔧 שלב 5: הגדרת Firewall ב-Oracle Cloud

### 5.1 Security List (חשוב מאוד!)
1. חזור ל-Oracle Cloud Console
2. לך ל-**Networking → Virtual Cloud Networks**
3. לחץ על ה-VCN שנוצר
4. לחץ על **Security Lists**
5. לחץ על **Default Security List**
6. לחץ **Add Ingress Rules**

### 5.2 הוסף כללים:
**כלל 1 - SSH:**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: TCP
- Destination Port Range: `22`

**כלל 2 - Health Check (אופציונלי):**
- Source CIDR: `0.0.0.0/0`  
- IP Protocol: TCP
- Destination Port Range: `8000`

## ✅ שלב 6: בדיקה

### 6.1 בדוק שהבוט רץ
```bash
# על ה-VM:
bot-status    # או: docker-compose ps
bot-logs      # או: docker-compose logs -f
```

### 6.2 בדוק ב-Telegram
1. פתח את הבוט: [t.me/VB_International_BOT](https://t.me/VB_International_BOT)
2. שלח `/start`
3. נסה `/locate google.com`

### 6.3 בדוק Health Check
```bash
curl http://localhost:8000/health
```

## 📊 ניהול הבוט

### פקודות שימושיות:
```bash
bot-status     # סטטוס הבוט
bot-logs       # לוגים בזמן אמת
bot-restart    # הפעלה מחדש
bot-stop       # עצירה
bot-start      # הפעלה
bot-update     # עדכון מ-git (אם יש)
bot-dir        # מעבר לתיקיית הבוט
```

### בדיקת לוגים:
```bash
# לוגים של הבוט
tail -f /opt/telegram-bot/logs/bot.log

# לוגים של המערכת
sudo journalctl -u telegram-bot.service -f

# לוגי Docker
docker logs -f vb-international-bot
```

## 🔄 עדכון הבוט

### עדכון ידני:
```bash
cd /opt/telegram-bot

# עדכן קבצים
sudo nano bot.py  # ערוך לפי הצורך

# בנה מחדש
docker-compose build
docker-compose up -d
```

### גיבוי קבצים:
```bash
# צור גיבוי
sudo tar -czf ~/bot-backup-$(date +%Y%m%d).tar.gz /opt/telegram-bot

# שחזר גיבוי
sudo tar -xzf ~/bot-backup-YYYYMMDD.tar.gz -C /
```

## 🛠️ פתרון בעיות

### הבוט לא מתחיל:
```bash
# בדוק לוגים
docker-compose logs

# בדוק את קובץ ה-.env
cat .env

# בדוק שהטוקן נכון
echo $TELEGRAM_BOT_TOKEN
```

### בעיות רשת:
```bash
# בדוק חיבור לאינטרנט
ping google.com

# בדוק פורטים פתוחים
sudo netstat -tlnp | grep :8000

# בדוק firewall
sudo iptables -L
```

### שחזור במקרה חירום:
```bash
# אתחול מוחלט
sudo systemctl stop telegram-bot
docker-compose down
docker system prune -af
docker-compose build --no-cache
docker-compose up -d
```

## 💡 טיפים ועצות

### 1. חיסכון בעלויות:
- Always Free Tier של Oracle מספיק לבוט קטן
- השתמש רק ב-resources שאתה צריך
- עקוב אחר השימוש ב-Oracle Cloud Console

### 2. אבטחה:
- שנה את ה-SSH key מדי פעם
- השתמש ב-SSH keys במקום סיסמאות
- עדכן את המערכת: `sudo apt update && sudo apt upgrade`

### 3. גיבויים:
- גבה את קבצי הבוט פעם בשבוע
- שמור עותק של ה-.env במקום בטוח
- תעד שינויים שאתה עושה

### 4. ניטור:
- בדוק לוגים פעמיים בשבוע
- השתמש ב-`htop` לבדיקת ביצועים
- הגדר alerts אם צריך

## 📞 תמיכה

אם יש בעיות:
1. בדוק את הלוגים קודם
2. נסה הפעלה מחדש
3. בדוק שהטוקן נכון
4. וודא שהפורטים פתוחים ב-Security List

**הבוט אמור לרוץ 24/7 בענן Oracle בחינם!** 🎉