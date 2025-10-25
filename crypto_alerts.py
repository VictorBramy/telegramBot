"""
🚀 Crypto Alerts Module
מודול מתקדם להתראות קריפטו עם תמיכה ב-Binance ואינדיקטורים טכניים
"""

import requests
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== Constants ==============
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker?symbol={}&windowSize={}"
BINANCE_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "12h", "1d", "7d"]
SIMPLE_INDICATORS = ["PRICE"]
SIMPLE_COMPARISONS = ["ABOVE", "BELOW", "PCTCHG", "24HRCHG"]

# Technical Indicators Database
TECHNICAL_INDICATORS = {
    "RSI": {
        "name": "Relative Strength Index",
        "endpoint": "https://api.taapi.io/rsi?secret={api_key}&exchange=binance&symbol={symbol}&interval={interval}",
        "params": [("period", "Period length", 14)],
        "output": ["value"],
        "description": "מחוון התנודתיות היחסית - מזהה מצבי קנייה/מכירה יתר"
    },
    "MACD": {
        "name": "Moving Average Convergence Divergence",
        "endpoint": "https://api.taapi.io/macd?secret={api_key}&exchange=binance&symbol={symbol}&interval={interval}",
        "params": [
            ("optInFastPeriod", "Fast period", 12),
            ("optInSlowPeriod", "Slow period", 26),
            ("optInSignalPeriod", "Signal smoothing", 9)
        ],
        "output": ["valueMACD", "valueMACDSignal", "valueMACDHist"],
        "description": "התכנסות והתרחקות ממוצעים נעים - מזהה שינויי מגמה"
    },
    "BBANDS": {
        "name": "Bollinger Bands",
        "endpoint": "https://api.taapi.io/bbands?secret={api_key}&exchange=binance&symbol={symbol}&interval={interval}",
        "params": [
            ("period", "Period length", 20),
            ("stddev", "Standard deviation", 2)
        ],
        "output": ["valueUpperBand", "valueMiddleBand", "valueLowerBand"],
        "description": "רצועות בולינגר - מזהה תנודתיות ומגמות מחיר"
    },
    "SMA": {
        "name": "Simple Moving Average",
        "endpoint": "https://api.taapi.io/sma?secret={api_key}&exchange=binance&symbol={symbol}&interval={interval}",
        "params": [("period", "Period length", 50)],
        "output": ["value"],
        "description": "ממוצע נע פשוט - מזהה כיוון מגמה כללי"
    },
    "EMA": {
        "name": "Exponential Moving Average",
        "endpoint": "https://api.taapi.io/ema?secret={api_key}&exchange=binance&symbol={symbol}&interval={interval}",
        "params": [("period", "Period length", 50)],
        "output": ["value"],
        "description": "ממוצע נע מעריכי - רגיש יותר לשינויי מחיר אחרונים"
    }
}


# ============== Data Models ==============
@dataclass
class SimpleAlert:
    """התראת מחיר פשוטה"""
    pair: str
    indicator: str  # PRICE
    comparison: str  # ABOVE/BELOW/PCTCHG/24HRCHG
    target: float
    entry_price: Optional[float] = None
    cooldown: Optional[int] = None  # seconds
    last_trigger: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": "simple",
            "pair": self.pair,
            "indicator": self.indicator,
            "comparison": self.comparison,
            "target": self.target,
            "entry_price": self.entry_price,
            "cooldown": self.cooldown,
            "last_trigger": self.last_trigger
        }


@dataclass
class TechnicalAlert:
    """התראה טכנית מתקדמת"""
    pair: str
    indicator: str  # RSI/MACD/BBANDS/SMA/EMA
    timeframe: str
    params: Dict[str, Any]
    output_value: str
    comparison: str  # ABOVE/BELOW
    target: float
    cooldown: Optional[int] = None
    last_trigger: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": "technical",
            "pair": self.pair,
            "indicator": self.indicator,
            "timeframe": self.timeframe,
            "params": self.params,
            "output_value": self.output_value,
            "comparison": self.comparison,
            "target": self.target,
            "cooldown": self.cooldown,
            "last_trigger": self.last_trigger
        }


