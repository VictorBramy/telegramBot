# 🔑 הוספת TAAPIIO_APIKEY ל-Railway

## שלבים מהירים:

### 1. כניסה ל-Railway Dashboard

1. לך ל-https://railway.app/dashboard
2. בחר את הפרויקט של הבוט

### 2. הוספת Variable

1. לחץ על הפרויקט
2. לך ל-**Variables** (בתפריט השמאלי)
3. לחץ על **+ New Variable**

### 3. הוסף את המפתח

```
שם: TAAPIIO_APIKEY
ערך: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbHVlIjoiNjhmZDA0ZmQ4MDZmZjE2NTFlNjJhNTM0IiwiaWF0IjoxNzYxNDEyMzQ5LCJleHAiOjMzMjY1ODc2MzQ5fQ.vg2T-nNhhP_mGseHw9i15k-ZhCrpIyztoQ_LSsp1sQw
```

### 4. שמירה

1. לחץ **Add**
2. Railway יעשה **auto-redeploy** תוך 1-2 דקות

## ✅ בדיקה:

אחרי שהבוט עולה מחדש, נסה:

```
/getindicator BTC/USDT RSI 1h default
```

צריך לעבוד! 🎯

## 📋 רשימת Variables הנוכחית:

צריך להיות לך:

- ✅ `TELEGRAM_BOT_TOKEN`
- ✅ `BOT_NAME`
- ✅ `DEBUG`
- ✅ `TAAPIIO_APIKEY` ← **הוסף את זה!**
