# 🚂 Railway Deployment Guide (ללא כרטיס אשראי!)

פריסה מהירה וחינמית של הבוט ל-Railway.

## 🎯 יתרונות Railway:

- ✅ **ללא כרטיس אשראי**
- ✅ **$5 credit חודשי חינם**
- ✅ **פריסה מ-GitHub בקליק אחד**
- ✅ **SSL אוטומטי**
- ✅ **מוניטורינג מובנה**
- ✅ **עדכונים אוטומטיים**

## 📋 שלבים:

### 1. הרשמה ל-Railway
1. לך ל-https://railway.app
2. לחץ **"Start a New Project"**
3. התחבר עם **GitHub** (או צור חשבון)

### 2. העלאת הקוד ל-GitHub
```bash
# צור repository חדש ב-GitHub
# העתק את כל הקבצים לrepository

git init
git add .
git commit -m "Initial commit - VB International Bot"
git remote add origin https://github.com/YOUR_USERNAME/telegram-bot
git push -u origin main
```

### 3. פריסה ב-Railway
1. ב-Railway Dashboard לחץ **"Deploy from GitHub repo"**
2. בחר את ה-repository שיצרת
3. Railway יזהה אוטומטית את הפרויקט

### 4. הגדרת משתני סביבה
1. לך ל-**Variables** בדashboard
2. הוסף:
   ```
   TELEGRAM_BOT_TOKEN=8228187620:AAGovEMQeCHAfE1BJHVuASE1l_W-d1PaNa8
   BOT_NAME=VB_International_BOT
   DEBUG=False
   ```

### 5. פריסה אוטומטית
Railway יתחיל לבנות ולפרוס אוטומטית!

## 📊 מעקב:

- **Logs:** ראה לוגים בזמן אמת
- **Metrics:** CPU, RAM, Network usage
- **Deployments:** היסטוריית פריסות
- **Settings:** הגדרות נוספות

## 🔄 עדכונים:

כל push ל-GitHub יפרוס אוטומטית ל-Railway!

```bash
# עדכון הבוט
git add .
git commit -m "Update bot features"
git push
# Railway יפרוס אוטומטיות תוך דקות!
```

## 💰 מגבלות החינמי:

- **$5 credit** חודשי
- **500 שעות** ריצה
- **100GB** bandwidth
- **1GB** RAM per service

**לבוט טלגרם - זה יותר ממספיק!**

## 🛠️ פתרון בעיות:

### הבוט לא מתחיל:
1. בדוק **Variables** - הטוקן נכון?
2. ראה **Logs** לשגיאות
3. וודא ש-`requirements.txt` עדכני

### חיבור לא עובד:
1. בדוק שהטוקן חוקי
2. ודא שהבוט לא חסום ב-Telegram
3. בדוק לוגים לשגיאות API

## 🎉 סיום:

הבוט יעבוד 24/7 בחינם ב-Railway!

**URL לניהול:** https://railway.app/dashboard