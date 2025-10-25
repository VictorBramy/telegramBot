# 💰 מדריך מהיר: התראות קריפטו

## התחלה מהירה

### 1. הפעלת מערכת ההתראות

המערכת פועלת אוטומטית עם הבוט. אין צורך בהתקנות נוספות להתראות מחיר פשוטות.

### 2. יצירת התראת מחיר ראשונה

```
/newalert BTC/USDT PRICE ABOVE 50000
```

זה ישלח לך התראה כאשר Bitcoin יעלה מעל $50,000.

---

## סוגי התראות

### 📊 התראות מחיר פשוטות (ללא API key)

#### 1. מחיר מעל (ABOVE)

```
/newalert BTC/USDT PRICE ABOVE 50000
```

התראה כאשר המחיר עולה מעל ערך מסוים.

#### 2. מחיר מתחת (BELOW)

```
/newalert ETH/USDT PRICE BELOW 2000
```

התראה כאשר המחיר יורד מתחת לערך מסוים.

#### 3. שינוי באחוזים (PCTCHG)

```
/newalert BTC/USDT PRICE PCTCHG 5 30000
```

התראה כאשר המחיר משתנה ב-5% ביחס למחיר התחלתי של $30,000.

#### 4. שינוי 24 שעות (24HRCHG)

```
/newalert BTC/USDT PRICE 24HRCHG 10 1h
```

התראה כאשר המחיר משתנה ב-10% ב-24 שעות האחרונות, עם cooldown של שעה.

---

### 📈 אינדיקטורים טכניים (דורש TAAPI.IO API)

#### להשגת API Key:

1. היכנס ל: https://taapi.io
2. הירשם בחינם (לא נדרש כרטיס אשראי)
3. העתק את ה-API key
4. הוסף ל-`.env`:
   ```
   TAAPIIO_APIKEY=your_key_here
   ```

#### דוגמאות אינדיקטורים:

**RSI (Relative Strength Index)**

```
/newalert ETH/USDT RSI 1h default value BELOW 30
```

התראה כאשר RSI יורד מתחת ל-30 (oversold).

**MACD (Moving Average Convergence Divergence)**

```
/newalert BTC/USDT MACD 4h default valueMACD ABOVE 0 1h
```

התראה כאשר MACD חותך מעל 0 (bullish signal).

**Bollinger Bands**

```
/newalert ETH/USDT BBANDS 1d default valueUpperBand ABOVE 3000
```

התראה כאשר הרצועה העליונה עולה מעל $3000.

**SMA (Simple Moving Average)**

```
/newalert BTC/USDT SMA 1h period=50 value ABOVE 45000
```

התראה כאשר ממוצע נע של 50 תקופות עולה מעל $45,000.

---

## ניהול התראות

### צפייה בהתראות פעילות

```
/viewalerts              # כל ההתראות
/viewalerts BTC/USDT     # רק BTC/USDT
```

### ביטול התראה

```
/cancelalert BTC/USDT 0  # מוחק התראה 0 של BTC/USDT
```

### קבלת מחירים נוכחיים

```
/getprice BTC/USDT       # מחיר BTC
/priceall                # כל המחירים של זוגות עם התראות
```

### קבלת ערך אינדיקטור

```
/getindicator BTC/USDT RSI 1h default
/getindicator ETH/USDT MACD 4h default
```

### רשימת אינדיקטורים

```
/indicators              # כל האינדיקטורים הזמינים
```

---

## Cooldown System

### מה זה Cooldown?

Cooldown מונע התראות חוזרות בזמן קצר. ברירת המחדל היא התראה חד-פעמית.

### דוגמאות:

```
/newalert BTC/USDT PRICE ABOVE 50000 30s    # כל 30 שניות
/newalert BTC/USDT PRICE ABOVE 50000 5m     # כל 5 דקות
/newalert BTC/USDT PRICE ABOVE 50000 1h     # כל שעה
/newalert BTC/USDT PRICE ABOVE 50000 1d     # כל יום
```

### יחידות זמן:

- `s` = שניות (30s)
- `m` = דקות (5m)
- `h` = שעות (1h)
- `d` = ימים (1d)

---

## Timeframes (טווחי זמן לאינדיקטורים)

- `1m` = דקה אחת
- `5m` = 5 דקות
- `15m` = 15 דקות
- `30m` = 30 דקות
- `1h` = שעה אחת
- `2h` = שעתיים
- `4h` = 4 שעות
- `12h` = 12 שעות
- `1d` = יום אחד
- `7d` = שבוע

---

## איפוס פרמטרים

להשארת פרמטרים default:

```
/newalert BTC/USDT RSI 1h default value BELOW 30
```

התאמה אישית:

```
/newalert BTC/USDT RSI 1h period=14 value BELOW 30
/newalert BTC/USDT BBANDS 1d period=20,stddev=2 valueUpperBand ABOVE 3000
```

---

## פורמט זוגות

תמיד השתמש בפורמט:

```
BASE/QUOTE
```

דוגמאות נכונות:

- ✅ `BTC/USDT`
- ✅ `ETH/USDT`
- ✅ `BNB/USDT`

דוגמאות שגויות:

- ❌ `BTCUSDT`
- ❌ `BTC-USDT`
- ❌ `BTC_USDT`

---

## אינדיקטורים נתמכים

### Simple Indicators (ללא API):

- **PRICE** - מחיר הזוג

### Technical Indicators (עם TAAPI.IO):

- **RSI** - Relative Strength Index
- **MACD** - Moving Average Convergence Divergence
- **BBANDS** - Bollinger Bands
- **SMA** - Simple Moving Average
- **EMA** - Exponential Moving Average

---

## טיפים למסחר

### 1. RSI Strategy

```
# קנה כאשר oversold
/newalert BTC/USDT RSI 1h default value BELOW 30

# מכור כאשר overbought
/newalert BTC/USDT RSI 1h default value ABOVE 70
```

### 2. Bollinger Bands Breakout

```
# התראה על פריצה מעל
/newalert ETH/USDT BBANDS 4h default valueUpperBand ABOVE 3000

# התראה על פריצה מתחת
/newalert ETH/USDT BBANDS 4h default valueLowerBand BELOW 2500
```

### 3. MACD Cross

```
# Signal חיובי
/newalert BTC/USDT MACD 1d default valueMACD ABOVE 0

# Signal שלילי
/newalert BTC/USDT MACD 1d default valueMACD BELOW 0
```

---

## שאלות נפוצות

**ש: האם המערכת עובדת 24/7?**
ת: כן, המערכת פועלת ברקע ובודקת התנאים כל 10 שניות.

**ש: כמה התראות אני יכול ליצור?**
ת: אין הגבלה, אך מומלץ להתחיל עם 5-10 התראות.

**ש: האם זה עובד עם כל הקריפטו?**
ת: כן, כל זוג שקיים ב-Binance.

**ש: מה קורה אם אני לא רוצה אינדיקטורים טכניים?**
ת: אתה יכול להשתמש רק בהתראות מחיר פשוטות ללא API key.

**ש: איך אני מקבל את ההתראות?**
ת: הבוט שולח לך הודעה ישירה ב-Telegram.

---

## תמיכה

אם יש בעיה או שאלה, שלח הודעה בבוט עם `/help`.

---

**🚀 בהצלחה במסחר!**
