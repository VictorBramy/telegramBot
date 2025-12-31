"""
Finance Handler Module
Calculates Israeli financial index values and analyzes stock prices
"""

import yfinance as yf
import pandas as pd
from typing import Dict, Optional, Tuple

# Portfolio weights for Israeli financial sector index (in percentages)
PORTFOLIO_WEIGHTS = {
    "PHOE.TA": 12.67,   # פניקס
    "POLI.TA": 11.95,   # פועלים
    "LUMI.TA": 11.94,   # לאומי
    "MZTF.TA": 11.20,   # מזרחי־טפחות
    "DSCT.TA": 11.11,   # דיסקונט
    "HARL.TA": 9.36,    # הראל השקעות
    "MNRA.TA": 8.25,    # מנורה מבטחים
    "FIBI.TA": 8.01,    # הבינלאומי
    "CLIS.TA": 5.50,    # כלל ביטוח
    "MGDL.TA": 4.94,    # מגדל ביטוח
    "FIBIH.TA": 3.00     # FIBI HOLDINGS (פיבי הולדינגס)
}

def fetch_live_data(tickers: list, period: str = "5d") -> pd.DataFrame:
    """
    Download live market data for given tickers
    
    Args:
        tickers: List of stock symbols
        period: Data period (default 5d)
    
    Returns:
        DataFrame with stock data
    """
    try:
        data = yf.download(
            tickers=list(tickers),
            period=period,
            interval="1d",
            progress=False
        )
        return data
    except Exception as e:
        raise Exception(f"Failed to fetch data: {str(e)}")

def calculate_index_value(weights: Dict[str, float], prices: Dict[str, float]) -> float:
    """
    Calculate weighted index value
    
    Args:
        weights: Dictionary of ticker weights (percentages)
        prices: Dictionary of current prices
    
    Returns:
        Weighted index value
    """
    total = 0
    for ticker, weight in weights.items():
        price = prices.get(ticker)
        if price:
            total += price * (weight / 100)
    return total

def get_index_data() -> Tuple[float, float, float, Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    """
    Get current index data including prices and changes
    
    Returns:
        Tuple of (index_value, index_change, index_change_pct, live_prices, opening_prices)
    """
    # Fetch live data
    df = fetch_live_data(PORTFOLIO_WEIGHTS.keys())
    
    # Extract current and opening prices
    live_prices = {}
    opening_prices = {}
    
    for ticker in PORTFOLIO_WEIGHTS.keys():
        try:
            if ticker in df["Close"].columns:
                price = df["Close"][ticker].iloc[-1]
                live_prices[ticker] = float(price) if not pd.isna(price) else None
                
                open_price = df["Open"][ticker].iloc[-1]
                opening_prices[ticker] = float(open_price) if not pd.isna(open_price) else None
            else:
                live_prices[ticker] = None
                opening_prices[ticker] = None
        except Exception:
            live_prices[ticker] = None
            opening_prices[ticker] = None
    
    # Calculate index values
    index_value = calculate_index_value(PORTFOLIO_WEIGHTS, live_prices)
    index_opening = calculate_index_value(PORTFOLIO_WEIGHTS, opening_prices)
    
    # Calculate change
    index_change = index_value - index_opening
    index_change_pct = (index_change / index_opening * 100) if index_opening != 0 else 0
    
    return index_value, index_change, index_change_pct, live_prices, opening_prices

def format_index_report() -> str:
    """
    Generate formatted index report for Telegram
    
    Returns:
        Formatted text report
    """
    try:
        index_value, index_change, index_change_pct, live_prices, opening_prices = get_index_data()
        
        # Build report
        report = f"📊 **מדד הפיננסים הישראלי**\n\n"
        report += f"💰 **שווי משוקלל:** {index_value:.2f} ₪\n"
        
        # Add emoji based on change direction
        change_emoji = "📈" if index_change >= 0 else "📉"
        report += f"{change_emoji} **שינוי:** {index_change:+.2f} ₪ ({index_change_pct:+.2f}%)\n\n"
        
        report += "📋 **מחירי מניות:**\n"
        
        # Sort by weight (descending)
        sorted_stocks = sorted(PORTFOLIO_WEIGHTS.items(), key=lambda x: x[1], reverse=True)
        
        for ticker, weight in sorted_stocks:
            price = live_prices.get(ticker)
            if price:
                try:
                    # Get additional info
                    stock_info = yf.Ticker(ticker).info
                    pct_change = stock_info.get("regularMarketChangePercent", 0)
                    if pct_change is None:
                        pct_change = 0
                    
                    # Format ticker name
                    name = ticker.replace(".TA", "")
                    change_emoji = "🟢" if pct_change >= 0 else "🔴"
                    
                    report += f"{change_emoji} `{name}`: {price:.2f} ₪ ({pct_change:+.2f}%) - משקל: {weight}%\n"
                except Exception:
                    name = ticker.replace(".TA", "")
                    report += f"⚪ `{name}`: {price:.2f} ₪ - משקל: {weight}%\n"
            else:
                name = ticker.replace(".TA", "")
                report += f"⚫ `{name}`: לא זמין - משקל: {weight}%\n"
        
        report += f"\n🕐 **עדכון:** בזמן אמת"
        
        return report
        
    except Exception as e:
        return f"❌ **שגיאה בטעינת נתונים:**\n{str(e)}"

def test_symbol(symbol: str) -> str:
    """
    Test if a stock symbol is valid and get its current price
    
    Args:
        symbol: Stock symbol to test
    
    Returns:
        Formatted result string
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            price = hist['Close'][-1]
            return f"✅ **{symbol}** - מחיר: {price:.2f} ₪"
        else:
            return f"❌ **{symbol}** - אין נתונים זמינים"
    except Exception as e:
        return f"❌ **{symbol}** - שגיאה: {str(e)}"

def get_stock_info(symbol: str) -> str:
    """
    Get detailed information about a specific stock
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Formatted stock information
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return f"❌ לא נמצאו נתונים עבור {symbol}"
        
        current_price = hist['Close'][-1]
        open_price = hist['Open'][-1]
        high_price = hist['High'][-1]
        low_price = hist['Low'][-1]
        volume = hist['Volume'][-1]
        
        change = current_price - open_price
        change_pct = (change / open_price * 100) if open_price != 0 else 0
        
        change_emoji = "📈" if change >= 0 else "📉"
        
        report = f"📊 **מידע על {symbol}**\n\n"
        report += f"💰 **מחיר נוכחי:** {current_price:.2f} ₪\n"
        report += f"{change_emoji} **שינוי:** {change:+.2f} ₪ ({change_pct:+.2f}%)\n\n"
        report += f"📊 **פתיחה:** {open_price:.2f} ₪\n"
        report += f"📈 **גבוה:** {high_price:.2f} ₪\n"
        report += f"📉 **נמוך:** {low_price:.2f} ₪\n"
        report += f"📦 **מחזור:** {volume:,.0f}\n"
        
        # Add company name if available
        if 'longName' in info:
            report = f"🏢 **{info['longName']}**\n\n" + report
        
        return report
        
    except Exception as e:
        return f"❌ **שגיאה:**\n{str(e)}"
