# 🚀 מדריך Restart ב-Railway

אם הבוט עדיין לא עובד אחרי 5 דקות, עשה Restart ידני:

## דרך 1: דרך ה-Dashboard

1. לך ל-https://railway.app/dashboard
2. בחר את הפרויקט שלך (VB_International_BOT)
3. לחץ על שלוש הנקודות (⋮) בפינה
4. בחר **"Restart"**
5. המתן 1-2 דקות
6. נסה שוב בטלגרם!

## דרך 2: Force Deploy חדש

אם Restart לא עזר:

1. ב-Railway Dashboard
2. לך ל-**"Deployments"**
3. לחץ **"Deploy"** או **"Redeploy"**
4. המתן לסיום הבנייה (1-3 דקות)
5. נסה שוב!

## דרך 3: Push ריק (אם כל השאר נכשל)

```bash
cd "c:\Users\A\Desktop\TELEGRAM BOT"
git commit --allow-empty -m "Force Railway redeploy"
git push
```

זה יכפה על Railway לפרוס מחדש גם בלי שינויים.

---

## 🔍 איך לדעת שזה עובד?

כאשר הבוט רץ כמו שצריך, תראה ב-Railway Logs:

```
INFO - 10bis handler module loaded successfully
INFO - Bot initialized successfully
INFO - Bot started! Polling for updates...
```

---

## 📊 בדיקת סטטוס מהירה

שלח לבוט בטלגרם:
- `/menu` - אמור להראות "🍔 שוברי 10Bis"
- `/tenbis_login test@test.com` - אמור לבקש OTP

אם אתה רואה "שירות 10Bis לא זמין" - המתן עוד קצת או עשה Restart.