# ============== Binance Price Handler ==============
class BinanceAPI:
    """מחלקה לטיפול ב-Binance API"""
    
    @staticmethod
    def get_price(pair: str) -> float:
        """קבלת מחיר נוכחי מ-Binance"""
        try:
            pair_formatted = pair.replace("/", "").upper()
            url = BINANCE_PRICE_URL.format(pair_formatted, BINANCE_TIMEFRAMES[0])
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return float(data["lastPrice"])
        except Exception as e:
            logger.error(f"שגיאה בקבלת מחיר {pair}: {e}")
            raise ValueError(f"לא ניתן לקבל מחיר עבור {pair}")
    
    @staticmethod
    def get_price_change(pair: str, window: str = "1d") -> float:
        """קבלת שינוי מחיר באחוזים"""
        try:
            pair_formatted = pair.replace("/", "").upper()
            url = BINANCE_PRICE_URL.format(pair_formatted, window)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return float(data["priceChangePercent"])
        except Exception as e:
            logger.error(f"שגיאה בקבלת שינוי מחיר {pair}: {e}")
            return 0.0


# ============== Technical Indicators Handler ==============
class TaapiioAPI:
    """מחלקה לטיפול ב-Taapi.io API לאינדיקטורים טכניים"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = api_key is not None
    
    def get_indicator(self, pair: str, indicator: str, timeframe: str, params: Dict = None) -> Dict:
        """קבלת ערכי אינדיקטור טכני"""
        if not self.enabled:
            raise ValueError("Taapi.io API key לא מוגדר")
        
        if indicator not in TECHNICAL_INDICATORS:
            raise ValueError(f"אינדיקטור לא ידוע: {indicator}")
        
        try:
            # Prepare parameters
            ind_config = TECHNICAL_INDICATORS[indicator]
            pair_formatted = pair.replace("/", "").upper()
            
            # Build endpoint
            endpoint = ind_config["endpoint"].format(
                api_key=self.api_key,
                symbol=pair_formatted,
                interval=timeframe
            )
            
            # Add custom params
            if params:
                param_str = "&" + "&".join([f"{k}={v}" for k, v in params.items()])
                endpoint += param_str
            
            # Make request
            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"שגיאה בקבלת אינדיקטור {indicator} עבור {pair}: {e}")
            raise


# ============== Alert Processor ==============
class AlertProcessor:
    """מעבד התראות - בודק תנאים ושולח התראות"""
    
    def __init__(self, binance_api: BinanceAPI, taapi: Optional[TaapiioAPI] = None):
        self.binance = binance_api
        self.taapi = taapi
        self.alerts_db = {}  # {user_id: {pair: [alerts]}}
    
    def check_simple_alert(self, alert: SimpleAlert, current_price: float) -> Tuple[bool, str]:
        """בדיקת התראת מחיר פשוטה"""
        comparison = alert.comparison
        target = alert.target
        
        # Check cooldown
        if alert.cooldown and alert.last_trigger:
            if time.time() - alert.last_trigger < alert.cooldown:
                return False, ""
        
        triggered = False
        message = ""
        
        if comparison == "ABOVE":
            if current_price > target:
                triggered = True
                message = f"💰 {alert.pair} עלה מעל {target}\nמחיר נוכחי: {current_price}"
        
        elif comparison == "BELOW":
            if current_price < target:
                triggered = True
                message = f"📉 {alert.pair} ירד מתחת ל-{target}\nמחיר נוכחי: {current_price}"
        
        elif comparison == "PCTCHG" and alert.entry_price:
            pct_change = ((current_price - alert.entry_price) / alert.entry_price) * 100
            if abs(pct_change) >= target * 100:
                triggered = True
                direction = "עלה" if pct_change > 0 else "ירד"
                message = f"📊 {alert.pair} {direction} ב-{abs(pct_change):.2f}%\nמחיר: {alert.entry_price} → {current_price}"
        
        elif comparison == "24HRCHG":
            change_24h = self.binance.get_price_change(alert.pair, "1d")
            if abs(change_24h) >= target * 100:
                triggered = True
                direction = "עלה" if change_24h > 0 else "ירד"
                message = f"📈 {alert.pair} {direction} ב-24 שעות: {abs(change_24h):.2f}%"
        
        if triggered:
            alert.last_trigger = time.time()
        
        return triggered, message
    
    def check_technical_alert(self, alert: TechnicalAlert) -> Tuple[bool, str]:
        """בדיקת התראה טכנית"""
        if not self.taapi or not self.taapi.enabled:
            return False, "אינדיקטורים טכניים לא זמינים"
        
        # Check cooldown
        if alert.cooldown and alert.last_trigger:
            if time.time() - alert.last_trigger < alert.cooldown:
                return False, ""
        
        try:
            # Get indicator data
            data = self.taapi.get_indicator(
                alert.pair,
                alert.indicator,
                alert.timeframe,
                alert.params
            )
            
            # Check if output value exists
            if alert.output_value not in data:
                return False, f"ערך פלט לא נמצא: {alert.output_value}"
            
            current_value = float(data[alert.output_value])
            triggered = False
            
            if alert.comparison == "ABOVE" and current_value > alert.target:
                triggered = True
            elif alert.comparison == "BELOW" and current_value < alert.target:
                triggered = True
            
            if triggered:
                alert.last_trigger = time.time()
                ind_name = TECHNICAL_INDICATORS[alert.indicator]["name"]
                message = f"📊 התראה טכנית: {alert.pair}\n"
                message += f"🔍 {ind_name} ({alert.timeframe})\n"
                message += f"📌 {alert.output_value}: {current_value:.4f} {alert.comparison} {alert.target}"
                return True, message
            
            return False, ""
        
        except Exception as e:
            logger.error(f"שגיאה בבדיקת התראה טכנית: {e}")
            return False, ""


# ============== Alert Manager ==============
class CryptoAlertManager:
    """ניהול כל מערכת ההתראות"""
    
    def __init__(self, taapi_key: Optional[str] = None):
        self.binance = BinanceAPI()
        self.taapi = TaapiioAPI(taapi_key) if taapi_key else None
        self.processor = AlertProcessor(self.binance, self.taapi)
        self.alerts = {}  # {user_id: {pair: [alerts]}}
        self.running = False
        self.monitor_thread = None
    
    def add_alert(self, user_id: str, alert: Any) -> str:
        """הוספת התראה חדשה"""
        if user_id not in self.alerts:
            self.alerts[user_id] = {}
        
        pair = alert.pair
        if pair not in self.alerts[user_id]:
            self.alerts[user_id][pair] = []
        
        self.alerts[user_id][pair].append(alert)
        logger.info(f"התראה חדשה נוספה למשתמש {user_id}: {pair}")
        return f"✅ התראה נוספה בהצלחה עבור {pair}"
    
    def get_alerts(self, user_id: str, pair: Optional[str] = None) -> List:
        """קבלת רשימת התראות"""
        if user_id not in self.alerts:
            return []
        
        if pair:
            return self.alerts[user_id].get(pair, [])
        
        all_alerts = []
        for pair_alerts in self.alerts[user_id].values():
            all_alerts.extend(pair_alerts)
        return all_alerts
    
    def remove_alert(self, user_id: str, pair: str, index: int) -> str:
        """הסרת התראה"""
        try:
            if user_id in self.alerts and pair in self.alerts[user_id]:
                if 0 <= index < len(self.alerts[user_id][pair]):
                    removed = self.alerts[user_id][pair].pop(index)
                    
                    # Clean empty lists
                    if not self.alerts[user_id][pair]:
                        del self.alerts[user_id][pair]
                    if not self.alerts[user_id]:
                        del self.alerts[user_id]
                    
                    return f"✅ התראה הוסרה: {pair}"
            
            return "❌ התראה לא נמצאה"
        except Exception as e:
            return f"❌ שגיאה: {e}"
    
    def format_alerts(self, user_id: str, pair: Optional[str] = None) -> str:
        """פורמט יפה לרשימת התראות"""
        alerts = self.get_alerts(user_id, pair)
        
        if not alerts:
            return "📭 אין התראות פעילות"
        
        message = "📋 *התראות פעילות:*\n\n"
        
        current_pair = None
        alert_index = 0
        
        for alert in alerts:
            if alert.pair != current_pair:
                current_pair = alert.pair
                message += f"🪙 *{current_pair}*\n"
                alert_index = 0
            
            if isinstance(alert, SimpleAlert):
                message += f"  {alert_index}. 💰 {alert.indicator} {alert.comparison} {alert.target}\n"
                if alert.cooldown:
                    message += f"     ⏰ Cooldown: {alert.cooldown}s\n"
            
            elif isinstance(alert, TechnicalAlert):
                message += f"  {alert_index}. 📊 {alert.indicator} ({alert.timeframe})\n"
                message += f"     {alert.output_value} {alert.comparison} {alert.target}\n"
                if alert.cooldown:
                    message += f"     ⏰ Cooldown: {alert.cooldown}s\n"
            
            alert_index += 1
        
        return message
    
    def start_monitoring(self, callback):
        """הפעלת מערכת ניטור התראות"""
        if self.running:
            return
        
        self.running = True
        self.callback = callback
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🚀 מערכת ניטור התראות הופעלה")
    
    def _monitor_loop(self):
        """לולאת ניטור רציפה"""
        while self.running:
            try:
                for user_id, pairs in self.alerts.items():
                    for pair, alerts in pairs.items():
                        # Get current price once per pair
                        try:
                            current_price = self.binance.get_price(pair)
                        except Exception as e:
                            logger.error(f"שגיאה בקבלת מחיר {pair}: {e}")
                            continue
                        
                        for alert in alerts:
                            try:
                                triggered = False
                                message = ""
                                
                                if isinstance(alert, SimpleAlert):
                                    triggered, message = self.processor.check_simple_alert(alert, current_price)
                                elif isinstance(alert, TechnicalAlert):
                                    triggered, message = self.processor.check_technical_alert(alert)
                                
                                if triggered and message:
                                    self.callback(user_id, message)
                            
                            except Exception as e:
                                logger.error(f"שגיאה בבדיקת התראה: {e}")
                
                # Sleep between checks
                time.sleep(10)  # Check every 10 seconds
            
            except Exception as e:
                logger.error(f"שגיאה בלולאת ניטור: {e}")
                time.sleep(5)
    
    def stop_monitoring(self):
        """עצירת ניטור"""
        self.running = False
        logger.info("⏹️ מערכת ניטור הופסקה")


# ============== Helper Functions ==============
def parse_cooldown(cooldown_str: Optional[str]) -> Optional[int]:
    """המרת מחרוזת cooldown לשניות"""
    if not cooldown_str:
        return None
    
    try:
        # Examples: 30s, 5m, 1h, 2d
        value = int(cooldown_str[:-1])
        unit = cooldown_str[-1].lower()
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        
        return value * multipliers.get(unit, 1)
    except:
        return None


def get_indicators_list() -> str:
    """רשימת כל האינדיקטורים הזמינים"""
    message = "📊 *אינדיקטורים זמינים:*\n\n"
    
    # Simple indicators
    message += "*🔹 אינדיקטורים פשוטים:*\n"
    message += "• *PRICE* - מחיר הזוג\n"
    message += "  השוואות: ABOVE, BELOW, PCTCHG, 24HRCHG\n\n"
    
    # Technical indicators
    if TECHNICAL_INDICATORS:
        message += "*🔹 אינדיקטורים טכניים:*\n"
        for ind_id, ind_data in TECHNICAL_INDICATORS.items():
            message += f"• *{ind_id}* - {ind_data['name']}\n"
            message += f"  {ind_data['description']}\n"
            message += f"  פרמטרים: "
            params = [f"{p[0]}={p[2]}" for p in ind_data['params']]
            message += ", ".join(params) + "\n"
            message += f"  פלטים: {', '.join(ind_data['output'])}\n\n"
    
    return message


# ============== Main Export ==============
__all__ = [
    'CryptoAlertManager',
    'SimpleAlert',
    'TechnicalAlert',
    'BinanceAPI',
    'TaapiioAPI',
    'parse_cooldown',
    'get_indicators_list',
    'TECHNICAL_INDICATORS',
    'SIMPLE_COMPARISONS',
    'BINANCE_TIMEFRAMES'
]
