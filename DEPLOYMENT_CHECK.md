# 🎯 איך לוודא שהבוט עובד בענן?

## בדיקה מהירה

### 1. בדוק ב-Railway Dashboard

1. לך ל-https://railway.app/dashboard
2. בחר את הפרויקט שלך (VB_International_BOT או שם אחר)
3. תראה:
   - ✅ **Status**: "Active" בירוק
   - 🔄 **Latest Deployment**: מהדקות האחרונות
   - 📊 **Logs**: הבוט רץ בלי שגיאות

### 2. בדוק Logs

לחץ על **View Logs** ותראה:
```
INFO - 10bis handler module loaded successfully
INFO - Bot initialized successfully
INFO - Bot started! Polling for updates...
```

אם יש שגיאה, תראה משהו כמו:
```
ERROR - Failed to load 10bis handler: ModuleNotFoundError...
```

### 3. בדוק בטלגרם

פתח את הבוט שלך בטלגרם ושלח:
```
/help
```

תראה ברשימת הפקודות:
```
🍔 שוברי 10Bis:
/tenbis_login <email> - התחבר לחשבון
/tenbis_vouchers [חודשים] - הצג שוברים פעילים
/tenbis_logout - התנתק
```

אם זה מופיע - **הכל עובד מצוין!** ✅

## בעיות נפוצות ופתרונות

### ❌ הבוט לא מתחיל

**סימפטום**: Status = "Crashed" או "Failed"

**פתרון**:
1. בדוק Logs לשגיאות
2. וודא ש-`TELEGRAM_BOT_TOKEN` מוגדר נכון ב-Variables
3. נסה Restart ידני

### ❌ הבוט רץ אבל לא עונה

**סימפטום**: Status = "Active" אבל הבוט לא מגיב בטלגרם

**פתרון**:
1. וודא שהטוקן תקף (לא פג תוקף)
2. בדוק שהבוט לא חסום על ידי Telegram
3. שלח `/start` שוב

### ❌ 10Bis לא עובד

**סימפטום**: הפקודות `/tenbis_*` לא עובדות

**פתרון**:
1. בדוק Logs:
   ```
   INFO - 10bis handler module loaded successfully
   ```
   אם לא רואה את זה - יש בעיה בייבוא
2. וודא ש-`tenbis_handler.py` קיים בגרסה האחרונה
3. וודא ש-`urllib3` ב-requirements.txt

### ❌ Railway לא מעדכן

**סימפטום**: push עובד אבל הבוט לא משתנה

**פתרון**:
1. וודא ש-Railway מחובר לה-repository הנכון
2. בדוק Settings → GitHub Integration
3. נסה Manual Deploy

## 🔍 איך לבצע Manual Deploy ב-Railway?

אם העדכון האוטומטי לא עובד:

1. לך לדashboard של הפרויקט
2. לחץ **⋮** (שלוש נקודות) בפינה
3. בחר **Redeploy**
4. המתן 1-2 דקות

## 📊 מה לבדוק ב-Logs?

חפש שורות אלה:
```
INFO - 10bis handler module loaded successfully    ← 10Bis נטען בהצלחה
INFO - Bot initialized successfully                ← הבוט אתחל
INFO - Bot started! Polling for updates...         ← הבוט רץ
```

אם יש שגיאות:
```
ERROR - Failed to load 10bis handler              ← בעיה בייבוא
ERROR - Unauthorized: invalid token               ← טוקן שגוי
ERROR - Network error                             ← בעיית רשת
```

## 🎉 הכל עובד? בדוק את זה:

1. שלח לבוט: `/tenbis_login test@example.com`
2. אמור לקבל: "קוד אימות נשלח לאימייל שלך..."
3. אם קיבלת - **הכל מושלם!** 🚀

## 💰 שימוש ב-Credits

Railway נותן $5 חינם בחודש. לבוט טלגרם פשוט זה יותר ממספיק!

בדוק:
- **Dashboard** → **Usage**
- תראה כמה נשאר

בדרך כלל בוט טלגרם צורך:
- ~$0.50 לחודש עם שימוש רגיל
- ~$1-2 עם שימוש כבד

## 📝 Checklist סופי

- [ ] הבוט רץ (Status = Active)
- [ ] אין שגיאות ב-Logs
- [ ] `/help` מציג פקודות 10Bis
- [ ] `/tenbis_login` עובד
- [ ] Variables מוגדרים נכון
- [ ] GitHub מחובר ל-Railway

**כל ה-checkboxes מסומנים?** 🎊 **הבוט שלך פרוס ועובד מצוין!**

---

**צריך עזרה?** 
- קרא [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) למדריך מלא
- בדוק [TENBIS_TROUBLESHOOTING.md](TENBIS_TROUBLESHOOTING.md) לבעיות ספציפיות
