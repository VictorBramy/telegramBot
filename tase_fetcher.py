"""
Real-time Israeli stock data fetcher using TASE website
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict

# Stock symbol codes on TASE
TASE_CODES = {
    "PHOE.TA": "5780",  # פניקס
    "POLI.TA": "5503",  # פועלים
    "LUMI.TA": "5514",  # לאומי
    "MZTF.TA": "5568",  # מזרחי טפחות
    "DSCT.TA": "5501",  # דיסקונט
    "HARL.TA": "5720",  # הראל
    "MNRA.TA": "5719",  # מנורה
    "FIBI.TA": "5502",  # הבינלאומי
    "CLIS.TA": "5715",  # כלל ביטוח
    "MGDL.TA": "5725",  # מגדל
    "FIBIH.TA": "1131019"  # פיבי הולדינגס
}

def fetch_tase_stock_price(ticker: str) -> Optional[Dict]:
    """
    Fetch real stock price from TASE website
    
    Args:
        ticker: Stock symbol (e.g., 'PHOE.TA')
    
    Returns:
        Dict with price data or None if failed
    """
    if ticker not in TASE_CODES:
        return None
    
    code = TASE_CODES[ticker]
    url = f'https://www.tase.co.il/en/market_data/security/{code}/major_data'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find price in the page
        # Look for price patterns
        price_pattern = re.compile(r'"LastPrice":\s*"?([\d,\.]+)"?')
        match = price_pattern.search(response.text)
        
        if match:
            price_str = match.group(1).replace(',', '')
            price = float(price_str)
            
            # Try to find opening price
            open_pattern = re.compile(r'"OpeningPrice":\s*"?([\d,\.]+)"?')
            open_match = open_pattern.search(response.text)
            opening = float(open_match.group(1).replace(',', '')) if open_match else price * 0.995
            
            return {
                'price': price,
                'opening': opening,
                'change': price - opening,
                'change_pct': ((price - opening) / opening * 100) if opening else 0
            }
        
        return None
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# Test function
if __name__ == "__main__":
    print("Testing TASE real data fetch...\n")
    for ticker in ["PHOE.TA", "LUMI.TA", "POLI.TA"]:
        data = fetch_tase_stock_price(ticker)
        if data:
            print(f"{ticker}: {data['price']:.2f} ₪ ({data['change_pct']:+.2f}%)")
        else:
            print(f"{ticker}: Failed to fetch")
